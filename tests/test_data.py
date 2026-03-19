# tests/test_data.py

import json
from pathlib import Path

def load_json(path):
    with open(path) as f:
        return json.load(f)

def flatten(data):
    """Pull all fields from nested JSON into one flat dict."""
    fields = {}
    if isinstance(data, dict):
        for k, v in data.items():
            fields[k] = v
            if isinstance(v, (dict, list)):
                fields.update(flatten(v))
    elif isinstance(data, list):
        for item in data:
            fields.update(flatten(item))
    return fields

print("=" * 50)
print("TESTING TENANT DATA FILES")
print("=" * 50)

# ── Load rules ───────────────────────────────────────
rules = load_json("data/dpdp_kb/dpdp_rules.json")
print(f"\n✓ Loaded {len(rules)} rules from dpdp_rules.json")

# ── Collect all field names rules expect ─────────────
expected_fields = set()
for rule in rules:
    cond = rule["condition"]
    for key, val in cond.items():
        if "field" in key:
            expected_fields.add(val)

print(f"✓ Rules expect these fields: {sorted(expected_fields)}")

# ── Test each tenant ─────────────────────────────────
for tenant in ["tenant_a", "tenant_b"]:
    print(f"\n── Checking {tenant} ──")

    redacted_dir = Path(f"data/tenants/{tenant}/redacted")
    files = list(redacted_dir.glob("*.json"))

    if not files:
        print(f"  ✗ No files found in {redacted_dir}")
        continue

    # Flatten all files into one dict
    all_fields = {}
    for f in files:
        data = load_json(f)
        all_fields.update(flatten(data))
        print(f"  ✓ Loaded {f.name}")

    # Check which expected fields are present
    print(f"\n  Field coverage:")
    missing = []
    for field in sorted(expected_fields):
        if field in all_fields:
            print(f"    ✓  {field}: {all_fields[field]}")
        else:
            print(f"    ✗  {field}: MISSING")
            missing.append(field)

    if missing:
        print(f"\n  ⚠ {tenant} is missing {len(missing)} fields: {missing}")
    else:
        print(f"\n  ✓ {tenant} has all required fields")

print("\n" + "=" * 50)
print("TEST COMPLETE")
print("=" * 50)