# src/api/routes.py

import json
from fastapi import APIRouter, HTTPException, UploadFile, File
from src.api.schemas import AnalyzeRequest, AnalyzeResponse, ViolationItem
from src.rules_engine.evaluate import evaluate_tenant, evaluate_record, load_rules
from src.scoring.score import calculate_score
from src.privacy_gateway.redact import redact_dict

router = APIRouter()


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

        # Step 2: Calculate risk score
        score = calculate_score(result['violations'])

        # Step 3: Build violation items
        violations = [
            ViolationItem(
                rule_id      = v['rule_id'],
                rule_name    = v['rule_name'],
                dpdp_section = v['dpdp_section'],
                severity     = v['severity'],
                risk_weight  = v['risk_weight'],
                reason       = v['reason']
            )
            for v in result['violations']
        ]

        # Step 4: Return response
        return AnalyzeResponse(
            tenant_id       = request.tenant_id,
            violation_count = result['total_violations'],
            risk_score      = score['score'],
            risk_tier       = score['tier'],
            violations      = violations,
            status          = "success"
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
    policies:  UploadFile = File(...),
    logs:      UploadFile = File(...),
    inventory: UploadFile = File(...)
):
    """
    Run full compliance check on uploaded files.

    Input:
        3 JSON files uploaded directly:
        - policies.json
        - logs.json
        - system_inventory.json

    Output:
        Full compliance report with violations and risk score
    """
    try:
        # ── Step 1: Read uploaded files ──────────────────
        policies_data  = json.loads(await policies.read())
        logs_data      = json.loads(await logs.read())
        inventory_data = json.loads(await inventory.read())

        # ── Step 2: Redact PII from all files ────────────
        policies_data  = redact_dict(policies_data)
        logs_data      = redact_dict(logs_data)
        inventory_data = redact_dict(inventory_data)

        # ── Step 3: Merge into one combined record ────────
        combined_record = {}

        if isinstance(policies_data, dict):
            combined_record.update(policies_data)

        if isinstance(logs_data, list) and len(logs_data) > 0:
            combined_record.update(logs_data[0])
        elif isinstance(logs_data, dict):
            combined_record.update(logs_data)

        if isinstance(inventory_data, dict):
            combined_record.update(inventory_data)
        elif isinstance(inventory_data, list) and len(inventory_data) > 0:
            combined_record.update(inventory_data[0])

        # ── Step 4: Run rules engine ──────────────────────
        rules      = load_rules()
        violations_raw = evaluate_record(combined_record, rules)

        # ── Step 5: Calculate risk score ──────────────────
        score = calculate_score(violations_raw)

        # ── Step 6: Build violation items ─────────────────
        violations = [
            ViolationItem(
                rule_id      = v['rule_id'],
                rule_name    = v['rule_name'],
                dpdp_section = v['dpdp_section'],
                severity     = v['severity'],
                risk_weight  = v['risk_weight'],
                reason       = v['reason']
            )
            for v in violations_raw
        ]

        # ── Step 7: Return response ───────────────────────
        return AnalyzeResponse(
            tenant_id       = "uploaded_tenant",
            violation_count = len(violations),
            risk_score      = score['score'],
            risk_tier       = score['tier'],
            violations      = violations,
            status          = "success"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code = 400,
            detail      = "Invalid JSON in uploaded files. "
                          "Make sure all 3 files are valid JSON."
        )
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail      = f"Upload analysis failed: {str(e)}"
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