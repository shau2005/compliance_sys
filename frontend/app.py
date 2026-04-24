# frontend/app.py

import streamlit as st
import requests
import json
import io


# ── Report Display Function ───────────────────────────
def display_report(data: dict):
    st.markdown("---")
    st.subheader("📊 Compliance Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Tenant", data['tenant_id'])
    with col2:
        st.metric("Risk Score", f"{data['risk_score']} / 100")
    with col3:
        tier_icons = {
            "COMPLIANT": "🟢",
            "LOW":       "🟡",
            "MEDIUM":    "🟠",
            "HIGH":      "🔴",
            "CRITICAL":  "🚨"
        }
        icon = tier_icons.get(data['risk_tier'], "⚪")
        st.metric("Risk Tier", f"{icon} {data['risk_tier']}")
    with col4:
        # Support both old and new field names for compatibility
        unique_rules = data.get('unique_rules_violated', data.get('violation_count', 0))
        st.metric("Unique Rules Violated", unique_rules)

    # Show total occurrences if available (new field)
    if 'total_violation_occurrences' in data:
        st.info(f"📊 **Total Violation Occurrences:** {data['total_violation_occurrences']} (across {data['unique_rules_violated']} rules)")

    st.markdown("---")
    st.subheader("🚨 Violations Detected")

    total_violations = data.get('total_violation_occurrences', data.get('violation_count', 0))
    if total_violations == 0:
        st.success("✅ Fully Compliant — No violations detected")
    else:
        severity_icons = {
            "CRITICAL": "🚨",
            "HIGH":     "🔴",
            "MEDIUM":   "🟠",
            "LOW":      "🟡"
        }

        for v in data['violations']:
            icon = severity_icons.get(v['severity'], "⚪")
            
            # Include occurrence count in the title if available
            occurrence_info = f" (×{v.get('occurrence_count', 1)})" if v.get('occurrence_count', 1) > 1 else ""
            
            with st.expander(
                f"{icon} [{v['severity']}] {v['rule_name']}{occurrence_info}",
                expanded=True  # Changed to True so violations are visible by default
            ):
                # SECTION 1: VIOLATION DETAILS
                st.markdown("### 📋 Violation Details")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Rule ID:**     {v['rule_id']}")
                    st.write(f"**Section:**     {v['dpdp_section']}")
                    st.write(f"**Severity:**    {v['severity']}")
                with col2:
                    st.write(f"**Risk Weight:** {v['risk_weight']}")
                    st.write(f"**Reason:**      {v['reason']}")
                with col3:
                    # Show new frequency data if available
                    if 'occurrence_count' in v:
                        st.write(f"**Occurrences:** {v['occurrence_count']}")
                    if 'contribution_to_score' in v:
                        st.write(f"**Score Contribution:** {v['contribution_to_score']:.2f}")
                
                # SECTION 2: EXPLAINABILITY (XAI) - NEW!
                if 'explanation' in v and v['explanation']:
                    st.markdown("---")
                    st.markdown("### Summary")
                    
                    explanation = v['explanation']
                    
                    # WHY DETECTED
                    st.markdown("####  Why Was This Detected?")
                    st.info(explanation.get('why_detected', 'No explanation available'))
                    
                    # EVIDENCE
                    st.markdown("####  Evidence")
                    st.write(explanation.get('evidence', 'No evidence details available'))
                    
                    # RISK REASON
                    st.markdown("####  Risk & Impact")
                    st.error(explanation.get('risk_reason', 'No risk details available'))
                    
                    # MITIGATION
                    st.markdown("####  How to Remediate")
                    mitigation = explanation.get('mitigation', 'No mitigation steps available')
                    st.success(mitigation)

    st.markdown("---")
    st.subheader("📥 Download Report")

    st.download_button(
        label     = "Download Full Report (JSON)",
        data      = json.dumps(data, indent=2),
        file_name = f"{data['tenant_id']}_compliance_report.json",
        mime      = "application/json"
    )


# ── Page config ──────────────────────────────────────
st.set_page_config(
    page_title = "DPDP Compliance Engine",
    page_icon  = "⚖️",
    layout     = "wide"
)

# ── Header ───────────────────────────────────────────
st.title("⚖️ DPDP Compliance Engine")
st.caption("AI-Powered FinTech Compliance & Regulatory Intelligence System")
st.markdown("---")

# ── Unknown Tenant Data Analysis ─────────────────────
st.subheader("📤 Unknown Tenant Data")
st.info("Upload 10 CSV files for an unseen tenant. The system will process and run full compliance check.")

# ── Tenant Name Input ────────────────────────────────
tenant_name = st.text_input("🏢 Tenant Name", help="Enter the tenant name", placeholder="e.g., MyFinTech Inc")
tenant_id_input = st.text_input(
    "🏷️ Tenant ID",
    help="Must exactly match tenant_id in uploaded CSV rows",
    placeholder="e.g., tenant_c"
)

# ── File Upload Fields ───────────────────────────────
st.markdown("### 📁 Upload Required Files (10 CSV Files)")

file_configs = [
    ("governance_config", "🏛️ Governance Configuration", "Input governance configuration file"),
    ("customer_master", "👥 Customer Master", "Input customer master file"),
    ("consent_records", "✅ Consent Records", "Input consent records file"),
    ("transaction_events", "💳 Transaction Events", "Input transaction events file"),
    ("access_logs", "📝 Access Logs", "Input access logs file"),
    ("data_lifecycle", "🔄 Data Lifecycle", "Input data lifecycle file"),
    ("security_events", "🔒 Security Events", "Input security events file"),
    ("dsar_requests", "🗂️ DSAR Requests", "Input DSAR requests file"),
    ("system_inventory", "🗄️ System Inventory", "Input system inventory file"),
    ("policies", "📋 Policies", "Input policies file"),
]

uploaded_files = {}

# Create 5 rows with 2 columns each
for i in range(0, len(file_configs), 2):
    col1, col2 = st.columns(2)
    
    # First file in the pair
    file_key, file_label, help_text = file_configs[i]
    with col1:
        uploaded_files[file_key] = st.file_uploader(
            file_label,
            type=["csv"],
            help=help_text,
            key=file_key
        )
    
    # Second file in the pair (if exists)
    if i + 1 < len(file_configs):
        file_key, file_label, help_text = file_configs[i + 1]
        with col2:
            uploaded_files[file_key] = st.file_uploader(
                file_label,
                type=["csv"],
                help=help_text,
                key=file_key
            )


# ── Run Compliance Check Button ──────────────────────
all_files_uploaded = (
    tenant_name and 
    tenant_id_input and
    all(uploaded_files[key] is not None for key in uploaded_files)
)

run = st.button(
    "🔍 Run Compliance Check",
    type="primary",
    disabled=not all_files_uploaded
)

if run:
    with st.spinner(f"Analyzing {tenant_name}..."):
        try:
            tenant_id = tenant_id_input.strip()
            
            # Prepare files for submission
            files_dict = {}
            for file_key, uploaded_file in uploaded_files.items():
                if uploaded_file is not None:
                    files_dict[file_key] = (uploaded_file.name, uploaded_file.getvalue(), "text/csv")
            
            # Submit to API
            response = requests.post(
                "http://localhost:8000/analyze/upload",
                files=files_dict,
                data={"tenant_id": tenant_id, "tenant_name": tenant_name}
            )
            data = response.json()
        except Exception as e:
            st.error(f"Could not connect to API: {str(e)}")
            st.stop()

    if response.status_code != 200:
        st.error(f"API Error: {data.get('detail', 'Unknown error')}")
        st.stop()

    display_report(data)