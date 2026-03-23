# src/privacy_gateway/redact.py

import os
import json
import re

RAW_PATH      = "data/raw"
REDACTED_PATH = "data/redacted"

# ── Required fields for each file type (for violation detection) ──
REQUIRED_FIELDS = {
    "policies.json": {
        "tenant_id",
        "consent_flag",
        "notice_provided",
        "processing_purpose",
        "consented_purpose",
        "pii_encrypted",
        "grievance_endpoint_available"
    },
    "logs.json": {
        "tenant_id",
        "log_id",
        "event_type",
        "user",
        "employee_role",
        "accessed_pii",
        "access_log_available",
        "shared_with_third_party",
        "consent_for_sharing",
        "breach_detected",
        "notification_delay",
        "erasure_requested",
        "data_deleted",
        "timestamp"
    },
    "system_inventory.json": {
        "tenant_id",
        "collected_fields",
        "required_fields",
        "pii_encrypted",
        "retention_expiry_date",
        "data_retained",
        "purpose_completed",
        "age",
        "guardian_consent"
    }
}


def redact_text(text):
    text = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', 'EMAIL_1', text)
    text = re.sub(r'\b\d{10}\b', 'PHONE_1', text)
    text = re.sub(r'\b\d{12}\b', 'AADHAAR_1', text)
    return text


def extract_required_fields(data, file_type):
    """
    Extract only the required fields for a given file type.
    
    Args:
        data: dict or list of dicts
        file_type: "policies.json", "logs.json", or "system_inventory.json"
    
    Returns:
        Filtered dict or list of dicts with only required fields
    """
    required = REQUIRED_FIELDS.get(file_type, set())
    
    if isinstance(data, list):
        # For lists, filter each item
        return [extract_required_fields(item, file_type) for item in data]
    elif isinstance(data, dict):
        # Keep only required fields
        return {k: v for k, v in data.items() if k in required}
    else:
        return data


def redact_dict(data):
    """
    Recursively redact PII from any dict or list.
    Used by the upload endpoint in routes.py.

    Example:
        Input:  { "email": "john@gmail.com" }
        Output: { "email": "EMAIL_1" }
    """
    if isinstance(data, dict):
        return {k: redact_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [redact_dict(item) for item in data]
    elif isinstance(data, str):
        return redact_text(data)
    else:
        return data


def redact_file(data, file_type):
    """
    Extract required fields AND redact PII for a file.
    
    Args:
        data: raw dict or list from JSON file
        file_type: "policies.json", "logs.json", or "system_inventory.json"
    
    Returns:
        Filtered and redacted data
    """
    # Step 1: Extract only required fields
    filtered = extract_required_fields(data, file_type)
    
    # Step 2: Redact PII in the filtered data
    redacted = redact_dict(filtered)
    
    return redacted


def process_file(input_path, output_path, file_type):
    with open(input_path, 'r') as f:
        data = json.load(f)

    # Extract required fields only, then redact PII
    processed = redact_file(data, file_type)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(processed, f, indent=4)


def process_all():
    for tenant in ["tenant_a", "tenant_b"]:
        input_folder  = os.path.join(RAW_PATH, tenant)
        output_folder = os.path.join(REDACTED_PATH, tenant)

        for file in os.listdir(input_folder):
            process_file(
                os.path.join(input_folder, file),
                os.path.join(output_folder, file),
                file
            )


if __name__ == "__main__":
    process_all()
    print("✅ Redaction complete!")