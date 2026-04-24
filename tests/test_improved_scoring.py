#!/usr/bin/env python3
"""
Regression test for the current agent-layer compliance scoring pipeline.
"""

from src.agent_layer.orchestrator import run_compliance_analysis


def test_improved_scoring():
    """Validate that orchestrator returns a well-formed score result."""
    tenant_id = "tenant_c"
    result = run_compliance_analysis(tenant_id)

    assert result["status"] == "success"
    assert "risk_score" in result
    assert "risk_tier" in result
    assert "violations" in result
    assert isinstance(result["violations"], list)

    # If violations exist, score should be positive.
    if result["total_violations"] > 0:
        assert float(result["risk_score"]) > 0
