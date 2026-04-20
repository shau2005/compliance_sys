import sys
import json
from pathlib import Path
from typing import Dict, Any

from src.agent_layer.orchestrator import run_compliance_analysis
from src.explainability.service import enrich_violations
from src.explainability.report_builder import build_compliance_report, save_report

def run_full_analysis(tenant_id: str) -> Dict[str, Any]:
    """
    Executes the end-to-end compliance analysis, explains the results, 
    and generates a detailed compliance report.
    
    Args:
        tenant_id: Target tenant to analyze.
        
    Returns:
        Dict containing metadata and the full compliance report.
    """
    # Step 1: Run agents
    analysis = run_compliance_analysis(tenant_id)
    if analysis.get("status") != "success":
        raise RuntimeError(f"Agent analysis failed: {analysis.get('message')}")

    # Step 2: Get precomputed contributions
    contributions = analysis.get("risk_contributions", {})

    # Step 3: Enrich violations and warnings with explanations
    all_records = analysis.get("violations", []) + analysis.get("warnings", [])
    all_explanations = enrich_violations(all_records, contributions)

    # Step 4 & 5: Build report
    # report_builder resolves tenant_name internally from DB if None
    report = build_compliance_report(
        tenant_id=tenant_id,
        tenant_name=None,
        analysis_result=analysis,
        all_explanations=all_explanations
    )

    # Step 6: Save report
    path = save_report(report, tenant_id)

    # Step 7: Save violation dicts to outputs/decisions/{tenant_id}/
    decisions_dir = Path(f"outputs/decisions/{tenant_id}")
    decisions_dir.mkdir(parents=True, exist_ok=True)
    
    for v in analysis.get("violations", []):
        rule_id = v.get("rule_id", "unknown_rule")
        record_id = v.get("record_id", "unknown_record")
        decision_file = decisions_dir / f"{rule_id}_{record_id}.json"
        with open(decision_file, "w", encoding="utf-8") as f:
            json.dump(v, f, indent=2, default=str)

    return {
        "tenant_id": tenant_id,
        "report_path": str(path),
        "risk_score": analysis.get("risk_score", 0.0),
        "risk_tier": analysis.get("risk_tier", "COMPLIANT"),
        "total_violations": analysis.get("total_violations", 0),
        "total_warnings": analysis.get("total_warnings", 0),
        "report": report
    }

if __name__ == "__main__":
    target_tenant_id = sys.argv[1] if len(sys.argv) > 1 else "tenant_a"
    
    try:
        result = run_full_analysis(target_tenant_id)
        report_data = result.pop("report")
        print(json.dumps(result, indent=2, default=str))
        print(f"\nFull report saved to: {result['report_path']}")
    except Exception as e:
        print(f"Analysis failed: {e}", file=sys.stderr)
        sys.exit(1)
