# Which New Businesses Are Riskiest to Lend To?
### SME Business Survival Analytics on Australian Public Data

> Which new Australian businesses are riskiest to lend to? End-to-end analytics on 4M+ ASIC company records using Databricks, PySpark, dbt and Streamlit.

> **Status:** 🟡 In progress  |  **Current phase:** Phase 3 – Silver (in progress)  |  **Last updated:** 2026-10-13

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
- [x] First Bronze snapshot (`2026-10-12`, loaded 2026-10-13): **4,450,307 rows · 4,016,371 distinct ACNs** (newer weekly file than the 8 Oct profiling: +1,258 rows, +1,337 ACNs)

> **Impact of coverage:** companies deregistered more than a year ago are not in the file, so long-run survival cannot be measured directly from registration cohorts (survivorship bias). See Section 5 and the Decisions Log for the adjusted method.

**Known field rules (from ASIC data dictionary):**
- `Status`: REGD registered, DRGD deregistered, EXAD external administration, SOFF strike-off in progress, NOAC not active, plus rarer codes
- `ABN` = `0` means the company has no ABN
- `Current Name Indicator` = `Y` marks the current-name row; null rows are historical names → deduplicate on ACN
- For `Type = RACN`, the ACN field holds an ARBN

### 3.2 Data dictionary (Bronze: `asic_companies_raw`)

All source columns are stored as `STRING` in Bronze (names snake_cased). Full descriptions are applied as Unity Catalog column comments from the ASIC help file (Appendix Item 2).

| Bronze column | Silver name | Description (short) | Profiling notes |
|---|---|---|---|
| company_name | company_name | Name as on the ASIC register | See §3.3 |
| acn | acn | 9-digit ACN (ARBN for type RACN) | 100% valid incl. check digit; 15% leading zeros |
| type | company_type | APTY / APUB / FNOS / RACN (+ CCIV, undocumented) | Clean; APTY ≈ 99% of companies |
| class | company_class | Liability class (LMSH, LMGT, LMSG, NLIA, UNLM, NONE) | Clean; NONE = exactly FNOS + RACN |
| sub_class | company_sub_class | 18 documented codes (+ WHSL, undocumented) | Clean; PROP 87%, PSTC (super trustee) 12% |
| status | status_code | REGD, DRGD, EXAD, SOFF, NOAC, CNCL, DISS, … | Clean; status is authoritative over dates |
| date_of_registration | registration_date | DD/MM/YYYY text → DATE | 4 missing; 0 bad format/unparseable; 1817-04-08 to snapshot date |
| date_of_deregistration | deregistration_date | DD/MM/YYYY text → DATE (DRGD only) | 0 bad format/unparseable/future/before registration; only past-year deregistrations in file |
| previous_state_of_registration | previous_state | State of registration before the 1991 national scheme | 95% null; 47 trailing spaces; NFK = Norfolk Island; **not current location** |
| state_registration_number | state_registration_number | Original state registry number | 200,758 filled; 131,697 contain letters → text; 147 without a state; Silver only |
| modified_since_last_report | modified_since_last_report | Y / null → BOOLEAN | 15,008 Y; pipeline use only |
| current_name_indicator | current_name_indicator | Y = current-name row; null = former-name row | Used for dedup (one Y per ACN) |
| abn | abn | ABN; `0` = no ABN → null | 1,631,164 `0` (41%); all real ABNs valid (format + check digit), none shared |
| current_name | current_name | Current name, on former-name rows only | Dropped after dedup |
| current_name_start_date | current_name_start_date | Start date of current name, on former-name rows only | Dropped after dedup |
| _snapshot_date, _source_file, _source_url, _ingested_at | (kept: `_snapshot_date`) | Load metadata | — |

### 3.3 Silver column profiling & transformation notes

Method per column: **profile → decide → transform → verify**. Profiling run on the 2026-10-12 snapshot (4,450,307 rows, before dedup).

#### `company_name`
| Finding | Count | Decision |
|---|---|---|
| Nulls / blanks / lowercase / control chars / encoding errors | 0 | Nothing to fix |
| Leading or trailing spaces | 45,798 | Trim |
| Double spaces | 46,776 | Collapse to one space |
| **CSV escaping** – value wrapped in `"` with inner quotes doubled | 429 (all balanced) | **Decode** (strip outer quotes, `""` → `"`). Verified on ASIC register: ACN 106 366 090 = `GO "N" OFF PTY LTD`; ACN 101 413 405 = `"WEOWNA" PILOT SERVICE PTY. LTD.` Also confirms why Bronze reads with quoting off |
| Asterisks `*` | 121 (80 on current-name rows, 41 on former-name rows) | **Keep** – genuine (verified: ACN 097 927 029 = `CREATE*IT PTY LTD`). Former-name rows are dropped by dedup; meaning of `*` on those rows not needed (open question) |
| Non-ASCII characters | 4 (`º` ×3, `›` ×1); only 1 on a current-name row | `º` appears to replace `\|` in ASIC's export (ACN 696 299 475: file `PILOTPATH º PILOT TRAINING`, register `PILOTPATH \| PILOT TRAINING`). **Flag, don't change** (`company_name_has_export_artifact`) pending a pipe check |
| Names containing a 9-digit number | 20,767 | **Keep names unchanged.** 12,524 current-name rows contain the company's **own ACN** (+ ABN-style names, e.g. `19097396346 PTY LTD`) → new feature `is_acn_named`. 79 current-name rows contain another number (other company's ABN, swapped digits, vanity numbers) → ordinary names, kept |
| Length | 3–104 chars | No truncation |

Cleaning order: decode CSV escaping → strip control chars → trim → collapse spaces → blank to null. Same helpers (`unescape_csv`, `clean_text`) applied to `current_name`.

#### `acn`
| Finding | Result | Decision |
|---|---|---|
| Null / spaces / non-digits / not 9 chars | 0 | No transformation; keep as text |
| ASIC check-digit validation (weights 8…1) | **0 failures** (incl. RACN/ARBN rows) | Add hard stop in validation for future snapshots |
| Leading zeros | 669,562 (15%) | Confirms ACN must stay `STRING` |
| Distinct ACNs | 4,016,371 | Matches Bronze |
| `acn_is_arbn` flag | — | **Not added**; ARBN note goes in the column description (same info as `company_type = 'RACN'`) |

#### `company_type`
| Finding | Result | Decision |
|---|---|---|
| Null / spaces / lowercase / not 4 chars / not in dictionary | 0 | No cleaning; add readable label |
| Current-name rows by type | APTY 3,977,855 (~99%) · APUB 31,693 · FNOS 4,695 · RACN 2,078 · CCIV 11 | Type is a top-level filter only; detailed segmentation within APTY |
| Type × class (current) | APTY: LMSH 3,977,590 · UNLM 167 · LMSG 98. APUB: LMGT 25,557 · LMSH 6,005 · NLIA 65 · LMSG 57 · UNLM 9. CCIV: LMSH 11 | APTY + LMSG (98) doesn't fit current law as understood → likely older registrations; genuine, not errors (unverified) |
| Validation | — | Hard stop if a new type code appears that is not in the dictionary |

#### `company_class`
| Finding | Result | Decision |
|---|---|---|
| Null / spaces / lowercase / not 4 chars / not in dictionary | 0 | No cleaning; add readable label |
| Current-name rows by class | LMSH 3,983,606 · LMGT 25,557 · NONE 6,773 · UNLM 176 · LMSG 155 · NLIA 65 | — |
| Consistency | Class NONE (6,773) = FNOS (4,695) + RACN (2,078) exactly | Matches ASIC definition ("no Australian equivalent") |

#### `company_sub_class`
| Finding | Result | Decision |
|---|---|---|
| Null / spaces / lowercase / not 4 chars | 0 | No cleaning; add readable label |
| Codes not in ASIC help file | **WHSL** – 13 rows, all CCIV + LMSH | Add to dictionary as `WHSL (not in ASIC help file; likely wholesale CCIV)` – meaning inferred, not confirmed. Unknown codes → validation hard stop |
| Current-name rows by sub-class (top) | PROP 3,483,991 · **PSTC 488,022** · ULSN 18,734 · ULST 8,792 · NONE 4,588 · PNPC 3,205 · HUNT 2,636 · RACA 1,950 · LIST 1,716 · LISN 1,201 · NLTD 1,193 · RACO 127 | See segment decision below |
| APTY consistency | APTY rows carry proprietary sub-classes only (PROP, PSTC, PNPC, HUNT, EXPT 1) | Consistent |
| Not-for-profit check: APUB + LMGT (25,557) by sub-class | ULSN 18,686 (73%) · ULST 4,448 · LISN 1,201 · NLTD 1,193 · STFI 21 · ULSS 7 · LISS 1 | **Confirmed**: public companies limited by guarantee are mostly documented non-profits |

#### `status_code`
| Finding | Result | Decision |
|---|---|---|
| Null / spaces / lowercase / not 4 chars / not in dictionary | 0 | No cleaning; add readable label |
| Current-name rows by status | REGD 3,729,504 · DRGD 211,591 · SOFF 43,084 · EXAD 31,857 · NOAC 295 · DISS 1 · CNCL 0 | Distress pool (SOFF + EXAD) ≈ 75,000 |
| DRGD with a deregistration date | 211,591 of 211,591 | ✅ Survival analysis has an event date for every deregistration |
| Deregistration date on non-DRGD current rows | 9 (EXAD 7, REGD 1, DISS 1); was 10 on 8 Oct | Status authoritative; `deregistration_date` only for DRGD; raw kept as `deregistration_date_reported`; flag `dereg_date_status_conflict` |
| ACNs with no current-name row | **39, all CNCL** (CNCL appears only on former-name rows) | Dropped by dedup – harmless. Permanent hard stop: fail if any no-Y ACN is not CNCL (null-safe logic: `coalesce(indicator = 'Y', 0)`) |
| Crude status mix by sub-class (preview, not age-adjusted) | Deregistered: PNPC ~10%, HUNT ~8%, ULST ~6%, NLTD ~3%, LIST 0% | Segments differ → supports per-segment reporting. PROP vs PSTC comparison pending |

#### Dates (`registration_date`, `deregistration_date`)
| Finding | Result | Decision |
|---|---|---|
| Registration: missing / bad format / unparseable / after snapshot | 4 / 0 / 0 / 0 | Parse to DATE. The 4 missing (3 NOAC + 1 DRGD, very low ACNs) → age band "Unknown", excluded from age-based KPIs; **1 deregistration event lost** (negligible, documented) |
| Registration range | 1817-04-08 (Westpac) to 2026-10-12 (= snapshot date) | Plausible |
| Deregistration: bad format / unparseable / after snapshot / before registration / same day as registration | all 0 | Parse; filled only for DRGD (status authoritative); raw kept as `deregistration_date_reported` |
| Most common registration dates | Late June / 1 July each year (e.g. 30 Jun 2026: 3,568) | **Not placeholders** – end of Australian financial year effect. No 01/01-style placeholder spikes |
| Deregistrations per month (snapshot 2026-10-12) | Typical 12k–21k; **May 2026: 38,738** (~2×); Oct 2025 9,514 and Oct 2026 6,845 are partial edge months. Sum = 211,591 = all DRGD | May spike possibly an ASIC batch of strike-offs (**unverified** – data can't separate voluntary vs ASIC-initiated). Annotate on monthly charts |
| Companies by registration year | Rises steeply to ~365k (2025) | **Survivorship:** counts only companies still in the file (plus last-year deregistrations) – label as "companies on today's register, by registration year", never "registrations per year" |
| Observation window | Earlier hard-coded 2025-10-06 → 2026-10-04 (8 Oct file) | **Changed:** window is computed per snapshot (min/max DRGD deregistration date) because the rolling year moves weekly |

#### Agreed decisions – dates (2026-10-13)
1. `registration_date`: parse; 4 missing → "Unknown" age band, excluded from age KPIs.
2. `deregistration_date`: parse; DRGD only; raw as `deregistration_date_reported`.
3. `current_name_start_date`: dropped after dedup (former-name rows only).
4. Observation window computed from each snapshot, not hard-coded.
5. Validation hard stops: any unparseable date, any date after the snapshot date, any deregistration before registration.
6. App/Gold notes: 30 June registration effect; May 2026 deregistration spike annotated; survivorship labelling.

#### `previous_state`, `state_registration_number`, `modified_since_last_report`, `abn`
| Finding | Result | Decision |
|---|---|---|
| `previous_state` filled | 200,611 (5%): VIC 67,121 · NSW 64,968 · QLD 23,426 · WA 20,846 · SA 15,222 · ACT 4,194 · TAS 3,243 · NT 1,533 · NFK 58 | Trim; add labels; hard stop on unknown codes |
| Duplicate SA / WA / NT codes | 47 rows with a trailing space (hex `20`) | Fixed by trim |
| Meaning | State of registration **before the 1991 national scheme** – earliest registration 1848 (NSW) | **Not current location** – the ASIC file has no current-location field, so no "risk by state" view |
| `previous_state` with registration date ≥ 1991 | 333: 275 state (VIC 131, QLD 55, NSW 34, WA 26, SA 16, TAS 8, ACT 4, NT 1) + all 58 NFK on **2021-08-02** | Registration date probably = date joined the ASIC register, so age understated. 0.008% – documented, not flagged. NFK single-date transfer: reason unverified |
| `state_registration_number` | 200,758 filled; 131,697 contain letters (e.g. `C0279655C`); 147 without a previous state (sample registered 2000–01; reason unverified) | Trim; keep as text; no format check; Silver only (not in Gold) |
| `modified_since_last_report` | Y 15,008; null 4,001,324 | Y → true, null → **false** (`coalesce` – plain `== 'Y'` returns null). Pipeline use only |
| `abn` = `"0"` | 1,631,164 (41%) | → null; `has_abn` flag |
| `abn` format / check digit / shared ABNs | 0 / 0 / 0 | Drop `abn_format_valid`; hard stops on all three |
| ABN built from own ACN (`xx` + ACN) | 2,384,902 of 2,385,168; **266 not** – charities (Coeliac Australia), foreign companies (Standard Chartered Bank), some PROP | Genuine – likely an ABN held before becoming a company (unverified). No flag |
| % with ABN by status | REGD 58.5 · DRGD 69.0 · SOFF 68.6 · EXAD 86.4 · NOAC 23.4 | Missing ABN is **not** a distress signal at headline level |
| % with ABN by sub-class | PSTC 9.3 · PROP 66.2 · ULSN 87.1 · LIST 99.4 · RACA 30.3 | Super trustees (fund holds the ABN) drag REGD down → ABN = "trading vs dormant" indicator |

#### Agreed decisions – remaining columns (2026-10-13)
1. `previous_state`: trim, labels (NFK = Norfolk Island), hard stop on unknown codes; documented as not current location; 333 post-1991 registrations documented.
2. `state_registration_number`: trim, text, Silver only.
3. `modified_since_last_report`: Y → true, null → false.
4. `abn`: `"0"` → null; `has_abn`; hard stops (11 digits, check digit, unique); no `abn_format_valid`, no `abn_derived_from_acn`.
5. Gold: ABN rate only within segment; test ABN × status inside Trading.

#### Agreed decisions – class, sub-class and borrower segment (2026-10-13)
1. **`company_class`:** no cleaning; add readable label.
2. **`company_sub_class`:** no cleaning; add WHSL to the dictionary with a "not in ASIC help file" label; unknown codes stop the load.
3. **Borrower segment** derived from type + sub-class:
   - **Trading company:** APTY + PROP (core SME borrower)
   - **Super trustee:** PSTC (~12% of companies; trustees of super funds, not trading businesses)
   - **Not-for-profit:** ULSN, PNPC, NLTD
   - **Home unit:** HUNT (administers a residential building)
   - **Other public / Foreign (FNOS) / Registrable body (RACN) / CCIV**
4. **Built in Gold**, not Silver: the segment lives in `dim_company_classification` (dbt), because it is a business grouping that may change; Silver keeps clean codes + labels.
5. **Keep everyone in the population, but segment:** no exclusions for super trustees, not-for-profits or home units. Results shown per segment; the app defaults to **Trading company**.

#### Analysis notes to revisit in Gold
- **`is_acn_named` looks like a strong risk signal:** of 12,524 current ACN-named companies, ~13% are deregistered (1,648) and ~7.7% in external administration (965), vs roughly 5% and 1% across all companies. **Not a finding yet** – must be tested with the age-adjusted RRI (numbered companies may be older or a different mix).
- **APUB + LMGT (25,557) are mostly not-for-profits** (charities, clubs, associations) – likely a separate borrower segment; confirm with sub-class (ULSN).
- **APTY ≈ 99%** → type adds little separation; the app's type filter is essentially "proprietary vs other".
- **CCIV (11)** will be suppressed by the reliability flag.
- **Super trustee companies (PSTC, ~12%)** likely behave very differently from trading companies (long-lived, rarely trade) – mixing them in would distort survival curves and risk rankings; hence segment-level results.
- **Home unit (HUNT) and not-for-profit companies** are not typical SME borrowers – shown as separate segments.
- **30 June effect:** registrations cluster around the end of the financial year – possible insight for the overview page.
- **May 2026 deregistration spike (38,738, ~2× normal):** annotate on trend charts; cause unverified.
- **Survivorship:** never present "companies by registration year" as registration volumes.
- **ABN held:** 9.3% of super trustees vs 66.2% of proprietary companies – compare within segment only; test whether no-ABN trading companies deregister more (dormant shells) or less.
- **No geography:** `previous_state` is pre-1991 history, not location – state-level risk needs another source (e.g. ABN Bulk Extract, parked).
- Companies with **no current-name row** are dropped by dedup (39 ACNs, all CNCL, in the 8 Oct profiling) – re-check on each snapshot that none are in the lending population.

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

### 4.1 Unity Catalog structure

```
catalog: workspace
  ├── sme_risk_bronze
  │     ├── source_systems (VOLUME)   asic_companies/snapshot_date=YYYY-MM-DD/<file> + _metadata.json
  │     └── asic_companies_raw        all weekly snapshots, source columns as STRING
  ├── sme_risk_silver
  │     └── companies                 one row per company, latest snapshot (4,016,332 rows on 2026-10-12)
  └── sme_risk_gold                   star schema (gold_build notebook, Spark SQL)
        dims:  dim_company (4,016,332), dim_company_classification (35), dim_status (6),
               dim_age_band (8), dim_date (76,702)
        facts: fct_company_snapshot (company × snapshot), fct_exposure (company × age band × snapshot)
```

**Load patterns:** Bronze = add each weekly snapshot (`replaceWhere` on `_snapshot_date`, idempotent) · Silver = overwrite from the latest snapshot (source is a full copy; also removes companies ASIC drops) · Gold = every table rebuilt from Silver (overwrite); Gold reflects the latest snapshot. **History is kept only in Bronze** (all weekly snapshots).

### 4.2 Repository structure [TODO – update as built]

```
├── README.md                # this file
├── CONTEXT.md               # working memory between sessions
├── Notebooks/
│   ├── bronze_ingest.ipynb      # download + Bronze load (pipeline)
│   ├── silver_transform.ipynb   # Silver pipeline (pipeline)
│   ├── silver_profile.ipynb     # Silver column profiling – evidence only, not in the job
│   └── gold_build.ipynb         # Gold star schema: 5 dims + 2 facts (pipeline)
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
| 2. Bronze | Databricks workspace and Unity Catalog set up | ✅ | 2026-10-13 | 3 schemas + `source_systems` volume; repo connected as Git folder |
| 2. Bronze | Ingestion jobs (Python / PySpark) | ✅ | 2026-10-13 | `bronze_ingest`; snapshot 2026-10-12 loaded, all checks passed |
| 3. Silver | Cleaning, typing, deduplication (PySpark) | ✅ | 2026-10-13 | `workspace.sme_risk_silver.companies` written: 4,016,332 rows (snapshot 2026-10-12); all 19 hard stops passed. Profiling kept in `silver_profile.ipynb` |
| 3. Silver | Data quality checks logged | ⬜ | | |
| 4. Gold | Star schema: 5 dimensions + 2 facts (Spark SQL) | ✅ | 2026-10-24 | `gold_build.ipynb`; every key links, totals tie back to Silver |
| 4. Gold | First KPI results | 🟡 | 2026-10-24 | Annual deregistration probability by age; age 2–3 peak under investigation |
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
| 2026-10-13 | Bronze load checks | Header (15 cols), raw line count, 14 tabs per line | All | All passed for snapshot 2026-10-12 |
| 2026-10-13 | company_name | Leading/trailing spaces; double spaces | 45,798 / 46,776 | Trim; collapse spaces |
| 2026-10-13 | company_name | CSV escaping kept as literal text (outer quotes, doubled inner quotes) | 429 | Decode in Silver; verified against ASIC register |
| 2026-10-13 | company_name | Asterisks | 121 | Kept – genuine (verified `CREATE*IT PTY LTD`) |
| 2026-10-13 | company_name | `º` appears to replace `\|` in export; `›` unexplained | 4 (1 current-name row) | Flagged (`company_name_has_export_artifact`), not changed |
| 2026-10-25 | company_name | **Bug:** flag searched for `°` (U+00B0, degree) but the file has `º` (U+00BA, masculine ordinal) → flag was 0 for every company | 1 current-name row missed | Fix: match both characters `[º°]`; rerun Silver and Gold |
| 2026-10-13 | acn | Format + ASIC check digit | 0 failures | No change; hard stop added for future snapshots |
| 2026-10-13 | company_type | Format / unknown codes | 0 | No change; CCIV undocumented in help file |
| 2026-10-13 | company_class | Format / unknown codes | 0 | No change; NONE = FNOS + RACN |
| 2026-10-13 | company_sub_class | Undocumented code WHSL (CCIV) | 13 rows | Added to dictionary with inferred label |
| 2026-10-13 | status_code | Deregistration date on non-DRGD companies | 9 | Status authoritative; flagged |
| 2026-10-13 | status_code | ACNs without a current-name row | 39 (all CNCL) | Dropped by dedup; hard stop if any non-CNCL appears |
| 2026-10-13 | registration_date | Missing | 4 (3 NOAC, 1 DRGD) | Age band "Unknown"; excluded from age KPIs |
| 2026-10-13 | dates | Format / parse / future / dereg-before-reg | 0 | Hard stops added for future snapshots |
| 2026-10-13 | previous_state | Trailing space on SA / WA / NT | 47 | Trimmed |
| 2026-10-13 | previous_state | Registered ≥ 1991 despite a previous state (incl. 58 NFK on 2021-08-02) | 333 | Documented; age may be understated |
| 2026-10-13 | state_registration_number | Number without a previous state | 147 | Documented; Silver only |
| 2026-10-13 | abn | `0` placeholder for no ABN | 1,631,164 | → null; `has_abn` |
| 2026-10-13 | abn | Format / check digit / shared | 0 | Hard stops added |

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
| 2026-10-13 | Bronze: add each weekly snapshot (`replaceWhere` per `_snapshot_date`) | Full overwrite; upsert (MERGE) on ACN | Keeps every file as received; upsert would overwrite status history |
| 2026-10-13 | Silver: overwrite from the latest snapshot | Upsert on ACN | Source is a full copy each week; overwrite also removes companies ASIC drops after a year (upsert would keep stale rows) |
| 2026-10-13 | Bronze CSV read with quoting off (`quote=""`) | Spark default `"` quoting | Values are not reliably quoted; decoding of CSV escaping done in Silver instead |
| 2026-10-13 | Silver: filter to the latest snapshot | Use all Bronze rows | Bronze holds one copy per week; mixing weeks would multiply companies |
| 2026-10-13 | Combine PySpark (multi-column cleaning, dictionaries) and SQL (dedup, business rules) via a temp view | All PySpark / all SQL | Each used where it is clearest |
| 2026-10-13 | Dedup on ACN keeping the current-name row; former names → `name_change_count` | Replace former-name text with current name | Keeps meaning of rows; outcome identical |
| 2026-10-13 | Keep names unchanged apart from verified decoding/formatting; add `is_acn_named` | Strip numbers / asterisks | Official names preserved; feature tested later in Gold |
| 2026-10-13 | Do not add `acn_is_arbn`; note in column description | Separate flag | Same information as `company_type = 'RACN'` |
| 2026-10-13 | Gold star schema: 5 dimensions, 3 facts, 3 marts | More granular dims | Single-source dataset; avoids over-modelling |
| 2026-10-13 | Borrower segment (Trading / Super trustee / Not-for-profit / Home unit / Other public / Foreign / Registrable body / CCIV) from type + sub-class | Use type only; exclude non-trading companies | Type is 99% APTY; sub-class reveals 12% super trustees and other non-trading entities |
| 2026-10-13 | Build the segment in Gold (`dim_company_classification`), not Silver | Silver column | Business grouping may change; Silver stays close to source |
| 2026-10-13 | Keep all segments in the population; app defaults to Trading company | Exclude super trustees / not-for-profits | Transparent; results comparable across segments |
| 2026-10-13 | Compute the observation window from each snapshot (min/max DRGD date) | Hard-coded 2025-10-06 → 2026-10-04 | ASIC's rolling year moves every week; hard-coding would break the weekly pipeline |
| 2026-10-13 | Treat `has_abn` as a trading-vs-dormant indicator, analysed within segment | Headline "no ABN = risky" | Distressed companies hold ABNs more often than REGD; PSTC (9.3%) distorts the overall rate |
| 2026-10-13 | No state/geography dimension | Use `previous_state` | It is pre-1991 registration history, not current location |
| 2026-10-24 | Gold = star schema (5 dims, 2 facts) built with Spark SQL in a notebook | dbt project with marts | Simpler to build and explain; same Delta tables; dbt can be added later |
| 2026-10-24 | Readable, stable keys: ACN as BIGINT, code-based keys, YYYYMMDD date keys (0 = no date) | Hash or ROW_NUMBER keys | Positive and readable; same every week so snapshot history keeps joining |
| 2026-10-24 | All Gold tables overwritten from Silver (Gold mirrors the latest snapshot) | Facts append weekly + dimensions MERGE | Dims and facts always consistent; KPIs (period method) need only the latest snapshot; history already kept in Bronze |

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
| 2026-10-13 | Bronze complete; data dictionary, UC structure, Gold model added; Silver profiling notes for company_name, acn, company_type |
| 2026-10-13 | Silver notes for company_class, company_sub_class; borrower segment decisions |
| 2026-10-13 | Silver notes for status_code, dates, previous_state, state_registration_number, modified_since_last_report, abn; all columns profiled |
| 2026-10-13 | Silver complete (4,016,332 rows, 19/19 hard stops); profiling split into its own notebook |
| 2026-10-24 | Gold star schema built (5 dims, 2 facts); first survival result by age band |
