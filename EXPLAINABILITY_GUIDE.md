# Explainability (XAI) Service - Complete Documentation

## Overview

The Explainability Service provides structured, rule-based explanations for DPDP compliance violations without using ML or external APIs. It's designed for modularity, extensibility, and production-readiness.

---

## Architecture

### Key Design Principles

1. **Modular**: All XAI logic isolated in `src/explainability/service.py`
2. **Rule-based**: Deterministic explanations from a dictionary store
3. **Extensible**: Easy to add new violations or update explanations
4. **Non-destructive**: Enrichment doesn't modify original data
5. **Production-ready**: Type hints, docstrings, error handling

### Component Structure

```
src/explainability/
├── __init__.py              # Exports public API
└── service.py               # Core service logic
    ├── VIOLATION_EXPLANATIONS  # Knowledge base (dict)
    ├── DEFAULT_EXPLANATION     # Fallback explanation
    ├── get_explanation()       # Retrieve explanation
    └── enrich_violations()     # Batch enrichment
```

### API Integration Flow

```
FastAPI Route
    ↓
rules_engine.evaluate()  [returns raw violations]
    ↓
explainability.enrich_violations()  [adds explanations]
    ↓
schemas.ViolationItem (includes explanation)
    ↓
HTTP Response
```

---

## Core Functions

### 1. `get_explanation(violation_identifier: str) -> Dict[str, str]`

Retrieves explanation for a specific violation.

**Parameters:**
- `violation_identifier`: Rule ID (e.g., "DPDP-001")

**Returns:**
- Dictionary with keys: `why_detected`, `evidence`, `risk_reason`, `mitigation`
- **Fallback**: Returns `DEFAULT_EXPLANATION` if rule not found

**Example:**
```python
from src.explainability.service import get_explanation

# Get explanation for known rule
explanation = get_explanation("DPDP-001")
print(explanation["why_detected"])      # Why violation was detected
print(explanation["evidence"])           # Supporting evidence
print(explanation["risk_reason"])        # Risk and impact
print(explanation["mitigation"])         # Steps to fix

# Get explanation for unknown rule (returns default)
explanation = get_explanation("CUSTOM-UNKNOWN")
print(explanation["why_detected"])       # Returns default template
```

### 2. `enrich_violations(violations: List[Dict]) -> List[Dict]`

Batch-processes violations to attach explanations.

**Parameters:**
- `violations`: List of violation dicts from compliance engine

**Input Format:**
```python
[
    {
        "rule_id": "DPDP-001",
        "rule_name": "Missing Consent Before Processing",
        "severity": "HIGH",
        "occurrence_count": 5,
        ...  # other fields preserved
    },
    ...
]
```

**Output Format:**
```python
[
    {
        "rule_id": "DPDP-001",
        "rule_name": "Missing Consent Before Processing",
        "severity": "HIGH",
        "occurrence_count": 5,
        "explanation": {
            "why_detected": "Personal data processing detected...",
            "evidence": "The automated compliance check...",
            "risk_reason": "Processing personal data without consent...",
            "mitigation": "1. Implement explicit consent collection\n2. ..."
        },
        ...  # other fields preserved
    },
    ...
]
```

**Example:**
```python
from src.explainability.service import enrich_violations

# Raw violations from compliance engine
raw_violations = [
    {"rule_id": "DPDP-001", "severity": "HIGH", "occurrence_count": 5},
    {"rule_id": "DPDP-003", "severity": "HIGH", "occurrence_count": 2}
]

# Enrich with explanations
enriched = enrich_violations(raw_violations)

# Access explanation
for v in enriched:
    print(f"{v['rule_id']}: {v['explanation']['why_detected']}")
```

### 3. `add_explanation_to_violation(violation: Dict) -> Dict`

Adds explanation to a single violation (utility function).

**Example:**
```python
from src.explainability.service import add_explanation_to_violation

violation = {"rule_id": "DPDP-002", "severity": "HIGH"}
enhanced = add_explanation_to_violation(violation)
# enhanced now has 'explanation' field
```

### 4. `list_available_violations() -> List[str]`

Returns list of all documented violations in the knowledge base.

**Example:**
```python
from src.explainability.service import list_available_violations

violations = list_available_violations()
# Output: ['DPDP-001', 'DPDP-002', 'DPDP-003', 'DPDP-004', 'DPDP-005', 'DPDP-006', 'DPDP-007']
print(f"Knowledge base covers {len(violations)} violations")
```

---

## Knowledge Base Structure

### Violation Explanations Dictionary

```python
VIOLATION_EXPLANATIONS = {
    "DPDP-001": {
        "why_detected": "Personal data processing detected without valid prior consent...",
        "evidence": "The automated compliance check identified personal data fields...",
        "risk_reason": "Processing personal data without consent is a direct violation...",
        "mitigation": "1. Implement explicit consent collection...\n2. ..."
    },
    "DPDP-002": { ... },
    ...
}
```

### Default Explanation

Used when a violation is not found in the knowledge base:

```python
DEFAULT_EXPLANATION = {
    "why_detected": "A compliance violation was detected during the automated...",
    "evidence": "The violation was identified through the rule-based...",
    "risk_reason": "This violation indicates a potential non-compliance...",
    "mitigation": "1. Review the violation in detail...\n2. ..."
}
```

---

## API Response Integration

The API automatically includes explanations in responses:

### Schema Definition
```python
# In src/api/schemas.py

class ExplanationDetail(BaseModel):
    why_detected: str
    evidence: str
    risk_reason: str
    mitigation: str

class ViolationItem(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    risk_weight: float
    occurrence_count: int
    explanation: Optional[ExplanationDetail] = None
```

### API Response Example
```json
{
  "tenant_id": "tenant_a",
  "unique_rules_violated": 2,
  "risk_score": 0.85,
  "violations": [
    {
      "rule_id": "DPDP-001",
      "rule_name": "Missing Consent Before Processing",
      "severity": "HIGH",
      "occurrence_count": 15,
      "explanation": {
        "why_detected": "Personal data processing detected without valid prior consent...",
        "evidence": "The automated compliance check identified personal data...",
        "risk_reason": "Processing personal data without consent is a direct violation...",
        "mitigation": "1. Implement explicit consent collection\n2. Maintain verifiable consent records\n..."
      }
    }
  ]
}
```

---

## How to Add New Violations

### Step 1: Add to Knowledge Base

Edit `src/explainability/service.py` and add entry to `VIOLATION_EXPLANATIONS`:

```python
VIOLATION_EXPLANATIONS: Dict[str, Dict[str, str]] = {
    # ... existing entries ...
    
    # NEW RULE: DPDP-008
    "DPDP-008": {
        "why_detected": (
            "Describe how violation is detected..."
        ),
        "evidence": (
            "Explain what data was checked..."
        ),
        "risk_reason": (
            "Explain compliance and business risks..."
        ),
        "mitigation": (
            "1. First remediation step\n"
            "2. Second remediation step\n"
            "3. ..."
        ),
    },
}
```

### Step 2: Test

```python
from src.explainability.service import get_explanation, enrich_violations

# Test individual explanation
explanation = get_explanation("DPDP-008")
print(explanation["why_detected"])

# Test in violation list
violations = [
    {"rule_id": "DPDP-008", "rule_name": "New Rule", "severity": "MEDIUM"}
]
enriched = enrich_violations(violations)
print(enriched[0]["explanation"])
```

---

## How to Customize Explanations

### Changing Existing Explanation

1. Locate rule in `VIOLATION_EXPLANATIONS` dict
2. Update any of the four fields: `why_detected`, `evidence`, `risk_reason`, `mitigation`
3. Changes automatically propagate to API responses

**Example:**
```python
"DPDP-001": {
    "why_detected": (
        "Updated description of how DPDP-001 is detected..."
    ),
    # ... other fields ...
}
```

### Using Long Multi-line Text

Use Python string continuation for readability:

```python
"mitigation": (
    "1. Step one explanation\n"
    "2. Step two explanation\n"
    "3. Another detailed step with more context about\n"
    "   why this is important\n"
    "4. Final step"
)
```

---

## Future Extension Possibilities

### 1. LLM-based Explanations
```python
# Could replace rule-based with LLM-generated explanations
async def get_explanation_llm(rule_id: str, context: Dict) -> Dict[str, str]:
    # Call LLM with rule + evidence context
    # Return structured explanation
    pass
```

### 2. Explanation Localization
```python
VIOLATION_EXPLANATIONS_EN = { ... }
VIOLATION_EXPLANATIONS_ES = { ... }
VIOLATION_EXPLANATIONS_FR = { ... }

def get_explanation(rule_id: str, language: str = "en") -> Dict[str, str]:
    # Return explanation in requested language
    pass
```

### 3. Evidence-Rich Explanations
```python
# Enhance with actual data points
enriched_explanation = {
    **get_explanation(rule_id),
    "affected_records": 15,
    "affected_data_fields": ["email", "phone", "ssn"],
    "violation_examples": [ ... ]
}
```

### 4. Dynamic Mitigation Prioritization
```python
def get_prioritized_mitigation(rule_id: str, context: Dict) -> List[str]:
    # Return mitigation steps prioritized by:
    # - Regulatory urgency
    # - Implementation difficulty
    # - Risk reduction impact
    pass
```

---

## Testing

### Running Tests

```bash
cd c:\Users\Shravani Bhosale\Desktop\compliance_sys
python -m pytest tests/test_explainability.py -v
```

### Manual Testing

```python
from tests.test_explainability import run_all_tests

# Run comprehensive test suite
run_all_tests()
```

### Test Coverage

- ✓ Get single explanation
- ✓ Get unknown violation (default return)
- ✓ Enrich violation list
- ✓ Add explanation to single violation
- ✓ List available violations
- ✓ Full integration flow

---

## Performance Considerations

### Dictionary Lookup (O(1))
```python
explanation = get_explanation("DPDP-001")  # O(1) hash lookup
```

### Batch Enrichment (O(n))
```python
enriched = enrich_violations(violations)  # O(n) where n = number of violations
```

### Memory Usage
- Knowledge base: ~15 KB (7 violations × ~2 KB per explanation)
- Per enriched violation: +0.5-1 KB (explanation text)
- Negligible for typical use cases

---

## Integration Checklist

- [x] Service layer created (`src/explainability/service.py`)
- [x] Knowledge base populated (7 DPDP violations)
- [x] Default explanation template implemented
- [x] API schemas updated (ExplanationDetail, ViolationItem)
- [x] API routes integrated (`/analyze` and `/analyze/upload`)
- [x] Module exports configured (`__init__.py`)
- [x] Type hints and docstrings complete
- [x] Test suite created (`tests/test_explainability.py`)
- [x] Documentation written
- [x] Production-ready (no external dependencies)

---

## Troubleshooting

### Issue: Explanations not appearing in API response

**Cause**: API not using enriched violations

**Solution**: 
```python
# In routes.py, ensure:
enriched_violations = enrich_violations(result['violations'])
# Then use enriched_violations, not result['violations']
```

### Issue: Unknown rule returns default explanation

**Root Cause**: Rule ID not in `VIOLATION_EXPLANATIONS` dictionary

**Solution**: 
1. Check spelling of rule_id
2. Add new explanation if it's a new rule
3. Or customize DEFAULT_EXPLANATION

### Issue: Explanation field is None

**Cause**: ExplanationDetail not being populated in ViolationItem

**Solution**: Verify the mapping in routes when building ViolationItem objects

---

## Code Quality

- **Type Hints**: 100% coverage
- **Docstrings**: Google-style, comprehensive
- **No External Dependencies**: Pure Python
- **Error Handling**: Returns sensible defaults
- **Code Style**: PEP 8 compliant

---

## Support & Maintenance

### Adding Violations
1. Update `VIOLATION_EXPLANATIONS` dict
2. Update tests
3. Run test suite
4. Document in changelog

### Updating Explanations
1. Edit explanation text in dict
2. Test in isolation
3. Verify in integrated tests
4. No code deployment needed

### Version Compatibility
- Python 3.8+
- FastAPI compatible
- Pydantic v1 & v2 compatible

---

## References

### Related Files
- `src/explainability/service.py` - Core service
- `src/api/routes.py` - API integration
- `src/api/schemas.py` - Response schemas
- `tests/test_explainability.py` - Test suite

### DPDP Documentation
- DPDP Rules: `data/dpdp_kb/dpdp_rules.json`
- DPDP Clauses: `data/dpdp_kb/clauses.json`

---

*Generated: March 24, 2026*
*Version: 1.0 - Production Ready*
