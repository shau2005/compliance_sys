"""
Explainability (XAI) module for DPDP Compliance System.

Provides structured explanations for compliance violations without ML or external APIs.
"""

from src.explainability.service import (
    get_explanation,
    enrich_violations,
    add_explanation_to_violation,
    list_available_violations,
    Explanation,
    VIOLATION_EXPLANATIONS,
    DEFAULT_EXPLANATION,
)

__all__ = [
    "get_explanation",
    "enrich_violations",
    "add_explanation_to_violation",
    "list_available_violations",
    "Explanation",
    "VIOLATION_EXPLANATIONS",
    "DEFAULT_EXPLANATION",
]