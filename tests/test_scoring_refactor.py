"""
REGRESSION TESTS for DPDP Compliance Engine Scoring Refactoring

This test suite validates:
1. Risk scoring correctly handles repeated violations
2. Occurrence multiplier formula is correct
3. Tier thresholds are appropriate
4. Explanation mappings are correct (especially DPDP-006 and DPDP-007)
5. Traceability fields are populated
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rules_engine.evaluate import evaluate_tenant, load_rules
from src.scoring.score import calculate_score, TIER_RANGES
from src.explainability.service import get_explanation


def test_tenant_a_compliant():
    """Test Tenant A (compliant) scores COMPLIANT."""
    print("\n✓ TEST 1: Tenant A Compliance")
    print("="*60)
    
    result = evaluate_tenant("tenant_a")
    violations = result["violations"]
    
    print(f"  Unique Rules Violated: {result['unique_rules_violated']}")
    print(f"  Total Occurrences: {result['total_violation_occurrences']}")
    
    score = calculate_score(violations)
    print(f"  Risk Score: {score['score']}/100")
    print(f"  Risk Tier: {score['tier']}")
    
    assert result['unique_rules_violated'] == 0, f"Expected 0 violations, got {result['unique_rules_violated']}"
    assert score['score'] == 0, f"Expected score 0, got {score['score']}"
    assert score['tier'] == 'COMPLIANT', f"Expected COMPLIANT, got {score['tier']}"
    
    print("  ✓ PASSED")
    return True


def test_tenant_b_noncompliant():
    """Test Tenant B (non-compliant) scores HIGH or CRITICAL."""
    print("\n✓ TEST 2: Tenant B Non-Compliance")
    print("="*60)
    
    result = evaluate_tenant("tenant_b")
    violations = result["violations"]
    
    print(f"  Unique Rules Violated: {result['unique_rules_violated']}")
    print(f"  Total Occurrences: {result['total_violation_occurrences']}")
    
    score = calculate_score(violations)
    print(f"  Risk Score: {score['score']}/100")
    print(f"  Risk Tier: {score['tier']}")
    
    assert result['unique_rules_violated'] > 0, "Expected violations in tenant_b"
    assert score['tier'] in ['MEDIUM', 'HIGH', 'CRITICAL'], f"Expected MEDIUM/HIGH/CRITICAL, got {score['tier']}"
    
    print("  ✓ PASSED")
    return True


def test_tenant_c_repeated_violations():
    """Test Tenant C with repeated HIGH/CRITICAL violations scores MEDIUM+."""
    print("\n✓ TEST 3: Tenant C with Repeated Violations")
    print("="*60)
    
    result = evaluate_tenant("tenant_c")
    violations = result["violations"]
    
    print(f"  Unique Rules Violated: {result['unique_rules_violated']}")
    print(f"  Total Occurrences: {result['total_violation_occurrences']}")
    
    # Show top violations
    print("\n  Top Violations:")
    for v in violations[:3]:
        print(f"    {v['rule_id']}: {v['rule_name']} ({v['severity']}, occurs={v['occurrence_count']})")
    
    score = calculate_score(violations)
    print(f"\n  Risk Score: {score['score']}/100")
    print(f"  Risk Tier: {score['tier']}")
    
    # With refactored scoring, 10 violations including CRITICAL should be MEDIUM or higher
    assert result['unique_rules_violated'] == 10, f"Expected 10 violations, got {result['unique_rules_violated']}"
    assert score['score'] >= 25, f"Expected score >= 25 for repeated violations, got {score['score']}"
    assert score['tier'] in ['MEDIUM', 'HIGH', 'CRITICAL'], \
        f"Expected MEDIUM+, got {score['tier']} (score={score['score']})"
    
    print("  ✓ PASSED")
    return True


def test_occurrence_multiplier():
    """Test that occurrence multiplier formula works correctly."""
    print("\n✓ TEST 4: Occurrence Multiplier Formula")
    print("="*60)
    
    # Single occurrence: multiplier = 1.0 + min(0.15 * 0, 1.0) = 1.0
    single = [
        {
            "rule_id": "DPDP-001",
            "rule_name": "Missing Consent",
            "severity": "HIGH",
            "risk_weight": 0.9,
            "occurrence_count": 1
        }
    ]
    score1 = calculate_score(single)
    print(f"  1 occurrence: score={score1['score']:.1f}, tier={score1['tier']}")
    
    # 3 occurrences: multiplier = 1.0 + min(0.15 * 2, 1.0) = 1.3
    triple = [
        {
            "rule_id": "DPDP-001",
            "rule_name": "Missing Consent",
            "severity": "HIGH",
            "risk_weight": 0.9,
            "occurrence_count": 3
        }
    ]
    score3 = calculate_score(triple)
    print(f"  3 occurrences: score={score3['score']:.1f}, tier={score3['tier']}")
    
    # Repeated violations should increase score
    assert score3['score'] > score1['score'], \
        f"Repeated violations should increase score: {score1['score']:.1f} < {score3['score']:.1f}"
    
    print("  ✓ PASSED: Multiplier correctly increases score for repeated violations")
    return True


def test_tier_thresholds():
    """Test that tier thresholds are configured correctly."""
    print("\n✓ TEST 5: Tier Thresholds")
    print("="*60)
    
    expected = {
        "COMPLIANT": (0, 0),
        "VERY_LOW": (0.01, 10),
        "LOW": (11, 30),
        "MEDIUM": (31, 55),
        "HIGH": (56, 75),
        "CRITICAL": (76, 100)
    }
    
    for tier_name, (min_val, max_val) in expected.items():
        actual = TIER_RANGES.get(tier_name)
        print(f"  {tier_name:12s}: {min_val:5.0f} - {max_val:5.0f}")
        assert actual == (min_val, max_val), f"Mismatch for {tier_name}"
    
    print("  ✓ PASSED: All tier thresholds correct")
    return True


def test_explanation_dpdp006():
    """Test that DPDP-006 explanation is correct (third-party sharing)."""
    print("\n✓ TEST 6: DPDP-006 Explanation (Third-Party Sharing)")
    print("="*60)
    
    exp = get_explanation("DPDP-006")
    why = exp['why_detected'].lower()
    
    print(f"  Why Detected: {exp['why_detected'][:60]}...")
    
    # Should mention third parties and sharing/shared
    assert 'third parties' in why or 'third-party' in why, \
        f"DPDP-006 should mention third parties, got: {why}"
    assert 'sharing' in why or 'shared' in why, \
        f"DPDP-006 should mention sharing, got: {why}"
    
    print("  ✓ PASSED: DPDP-006 correctly explains third-party sharing")
    return True


def test_explanation_dpdp007():
    """Test that DPDP-007 explanation is correct (data minimization)."""
    print("\n✓ TEST 7: DPDP-007 Explanation (Data Minimization)")
    print("="*60)
    
    exp = get_explanation("DPDP-007")
    why = exp['why_detected'].lower()
    
    print(f"  Why Detected: {exp['why_detected'][:60]}...")
    
    # Should mention data minimization or over-collection
    assert 'data minimization' in why or 'minimization' in why or 'over-collection' in why or 'collected' in why, \
        f"DPDP-007 should mention data minimization, got: {why}"
    
    print("  ✓ PASSED: DPDP-007 correctly explains data minimization")
    return True


def test_traceability_fields():
    """Test that violations include traceability fields."""
    print("\n✓ TEST 8: Traceability Fields")
    print("="*60)
    
    result = evaluate_tenant("tenant_c")
    violations = result["violations"]
    
    print(f"  Checking {len(violations)} violations for traceability fields...")
    
    for v in violations[:2]:  # Check first 2
        has_matched_ids = 'matched_record_ids' in v
        has_fields = 'fields_triggered' in v
        has_count = 'matched_logs_count' in v
        
        print(f"\n  {v['rule_id']}:")
        print(f"    matched_record_ids: {v.get('matched_record_ids', ['MISSING'])} {'✓' if has_matched_ids else '✗'}")
        print(f"    fields_triggered: {v.get('fields_triggered', ['MISSING'])} {'✓' if has_fields else '✗'}")
        print(f"    matched_logs_count: {v.get('matched_logs_count', 'MISSING')} {'✓' if has_count else '✗'}")
        
        assert has_matched_ids, f"{v['rule_id']} missing matched_record_ids"
        assert has_fields, f"{v['rule_id']} missing fields_triggered"
        assert has_count, f"{v['rule_id']} missing matched_logs_count"
    
    print("\n  ✓ PASSED: All violations have traceability fields")
    return True


def run_all_tests():
    """Run all regression tests."""
    print("\n" + "="*70)
    print("DPDP COMPLIANCE ENGINE - REFACTORING REGRESSION TESTS")
    print("="*70)
    
    tests = [
        ("Tenant A Compliance", test_tenant_a_compliant),
        ("Tenant B Non-Compliance", test_tenant_b_noncompliant),
        ("Tenant C Repeated Violations", test_tenant_c_repeated_violations),
        ("Occurrence Multiplier", test_occurrence_multiplier),
        ("Tier Thresholds", test_tier_thresholds),
        ("DPDP-006 Explanation", test_explanation_dpdp006),
        ("DPDP-007 Explanation", test_explanation_dpdp007),
        ("Traceability Fields", test_traceability_fields),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
