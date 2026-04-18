import sys
import json
sys.path.insert(0, '.')

from src.api.routes import analyze_tenant
from src.api.schemas import AnalyzeRequest

# Test with tenant_b (has violations)
request = AnalyzeRequest(tenant_id='tenant_b')

try:
    response = analyze_tenant(request)
    
    print("=== API RESPONSE VERIFICATION ===\n")
    print(f"Tenant: {response.tenant_id}")
    print(f"Risk Score: {response.risk_score}")
    print(f"Violations: {len(response.violations)}")
    print()
    
    # Check first few violations
    for i, v in enumerate(response.violations[:3], 1):
        print(f"\n{i}. {v.rule_id}: {v.rule_name}")
        print(f"   Explanation Present: {v.explanation is not None}")
        if v.explanation:
            print(f"   - Why Detected: {v.explanation.why_detected[:60]}...")
            print(f"   - Risk Reason: {v.explanation.risk_reason[:60]}...")
            print(f"   - Mitigation Steps: {len(v.explanation.mitigation.split(chr(10)))} steps")
            print("   ✓ EXPLANATION COMPLETE")
        else:
            print("   ✗ NULL EXPLANATION")
    
    print("\n" + "="*60)
    print("SUMMARY:")
    violations_with_exp = sum(1 for v in response.violations if v.explanation)
    print(f"Violations with explanations: {violations_with_exp}/{len(response.violations)}")
    
    if violations_with_exp == len(response.violations):
        print("✅ ALL VIOLATIONS HAVE EXPLANATIONS!")
    else:
        print(f"⚠️  {len(response.violations) - violations_with_exp} violations missing explanations")
        
except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
