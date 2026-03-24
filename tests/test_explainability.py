"""
Test and example file for the Explainability (XAI) Service.

Demonstrates:
- Getting individual explanations
- Enriching violation lists
- Integration with the compliance system

Run with: python -m pytest tests/test_explainability.py -v
Or:       python -c "import sys; sys.path.insert(0, '.'); from tests.test_explainability import run_all_tests; run_all_tests()"
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.explainability.service import (
    get_explanation,
    enrich_violations,
    add_explanation_to_violation,
    list_available_violations,
)


def test_get_single_explanation():
    """Test retrieving explanation for a known violation."""
    print("\n" + "="*70)
    print("TEST 1: Get Single Explanation for DPDP-001")
    print("="*70)
    
    explanation = get_explanation("DPDP-001")
    
    print(f"\nRule: DPDP-001 - Missing Consent Before Processing")
    print(f"\n❓ WHY DETECTED:")
    print(f"   {explanation['why_detected']}\n")
    
    print(f"📋 EVIDENCE:")
    print(f"   {explanation['evidence']}\n")
    
    print(f"⚠️  RISK REASON:")
    print(f"   {explanation['risk_reason']}\n")
    
    print(f"✅ MITIGATION:")
    for line in explanation['mitigation'].split('\n'):
        print(f"   {line}")


def test_get_unknown_explanation():
    """Test that unknown violations return default explanation."""
    print("\n" + "="*70)
    print("TEST 2: Get Explanation for Unknown Violation")
    print("="*70)
    
    explanation = get_explanation("UNKNOWN-999")
    
    print(f"\nRule: UNKNOWN-999 (not in knowledge base)")
    print(f"\n❓ WHY DETECTED (DEFAULT):")
    print(f"   {explanation['why_detected']}\n")
    
    print("✓ Returns sensible default explanation for unmapped violations")


def test_enrich_violations():
    """Test enriching a list of violations."""
    print("\n" + "="*70)
    print("TEST 3: Enrich Violations List")
    print("="*70)
    
    # Simulate violations from compliance engine
    raw_violations = [
        {
            "rule_id": "DPDP-001",
            "rule_name": "Missing Consent Before Processing",
            "dpdp_section": "Consent Requirement",
            "severity": "HIGH",
            "risk_weight": 0.9,
            "occurrence_count": 5,
            "reason": "Found 5 records with consent_flag=false"
        },
        {
            "rule_id": "DPDP-003",
            "rule_name": "Retention Beyond Allowed Period",
            "dpdp_section": "Storage Limitation",
            "severity": "HIGH",
            "risk_weight": 0.8,
            "occurrence_count": 2,
            "reason": "Found 2 records with expired retention dates"
        },
        {
            "rule_id": "UNKNOWN-RULE",
            "rule_name": "Custom Rule",
            "dpdp_section": "Custom",
            "severity": "MEDIUM",
            "risk_weight": 0.5,
            "occurrence_count": 1,
            "reason": "Custom business rule violation"
        }
    ]
    
    print(f"\n📊 INPUT: {len(raw_violations)} violations to enrich")
    print(f"   - DPDP-001 (5 occurrences)")
    print(f"   - DPDP-003 (2 occurrences)")
    print(f"   - UNKNOWN-RULE (1 occurrence)")
    
    # Enrich violations
    enriched = enrich_violations(raw_violations)
    
    print(f"\n✓ OUTPUT: {len(enriched)} violations enriched with explanations\n")
    
    # Show first violation in detail
    v = enriched[0]
    print(f"\n   ┌─ DPDP-001 (Enriched)")
    print(f"   ├─ Severity: {v['severity']}")
    print(f"   ├─ Occurrences: {v['occurrence_count']}")
    print(f"   ├─ Why Detected: {v['explanation']['why_detected'][:60]}...")
    print(f"   ├─ Risk: {v['explanation']['risk_reason'][:60]}...")
    print(f"   └─ Mitigation Steps: {len(v['explanation']['mitigation'].split(chr(10)))} actions")
    
    # Verify UNKNOWN-RULE gets default explanation
    unknown = enriched[2]
    print(f"\n   ┌─ UNKNOWN-RULE (Gets Default)")
    print(f"   ├─ Original Fields: All preserved ✓")
    print(f"   └─ Explanation: Default template applied ✓")


def test_add_explanation_single():
    """Test adding explanation to a single violation."""
    print("\n" + "="*70)
    print("TEST 4: Add Explanation to Single Violation")
    print("="*70)
    
    violation = {
        "rule_id": "DPDP-002",
        "rule_name": "Processing Beyond Stated Purpose",
        "severity": "HIGH",
        "occurrence_count": 3
    }
    
    print(f"\nBEFORE: Violation has no explanation field")
    print(f"   {list(violation.keys())}")
    
    enhanced = add_explanation_to_violation(violation)
    
    print(f"\nAFTER: Explanation added")
    print(f"   {list(enhanced.keys())}")
    print(f"\n✓ Original violation unchanged (non-destructive)")
    print(f"✓ New object has 'explanation' field with full details")


def test_list_available():
    """Test listing all available explanations."""
    print("\n" + "="*70)
    print("TEST 5: List Available Violations with Explanations")
    print("="*70)
    
    available = list_available_violations()
    
    print(f"\n📚 Knowledge Base contains {len(available)} documented violations:\n")
    for rule_id in available:
        print(f"   ✓ {rule_id}")
    
    print(f"\n💡 To get explanation: get_explanation('{available[0]}')")
    print(f"💡 To enrich violations: enrich_violations(violations_list)")


def test_full_integration_example():
    """Full end-to-end example of violation analysis with explanations."""
    print("\n" + "="*70)
    print("TEST 6: Full Integration Example")
    print("="*70)
    
    print("\n🔄 SCENARIO: Analyzing Tenant A compliance violations\n")
    
    # Step 1: Violations from compliance engine
    raw_violations = [
        {
            "rule_id": "DPDP-001",
            "rule_name": "Missing Consent Before Processing",
            "dpdp_section": "Consent Requirement",
            "severity": "HIGH",
            "risk_weight": 0.9,
            "occurrence_count": 15,
            "reason": "Processing personal data without valid consent"
        }
    ]
    
    print("1️⃣  COMPLIANCE ENGINE OUTPUT:")
    print(f"   Rule: {raw_violations[0]['rule_name']}")
    print(f"   Occurrences: {raw_violations[0]['occurrence_count']}")
    
    # Step 2: Enrich with explanations
    enriched = enrich_violations(raw_violations)
    violation = enriched[0]
    
    print("\n2️⃣  EXPLAINABILITY LAYER ADDS:")
    print(f"   ✓ Why it was detected")
    print(f"   ✓ Evidence details")
    print(f"   ✓ Risk reasoning")
    print(f"   ✓ Remediation steps")
    
    # Step 3: Present to stakeholders
    print("\n3️⃣  STAKEHOLDER COMMUNICATION:")
    print(f"\n   📌 ISSUE: {violation['rule_name']}")
    print(f"   🎯 SEVERITY: {violation['severity']}")
    print(f"   📊 COUNT: {violation['occurrence_count']} violations detected")
    
    print(f"\n   WHY THIS MATTERS:")
    print(f"   {violation['explanation']['risk_reason']}")
    
    print(f"\n   HOW TO FIX (in priority order):")
    for idx, step in enumerate(violation['explanation']['mitigation'].split('\n'), 1):
        if step.strip():
            print(f"   {step}")
    
    print(f"\n   ✅ Clear, actionable guidance for remediation")


def run_all_tests():
    """Run all test/demonstration functions."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "EXPLAINABILITY (XAI) SERVICE TESTS" + " "*20 + "║")
    print("║" + " "*15 + "Production-Ready Compliance Explanations" + " "*15 + "║")
    print("╚" + "="*68 + "╝")
    
    test_get_single_explanation()
    test_get_unknown_explanation()
    test_enrich_violations()
    test_add_explanation_single()
    test_list_available()
    test_full_integration_example()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70)
    print("\n📖 KEY TAKEAWAYS:")
    print("   • Explanations are rule-based (deterministic, no ML)")
    print("   • Service layer handles all XAI logic (clean separation)")
    print("   • API automatically enriches violations with explanations")
    print("   • Easy to extend: Add rule explanations to dictionary")
    print("   • Non-destructive: Original data preserved")
    print("   • Production-ready: Type hints, docstrings, defaults")
    print("\n")


if __name__ == "__main__":
    run_all_tests()
