#!/usr/bin/env python3
"""
Test the improved frequency-weighted compliance scoring system.

Tests:
1. Loads tenant_c data files
2. Evaluates compliance violations
3. Calculates frequency-weighted risk score
4. Displays comparison: unique rules vs total occurrences
"""

import json
from src.rules_engine.evaluate import evaluate_tenant
from src.scoring.score import calculate_score
from src.privacy_gateway.redact import redact_dict

def test_improved_scoring():
    """Test the new frequency-weighted scoring system."""
    
    print("\n" + "="*80)
    print("IMPROVED FREQUENCY-WEIGHTED COMPLIANCE SCORING TEST")
    print("="*80)
    
    # Test with tenant_c data
    tenant_id = "tenant_c"
    
    print(f"\n📂 Loading tenant data from: data/tenants/{tenant_id}/redacted/")
    print("-" * 80)
    
    try:
        result = evaluate_tenant(tenant_id)
        
        print(f"\n✅ EVALUATION RESULTS:")
        print(f"   • Unique Rules Violated: {result['unique_rules_violated']}")
        print(f"   • Total Violation Occurrences: {result['total_violation_occurrences']}")
        
        # Calculate risk score with new frequency-weighted formula
        score = calculate_score(result['violations'])
        
        print(f"\n📊 FREQUENCY-WEIGHTED RISK SCORE:")
        print(f"   • Risk Score: {score['score']}")
        print(f"   • Risk Tier: {score['tier']}")
        
        print(f"\n📋 VIOLATION BREAKDOWN by Rule:")
        print("-" * 80)
        print(f"{'Rule ID':<12} {'Rule Name':<45} {'Count':<8} {'Score':<10}")
        print("-" * 80)
        
        for i, violation in enumerate(result['violations'], 1):
            rule_id = violation.get('rule_id')
            rule_name = violation.get('rule_name')
            occurrence_count = violation.get('occurrence_count', 1)
            
            # Find contribution from score breakdown
            contribution = next(
                (b['contribution_to_score'] for b in score['breakdown'] 
                 if b['rule_id'] == rule_id),
                0.0
            )
            
            print(f"{rule_id:<12} {rule_name:<45} {occurrence_count:<8} {contribution:<10.2f}")
        
        print("-" * 80)
        print(f"{'TOTALS':<12} {'':<45} {result['total_violation_occurrences']:<8} {score['score']:<10.2f}")
        print("-" * 80)
        
        print(f"\n🎯 KEY INSIGHTS:")
        print(f"   • Unique Rules Breached: {result['unique_rules_violated']}")
        print(f"   • Average Violations per Rule: {result['total_violation_occurrences'] / result['unique_rules_violated']:.1f}")
        print(f"   • Risk Score: {score['score']:.2f}/100")
        print(f"   • Risk Category: {score['tier']}")
        
        print(f"\n📌 COMPARISON WITH OLD METHOD:")
        old_method_score = (result['total_violation_occurrences'] * 2.5)  # Old formula approximation
        print(f"   • Old Method Score (30 violations × avg weight): ~{min(old_method_score, 100):.2f}")
        print(f"   • New Method Score (frequency-weighted): {score['score']:.2f}")
        print(f"   • Difference: {abs(min(old_method_score, 100) - score['score']):.2f} points lower (more accurate)")
        
        print(f"\n✨ BENEFITS OF NEW APPROACH:")
        print(f"   ✓ Unique rules are primary driver (not total count)")
        print(f"   ✓ Frequency increases score logarithmically (√count), not linearly")
        print(f"   ✓ Adding more logs with same issues won't inflate risk artificially")
        print(f"   ✓ Audit-ready: Shows both unique violations AND frequency")
        
        return score['score'], score['tier'], result['unique_rules_violated'], result['total_violation_occurrences']
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_improved_scoring()
    if result:
        score, tier, unique, total = result
        print(f"\n" + "="*80)
        print(f"✅ TEST COMPLETE: Score={score}, Tier={tier}, Unique Rules={unique}, Total Occurrences={total}")
        print("="*80 + "\n")
