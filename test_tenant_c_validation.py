"""
Test Tenant C against DPDP Rules to verify violation accuracy
"""
import json
from src.rules_engine.evaluate import load_rules, evaluate_record

# Tenant C data
tenant_c_policies = {
    "tenant_id": "tenant_c",
    "company_name": "TrustPay Solutions",
    "consent_flag": True,
    "notice_provided": True,
    "processing_purpose": "analytics",
    "consented_purpose": "loan_processing",
    "pii_encrypted": True,
    "grievance_endpoint_available": False
}

tenant_c_inventory = {
    "tenant_id": "tenant_c",
    "component_id": "COMP-001",
    "name": "User Database",
    "data_collected": ["email", "phone", "location", "credit_score"],
    "collected_fields": 4,
    "required_fields": 2,
    "storage": "encrypted_db",
    "pii_encrypted": True,
    "access_control_enabled": True,
    "audit_logging_enabled": True,
    "retention_expiry_date": "2024-01-01",
    "data_retained": True,
    "purpose_completed": True,
    "erasure_requested": False,
    "data_deleted": False,
    "age": 30,
    "guardian_consent": True
}

# Some example log entries
tenant_c_logs = [
    {
        "log_id": "LOG-004",
        "user": "intern1@trustpay.com",
        "employee_role": "intern",
        "accessed_pii": True,
        "access_log_available": True,
    },
    {
        "log_id": "LOG-006",
        "user": "admin2@trustpay.com",
        "employee_role": "admin",
        "accessed_pii": True,
        "access_log_available": True,
        "shared_with_third_party": True,
        "consent_for_sharing": False,
    },
    {
        "log_id": "LOG-007",
        "user": "analyst4@trustpay.com",
        "employee_role": "analyst",
        "accessed_pii": True,
        "access_log_available": True,
        "breach_detected": True,
        "notification_delay": 80,
    },
    {
        "log_id": "LOG-008",
        "user": "analyst5@trustpay.com",
        "employee_role": "analyst",
        "accessed_pii": True,
        "access_log_available": True,
        "erasure_requested": True,
        "data_deleted": False,
    },
]

print("\n" + "="*80)
print("TENANT C VIOLATION VERIFICATION AGAINST DPDP CLAUSES")
print("="*80)

# Merge base record
base_record = {**tenant_c_policies, **tenant_c_inventory}

print("\n📋 BASE RECORD DATA:")
print("-" * 80)
print(f"consent_flag: {base_record.get('consent_flag')}")
print(f"notice_provided: {base_record.get('notice_provided')}")
print(f"processing_purpose: {base_record.get('processing_purpose')}")
print(f"consented_purpose: {base_record.get('consented_purpose')}")
print(f"pii_encrypted: {base_record.get('pii_encrypted')}")
print(f"grievance_endpoint_available: {base_record.get('grievance_endpoint_available')}")
print(f"collected_fields: {base_record.get('collected_fields')}")
print(f"required_fields: {base_record.get('required_fields')}")
print(f"retention_expiry_date: {base_record.get('retention_expiry_date')}")
print(f"data_retained: {base_record.get('data_retained')}")
print(f"purpose_completed: {base_record.get('purpose_completed')}")
print(f"age: {base_record.get('age')}")
print(f"guardian_consent: {base_record.get('guardian_consent')}")

# Load rules
rules = load_rules()

# Evaluate base record
print("\n🔍 EVALUATING BASE RECORD (Policies + Inventory):")
print("-" * 80)
violations = evaluate_record(base_record, rules)

print(f"\nViolations found in base record: {len(violations)}\n")

violation_summary = {}
for v in violations:
    rule_id = v.get("rule_id")
    rule_name = v.get("rule_name")
    severity = v.get("severity")
    violation_summary[rule_id] = {
        "name": rule_name,
        "severity": severity
    }
    print(f"✗ {rule_id}: {rule_name} ({severity})")

print("\n" + "="*80)
print("DETAILED VIOLATION ANALYSIS")
print("="*80)

# DPDP-001 Analysis
print("\n🔴 DPDP-001 (Missing Consent Before Processing)")
print("-" * 80)
print("Expected condition: consent_flag == false")
print(f"Actual data: consent_flag = {base_record.get('consent_flag')}")
if "DPDP-001" in violation_summary:
    print("⚠️  VIOLATION REPORTED - BUT IS IT CORRECT?")
    print("❌ FALSE POSITIVE: consent_flag is TRUE (no violation)")
else:
    print("✓ CORRECT: No violation reported")

# DPDP-002 Analysis
print("\n🔴 DPDP-002 (Processing Beyond Stated Purpose)")
print("-" * 80)
print("Expected condition: processing_purpose != consented_purpose")
print(f"Actual data: processing_purpose = '{base_record.get('processing_purpose')}'")
print(f"Actual data: consented_purpose = '{base_record.get('consented_purpose')}'")
if "DPDP-002" in violation_summary:
    print("✓ CORRECT: Violation reported - purposes DO NOT MATCH")
else:
    print("❌ FALSE NEGATIVE: Purposes don't match but no violation reported")

# DPDP-003 Analysis
print("\n🔴 DPDP-003 (Retention Beyond Allowed Period)")
print("-" * 80)
print("Expected condition: retention_expiry_date < today (2026-02-24)")
print(f"Actual data: retention_expiry_date = '{base_record.get('retention_expiry_date')}'")
from datetime import datetime
retention_date = datetime.strptime(base_record.get('retention_expiry_date'), "%Y-%m-%d")
today = datetime.now()
print(f"Date comparison: {retention_date.date()} < {today.date()} = {retention_date < today}")
if "DPDP-003" in violation_summary:
    print("✓ CORRECT: Violation reported - data retention period EXPIRED")
else:
    print("❌ FALSE NEGATIVE: Retention period expired but no violation reported")

# DPDP-004 Analysis
print("\n🟠 DPDP-004 (Missing Notice to Data Principal)")
print("-" * 80)
print("Expected condition: notice_provided == false")
print(f"Actual data: notice_provided = {base_record.get('notice_provided')}")
if "DPDP-004" in violation_summary:
    print("⚠️  VIOLATION REPORTED - BUT IS IT CORRECT?")
    print("❌ FALSE POSITIVE: notice_provided is TRUE (no violation)")
else:
    print("✓ CORRECT: No violation reported")

# DPDP-005 Analysis
print("\n🚨 DPDP-005 (Children Data Without Guardian Consent)")
print("-" * 80)
print("Expected condition: age < 18 AND guardian_consent == false")
print(f"Actual data: age = {base_record.get('age')}")
print(f"Actual data: guardian_consent = {base_record.get('guardian_consent')}")
age_check = base_record.get('age', 0) < 18
guardian_check = base_record.get('guardian_consent') == False
print(f"Condition evaluation: ({age_check}) AND ({guardian_check}) = {age_check and guardian_check}")
if "DPDP-005" in violation_summary:
    print("⚠️  VIOLATION REPORTED - BUT IS IT CORRECT?")
    print("❌ FALSE POSITIVE: Subject is adult with guardian consent (no violation)")
else:
    print("✓ CORRECT: No violation reported")

# DPDP-007 Analysis
print("\n🟠 DPDP-007 (Missing Data Minimization)")
print("-" * 80)
print("Expected condition: collected_fields > required_fields")
print(f"Actual data: collected_fields = {base_record.get('collected_fields')}")
print(f"Actual data: required_fields = {base_record.get('required_fields')}")
print(f"Condition evaluation: {base_record.get('collected_fields')} > {base_record.get('required_fields')} = {base_record.get('collected_fields', 0) > base_record.get('required_fields', 0)}")
if "DPDP-007" in violation_summary:
    print("✓ CORRECT: Violation reported - MORE data collected than needed")
else:
    print("❌ FALSE NEGATIVE: Over-collection not detected")

# DPDP-008 Analysis
print("\n🚨 DPDP-008 (Sensitive Data Stored Without Encryption)")
print("-" * 80)
print("Expected condition: pii_encrypted == false")
print(f"Actual data: pii_encrypted = {base_record.get('pii_encrypted')}")
if "DPDP-008" in violation_summary:
    print("⚠️  VIOLATION REPORTED - BUT IS IT CORRECT?")
    print("❌ FALSE POSITIVE: pii_encrypted is TRUE (data IS encrypted, no violation)")
else:
    print("✓ CORRECT: No violation reported")

# DPDP-009 Analysis
print("\n🟡 DPDP-009 (Missing Grievance Redress Mechanism)")
print("-" * 80)
print("Expected condition: grievance_endpoint_available == false")
print(f"Actual data: grievance_endpoint_available = {base_record.get('grievance_endpoint_available')}")
if "DPDP-009" in violation_summary:
    print("✓ CORRECT: Violation reported - NO grievance endpoint available")
else:
    print("❌ FALSE NEGATIVE: Missing grievance endpoint not detected")

# DPDP-011 Analysis
print("\n🟠 DPDP-011 (Excess Data Retention Without Purpose)")
print("-" * 80)
print("Expected condition: data_retained == true AND purpose_completed == true")
print(f"Actual data: data_retained = {base_record.get('data_retained')}")
print(f"Actual data: purpose_completed = {base_record.get('purpose_completed')}")
retention_check = base_record.get('data_retained') == True
purpose_check = base_record.get('purpose_completed') == True
print(f"Condition evaluation: ({retention_check}) AND ({purpose_check}) = {retention_check and purpose_check}")
if "DPDP-011" in violation_summary:
    print("✓ CORRECT: Violation reported - DATA RETAINED AFTER PURPOSE COMPLETE")
else:
    print("❌ FALSE NEGATIVE: Excess retention not detected")

print("\n" + "="*80)
print("LOG-BASED VIOLATIONS FOUND")
print("="*80)

log_violations = {}
for log_entry in tenant_c_logs:
    combined_record = {**base_record, **log_entry}
    log_viols = evaluate_record(combined_record, rules)
    print(f"\n📝 {log_entry.get('log_id')} ({log_entry.get('user')}):")
    for v in log_viols:
        rule_id = v.get("rule_id")
        if rule_id not in log_violations:
            log_violations[rule_id] = []
        log_violations[rule_id].append(log_entry.get('log_id'))
        print(f"   ✗ {rule_id}: {v.get('rule_name')}")

print("\n" + "="*80)
print("SUMMARY: VIOLATIONS ACCURACY CHECK")
print("="*80)

print("\n✅ CORRECT VIOLATIONS (Match DPDP Clauses):")
correct_violations = ["DPDP-002", "DPDP-003", "DPDP-007", "DPDP-009", "DPDP-011"]
for vid in correct_violations:
    if vid in violation_summary:
        print(f"   ✓ {vid}: {violation_summary[vid]['name']}")
    if vid in log_violations:
        print(f"   ✓ {vid}: Found in {len(log_violations[vid])} logs")

print("\n❌ FALSE POSITIVES (No violations but reported):")
false_positives = {
    "DPDP-001": "❌ consent_flag is TRUE (no violation)",
    "DPDP-004": "❌ notice_provided is TRUE (no violation)",
    "DPDP-005": "❌ Adult (age 30) with guardian consent (no violation)",
    "DPDP-008": "❌ pii_encrypted is TRUE (no violation)"
}

for vid, reason in false_positives.items():
    if vid in violation_summary:
        print(f"   {reason}")

print("\n🟠 LOG-BASED VIOLATIONS (Need to check logs):")
log_only = ["DPDP-006", "DPDP-010", "DPDP-012", "DPDP-013", "DPDP-014"]
for vid in log_only:
    if vid in log_violations:
        print(f"   ✓ {vid}: Found in {len(log_violations[vid])} logs - {log_violations[vid]}")

print("\n" + "="*80)
