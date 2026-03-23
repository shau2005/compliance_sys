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
# SECTION 2: CALCULATE RISK SCORE FROM VIOLATIONS (FREQUENCY-WEIGHTED)
# ═══════════════════════════════════════════════════════════

def calculate_score(violations: List[Dict]) -> Dict:
    """
    Calculate risk score from list of violations using frequency-weighted formula.
    
    IMPROVED FORMULA:
    Risk Score = Σ(Risk Weight × Severity Multiplier × √Occurrence Count)
    
    This ensures:
    - Unique rule violations are the primary driver
    - Multiple occurrences increase score logarithmically (not linearly)
    - Adding more logs with same issues doesn't inflate risk artificially
    
    Args:
        violations (list): List of violation objects with occurrence_count
    
    Returns:
        dict: Scoring breakdown with frequency weighting
        {
            "score": 25.5,
            "tier": "MEDIUM",
            "unique_rules_violated": 10,
            "total_violation_occurrences": 30,
            "breakdown": [
                {
                    "rule_id": "DPDP-013",
                    "severity": "HIGH",
                    "risk_weight": 0.9,
                    "occurrence_count": 7,
                    "contribution_to_score": 2.38
                },
                ...
            ]
        }
    """
    import math
    
    # If no violations, score is 0 (COMPLIANT)
    if not violations or len(violations) == 0:
        return {
            "score": 0,
            "tier": "COMPLIANT",
            "unique_rules_violated": 0,
            "total_violation_occurrences": 0,
            "breakdown": []
        }
    
    # Calculate score for each unique violation
    breakdown = []
    total_score = 0
    total_occurrences = 0
    
    for violation in violations:
        severity = violation.get("severity", "MEDIUM")
        risk_weight = violation.get("risk_weight", 0.5)
        occurrence_count = violation.get("occurrence_count", 1)
        
        # Track total occurrences
        total_occurrences += occurrence_count
        
        # Get multiplier for this severity
        multiplier = SEVERITY_MULTIPLIERS.get(severity, 0.5)
        
        # NEW FORMULA: risk_weight × multiplier × √occurrence_count
        # This makes frequency impact logarithmic instead of linear
        frequency_factor = math.sqrt(occurrence_count)
        contribution = risk_weight * multiplier * frequency_factor
        
        breakdown.append({
            "rule_id": violation.get("rule_id"),
            "severity": severity,
            "risk_weight": risk_weight,
            "occurrence_count": occurrence_count,
            "contribution_to_score": round(contribution, 2)
        })
        
        total_score += contribution
    
    # Normalize score to 0-100 range
    # Divide by number of unique rules to get average impact per rule
    num_unique_rules = len(violations)
    avg_score = (total_score / num_unique_rules) * 10  # Scale to reasonable range
    
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
        "unique_rules_violated": num_unique_rules,
        "total_violation_occurrences": total_occurrences,
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