"""Shared look and feel (light theme): colours, CSS, KPI tiles, finding cards, chart styling."""
from html import escape

import streamlit as st

# Validated light-mode palette (blue / orange pass colour-blind and contrast checks on white)
BLUE = "#2a78d6"
ORANGE = "#eb6834"
GREY = "#b4b2a9"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e6e4df"
CARD = "#ffffff"

# Lending tiers (ordinal: dark orange = riskiest, blue = lowest risk)
TIER_COLORS = {
    "High": "#c9471a", "Elevated": "#f2a07b", "Standard": "#dcdad3", "Low": "#7fb0ea",
    "Insufficient data": "#f3f2ef",
    "Decline / refer (red flag)": "#c9471a", "Deregistered": "#8f8d86",
    "Out of scope (not a trading company)": "#dcdad3", "Excluded": "#dcdad3",
}
TIER_ACTIONS = {
    "High": "Decline or refer to senior credit",
    "Elevated": "Extra checks, tighter terms",
    "Standard": "Standard criteria",
    "Low": "Standard criteria, faster approval",
    "Insufficient data": "Manual assessment (not enough data for this profile)",
    "Decline / refer (red flag)": "Decline or refer: company is in strike-off or external administration",
    "Deregistered": "Not lendable: company is no longer registered",
    "Out of scope (not a trading company)": "Outside this model: assess with the relevant policy",
    "Excluded": "Outside this model",
}

CSS = f"""
<style>
.block-container {{ padding-top: 2.2rem; padding-bottom: 1.5rem; max-width: 1280px; }}
section[data-testid="stSidebar"] {{ border-right: 1px solid {GRID}; }}
h1 {{ font-size: 2.1rem !important; }}
.kpi {{ background:{CARD}; border:1px solid {GRID}; border-radius:12px; box-shadow:0 1px 2px rgba(0,0,0,.04);
        padding:16px 18px; min-height:128px; }}
.kpi-label {{ font-size:0.85rem; color:{TEXT_2}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.kpi-value {{ font-size:1.9rem; font-weight:650; color:{TEXT}; line-height:1.15; margin-top:6px; }}
.kpi-note  {{ font-size:0.8rem; color:{TEXT_2}; margin-top:6px; }}
.finding {{ background:{CARD}; border:1px solid {GRID}; border-left:5px solid var(--accent);
            border-radius:12px; padding:16px 18px; min-height:190px; box-shadow:0 1px 2px rgba(0,0,0,.04); }}
.finding-kicker {{ font-size:0.75rem; text-transform:uppercase; letter-spacing:.06em; color:{TEXT_2}; }}
.finding-title {{ font-size:1.08rem; font-weight:650; color:{TEXT}; margin:4px 0 6px; }}
.finding-body {{ font-size:0.92rem; color:{TEXT_2}; }}
.finding-body b {{ color:{TEXT}; }}
.subtitle {{ color:{TEXT_2}; font-size:1rem; margin-top:-0.6rem; }}
.kpi table, .kpi tr, .kpi td {{ border:none !important; background:transparent !important; }}
.kpi td {{ font-size:0.92rem; vertical-align:top; }}
.side-label {{ font-size:0.72rem; text-transform:uppercase; letter-spacing:.06em; color:{TEXT_2}; margin-top:0.8rem; }}
.side-value {{ font-size:0.95rem; color:{TEXT}; }}
.side-note {{ font-size:0.88rem; color:{TEXT_2}; line-height:1.5; }}
.side-note b {{ color:{TEXT}; }}
.side-note p {{ margin:0 0 0.6rem 0; }}
.side-note a {{ color:{BLUE}; }}
.kicker {{ font-size:0.75rem; text-transform:uppercase; letter-spacing:.06em; color:{TEXT_2}; }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def kpi(col, label, value, note=""):
    col.markdown(
        f"<div class='kpi'><div class='kpi-label'>{escape(label)}</div>"
        f"<div class='kpi-value'>{escape(value)}</div>"
        f"<div class='kpi-note'>{escape(note)}</div></div>",
        unsafe_allow_html=True,
    )


def finding(col, kicker, title, body_html, accent=BLUE):
    """body_html may contain <b> tags; all numbers come from our own report tables."""
    col.markdown(
        f"<div class='finding' style='--accent:{accent}'>"
        f"<div class='finding-kicker'>{escape(kicker)}</div>"
        f"<div class='finding-title'>{escape(title)}</div>"
        f"<div class='finding-body'>{body_html}</div></div>",
        unsafe_allow_html=True,
    )


def side_item(label, value):
    st.sidebar.markdown(
        f"<div class='side-label'>{escape(label)}</div><div class='side-value'>{value}</div>",
        unsafe_allow_html=True,
    )


def side_note(html):
    st.sidebar.markdown(f"<div class='side-note'>{html}</div>", unsafe_allow_html=True)


def style_fig(fig, height=380):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_2, size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
        hoverlabel=dict(bgcolor=CARD, bordercolor=GRID, font=dict(color=TEXT, size=13)),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="")
    fig.update_yaxes(gridcolor=GRID, zeroline=False, ticks="")
    return fig
