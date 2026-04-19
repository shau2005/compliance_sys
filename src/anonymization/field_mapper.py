import datetime
from typing import Dict, List, Any
from .hasher import hash_id

def _truncate_timestamp(ts: str) -> str:
    """
    Technique 2 — Timestamp Truncation
    Evidence: ISO/IEC 20889 — generalisation technique.
    Time-of-day creates re-identification risk. Date is sufficient.
    """
    if not ts:
        return None
    return ts.split("T")[0]

def _get_today_str() -> str:
    return datetime.date.today().isoformat()

def map_governance_config(policies: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps policies data to governance_config table.
    Gate 1: tenant_id is required for isolation.
    Gate 1/2: company_name kept as tenant_name for MVP identification, though no DPDP agent uses it.
    Gate 2: grievance_endpoint_available needed for compliance checks.
    Technique 4: Drops consent_flag, notice_provided, etc. here as they fall under different tables.
    """
    return {
        "tenant_id": policies["tenant_id"], # Gate 1: Keep
        "tenant_name": policies.get("company_name", "Unknown"), # Gate 1: Keep (Mapped from company_name)
        "grievance_endpoint_available": policies.get("grievance_endpoint_available", False), # Gate 2: Keep
        "dpo_assigned": False, # Generated
        "audit_frequency_days": 90, # Generated
        "last_audit_date": _get_today_str(), # Generated
        "risk_level": "MEDIUM" # Generated
    }

def map_system_inventory(sys_inv: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps system_inventory raw data to new system_inventory table.
    Technique 1: hash_id on component_id
    Technique 5: storage -> system_type, pii_encrypted -> data_processor_type
    Technique 4 (Suppression): Drop name, data_collected, storage, age (used in customer_master instead), component_id
    """
    tenant_id = sys_inv["tenant_id"]
    
    # Technique 5: storage mapped to system_type_enum
    storage = sys_inv.get("storage", "")
    if storage == "encrypted_db":
        sys_type = "core_banking"
    elif storage == "plain_text":
        sys_type = "crm"
    else:
        sys_type = "crm"

    return {
        "system_hash": hash_id(sys_inv.get("component_id", "COMP-001"), tenant_id), # Gate 1
        "tenant_id": tenant_id, # Gate 1
        "system_name": "User Database", # Gate 1: Hardcoded per instructions
        "system_type": sys_type, # Gate 2
        "encryption_enabled": sys_inv.get("pii_encrypted", False), # Gate 2
        "access_control_enabled": sys_inv.get("access_control_enabled", False), # Gate 2
        "data_processor_type": "internal", # Gate 1 (Derived from pii_encrypted existence)
        "retention_policy_applied": sys_inv.get("audit_logging_enabled", False), # Gate 2
        "dpa_signed": False, # Generated
        "dpa_expiry_date": None # Generated
    }

def map_policies(policies: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps raw policies into standard retention policy for the policies table.
    Gate 1: tenant_id, policy_hash
    Gate 2: standard values for retention required by agent checks
    """
    tenant_id = policies["tenant_id"]
    return {
        "policy_hash": hash_id(f"{tenant_id}_ret_policy", tenant_id),
        "tenant_id": tenant_id,
        "policy_type": "retention",
        "policy_name": "Default Retention Policy",
        "policy_value_numeric": 365,
        "policy_value_unit": "days",
        "effective_date": _get_today_str(),
        "last_updated": _get_today_str(),
        "is_active": True
    }

def map_customer_master(sys_inv: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates one synthetic customer per tenant based on system inventory stats.
    Technique 1: hash_id applied to synthetic ID
    Gate 1: customer_hash
    Gate 2: age dictates if minor data principal type is applied.
    """
    tenant_id = sys_inv["tenant_id"]
    age = sys_inv.get("age", 25)
    is_minor = age < 18
    princ_type = "minor" if is_minor else "individual"
    
    return {
        "customer_hash": hash_id("CUST_001", tenant_id), # Gate 1
        "tenant_id": tenant_id, # Gate 1
        "is_minor": is_minor, # Gate 2: Age derived check
        "data_principal_type": princ_type, # Gate 2
        "account_status": "active", # Gate 2
        "kyc_status": "verified", # Gate 2
        "country": "IN", # Gate 2
        "created_at": _get_today_str() # Gate 1
    }

def map_consent_records(policies: Dict[str, Any], sys_inv: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps consent flags from policies into consent_records table.
    Technique 5: consent_flag bool -> consent_status ENUM
    """
    tenant_id = policies["tenant_id"]
    
    # Technique 5 mapping
    consent_flag = policies.get("consent_flag", False)
    consent_status = "active" if consent_flag else "expired"
    
    # Guardian consent hash
    guardian_consent = sys_inv.get("guardian_consent", False)
    g_hash = hash_id(f"{tenant_id}_guardian", tenant_id) if guardian_consent else None

    # Calculate expiry
    expiry = (datetime.date.today() + datetime.timedelta(days=365)).isoformat()
    
    return {
        "consent_hash": hash_id("CONSENT_001", tenant_id), # Gate 1
        "customer_hash": hash_id("CUST_001", tenant_id), # Gate 1
        "tenant_id": tenant_id, # Gate 1
        "consent_status": consent_status, # Gate 2 (Technique 5)
        "consent_date": _get_today_str(), # Gate 2
        "expiry_date": expiry, # Gate 2
        "consented_purpose": policies.get("consented_purpose", "loan_processing"), # Gate 2
        "consent_version": "v1.0", # Gate 2
        "notice_provided": policies.get("notice_provided", False), # Gate 2
        "is_bundled": False, # Gate 2
        "consent_channel": "app", # Gate 2
        "guardian_consent_hash": g_hash # Gate 2 (Technique 5 mapping)
    }

def map_transaction_events(logs: List[Dict[str, Any]], policies: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Maps log data to transaction_events.
    Technique 1: hash_id for log IDs.
    Technique 2: Timestamp truncation.
    Technique 5: event_type mapping.
    Technique 4 (Suppression): Drops raw 'user', drops 'log_id' as clear text.
    """
    results = []
    for log in logs:
        tenant_id = log["tenant_id"]
        
        # Technique 5 string mapping
        raw_event = log.get("event_type", "")
        # data_access defaults to account_update for processing context
        event_enum = "account_update" if raw_event == "data_access" else "account_update"
        
        tx = {
            "event_hash": hash_id(log["log_id"] + "_tx", tenant_id), # Gate 1
            "customer_hash": hash_id("CUST_001", tenant_id), # Gate 1
            "tenant_id": tenant_id, # Gate 1
            "consent_hash": hash_id("CONSENT_001", tenant_id), # Gate 1
            "event_type": event_enum, # Gate 2 (Technique 5)
            "processing_purpose": policies.get("processing_purpose", "loan_processing"), # Gate 2
            "event_date": _truncate_timestamp(log.get("timestamp")), # Gate 2 (Technique 2)
            "shared_with_third_party": log.get("shared_with_third_party", False), # Gate 2
            "third_party_hash": None, # Gate 2
            "is_cross_border": False, # Gate 2
            "transfer_country": None # Gate 2
        }
        results.append(tx)
    return results

def map_access_logs(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Maps logs to access_logs table.
    Technique 1: hash_id for employee role.
    Technique 5: employee_role and access_reason ENUM mappings.
    """
    results = []
    for log in logs:
        tenant_id = log["tenant_id"]
        
        raw_role = log.get("employee_role", "")
        role_map = {
            "analyst": "data_analyst",
            "intern": "data_analyst",
            "admin": "compliance_officer"
        }
        mapped_role = role_map.get(raw_role, "customer_support")
        
        reason_map = {
            "data_analyst": "data_export",
            "underwriter": "loan_review",
            "compliance_officer": "kyc_check",
            "collections_agent": "loan_review"
        }
        access_reason = reason_map.get(mapped_role, "support_query")
        
        acc = {
            "access_hash": hash_id(log["log_id"] + "_acc", tenant_id), # Gate 1
            "customer_hash": hash_id("CUST_001", tenant_id), # Gate 1
            "tenant_id": tenant_id, # Gate 1
            "employee_hash": hash_id(mapped_role + "_emp", tenant_id), # Gate 1
            "employee_role": mapped_role, # Gate 2 (Technique 5)
            "accessed_pii": log.get("accessed_pii", False), # Gate 2
            "pii_fields_accessed": "kyc_documents" if log.get("accessed_pii") else None, # Gate 2
            "access_reason": access_reason, # Gate 2 (Technique 5)
            "access_outcome": "granted", # Gate 2
            "data_volume_accessed": "low", # Gate 2
            "access_date": _truncate_timestamp(log.get("timestamp")) # Gate 2 (Technique 2)
        }
        results.append(acc)
    return results

def map_data_lifecycle(sys_inv: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps system inventory lifecycle logic to data_lifecycle table.
    Technique 5: Complex ENUM mapping for retention_status.
    """
    tenant_id = sys_inv["tenant_id"]
    
    data_retained = sys_inv.get("data_retained", False)
    purpose_completed = sys_inv.get("purpose_completed", False)
    erasure_requested = sys_inv.get("erasure_requested", False)
    
    # Technique 5 for retention status
    if data_retained and purpose_completed:
        retention_status = "expired"
    elif not data_retained and erasure_requested:
        retention_status = "pending_deletion"
    else:
        retention_status = "active"
        
    return {
        "lifecycle_hash": hash_id("LC_001", tenant_id), # Gate 1
        "customer_hash": hash_id("CUST_001", tenant_id), # Gate 1
        "tenant_id": tenant_id, # Gate 1
        "data_category": "kyc_documents", # Gate 2
        "retention_expiry_date": sys_inv.get("retention_expiry_date"), # Gate 2
        "retention_status": retention_status, # Gate 2 (Technique 5)
        "purpose_completed": purpose_completed, # Gate 2
        "erasure_requested": erasure_requested, # Gate 2
        "erasure_date": _get_today_str() if erasure_requested else None, # Gate 2
        "legal_hold_flag": False, # Gate 2
        "erasure_request_source": "user" if erasure_requested else None # Gate 2
    }

def map_security_events(logs: List[Dict[str, Any]], policies: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Maps breaches to security_events table.
    Technique 3: Buckets affected_user_count into user_count_band ENUM.
    Technique 3: Keeps notification_delay as integer hours.
    Technique 5: pii_encrypted -> encryption_type
    """
    def _bucket_user_count(count) -> str:
        """
        Technique 3 — Bucketing
        Bands derived from CERT-In and DPDP penalty thresholds.
        """
        if count is None:
            return None
        count = int(count)
        if count <= 100:
            return "minimal"
        elif count <= 1000:
            return "moderate"
        elif count <= 10000:
            return "large"
        else:
            return "critical"

    results = []
    for log in logs:
        tenant_id = log["tenant_id"]
        pii_encrypted = policies.get("pii_encrypted", False)
        encryption_type = "AES-256" if pii_encrypted else "none"

        breach_detected = log.get("breach_detected", False)

        if breach_detected:
            confirmed_date = _truncate_timestamp(log.get("timestamp"))
            delay_hours = log.get("notification_delay", 0)
        else:
            confirmed_date = None
            delay_hours = None

        sec = {
            "security_hash": hash_id(log["log_id"] + "_sec", tenant_id),
            "customer_hash": hash_id("CUST_001", tenant_id),
            "tenant_id": tenant_id,
            "pii_encrypted": pii_encrypted,
            "encryption_type": encryption_type,
            "breach_detected": breach_detected,
            "breach_confirmed_date": confirmed_date,
            "notification_delay_hours": delay_hours,
            "affected_user_count": _bucket_user_count(log.get("affected_user_count")) if breach_detected else None,  # Technique 3
            "data_categories_breached": log.get("data_categories_breached") if breach_detected else None,
            "security_audit_flag": False
        }
        results.append(sec)
    return results

def map_dsar_requests(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Maps erasure requests to dsar_requests table.
    Only maps logs where erasure_requested is True.
    """
    results = []
    for log in logs:
        if not log.get("erasure_requested", False):
            continue
            
        tenant_id = log["tenant_id"]
        sub_date_str = _truncate_timestamp(log.get("timestamp"))
        sub_date = datetime.date.fromisoformat(sub_date_str) if sub_date_str else datetime.date.today()
        
        sla_due = sub_date + datetime.timedelta(days=30)
        today = datetime.date.today()
        
        data_deleted = log.get("data_deleted", False)
        sla_breached = not data_deleted and today > sla_due
        
        dsar = {
            "dsar_hash": hash_id(log["log_id"] + "_dsar", tenant_id), # Gate 1
            "customer_hash": hash_id("CUST_001", tenant_id), # Gate 1
            "tenant_id": tenant_id, # Gate 1
            "request_type": "erasure", # Gate 2
            "submitted_date": sub_date.isoformat(), # Gate 2 (Technique 2)
            "acknowledged_date": None, # Gate 2
            "sla_due_date": sla_due.isoformat(), # Gate 2
            "sla_breached": sla_breached, # Gate 2
            "fulfilled_date": _get_today_str() if data_deleted else None, # Gate 2
            "fulfillment_status": "fulfilled" if data_deleted else "pending", # Gate 2
            "rejection_reason": None # Gate 2
        }
        results.append(dsar)
    return results
