# src/rules_engine/evaluate.py

import json
from pathlib import Path
from datetime import datetime
from src.config import RULES_FILE

# ═══════════════════════════════════════════════════════════
# SECTION 1: LOAD RULES FROM JSON
# ═══════════════════════════════════════════════════════════

def load_rules():
    """
    Load all rules from dpdp_rules.json
    
    Returns:
        list: List of rule dictionaries
    
    Example output:
        [
            {
                "rule_id": "DPDP-001",
                "rule_name": "Missing Consent Before Processing",
                "severity": "HIGH",
                "risk_weight": 0.9,
                "check_type": "boolean_check",
                "condition": {...},
                "enabled": true
            },
            ...
        ]
    """
    with open(RULES_FILE, 'r') as f:
        rules = json.load(f)
    
    # Filter only enabled rules
    enabled_rules = [r for r in rules if r.get("enabled", True)]
    
    return enabled_rules

# ═══════════════════════════════════════════════════════════
# SECTION 2: CONDITION EVALUATORS FOR 4 CHECK TYPES
# ═══════════════════════════════════════════════════════════

def evaluate_boolean_check(record, condition):
    """
    Check: field == value
    
    Example condition:
        {"field": "consent_flag", "operator": "equals", "value": false}
    
    Returns:
        bool: True if violation (condition is met)
    """
    field = condition.get("field")
    operator = condition.get("operator")
    expected_value = condition.get("value")
    
    actual_value = record.get(field)
    
    if operator == "equals":
        # Violation if actual == expected
        return actual_value == expected_value
    elif operator == "not_equals":
        # Violation if actual != expected
        return actual_value != expected_value
    
    return False


def evaluate_comparison_check(record, condition):
    """
    Check: field_1 operator field_2
    
    Example condition:
        {
            "field_1": "processing_purpose",
            "operator": "not_equals",
            "field_2": "consented_purpose"
        }
    
    Returns:
        bool: True if violation
    """
    field_1 = condition.get("field_1")
    field_2 = condition.get("field_2")
    operator = condition.get("operator")
    
    value_1 = record.get(field_1)
    value_2 = record.get(field_2)
    
    if operator == "not_equals":
        return value_1 != value_2
    elif operator == "equals":
        return value_1 == value_2
    elif operator == "greater_than":
        # Add None checks to prevent TypeError
        if value_1 is None or value_2 is None:
            return False
        return value_1 > value_2
    elif operator == "less_than":
        # Add None checks to prevent TypeError
        if value_1 is None or value_2 is None:
            return False
        return value_1 < value_2
    
    return False


def evaluate_date_comparison(record, condition):
    """
    Check: date field is in the past
    
    Example condition:
        {"field": "retention_expiry_date", "operator": "past_date"}
    
    Returns:
        bool: True if date is in past (violation)
    """
    field = condition.get("field")
    operator = condition.get("operator")
    
    date_str = record.get(field)
    
    if not date_str:
        return False
    
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now()
        
        if operator == "past_date":
            # Violation if date is in the past
            return date_obj < today
    except (ValueError, TypeError):
        return False
    
    return False


def evaluate_compound_check(record, condition):
    """
    Check: multiple conditions (AND logic - all must be true)
    
    Example condition (DPDP-005):
        {
            "age_field": "age",
            "age_operator": "less_than",
            "age_value": 18,
            "guardian_consent_field": "guardian_consent",
            "guardian_operator": "equals",
            "guardian_value": false
        }
    
    Returns:
        bool: True if ALL sub-conditions are met (violation)
    """
    # For children data protection (age < 18 AND no guardian consent)
    if "age_field" in condition:
        age_field = condition.get("age_field")
        age_operator = condition.get("age_operator")
        age_value = condition.get("age_value")
        
        age = record.get(age_field)
        
        age_check = False
        if age_operator == "less_than":
            age_check = age < age_value
        
        guardian_field = condition.get("guardian_consent_field")
        guardian_operator = condition.get("guardian_operator")
        guardian_value = condition.get("guardian_value")
        
        guardian = record.get(guardian_field)
        
        guardian_check = False
        if guardian_operator == "equals":
            guardian_check = guardian == guardian_value
        
        # Both must be true for violation
        return age_check and guardian_check
    
    # For unauthorized sharing (shared AND no consent)
    if "share_field" in condition:
        share_field = condition.get("share_field")
        share_operator = condition.get("share_operator")
        share_value = condition.get("share_value")
        
        shared = record.get(share_field)
        share_check = shared == share_value if share_operator == "equals" else False
        
        consent_field = condition.get("consent_field")
        consent_operator = condition.get("consent_operator")
        consent_value = condition.get("consent_value")
        
        consent = record.get(consent_field)
        consent_check = consent == consent_value if consent_operator == "equals" else False
        
        return share_check and consent_check
    
    # For erasure requests (requested AND not deleted)
    if "request_field" in condition:
        request_field = condition.get("request_field")
        request_operator = condition.get("request_operator")
        request_value = condition.get("request_value")
        
        requested = record.get(request_field)
        request_check = requested == request_value if request_operator == "equals" else False
        
        deleted_field = condition.get("deleted_field")
        deleted_operator = condition.get("deleted_operator")
        deleted_value = condition.get("deleted_value")
        
        deleted = record.get(deleted_field)
        deleted_check = deleted == deleted_value if deleted_operator == "equals" else False
        
        return request_check and deleted_check
    
    # For excess retention (retained AND purpose completed)
    if "retain_field" in condition:
        retain_field = condition.get("retain_field")
        retain_operator = condition.get("retain_operator")
        retain_value = condition.get("retain_value")
        
        retained = record.get(retain_field)
        retain_check = retained == retain_value if retain_operator == "equals" else False
        
        purpose_field = condition.get("purpose_field")
        purpose_operator = condition.get("purpose_operator")
        purpose_value = condition.get("purpose_value")
        
        purpose = record.get(purpose_field)
        purpose_check = purpose == purpose_value if purpose_operator == "equals" else False
        
        return retain_check and purpose_check
    
    # For unauthorized access (accessed AND wrong role)
    if "access_field" in condition:
        access_field = condition.get("access_field")
        access_operator = condition.get("access_operator")
        access_value = condition.get("access_value")
        
        accessed = record.get(access_field)
        access_check = accessed == access_value if access_operator == "equals" else False
        
        role_field = condition.get("role_field")
        role_operator = condition.get("role_operator")
        allowed_roles = condition.get("allowed_roles", [])
        
        role = record.get(role_field)
        role_check = role not in allowed_roles if role_operator == "not_in" else False
        
        return access_check and role_check
    
    # For delayed breach notification (breach detected AND delay > threshold)
    if "breach_field" in condition:
        breach_field = condition.get("breach_field")
        breach_operator = condition.get("breach_operator")
        breach_value = condition.get("breach_value")
        
        breach = record.get(breach_field)
        breach_check = breach == breach_value if breach_operator == "equals" else False
        
        delay_field = condition.get("delay_field")
        delay_operator = condition.get("delay_operator")
        delay_threshold = condition.get("delay_threshold")
        
        delay = record.get(delay_field)
        # Add None check to prevent TypeError
        delay_check = False
        if delay_operator == "greater_than" and delay is not None:
            delay_check = delay > delay_threshold
        
        return breach_check and delay_check
    
    return False


# ═══════════════════════════════════════════════════════════
# SECTION 3: MAIN EVALUATOR - CHECK RECORD AGAINST RULES
# ═══════════════════════════════════════════════════════════

def evaluate_record(record, rules):
    """
    Check a single record against all rules.
    
    Args:
        record (dict): A data record with fields to check
        rules (list): List of rule objects from dpdp_rules.json
    
    Returns:
        list: List of violation objects (empty if compliant)
    
    Example violation:
        {
            "rule_id": "DPDP-001",
            "rule_name": "Missing Consent Before Processing",
            "dpdp_section": "Consent Requirement",
            "severity": "HIGH",
            "risk_weight": 0.9,
            "reason": "consent_flag is False — expected True",
            "evidence": {
                "consent_flag": False,
                "notice_provided": True,
                ...
            }
        }
    """
    violations = []
    
    for rule in rules:
        # Skip disabled rules
        if not rule.get("enabled", True):
            continue
        
        check_type = rule.get("check_type")
        condition = rule.get("condition")
        
        # Determine which evaluator to use
        is_violated = False
        
        if check_type == "boolean_check":
            is_violated = evaluate_boolean_check(record, condition)
        
        elif check_type == "comparison_check":
            is_violated = evaluate_comparison_check(record, condition)
        
        elif check_type == "date_comparison":
            is_violated = evaluate_date_comparison(record, condition)
        
        elif check_type == "compound_check":
            is_violated = evaluate_compound_check(record, condition)
        
        # If rule is violated, create violation report
        if is_violated:
            violation = {
                "rule_id": rule.get("rule_id"),
                "rule_name": rule.get("rule_name"),
                "dpdp_section": rule.get("dpdp_section"),
                "severity": rule.get("severity"),
                "risk_weight": rule.get("risk_weight"),
                "reason": f"Rule {rule.get('rule_id')} violated: {rule.get('rule_name')}",
                "entity": rule.get("entity"),  # ← Add entity for deduplication
                "evidence": record
            }
            violations.append(violation)
    
    return violations


def extract_triggered_fields(rule_id, rules):
    """
    Extract which fields from the rule condition triggered a violation.
    
    Args:
        rule_id: The rule_id to extract fields from
        rules: All rule definitions
    
    Returns:
        list: Field names that trigger this rule
    """
    fields_triggered = []
    
    # Find the rule definition
    for rule in rules:
        if rule.get("rule_id") == rule_id:
            condition = rule.get("condition", {})
            
            # Extract field names from condition based on check_type
            check_type = rule.get("check_type")
            
            if check_type == "boolean_check":
                field = condition.get("field")
                if field:
                    fields_triggered.append(field)
            
            elif check_type == "comparison_check":
                field_1 = condition.get("field_1")
                field_2 = condition.get("field_2")
                if field_1:
                    fields_triggered.append(field_1)
                if field_2:
                    fields_triggered.append(field_2)
            
            elif check_type == "date_comparison":
                field = condition.get("field")
                if field:
                    fields_triggered.append(field)
            
            elif check_type == "compound_check":
                # Extract all relevant fields from compound conditions
                for key, value in condition.items():
                    if key.endswith("_field"):
                        fields_triggered.append(value)
            
            break
    
    return list(set(fields_triggered))  # Remove duplicates


def evaluate_tenant(tenant_id):
    """
    Load all tenant data files and evaluate for violations.
    
    Args:
        tenant_id (str): "tenant_a" or "tenant_b"
    
    Returns:
        dict: Summary of violations found
        {
            "tenant_id": "tenant_a",
            "total_violations": 0,
            "violations": [...]
        }
    """
    from src.config import tenant_redacted_dir
    
    tenant_dir = tenant_redacted_dir(tenant_id)
    
    # Load all tenant data files
    policies_file = tenant_dir / "policies.json"
    logs_file = tenant_dir / "logs.json"
    inventory_file = tenant_dir / "system_inventory.json"
    
    # Step 1: Load base record from policies and inventory
    base_record = {}
    
    if policies_file.exists():
        with open(policies_file, 'r') as f:
            policies_data = json.load(f)
            if isinstance(policies_data, dict):
                base_record.update(policies_data)
    
    if inventory_file.exists():
        with open(inventory_file, 'r') as f:
            inventory_data = json.load(f)
            if isinstance(inventory_data, dict):
                base_record.update(inventory_data)
            elif isinstance(inventory_data, list) and len(inventory_data) > 0:
                base_record.update(inventory_data[0])
    
    # Load rules
    rules = load_rules()
    
    # Step 2: Evaluate base record (policies + inventory)
    all_violations = []
    violations = evaluate_record(base_record, rules)
    all_violations.extend(violations)
    
    # Step 3: Process and evaluate EACH log entry separately with traceability tracking
    logs_data = []
    if logs_file.exists():
        with open(logs_file, 'r') as f:
            logs_data = json.load(f)
    
    # Track which log IDs triggered which rules
    rule_to_logs = {}  # rule_id -> set of log_ids that triggered it
    
    if isinstance(logs_data, list):
        # Loop through ALL log entries
        for log_entry in logs_data:
            if isinstance(log_entry, dict):
                log_id = log_entry.get("log_id", f"LOG-{logs_data.index(log_entry)}")
                
                # Create combined record: base + individual log entry
                combined_record = {**base_record, **log_entry}
                
                # Evaluate this specific log entry
                log_violations = evaluate_record(combined_record, rules)
                
                # Track log_id for each rule violation
                for violation in log_violations:
                    rule_id = violation.get("rule_id")
                    if rule_id not in rule_to_logs:
                        rule_to_logs[rule_id] = []
                    if log_id not in rule_to_logs[rule_id]:
                        rule_to_logs[rule_id].append(log_id)
                
                all_violations.extend(log_violations)
    
    elif isinstance(logs_data, dict):
        # If logs is a single dict, treat it as one entry
        log_id = logs_data.get("log_id", "LOG-0")
        combined_record = {**base_record, **logs_data}
        log_violations = evaluate_record(combined_record, rules)
        
        for violation in log_violations:
            rule_id = violation.get("rule_id")
            if rule_id not in rule_to_logs:
                rule_to_logs[rule_id] = []
            if log_id not in rule_to_logs[rule_id]:
                rule_to_logs[rule_id].append(log_id)
        
        all_violations.extend(log_violations)
    
    # Step 4: Aggregate violations by rule_id with traceability
    violations_by_rule = {}
    
    for violation in all_violations:
        rule_id = violation.get("rule_id")
        
        if rule_id not in violations_by_rule:
            violations_by_rule[rule_id] = {
                **violation,
                "occurrence_count": 1,
                "matched_record_ids": rule_to_logs.get(rule_id, []),
                "fields_triggered": extract_triggered_fields(rule_id, rules),
                "matched_logs_count": len(rule_to_logs.get(rule_id, []))
            }
        else:
            # Accumulate occurrence count
            violations_by_rule[rule_id]["occurrence_count"] += 1
    
    violations_list = list(violations_by_rule.values())
    
    return {
        "tenant_id": tenant_id,
        "unique_rules_violated": len(violations_list),
        "total_violation_occurrences": sum(v.get("occurrence_count", 1) for v in violations_list),
        "violations": violations_list
    }


# Test the evaluator with real tenant data
if __name__ == "__main__":
    print("\n" + "="*70)
    print("DPDP RULE EVALUATOR TEST")
    print("="*70)
    
    # First, test with hardcoded records
    print("\n📝 TESTING WITH HARDCODED RECORDS...\n")
    
    # Test 1: Compliant record
    compliant_record = {
        "consent_flag": True,
        "notice_provided": True,
        "processing_purpose": "loan_processing",
        "consented_purpose": "loan_processing",
        "pii_encrypted": True,
        "grievance_endpoint_available": True,
        "access_log_available": True,
        "shared_with_third_party": False,
        "consent_for_sharing": True,
        "breach_detected": False,
        "notification_delay": 0,
        "erasure_requested": False,
        "data_deleted": False,
        "collected_fields": 2,
        "required_fields": 2,
        "retention_expiry_date": "2027-01-15",
        "data_retained": False,
        "purpose_completed": False,
        "age": 25,
        "guardian_consent": True,
        "employee_role": "analyst",
        "accessed_pii": True
    }
    
    rules = load_rules()
    violations = evaluate_record(compliant_record, rules)
    print(f"  Test 1 - Compliant Record: {len(violations)} violations (Expected: 0)")
    
    # Test 2: Non-compliant record
    non_compliant_record = {
        "consent_flag": False,  # ← DPDP-001 violation
        "notice_provided": False,  # ← DPDP-004 violation
        "processing_purpose": "marketing",
        "consented_purpose": "loan_processing",  # ← DPDP-002 violation
        "pii_encrypted": False,  # ← DPDP-008 violation
        "grievance_endpoint_available": False,  # ← DPDP-009 violation
        "access_log_available": False,  # ← DPDP-012 violation
        "shared_with_third_party": True,
        "consent_for_sharing": False,  # ← DPDP-006 violation
        "breach_detected": True,
        "notification_delay": 96,  # ← DPDP-014 violation (>72)
        "erasure_requested": True,
        "data_deleted": False,  # ← DPDP-010 violation
        "collected_fields": 12,
        "required_fields": 4,  # ← DPDP-007 violation
        "retention_expiry_date": "2023-01-01",  # ← DPDP-003 violation (past)
        "data_retained": True,
        "purpose_completed": True,  # ← DPDP-011 violation
        "age": 15,  # ← DPDP-005 violation
        "guardian_consent": False,
        "employee_role": "intern",  # ← DPDP-013 violation
        "accessed_pii": True
    }
    
    violations = evaluate_record(non_compliant_record, rules)
    print(f"  Test 2 - Non-Compliant Record: {len(violations)} violations (Expected: ~11-13)\n")
    
    # Test tenant_a (should be compliant - 0 violations)
    print("\n📋 EVALUATING TENANT_A (Compliant Company)...")
    result_a = evaluate_tenant("tenant_a")
    print(f"   ✓ Total Violations: {result_a['total_violations']}")
    if result_a['violations']:
        for v in result_a['violations']:
            print(f"     - {v['rule_id']}: {v['rule_name']}")
    else:
        print(f"   ✓ COMPLIANT - No violations detected!")
    
    # Test tenant_b (should be non-compliant - ~11-14 violations)
    print("\n📋 EVALUATING TENANT_B (Non-Compliant Company)...")
    result_b = evaluate_tenant("tenant_b")
    print(f"   ✗ Total Violations: {result_b['total_violations']}")
    if result_b['violations']:
        print("\n   Violations detected:")
        for i, v in enumerate(result_b['violations'], 1):
            print(f"     {i}. {v['rule_id']} | {v['rule_name']} | {v['severity']} | Weight: {v['risk_weight']}")
    
    print("\n" + "="*70)