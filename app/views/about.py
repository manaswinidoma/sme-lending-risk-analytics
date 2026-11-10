import streamlit as st

from data import load_report
from ui import TEXT_2, kpi

metrics = load_report("rpt_key_metrics").sort_values("metric_order").reset_index(drop=True)
snapshot = metrics["snapshot_date"].iloc[0]
window_start = metrics["window_start_date"].iloc[0]

st.title("About & method")
st.markdown(
    "<div class='subtitle'>Where the data comes from, how the numbers are calculated, "
    "and what they can and cannot tell you.</div>",
    unsafe_allow_html=True,
)
st.write("")

# ---------- the question ----------
st.subheader("The question")
st.markdown(
    "Lenders have little to go on when a business is new: no long trading record, often no financial "
    "statements and no repayment history. This project measures **how likely Australian companies are "
    "to be deregistered at each age**, by type of company and by warning signs a lender can see on an "
    "application, and turns that into **risk tiers and lending recommendations** for an SME credit team."
)

c1, c2, c3 = st.columns(3)
kpi(c1, "Data", "ASIC register", "Public company dataset, data.gov.au")
kpi(c2, "Snapshot used", f"{snapshot:%d %b %Y}", "Updated weekly by the pipeline")
kpi(c3, "Deregistrations counted", "Last 12 months", f"{window_start:%d %b %Y} – {snapshot:%d %b %Y}")

st.write("")

# ---------- data and pipeline ----------
st.subheader("Data and pipeline")
left, right = st.columns([3, 2], gap="large")
with left:
    st.markdown(
        "- **Source:** the [ASIC Company Dataset](https://data.gov.au/data/dataset/asic-companies), "
        "the public register of every Australian company, published weekly as a tab-delimited file "
        "(about 4.45 million rows: one per company name).\n"
        "- **What it contains:** every current company, companies deregistered in the **past 12 months**, "
        "and former names. Type, class, sub-class, status, registration and deregistration dates, ABN.\n"
        "- **What it doesn't contain:** address, industry, size, finances or loan outcomes, so risk cannot "
        "be split by state or industry.\n"
        "- **Pipeline:** a Databricks Job runs every **Wednesday 7am (Sydney)**: download → Bronze (raw "
        "snapshots) → Silver (cleaned, one row per company) → Gold (star schema) → report tables. "
        "Each layer has hard-stop checks (22 in Silver, 22 in Gold, 10 on the reports), so a failed "
        "check stops the job before bad numbers reach this app."
    )
with right:
    steps = [
        ("data.gov.au", "ASIC company file, weekly"),
        ("Bronze", "raw snapshots, all text"),
        ("Silver", "cleaned, one row per company"),
        ("Gold", "star schema: 5 dimensions + 2 facts"),
        ("Report tables", "6 summary tables (rpt_*)"),
        ("This app", "Streamlit"),
    ]
    boxes = []
    for i, (name, note) in enumerate(steps):
        last = i == len(steps) - 1
        style = "background:#2a78d6;color:#ffffff;border-color:#2a78d6" if last else ""
        note_color = "#e8f0fb" if last else TEXT_2
        boxes.append(
            f"<div class='kpi' style='min-height:0;padding:10px 14px;text-align:center;{style}'>"
            f"<div style='font-weight:650'>{name}</div>"
            f"<div style='font-size:0.8rem;color:{note_color}'>{note}</div></div>"
        )
    arrow = f"<div style='text-align:center;color:{TEXT_2};line-height:1.4'>↓</div>"
    st.markdown(arrow.join(boxes), unsafe_allow_html=True)

st.write("")

# ---------- method ----------
st.subheader("How the numbers are calculated")
st.markdown(
    "ASIC only publishes **the last 12 months** of deregistrations, so companies can't be followed from "
    "birth. Instead the app uses a **period life table**: the deregistration rate at each company age over "
    "the last 12 months, chained together into a survival curve. It answers: *if the last year's "
    "conditions continued, how many new companies would still be registered after N years?*"
)

with st.expander("1 · Exposure and yearly deregistration chance", expanded=True):
    st.markdown(
        "- **Company-years at risk (exposure):** for every company, the time it spent registered inside the "
        "12-month window, split at its registration anniversaries into age bands (0–1, 1–2, … 4–5, 5–10, 10+ years).\n"
        "- **Deregistrations:** each counted once, in the age band the company was in when it was deregistered.\n"
        "- **Rate** at an age = deregistrations ÷ company-years."
    )
    st.latex(r"q_{\text{age}} = 1 - e^{-\,\text{deregistrations} \,/\, \text{company-years}}")
    st.caption("q is the chance a company of that age is deregistered within a year.")

with st.expander("2 · Survival curve"):
    st.latex(r"S(N) = \prod_{\text{age}=0}^{N-1} \left(1 - q_{\text{age}}\right)")
    st.markdown(
        "S(N) is the share of new companies still registered after N years. "
        "A **sensitivity check** removes every deregistration ASIC processed in May–June 2026 (a run of "
        "unusually large administrative batches). It is deliberately harsh, because it also removes that "
        "period's normal deregistrations, so the true answer lies between the two curves."
    )

with st.expander("3 · Relative risk index (comparing groups fairly)"):
    st.latex(r"\text{risk index} = \frac{1 - S(5)_{\text{group}}}{1 - S(5)_{\text{benchmark}}}")
    st.markdown(
        "Each group's 5-year deregistration chance is built from **its own rates at each age**, so a group "
        "full of young companies is not penalised just for being young.\n\n"
        "- Benchmarks: **all companies** for company types, **all trading companies** for warning signs.\n"
        "- Above **1.25** = higher risk, below **0.80** = lower risk (illustrative cut-offs).\n"
        "- A group needs **≥ 100 company-years and ≥ 10 deregistrations in every age band 0–5**, otherwise "
        "it shows \"not enough data\"."
    )

with st.expander("4 · Risk tiers and the company lookup"):
    st.markdown(
        "- **Profiles:** trading companies split by **age band × numbered or named × ABN held** (28 profiles).\n"
        "- **Multiple:** the profile's yearly rate ÷ the trading-company average rate.\n"
        "- **95% interval** so that small profiles aren't over-called:"
    )
    st.latex(r"\text{rate} \times e^{\pm 1.96/\sqrt{\text{deregistrations}}}")
    st.markdown(
        "| Tier | Rule | Suggested action |\n|---|---|---|\n"
        "| High | lower bound of the multiple above 2× | Decline or refer to senior credit |\n"
        "| Elevated | lower bound above 1.25× | Extra checks, tighter terms |\n"
        "| Standard | otherwise | Standard criteria |\n"
        "| Low | upper bound below 0.8× | Standard criteria, faster approval |\n"
        "| Insufficient data | < 100 company-years or < 10 deregistrations | Manual assessment |\n\n"
        "**Red-flag override:** a company in strike-off or external administration is *Decline / refer* "
        "whatever its profile.\n\n"
        "**Lift** checks that the tiers work: a tier's share of deregistrations ÷ its share of company-years. "
        "Above 1 means the tier holds more than its fair share of deregistrations."
    )

st.write("")

# ---------- definitions ----------
st.subheader("Definitions")
st.markdown(
    "| Term | Meaning |\n|---|---|\n"
    "| **Deregistered** | Removed from the ASIC register (status DRGD). Used as a proxy for a business stopping. |\n"
    "| **Active** | Still on the register: registered, strike-off in progress, external administration or not active. |\n"
    "| **Red flag (distressed)** | Strike-off action in progress (SOFF) or external administration (EXAD). |\n"
    "| **Trading company** | Australian proprietary company not otherwise classified (sub-class PROP, plus EXPT): the typical small-business borrower. |\n"
    "| **Super trustee** | Proprietary company acting as a superannuation trustee (sub-class PSTC). |\n"
    "| **Not-for-profit** | Non-profit public companies (sub-classes ULSN, PNPC, NLTD). |\n"
    "| **Numbered company** | A company whose own ACN appears in its name (e.g. *123 456 789 PTY LTD*). |\n"
    "| **ABN held** | An ABN is recorded against the company on the ASIC register (not a check that it is active). |\n"
    "| **Company age** | Full years since registration, counted at the snapshot (or at deregistration). |"
)

st.write("")

# ---------- caveats ----------
st.subheader("Read with care")
st.markdown(
    f"""
<div class='finding' style='--accent:#eb6834;min-height:0'><div class='finding-body'>
<p>• <b>Deregistration is not loan default.</b> Companies also close voluntarily, merge or restructure; a lender's own repayment data would be needed to measure default.</p>
<p>• <b>Period assumption.</b> Rates describe the last 12 months; if conditions change, so will the risk. Deregistration dates are ASIC processing dates, which arrive in batches.</p>
<p>• <b>Risk of similar companies, not a prediction.</b> A tier describes how companies with the same profile behaved, not what one company will do.</p>
<p>• <b>Survivor effects.</b> Name changes and ABNs are observed at the snapshot, so companies that lasted longer had more time to rename or register an ABN.</p>
<p>• <b>Illustrative policy settings.</b> Tier cut-offs and actions are examples for discussion, not a validated credit model.</p>
<p style='margin-bottom:0'>• <b>Known data gaps.</b> a handful of companies have no registration date (age unknown); code labels for CCIV and WHSL are inferred because they are not in the ASIC help file.</p>
</div></div>
""",
    unsafe_allow_html=True,
)

st.write("")
st.markdown(
    f"<div style='color:{TEXT_2};font-size:0.9rem'>Built by <b>Manaswini Doma</b> with Databricks "
    "(Delta Lake, Unity Catalog, PySpark, Spark SQL, Jobs) and Streamlit. "
    "Data: ASIC Company Dataset, Australian Securities &amp; Investments Commission, via data.gov.au. · "
    "<a href='https://github.com/manaswinidoma/sme-lending-risk-analytics' target='_blank'>Code on GitHub</a> · "
    "<a href='https://www.linkedin.com/in/domamanaswini/' target='_blank'>LinkedIn</a></div>",
    unsafe_allow_html=True,
)
