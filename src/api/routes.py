# src/api/routes.py

import json
import os
import psycopg
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from src.api.schemas import AnalyzeRequest, AnalyzeResponse, ViolationItem, ExplanationDetail
from src.rules_engine.evaluate import evaluate_tenant, evaluate_record, load_rules
from src.scoring.score import calculate_score
from src.privacy_gateway.redact import redact_file, redact_dict
from src.explainability.service import enrich_violations
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'tenant_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'rasika23')

router = APIRouter()

def get_db_connection():
    return psycopg.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=False
    )


@router.get("/health")
def health_check():
    """
    Simple health check endpoint.
    Visit http://localhost:8000/health to confirm API is running.
    """
    return {
        "status": "running",
        "service": "DPDP Compliance Engine"
    }

@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_tenant(request: AnalyzeRequest):
    """
    Run full compliance check for a known tenant.

    Input:
        { "tenant_id": "tenant_b" }

    Output:
        Full compliance report with violations and risk score
    """
    try:
        # Step 1: Run rules engine
        result = evaluate_tenant(request.tenant_id)

        # Step 2: Enrich violations with explanations
        enriched_violations = enrich_violations(result['violations'])

        # Step 3: Calculate risk score using frequency-weighted formula
        score = calculate_score(enriched_violations)

        # Step 4: Build violation items with occurrence count and contribution
        violations = [
            ViolationItem(
                rule_id              = v['rule_id'],
                rule_name            = v['rule_name'],
                dpdp_section         = v['dpdp_section'],
                severity             = v['severity'],
                risk_weight          = v['risk_weight'],
                occurrence_count     = v.get('occurrence_count', 1),
                contribution_to_score= next(
                    (b['contribution_to_score'] for b in score['breakdown'] 
                     if b['rule_id'] == v['rule_id']),
                    0.0
                ),
                reason               = v['reason'],
                explanation          = ExplanationDetail(
                    why_detected = v['explanation']['why_detected'],
                    evidence     = v['explanation']['evidence'],
                    risk_reason  = v['explanation']['risk_reason'],
                    mitigation   = v['explanation']['mitigation']
                ) if 'explanation' in v else None
            )
            for v in enriched_violations
        ]

        # Step 4: Return response
        return AnalyzeResponse(
            tenant_id                   = request.tenant_id,
            unique_rules_violated       = result['unique_rules_violated'],
            total_violation_occurrences = result['total_violation_occurrences'],
            risk_score                  = score['score'],
            risk_tier                   = score['tier'],
            violations                  = violations,
            status                      = "success"
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code = 404,
            detail      = f"Tenant '{request.tenant_id}' not found. "
                          f"Check that redacted files exist."
        )
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail      = f"Analysis failed: {str(e)}"
        )


@router.post("/analyze/upload", response_model=AnalyzeResponse)
async def analyze_upload(
    policies:      UploadFile = File(...),
    logs:          UploadFile = File(...),
    inventory:     UploadFile = File(...),
    tenant_id:     str = Form(...),
    company_name:  str = Form(...)
):
    """
    Run full compliance check on uploaded files.

    Input:
        3 JSON files uploaded directly:
        - policies.json
        - logs.json
        - system_inventory.json
        - tenant_id (form field)

    Output:
        Full compliance report with violations and risk score
    """
    try:
        # ── Step 1: Read uploaded files ──────────────────
        policies_data  = json.loads(await policies.read())
        logs_data      = json.loads(await logs.read())
        inventory_data = json.loads(await inventory.read())

        # ── Step 2: Redact PII from all files ────────────
        policies_data = redact_file(policies_data, "policies.json")
        logs_data = redact_file(logs_data, "logs.json")
        inventory_data = redact_file(inventory_data, "system_inventory.json")

        # ── Step 3: Check or insert tenant ─────
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Check if tenant exists
                    cur.execute(
                        "SELECT tenant_id FROM tenants WHERE company_name = %s",
                        (company_name,)
                    )
                    existing = cur.fetchone()
                    if existing:
                        db_tenant_id = existing[0]
                    else:
                        cur.execute(
                            "INSERT INTO tenants (company_name) VALUES (%s) RETURNING tenant_id",
                            (company_name,)
                        )
                        db_tenant_id = cur.fetchone()[0]
                    conn.commit()
        except Exception as db_ex:
            raise HTTPException(status_code=500, detail=f"Tenant DB operation failed: {db_ex}")

        # ── Step 4: Store redacted data in DB ──────────
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Insert policies
                    cur.execute(
                        "INSERT INTO policies (tenant_id, policy_json) VALUES (%s, %s)",
                        (db_tenant_id, json.dumps(policies_data))
                    )
                    # Insert inventory
                    cur.execute(
                        "INSERT INTO redacted_sysinv (tenant_id, inventory_json) VALUES (%s, %s)",
                        (db_tenant_id, json.dumps(inventory_data))
                    )
                    # Insert combined logs as a single row in redacted_logs
                    cur.execute(
                        "INSERT INTO redacted_logs (tenant_id, log_json) VALUES (%s, %s)",
                        (db_tenant_id, json.dumps(logs_data))
                    )
                    conn.commit()
        except Exception as db_ex:
            raise HTTPException(status_code=500, detail=f"Redacted data DB insert failed: {db_ex}")

        # ── Step 5: Create base record from policies + inventory ──────────
        base_record = {}

        if isinstance(policies_data, dict):
            base_record.update(policies_data)

        if isinstance(inventory_data, dict):
            base_record.update(inventory_data)
        elif isinstance(inventory_data, list) and len(inventory_data) > 0:
            base_record.update(inventory_data[0])

        # ── Step 6: Run rules engine on base record ──────────────────────
        rules = load_rules()
        all_violations = []
        
        # Evaluate base record (policies + inventory)
        violations_base = evaluate_record(base_record, rules)
        all_violations.extend(violations_base)
        
        # ── Step 7: Evaluate EACH log entry separately ─────────────────
        if isinstance(logs_data, list):
            # ✅ FIXED: Loop through ALL log entries, not just first
            for log_entry in logs_data:
                if isinstance(log_entry, dict):
                    # Create combined record: base + individual log entry
                    combined_record = {**base_record, **log_entry}
                    
                    # Evaluate this specific log entry
                    log_violations = evaluate_record(combined_record, rules)
                    all_violations.extend(log_violations)
        
        elif isinstance(logs_data, dict):
            # If logs is a single dict, treat it as one entry
            combined_record = {**base_record, **logs_data}
            log_violations = evaluate_record(combined_record, rules)
            all_violations.extend(log_violations)
        
        # ── Step 8: Separate and deduplicate violations by type ────────────
        # Policy violations should be counted ONCE (from base record evaluation)
        # Log violations should be counted PER LOG ENTRY
        
        policy_violations = {}  # Policy rules - count once
        log_violations_list = []  # Log rules - count per log
        
        # Separate violations by entity type
        for violation in all_violations:
            rule_id = violation.get("rule_id")
            entity = violation.get("entity", "")
            evidence = violation.get("evidence", {})
            log_id = evidence.get("log_id")
            
            # Policy/inventory violations - only keep first occurrence
            if entity in ["customer_personal_data", "data_inventory"]:
                if rule_id not in policy_violations:
                    policy_violations[rule_id] = {
                        **violation,
                        "occurrence_count": 1
                    }
            # Log violations - track by rule + log_id
            else:
                key = f"{rule_id}:{log_id}" if log_id else rule_id
                log_violations_list.append({
                    "rule_id": rule_id,
                    "violation_obj": violation,
                    "key": key
                })
        
        # Deduplicate log violations by rule + log_id
        unique_log_violations = {}
        for item in log_violations_list:
            key = item["key"]
            if key not in unique_log_violations:
                unique_log_violations[key] = {
                    **item["violation_obj"],
                    "occurrence_count": 1
                }
            else:
                unique_log_violations[key]["occurrence_count"] += 1
        
        # ── Step 9: Aggregate by rule_id ──────────────────────────────────
        violations_by_rule = {}
        
        # Add policy violations
        for rule_id, violation in policy_violations.items():
            violations_by_rule[rule_id] = violation
        
        # Add log violations (aggregate by rule_id)
        for violation_key, violation in unique_log_violations.items():
            rule_id = violation.get("rule_id")
            
            if rule_id not in violations_by_rule:
                violations_by_rule[rule_id] = {
                    **violation,
                    "occurrence_count": violation.get("occurrence_count", 1)
                }
            else:
                # Accumulate occurrence count for recurring logs
                violations_by_rule[rule_id]["occurrence_count"] += violation.get("occurrence_count", 1)
        
        violations_raw = list(violations_by_rule.values())
        
        # ── Step 8: Enrich violations with explanations ──────────────────
        enriched_violations = enrich_violations(violations_raw)
        
        # ── Step 9: Calculate risk score using frequency-weighted formula ──
        score = calculate_score(enriched_violations)

        # ── Step 10: Build violation items with occurrence and contribution ──
        violations = [
            ViolationItem(
                rule_id              = v['rule_id'],
                rule_name            = v['rule_name'],
                dpdp_section         = v['dpdp_section'],
                severity             = v['severity'],
                risk_weight          = v['risk_weight'],
                occurrence_count     = v.get('occurrence_count', 1),
                contribution_to_score= next(
                    (b['contribution_to_score'] for b in score['breakdown'] 
                     if b['rule_id'] == v['rule_id']),
                    0.0
                ),
                reason               = v['reason'],
                explanation          = ExplanationDetail(
                    why_detected = v['explanation']['why_detected'],
                    evidence     = v['explanation']['evidence'],
                    risk_reason  = v['explanation']['risk_reason'],
                    mitigation   = v['explanation']['mitigation']
                ) if 'explanation' in v else None
            )
            for v in enriched_violations
        ]

        # ── Step 11: Save evaluation result to DB ──

        try:

            with get_db_connection() as conn:

                with conn.cursor() as cur:

                    cur.execute(

                        "INSERT INTO evaluation_results (tenant_id, result_json, risk_score) VALUES (%s, %s, %s)",

                        (

                            db_tenant_id,

                            json.dumps({

                                "tenant_id": str(db_tenant_id),

                                "unique_rules_violated": len(enriched_violations),

                                "total_violation_occurrences": sum(v.get('occurrence_count', 1) for v in enriched_violations),

                                "risk_score": score['score'],

                                "risk_tier": score['tier'],

                                "violations": [v.dict() for v in violations],

                                "status": "success"

                            }),

                            float(score['score'])

                        )

                    )

                    conn.commit()

        except Exception as db_ex:

            raise HTTPException(

                status_code=500,

                detail=f"Evaluation results DB insert failed: {db_ex}"

            )

        # ── Step 12: Return response ──

        return AnalyzeResponse(

            tenant_id                   = str(db_tenant_id),

            unique_rules_violated       = len(enriched_violations),

            total_violation_occurrences = sum(v.get('occurrence_count', 1) for v in enriched_violations),

            risk_score                  = score['score'],

            risk_tier                   = score['tier'],

            violations                  = violations,

            status                      = "success"

        )

    except json.JSONDecodeError:

        raise HTTPException(

            status_code=400,

            detail="Invalid JSON in uploaded files. Make sure all 3 files are valid JSON."

        )

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=f"Upload analysis failed: {str(e)}"

        )
# ```

# Save the file.

# ---

# ## What Changed
# ```
# Kept:    GET  /health
# Kept:    POST /analyze        (tenant_id based)
# Added:   POST /analyze/upload (3 file uploads)

# New endpoint does:
# 1. Reads 3 uploaded JSON files
# 2. Redacts PII from all 3
# 3. Merges into one combined record
# 4. Runs rules engine
# 5. Calculates risk score
# 6. Returns compliance report