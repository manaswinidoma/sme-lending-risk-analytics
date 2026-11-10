import plotly.graph_objects as go
import streamlit as st

from data import load_report
from ui import BLUE, GRID, ORANGE, TEXT_2, finding, kpi, style_fig

curve = load_report("rpt_survival_curve")
GROUP_COLORS = {"All companies": BLUE, "Trading companies": ORANGE}

# ---------- header ----------
st.title("When is a new company most at risk?")
st.markdown(
    "<div class='subtitle'>Chance of still being registered after each year, and the yearly chance "
    "of deregistering at each age, from the last 12 months of ASIC deregistrations.</div>",
    unsafe_allow_html=True,
)
st.write("")

scenarios = (curve[["scenario_order", "scenario"]].drop_duplicates()
             .sort_values("scenario_order")["scenario"].tolist())
scenario = st.radio(
    "Deregistrations included", scenarios, horizontal=True,
    help="The second option removes every deregistration ASIC processed in May–June 2026, "
         "a run of unusually large administrative batches. It is a deliberately harsh test: "
         "it also removes that period's normal deregistrations.",
)
sel = curve[curve["scenario"] == scenario]
other = curve[curve["scenario"] != scenario]


def by_group(df, group):
    return df[df["company_group"] == group].sort_values("survive_to_year")


all_c = by_group(sel, "All companies")
trd_c = by_group(sel, "Trading companies")
s_all = dict(zip(all_c["survive_to_year"], all_c["survival_pct"]))
s_trd = dict(zip(trd_c["survive_to_year"], trd_c["survival_pct"]))
all_bands = all_c.query("survive_to_year > 0")
peak = all_bands.loc[all_bands["yearly_dereg_prob_pct"].idxmax()]
peak_year = int(peak["survive_to_year"])

# ---------- tiles: survival to year N ----------
cols = st.columns(4)
for col, year in zip(cols, [1, 2, 3, 5]):
    kpi(col, f"Still registered after {year} year{'s' if year > 1 else ''}",
        f"{s_all[year]:.1f}%", f"trading companies {s_trd[year]:.1f}%")

st.write("")
left, right = st.columns(2, gap="large")

# ---------- survival curve ----------
with left:
    st.subheader("Survival curve")
    st.caption("Share of new companies still registered after each year.")
    fig = go.Figure()
    for group, color in GROUP_COLORS.items():
        g = by_group(sel, group)
        fig.add_scatter(
            x=g["survive_to_year"], y=g["survival_pct"], name=group, mode="lines+markers",
            line=dict(color=color, width=2.5), marker=dict(size=8, color=color),
            hovertemplate=f"<b>{group}</b><br>after %{{x}} years: %{{y:.1f}}% still registered<extra></extra>",
        )
        last = g.iloc[-1]
        fig.add_annotation(x=last["survive_to_year"], y=last["survival_pct"], text=f"{last['survival_pct']:.0f}%",
                           showarrow=False, xshift=24, yshift=9 if group == "All companies" else -9,
                           font=dict(color=color, size=13))
    fig.add_vrect(x0=peak_year - 1, x1=peak_year, fillcolor=ORANGE, opacity=0.08, line_width=0,
                  annotation_text="steepest drop", annotation_position="bottom left",
                  annotation_font=dict(color=TEXT_2, size=12))
    fig.update_xaxes(title="Years since registration", dtick=1, range=[-0.2, 5.5])
    fig.update_yaxes(title=None, ticksuffix="%", range=[0, 102])
    st.plotly_chart(style_fig(fig, 380), use_container_width=True)

# ---------- yearly chance by age ----------
with right:
    st.subheader("Yearly risk by age")
    st.caption("Out of companies at each age, the share deregistered within that year.")
    fig2 = go.Figure()
    for group, color in GROUP_COLORS.items():
        g = by_group(sel, group).query("survive_to_year > 0")
        fig2.add_bar(
            x=g["age_band_label"], y=g["yearly_dereg_prob_pct"], name=group,
            marker=dict(color=color, cornerradius=4),
            customdata=g[["company_years", "deregistrations"]],
            hovertemplate=f"<b>{group}</b> · age %{{x}}<br>%{{y:.2f}}% a year"
                          "<br>%{customdata[1]:,} deregistrations / %{customdata[0]:,.0f} company-years<extra></extra>",
        )
    fig2.update_xaxes(type="category", title="Company age")
    fig2.update_yaxes(title=None, ticksuffix="%", gridcolor=GRID)
    fig2.update_layout(barmode="group", bargroupgap=0.08)
    st.plotly_chart(style_fig(fig2, 380), use_container_width=True)

# ---------- what it means ----------
st.subheader("What this means")

before = all_bands.loc[all_bands["survive_to_year"] == peak["survive_to_year"] - 1, "yearly_dereg_prob_pct"]
ratio = peak["yearly_dereg_prob_pct"] / before.iloc[0] if not before.empty else None

other_all = by_group(other, "All companies").query("survive_to_year > 0")
other_peak = other_all.loc[other_all["yearly_dereg_prob_pct"].idxmax()]
s5_values = sorted([s_all[5], by_group(other, "All companies")["survival_pct"].iloc[-1]])
other_name = other["scenario"].iloc[0]

f1, f2, f3 = st.columns(3)
finding(
    f1, "The peak", f"Age {peak['age_band_label'].replace(' years', '')} is the riskiest year",
    f"<b>{peak['yearly_dereg_prob_pct']:.1f}%</b> of companies aged {peak['age_band_label']} deregister "
    f"within the year" + (f", about <b>{ratio:.0f}×</b> the year before." if ratio else "."),
    accent=ORANGE,
)
finding(
    f2, "Is it real?", "The peak survives the stress test",
    f"With the other view ({other_name.replace('-', '–')}), the riskiest age is still "
    f"<b>{other_peak['age_band_label']}</b> ({other_peak['yearly_dereg_prob_pct']:.1f}% a year). "
    f"5-year survival lies between <b>{s5_values[0]:.0f}%</b> and <b>{s5_values[1]:.0f}%</b>.",
    accent=BLUE,
)
finding(
    f3, "For lenders", "Tighten in year three, watch years 3–5",
    "Almost every company survives its first two years, so a clean two-year record says little. "
    "Apply tighter criteria to companies entering their <b>third year</b> and keep "
    "monitoring until year five, when the yearly risk settles.",
    accent=BLUE,
)

st.write("")
with st.expander("Numbers behind the charts"):
    table = sel[sel["survive_to_year"] > 0][[
        "company_group", "age_band_label", "company_years", "deregistrations",
        "yearly_dereg_prob_pct", "survival_pct"]].rename(columns={
            "company_group": "Group", "age_band_label": "Age", "company_years": "Company-years",
            "deregistrations": "Deregistrations", "yearly_dereg_prob_pct": "Yearly chance %",
            "survival_pct": "Still registered at end of band %"})
    st.dataframe(table, hide_index=True, use_container_width=True,
                 column_config={"Company-years": st.column_config.NumberColumn(format="%d")})
    st.caption("Method: yearly chance q = 1 − exp(−deregistrations ÷ company-years); "
               "survival = product of (1 − q) over the years.")
