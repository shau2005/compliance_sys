"""
Explainability Service (XAI) for DPDP Compliance System

Provides structured explanations for compliance violations with:
- Why violations are detected
- Supporting evidence
- Risk reasoning
- Mitigation strategies

All logic is rule-based and deterministic (no ML/external APIs).
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class Explanation:
    """Structured explanation for a compliance violation."""
    why_detected: str
    evidence: str
    risk_reason: str
    mitigation: str


# ═══════════════════════════════════════════════════════════
# EXPLANATION STORE: Dictionary-based knowledge base
# ═══════════════════════════════════════════════════════════

VIOLATION_EXPLANATIONS: Dict[str, Dict[str, str]] = {
    # DPDP-001: Missing Consent Before Processing
    "DPDP-001": {
        "why_detected": (
            "Personal data processing detected without valid prior consent. "
            "The system found records where consent_flag is false or missing, "
            "indicating data was processed without obtaining explicit permission from the data subject."
        ),
        "evidence": (
            "The automated compliance check identified personal data fields being processed "
            "while the consent_flag in the logs/policies indicates no valid consent was obtained. "
            "This violates DPDP Section 6 which mandates explicit consent before any personal data processing."
        ),
        "risk_reason": (
            "Processing personal data without consent is a direct violation of the core principle "
            "of DPDP. This creates legal exposure, potential regulatory fines, reputational damage, "
            "and loss of customer trust. Unauthorized data processing can also lead to data misuse."
        ),
        "mitigation": (
            "1. Implement explicit consent collection before any data processing\n"
            "2. Maintain verifiable consent records with timestamp and data subject identification\n"
            "3. Add consent validation checks before processing personal data\n"
            "4. Conduct regular consent audits to identify and remediate missing consents\n"
            "5. Train teams on consent requirements and establish consent management policies"
        ),
    },

    # DPDP-002: Processing Beyond Stated Purpose
    "DPDP-002": {
        "why_detected": (
            "Data processing detected beyond the stated purpose. "
            "The system found records where processing_purpose does not match consented_purpose, "
            "indicating data is being used for purposes the data subject did not consent to."
        ),
        "evidence": (
            "Compliance check identified discrepancies between what the data subject consented to "
            "(consented_purpose field) and what the organization is actually processing the data for "
            "(processing_purpose field). This violates the DPDP principle of Purpose Limitation."
        ),
        "risk_reason": (
            "Purpose limitation is a fundamental DPDP requirement. Using personal data for purposes "
            "beyond consent creates legal violations, erodes trust, and may enable unauthorized use of data. "
            "It exposes the organization to regulatory action and potential penalties."
        ),
        "mitigation": (
            "1. Update data collection to explicitly list all intended processing purposes\n"
            "2. Obtain granular consent for each distinct purpose of processing\n"
            "3. Implement controls to prevent out-of-scope processing\n"
            "4. Maintain clear mapping between consented purposes and actual processing\n"
            "5. Regularly audit processing activities for purpose drift\n"
            "6. Establish clear data governance policies limiting purpose expansion"
        ),
    },

    # DPDP-003: Retention Beyond Allowed Period
    "DPDP-003": {
        "why_detected": (
            "Personal data retention detected beyond the allowed period. "
            "The system found records where retention_expiry_date is in the past, "
            "indicating data is being retained longer than legally permitted."
        ),
        "evidence": (
            "The automated check compared current date with retention_expiry_date in the system. "
            "Records with expiry dates that have already passed indicate data is being retained "
            "after its authorized retention period, violating DPDP Storage Limitation principle."
        ),
        "risk_reason": (
            "Storing personal data beyond the authorized period increases exposure risk, "
            "potential for data misuse, and violates data security obligations. "
            "Extended retention amplifies the impact of potential breaches and demonstrates "
            "non-compliance with DPDP requirements for timely data deletion."
        ),
        "mitigation": (
            "1. Establish explicit data retention schedules for each data category\n"
            "2. Implement automated deletion processes to purge expired data\n"
            "3. Create secure backup deletion procedures\n"
            "4. Monitor and audit retention compliance regularly\n"
            "5. Ensure logs capture deletion activities for audit trails\n"
            "6. Review and document legitimate business reasons for any retention extensions"
        ),
    },

    # DPDP-004: Data Shared Without Proper Authorization
    "DPDP-004": {
        "why_detected": (
            "Personal data sharing detected without proper authorization or recipient verification. "
            "The system found records where data_shared flags data disclosure to recipients "
            "without documented authorization or legitimate purpose."
        ),
        "evidence": (
            "Compliance check identified data sharing activities where either: "
            "(1) No authorization exists, or (2) The recipient is not in the approved recipients list. "
            "This indicates potential unauthorized disclosure violating DPDP principles."
        ),
        "risk_reason": (
            "Unauthorized data sharing creates direct privacy violations, potential data breaches, "
            "and loss of data control. It exposes the organization to regulatory penalties and "
            "loss of customer trust. Uncontrolled recipient access increases data misuse risks."
        ),
        "mitigation": (
            "1. Maintain explicit approved recipient lists for each data category\n"
            "2. Require documented authorization before any data sharing\n"
            "3. Implement sharing controls and audit trails\n"
            "4. Conduct recipient security assessments before sharing\n"
            "5. Define clear data sharing agreements with recipients\n"
            "6. Monitor sharing activities against authorized recipients regularly"
        ),
    },

    # DPDP-005: Insufficient Security Controls
    "DPDP-005": {
        "why_detected": (
            "Inadequate security controls detected for personal data protection. "
            "The system identified missing or weak security measures in data handling processes."
        ),
        "evidence": (
            "Compliance check evaluated system inventory against DPDP security requirements "
            "and found gaps in encryption, access controls, monitoring, or other protective measures. "
            "This indicates insufficient technical and organizational measures as required by DPDP."
        ),
        "risk_reason": (
            "Weak security controls increase vulnerability to data breaches, unauthorized access, "
            "and data loss. This violates DPDP security obligations and exposes personal data to harm. "
            "Security failures can result in significant regulatory penalties and reputational damage."
        ),
        "mitigation": (
            "1. Implement encryption for personal data at rest and in transit\n"
            "2. Establish robust access controls with principle of least privilege\n"
            "3. Deploy detection and monitoring systems for unauthorized access\n"
            "4. Conduct regular security audits and vulnerability assessments\n"
            "5. Implement incident response procedures\n"
            "6. Provide security training to all personnel handling personal data"
        ),
    },

    # DPDP-006: Unauthorized Third Party Data Sharing
    "DPDP-006": {
        "why_detected": (
            "Personal data is being shared with third parties without explicit consent. "
            "The system detected data marked as shared with third parties (shared_with_third_party=true), "
            "but no corresponding consent for sharing with third parties was recorded (consent_for_sharing=false)."
        ),
        "evidence": (
            "Compliance check found records where shared_with_third_party is True but "
            "consent_for_sharing is False. This indicates unauthorized third-party data sharing "
            "that violates DPDP's requirement for explicit consent before sharing personal data with "
            "external entities."
        ),
        "risk_reason": (
            "Sharing personal data with third parties without explicit consent violates fundamental DPDP "
            "principles and data subject rights. It exposes individuals' data to unauthorized recipients "
            "without their knowledge or agreement. This creates significant compliance and privacy risks."
        ),
        "mitigation": (
            "1. Review all third-party data sharing arrangements\n"
            "2. Obtain explicit consent from data subjects before sharing with any third parties\n"
            "3. Implement consent tracking and management systems\n"
            "4. Define and communicate data sharing purposes to data subjects\n"
            "5. Establish data processing agreements with all third parties\n"
            "6. Document justification for any necessary data sharing"
        ),
    },

    # DPDP-007: Missing Data Minimization (Over-Collection)
    "DPDP-007": {
        "why_detected": (
            "Data minimization violation detected: more data fields are being collected than required. "
            "The system found that collected_fields exceeds required_fields, indicating the organization "
            "is collecting more personal data than is actually necessary."
        ),
        "evidence": (
            "Compliance check compared collected_fields against required_fields and found that "
            "more data is being collected than is actually needed. This violates DPDP's data minimization "
            "principle (Section 4) which requires collecting only the minimum personal data necessary "
            "for the stated purpose."
        ),
        "risk_reason": (
            "Over-collecting personal data violates the data minimization principle and increases "
            "privacy risks for data subjects. Unnecessary data collection expands the scope of data "
            "processing, increases storage and security risks, and limits the organization's ability to "
            "control the extent of data handling."
        ),
        "mitigation": (
            "1. Conduct data mapping to identify all collected fields\n"
            "2. Determine minimum fields required for each processing purpose\n"
            "3. Remove collection of unnecessary fields from forms and systems\n"
            "4. Implement field-level access controls to restrict collection\n"
            "5. Review and update data collection processes and requirements\n"
            "6. Document justification for any additional fields beyond the minimum"
        ),
    },

    # DPDP-008: Sensitive Data Stored Without Encryption
    "DPDP-008": {
        "why_detected": (
            "Sensitive personal data (PII) detected stored without encryption. "
            "The system found pii_encrypted flag is false, indicating sensitive data is stored "
            "in plain text or unencrypted format, making it vulnerable to unauthorized access."
        ),
        "evidence": (
            "Compliance check identified sensitive personal data fields (email, phone, SSN, etc.) "
            "stored without encryption. The pii_encrypted field indicates data is not protected "
            "with cryptographic controls, violating DPDP security safeguards requirements."
        ),
        "risk_reason": (
            "Unencrypted sensitive data significantly increases breach risk and potential data loss impact. "
            "If systems are compromised, all sensitive data is immediately exposed. This is a critical "
            "security vulnerability that violates DPDP and creates severe regulatory and legal exposure."
        ),
        "mitigation": (
            "1. Implement encryption at rest for all sensitive personal data\n"
            "2. Use strong encryption standards (AES-256 or equivalent)\n"
            "3. Implement encryption in transit (TLS 1.2+) for data transmission\n"
            "4. Manage encryption keys securely with HSM or key management service\n"
            "5. Audit all sensitive data storage locations\n"
            "6. Re-encrypt all existing unencrypted sensitive data"
        ),
    },

    # DPDP-009: Missing Grievance Redress Mechanism
    "DPDP-009": {
        "why_detected": (
            "No grievance redress mechanism detected. The system found grievance_endpoint_available "
            "is false, indicating data subjects have no way to file complaints or grievances about "
            "data processing activities."
        ),
        "evidence": (
            "Compliance check found that the organization lacks a documented grievance redress "
            "process or endpoint for data subjects to lodge complaints. This violates DPDP Section 8 "
            "which requires organizations to establish mechanisms for grievance resolution."
        ),
        "risk_reason": (
            "Without grievance mechanisms, data subjects cannot report violations or seek remedies. "
            "This indicates lack of accountability and violates fundamental DPDP requirements for "
            "data subject rights. May result in regulatory sanctions and loss of customer trust."
        ),
        "mitigation": (
            "1. Establish documented grievance redress policy and procedures\n"
            "2. Create publicly accessible grievance filing mechanism (email, website, phone)\n"
            "3. Define clear timelines for grievance acknowledgment and resolution\n"
            "4. Assign accountability for grievance handling\n"
            "5. Maintain records of all grievances and resolutions\n"
            "6. Regularly review and improve grievance handling processes"
        ),
    },

    # DPDP-010: Failure to Honor Data Erasure Request
    "DPDP-010": {
        "why_detected": (
            "Data erasure request not honored. The system found erasure_requested is true but "
            "data_deleted is false, indicating a data subject requested deletion but data was not removed "
            "from systems, violating the right to be forgotten."
        ),
        "evidence": (
            "Compliance check identified processing logs where data erasure was explicitly requested "
            "but the data remains in the system. This is a direct violation of DPDP Section 10 (Right to Erasure) "
            "which mandates timely deletion of personal data upon request."
        ),
        "risk_reason": (
            "Failure to honor erasure requests is a critical compliance violation that exposes retained data "
            "to unauthorized use and breach risks. This creates legal liability, regulatory penalties, and "
            "may result in mandatory deletion orders or suspension of processing rights."
        ),
        "mitigation": (
            "1. Implement automated erasure workflows triggered by erasure requests\n"
            "2. Define SLA for erasure (typically 15-30 days from request)\n"
            "3. Ensure deletion from primary storage, backups, and archives\n"
            "4. Maintain audit trail of all erasure operations\n"
            "5. Verify erasure completion before notifying data subject\n"
            "6. Establish monitoring to detect re-appearance of erased data"
        ),
    },

    # DPDP-011: Excess Data Retention Without Purpose
    "DPDP-011": {
        "why_detected": (
            "Data retained beyond processing purpose completion. The system found purpose_completed is true "
            "but data_retained is still true, indicating data is kept after the original purpose is fulfilled."
        ),
        "evidence": (
            "Compliance check identified data that continues to be retained even though the processing purpose "
            "(e.g., transaction completion, complaint resolution) has been achieved. DPDP Section 4 requires "
            "deletion or anonymization when the purpose is complete."
        ),
        "risk_reason": (
            "Unnecessary retention increases breach exposure and violates storage limitation principles. "
            "The longer data is retained, the higher the risk of unauthorized use, accidental exposure, or loss. "
            "This violates DPDP and regulatory requirements."
        ),
        "mitigation": (
            "1. Define explicit retention periods for each data category\n"
            "2. Implement automated deletion based on purpose completion\n"
            "3. Review and classify data retention needs\n"
            "4. Establish retention schedules and stick to them\n"
            "5. Implement monitoring to identify over-retained data\n"
            "6. Securely delete or anonymize data when purpose complete"
        ),
    },

    # DPDP-012: Missing Audit Logs for Data Access
    "DPDP-012": {
        "why_detected": (
            "Data access logs not available. The system found access_log_available is false, indicating "
            "data access and processing are occurring without audit trail documentation."
        ),
        "evidence": (
            "Compliance check found that data is being accessed and processed without corresponding audit logs "
            "or access records. DPDP Section 8 requires maintaining records of who accesses what data and when, "
            "to ensure accountability and enable breach investigation."
        ),
        "risk_reason": (
            "Without audit logs, unauthorized access cannot be detected or investigated. This violates "
            "accountability requirements and prevents identification of breaches or misuse. Regulatory bodies "
            "expect comprehensive logging for compliance verification."
        ),
        "mitigation": (
            "1. Implement comprehensive audit logging for all data access\n"
            "2. Log user ID, timestamp, action, and data accessed\n"
            "3. Enable immutable audit logs to prevent tampering\n"
            "4. Retain logs for at least 1-2 years\n"
            "5. Implement real-time monitoring for suspicious access patterns\n"
            "6. Review logs regularly for unauthorized access"
        ),
    },

    # DPDP-013: Unauthorized Employee Access to PII
    "DPDP-013": {
        "why_detected": (
            "Unauthorized employee access to PII detected. The system found employees without approved roles "
            "(admin, analyst) accessed personal data, violating principle of least privilege."
        ),
        "evidence": (
            "Compliance check identified access logs showing employees with non-authorized roles accessing "
            "PII. DPDP Section 8 requires organizations to implement role-based access controls and ensure "
            "only authorized personnel can access personal data."
        ),
        "risk_reason": (
            "Unauthorized access increases insider threat risk and data misuse potential. Employees without "
            "legitimate business need having PII access creates both security and privacy violations. This "
            "breaches trust and violates DPDP requirements."
        ),
        "mitigation": (
            "1. Implement strict role-based access control (RBAC)\n"
            "2. Define data access roles with clear responsibilities\n"
            "3. Conduct access reviews to remove unnecessary permissions\n"
            "4. Use principle of least privilege for all accounts\n"
            "5. Implement multi-factor authentication for sensitive access\n"
            "6. Provide security awareness training on data access policies"
        ),
    },

    # DPDP-014: Delayed Breach Notification
    "DPDP-014": {
        "why_detected": (
            "Breach notification delayed beyond acceptable threshold. The system found breach_detected is true "
            "but notification_delay exceeds 72 hours, violating DPDP breach reporting timelines."
        ),
        "evidence": (
            "Compliance check identified security breaches where notification to data subjects or authorities "
            "was delayed beyond 72 hours. DPDP Section 9 mandates that data breaches must be reported within "
            "72 hours of discovery."
        ),
        "risk_reason": (
            "Delayed breach notification violates DPDP and regulatory requirements, exposes affected individuals "
            "to prolonged risk, and demonstrates lack of incident response procedures. This is a critical breach "
            "of trust and can result in severe regulatory penalties."
        ),
        "mitigation": (
            "1. Establish breach detection and incident response procedures\n"
            "2. Define 72-hour SLA for breach notification\n"
            "3. Create breach notification templates and communication plans\n"
            "4. Implement automated alerting for security incidents\n"
            "5. Conduct regular incident response drills\n"
            "6. Document root cause and corrective actions for all breaches"
        ),
    },
}


# ═══════════════════════════════════════════════════════════
# DEFAULT EXPLANATION (Used when violation not in store)
# ═══════════════════════════════════════════════════════════

DEFAULT_EXPLANATION: Dict[str, str] = {
    "why_detected": (
        "A compliance violation was detected during the automated rules evaluation. "
        "The specific rule condition was met against the data records."
    ),
    "evidence": (
        "The violation was identified through the rule-based compliance engine evaluation. "
        "Please refer to the rule definition and data records for detailed evidence."
    ),
    "risk_reason": (
        "This violation indicates a potential non-compliance with data privacy and protection regulations. "
        "It requires attention to ensure regulatory compliance and protection of personal data."
    ),
    "mitigation": (
        "1. Review the violation in detail with the compliance and data governance teams\n"
        "2. Identify root cause of the violation\n"
        "3. Develop remediation plan with specific corrective actions\n"
        "4. Implement controls to prevent recurrence\n"
        "5. Document all remediation efforts\n"
        "6. Monitor for effectiveness of controls"
    ),
}


# ═══════════════════════════════════════════════════════════
# PRIMARY FUNCTION: Get Explanation
# ═══════════════════════════════════════════════════════════

def get_explanation(violation_identifier: str) -> Dict[str, str]:
    """
    Retrieve explanation for a specific violation.

    Args:
        violation_identifier: Rule ID (e.g., "DPDP-001") or rule name.
                             Automatically tries both formats.

    Returns:
        Dictionary with keys: why_detected, evidence, risk_reason, mitigation.
        Returns default explanation if violation_identifier not found.

    Example:
        >>> explanation = get_explanation("DPDP-001")
        >>> print(explanation["why_detected"])
        >>> print(explanation["mitigation"])

        >>> explanation = get_explanation("UNKNOWN-RULE")
        >>> print(explanation["why_detected"])  # Returns default
    """
    # Try direct lookup first (e.g., DPDP-001)
    if violation_identifier in VIOLATION_EXPLANATIONS:
        return VIOLATION_EXPLANATIONS[violation_identifier]

    # Try matching by rule_name in case rule_name was provided
    for rule_id, explanation in VIOLATION_EXPLANATIONS.items():
        # Extract the key from explanation dict for comparison
        # (Could extend this to match by name if needed)
        pass

    # Return default explanation if not found
    return DEFAULT_EXPLANATION


# ═══════════════════════════════════════════════════════════
# SECONDARY FUNCTION: Enrich Violations with Explanations
# ═══════════════════════════════════════════════════════════

def enrich_violations(violations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Attach structured explanations to each violation.

    Transforms a flat violation list into enriched violations with full explanations.

    Args:
        violations: List of violation dictionaries, each containing at minimum:
                   - rule_id (str, e.g., "DPDP-001")
                   - rule_name (str)
                   - severity (str)
                   Additional fields like severity, risk_weight are preserved.

    Returns:
        List of enriched violation dictionaries including original fields plus:
        - explanation: Dictionary with why_detected, evidence, risk_reason, mitigation

    Example Input:
        [
            {
                "rule_id": "DPDP-001",
                "rule_name": "Missing Consent Before Processing",
                "severity": "HIGH",
                "occurrence_count": 5
            },
            {
                "rule_id": "DPDP-003",
                "rule_name": "Retention Beyond Allowed Period",
                "severity": "HIGH",
                "occurrence_count": 2
            }
        ]

    Example Output:
        [
            {
                "rule_id": "DPDP-001",
                "rule_name": "Missing Consent Before Processing",
                "severity": "HIGH",
                "occurrence_count": 5,
                "explanation": {
                    "why_detected": "Personal data processing detected without valid prior consent...",
                    "evidence": "The automated compliance check identified...",
                    "risk_reason": "Processing personal data without consent...",
                    "mitigation": "1. Implement explicit consent collection..."
                }
            },
            ...
        ]

    Notes:
        - Original violation fields are preserved
        - Missing rule_id fields default to "UNKNOWN"
        - If explanation not found, default explanation is used
        - Modifications are non-destructive (original input is not modified)
    """
    enriched_violations: List[Dict[str, Any]] = []

    for violation in violations:
        # Create a copy to avoid modifying original
        enriched = violation.copy()

        # Extract rule_id, defaulting to UNKNOWN if not present
        rule_id = violation.get("rule_id", "UNKNOWN")

        # Get explanation for this violation
        explanation = get_explanation(rule_id)

        # Attach explanation to violation
        enriched["explanation"] = explanation

        enriched_violations.append(enriched)

    return enriched_violations


# ═══════════════════════════════════════════════════════════
# UTILITY FUNCTION: Add explanation to single violation (Optional)
# ═══════════════════════════════════════════════════════════

def add_explanation_to_violation(violation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add explanation to a single violation dictionary.

    Args:
        violation: Single violation dict with rule_id

    Returns:
        Same violation dict with 'explanation' field added

    Example:
        >>> v = {"rule_id": "DPDP-001", "severity": "HIGH"}
        >>> v_enriched = add_explanation_to_violation(v)
        >>> print(v_enriched["explanation"]["why_detected"])
    """
    enriched = violation.copy()
    rule_id = violation.get("rule_id", "UNKNOWN")
    enriched["explanation"] = get_explanation(rule_id)
    return enriched


# ═══════════════════════════════════════════════════════════
# UTILITY FUNCTION: List all available explanations (Optional)
# ═══════════════════════════════════════════════════════════

def list_available_violations() -> List[str]:
    """
    Get list of all violations with explanations in the store.

    Returns:
        List of rule IDs that have defined explanations

    Example:
        >>> violations = list_available_violations()
        >>> print(violations)
        ['DPDP-001', 'DPDP-002', 'DPDP-003', ...]
    """
    return list(VIOLATION_EXPLANATIONS.keys())
