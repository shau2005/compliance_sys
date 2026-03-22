# src/privacy_gateway/redact.py

import os
import json
import re

RAW_PATH      = "data/raw"
REDACTED_PATH = "data/redacted"


def redact_text(text):
    text = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', 'EMAIL_1', text)
    text = re.sub(r'\b\d{10}\b', 'PHONE_1', text)
    text = re.sub(r'\b\d{12}\b', 'AADHAAR_1', text)
    return text


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


def process_file(input_path, output_path):
    with open(input_path, 'r') as f:
        data = json.load(f)

    text_data    = json.dumps(data)
    redacted     = redact_text(text_data)
    redacted_json = json.loads(redacted)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(redacted_json, f, indent=4)


def process_all():
    for tenant in ["tenant_a", "tenant_b"]:
        input_folder  = os.path.join(RAW_PATH, tenant)
        output_folder = os.path.join(REDACTED_PATH, tenant)

        for file in os.listdir(input_folder):
            process_file(
                os.path.join(input_folder, file),
                os.path.join(output_folder, file)
            )


if __name__ == "__main__":
    process_all()
    print("✅ Redaction complete!")