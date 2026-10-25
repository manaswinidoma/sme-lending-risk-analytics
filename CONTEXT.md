# Project Context & Session Memory

> Last updated: 2026-10-13 (evening) · Current phase: **Phase 3 – Silver (in progress, column-by-column)**
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
- **Medallion layers:** Bronze (raw, all strings) → Silver (PySpark: typed, deduplicated, flagged) → Gold (Spark SQL star schema) → Streamlit.
- **Unity Catalog:** catalog `workspace`; schemas `sme_risk_bronze`, `sme_risk_silver`, `sme_risk_gold` (created 2026-10-13). Bronze volume: **`source_systems`** (replaces the `landing` volume from testing).
- **Load patterns:** Bronze = append each weekly snapshot (replaceWhere per `_snapshot_date`, idempotent); Silver = overwrite from latest snapshot; Gold = overwrite from Silver (option A).
- **Landing layout:** `/Volumes/workspace/sme_risk_bronze/source_systems/asic_companies/snapshot_date=YYYY-MM-DD/<file>` + `_metadata.json` (source URL, ASIC last-modified, bytes, SHA-256). `snapshot_date` = resource `last_modified` from the data.gov.au CKAN API (`package_show?id=asic-companies`). Download skips if the snapshot folder already has the file; writes via `.part` then rename.
- **Bronze table:** `workspace.sme_risk_bronze.asic_companies_raw` — 15 source columns as STRING with snake_case names (`type`, `class` kept as-is; rename in Silver) + `_snapshot_date`, `_source_file`, `_source_url`, `_ingested_at`. CSV read with `sep="\t"`, `quote=""` (quoting off), `inferSchema=False`. Load stops unless: header matches the 15 documented names, row count = raw non-empty line count − 1, every line has exactly 14 tabs. Cell 7 loads only snapshot folders not yet in the table.
- **Metadata:** table, column and volume comments sourced from the ASIC help file (Appendix Item 2), applied in `bronze_ingest` (each rerun adds ~19 CHANGE COLUMN versions; harmless). `CCIV` type appears in data but is not documented by ASIC.
- **Notebook conventions:** every cell safe to rerun → "Run All" is the normal way to run; all config (incl. `BRONZE_TABLE`) lives in Cell 1.
- **Orchestration (DONE 2026-10-25):** Databricks Job `sme_risk_weekly_pipeline`: tasks `bronze_layer` → `silver_layer` → `gold_layer` (notebooks `notebooks/bronze_ingest`, `silver_transform`, `gold_build`; source WORKSPACE = the Git folder; serverless; Bronze 1 retry after 15 min; tag project=sme-lending-risk). Definition exported to `jobs/sme_risk_weekly_pipeline.yml`. First runs succeeded (~7 min). Still to add: weekly schedule Wed 07:00 Australia/Sydney + failure email, then re-export YAML. Free Edition limit: 5 concurrent job tasks.
- **Why not upsert:** Bronze appends snapshots (upsert would overwrite status history); Silver overwrites from the latest snapshot (full-copy source; overwrite removes companies ASIC drops after a year). Upsert-style SCD2 only later in Gold via dbt snapshots.
- **Silver notebook structure (`notebooks/silver_transform.ipynb`):** 1) imports → 2) config + `RENAME_MAP` + code-label dictionaries → 3) read Bronze → 4) filter latest snapshot (+ baseline counts) → 5) rename → per-column transforms (PySpark) → temp view `v_companies_clean` → dedup + business rules (SQL) → labels (PySpark) → validate (hard stops) → write (overwrite).
- **RENAME_MAP (user-edited, no `_raw` suffixes):** type→company_type, class→company_class, sub_class→company_sub_class, status→status_code, date_of_registration→registration_date, date_of_deregistration→deregistration_date, previous_state_of_registration→previous_state; others keep their names. Date flags (`*_unparseable`) must be computed **before** parsing in place; text `deregistration_date` dropped and rebuilt in SQL as status-authoritative, raw parse kept as `deregistration_date_reported`.
- **Column decisions so far (detail in README §3.3):**
  - `company_name`: decode CSV escaping first (429 rows; verified on ASIC register), then strip control chars, trim (45,798), collapse spaces (46,776). Keep asterisks (genuine), numbers, case, punctuation. `º` (suspected export replacement of `|`) flagged via `company_name_has_export_artifact`, not changed — pending pipe check. New feature `is_acn_named` (own ACN appears anywhere in the name's digits; catches ABN-style names). Helpers `unescape_csv`, `clean_text` also applied to `current_name`.
  - `acn`: 100% valid (9 digits + ASIC check digit, incl. ARBNs); 15% leading zeros → keep STRING, no transform; hard stop in validation. No `acn_is_arbn` flag (ARBN note in column description). Draft `acn_format_valid` column dropped.
  - `company_type`: clean; APTY ≈ 99% of companies → top-level filter only; add labels; hard stop on unknown codes. CCIV label marked "not in ASIC help file".
  - `company_class`: clean; NONE = exactly FNOS + RACN; add labels.
  - `company_sub_class`: clean; undocumented **WHSL** (13, all CCIV) added to dictionary as "not in ASIC help file; likely wholesale CCIV"; PSTC (super trustee) = 488,022 (~12%); APUB+LMGT confirmed mostly non-profit (ULSN 73%).
  - **Borrower segment (agreed):** Trading (APTY+PROP) · Super trustee (PSTC) · Not-for-profit (ULSN, PNPC, NLTD) · Home unit (HUNT) · Other public · Foreign (FNOS) · Registrable body (RACN) · CCIV. **Built in Gold** (`dim_company_classification`), not Silver. **Keep all in population**, report per segment, app defaults to Trading.
  - `status_code`: clean. Current: REGD 3,729,504 · DRGD 211,591 (all with dereg date) · SOFF 43,084 · EXAD 31,857 · NOAC 295 · DISS 1 · CNCL 0. 9 status/date conflicts (status authoritative, flagged). 39 no-Y ACNs, all CNCL → hard stop if any non-CNCL. Null-safe has-Y logic required (`coalesce((indicator='Y').cast(int), 0)`) — an earlier check missed them because of nulls.
  - Dates: registration 4 missing (3 NOAC + 1 DRGD → age "Unknown", 1 event lost), 0 bad/unparseable/future; deregistration all checks 0. 30 June registration spikes = financial-year effect (not placeholders). May 2026 deregistrations 38,738 (~2× normal; cause unverified; annotate). "Companies by registration year" is survivorship-biased — label accordingly. Hard stops: unparseable dates, dates after snapshot, dereg before reg.
  - `previous_state`: 5% filled; 47 trailing spaces (trim); NFK = Norfolk Island (58, all registered 2021-08-02); pre-1991 state registration, **not current location** (no geography in ASIC file). 333 with previous_state but reg ≥ 1991 → age may be understated (documented only). Hard stop on unknown codes.
  - `state_registration_number`: text (131,697 contain letters); 147 without state; Silver only.
  - `modified_since_last_report`: Y → true, null → false via coalesce (plain `== 'Y'` gives null — bug fixed). Pipeline use only.
  - `abn`: `"0"` (1,631,164, 41%) → null; `has_abn`; all real ABNs valid + unique → hard stops (11 digits, mod-89 check, unique); `abn_format_valid` dropped. 266 ABNs not built from ACN (charities, foreign, converted entities) — genuine, no flag. ABN % by status: REGD 58.5, DRGD 69.0, SOFF 68.6, EXAD 86.4 → not a headline distress signal; PSTC 9.3% vs PROP 66.2% → "trading vs dormant" indicator, analyse within segment.
  - Former-name rows (indicator null) are not edited; dedup keeps the Y row per ACN. ACNs with no Y row are dropped (were 39, all CNCL) — check none are in the lending population.
- **Gold model (DECIDED 2026-10-24, replaces dbt plan):** star schema in notebook **`notebooks/gold_build.ipynb`**; each table = one `spark.sql` query → DataFrame → `saveAsTable` in `workspace.sme_risk_gold` → `%sql` sanity checks. No marts, no dbt for now (KPIs queried on top).
  - Keys: `company_key = CAST(acn AS BIGINT)` (user rejected negative xxhash64); `classification_key = type-class-sub_class`; `status_key = status_code`; `age_band_key` 0–7 (0 Unknown; rule: age<5 → age+1, <10 → 6, else 7); `date_key = YYYYMMDD` int, 0 = "No date".
  - Dims (all ✅ 2026-10-24): dim_company 4,016,332 · dim_company_classification 35 rows / 8 borrower segments (Trading 3,483,992 · Super trustee 488,022 · Not-for-profit 23,132 · Other public 11,766 · Foreign 4,695 · Home unit 2,636 · Registrable body 2,078 · CCIV 11; ULSS/LISS left in Other public) · dim_status 6 (+ status_group) · dim_age_band 8 (built from ages 0–10 via CASE + DISTINCT) · dim_date 76,702 (1817-01-01 → 2026-12-31 + No-date row; AU financial year columns).
  - **Load pattern (DECIDED 2026-10-24, option A):** every Gold table (dims AND facts) is **overwritten from Silver** each run — Gold mirrors the latest snapshot; no MERGE. History lives only in Bronze (all weekly snapshots) and can be rebuilt from there later. Fact write cells: plain overwrite + overwriteSchema (replaceWhere removed).
  - Facts (✅ 2026-10-24):
    - `fct_company_snapshot`: company × snapshot, 4,016,332 rows; age at snapshot (or at deregistration for DRGD); 0/1 measures active 3,804,740 · distressed 74,941 · deregistered 211,591 · in_population 4,016,331; unknown age 4.
    - `fct_exposure`: company × age band × snapshot, 5,503,420 rows; window 2025-10-13 → 2026-10-12 (364 days); 4,016,321 companies at risk; 211,590 deregistrations; 3,712,991 company-years; split at anniversaries with add_months.
- **Extra sources:** discussed (ASIC Business Names, ABN Bulk Extract, banned orgs, ASIC insolvency stats) — **parked**; staying single-source for now.
- **Ingestion runs inside Databricks:** data.gov.au is reachable from Free Edition serverless (tested 2026-10-08). ABS API returned a read timeout on the first test (optional source; retry with a small query).
- **File format:** ASIC "csv" is **tab-delimited**; dates are text `DD/MM/YYYY`. Read with `sep="\t"`, keep strings in Bronze.
- **Coverage limit → method:** the file holds all current companies but **deregistrations from the past year only**. Cohort survival would be biased, so use a **period (last-12-months) method**: age-specific deregistration rates over the window, chained into an implied survival curve.
- **Observation window:** **computed per snapshot** = min/max DRGD deregistration date (rolling year moves weekly). 8 Oct file: 2025-10-06 → 2026-10-04 (211,205). 12 Oct snapshot: 211,591 DRGD across Oct 2025 → Oct 2026 (edge months partial). Do not hard-code.
- **Deduplication:** keep `Current Name Indicator = 'Y'` (exactly one per ACN). Use the count of historical-name rows as a "name changes" feature.
- **Population exclusions:** CNCL (39 companies with no current-name row, all CNCL) and DISS.
- **Status is authoritative:** ignore Date of Deregistration when Status ≠ DRGD (10 rows, likely reinstatements); flag them in Silver.
- **Segmentation:** company age band, borrower segment (Type/Class/Sub Class), ABN held (within segment only), name-change history. **No state/geography** (`previous_state` is pre-1991 history, not location).
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
- [x] Downloaded ASIC company file into the testing `landing` volume (scratch notebook; superseded by `01_ingest_bronze`).
- [x] Profiling complete (validation gate passed):
  - 4,449,049 rows · 15 columns · **4,015,034 distinct ACNs** · 4,014,995 current-name rows · 434,054 historical-name rows
  - Status (row level): REGD 4,129,666 · DRGD 231,738 · SOFF 46,520 · EXAD 40,575 · NOAC 490 · CNCL 59 · DISS 1
  - Registration dates 1817-04-08 (Westpac, genuine) to 2026-10-05; 4 companies with missing registration date
  - DRGD rows without a date (20,533) are all historical-name rows → 0 after dedup
- [x] README project guide written (data quality log + decisions log filled).
- [x] KPI spec v1 finalised (2026-10-10): exposure denominator, age bands, distress denominator, age-adjusted RRI, reliability flag, caveats.
- [x] GitHub repo created; CONTEXT.md set up; repo connected to Databricks as a Git folder.
- [x] Unity Catalog structure created (2026-10-13): 3 schemas + volume `sme_risk_bronze.source_systems`.
- [x] **Bronze layer complete (2026-10-13)** — `notebooks/bronze_ingest` (was 01_ingest_bronze):
  - First snapshot `2026-10-12`: **4,450,307 rows · 4,016,371 distinct ACNs** (vs 8 Oct profiling: +1,258 rows, +1,337 ACNs — newer weekly file)
  - All checks passed (header, raw line count, 14 tabs per line); descriptions visible in Catalog Explorer
- [x] Silver profiling + decisions done for `company_name`, `acn`, `company_type` (2026-10-13); README §3.2 data dictionary, §3.3 profiling notes, §4.1 UC structure, DQ log and decisions log updated.

## 4. Current State (WIP)
- **Active Task:** Phase 5 – Analysis in `notebooks/gold_analysis.ipynb` (not in the job), **one business question at a time**:
  1. Q1 survival to years 1, 2, 5 (all companies vs Trading) + checks on the age 2–3 peak ← **in progress (queries given 2026-10-25)**
  2. Q2 which borrower segments deregister earliest (needs RRI horizon decision: S(2) vs S(3)/S(5))
  3. Q3 within Trading: ABN held, name change, ACN-named
  4. Q4 distress share (SOFF + EXAD) by segment × age
  5. Q5 is early-stage risk changing over time (limited: one year of deregistrations; weekly snapshots build history in Bronze)
  6. Q6 recommendations (tighten / relax criteria)
- **First result (12 Oct snapshot, all companies, annual deregistration probability q by age):** 0–1 0.81% · 1–2 2.78% · **2–3 13.93%** · 3–4 7.90% · 4–5 7.13% · 5–10 6.24% · 10+ 4.64%. Implied S(2) ≈ 96.4%, S(5) ≈ 71%. Low first-year rate likely reflects deregistration lag (unverified). Age 2–3 peak cause unverified.
- **Data now:** Bronze holds snapshots 2026-10-12 and **2026-10-19** (4,452,194 rows · 4,018,291 ACNs); Silver/Gold rebuilt from 2026-10-19 (≈4,018,252 companies; 212,050 DRGD; May 2026 deregistrations 38,698). README §3 figures stay labelled as the 2026-10-12 baseline.
- **Notebooks (`notebooks/`, lowercase since 2026-10-25):** pipeline = `bronze_ingest`, `silver_transform`, `gold_build` (has hard-stop cell + table/column comments); analysis only = `silver_profile` (reordered: raw profiling → cleaning → after-cleaning check), `gold_analysis` (new).
- **Fixed 2026-10-25:** `company_name_has_export_artifact` searched `°` (U+00B0) but the file has `º` (U+00BA) → now `rlike('[\u00BA\u00B0]')`; expect 1 current company (PILOTPATH, ACN 696299475).
- **Working rules:** discuss findings first, ask before giving transformation code (profiling/inspection code can be given directly). Pull before working on either side (Mac or Databricks), push when done.
- **Repo state (2026-10-25):** GitHub has `notebooks/` + `jobs/sme_risk_weekly_pipeline.yml` + `.databricks/commit_outputs` (lowercase paths, all 4 notebooks). **Notebook outputs still not appearing on GitHub** even after Run all + commit with the admin setting on — unresolved, parked by user. User's Mac copy is out of date (old `Notebooks/` folder) — sync later: `git checkout -- .databricks/commit_outputs && rm -rf Notebooks && git pull`.
- **Open Questions / Blockers:**
  - Notebook outputs not committed to GitHub (parked)
  - Reliability thresholds (100 company-years / 10 deregistrations) to review in Q2
  - RRI horizon S(2) vs S(3)/S(5)
  - ABS context data (optional); RAG / vector search idea parked

## 5. Next Immediate Step
1. Run Q1 cells A (survival table), B (age 2–3 by deregistration month), C (age 2–3 by registration month) in `gold_analysis`; interpret; write Q1 answer into README §7.
2. Add job schedule (Wed 07:00 Sydney) + failure email; re-export YAML to `jobs/`.
3. Then Q2 (segments) after deciding the RRI horizon.
