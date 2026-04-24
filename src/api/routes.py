import json
import os
import psycopg
import tempfile
import shutil
from pathlib import Path
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from src.api.schemas import AnalyzeRequest, AnalyzeResponse, ViolationItem, ExplanationDetail
from src.rules_engine.evaluate import evaluate_tenant, evaluate_record, load_rules
from src.scoring.score import calculate_score
from src.explainability.service import enrich_violations
from src.anonymization.csv_loader import load_tenant_csvs
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
        enriched_violations = enrich_violations(
            result['violations'], {}
        )

        # Step 3: Calculate risk score using frequency-weighted formula
        score = calculate_score(enriched_violations)

        # Step 4: Build violation items with occurrence count, contribution, and traceability
        violations = [
            ViolationItem(
                rule_id               = v.rule_id,
                rule_name             = v.rule_name,
                dpdp_section          = v.dpdp_section,
                severity              = v.severity,
                risk_weight           = 0.0,
                occurrence_count      = 1,
                contribution_to_score = v.risk_contribution,
                reason                = v.what_happened,
                explanation           = ExplanationDetail(
                    why_detected = v.why_violation,
                    evidence     = str([
                        s for s in v.signals_analysis
                        if s.get("fired")
                    ]),
                    risk_reason  = v.root_cause,
                    mitigation   = (
                        v.remediation_steps[0]
                        if v.remediation_steps else ""
                    )
                ),
                matched_record_ids    = [],
                fields_triggered      = [],
                matched_logs_count    = 0
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
    governance_config: UploadFile = File(...),
    customer_master: UploadFile = File(...),
    consent_records: UploadFile = File(...),
    transaction_events: UploadFile = File(...),
    access_logs: UploadFile = File(...),
    data_lifecycle: UploadFile = File(...),
    security_events: UploadFile = File(...),
    dsar_requests: UploadFile = File(...),
    system_inventory: UploadFile = File(...),
    policies: UploadFile = File(...),
    tenant_id: str = Form(...),
    tenant_name: str = Form(...)
):
    """
    Run full compliance check on 10 uploaded CSV files.

    Input:
        10 CSV files uploaded:
        - governance_config.csv
        - customer_master.csv
        - consent_records.csv
        - transaction_events.csv
        - access_logs.csv
        - data_lifecyle.csv
        - security_events.csv
        - dsar_requests.csv
        - system_inventory.csv
        - policies.csv
        - tenant_id (form field)
        - tenant_name (form field)

    Flow:
        1. Receive 10 CSV files
        2. Pass directly to csv_loader.py for anonymization
        4. Run compliance check
        5. Return report

    Output:
        Full compliance report with violations and risk score
    """
    try:
        # ── Step 1: Write uploaded CSV files to temp directory ───────────
        # and pass directly to csv_loader for validation/anonymization
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()

            uploaded_file_map = {
                "governance_config.csv": governance_config,
                "customer_master.csv": customer_master,
                "consent_records.csv": consent_records,
                "transaction_events.csv": transaction_events,
                "access_logs.csv": access_logs,
                "data_lifecycle.csv": data_lifecycle,
                "security_events.csv": security_events,
                "dsar_requests.csv": dsar_requests,
                "system_inventory.csv": system_inventory,
                "policies.csv": policies,
            }

            for csv_filename, uploaded_file in uploaded_file_map.items():
                csv_bytes = await uploaded_file.read()
                csv_path = Path(temp_dir) / csv_filename
                with open(csv_path, "wb") as f:
                    f.write(csv_bytes)

            # ── Step 2: Pass to csv_loader.load_tenant_csvs ───────────────
            anonymized_data = load_tenant_csvs(Path(temp_dir), tenant_id)
            
        except Exception as loader_error:
            raise HTTPException(
                status_code=500,
                detail=f"CSV loader anonymization failed: {str(loader_error)}"
            )
        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

        # ── Step 4: Check or insert tenant ─────
        try:
            # governance_config is the tenant anchor in the schema.
            # No separate tenants table exists.
            # tenant_id from the form is used directly as the
            # database identifier.
            db_tenant_id = tenant_id
        except Exception as db_ex:
            raise HTTPException(status_code=500, detail=f"Tenant DB operation failed: {db_ex}")

        # ── Step 5: Create base records from single-row tables ──
        base_record = {}
        
        # Add governance config
        if "governance_config" in anonymized_data and len(anonymized_data["governance_config"]) > 0:
            base_record.update(anonymized_data["governance_config"].iloc[0].to_dict())
        
        # Add system inventory
        if "system_inventory" in anonymized_data and len(anonymized_data["system_inventory"]) > 0:
            base_record.update(anonymized_data["system_inventory"].iloc[0].to_dict())
        
        # Add policies
        if "policies" in anonymized_data and len(anonymized_data["policies"]) > 0:
            base_record.update(anonymized_data["policies"].iloc[0].to_dict())

        # ── Step 6: Run rules engine on base record ──────────────────────
        rules = load_rules()
        all_violations = []
        
        # Evaluate base record
        violations_base = evaluate_record(base_record, rules)
        all_violations.extend(violations_base)
        
        # ── Step 7: Evaluate EACH transaction and event record ───────────
        # Process all multi-row tables
        multi_row_tables = [
            "customer_master",
            "consent_records",
            "transaction_events",
            "access_logs",
            "data_lifecycle",
            "security_events",
            "dsar_requests"
        ]
        
        for table_name in multi_row_tables:
            if table_name in anonymized_data:
                for idx, row in anonymized_data[table_name].iterrows():
                    record = row.to_dict()
                    # Combine base record with individual row
                    combined_record = {**base_record, **record}
                    
                    # Evaluate this specific record
                    record_violations = evaluate_record(combined_record, rules)
                    all_violations.extend(record_violations)
        
        # ── Step 8: Separate and deduplicate violations by type ────────────
        policy_violations = {}  # Policy rules - count once
        record_violations_list = []  # Record-based violations - count per record
        
        # Separate violations by entity type
        for violation in all_violations:
            rule_id = violation.get("rule_id")
            entity = violation.get("entity", "")
            evidence = violation.get("evidence", {})
            record_id = evidence.get("record_id")
            
            # Policy/inventory violations - only keep first occurrence
            if entity in ["governance_config", "system_inventory", "policies"]:
                if rule_id not in policy_violations:
                    policy_violations[rule_id] = {
                        **violation,
                        "occurrence_count": 1
                    }
            # Record violations - track by rule + record_id
            else:
                key = f"{rule_id}:{record_id}" if record_id else rule_id
                record_violations_list.append({
                    "rule_id": rule_id,
                    "violation_obj": violation,
                    "key": key
                })
        
        # Deduplicate record violations by rule + record_id
        unique_record_violations = {}
        for item in record_violations_list:
            key = item["key"]
            if key not in unique_record_violations:
                unique_record_violations[key] = {
                    **item["violation_obj"],
                    "occurrence_count": 1
                }
            else:
                unique_record_violations[key]["occurrence_count"] += 1
        
        # ── Step 9: Aggregate by rule_id ──────────────────────────────────
        violations_by_rule = {}
        
        # Add policy violations
        for rule_id, violation in policy_violations.items():
            violations_by_rule[rule_id] = violation
        
        # Add record violations (aggregate by rule_id)
        for violation_key, violation in unique_record_violations.items():
            rule_id = violation.get("rule_id")
            
            if rule_id not in violations_by_rule:
                violations_by_rule[rule_id] = {
                    **violation,
                    "occurrence_count": violation.get("occurrence_count", 1)
                }
            else:
                # Accumulate occurrence count for recurring violations
                violations_by_rule[rule_id]["occurrence_count"] += violation.get("occurrence_count", 1)
        
        violations_raw = list(violations_by_rule.values())
        
        # ── Step 10: Enrich violations with explanations ──────────────────
        enriched_violations = enrich_violations(violations_raw, {})
        
        # ── Step 11: Calculate risk score using frequency-weighted formula ──
        score = calculate_score(enriched_violations)

        # ── Step 12: Build violation items with occurrence and contribution ──
        violations = [
            ViolationItem(
                rule_id               = v.rule_id,
                rule_name             = v.rule_name,
                dpdp_section          = v.dpdp_section,
                severity              = v.severity,
                risk_weight           = 0.0,
                occurrence_count      = 1,
                contribution_to_score = v.risk_contribution,
                reason                = v.what_happened,
                explanation           = ExplanationDetail(
                    why_detected = v.why_violation,
                    evidence     = str([
                        s for s in v.signals_analysis
                        if s.get("fired")
                    ]),
                    risk_reason  = v.root_cause,
                    mitigation   = (
                        v.remediation_steps[0]
                        if v.remediation_steps else ""
                    )
                ),
                matched_record_ids    = [],
                fields_triggered      = [],
                matched_logs_count    = 0
            )
            for v in enriched_violations
        ]

        # ── Step 13: Save evaluation result to DB ──

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
            import logging
            logging.warning(
                f"evaluation_results insert skipped "
                f"(table may not exist yet): {db_ex}"
            )

        # ── Step 14: Return response ──

        return AnalyzeResponse(

            tenant_id                   = str(db_tenant_id),

            unique_rules_violated       = len(enriched_violations),

            total_violation_occurrences = sum(v.get('occurrence_count', 1) for v in enriched_violations),

            risk_score                  = score['score'],

            risk_tier                   = score['tier'],

            violations                  = violations,

            status                      = "success"

        )

    except ValueError as val_error:
        raise HTTPException(
            status_code=400,
            detail=f"Validation error: {str(val_error)}"
        )

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=f"Upload analysis failed: {str(e)}"

        )