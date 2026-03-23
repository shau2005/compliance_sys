# src/api/schemas.py

from pydantic import BaseModel
from typing import List, Optional


class AnalyzeRequest(BaseModel):
    """
    What the client sends to our API.
    Just the tenant_id for now.
    """
    tenant_id: str


class ViolationItem(BaseModel):
    """
    One unique violation found in the compliance check.
    Includes occurrence count for frequency-weighted risk calculation.
    """
    rule_id:              str
    rule_name:            str
    dpdp_section:         str
    severity:             str
    risk_weight:          float
    occurrence_count:     int                          # How many times this rule violated
    contribution_to_score: float                       # Contribution to overall risk score
    reason:               str


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