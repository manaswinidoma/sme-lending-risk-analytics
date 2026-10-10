# Which New Businesses Are Riskiest to Lend To?
### SME Business Survival Analytics on Australian Public Data

> Which new Australian businesses are riskiest to lend to? End-to-end analytics on 4M+ ASIC company records using Databricks, PySpark, dbt and Streamlit.

> **Status:** 🟡 In progress  |  **Current phase:** Phase 2 – Bronze  |  **Last updated:** 2026-10-10

<!-- Living document. Update the status line, progress tracker and changelog after every step.
     Sections marked [TODO] are placeholders. Sections marked [VERIFY] must be confirmed against
     the real data before they are treated as fact. -->

---

## 1. Project Overview

An end-to-end analytics project for an **Australian SME lender** that measures how long newly registered companies stay active, which segments are at higher risk of early deregistration, and what that means for lending criteria.

| Item | Detail |
|---|---|
| Company type | Australian bank / SME lender (hypothetical stakeholder) |
| Goal | Identify higher-risk new-business segments and recommend lending criteria adjustments |
| Main tools | Databricks (Delta Lake, Unity Catalog), PySpark, dbt, SQL, Python, Streamlit |
| Data | Australian public data only (see Section 3) |
| Final product | Stakeholder-ready Streamlit app with insights and recommendations |

**One-line summary (for the top of the repo):**
[TODO – write once findings exist, e.g. "Cohort survival analysis of Australian companies to guide SME lending risk appetite."]

---

## 2. Business Problem

<!-- Keep this non-technical. It should read like a business problem statement. -->

SME lenders have limited history to judge newly established businesses. Credit teams need to know:

- How likely is a new company to still be active after 1, 2 and 5 years?
- Which segments (company age, type, class, ABN status, name-change history) deregister earliest?
- Is early-stage risk changing over time?
- Where should lending criteria be tightened or relaxed?

**Primary stakeholder:** SME Credit Risk / Business Lending team
**Decision supported:** Risk appetite and lending criteria for businesses under 2–3 years old

**Important framing:** Deregistration is used as a **proxy** for business discontinuation. It is not the same as loan default or insolvency (companies can deregister voluntarily, merge, or restructure). This limitation is stated in the app and in Section 7.

---

## 3. Data Sources

| Source | Publisher | Access | Refresh | Used for | Status |
|---|---|---|---|---|---|
| ASIC Company Dataset (data.gov.au id: `asic-companies`) | ASIC via data.gov.au | CSV (tab-delimited) / ZIP / CKAN API | Weekly (Tuesdays) | Company registrations, status, deregistrations | ✅ Reachable from Databricks Free Edition |
| ABS Data API | Australian Bureau of Statistics | SDMX REST API (no key, beta) | Varies by dataflow | Context, e.g. state-level economic indicators | ⚠️ Read timeout on first test – retry with a small query |
| [Optional] ASIC Business Names Dataset | ASIC via data.gov.au | CSV / API | Weekly | Possible enrichment | [TODO – decide] |

### 3.1 Data validation gate (complete before modelling)

- [x] data.gov.au reachable from Databricks Free Edition serverless compute (2026-10-08)
- [x] Fields confirmed: Status, Date of Registration, Date of Deregistration, Type, Class, Sub Class, ABN
- [x] File format confirmed (ASIC help file): **tab-delimited** despite `.csv` extension; dates are text `DD/MM/YYYY`
- [x] Coverage confirmed (ASIC help file): all currently registered companies, **deregistered companies for the past year only**, and historical name rows for registered companies
- [x] File profiled (`company_202610.csv`, 400.1 MB): **4,449,049 rows**, 15 columns
- [x] Status breakdown (row level, before dedup): REGD 4,129,666 · DRGD 231,738 · SOFF 46,520 · EXAD 40,575 · NOAC 490 · CNCL 59 · DISS 1
- [x] Name history: 4,014,995 current-name rows (`Y`), 434,054 historical-name rows; **4,015,034 distinct ACNs**
- [x] Registration dates: no blanks; range 1817-04-08 to 2026-10-05
- [x] Deregistration date blank on 95.25% of rows (expected: only deregistered companies have one)
- [x] Exactly one current-name (`Y`) row per ACN (0 duplicates)
- [x] Deregistration window for **DRGD companies only**: **2025-10-06 to 2026-10-04** (211,205 deregistered companies). This is a rolling one-year window, so the first and last calendar months are partial by design, not missing data
- [x] Data quality issues investigated (see Section 10)
- [x] State: `Previous State of Registration` is null for ~95% of companies → **state is not usable for segmentation**

> **Impact of coverage:** companies deregistered more than a year ago are not in the file, so long-run survival cannot be measured directly from registration cohorts (survivorship bias). See Section 5 and the Decisions Log for the adjusted method.

**Known field rules (from ASIC data dictionary):**
- `Status`: REGD registered, DRGD deregistered, EXAD external administration, SOFF strike-off in progress, NOAC not active, plus rarer codes
- `ABN` = `0` means the company has no ABN
- `Current Name Indicator` = `Y` marks the current-name row; null rows are historical names → deduplicate on ACN
- For `Type = RACN`, the ACN field holds an ARBN

### 3.2 Data dictionary [TODO – fill after profiling]

| Column | Type | Description | Null % | Notes |
|---|---|---|---|---|
| | | | | |

---

## 4. Architecture (High Level)

```
Sources (ASIC, ABS)
      │  Python / PySpark ingestion (Databricks Jobs)
      ▼
Bronze  – raw files and API responses, unchanged        (Delta, Unity Catalog)
      │  PySpark cleaning and standardisation
      ▼
Silver  – cleaned, typed, deduplicated, conformed       (Delta, Unity Catalog)
      │  dbt models (SQL) + dbt tests
      ▼
Gold    – business-ready marts: cohorts, survival, KPIs  (Delta, Unity Catalog)
      │
      ▼
Streamlit app – insights and recommendations for the credit team
```

**Why layered:** clarity, traceability from source to dashboard, and the ability to re-run any layer without re-downloading data.

### 4.1 Unity Catalog structure [TODO – confirm names]

```
catalog: sme_risk
  ├── bronze   (raw_asic_companies, raw_abs_*)
  ├── silver   (companies, abs_indicators)
  └── gold     (dim_company, fct_company_lifecycle, mart_cohort_survival, mart_segment_risk)
```

### 4.2 Repository structure [TODO – update as built]

```
├── README.md                # this file
├── notebooks/
│   ├── 01_ingest_bronze/
│   └── 02_clean_silver/
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   └── tests/
├── app/                     # Streamlit
├── docs/
│   ├── screenshots/
│   └── data_quality_log.md
└── requirements.txt
```

---

## 5. KPIs and Definitions

**Method:** an exposure-based **period life table**. The file holds only the last 12 months of deregistrations, so instead of following cohorts we measure what happened to *every* company during the observation window (**2025-10-06 to 2026-10-04**), by company age, and chain the age-specific rates into an implied survival curve.

### 5.1 Age bands
Non-overlapping, contiguous bands on completed years since registration: `[0,1)` `[1,2)` `[2,3)` `[3,4)` `[4,5)` `[5,10)` `[10,+)`.
- The first five bands feed the 1–5 year survival curve; `[5,10)` and `[10,+)` are context only.
- Band boundaries are company **anniversaries** computed with `add_months(registration_date, 12*k)`, so leap years are handled consistently (a 29 Feb registration has its anniversary on 28 Feb in non-leap years). Never use `datediff/365`.
- 4 companies with no registration date get age band `Unknown` and are excluded from age-based KPIs.

### 5.2 KPI definitions

| # | KPI | Definition | Grain |
|---|---|---|---|
| 0 | **Exposure (company-years at risk)** | Time each company was registered inside the window: from `max(window_start, registration_date)` to `min(window_end, deregistration_date)`, **split across age bands at each anniversary**. Replaces the draft "companies at risk at the start of the window", which missed companies registered during the window and ignored partial exposure. | Age band × segment |
| 1 | **Annual deregistration rate (q)** | Central rate `m = deregistrations in band ÷ exposure in band`; converted to an annual probability `q = 1 − exp(−m)` (constant hazard within a band). Each deregistration is assigned to the age band the company was in **on its deregistration date**. | Age band × segment |
| 2 | **Implied N-year survival** | `S(N) = ∏ (1 − q_x)` for x = 0 … N−1, reported for N = 1, 2, 5. Reads as: "under the last 12 months' conditions, X% of new companies are still registered after N years." | Segment |
| 3 | **Distress share** | `companies currently in SOFF or EXAD ÷ all companies not deregistered (REGD + SOFF + EXAD + NOAC)` in the segment, at the file snapshot date. SOFF and EXAD companies are still registered, so they sit in **both** numerator and denominator. Deregistered (DRGD), cancelled (CNCL) and dissolved (DISS) entities are excluded from the base. A point-in-time leading indicator, not a 12-month rate. | Age band × segment |
| 4 | **Relative risk index (RRI)** | `(1 − S(2)) for the segment ÷ (1 − S(2)) for all companies`. Uses the 2-year cumulative deregistration probability so the comparison is **age-adjusted** (crude rates would be distorted by segments that are mostly young or mostly old). Segments above **1.25×** are flagged for review (illustrative threshold; a credit policy choice). | Segment |
| 5 | **Data reliability flag** | `Low reliability` if any age band used in a segment's survival curve has **exposure < 100 company-years** or **fewer than 10 deregistrations**. Low-reliability segments show a warning and their RRI is suppressed. Thresholds to be reviewed after the first Gold run. | Segment |

### 5.3 Caveats (shown in the app)
- **Period assumption:** survival assumes the last 12 months' deregistration rates stay the same for the next five years (no cohort or economic shifts). If interest rates, inflation or ASIC enforcement activity during the window were unusual, the curve will be biased. This must be stated to credit committees.
- **Proxy, not default:** deregistration includes voluntary, solvent closures and restructures. It indicates business discontinuation, not loan loss.
- **Window completeness:** the method assumes the file contains every deregistration in the window. Monthly counts look complete, but the file is a weekly snapshot and companies deregistered then reinstated inside the window appear as registered and cannot be detected.
- **Distress is a snapshot:** SOFF and EXAD counts describe the file date, not the whole year.
- **No financial data:** no turnover, credit or industry information is available per company, so risk is described by registration attributes only.
- **Small segments:** rare company types (e.g. CCIV, RACN) can produce volatile curves; the reliability flag controls this. State is not used (≈95% null).

## 6. Dashboards & Analysis (Streamlit)

<!-- Screenshots matter more than text. Add one per page once built. -->

| Page | Question it answers | Screenshot |
|---|---|---|
| 1. Overview | How many companies are registering and deregistering, and what are the headline survival rates? | [TODO] |
| 2. Survival curves | How likely is a new company to survive 1, 2 and 5 years, by segment? | [TODO] |
| 3. Segment risk | Which segments have the highest relative risk index and distress share? | [TODO] |
| 4. Recommendations | What should the credit team change? | [TODO] |

---

## 7. Findings & Recommendations [TODO – complete at the end]

### Key findings
1.
2.
3.

### Recommendations for the SME Credit team
| Recommendation | Evidence | Expected benefit |
|---|---|---|
| | | |

### Limitations
- Deregistration is a proxy for business discontinuation, not loan default.
- No financial or credit data is available for individual companies.
- [TODO – add data-specific limitations found during profiling]

---

## 8. Outcome & Value [TODO]

- Clear visibility of early-stage business risk by segment
- Evidence base for lending criteria decisions
- Repeatable pipeline that refreshes with ASIC's weekly updates

---

## 9. Progress Tracker

| Phase | Step | Status | Date | Notes |
|---|---|---|---|---|
| 0. Scoping | Business problem and stakeholder questions defined | ✅ | 2026-10-08 | |
| 0. Scoping | KPI definitions finalised (v1) | ✅ | 2026-10-10 | Exposure-based period life table; reliability flag added |
| 1. Data | Download and profile ASIC dataset | ✅ | 2026-10-08 | 4,449,049 rows; 4,015,034 companies |
| 1. Data | Complete data validation gate (3.1) | ✅ | 2026-10-08 | |
| 1. Data | Choose ABS dataflows | ⬜ | | Optional; ABS API timed out on first test |
| 2. Bronze | Databricks workspace and Unity Catalog set up | ⬜ | | |
| 2. Bronze | Ingestion jobs (Python / PySpark) | ⬜ | | |
| 3. Silver | Cleaning, typing, deduplication (PySpark) | ⬜ | | |
| 3. Silver | Data quality checks logged | ⬜ | | |
| 4. Gold | dbt project connected to Databricks | ⬜ | | |
| 4. Gold | Staging, intermediate and mart models | ⬜ | | |
| 4. Gold | dbt tests and docs | ⬜ | | |
| 5. Analysis | Cohort and survival analysis | ⬜ | | |
| 5. Analysis | Segment risk analysis | ⬜ | | |
| 6. App | Streamlit pages built | ⬜ | | |
| 6. App | App deployed | ⬜ | | |
| 7. Wrap-up | Findings and recommendations written | ⬜ | | |
| 7. Wrap-up | Screenshots, CV bullet, LinkedIn post | ⬜ | | |

Status key: ⬜ Not started · 🟡 In progress · ✅ Done · ⛔ Blocked

---

## 10. Data Quality Log

| Date | Table / column | Issue found | Rows affected | Fix applied |
|---|---|---|---|---|
| 2026-10-08 | Company file / delimiter | File is tab-delimited despite `.csv` extension | All | Read with `sep="\t"` |
| 2026-10-08 | Company name history | Historical name rows repeat the same ACN | 434,054 | Keep `Current Name Indicator = 'Y'` rows in Silver (verified: one `Y` row per ACN); count prior names as a feature |
| 2026-10-08 | ACN vs current-name rows | 39 ACNs have no current-name row | 39 ACNs | All are status CNCL (cancelled / transferred to another law) → excluded from the population |
| 2026-10-08 | Status DRGD | DRGD rows without a deregistration date | 20,533 rows | Resolved: all are historical-name rows; 0 after dedup |
| 2026-10-08 | Status vs deregistration date | Deregistration date present on non-DRGD statuses (EXAD 7, SOFF 1, REGD 1, DISS 1), dates 2001–2026 | 10 rows | Treat Status as authoritative; ignore deregistration date when Status ≠ DRGD (likely reinstatements); flag in Silver |
| 2026-10-08 | Date of Registration | Earliest date 1817-04-08 | 1 | Genuine: Westpac Banking Corporation |
| 2026-10-08 | Date of Registration | Registration date missing (raw value null; earlier 0% blank rate was a rounding effect) | 4 companies | Exclude from age-based KPIs; keep in counts with age band "Unknown" |
| 2026-10-08 | Previous State of Registration | ~95% null; duplicate labels (SA, WA, NT appear twice, likely whitespace) | All | Trim values; state dropped from segmentation |

---

## 11. Decisions Log

<!-- Record why decisions were made. This is what interviewers ask about. -->

| Date | Decision | Options considered | Reason |
|---|---|---|---|
| 2026-10-08 | Chose "Which new businesses are riskiest to lend to?" as the project | Rate pass-through, branch closures, others | Large Australian public dataset, clear lending stakeholder |
| 2026-10-08 | Build on Databricks Free Edition | Paid trial workspace | Free; data.gov.au confirmed reachable from serverless compute |
| 2026-10-08 | Use a period (last-12-months) survival method instead of cohort survival | Cohort Kaplan–Meier; wait for weekly snapshots to build history | ASIC file only includes deregistrations from the past year, so cohort survival would be biased |
| 2026-10-08 | Also keep weekly snapshots from now on | Single download | Builds true status-change history over time as a future enhancement |
| 2026-10-08 | Drop state as a segment; segment by company age, Type, Class, Sub Class, ABN held (ABN ≠ 0) and name-change history | Segment by state | `Previous State of Registration` is ~95% null; the file has no current state field |
| 2026-10-08 | Exclude CNCL (and DISS) companies from the population | Keep all statuses | Cancelled/transferred entities are not businesses a lender would assess |
| 2026-10-08 | Define the observation window as exactly 2025-10-06 to 2026-10-04, matching the file's rolling year | Trim to complete calendar months only | Keeps all 211,205 deregistrations; monthly trend charts will label the two partial months |
| 2026-10-10 | Use exposure (company-years) split by age band as the denominator, with q = 1 − exp(−m) | Count of companies at the start of the window | Includes companies registered during the window and handles partial exposure correctly |
| 2026-10-10 | Age bands [0,1)…[4,5), [5,10), [10,+) on anniversaries via `add_months` | `datediff/365` | Contiguous, non-overlapping bands; consistent leap-year handling |
| 2026-10-10 | Distress share denominator = all non-deregistered companies (REGD + SOFF + EXAD + NOAC) | % of all companies in the file | Numerator must be a subset of the denominator; deregistered entities excluded |
| 2026-10-10 | Relative risk index based on 2-year cumulative deregistration probability | Crude 12-month rate ratio | Age-adjusted comparison between segments with different age mixes |
| 2026-10-10 | Add data reliability flag (exposure < 100 company-years or < 10 deregistrations) | No threshold | Prevents volatile curves for small segments from driving recommendations |

---

## 12. Portfolio & Interview Notes [TODO – fill at the end]

**CV bullet (one strong line):**
> Built an end-to-end SME business-survival analytics project on Databricks (PySpark, dbt, SQL) and Streamlit using ASIC public data, delivering [TODO – outcome].

**60–90 second explanation:**
- **Context:** [TODO]
- **Problem:** [TODO]
- **Solution:** [TODO]
- **Impact:** [TODO]

**Most challenging part:** [TODO – focus on scoping, trade-offs, design decisions]
**What I'd improve with more time:** [TODO]
**What I learned:** [TODO – business understanding, communication, structuring analytics work]

---

## 13. How to Run [TODO]

```bash
# 1. Clone the repo
# 2. Set up the Databricks workspace and Unity Catalog (see docs/)
# 3. Run ingestion jobs
# 4. dbt build
# 5. streamlit run app/app.py
```

---

## Changelog

| Date | Change |
|---|---|
| 2026-10-08 | Created project guide template |
| 2026-10-08 | Connectivity test done; ASIC coverage and field rules recorded; KPIs switched to period method |
| 2026-10-08 | First profiling results and data quality log added |
| 2026-10-08 | Profiling round 2: issues resolved, state dropped, segmentation decided |
| 2026-10-08 | Profiling complete: observation window confirmed; Phase 0–1 marked done |
| 2026-10-10 | KPI spec v1: exposure denominator, age bands, distress denominator, age-adjusted RRI, reliability flag, caveats |
