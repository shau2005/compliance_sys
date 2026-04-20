import sys
import json
import math
from typing import List, Tuple, Dict
from .db_connection import get_connection
from .violation_record import ViolationRecord
from .regulation_agent import RegulationAgent
from .audit_agent import AuditAgent
from .risk_agent import RiskAgent

def compute_risk_score(violations: List[ViolationRecord], tenant_id: str) -> Tuple[float, str, Dict[str, float]]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM transaction_events WHERE tenant_id = %s",
            [tenant_id]
        ).fetchone()
        total_rows = row["count"] if row else 1
    finally:
        conn.close()

    rule_groups: Dict[str, List[ViolationRecord]] = {}
    for v in violations:
        rule_groups.setdefault(v.rule_id, []).append(v)

    contributions: Dict[str, float] = {}
    for rule_id, rule_vs in rule_groups.items():
        affected_rows = len(rule_vs)
        rule_score = max(v.rule_score for v in rule_vs)
        risk_weight = rule_vs[0].risk_weight

        E = rule_score
        S = risk_weight
        V = (math.log1p(affected_rows) / math.log1p(max(total_rows, 1) + 1))
        R = 0.0

        contribution = min((E * S * V) + R, 1.0)
        contributions[rule_id] = round(contribution, 4)

    raw = sum(contributions.values())
    normalised = (raw / 14) * 100
    risk_score = round(normalised, 1)

    if risk_score == 0:
        tier = "COMPLIANT"
    elif risk_score < 30:
        tier = "LOW"
    elif risk_score < 55:
        tier = "MEDIUM"
    elif risk_score < 75:
        tier = "HIGH"
    else:
        tier = "CRITICAL"

    return risk_score, tier, contributions

def run_compliance_analysis(tenant_id: str) -> dict:
    conn = get_connection()
    all_violations = (
        RegulationAgent().run(tenant_id, conn) +
        AuditAgent().run(tenant_id, conn) +
        RiskAgent().run(tenant_id, conn)
    )
    conn.close()

    violations_only = [v for v in all_violations if v.outcome == "VIOLATION"]
    warnings_only = [v for v in all_violations if v.outcome == "WARNING"]

    risk_score, tier, contributions = compute_risk_score(violations_only, tenant_id)

    agent_breakdown = {}
    for agent in ["regulation_agent", "audit_agent", "risk_agent"]:
        agent_breakdown[agent] = {
            "violations": sum(1 for v in violations_only if v.agent_name == agent),
            "warnings": sum(1 for v in warnings_only if v.agent_name == agent)
        }

    return {
        "tenant_id": tenant_id,
        "total_violations": len(violations_only),
        "total_warnings": len(warnings_only),
        "risk_score": risk_score,
        "risk_tier": tier,
        "risk_contributions": contributions,
        "agent_breakdown": agent_breakdown,
        "violations": [v.to_dict() for v in violations_only],
        "warnings": [v.to_dict() for v in warnings_only],
        "status": "success"
    }

if __name__ == "__main__":
    tenant_id = sys.argv[1] if len(sys.argv) > 1 else "tenant_a"
    result = run_compliance_analysis(tenant_id)
    print(json.dumps(result, indent=2, default=str))