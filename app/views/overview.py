import plotly.graph_objects as go
import streamlit as st

from data import load_report
from ui import BLUE, GREY, GRID, ORANGE, TEXT_2, finding, kpi, style_fig

# ---------- data ----------
metrics = load_report("rpt_key_metrics").sort_values("metric_order").reset_index(drop=True)
monthly = load_report("rpt_monthly_deregistrations").sort_values("month_start_date").reset_index(drop=True)
survival = load_report("rpt_survival_curve")
segments = load_report("rpt_segment_risk")
profiles = load_report("rpt_profile_risk")

m = dict(zip(range(1, len(metrics) + 1), metrics["metric_value"]))
# metric order: 1 total · 2 active · 3 distressed · 4 distress share · 5 deregistered 12m ·
# 6 company-years · 7 yearly probability · 8 ABN % · 9 renamed % · 10 numbered % · 11 median age

# ---------- header ----------
st.title("Which new businesses are riskiest to lend to?")
st.markdown(
    "<div class='subtitle'>How likely Australian companies are to be deregistered, by age, type "
    "and warning signs, and what that means for lending criteria.</div>",
    unsafe_allow_html=True,
)
st.write("")

# ---------- headline tiles ----------
c1, c2, c3, c4 = st.columns(4)
kpi(c1, "Active companies", f"{m[2]:,.0f}", f"of {m[1]:,.0f} on the register")
kpi(c2, "Deregistered, last 12 months", f"{m[5]:,.0f}", f"about 1 in {round(100 / m[7])} companies a year")
kpi(c3, "Yearly deregistration chance", f"{m[7]:.2f}%", "all companies, all ages")
kpi(c4, "Strike-off or administration", f"{m[3]:,.0f}", f"{m[4]:.2f}% of active · red flag")

st.write("")
st.subheader("Three things a lender should know")

# Finding 1: survival curve (all companies, all deregistrations)
curve = survival[(survival["company_group"] == "All companies") & (survival["scenario_order"] == 1)]
s = dict(zip(curve["survive_to_year"], curve["survival_pct"]))
q3 = curve.loc[curve["survive_to_year"] == 3, "yearly_dereg_prob_pct"].iloc[0]
q2 = curve.loc[curve["survive_to_year"] == 2, "yearly_dereg_prob_pct"].iloc[0]

# Finding 2: numbered trading companies vs all trading companies
seg = segments.set_index("group_name")
numbered = seg.loc["Numbered (ACN in name)"]
trading_all = seg.loc["All trading companies"]

# Finding 3: High + Elevated tiers
tier_order = ["High", "Elevated", "Standard", "Low"]
tiers = (profiles.groupby("risk_tier")[["pct_of_company_years", "pct_of_deregistrations"]].sum()
         .reindex([t for t in tier_order if t in profiles["risk_tier"].unique()]))
watch = tiers.loc[["High", "Elevated"]].sum()
high_lift = profiles.loc[profiles["risk_tier"] == "High", "tier_lift"].max()

f1, f2, f3 = st.columns(3)
finding(
    f1, "When", "Year three is the danger zone",
    f"A company aged 2–3 has a <b>{q3:.1f}%</b> chance of deregistering that year, "
    f"about <b>{q3 / q2:.0f}×</b> the year before. Only <b>{s[5]:.0f}%</b> of new companies "
    f"are still registered after 5 years.",
    accent=ORANGE,
)
finding(
    f2, "Who", "A numbered name doubles the risk",
    f"Trading companies named after their ACN: <b>{numbered['dereg_within_5y_pct']:.0f}%</b> "
    f"deregister within 5 years, vs <b>{trading_all['dereg_within_5y_pct']:.0f}%</b> for all trading "
    f"companies (risk index <b>{numbered['risk_index']:.2f}</b>).",
    accent=ORANGE,
)
finding(
    f3, "Where", "Risk tiers find the risk early",
    f"High and Elevated profiles hold <b>{watch['pct_of_company_years']:.0f}%</b> of trading-company "
    f"exposure but <b>{watch['pct_of_deregistrations']:.0f}%</b> of deregistrations. The High tier "
    f"deregisters at <b>{high_lift:.1f}×</b> its share.",
    accent=BLUE,
)

st.write("")
left, right = st.columns([3, 2], gap="large")

# ---------- monthly deregistrations ----------
with left:
    st.subheader("Deregistrations per month")
    st.caption("ASIC processing dates. Orange = large administrative batches.")

    def month_type(row):
        if row["is_partial_month"]:
            return "Partial month"
        if row["year_month"] in ("2026-05", "2026-06"):
            return "May–Jun 2026 batch"
        return "Regular month"

    monthly["label"] = monthly["month_start_date"].map(lambda d: d.strftime("%b<br>%y"))
    monthly["type"] = monthly.apply(month_type, axis=1)
    colors = {"Regular month": BLUE, "May–Jun 2026 batch": ORANGE, "Partial month": GREY}

    fig = go.Figure()
    for name, color in colors.items():
        part = monthly[monthly["type"] == name]
        if part.empty:
            continue
        fig.add_bar(
            x=part["label"], y=part["deregistrations"], name=name,
            marker=dict(color=color, cornerradius=4),
            customdata=part[["trading_companies", "other_segments"]],
            hovertemplate="<b>%{x}</b><br>%{y:,} deregistrations"
                          "<br>Trading: %{customdata[0]:,}<br>Other: %{customdata[1]:,}<extra></extra>",
        )
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=monthly["label"].tolist())
    fig.update_yaxes(title=None, tickformat=",")
    typical = monthly.loc[monthly["type"] == "Regular month", "deregistrations"].median()
    fig.add_hline(y=typical, line=dict(color=TEXT_2, dash="dot", width=1),
                  annotation_text=f"typical ≈ {typical:,.0f}", annotation_position="top left")
    st.plotly_chart(style_fig(fig, 360), use_container_width=True)

# ---------- risk tiers at a glance ----------
with right:
    st.subheader("Risk tiers vs outcomes")
    st.caption("Trading companies: share of exposure vs share of deregistrations.")
    fig2 = go.Figure()
    fig2.add_bar(y=tiers.index, x=tiers["pct_of_company_years"], name="Share of exposure",
                 orientation="h", marker=dict(color=BLUE, cornerradius=4),
                 hovertemplate="%{y}: %{x:.1f}% of company-years<extra></extra>")
    fig2.add_bar(y=tiers.index, x=tiers["pct_of_deregistrations"], name="Share of deregistrations",
                 orientation="h", marker=dict(color=ORANGE, cornerradius=4),
                 hovertemplate="%{y}: %{x:.1f}% of deregistrations<extra></extra>")
    fig2.update_yaxes(autorange="reversed", showgrid=False)
    fig2.update_xaxes(ticksuffix="%", gridcolor=GRID, showgrid=True)
    fig2.update_layout(barmode="group", bargroupgap=0.08)
    st.plotly_chart(style_fig(fig2, 360), use_container_width=True)

with st.expander("All headline metrics"):
    def fmt(value, unit):
        if unit == "percent":
            return f"{value:.2f}%"
        if unit == "years":
            return f"{value:g} years"
        return f"{value:,.0f}"

    table = metrics.assign(value=[fmt(v, u) for v, u in zip(metrics["metric_value"], metrics["unit"])])
    st.dataframe(table[["metric_name", "value"]].rename(columns={"metric_name": "Metric", "value": "Value"}),
                 hide_index=True, use_container_width=True)
