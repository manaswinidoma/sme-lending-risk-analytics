import re
from html import escape

import pandas as pd
import streamlit as st

from data import lookup_company, search_companies
from ui import GRID, TEXT, TEXT_2, TIER_ACTIONS, TIER_COLORS

st.title("Company lookup")
st.markdown(
    "<div class='subtitle'>Find any Australian company by ACN or name and see how this project would "
    "treat it as a borrower.</div>",
    unsafe_allow_html=True,
)
st.write("")


def clean_acn(text: str) -> str | None:
    """Digits only; 9-digit ACN with a valid ASIC check digit, else None."""
    digits = re.sub(r"\D", "", text or "")
    if len(digits) != 9:
        return None
    weights = [8, 7, 6, 5, 4, 3, 2, 1]
    check = (10 - sum(int(d) * w for d, w in zip(digits[:8], weights)) % 10) % 10
    return digits if check == int(digits[8]) else None


# ---------- search box (ACN can also come from the URL: ?acn=...) ----------
if "lookup_query" not in st.session_state:
    st.session_state["lookup_query"] = st.query_params.get("acn", "")
c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
query = c1.text_input("ACN or company name", key="lookup_query", placeholder="e.g. 000 386 685 or GROWTHOPS")
c2.button("Search", type="primary", use_container_width=True)

if not query.strip():
    st.query_params.clear()
    st.caption("Tip: an ACN is the 9-digit number on the company's ASIC record. Spaces are fine.")
    st.stop()

acn = clean_acn(query)
digits_only = re.fullmatch(r"[\d\s]+", query.strip()) is not None

if digits_only and not acn:
    st.warning("That doesn't look like a valid ACN: it needs 9 digits and a valid ASIC check digit.")
    st.stop()

# ---------- name search → pick a company ----------
if not acn:
    st.query_params.clear()
    if len(query.strip()) < 3:
        st.info("Type at least 3 characters of the company name.")
        st.stop()
    hits = search_companies(query.strip())
    if hits.empty:
        st.info("No company names contain that text.")
        st.stop()
    st.caption(f"{len(hits)} match{'es' if len(hits) != 1 else ''}"
               f"{' (showing the first 25)' if len(hits) == 25 else ''}. Select one to see the details.")
    picked = st.dataframe(
        hits.rename(columns={"acn": "ACN", "company_name": "Company", "status_label": "Status",
                             "borrower_segment": "Segment", "lending_tier": "Lending tier"}),
        hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row",
    )
    rows = picked.selection.rows
    if not rows:
        st.stop()
    acn = hits.iloc[rows[0]]["acn"]

# ---------- company card ----------
result = lookup_company(acn)
if result.empty:
    st.info(f"ACN {acn[:3]} {acn[3:6]} {acn[6:]} is valid but is not on the current ASIC register file "
            "(it may have been deregistered more than a year ago).")
    st.stop()

c = result.iloc[0]
st.query_params["acn"] = acn
tier = c["lending_tier"]
color = TIER_COLORS.get(tier, GRID)


def show(v, fmt=None):
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
        return "–"
    try:
        if pd.isna(v):
            return "–"
    except (TypeError, ValueError):
        pass
    return fmt(v) if fmt else str(v)


st.write("")
st.markdown(
    f"<div class='kpi' style='border-left:8px solid {color}; min-height:0'>"
    f"<div class='kpi-label'>ACN {acn[:3]} {acn[3:6]} {acn[6:]}</div>"
    f"<div class='kpi-value' style='font-size:1.6rem'>{escape(str(c['company_name']))}</div>"
    f"<div style='margin-top:10px;font-size:1.05rem;color:{TEXT}'><b>Lending tier: {escape(tier)}</b></div>"
    f"<div class='kpi-note' style='font-size:0.95rem'>{escape(TIER_ACTIONS.get(tier, ''))}</div></div>",
    unsafe_allow_html=True,
)
st.write("")


def facts(col, title, items):
    rows = "".join(
        f"<tr><td style='color:{TEXT_2};padding:5px 12px 5px 0;white-space:nowrap'>{escape(k)}</td>"
        f"<td style='color:{TEXT};padding:5px 0'>{escape(v)}</td></tr>" for k, v in items)
    col.markdown(
        f"<div class='kpi' style='min-height:0'><div class='kicker'>{escape(title)}</div>"
        f"<table style='width:100%;border-collapse:collapse;margin-top:6px;border:none'>{rows}</table></div>",
        unsafe_allow_html=True,
    )


date = lambda d: pd.Timestamp(d).strftime("%d %b %Y")
left, mid, right = st.columns(3)
facts(left, "Company", [
    ("Status", show(c["status_label"])),
    ("Type", show(c["company_type_label"])),
    ("Borrower segment", show(c["borrower_segment"])),
    ("ABN", show(c["abn"])),
    ("Registered", show(c["registration_date"], date)),
    ("Deregistered", show(c["deregistration_date"], date)),
])
facts(mid, "Profile used for the tier", [
    ("Age", show(c["age_years"], lambda v: f"{int(v)} years")),
    ("Age band", show(c["age_band_label"])),
    ("Name", show(c["name_type"])),
    ("ABN held", show(c["abn_held"])),
    ("Former names", show(c["former_name_count"], lambda v: f"{int(v)}")),
    ("Renamed in last 12 months", "Yes" if c["changed_name_last_12m"] else "No"),
])
facts(right, "Risk of similar companies", [
    ("Profile tier", show(c["profile_risk_tier"])),
    ("Yearly deregistration chance", show(c["profile_yearly_dereg_prob_pct"], lambda v: f"{v:.2f}%")),
    ("vs trading average", show(c["profile_x_trading_average"], lambda v: f"{v:.2f}×")),
    ("Red flag", show(c["red_flag"]) if show(c["red_flag"]) != "–" else "None"),
    ("Data as at", show(c["snapshot_date"], date)),
])

st.write("")
# ---------- why this tier ----------
if tier == "Deregistered":
    why = "The company has been deregistered, so it cannot borrow. The profile risk is shown for context only."
elif tier.startswith("Decline"):
    why = (f"The company is currently <b>{escape(str(c['red_flag']))}</b>. The red-flag rule overrides "
           "the profile tier, whatever the company's age or name.")
elif tier.startswith("Out of scope"):
    why = (f"Risk tiers are built for trading companies only. This is a <b>{escape(str(c['borrower_segment']))}</b>, "
           "so it should be assessed under the policy for that type of entity.")
elif tier == "Excluded":
    why = "This status is outside the analysed population."
elif tier == "Insufficient data":
    why = "The company's age is unknown (no registration date), so no profile tier applies."
else:
    why = (f"Trading companies like this one ({escape(str(c['name_type']).lower())}, "
           f"{escape(str(c['abn_held']).lower().replace('has abn', 'with an ABN').replace('no abn', 'without an ABN'))}, "
           f"aged {escape(str(c['age_band_label']))}) deregistered at "
           f"<b>{c['profile_x_trading_average']:.2f}×</b> the trading-company average over the last 12 months, "
           f"which puts the profile in the <b>{escape(tier)}</b> tier.")
st.markdown(f"<div class='finding' style='--accent:{color};min-height:0'>"
            f"<div class='finding-kicker'>Why this tier</div><div class='finding-body'>{why}</div></div>",
            unsafe_allow_html=True)
st.caption("The tier describes the risk of similar companies, not a prediction for this company. "
           "Deregistration is a proxy for a business stopping, not loan default. "
           "Always confirm the company's current status on the ASIC register.")
