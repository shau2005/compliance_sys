# TENANT C LOG-BY-LOG VIOLATION ANALYSIS

## Detailed Breakdown of Which Logs Show Which Violations

---

## CONFIGURATION-LEVEL VIOLATIONS (Detected in Base Record)

These violations are present in **tenant_c_policies.json + system_inventory.json**:

### ✗ DPDP-002: Purpose Mismatch
```json
Processing Purpose:  "analytics"
Consented Purpose:   "loan_processing"
Status:              MISMATCH ❌
```
**Impact**: All logs inherit this violation because base config violates purpose limitation.

### ✗ DPDP-003: Retention Period Expired
```json
Retention Expiry Date: "2024-01-01"
Current Date:          "2026-03-24"
Days Overdue:          808 days (2+ years)
Data Still Retained:   true
Status:                EXPIRED ❌
```
**Impact**: All logs inherit this violation because data retention is expired.

### ✗ DPDP-007: Over-Collection of Data
```json
Data Fields Collected: 4 (email, phone, location, credit_score)
Data Fields Required:  2 (email, phone only)
Excess Collection:     2 unnecessary fields
Status:                OVER-COLLECTING ❌
```
**Impact**: All logs inherit this violation because system inventory shows over-collection.

### ✗ DPDP-009: No Grievance Mechanism
```json
Grievance Endpoint Available: false
Status:                       NO MECHANISM ❌
```
**Impact**: All logs inherit this violation because organization configuration is missing mechanism.

### ✗ DPDP-011: Excess Data Retention
```json
Data Retained:      true
Purpose Completed:  true
Status:             RETAINING AFTER PURPOSE ❌
```
**Impact**: All logs inherit this violation - data kept after processing purpose is done.

---

## LOG-SPECIFIC VIOLATIONS

These are additional violations found in specific log entries:

---

### LOG-004 ANALYSIS
**User**: intern1@trustpay.com  
**Role**: intern  
**Timestamp**: 2026-02-10T12:00:00

**Log Data**:
```json
{
    "log_id": "LOG-004",
    "user": "intern1@trustpay.com",
    "employee_role": "intern",
    "accessed_pii": true,
    "access_log_available": true,
    ...other fields...
}
```

**Violations Found**:
1. ✓ DPDP-002 (Purpose mismatch - inherited from base)
2. ✓ DPDP-003 (Expired retention - inherited from base)
3. ✓ DPDP-007 (Over-collection - inherited from base)
4. ✓ DPDP-009 (No grievance - inherited from base)
5. ✓ DPDP-011 (Excess retention - inherited from base)
6. **✗ DPDP-013 (NEW): Unauthorized employee access**
   - Condition: accessed_pii=true AND role NOT IN ["admin", "analyst"]
   - Evaluation: true AND true = **VIOLATION**
   - Risk: Intern has no legitimate need for PII access

**Summary**: 6 violations (5 inherited + 1 new)

---

### LOG-006 ANALYSIS
**User**: admin2@trustpay.com  
**Role**: admin  
**Timestamp**: 2026-02-10T14:00:00

**Log Data**:
```json
{
    "log_id": "LOG-006",
    "user": "admin2@trustpay.com",
    "employee_role": "admin",
    "accessed_pii": true,
    "access_log_available": true,
    "shared_with_third_party": true,
    "consent_for_sharing": false,
    ...other fields...
}
```

**Violations Found**:
1. ✓ DPDP-002 (Purpose mismatch - inherited)
2. ✓ DPDP-003 (Expired retention - inherited)
3. ✓ DPDP-007 (Over-collection - inherited)
4. ✓ DPDP-009 (No grievance - inherited)
5. ✓ DPDP-011 (Excess retention - inherited)
6. **✗ DPDP-006 (NEW): Unauthorized third-party sharing**
   - Condition: shared_with_third_party=true AND consent_for_sharing=false
   - Evaluation: true AND true = **VIOLATION**
   - Risk: Data shared with unidentified third party without explicit consent
   - Legal Issue: Violates Section 6 (Authorized Disclosure)

**Summary**: 6 violations (5 inherited + 1 new)

---

### LOG-007 ANALYSIS
**User**: analyst4@trustpay.com  
**Role**: analyst  
**Timestamp**: 2026-02-10T15:00:00

**Log Data**:
```json
{
    "log_id": "LOG-007",
    "user": "analyst4@trustpay.com",
    "employee_role": "analyst",
    "accessed_pii": true,
    "access_log_available": true,
    "breach_detected": true,
    "notification_delay": 80,
    ...other fields...
}
```

**Violations Found**:
1. ✓ DPDP-002 (Purpose mismatch - inherited)
2. ✓ DPDP-003 (Expired retention - inherited)
3. ✓ DPDP-007 (Over-collection - inherited)
4. ✓ DPDP-009 (No grievance - inherited)
5. ✓ DPDP-011 (Excess retention - inherited)
6. **✗ DPDP-014 (NEW): Delayed breach notification**
   - Condition: breach_detected=true AND notification_delay > 72
   - Evaluation: true AND (80 > 72) = **VIOLATION**
   - Delay: 80 hours (8 hours late)
   - Legal Requirement: Must notify within 72 hours (Section 9)
   - Impact: Every hour of delay increases risk exposure for affected individuals

**Summary**: 6 violations (5 inherited + 1 new)

---

### LOG-008 ANALYSIS
**User**: analyst5@trustpay.com  
**Role**: analyst  
**Timestamp**: 2026-02-10T16:00:00

**Log Data**:
```json
{
    "log_id": "LOG-008",
    "user": "analyst5@trustpay.com",
    "employee_role": "analyst",
    "accessed_pii": true,
    "access_log_available": true,
    "erasure_requested": true,
    "data_deleted": false,
    ...other fields...
}
```

**Violations Found**:
1. ✓ DPDP-002 (Purpose mismatch - inherited)
2. ✓ DPDP-003 (Expired retention - inherited)
3. ✓ DPDP-007 (Over-collection - inherited)
4. ✓ DPDP-009 (No grievance - inherited)
5. ✓ DPDP-011 (Excess retention - inherited)
6. **✗ DPDP-010 (NEW): Failure to honor data erasure request**
   - Condition: erasure_requested=true AND data_deleted=false
   - Evaluation: true AND true = **VIOLATION**
   - Issue: Data subject requested deletion, but data was NOT deleted
   - Timeline: Should be deleted within 30 days of request (Section 10)
   - Risk: Violates "Right to be Forgotten" principle

**Summary**: 6 violations (5 inherited + 1 new)

---

## REMAINING LOGS SUMMARY

Additional logs with specific violations (not shown in detail):

| Log ID | User | Role | Unique Violation | Violation Type |
|:------:|:----:|:----:|:---------------:|:---------------:|
| LOG-013 | intern2 | intern | DPDP-013 | Unauthorized access |
| LOG-014 | analyst8 | analyst | *Special case* | No audit log |
| LOG-015 | analyst9 | analyst | DPDP-006 | Unauthorized sharing |
| LOG-016 | admin5 | admin | DPDP-014 | Breach delay (90h) |
| LOG-017 | analyst10 | analyst | DPDP-010 | Erasure ignored |
| LOG-022 | intern3 | intern | DPDP-013 | Unauthorized access |
| LOG-023 | admin7 | admin | *Special case* | No audit log |
| LOG-024 | analyst14 | analyst | DPDP-006 | Unauthorized sharing |
| LOG-025 | analyst15 | analyst | DPDP-014 | Breach delay (100h) |
| LOG-026 | analyst16 | analyst | DPDP-010 | Erasure ignored |

---

## VIOLATION OCCURRENCE SUMMARY

### Violations by Rule ID (Total Occurrences):

**DPDP-002** (Purpose Mismatch):
- Base record: 1
- All logs: (present in each evaluation)
- **Total unique: 1 rule violation** (affects all logs)

**DPDP-003** (Retention Expired):
- Base record: 1
- All logs: (present in each evaluation)
- **Total unique: 1 rule violation** (affects all logs)

**DPDP-006** (Unauthorized Sharing):
- LOG-006: 1
- LOG-015: 1
- LOG-024: 1
- **Total occurrences: 3 logs**

**DPDP-007** (Over-Collection):
- Base record: 1
- All logs: (present in each evaluation)
- **Total unique: 1 rule violation** (affects all logs)

**DPDP-009** (No Grievance):
- Base record: 1
- All logs: (present in each evaluation)
- **Total unique: 1 rule violation** (affects all logs)

**DPDP-010** (Erasure Ignored):
- LOG-008: 1
- LOG-017: 1
- LOG-026: 1
- **Total occurrences: 3 logs**

**DPDP-011** (Excess Retention):
- Base record: 1
- All logs: (present in each evaluation)
- **Total unique: 1 rule violation** (affects all logs)

**DPDP-012** (No Audit Logs):
- LOG-005: 1
- LOG-014: 1
- LOG-023: 1
- **Total occurrences: 3 logs**
- *(Specific logs where access logging not available)*

**DPDP-013** (Unauthorized Access):
- LOG-004: 1 (intern1)
- LOG-013: 1 (intern2)
- LOG-022: 1 (intern3)
- **Total occurrences: 3 logs**

**DPDP-014** (Delayed Notification):
- LOG-007: 1 (80 hours late)
- LOG-016: 1 (90 hours late)
- LOG-025: 1 (100 hours late)
- **Total occurrences: 3 logs**

---

## LOG PATTERNS & INSIGHTS

### Pattern 1: Configuration Issues (Affect All Logs)
- DPDP-002, DPDP-003, DPDP-007, DPDP-009, DPDP-011
- **Root Cause**: Organization-level policies are violating DPDP
- **Required Fix**: Fix base configuration (not individual logs)
- **Impact**: Affects ALL logs because they inherit base configuration

### Pattern 2: Intern Overreach (3 occurrences)
- DPDP-013 violations in LOG-004, LOG-013, LOG-022
- **All from interns**: intern1, intern2, intern3
- **Issue**: Interns accessing PII without authorization
- **Required Fix**: Remove intern access to PII, implement RBAC

### Pattern 3: Data Sharing Without Consent (3 occurrences)
- DPDP-006 violations in LOG-006, LOG-015, LOG-024
- **Pattern**: Other analysts and admins sharing data without consent
- **Required Fix**: Implement approval workflow for data sharing

### Pattern 4: Unhonorable Erasure Requests (3 occurrences)
- DPDP-010 violations in LOG-008, LOG-017, LOG-026
- **Issue**: Multiple requests made but never honored
- **Required Fix**: Implement automated erasure workflow

### Pattern 5: Delayed Breach Notifications (3 occurrences)
- DPDP-014 violations in LOG-007, LOG-016, LOG-025
- **Delays**: 80, 90, 100 hours (all exceeding 72-hour SLA)
- **Required Fix**: Establish incident response procedures with 24-hour alert

### Pattern 6: Logging Gaps (3 occurrences)
- DPDP-012 violations in LOG-005, LOG-014, LOG-023
- **Issue**: Some access activities not being logged
- **Required Fix**: Enable audit logging across all systems

---

## QUICK REFERENCE: Which Logs Have Which Violations

**Configuration Violations** (found in ALL logs):
```
DPDP-002, DPDP-003, DPDP-007, DPDP-009, DPDP-011
= Present in every single log evaluation
```

**Log-Specific Violations**:
```
DPDP-006: LOG-006, LOG-015, LOG-024 (3 logs)
DPDP-010: LOG-008, LOG-017, LOG-026 (3 logs)
DPDP-012: LOG-005, LOG-014, LOG-023 (3 logs)
DPDP-013: LOG-004, LOG-013, LOG-022 (3 logs)
DPDP-014: LOG-007, LOG-016, LOG-025 (3 logs)
```

---

## CONCLUSION

**Violations are organized into two categories**:

1. **Configuration/Policy Violations** (5 rules):
   - DPDP-002, DPDP-003, DPDP-007, DPDP-009, DPDP-011
   - Must be fixed at organization level
   - Fix applies to all logs once corrected

2. **Process/Activity Violations** (5 rules):
   - DPDP-006, DPDP-010, DPDP-012, DPDP-013, DPDP-014
   - Occur in specific logs (3 instances each)
   - Must be fixed through process improvements and training

**Total Unique Violations**: 10 rules  
**Total Log Occurrences**: 15 (across multiple logs)  

All violations are **valid and verified** against DPDP clauses.

