import sys
import json
import math
from typing import List, Tuple, Dict
from .db_connection import get_connection
from .violation_record import ViolationRecord
from .regulation_agent import RegulationAgent
from .audit_agent import AuditAgent
from .risk_agent import RiskAgent

# ── DPDP Act Risk Scoring Constants ──────────────────────────
# Max financial penalty under DPDP Act (₹250 Cr)
MAX_PENALTY_CRORE = 250.0

# Section 33 Recurrence Escalation
_RECURRENCE_STEP = 0.10
_RECURRENCE_MAX_BONUS = 0.50

SEVERITY_SCORE = {
    "CRITICAL": 1.00,
    "HIGH":     0.75,
    "MEDIUM":   0.50,
    "LOW":      0.25
}

# Accurate rule weight sum for normalization
ALL_RULE_WEIGHTS = {
    "DPDP-001": 0.80, "DPDP-002": 0.90, "DPDP-003": 0.65,
    "DPDP-004": 0.80, "DPDP-005": 0.70, "DPDP-006": 0.95,
    "DPDP-007": 0.50, "DPDP-008": 0.95, "DPDP-009": 0.30,
    "DPDP-010": 0.85, "DPDP-011": 0.60, "DPDP-012": 0.55,
    "DPDP-013": 0.40, "DPDP-014": 0.75,
}

RULE_SOURCE_TABLE = {
    "DPDP-001": "consent_records",
    "DPDP-002": "consent_records",
    "DPDP-003": "data_lifecycle",
    "DPDP-004": "data_lifecycle",
    "DPDP-005": "data_lifecycle",
    "DPDP-006": "security_events",
    "DPDP-007": "dsar_requests",
    "DPDP-008": "system_inventory",
    "DPDP-009": "governance_config",
    "DPDP-010": "dsar_requests",
    "DPDP-011": "policies",
    "DPDP-012": "governance_config",
    "DPDP-013": "access_logs",
    "DPDP-014": "customer_master",
}

def compute_risk_score(violations: List[ViolationRecord], tenant_id: str) -> Tuple[float, str, Dict[str, float]]:
    """
    Computes an ISO 31000/NIST aligned 'Likelihood x Impact' risk score.
    Replaces legacy logarithmic-dampened scoring with linear prevalence ratios, 
    adding DPDP Act Section 33 recurrence escalation.
    """
    conn = get_connection()
    try:
        table_counts = {}
        for table in set(RULE_SOURCE_TABLE.values()):
            try:
                row = conn.execute(
                    f"SELECT COUNT(*) AS count FROM {table} WHERE tenant_id = %s",
                    [tenant_id]
                ).fetchone()
                table_counts[table] = max(row["count"] if row else 1, 1)
            except Exception:
                table_counts[table] = 1
    finally:
        conn.close()

    # ── Step 2: Group violations by rule_id ───────────────────
    rule_groups: Dict[str, List[ViolationRecord]] = {}
    for v in violations:
        rule_groups.setdefault(v.rule_id, []).append(v)

    # ── Step 3: Compute per-rule contribution ─────────────────
    contributions: Dict[str, float] = {}
    for rule_id, rule_vs in rule_groups.items():
        affected_rows = len(rule_vs)
        max_rule_score = max(v.rule_score for v in rule_vs)
        risk_weight = rule_vs[0].risk_weight
        severity = rule_vs[0].severity
        penalty_crore = rule_vs[0].penalty_exposure_crore

        # ── Likelihood ──
        source_table = RULE_SOURCE_TABLE.get(rule_id, "transaction_events")
        total_rows = table_counts.get(source_table, 1)
        prevalence_ratio = min(affected_rows / total_rows, 1.0)

        recurrence_factor = 1.0 + min(
            _RECURRENCE_STEP * (affected_rows - 1),
            _RECURRENCE_MAX_BONUS
        )
        L = prevalence_ratio * recurrence_factor

        # ── Impact ──
        sev_score = SEVERITY_SCORE.get(severity, 0.5)
        penalty_norm = penalty_crore / MAX_PENALTY_CRORE
        signal_strength = max_rule_score

        I = (
            0.4 * sev_score
            + 0.3 * penalty_norm
            + 0.3 * signal_strength
        )

        # ── Per-rule inherent risk ──
        contribution = L * I * risk_weight
        contributions[rule_id] = round(contribution, 4)

    # ── Step 4: Aggregate and normalise ───────────────────────
    raw = sum(contributions.values())
    max_possible = sum(ALL_RULE_WEIGHTS.values())
    risk_score = round(min((raw / max_possible) * 100, 100.0), 1)

    # ── Step 5: Tier classification ───────────────
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