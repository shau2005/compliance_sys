#!/usr/bin/env python3
"""Check if DPDP-013 is violating at policy level."""

import json
from src.rules_engine.evaluate import load_rules, evaluate_record

# Load tenant_c data
with open('data/tenants/tenant_c/redacted/policies.json') as f:
    policies = json.load(f)
with open('data/tenants/tenant_c/redacted/system_inventory.json') as f:
    inventory = json.load(f)

# Combine base record
base_record = {**policies, **inventory}

rules = load_rules()
dpdp_013 = next((r for r in rules if r['rule_id'] == 'DPDP-013'), None)

if dpdp_013:
    print(f'Rule: {dpdp_013["rule_id"]} - {dpdp_013["rule_name"]}')
    print(f'Entity: {dpdp_013.get("entity")}')
    print(f'Condition: {json.dumps(dpdp_013["condition"], indent=2)}')
    print()
    
    # Test on base record
    violations = evaluate_record(base_record, [dpdp_013])
    print(f'Violations in base record (policies + inventory): {len(violations)}')
    if violations:
        print('  ^ Policy-level violation detected!')
        print(f'  Base record fields that might trigger:')
        for key in ['accessed_pii', 'employee_role']:
            if key in base_record:
                print(f'    {key}: {base_record[key]}')
    else:
        print('  No policy-level violation')
