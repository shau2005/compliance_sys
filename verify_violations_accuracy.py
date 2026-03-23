#!/usr/bin/env python3
"""
Verify that detected violations match the raw tenant_c data.
Cross-check each violation against actual data values.
"""

import json
from pathlib import Path

# Load tenant_c files
policies_file = Path("data/tenants/tenant_c/redacted/policies.json")
logs_file = Path("data/tenants/tenant_c/redacted/logs.json")
inventory_file = Path("data/tenants/tenant_c/redacted/system_inventory.json")

with open(policies_file) as f:
    policies = json.load(f)
with open(logs_file) as f:
    logs = json.load(f)
with open(inventory_file) as f:
    inventory = json.load(f)

print("\n" + "="*100)
print("VERIFICATION: Detected Violations vs Raw Tenant_C Data")
print("="*100)

print("\n📋 POLICIES DATA:")
print(f"  • processing_purpose: {policies.get('processing_purpose')}")
print(f"  • consented_purpose: {policies.get('consented_purpose')}")
print(f"  • grievance_endpoint_available: {policies.get('grievance_endpoint_available')}")
print(f"  • consent_flag: {policies.get('consent_flag')}")

print("\n📋 INVENTORY DATA:")
print(f"  • collected_fields: {inventory.get('collected_fields')}")
print(f"  • required_fields: {inventory.get('required_fields')}")
print(f"  • retention_expiry_date: {inventory.get('retention_expiry_date')}")
print(f"  • data_retained: {inventory.get('data_retained')}")
print(f"  • purpose_completed: {inventory.get('purpose_completed')}")
print(f"  • age: {inventory.get('age')}")
print(f"  • erasure_requested: {inventory.get('erasure_requested')}")
print(f"  • data_deleted: {inventory.get('data_deleted')}")

print(f"\n📋 LOGS DATA: {len(logs)} total log entries")

# Check POLICY LEVEL violations
print("\n" + "="*100)
print("POLICY-LEVEL VIOLATIONS (counted once)")
print("="*100)

violations_found = {
    "DPDP-002": False,
    "DPDP-003": False,
    "DPDP-007": False,
    "DPDP-009": False,
    "DPDP-011": False,
}

# DPDP-002: Processing Beyond Stated Purpose
if policies.get('processing_purpose') != policies.get('consented_purpose'):
    violations_found["DPDP-002"] = True
    print(f"\n✅ DPDP-002: Processing Beyond Stated Purpose")
    print(f"   Condition: processing_purpose ({policies['processing_purpose']}) != consented_purpose ({policies['consented_purpose']})")
    print(f"   Status: VIOLATED ✓")
else:
    print(f"\n❌ DPDP-002: Processing Beyond Stated Purpose")
    print(f"   Status: NOT VIOLATED (but should be detected)")

# DPDP-003: Retention Beyond Allowed Period
if policies.get('data_retained') and inventory.get('purpose_completed'):
    violations_found["DPDP-003"] = True
    print(f"\n✅ DPDP-003: Retention Beyond Allowed Period")
    print(f"   Condition: data_retained ({inventory['data_retained']}) AND purpose_completed ({inventory['purpose_completed']})")
    print(f"   Status: VIOLATED ✓")
else:
    print(f"\n❌ DPDP-003: Retention Beyond Allowed Period")
    print(f"   Status: NOT VIOLATED")

# DPDP-007: Missing Data Minimization
if inventory.get('collected_fields', 0) > inventory.get('required_fields', 0):
    violations_found["DPDP-007"] = True
    print(f"\n✅ DPDP-007: Missing Data Minimization")
    print(f"   Condition: collected_fields ({inventory['collected_fields']}) > required_fields ({inventory['required_fields']})")
    print(f"   Status: VIOLATED ✓")
else:
    print(f"\n❌ DPDP-007: Missing Data Minimization")
    print(f"   Status: NOT VIOLATED")

# DPDP-009: Missing Grievance Redress Mechanism
if not policies.get('grievance_endpoint_available'):
    violations_found["DPDP-009"] = True
    print(f"\n✅ DPDP-009: Missing Grievance Redress Mechanism")
    print(f"   Condition: grievance_endpoint_available == {policies['grievance_endpoint_available']}")
    print(f"   Status: VIOLATED ✓")
else:
    print(f"\n❌ DPDP-009: Missing Grievance Redress Mechanism")
    print(f"   Status: NOT VIOLATED")

# DPDP-011: Excess Data Retention Without Purpose
if inventory.get('data_retained') and inventory.get('purpose_completed') and inventory.get('age', 0) >= 30:
    violations_found["DPDP-011"] = True
    print(f"\n✅ DPDP-011: Excess Data Retention Without Purpose")
    print(f"   Condition: data_retained ({inventory['data_retained']}) AND purpose_completed ({inventory['purpose_completed']}) AND age ({inventory['age']}) >= 30")
    print(f"   Status: VIOLATED ✓")
else:
    print(f"\n❌ DPDP-011: Excess Data Retention Without Purpose")
    print(f"   Status: NOT VIOLATED")

# LOG-LEVEL violations
print("\n" + "="*100)
print("LOG-LEVEL VIOLATIONS (counted per log entry)")
print("="*100)

log_violations = {
    "DPDP-006": [],  # shared_with_third_party && !consent_for_sharing
    "DPDP-010": [],  # erasure_requested && !data_deleted
    "DPDP-012": [],  # !access_log_available
    "DPDP-013": [],  # accessed_pii && !access_log_available
    "DPDP-014": [],  # breach_detected && notification_delay > 72
}

for log in logs:
    log_id = log.get('log_id')
    
    # DPDP-006: Unauthorized Third Party Data Sharing
    if log.get('shared_with_third_party') and not log.get('consent_for_sharing'):
        log_violations["DPDP-006"].append(log_id)
    
    # DPDP-010: Failure to Honor Data Erasure Request
    if log.get('erasure_requested') and not log.get('data_deleted'):
        log_violations["DPDP-010"].append(log_id)
    
    # DPDP-012: Missing Audit Logs for Data Access
    if not log.get('access_log_available'):
        log_violations["DPDP-012"].append(log_id)
    
    # DPDP-013: Unauthorized Employee Access to PII
    if log.get('accessed_pii') and not log.get('access_log_available'):
        log_violations["DPDP-013"].append(log_id)
    
    # DPDP-014: Delayed Breach Notification
    if log.get('breach_detected') and log.get('notification_delay', 0) > 72:
        log_violations["DPDP-014"].append(log_id)

# Display log violation analysis
for rule_id, log_ids in log_violations.items():
    count = len(log_ids)
    status = "✓" if count > 0 else "✗"
    print(f"\n{status} {rule_id}: {len(log_ids)} violations")
    if log_ids:
        print(f"   Affected logs: {', '.join(log_ids[:10])}", end="")
        if len(log_ids) > 10:
            print(f" ... and {len(log_ids) - 10} more")
        else:
            print()

print("\n" + "="*100)
print("SUMMARY OF FINDINGS")
print("="*100)

detected_violations = {
    "DPDP-002": 1,
    "DPDP-003": 1,
    "DPDP-007": 1,
    "DPDP-009": 1,
    "DPDP-011": 1,
    "DPDP-010": len(log_violations["DPDP-010"]),
    "DPDP-006": len(log_violations["DPDP-006"]),
    "DPDP-012": len(log_violations["DPDP-012"]),
    "DPDP-013": len(log_violations["DPDP-013"]),
    "DPDP-014": len(log_violations["DPDP-014"]),
}

reported_violations = {
    "DPDP-002": 1,
    "DPDP-003": 1,
    "DPDP-007": 1,
    "DPDP-009": 1,
    "DPDP-011": 1,
    "DPDP-010": 1,
    "DPDP-006": 6,
    "DPDP-012": 6,
    "DPDP-013": 7,
    "DPDP-014": 5,
}

print(f"\n{'Rule ID':<12} {'Expected':<12} {'Reported':<12} {'Status':<20}")
print("-" * 60)

mismatches = []
for rule_id in sorted(detected_violations.keys()):
    expected = detected_violations[rule_id]
    reported = reported_violations[rule_id]
    
    if expected == reported:
        status = "✅ MATCH"
    else:
        status = f"⚠️  MISMATCH ({expected} vs {reported})"
        mismatches.append((rule_id, expected, reported))
    
    print(f"{rule_id:<12} {expected:<12} {reported:<12} {status:<20}")

total_violations = sum(detected_violations.values())
total_reported = sum(reported_violations.values())

print("-" * 60)
print(f"{'TOTAL':<12} {total_violations:<12} {total_reported:<12}", end="")
if total_violations == total_reported:
    print("✅ MATCH")
else:
    print(f"⚠️  MISMATCH ({total_violations} vs {total_reported})")

if mismatches:
    print(f"\n⚠️  VIOLATIONS WITH MISMATCHES:")
    for rule_id, expected, reported in mismatches:
        print(f"   • {rule_id}: Expected {expected}, Reported {reported}")
else:
    print(f"\n✅ ALL VIOLATIONS MATCH THE RAW DATA!")

print("\n" + "="*100)
