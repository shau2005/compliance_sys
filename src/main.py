import json
from pathlib import Path
from src.config import tenant_redacted_dir, RULES_FILE
from src.rules_engine.evaluate import evaluate_tenant
from src.scoring.score import calculate_score


def print_report(tenant_id: str, result: dict, score: dict):
    """
    Print a clean compliance report to the terminal.
    """
    print("\n" + "=" * 60)
    print(f"  COMPLIANCE REPORT — {tenant_id.upper()}")
    print("=" * 60)

    print(f"  Tenant ID      : {tenant_id}")
    print(f"  Violations     : {result['total_violations']}")
    print(f"  Risk Score     : {score['score']} / 100")
    print(f"  Risk Tier      : {score['tier']}")

    print("\n" + "-" * 60)

    if result['total_violations'] == 0:
        print("  ✓ FULLY COMPLIANT — No violations detected")
    else:
        print("  VIOLATIONS FOUND:")
        for i, v in enumerate(result['violations'], 1):
            print(f"\n  {i}. [{v['severity']}] {v['rule_name']}")
            print(f"     Section : {v['dpdp_section']}")
            print(f"     Reason  : {v['reason']}")
            print(f"     Weight  : {v['risk_weight']}")

    print("\n" + "=" * 60 + "\n")


def run_compliance_check(tenant_id: str):
    """
    Run full compliance pipeline for one tenant.

    Steps:
    1. Run rules engine
    2. Calculate risk score
    3. Print report
    4. Save output to file
    """
    print(f"\n[MAIN] Starting compliance check for: {tenant_id}")

    # Step 1: Run rules engine
    print(f"[MAIN] Running rules engine...")
    result = evaluate_tenant(tenant_id)

    # Step 2: Calculate risk score
    print(f"[MAIN] Calculating risk score...")
    score = calculate_score(result['violations'])

    # Step 3: Print report
    print_report(tenant_id, result, score)

    # Step 4: Save output
    output = {
        "tenant_id":       tenant_id,
        "violation_count": result['total_violations'],
        "risk_score":      score['score'],
        "risk_tier":       score['tier'],
        "violations":      result['violations']
    }

    output_path = Path(f"outputs/decisions/{tenant_id}_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[MAIN] Report saved to: {output_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("  DPDP COMPLIANCE ENGINE")
    print("=" * 60)

    run_compliance_check("tenant_a")
    run_compliance_check("tenant_b")