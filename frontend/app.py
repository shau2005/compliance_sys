# frontend/app.py

import streamlit as st
import requests
import json


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
        st.metric("Violations", data['violation_count'])

    st.markdown("---")
    st.subheader("🚨 Violations Detected")

    if data['violation_count'] == 0:
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
            with st.expander(
                f"{icon} [{v['severity']}] {v['rule_name']}"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Rule ID:**     {v['rule_id']}")
                    st.write(f"**Section:**     {v['dpdp_section']}")
                    st.write(f"**Severity:**    {v['severity']}")
                with col2:
                    st.write(f"**Risk Weight:** {v['risk_weight']}")
                    st.write(f"**Reason:**      {v['reason']}")

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

# ── Sidebar ──────────────────────────────────────────
st.sidebar.title("Configuration")
api_url = st.sidebar.text_input("API URL", value="http://localhost:8000")

st.sidebar.markdown("---")
st.sidebar.markdown("**How to use:**")
st.sidebar.markdown("1. Choose analysis mode")
st.sidebar.markdown("2. Provide tenant data")
st.sidebar.markdown("3. Click Run Compliance Check")

# ── Mode Selection ───────────────────────────────────
mode = st.radio(
    "Select Analysis Mode",
    ["Known Tenant", "Upload New Files"],
    horizontal=True
)

st.markdown("---")

# ── MODE 1: Known Tenant ─────────────────────────────
if mode == "Known Tenant":
    st.subheader("📂 Known Tenant Analysis")

    tenant_id = st.selectbox(
        "Select Tenant",
        ["tenant_a", "tenant_b"],
        help="tenant_a = SafeFinance Ltd (Compliant)\n"
             "tenant_b = RiskyPay Inc (Non-Compliant)"
    )

    run = st.button("🔍 Run Compliance Check", type="primary")

    if run:
        with st.spinner(f"Analyzing {tenant_id}..."):
            try:
                response = requests.post(
                    f"{api_url}/analyze",
                    json={"tenant_id": tenant_id}
                )
                data = response.json()
            except Exception as e:
                st.error(f"Could not connect to API: {str(e)}")
                st.stop()

        if response.status_code != 200:
            st.error(f"API Error: {data.get('detail', 'Unknown error')}")
            st.stop()

        display_report(data)

# ── MODE 2: Upload New Files ─────────────────────────
else:
    st.subheader("📤 Upload New Tenant Files")
    st.info(
        "Upload 3 JSON files for an unseen tenant. "
        "The system will redact PII and run full compliance check."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        policies_file = st.file_uploader(
            "📋 policies.json",
            type=["json"],
            help="Company privacy policies and consent settings"
        )

    with col2:
        logs_file = st.file_uploader(
            "📝 logs.json",
            type=["json"],
            help="Access logs and activity records"
        )

    with col3:
        inventory_file = st.file_uploader(
            "🗄️ system_inventory.json",
            type=["json"],
            help="System components and data storage details"
        )

    run = st.button(
        "🔍 Run Compliance Check",
        type="primary",
        disabled=not (policies_file and logs_file and inventory_file)
    )

    if run:
        with st.spinner("Analyzing uploaded files..."):
            try:
                response = requests.post(
                    f"{api_url}/analyze/upload",
                    files={
                        "policies":  ("policies.json",
                                      policies_file.getvalue(),
                                      "application/json"),
                        "logs":      ("logs.json",
                                      logs_file.getvalue(),
                                      "application/json"),
                        "inventory": ("system_inventory.json",
                                      inventory_file.getvalue(),
                                      "application/json")
                    }
                )
                data = response.json()
            except Exception as e:
                st.error(f"Could not connect to API: {str(e)}")
                st.stop()

        if response.status_code != 200:
            st.error(f"API Error: {data.get('detail', 'Unknown error')}")
            st.stop()

        display_report(data)