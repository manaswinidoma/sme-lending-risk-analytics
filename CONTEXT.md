# Project Context & Session Memory

> Last updated: 2026-10-10 · Current phase: **Phase 2 – Bronze (not started)**
> `README.md` is the public project guide (case study, progress tracker, data quality log, decisions log).
> This file is the working memory for resuming between chat sessions.

## 1. Project Overview & Rules
- **Core Goal:** Answer "Which new Australian businesses are riskiest to lend to?" for a hypothetical SME Credit Risk / Business Lending team. Measure early-stage deregistration risk by company segment and turn it into lending-criteria recommendations.
- **Repo:** `sme-lending-risk-analytics` (GitHub, branch `main`)
- **Tech Stack / Tools:** Databricks **Free Edition** (serverless only), Delta Lake, Unity Catalog, Python, PySpark, dbt Core (`dbt-databricks` adapter), SQL, Streamlit.
- **Data:** ASIC Company Dataset via data.gov.au (dataset id `asic-companies`). Optional later: ABS Data API for context.
- **Strict Constraints:**
  - Australian publicly available data only. No synthetic, simulated or invented data.
  - Never state facts about the data that have not been verified by profiling. Mark unverified items `[VERIFY]`.
  - Data analytics framing: business question → KPIs → insights → recommendations. Not a pure engineering demo.
  - Deregistration is a **proxy** for business discontinuation, not loan default. Say so in the app.
  - Free Edition limits: serverless compute only; cannot create SQL warehouses (use the pre-created **Serverless Starter Warehouse**); daily fair-usage quota; up to 3 Databricks Apps; outbound internet limited to trusted domains; inactive accounts may be deleted, so keep all code in GitHub.

## 2. Architecture & Key Decisions
- **Medallion layers:** Bronze (raw, all strings) → Silver (PySpark: typed, deduplicated, flagged) → Gold (dbt marts) → Streamlit.
- **Unity Catalog:** default catalog `workspace`. Proposed schemas `sme_risk_bronze`, `sme_risk_silver`, `sme_risk_gold`. Existing: `workspace.sme_risk_bronze` with volume `landing` (created during testing; holds `company_202610.csv`, 400.1 MB).
- **Ingestion runs inside Databricks:** data.gov.au is reachable from Free Edition serverless (tested 2026-10-08). ABS API returned a read timeout on the first test (optional source; retry with a small query).
- **File format:** ASIC "csv" is **tab-delimited**; dates are text `DD/MM/YYYY`. Read with `sep="\t"`, keep strings in Bronze.
- **Coverage limit → method:** the file holds all current companies but **deregistrations from the past year only**. Cohort survival would be biased, so use a **period (last-12-months) method**: age-specific deregistration rates over the window, chained into an implied survival curve.
- **Observation window:** exactly **2025-10-06 to 2026-10-04** (211,205 deregistered companies). First/last calendar months are partial by design.
- **Deduplication:** keep `Current Name Indicator = 'Y'` (exactly one per ACN). Use the count of historical-name rows as a "name changes" feature.
- **Population exclusions:** CNCL (39 companies with no current-name row, all CNCL) and DISS.
- **Status is authoritative:** ignore Date of Deregistration when Status ≠ DRGD (10 rows, likely reinstatements); flag them in Silver.
- **Segmentation:** company age band, Type, Class, Sub Class, ABN held (`ABN != '0'`), name-change history. **State dropped** (`Previous State of Registration` ~95% null; no current-state field).
- **KPI spec v1 (2026-10-10, full detail in README §5):** exposure-based period life table.
  - Exposure = company-years registered inside the window, split across age bands at anniversaries; replaces "companies at risk at window start".
  - Age bands `[0,1)…[4,5)`, `[5,10)`, `[10,+)` on anniversaries via `add_months(reg_date, 12*k)` (leap-year safe; never `datediff/365`).
  - q = 1 − exp(−m), m = deregistrations ÷ exposure; deregistration assigned to age band on its deregistration date.
  - Survival S(N) = ∏(1 − q_x), reported for N = 1, 2, 5.
  - Distress share = SOFF+EXAD ÷ all non-deregistered (REGD+SOFF+EXAD+NOAC); snapshot, not a rate.
  - Relative risk index = segment (1 − S(2)) ÷ overall (1 − S(2)) (age-adjusted); flag > 1.25× (illustrative).
  - Reliability flag: exposure < 100 company-years or < 10 deregistrations in any band used → warn and suppress RRI.
  - App must state: period assumption (last 12 months' conditions persist), deregistration ≠ default, snapshot/reinstatement limits.
- **Keep weekly snapshots** from now on (file updates every Tuesday) to build true status-change history later.
- **Streamlit hosting plan:** build as a Databricks App; publish a public copy on Streamlit Community Cloud using exported Gold summary tables (verify access options at that stage).

## 3. Completed Milestones
- [x] Project chosen and scoped (business question, stakeholder, KPIs drafted).
- [x] Confirmed Databricks Free Edition supports the stack (Community Edition retired 2026-01-01).
- [x] Connectivity test: data.gov.au ✅, PyPI ✅, ABS ⚠️ timeout.
- [x] Downloaded ASIC company file into `/Volumes/workspace/sme_risk_bronze/landing/` (test notebook).
- [x] Profiling complete (validation gate passed):
  - 4,449,049 rows · 15 columns · **4,015,034 distinct ACNs** · 4,014,995 current-name rows · 434,054 historical-name rows
  - Status (row level): REGD 4,129,666 · DRGD 231,738 · SOFF 46,520 · EXAD 40,575 · NOAC 490 · CNCL 59 · DISS 1
  - Registration dates 1817-04-08 (Westpac, genuine) to 2026-10-05; 4 companies with missing registration date
  - DRGD rows without a date (20,533) are all historical-name rows → 0 after dedup
- [x] README project guide written (data quality log + decisions log filled).
- [x] KPI spec v1 finalised (2026-10-10): exposure denominator, age bands, distress denominator, age-adjusted RRI, reliability flag, caveats.
- [x] GitHub repo created; CONTEXT.md set up.

## 4. Current State (WIP)
- **Active Task:** Move from testing into the real build (Phase 2 – Bronze).
- **Repo state:** full project guide copied into `README.md` (2026-10-08). `README.md` (now incl. KPI spec v1) and `CONTEXT.md` are not yet committed or pushed.
- **Notebook state:** profiling code lives in a scratch/test notebook in Databricks, not in the repo.
- **Open Questions / Blockers:**
  - ABS context data: needed or not? (optional; retry later)
  - Reliability thresholds (100 company-years / 10 deregistrations) to review after the first Gold run
  - RAG / vector search idea parked for a later project

## 5. Next Immediate Step
1. Commit `README.md` + `CONTEXT.md` and push to `main`.
2. In Databricks: Workspace → Create → **Git folder** → paste the repo URL.
3. Create `notebooks/01_ingest_bronze` inside the Git folder, then ask Claude for the production ingestion notebook (dated weekly file in the Volume + load metadata + Bronze Delta table).
