# src/api/schemas.py

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class AnalyzeRequest(BaseModel):
    """
    What the client sends to our API.
    Just the tenant_id for now.
    """
    tenant_id: str


class ExplanationDetail(BaseModel):
    """
    Structured explanation for a compliance violation.
    Provides why the violation was detected, supporting evidence, risk, and mitigation.
    """
    why_detected: str       # Why the violation was detected
    evidence: str           # Supporting evidence from the data
    risk_reason: str        # Risk and impact explanation
    mitigation: str         # Steps to remediate the violation


class ViolationItem(BaseModel):
    """
    One unique violation found in the compliance check.
    Includes occurrence count for frequency-weighted risk calculation,
    and structured explanation for remediation guidance.
    """
    rule_id:              str
    rule_name:            str
    dpdp_section:         str
    severity:             str
    risk_weight:          float
    occurrence_count:     int                          # How many times this rule violated
    contribution_to_score: float                       # Contribution to overall risk score
    reason:               str
    explanation:          Optional[ExplanationDetail] = None  # Structured explanation (XAI)


class RiskScore(BaseModel):
    """
    Risk score result from the scorer.
    """
    score: float
    tier:  str


class AnalyzeResponse(BaseModel):
    """
    What our API sends back to the client.
    Includes frequency-weighted risk assessment.
    """
    tenant_id:                      str
    unique_rules_violated:          int                 # Unique compliance rules breached
    total_violation_occurrences:    int                 # Total count across all logs
    risk_score:                     float
    risk_tier:                      str
    violations:                     List[ViolationItem]
    status:                         str
# ```

# Save the file.

# ---

# ## What Each Class Does
# ```
# AnalyzeRequest  → validates incoming request
#                   ensures tenant_id is always present

# ViolationItem   → shape of one violation in response

# RiskScore       → shape of score result

# AnalyzeResponse → full response shape
#                   Pydantic validates this automatically
#                   before sending to client