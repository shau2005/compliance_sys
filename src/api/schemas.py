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
    One violation found in the compliance check.
    """
    rule_id:      str
    rule_name:    str
    dpdp_section: str
    severity:     str
    risk_weight:  float
    reason:       str


class RiskScore(BaseModel):
    """
    Risk score result from the scorer.
    """
    score: float
    tier:  str


class AnalyzeResponse(BaseModel):
    """
    What our API sends back to the client.
    """
    tenant_id:       str
    violation_count: int
    risk_score:      float
    risk_tier:       str
    violations:      List[ViolationItem]
    status:          str
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