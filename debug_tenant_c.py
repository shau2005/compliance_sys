import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from src.rules_engine.evaluate import evaluate_tenant

result = evaluate_tenant('tenant_c')
print(f'Unique Rules Violated: {result["unique_rules_violated"]}')
print(f'Total Occurrences: {result["total_violation_occurrences"]}')
print('\nViolations Breakdown:')
for v in result['violations']:
    print(f'  {v["rule_id"]}: {v["rule_name"]:40s} - {v["occurrence_count"]:3d} times')
print(f'\nTotal (sum): {sum(v["occurrence_count"] for v in result["violations"])}')

# Show actual log count
logs = json.load(open('data/tenants/tenant_c/redacted/logs.json'))
print(f'\nActual logs in Tenant C data: {len(logs)}')
