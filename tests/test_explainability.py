import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.explainability.service import (
    RULE_EXPLANATIONS,
    explain_violation,
    enrich_violations,
    generate_executive_summary,
)
from src.explainability.explanation import ViolationExplanation


def test_get_single_explanation():
    """Test retrieving explanation for a known violation."""
    print("\n" + "="*70)
    print("TEST 1: Get Single Explanation for DPDP-001")
    print("="*70)
    
    mock_violation = {
        "rule_id": "DPDP-001",
        "rule_name": "Consent Validity",
        "dpdp_section": "Section 6(1)",
        "agent_name": "Regulation Agent",
        "outcome": "VIOLATION",
        "severity": "HIGH",
        "penalty_exposure_crore": 200,
        "signals_fired": ["S1", "S2"],
        "signal_reasons": ["Status is Revoked", "Event date 2024-05-12 is after expiry"]
    }
    
    explanation = explain_violation(mock_violation, risk_contribution=15.5)
    
    print(f"\nRule: DPDP-001 - {explanation.rule_name}")
    print(f"Top Signal: {explanation.top_contributing_signal} (Weight: {explanation.top_signal_weight})")
    print(f"\n[WHY VIOLATION]\n   {explanation.why_violation}")
    print(f"\n[WHAT HAPPENED]\n   {explanation.what_happened}")
    print(f"\n[REMEDIATION STEPS]")
    for i, step in enumerate(explanation.remediation_steps, 1):
        print(f"   {i}. {step}")
    print("\n[SIGNALS ANALYSIS]")
    for s in explanation.signals_analysis:
        print(f"   {s['signal']} (Fired={s['fired']}, W={s['weight']}) -> {s['reason']}")


def test_enrich_violations():
    """Test that a list of violations is enriched accurately."""
    print("\n" + "="*70)
    print("TEST 2: Enrich List of Violations")
    print("="*70)
    
    raw_violations = [
        {
            "rule_id": "DPDP-002",
            "outcome": "VIOLATION",
            "severity": "CRITICAL",
            "penalty_exposure_crore": 250,
            "signals_fired": ["S1"],
            "signal_reasons": ["Purpose mismatch in targeted marketing"]
        },
        {
            "rule_id": "DPDP-007",
            "outcome": "WARNING",
            "severity": "MEDIUM",
            "penalty_exposure_crore": 50,
            "signals_fired": [],
            "signal_reasons": []
        }
    ]
    
    contributions = {"DPDP-002": 25.0, "DPDP-007": 0.0}
    enriched = enrich_violations(raw_violations, contributions)
    
    print(f"Enriched {len(enriched)} records.")
    for e in enriched:
        print(f" - {e.rule_id} (Outcome: {e.outcome}, Risk Contrib: {e.risk_contribution})")


def run_all_tests():
    """Run all test/demonstration functions."""
    print("\nRUNNING XAI LAYER TESTS")
    test_get_single_explanation()
    test_enrich_violations()
    print("\nALL XAI TESTS COMPLETED\n")


if __name__ == "__main__":
    run_all_tests()
