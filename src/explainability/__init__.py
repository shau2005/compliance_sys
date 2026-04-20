"""
Explainability (XAI) module for DPDP Compliance System.

Provides structured explanations for compliance violations without ML or external APIs.
"""

from src.explainability.explanation import ViolationExplanation
from src.explainability.service import (
    RULE_EXPLANATIONS,
    explain_violation,
    enrich_violations,
    generate_executive_summary,
)
from src.explainability.report_builder import (
    build_compliance_report,
    save_report,
)

__all__ = [
    "ViolationExplanation",
    "RULE_EXPLANATIONS",
    "explain_violation",
    "enrich_violations",
    "generate_executive_summary",
    "build_compliance_report",
    "save_report",
]
