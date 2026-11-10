import plotly.graph_objects as go
import streamlit as st

from data import lending_tier_counts, load_report
from ui import BLUE, GRID, ORANGE, TEXT_2, TIER_ACTIONS as ACTIONS, TIER_COLORS, finding, style_fig

prof = load_report("rpt_profile_risk")
counts = lending_tier_counts()

TIERS = ["High", "Elevated", "Standard", "Low"]

# ---------- header ----------
st.title("Where should lending criteria be tightened or relaxed?")
st.markdown(
    "<div class='subtitle'>Trading-company borrower profiles (company age × numbered or named × ABN held), "
    "tiered by how their yearly deregistration rate compares with the trading-company average.</div>",
    unsafe_allow_html=True,
)
st.write("")

avg_rate = prof["trading_avg_rate_pct"].iloc[0]
st.info(
    f"**Tier rules** (illustrative policy settings): multiple of the trading-company average rate "
    f"({avg_rate:.2f}% a year), using the 95% confidence interval so small profiles are not over-called. "
    "**High**: lower bound above 2× · **Elevated**: lower bound above 1.25× · "
    "**Low**: upper bound below 0.8× · otherwise **Standard**. "
    "**Red flag override**: any company in strike-off or external administration → decline or refer.",
    icon=":material/rule:",
)

# ---------- tier tiles ----------
tier_sum = (prof.groupby("risk_tier")
            .agg(profiles=("risk_tier", "size"), active=("active_companies", "sum"),
                 pct_active=("pct_of_active_companies", "sum"), lift=("tier_lift", "max"))
            .reindex(TIERS))
cols = st.columns(4)
for col, tier in zip(cols, TIERS):
    r = tier_sum.loc[tier]
    col.markdown(
        f"<div class='kpi' style='border-top:5px solid {TIER_COLORS[tier]}'>"
        f"<div class='kpi-label'>{tier} · {int(r['profiles'])} profiles</div>"
        f"<div class='kpi-value'>{r['active']:,.0f}</div>"
        f"<div class='kpi-note'>{r['pct_active']:.1f}% of active trading companies · lift {r['lift']:.2f}×</div>"
        f"<div class='kpi-note' style='color:#0b0b0b;font-weight:600'>{ACTIONS[tier]}</div></div>",
        unsafe_allow_html=True,
    )

st.write("")
left, right = st.columns([3, 2], gap="large")

# ---------- profile map ----------
with left:
    st.subheader("Profile map")
    st.caption("Each cell is one borrower profile: multiple of the average yearly rate, coloured by tier.")
    prof["profile"] = prof["name_type"] + " · " + prof["abn_held"].str.replace("Has ABN", "ABN").str.replace("No ABN", "no ABN")
    col_order = ["Named · ABN", "Named · no ABN", "Numbered · ABN", "Numbered · no ABN"]
    rows = prof.sort_values("age_band_key")["age_band_label"].unique().tolist()
    tier_codes = {t: i for i, t in enumerate(["Low", "Standard", "Elevated", "High", "Insufficient data"])}
    grid = prof.pivot(index="age_band_label", columns="profile", values="risk_tier").reindex(index=rows, columns=col_order)
    mult = prof.pivot(index="age_band_label", columns="profile", values="x_trading_average").reindex(index=rows, columns=col_order)
    prob = prof.pivot(index="age_band_label", columns="profile", values="yearly_dereg_prob_pct").reindex(index=rows, columns=col_order)
    active = prof.pivot(index="age_band_label", columns="profile", values="active_companies").reindex(index=rows, columns=col_order)
    z = grid.apply(lambda c: c.map(tier_codes)).values
    n = len(tier_codes)
    scale = []
    for t, i in tier_codes.items():
        scale += [[i / n, TIER_COLORS[t]], [(i + 1) / n, TIER_COLORS[t]]]
    text = mult.apply(lambda c: c.map(lambda v: f"{v:.1f}×" if v == v else "")).values
    custom = list(zip(grid.values.tolist(), prob.values.tolist(), active.values.tolist()))
    custom = [[[g, p, a] for g, p, a in zip(*row)] for row in custom]
    fig = go.Figure(go.Heatmap(
        z=z, x=col_order, y=rows, zmin=0, zmax=n, colorscale=scale, showscale=False,
        text=text, texttemplate="%{text}", textfont=dict(color="#0b0b0b", size=13),
        xgap=3, ygap=3, customdata=custom,
        hovertemplate="<b>%{y} · %{x}</b><br>Tier: %{customdata[0]}<br>%{text} the average rate"
                      "<br>%{customdata[1]:.1f}% a year<br>%{customdata[2]:,} active companies<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", title="Company age", showgrid=False)
    fig.update_xaxes(side="top", showgrid=False)
    st.plotly_chart(style_fig(fig, 420), use_container_width=True)

# ---------- validation: lift ----------
with right:
    st.subheader("Do the tiers work?")
    st.caption("Share of exposure vs share of deregistrations. Lift = deregistrations share ÷ exposure share.")
    shares = prof.groupby("risk_tier")[["pct_of_company_years", "pct_of_deregistrations"]].sum().reindex(TIERS)
    fig2 = go.Figure()
    fig2.add_bar(y=shares.index, x=shares["pct_of_company_years"], name="Share of exposure", orientation="h",
                 marker=dict(color=BLUE, cornerradius=4), hovertemplate="%{y}: %{x:.1f}% of company-years<extra></extra>")
    fig2.add_bar(y=shares.index, x=shares["pct_of_deregistrations"], name="Share of deregistrations", orientation="h",
                 marker=dict(color=ORANGE, cornerradius=4), hovertemplate="%{y}: %{x:.1f}% of deregistrations<extra></extra>")
    for tier in TIERS:
        fig2.add_annotation(x=max(shares.loc[tier]) + 2, y=tier, text=f"lift {tier_sum.loc[tier, 'lift']:.2f}×",
                            showarrow=False, xanchor="left", font=dict(color=TEXT_2, size=12))
    fig2.update_yaxes(autorange="reversed", showgrid=False)
    fig2.update_xaxes(ticksuffix="%", gridcolor=GRID, range=[0, shares.values.max() * 1.35])
    fig2.update_layout(barmode="group", bargroupgap=0.08)
    st.plotly_chart(style_fig(fig2, 420), use_container_width=True)

# ---------- red flags + takeaways ----------
st.subheader("What this means")
trading = counts[counts["is_trading"]]
flags = trading[trading["lending_tier"].str.startswith("Decline")]
flag_total = int(flags["companies"].sum())
flag_split = " · ".join(f"{r['red_flag']}: <b>{int(r['companies']):,}</b>" for _, r in flags.sort_values("companies", ascending=False).iterrows())
watch = shares.loc[["High", "Elevated"]].sum()
top = prof[prof["risk_tier"] == "High"].sort_values("x_trading_average", ascending=False).iloc[0]

f1, f2, f3 = st.columns(3)
finding(
    f1, "Tighten", "High and Elevated: small groups, outsized risk",
    f"These profiles hold <b>{watch['pct_of_company_years']:.0f}%</b> of exposure but "
    f"<b>{watch['pct_of_deregistrations']:.0f}%</b> of deregistrations. The riskiest profile, "
    f"<b>{top['name_type'].lower()} companies aged {top['age_band_label']} "
    f"{'with' if top['abn_held'] == 'Has ABN' else 'without'} an ABN</b>, "
    f"deregisters at <b>{top['x_trading_average']:.1f}×</b> the average rate.",
    accent=ORANGE,
)
finding(
    f2, "Relax", "Low tier: room for lighter checks",
    f"Low profiles are <b>{tier_sum.loc['Low', 'pct_active']:.0f}%</b> of active trading companies with a lift of "
    f"<b>{tier_sum.loc['Low', 'lift']:.2f}×</b>: candidates for faster approval or lighter documentation.",
    accent=BLUE,
)
finding(
    f3, "Override", f"{flag_total:,} trading companies carry a red flag",
    f"{flag_split}. Whatever their profile, these should be declined or referred, "
    "and ASIC status should be checked again during the loan.",
    accent="#c9471a",
)

st.write("")
with st.expander("All 28 profiles"):
    table = prof.sort_values(["tier_order", "x_trading_average"], ascending=[False, False])[[
        "risk_tier", "age_band_label", "name_type", "abn_held", "active_companies", "company_years",
        "deregistrations", "yearly_dereg_prob_pct", "x_trading_average", "x_low_95", "x_high_95"]].rename(columns={
            "risk_tier": "Tier", "age_band_label": "Age", "name_type": "Name", "abn_held": "ABN",
            "active_companies": "Active companies", "company_years": "Company-years",
            "deregistrations": "Deregistrations", "yearly_dereg_prob_pct": "Yearly chance %",
            "x_trading_average": "× average", "x_low_95": "× low (95%)", "x_high_95": "× high (95%)"})
    st.dataframe(table, hide_index=True, use_container_width=True,
                 column_config={"Company-years": st.column_config.NumberColumn(format="%d")})
    st.caption("95% interval ≈ rate × e^(±1.96/√deregistrations). Profiles with < 100 company-years or "
               "< 10 deregistrations are 'Insufficient data'.")
