import dataclasses
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ViolationExplanation:
    """
    Represents a comprehensive explanation of a DPDP Act violation or warning.
    Includes SHAP-equivalent signal weights (analytical SHAP for linear models)
    to explain the contribution of each signal to the final rule score.
    """
    rule_id: str
    rule_name: str
    dpdp_section: str
    agent_name: str
    outcome: str
    severity: str
    what_happened: str
    why_violation: str
    signals_analysis: List[Dict[str, Any]]
    top_contributing_signal: str
    top_signal_weight: float
    penalty_exposure_crore: int
    root_cause: str
    remediation_steps: List[str]
    risk_contribution: float

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the ViolationExplanation instance to a JSON-serializable dictionary.
        
        Returns:
            Dict[str, Any]: The dictionary representation of the explanation.
        """
        return dataclasses.asdict(self)
