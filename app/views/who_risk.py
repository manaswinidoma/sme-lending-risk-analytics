import plotly.graph_objects as go
import streamlit as st

from data import load_report
from ui import BLUE, GREY, GRID, ORANGE, TEXT_2, finding, style_fig

seg = load_report("rpt_segment_risk").sort_values(["analysis_order", "group_order"])
FLAG_COLORS = {"Higher risk": ORANGE, "Around average": "#8f8d86", "Lower risk": BLUE}

# ---------- header ----------
st.title("Which companies carry the most risk?")
st.markdown(
    "<div class='subtitle'>Chance of deregistering within 5 years, compared on an age-adjusted basis: "
    "each group's own yearly rates at ages 0–5, so young and old groups are compared fairly.</div>",
    unsafe_allow_html=True,
)
st.write("")
st.info(
    "**Risk index** = a group's 5-year deregistration chance ÷ the benchmark's. "
    "**1.00 = average**, above **1.25 = higher risk**, below **0.80 = lower risk**. "
    "Groups without enough data in every age band (≥ 100 company-years and ≥ 10 deregistrations) get no index.",
    icon=":material/info:",
)


def risk_chart(df, height):
    """Horizontal bars of the risk index, coloured by flag, with the 'around average' band."""
    rows = df[df["is_reliable"] & ~df["is_benchmark"]].iloc[::-1]   # first group at the top
    fig = go.Figure()
    fig.add_vrect(x0=0.8, x1=1.25, fillcolor=GREY, opacity=0.18, line_width=0, layer="below")
    fig.add_vline(x=1, line=dict(color=TEXT_2, width=1, dash="dot"), layer="below")
    for flag, color in FLAG_COLORS.items():
        part = rows[rows["risk_flag"] == flag]   # empty traces still show in the legend
        fig.add_bar(
            y=part["group_name"], x=part["risk_index"], name=flag, orientation="h",
            marker=dict(color=color, cornerradius=4),
            text=part["risk_index"].map(lambda v: f"{v:.2f}"), textposition="outside",
            textfont=dict(color=TEXT_2),
            customdata=part[["dereg_within_5y_pct", "deregistrations_age_0_5", "company_years_age_0_5"]],
            hovertemplate="<b>%{y}</b><br>risk index %{x:.2f}"
                          "<br>%{customdata[0]:.1f}% deregister within 5 years"
                          "<br>%{customdata[1]:,} deregistrations / %{customdata[2]:,.0f} company-years<extra></extra>",
        )
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=rows["group_name"].tolist(),
                     showgrid=False)
    fig.update_xaxes(title="Risk index (1.00 = benchmark)", range=[0, max(2.3, rows["risk_index"].max() * 1.15)],
                     gridcolor=GRID)
    style_fig(fig, height)
    fig.update_layout(barmode="overlay", bargap=0.35, showlegend=False, margin=dict(t=10))
    return fig


def benchmark_line(df):
    b = df[df["is_benchmark"]].iloc[0]
    return f"Benchmark: **{b['group_name']}**, {b['dereg_within_5y_pct']:.1f}% deregister within 5 years."


swatch = "<span style='display:inline-block;width:11px;height:11px;border-radius:2px;background:{};margin:0 5px 0 14px'></span>"
legend = "".join(swatch.format(c) + f for f, c in FLAG_COLORS.items())
st.markdown(f"<div style='color:{TEXT_2};font-size:0.88rem;margin-left:-14px'>{legend}"
            f"<span style='margin-left:18px'>Shaded band = around average (0.80–1.25) · dotted line = benchmark</span></div>",
            unsafe_allow_html=True)

segments = seg[seg["analysis"] == "Borrower segment"]
signs = seg[seg["analysis"] == "Warning sign"]

left, right = st.columns(2, gap="large")
with left:
    st.subheader("Type of company")
    st.caption(benchmark_line(segments))
    st.plotly_chart(risk_chart(segments, 340), use_container_width=True)
    thin = segments[~segments["is_reliable"]]["group_name"].tolist()
    if thin:
        st.caption("Not enough data for an index: " + ", ".join(thin) + ".")

with right:
    st.subheader("Warning signs")
    st.caption("Within trading companies. " + benchmark_line(signs))
    st.plotly_chart(risk_chart(signs, 340), use_container_width=True)
    thin = signs[~signs["is_reliable"]]["group_name"].tolist()
    if thin:
        st.caption("Not enough data for an index: " + ", ".join(thin) + ".")

# ---------- what it means ----------
st.subheader("What this means")
g = seg.set_index("group_name")
reliable_segments = segments[segments["is_reliable"] & ~segments["is_benchmark"]]
lowest = reliable_segments.loc[reliable_segments["risk_index"].idxmin()]
num, trd = g.loc["Numbered (ACN in name)"], g.loc["All trading companies"]
abn, no_abn = g.loc["Has ABN"], g.loc["No ABN"]
ren = g.loc["Renamed"]

f1, f2, f3 = st.columns(3)
finding(
    f1, "Strongest warning sign", "A numbered name doubles the risk",
    f"<b>{num['dereg_within_5y_pct']:.0f}%</b> of trading companies named after their ACN deregister within "
    f"5 years, vs <b>{trd['dereg_within_5y_pct']:.0f}%</b> of all trading companies "
    f"(index <b>{num['risk_index']:.2f}</b>). Ask for extra evidence of trading.",
    accent=ORANGE,
)
finding(
    f2, "Lowest risk", f"{lowest['group_name']}s carry less risk",
    f"Risk index <b>{lowest['risk_index']:.2f}</b>: only <b>{lowest['dereg_within_5y_pct']:.0f}%</b> deregister "
    f"within 5 years. Keeping them in 'all companies' makes risk look lower than it is for "
    f"real trading businesses, so judge trading companies against their own benchmark.",
    accent=BLUE,
)
finding(
    f3, "Read with care", "Not every signal is a lending signal",
    f"Companies <b>with an ABN</b> deregister more ({abn['risk_index']:.2f}) than those without "
    f"({no_abn['risk_index']:.2f}), likely because dormant holding companies rarely close. "
    f"<b>Renamed</b> companies look safer ({ren['risk_index']:.2f}), but that is survivor bias: "
    f"only companies that lasted had time to rename.",
    accent=GREY,
)

st.write("")
with st.expander("Numbers behind the charts"):
    table = seg[["analysis", "group_name", "benchmark", "company_years_age_0_5", "deregistrations_age_0_5",
                 "dereg_within_5y_pct", "risk_index", "risk_flag"]].rename(columns={
        "analysis": "Analysis", "group_name": "Group", "benchmark": "Compared with",
        "company_years_age_0_5": "Company-years (age 0–5)", "deregistrations_age_0_5": "Deregistrations (age 0–5)",
        "dereg_within_5y_pct": "Deregister within 5 years %", "risk_index": "Risk index", "risk_flag": "Flag"})
    st.dataframe(table, hide_index=True, use_container_width=True,
                 column_config={"Company-years (age 0–5)": st.column_config.NumberColumn(format="%d")})
    st.caption("Method: 1 − S(5), where S(5) is the product of (1 − yearly chance) over ages 0–1 … 4–5; "
               "risk index = group ÷ benchmark.")
