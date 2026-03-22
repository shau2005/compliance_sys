# src/api/routes.py

from fastapi import APIRouter, HTTPException
from src.api.schemas import AnalyzeRequest, AnalyzeResponse, ViolationItem
from src.rules_engine.evaluate import evaluate_tenant
from src.scoring.score import calculate_score

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
    Run full compliance check for a tenant.

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
# ```

# Save the file.

# ---

# ## What This Does Simply
# ```
# GET  /health   → confirms API is running
# POST /analyze  → runs full pipeline, returns report

# If tenant not found → returns 404 error
# If anything breaks  → returns 500 error