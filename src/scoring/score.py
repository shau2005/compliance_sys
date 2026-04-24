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
    "VERY_LOW": (0.01, 10),
    "LOW": (11, 30),
    "MEDIUM": (31, 55),
    "HIGH": (56, 75),
    "CRITICAL": (76, 100)
}

# ═══════════════════════════════════════════════════════════
# SECTION 2: CALCULATE RISK SCORE FROM VIOLATIONS (FREQUENCY-WEIGHTED)
# ═══════════════════════════════════════════════════════════

def calculate_score(violations: List[Dict]) -> Dict:
    """
    Calculate risk score from list of violations using corrected occurrence multiplier formula.
    
    REFACTORED FORMULA:
    1. occurrence_multiplier = 1.0 + min(0.15 * (occurrence_count - 1), 1.0)
       - Base 1.0 for single occurrence
       - +0.15 per extra occurrence, capped at +1.0 (max 2.0 total)
       - Ensures repeated violations meaningfully increase score without linear explosion
    
    2. contribution = risk_weight × severity_multiplier × occurrence_multiplier
    
    3. normalized_score = (total_score_raw / max_possible_score) * 100
       - max_possible_score = sum(rule.weight * 2.0 for all rules)
       - Accounts for maximum possible multiplier of 2.0
    
    This ensures:
    - Repeated violations of HIGH/CRITICAL rules significantly increase risk
    - Tenant with 10 violations gets appropriate MEDIUM+ score
    - Repeated issues at threshold rules (e.g., DPDP-013) scale scoring appropriately
    
    Args:
        violations (list): List of violation objects with occurrence_count, risk_weight, severity
    
    Returns:
        dict: Scoring breakdown with corrected frequency weighting
        {
            "score": 45.2,
            "tier": "MEDIUM",
            "unique_rules_violated": 10,
            "total_violation_occurrences": 34,
            "breakdown": [
                {
                    "rule_id": "DPDP-013",
                    "severity": "HIGH",
                    "risk_weight": 0.9,
                    "occurrence_count": 3,
                    "occurrence_multiplier": 1.3,
                    "contribution_to_score": 0.88
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
            "unique_rules_violated": 0,
            "total_violation_occurrences": 0,
            "breakdown": []
        }
    
    # Load all rules to calculate max_possible_score
    from src.config import RULES_FILE
    try:
        with open(RULES_FILE, 'r') as f:
            all_rules = json.load(f)
        # Only count enabled rules
        enabled_rules = [r for r in all_rules if r.get("enabled", True)]
        max_possible_score = sum(r.get("risk_weight", 0.5) * 2.0 for r in enabled_rules)
    except:
        # Fallback if rules file can't be loaded: estimate based on 14 rules at avg weight 0.85
        max_possible_score = 14 * 0.85 * 2.0
    
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
        severity_multiplier = SEVERITY_MULTIPLIERS.get(severity, 0.5)
        
        # REFACTORED FORMULA: occurrence_multiplier = 1.0 + min(0.15 * (count - 1), 1.0)
        # This increases score meaningfully for repeated violations but caps the growth
        occurrence_multiplier = 1.0 + min(0.15 * (occurrence_count - 1), 1.0)
        
        # Final contribution: weight × severity × occurrence multiplier
        contribution = risk_weight * severity_multiplier * occurrence_multiplier
        
        breakdown.append({
            "rule_id": violation.get("rule_id"),
            "severity": severity,
            "risk_weight": risk_weight,
            "occurrence_count": occurrence_count,
            "occurrence_multiplier": round(occurrence_multiplier, 2),
            "contribution_to_score": round(contribution, 2)
        })
        
        total_score += contribution
    
    # Normalize score to 0-100 range using max_possible_score
    # This accounts for maximum multiplier of 2.0 and ensures proper scaling
    normalized_score = (total_score / max_possible_score) * 100
    
    # Cap at 100
    final_score = min(normalized_score, 100)
    
    # Determine tier
    num_unique_rules = len(violations)
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
# SECTION 3: BASIC LOCAL SMOKE TEST
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("DPDP RISK SCORER TEST")
    print("=" * 70)

    sample_violations = [
        {
            "rule_id": "DPDP-001",
            "severity": "HIGH",
            "risk_weight": 0.9,
            "occurrence_count": 2,
        },
        {
            "rule_id": "DPDP-008",
            "severity": "CRITICAL",
            "risk_weight": 0.95,
            "occurrence_count": 1,
        },
    ]

    score = calculate_score(sample_violations)
    print(f"Score: {score['score']}")
    print(f"Tier: {score['tier']}")
    print(f"Unique rules: {score['unique_rules_violated']}")
    print(f"Total occurrences: {score['total_violation_occurrences']}")
    print("\n" + "=" * 70)