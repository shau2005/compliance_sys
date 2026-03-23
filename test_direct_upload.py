#!/usr/bin/env python3
"""
Direct test of the fixed upload analysis - using evaluate_tenant function
"""

import json
import shutil
from pathlib import Path
from src.rules_engine.evaluate import evaluate_tenant

def test_upload_analysis():
    """Test by creating tenant_c in the data directory and using evaluate_tenant"""
    print("\n" + "="*80)
    print("🧪 TESTING UPLOAD ANALYSIS (Using evaluate_tenant Function)")
    print("="*80)
    
    files_path = Path(r"C:\Users\Shravani Bhosale\Downloads")
    tenant_dir = Path("data/tenants/tenant_c/redacted")
    
    # Create directory if it doesn't exist
    print("\n📂 Preparing test data...")
    tenant_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy files
    print("   Copying tenant_c files to data/tenants/tenant_c/redacted/...")
    shutil.copy(
        files_path / "tenant_c_policies (1).json",
        tenant_dir / "policies.json"
    )
    shutil.copy(
        files_path / "tenant_c_logs.json",
        tenant_dir / "logs.json"
    )
    shutil.copy(
        files_path / "tenant_c_sysinven.json",
        tenant_dir / "system_inventory.json"
    )
    print("   ✓ Files copied")
    
    # Evaluate using the fixed function
    print("\n⚙️  Evaluating tenant_c with fixed evaluate_tenant()...")
    try:
        result = evaluate_tenant("tenant_c")
        
        total = result['total_violations']
        violations = result['violations']
        
        print("\n" + "-"*80)
        print("📊 VIOLATIONS SUMMARY:")
        print("-"*80)
        
        violations_by_rule = {}
        for v in violations:
            rule_id = v['rule_id']
            if rule_id not in violations_by_rule:
                violations_by_rule[rule_id] = []
            violations_by_rule[rule_id].append(v)
        
        for rule_id in sorted(violations_by_rule.keys()):
            count = len(violations_by_rule[rule_id])
            rule_name = violations_by_rule[rule_id][0]['rule_name']
            severity = violations_by_rule[rule_id][0]['severity']
            print(f"   {rule_id}: {count:2d} × {rule_name:40s} [{severity}]")
        
        print(f"\n   📈 TOTAL: {total} violations detected")
        
        if total > 5:
            print(f"   ✅ SUCCESS! Detecting {total} violations (was 5 before fix)")
            return True
        else:
            print(f"   ⚠️  Still showing only {total} violations")
            return False
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_upload_analysis()
    print("\n" + "="*80)
    exit(0 if success else 1)
