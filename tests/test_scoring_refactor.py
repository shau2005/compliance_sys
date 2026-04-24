"""
Regression tests for the current agent-layer compliance engine.
"""

from src.agent_layer.orchestrator import run_compliance_analysis
from src.explainability.service import get_explanation


def test_tenant_a_compliant_shape():
    result = run_compliance_analysis("tenant_a")
    assert result["status"] == "success"
    assert "risk_score" in result
    assert "risk_tier" in result
    assert "violations" in result


def test_tenant_b_noncompliant_has_fields():
    result = run_compliance_analysis("tenant_b")
    assert result["status"] == "success"
    assert isinstance(result["violations"], list)
    assert isinstance(result["total_violations"], int)
    assert result["risk_tier"] in {"COMPLIANT", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_tenant_c_repeatable_results():
    first = run_compliance_analysis("tenant_c")
    second = run_compliance_analysis("tenant_c")

    assert first["status"] == "success"
    assert second["status"] == "success"
    assert first["risk_tier"] == second["risk_tier"]


def test_explanation_dpdp006():
    exp = get_explanation("DPDP-006")
    why = exp["why_detected"].lower()
    assert "third" in why or "sharing" in why


def test_explanation_dpdp007():
    exp = get_explanation("DPDP-007")
    why = exp["why_detected"].lower()
    assert "minim" in why or "collect" in why
