# src/scoring/score.py

import json
from typing import List, Dict

# ═══════════════════════════════════════════════════════════
# SECTION 1: SEVERITY MULTIPLIERS
# ═══════════════════════════════════════════════════════════

SEVERITY_MULTIPLIERS = {
    "CRITICAL": 1.0,
    "HIGH": 0.75,
    "MEDIUM": 0.5,
    "LOW": 0.25
}

TIER_RANGES = {
    "COMPLIANT": (0, 0),
    "LOW": (0.01, 24),
    "MEDIUM": (25, 49),
    "HIGH": (50, 74),
    "CRITICAL": (75, 100)
}

# ═══════════════════════════════════════════════════════════
# SECTION 2: CALCULATE RISK SCORE FROM VIOLATIONS
# ═══════════════════════════════════════════════════════════

def calculate_score(violations: List[Dict]) -> Dict:
    """
    Calculate risk score from list of violations.
    
    Args:
        violations (list): List of violation objects from evaluate_record()
    
    Returns:
        dict: Scoring breakdown
        {
            "score": 78.5,
            "tier": "CRITICAL",
            "violation_count": 11,
            "breakdown": [
                {
                    "rule_id": "DPDP-001",
                    "severity": "HIGH",
                    "risk_weight": 0.9,
                    "contribution": 67.5
                },
                ...
            ]
        }
    """
    
    # If no violations, score is 0 (COMPLIANT)
    if not violations or len(violations) == 0:
        return {
            "score": 0,
            "tier": "COMPLIANT",
            "violation_count": 0,
            "breakdown": []
        }
    
    # Calculate score for each violation
    breakdown = []
    total_score = 0
    
    for violation in violations:
        severity = violation.get("severity", "MEDIUM")
        risk_weight = violation.get("risk_weight", 0.5)
        
        # Get multiplier for this severity
        multiplier = SEVERITY_MULTIPLIERS.get(severity, 0.5)
        
        # Calculate contribution: risk_weight × multiplier × 100
        contribution = risk_weight * multiplier * 100
        
        breakdown.append({
            "rule_id": violation.get("rule_id"),
            "severity": severity,
            "risk_weight": risk_weight,
            "contribution": round(contribution, 2)
        })
        
        total_score += contribution
    
    # Calculate average score
    avg_score = total_score / len(violations)
    
    # Cap at 100
    final_score = min(avg_score, 100)
    
    # Determine tier
    tier = "COMPLIANT"
    for tier_name, (min_val, max_val) in TIER_RANGES.items():
        if min_val <= final_score <= max_val:
            tier = tier_name
            break
    
    return {
        "score": round(final_score, 2),
        "tier": tier,
        "violation_count": len(violations),
        "breakdown": breakdown
    }

# ═══════════════════════════════════════════════════════════
# SECTION 3: TEST WITH VIOLATIONS FROM EVALUATOR
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    from src.rules_engine.evaluate import evaluate_tenant, evaluate_record, load_rules
    
    print("\n" + "="*70)
    print("DPDP RISK SCORER TEST")
    print("="*70)
    
    # Test 1: Score tenant_a (0 violations → 0 score, COMPLIANT)
    print("\n📊 SCORING TENANT_A (Compliant Company)...")
    result_a = evaluate_tenant("tenant_a")
    violations_a = result_a["violations"]
    
    score_a = calculate_score(violations_a)
    print(f"   Violations: {score_a['violation_count']}")
    print(f"   Risk Score: {score_a['score']}/100")
    print(f"   Risk Tier: {score_a['tier']} ✓")
    
    # Test 2: Score tenant_b (13 violations → ~67+ score, HIGH/CRITICAL)
    print("\n📊 SCORING TENANT_B (Non-Compliant Company)...")
    result_b = evaluate_tenant("tenant_b")
    violations_b = result_b["violations"]
    
    score_b = calculate_score(violations_b)
    print(f"   Violations: {score_b['violation_count']}")
    print(f"   Risk Score: {score_b['score']}/100")
    print(f"   Risk Tier: {score_b['tier']} ⚠️")
    
    print("\n   Breakdown by rule:")
    for item in score_b['breakdown'][:5]:  # Show first 5
        print(f"     {item['rule_id']} ({item['severity']}, weight={item['risk_weight']}) → {item['contribution']} points")
    if len(score_b['breakdown']) > 5:
        print(f"     ... and {len(score_b['breakdown']) - 5} more violations")
    
    # Test 3: Hardcoded test with single violation
    print("\n📊 TEST CASE: Single HIGH Severity Violation")
    test_violation = {
        "rule_id": "DPDP-001",
        "rule_name": "Missing Consent",
        "severity": "HIGH",
        "risk_weight": 0.9
    }
    score_test = calculate_score([test_violation])
    print(f"   Risk Score: {score_test['score']}/100 (Expected: 67.5)")
    print(f"   Risk Tier: {score_test['tier']} (Expected: HIGH)")
    
    # Test 4: Hardcoded test with single CRITICAL violation
    print("\n📊 TEST CASE: Single CRITICAL Severity Violation")
    test_violation_critical = {
        "rule_id": "DPDP-008",
        "rule_name": "Unencrypted PII",
        "severity": "CRITICAL",
        "risk_weight": 0.95
    }
    score_test_critical = calculate_score([test_violation_critical])
    print(f"   Risk Score: {score_test_critical['score']}/100 (Expected: 95.0)")
    print(f"   Risk Tier: {score_test_critical['tier']} (Expected: CRITICAL)")
    
    print("\n" + "="*70)