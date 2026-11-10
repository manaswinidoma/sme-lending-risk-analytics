import streamlit as st

from data import DATA_SOURCE, load_report
from ui import inject_css, side_item, side_note

st.set_page_config(
    page_title="SME Lending Risk",
    page_icon="📉",
    layout="wide",
)
inject_css()

pages = [
    st.Page("views/overview.py", title="Overview", icon=":material/dashboard:", default=True),
    st.Page("views/when_risk.py", title="When is risk highest?", icon=":material/timeline:", url_path="when-risk"),
    st.Page("views/who_risk.py", title="Who is riskiest?", icon=":material/groups:", url_path="who-risk"),
    st.Page("views/risk_tiers.py", title="Risk tiers", icon=":material/rule:", url_path="risk-tiers"),
    st.Page("views/acn_lookup.py", title="Company lookup", icon=":material/search:", url_path="lookup"),
    st.Page("views/about.py", title="About & method", icon=":material/info:", url_path="about"),
]
nav = st.navigation(pages)

# ---------- sidebar: what this is, data freshness, how to read it ----------
metrics = load_report("rpt_key_metrics")
snapshot = metrics["snapshot_date"].iloc[0]
window_start = metrics["window_start_date"].iloc[0]

with st.sidebar:
    st.markdown("### SME Lending Risk")
side_note("Which new Australian businesses are riskiest to lend to?")

side_item("Data", "ASIC company register<br>(data.gov.au, public)")
side_item("Snapshot", f"{snapshot:%d %b %Y}")
side_item("Deregistrations counted", f"{window_start:%d %b %Y} – {snapshot:%d %b %Y}")
if DATA_SOURCE == "databricks":
    side_item("Refreshed", "Weekly · Wednesday 7am (Sydney)")
else:
    side_item("Version", "Public copy: fixed snapshot<br>(live version refreshes weekly)")

st.sidebar.divider()
st.sidebar.markdown("**How to read this**")
side_note(
    "<p>• Deregistration is a proxy for a business stopping, <b>not loan default</b>.</p>"
    "<p>• Rates use the last 12 months at each company age (period method).</p>"
    "<p>• Risk tiers are illustrative policy settings, not a credit model.</p>"
)
st.sidebar.divider()
side_note("<a href='https://github.com/manaswinidoma/sme-lending-risk-analytics' target='_blank'>Project on GitHub</a>")

nav.run()
