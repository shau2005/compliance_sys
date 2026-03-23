#!/usr/bin/env python3
"""
Verify violations in the API report
"""

import json
from pathlib import Path
from collections import Counter

report_file = Path(r"C:\Users\Shravani Bhosale\Downloads\uploaded_tenant_compliance_report (1).json")

with open(report_file) as f:
    report = json.load(f)

print("\n" + "="*80)
print("✅ VIOLATION VERIFICATION REPORT")
print("="*80)

print(f"\n📊 REPORT SUMMARY:")
print(f"   Tenant ID: {report['tenant_id']}")
print(f"   Violation Count (Reported): {report['violation_count']}")
print(f"   Risk Score: {report['risk_score']}")
print(f"   Risk Tier: {report['risk_tier']}")
print(f"   Status: {report['status']}")

# Count violations by rule_id
violations = report['violations']
rule_counts = Counter(v['rule_id'] for v in violations)
unique_rules = len(rule_counts)

print(f"\n📋 VIOLATIONS BREAKDOWN:")
print(f"   Total violations in array: {len(violations)}")
print(f"   Unique rule violations: {unique_rules}")

print(f"\n   By Rule:")
for rule_id in sorted(rule_counts.keys()):
    count = rule_counts[rule_id]
    rule_name = next((v['rule_name'] for v in violations if v['rule_id'] == rule_id), "Unknown")
    severity = next((v['severity'] for v in violations if v['rule_id'] == rule_id), "Unknown")
    print(f"      {rule_id}: {count:2d} × {rule_name:40s} [{severity}]")

# Verify counts match
total_in_array = len(violations)
reported_count = report['violation_count']

print(f"\n🔍 VERIFICATION:")
if total_in_array == reported_count:
    print(f"   ✅ Array count matches reported count: {total_in_array}")
else:
    print(f"   ⚠️  MISMATCH: Array has {total_in_array}, report says {reported_count}")

# Check for duplicates (same rule_id twice in a row might indicate wrong deduplication)
print(f"\n📌 DUPLICATE CHECK:")
has_consecutive_dupes = False
for i in range(len(violations) - 1):
    if violations[i]['rule_id'] == violations[i+1]['rule_id']:
        has_consecutive_dupes = True
        print(f"   ⚠️  {violations[i]['rule_id']} appears consecutively at positions {i} and {i+1}")

if not has_consecutive_dupes:
    print(f"   ✅ No consecutive duplicates found")

# Check if violations make sense for tenant_c
print(f"\n📑 EXPECTED vs ACTUAL:")
expected_violations = {
    "DPDP-002": 1,  # Policy: analytics != loan_processing
    "DPDP-003": 1,  # Policy: retention_expiry_date in past
    "DPDP-006": 6,  # Logs: shared without consent (6 occurrences)
    "DPDP-007": 1,  # Policy: 4 collected > 2 required
    "DPDP-009": 1,  # Policy: no grievance endpoint
    "DPDP-010": 5,  # Logs: erasure not honored (should be 5, not 1)
    "DPDP-011": 1,  # Policy: retained=true + purpose_completed=true
    "DPDP-012": 6,  # Logs: missing audit logs (6 occurrences)
    "DPDP-013": 7,  # Logs: unauthorized employee access (7 occurrences)
    "DPDP-014": 5,  # Logs: delayed breach notification (5 occurrences)
}

print(f"   {'Rule':<10} {'Expected':<10} {'Actual':<10} {'Status':<10}")
print(f"   {'-'*40}")

issues = []
for rule_id in sorted(expected_violations.keys()):
    expected = expected_violations[rule_id]
    actual = rule_counts.get(rule_id, 0)
    status = "✅ OK" if actual == expected else "⚠️  ISSUE"
    if actual != expected:
        issues.append(f"{rule_id}: got {actual}, expected {expected}")
    print(f"   {rule_id:<10} {expected:<10} {actual:<10} {status:<10}")

if issues:
    print(f"\n🚨 ISSUES FOUND:")
    for issue in issues:
        print(f"   - {issue}")
else:
    print(f"\n✅ ALL VIOLATIONS MATCH EXPECTED VALUES!")

print("\n" + "="*80 + "\n")
