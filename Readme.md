# Which New Businesses Are Riskiest to Lend To?
### SME business-survival analytics on the Australian company register

*Which young Australian companies are most likely to stop operating, and where should a lender tighten its criteria? An end-to-end project from the public ASIC company register to a Databricks lakehouse, a star schema, SQL survival analysis, lending recommendations and an interactive app.*

**[▶ Open the live app](https://sme-lending-risk-analytics.streamlit.app/)** · **[Databricks App (live tables)](DATABRICKS_APP_URL)** · **[Code](https://github.com/manaswinidoma/sme-lending-risk-analytics)**

---

## Background and Overview

Banks and other lenders have very little history to judge a newly established business: no long trading record, often no financial statements, and no repayment history. Yet young companies make up a large part of the market. In the Australian company register, **half of all active companies are 7 years old or younger**.

This project uses the **ASIC Company Dataset**, the public register of every company in Australia (about **4.46 million records**, published weekly on data.gov.au), to measure **how likely companies are to be deregistered** at each age, by type of company and by warning signs a lender can see on an application.

**Stakeholder:** SME Credit Risk / Business Lending team, who set the bank's risk appetite and lending criteria for young businesses.

**The decision:** which kinds of new business should get standard lending criteria, which need extra checks or tighter terms, and which should be declined or referred?

**Why it matters:** about **1 in 18** Australian companies is deregistered in a typical year, and about **3 in 10** new companies are gone within 5 years. Applying the same criteria to every young company either turns away good borrowers or under-prices risky ones.

**Questions this project answers**
1. **When is a new company most at risk?** How likely is it to still be registered after 1, 2 and 5 years, and which age is the riskiest?
2. **Which types of company, and which warning signs, carry the most risk?** Borrower segments, then ABN held, name changes and numbered (ACN-named) companies within trading companies, compared on an age-adjusted basis.
3. **Where should lending criteria be tightened or relaxed?** A risk-tier table of borrower profiles, validated against actual outcomes, plus red-flag rules and a company lookup.

> **Important framing:** deregistration is used as a **proxy for a business stopping**. It is **not** the same as loan default: companies can also close voluntarily, merge or restructure. ASIC publishes only **the last 12 months** of deregistrations, so risk is measured with a period method (the last 12 months' rates at each age), not by following companies from birth.

---

## Executive Summary

**Headline numbers** (ASIC snapshot of **9 November 2026**; observation window **10 Nov 2025 – 9 Nov 2026**)

| Companies | Active | Distressed (strike-off / administration) | Deregistered in last 12 months | Company-years at risk | Yearly deregistration probability |
|---|---|---|---|---|---|
| 4,024,917 | 3,811,222 | 75,054 (1.97% of active) | 213,694 | 3,726,156 | **5.57%** |

**Key findings**
- **The third year is the danger zone.** A company aged 2–3 has a **14.0%** chance of being deregistered that year (trading companies **14.9%**), about **5× the year before**. It is the riskiest age for every segment, and it stays the riskiest after removing a large administrative batch of deregistrations.
- **About 3 in 10 new companies are gone within 5 years.** Survival is 99.2% at year 1, 96.4% at year 2, **82.9% at year 3** and **70.9% at year 5** (trading companies 69.2%).
- **A numbered company name is the strongest warning sign.** Trading companies with their ACN as their name are **twice as likely** to be deregistered within 5 years (**61.1% vs 30.8%**), and up to **7.6×** the average yearly risk at age 2–3.
- **Super trustee companies carry half the average risk** (risk index **0.46**). Leaving them in "all companies" makes risk look lower than it is for real trading businesses.
- **Risk tiers separate risk well.** The High and Elevated tiers cover **16% of trading-company exposure but 34% of deregistrations**; the High tier alone has a **lift of 3.06×**.
- **70,918 trading companies are currently in strike-off or external administration.**

**Recommendation:** **Tighten criteria for trading companies in their third year and for numbered companies aged 2+, monitor companies aged 3–5, keep standard criteria for established companies, and check ASIC status before every approval and during the loan.**

---

## The App

The results are published as a six-page **Streamlit** app, built once and deployed twice:

| | Where | Data | Refresh |
|---|---|---|---|
| **[Public app](https://sme-lending-risk-analytics.streamlit.app/)** | Streamlit Community Cloud | Parquet exports of the report tables in [`app/data/`](app/data/), queried with DuckDB | Fixed snapshot (9 Nov 2026) |
| **[Databricks App](DATABRICKS_APP_URL)** | Databricks Apps (needs workspace access) | Live `rpt_*` tables through a SQL warehouse | Weekly, after the pipeline runs |

| Page | What it answers |
|---|---|
| **Overview** | Headline numbers, three findings a lender should know, monthly deregistrations, risk tiers vs outcomes |
| **When is risk highest?** | Survival curve and yearly risk by age, with a toggle that removes the May–June 2026 batch |
| **Who is riskiest?** | Age-adjusted risk index by type of company and by warning sign |
| **Risk tiers** | The 28 borrower profiles on a profile map, the lift check and the red-flag override |
| **Company lookup** | Any ACN or company name → lending tier, recommended action and the reason for it |
| **About & method** | Data, pipeline, formulas, definitions and caveats |

<p align="center"><img src="images/01_overview.png" alt="Overview page" width="900"></p>

<details>
<summary>More screenshots</summary>

**When is risk highest?**
<img src="images/02_when_risk.png" alt="When is risk highest page" width="900">

**Who is riskiest?**
<img src="images/03_who_risk.png" alt="Who is riskiest page" width="900">

**Risk tiers**
<img src="images/04_risk_tiers.png" alt="Risk tiers page" width="900">

**Company lookup**
<img src="images/05_company_lookup.png" alt="Company lookup page" width="900">
</details>

---

## Insights

### 1. Almost every company survives two years, then risk jumps in year three

Survival curves were built with an exposure-based period life table: for each age band, the yearly deregistration probability is `q = 1 − e^(−deregistrations ÷ company-years at risk)`, and survival to year *N* is the product of `(1 − q)` for each year.

Almost every company is still registered after two years (**96.4%**). Then there is a cliff: **about 1 in 7 companies still registered at year 2 are gone by year 3**. After year 3 the curve keeps falling, more gently, reaching **70.9%** at year 5. Trading companies sit slightly below the overall line at every age (69.2% at year 5), because the overall figure includes the much safer super trustee companies.

The first two years look very safe partly because **deregistration lags real failure**: striking a company off takes time (unpaid fees, notices, waiting periods), so a business that stops early often only shows up as deregistered in its second or third year. **A low first-year rate does not mean new companies are low risk; the risk shows up a little later.**

**Is the peak real?** Deregistrations are processed in batches (see *Data exploration* below), including an unusually large run in May–June 2026. Recalculating survival after removing **every** deregistration processed in May–June 2026 (a deliberately harsh test that also removes normal ones), age 2–3 is **still the riskiest year (8.91% vs 5.58% for the next band)**. The true 5-year survival lies between **70.9% and 79.2%**.

<details>
<summary>See the numbers</summary>

| Age | Yearly deregistration rate | Yearly probability (all) | Survival (all) | Yearly probability (trading) | Survival (trading) |
|---|---|---|---|---|---|
| 0–1 years | 0.84% | 0.84% | 99.2% | 0.87% | 99.1% |
| 1–2 years | 2.83% | 2.79% | 96.4% | 3.03% | 96.1% |
| 2–3 years | 15.08% | **14.00%** | **82.9%** | **14.92%** | **81.8%** |
| 3–4 years | 8.28% | 7.94% | 76.3% | 8.44% | 74.9% |
| 4–5 years | 7.40% | 7.13% | **70.9%** | 7.59% | **69.2%** |

**Sensitivity: without the May–June 2026 batch**

| Survive to year | Yearly probability | Yearly probability, excl. batch | Survival | Survival, excl. batch |
|---|---|---|---|---|
| 1 | 0.84% | 0.71% | 99.2% | 99.3% |
| 2 | 2.79% | 2.39% | 96.4% | 96.9% |
| 3 | 14.00% | 8.91% | 82.9% | 88.3% |
| 4 | 7.94% | 5.58% | 76.3% | 83.4% |
| 5 | 7.13% | 4.94% | 70.9% | 79.2% |

**Riskiest age band:** 2–3 years for trading companies (14.92%) and for all other segments combined (6.69%).

- The rate (`deregistrations ÷ company-years`) and the probability (`1 − e^(−rate)`) are almost identical except at age 2–3 (15.08% vs 14.00%).

*Source: report table `rpt_survival_curve` (from the Q1 analysis on `fct_exposure`)*
</details>

### 2. Numbered trading companies are twice as risky; super trustees half as risky

Segments differ in age (not-for-profits and super trustees tend to be older), and age drives risk, so comparing raw shares would mislead. Each group is compared on its **chance of being deregistered within 5 years, `1 − S(5)`**, built from the group's own rate in each age band. The **relative risk index** divides that by a benchmark: 1.0 = average, above 1.25 = higher risk, below 0.80 = lower risk. A group needs at least 100 company-years and 10 deregistrations in every age band, otherwise it is shown as *not enough data*.

**By segment**, trading companies (87% of all companies and the main SME borrowers) sit just above average (**1.06**). Super trustee companies carry **less than half** the average risk (**0.46**). Not-for-profits look safer on a raw count but are **exactly average once age is accounted for (1.00)**, because many are old: a clear example of why the age adjustment matters.

**Within trading companies**, a **numbered name** (the company's ACN used as its name, e.g. `123 456 789 PTY LTD`) is the strongest warning sign: **61.1%** are gone within 5 years against **30.8%** for all trading companies, a risk index of **1.99**, based on 624 deregistrations with enough data in every age band. Trading companies **with an ABN** are riskier (1.12) than those without (0.72); a likely reading is that companies that actually trade can fail, while many no-ABN companies are passive holding vehicles. Since loan applicants almost always hold an ABN, the higher figure is the realistic benchmark for lenders.

**Current distress** (strike-off or external administration) among active trading companies is **1.74%** under 5 years, **2.85%** at 5–10 years and **2.17%** at 10+ years, against 0.5–0.8% for super trustees. Young companies show *less* current distress, consistent with the delay before strike-off begins.

<details>
<summary>See the numbers</summary>

**Borrower segments (benchmark: all companies)**

| Segment | Company-years (age 0–5) | Deregistrations (age 0–5) | Survival to year 5 | Deregistered within 5 years | Risk index | Flag |
|---|---|---|---|---|---|---|
| All companies | 1,439,324 | 90,378 | 70.9% | 29.1% | 1.00 | benchmark |
| Trading company | 1,259,716 | 85,355 | 69.2% | 30.8% | 1.06 | Around average |
| Super trustee | 167,208 | 4,160 | 86.5% | 13.5% | **0.46** | **Lower risk** |
| Not-for-profit | 7,167 | 454 | 70.8% | 29.2% | 1.00 | Around average |
| Other public | 2,514 | 205 | 64.8% | 35.2% | 1.21 | Around average |
| Home unit | 822 | 153 | 35.6% | 64.4% | – | Not enough data |
| Foreign company | 1,381 | 48 | 83.9% | 16.1% | – | Not enough data |
| Registrable body | 505 | 3 | 97.0% | 3.0% | – | Not enough data |
| CCIV | 10 | 0 | 100.0% | 0.0% | – | Not enough data |

**Warning signs within trading companies (benchmark: all trading companies)**

| Signal | Group | Company-years (age 0–5) | Deregistrations (age 0–5) | Deregistered within 5 years | Risk index | Flag |
|---|---|---|---|---|---|---|
| Benchmark | All trading companies | 1,259,716 | 85,355 | 30.8% | 1.00 | |
| Name type | **Numbered (ACN in name)** | 3,960 | 624 | **61.1%** | **1.99** | **Higher risk** |
| Name type | Named | 1,255,756 | 84,731 | 30.7% | 1.00 | Around average |
| ABN held | Has ABN | 834,259 | 66,325 | 34.6% | 1.12 | Around average |
| ABN held | No ABN | 425,457 | 19,030 | 22.3% | 0.72 | Lower risk |
| Name history | Renamed | 33,699 | 1,791 | 21.4% | 0.70 | Lower risk* |
| Name history | Never renamed | 1,226,017 | 83,564 | 31.1% | 1.01 | Around average |

\*Name history is recorded at the snapshot, and deregistered companies can no longer rename, so this comparison leans towards survivors. It is not used as a lending signal.

**Current distress share of active companies**

| Segment | Under 5 years | 5–10 years | 10+ years |
|---|---|---|---|
| Trading company | 1.74% | 2.85% | 2.17% |
| Super trustee | 0.53% | 0.72% | 0.75% |
| Not-for-profit | 1.45% | 1.60% | 1.37% |

*Source: report table `rpt_segment_risk` (from the Q2 analysis on `fct_exposure`, `fct_company_snapshot`, `dim_company`)*
</details>

### 3. Risk tiers: 16% of trading companies account for 34% of deregistrations

Every trading company was placed in one of **28 borrower profiles**: age band × numbered or named × ABN held or not, which are the three things a lender knows from an application. Each profile's yearly deregistration rate was compared with the trading-company average (**6.11% a year**) and placed in a tier:

| Tier | Rule (multiple of the trading-company average) | Suggested action |
|---|---|---|
| 🔴 High | above 2× | Decline or refer to senior credit |
| 🟠 Elevated | above 1.25× | Extra checks, tighter terms |
| 🟡 Standard | 0.8–1.25× | Standard criteria |
| 🟢 Low | below 0.8× | Standard criteria, faster approval |
| ⚪ Insufficient data | fewer than 100 company-years or 10 deregistrations | Manual assessment |

To avoid tiers driven by chance, a profile is only Elevated or High if the **lower end of its 95% interval** (`rate × e^(±1.96/√deregistrations)`) clears the cut-off, and only Low if the upper end is below 0.8×. The thresholds are illustrative policy defaults; a bank would set its own.

**High tier:** numbered trading companies aged 2–4 (with or without an ABN) and numbered companies with an ABN at any age from 4 (up to **7.6×** average, about **35–37% a year** at age 2–3), plus **named trading companies with an ABN in their third year** (3.05×, 17.0% a year). That second group is the largest high-risk group, with about **158,000** active companies.
**Elevated:** named companies with an ABN aged 3–5 (1.5–1.6×), named companies without an ABN aged 2–3 (1.73×) and older numbered companies without an ABN.
**Low:** named companies under 2 years old, numbered companies with an ABN under 1 year, and named companies without an ABN aged 10+.

**The tiers separate risk well.** The High tier holds **5.4%** of trading-company exposure but **16.4%** of deregistrations (**lift 3.06×**); High and Elevated together hold **16%** of exposure and **34%** of deregistrations. In lending terms: **tightening criteria for about 1 in 6 trading companies targets about 1 in 3 failures.**

On top of the tiers, a **red-flag rule** applies to any company currently in strike-off or external administration: **70,918 trading companies** (39,396 strike-off, 31,522 external administration) should be declined or referred whatever their profile.

<details>
<summary>See the numbers</summary>

**Capture (lift) table**

| Tier | Profiles | Active companies | % of active companies | % of company-years | % of deregistrations | Lift |
|---|---|---|---|---|---|---|
| 🔴 High | 8 | 162,801 | 5.1% | 5.4% | 16.4% | **3.06** |
| 🟠 Elevated | 6 | 345,056 | 10.7% | 10.9% | 17.4% | 1.60 |
| 🟡 Standard | 8 | 1,665,549 | 51.7% | 51.9% | 50.1% | 0.97 |
| 🟢 Low | 6 | 1,049,957 | 32.6% | 31.8% | 16.0% | 0.50 |

**All 28 profiles**

| Tier | Age | Name | ABN | Active companies | Company-years | Deregistrations | Yearly probability | × trading average | 95% interval |
|---|---|---|---|---|---|---|---|---|---|
| High | 2–3 | Numbered | No ABN | 184 | 230 | 107 | 37.14% | 7.60 | 6.29–9.19 |
| High | 2–3 | Numbered | Has ABN | 437 | 508 | 219 | 35.01% | 7.06 | 6.18–8.06 |
| High | 3–4 | Numbered | Has ABN | 309 | 337 | 77 | 20.42% | 3.74 | 2.99–4.68 |
| High | 3–4 | Numbered | No ABN | 169 | 143 | 32 | 20.03% | 3.66 | 2.59–5.17 |
| High | 2–3 | Named | Has ABN | 157,946 | 167,045 | 31,106 | 16.99% | 3.05 | 3.02–3.08 |
| High | 5–10 | Numbered | Has ABN | 1,110 | 1,491 | 271 | 16.62% | 2.98 | 2.64–3.35 |
| High | 4–5 | Numbered | Has ABN | 241 | 342 | 62 | 16.57% | 2.97 | 2.31–3.80 |
| High | 10+ | Numbered | Has ABN | 2,405 | 3,174 | 517 | 15.03% | 2.67 | 2.45–2.91 |
| Elevated | 4–5 | Numbered | No ABN | 97 | 139 | 24 | 15.82% | 2.82 | 1.89–4.21 |
| Elevated | 5–10 | Numbered | No ABN | 543 | 602 | 78 | 12.15% | 2.12 | 1.70–2.65 |
| Elevated | 10+ | Numbered | No ABN | 1,258 | 1,364 | 161 | 11.14% | 1.93 | 1.66–2.26 |
| Elevated | 2–3 | Named | No ABN | 81,464 | 77,078 | 8,136 | 10.02% | 1.73 | 1.69–1.77 |
| Elevated | 3–4 | Named | Has ABN | 138,799 | 139,503 | 13,961 | 9.52% | 1.64 | 1.61–1.67 |
| Elevated | 4–5 | Named | Has ABN | 122,895 | 133,490 | 11,999 | 8.60% | 1.47 | 1.45–1.50 |
| Standard | 5–10 | Named | Has ABN | 449,974 | 453,158 | 34,882 | 7.41% | 1.26 | 1.25–1.27 |
| Standard | 1–2 | Numbered | Has ABN | 653 | 616 | 47 | 7.35% | 1.25 | 0.94–1.66 |
| Standard | 3–4 | Named | No ABN | 65,168 | 65,189 | 4,028 | 5.99% | 1.01 | 0.98–1.04 |
| Standard | 4–5 | Named | No ABN | 64,462 | 71,910 | 4,157 | 5.62% | 0.95 | 0.92–0.98 |
| Standard | 5–10 | Named | No ABN | 248,715 | 244,972 | 13,368 | 5.31% | 0.89 | 0.88–0.91 |
| Standard | 1–2 | Numbered | No ABN | 372 | 297 | 15 | 4.92% | 0.83 | 0.50–1.37 |
| Standard | 10+ | Named | Has ABN | 835,571 | 838,404 | 42,242 | 4.91% | 0.82 | 0.82–0.83 |
| Standard | 0–1 | Numbered | No ABN | 634 | 529 | 16 | 2.98% | 0.50 | 0.30–0.81 |
| Low | 10+ | Named | No ABN | 432,255 | 424,717 | 20,262 | 4.66% | 0.78 | 0.77–0.79 |
| Low | 1–2 | Named | Has ABN | 190,807 | 184,785 | 6,745 | 3.58% | 0.60 | 0.58–0.61 |
| Low | 0–1 | Numbered | Has ABN | 835 | 817 | 25 | 3.01% | 0.50 | 0.34–0.74 |
| Low | 1–2 | Named | No ABN | 106,005 | 94,830 | 1,822 | 1.90% | 0.31 | 0.30–0.33 |
| Low | 0–1 | Named | Has ABN | 210,414 | 206,815 | 2,084 | 1.00% | 0.16 | 0.16–0.17 |
| Low | 0–1 | Named | No ABN | 109,641 | 115,112 | 693 | 0.60% | 0.10 | 0.09–0.11 |

- Named companies with an ABN aged 5–10 (1.26×) sit on the Elevated boundary: their interval touches 1.25, so they stay Standard.
- Small profiles with wide intervals (for example numbered companies under 2) stay Standard even when their point estimate is high or low, because the evidence is not strong enough to move them.
- No profile fell into *Insufficient data*.
- Active companies exclude those currently in strike-off or administration (covered by the red-flag rule).
- The same profile table drives the app's **Company lookup**: given an ACN or name, it returns the company's segment, status, age band, profile, lending tier and any red flag.

*Source: report tables `rpt_profile_risk` and `rpt_company_lookup` (from the Q3 analysis)*
</details>

> **Overall:** risk for young companies is concentrated in a few identifiable profiles. Third-year trading companies and numbered companies carry most of the excess risk, and a simple ASIC status check catches companies already on their way out.

---

## Recommendations

Thresholds are illustrative and the analysis measures deregistration, not default; expected impact is described qualitatively.

**Credit criteria**
1. **(P0) Tighten criteria in the third year.** For trading companies aged 2–3, ask for stronger serviceability evidence, shorter terms or security. *Evidence:* the riskiest year (14.9% yearly for trading companies, 3.05× average for named companies with an ABN). *Metric to watch:* share of approvals in the High tier; deregistration rate of approved third-year borrowers.
2. **(P0) Treat a numbered company name as a risk flag** for trading companies aged 2 or more: extra verification of directors and trading history, lower limits or security. *Evidence:* 2× the 5-year risk; numbered companies in the High tier run at 2.7–7.6× the average yearly rate. *Metric to watch:* numbered-company share of new lending.
3. **(P1) Price or monitor Elevated profiles rather than declining them** (mainly named trading companies aged 3–5). *Evidence:* 1.5–1.7× average; 10.9% of exposure, 17.4% of deregistrations.
4. **(P1) Do not relax criteria for companies under 2 because they look "Low".** Assess risk over the loan term: a 3-year loan to a new company spans the riskiest year (only 81.8% of trading companies are still registered at year 3). *Metric to watch:* cumulative risk over the loan term rather than current-age risk.

**Monitoring**

5. **(P0) Check ASIC status before approval and during the loan**, using the weekly file. *Evidence:* 70,918 trading companies currently in strike-off or external administration. *Metric to watch:* borrowers entering strike-off or administration each week.

**Model governance**

6. **(P1) Calibrate the tiers with the bank's own loan outcomes.** Deregistration is a proxy; the cut-offs should be tuned to actual credit losses.

---

## Data exploration

Before answering the questions, the Gold tables were explored with SQL (dimensions, measures, magnitude, change over time and part-to-whole analysis). The findings below shaped how the results are read.

- **Deregistrations are processed in batches.** **41.0%** are dated on a **Sunday** and 28.4% on a Wednesday, against 0.7% on Saturdays. The seven busiest single days are all Sundays in May–June 2026 (up to **8,342** in one day). A deregistration date is the day ASIC processed it, not the day the business stopped.
- **The May 2026 spike** (38,584 deregistrations, about 2–3× a normal month of 12k–20k) is a run of large Sunday batches; 28% were companies aged 2–3. In other months, age 2–3 is still **12–20%** of deregistrations while holding about **8%** of companies, so the peak is not only the batch.
- **The 30 June effect:** the last week of June (24–30 June) holds **3.5–5.2%** of each financial year's registrations, against about 1.9% for an average week.
- **Who takes more than their share** (share of deregistrations ÷ share of company-years): age 2–3 **2.63×**, age 3–4 1.44×, age 0–1 0.15×; trading companies 1.07×, super trustees 0.56×. Trading companies also hold **94.5%** of all currently distressed companies.
- **Crude comparisons mislead:** on raw counts, companies with an ABN looked riskier than those without and renamed companies looked safer. These patterns are largely driven by age and segment mix, which is why the questions use age-adjusted measures.

<details>
<summary>See the numbers</summary>

**Key metrics**

| Measure | Value |
|---|---|
| Total companies | 4,024,917 |
| Active companies | 3,811,222 |
| Distressed companies (strike-off + administration) | 75,054 |
| Distress share of active | 1.97% |
| Deregistered in the last 12 months | 213,694 |
| Company-years at risk | 3,726,156 |
| Yearly deregistration probability | 5.57% |
| Companies with an ABN | 59.45% |
| Companies ever renamed | 8.25% |
| Numbered (ACN-named) companies | 0.31% (12,625) |
| Median age of active companies | 7 years (mean 10.6, oldest 209) |

**Companies by segment and age band**

| Group | Companies | % of companies | Active | Distressed | Deregistered (12 months) |
|---|---|---|---|---|---|
| Trading company | 3,491,420 | 86.75% | 3,294,283 | 70,918 | 197,137 |
| Super trustee | 489,124 | 12.15% | 474,470 | 3,146 | 14,654 |
| Not-for-profit | 23,173 | 0.58% | 22,181 | 321 | 991 |
| Other public | 11,753 | 0.29% | 11,218 | 463 | 535 |
| Foreign company | 4,706 | 0.12% | 4,552 | 129 | 154 |
| Home unit | 2,652 | 0.07% | 2,439 | 52 | 213 |
| Registrable body | 2,078 | 0.05% | 2,068 | 25 | 10 |
| CCIV | 11 | 0.00% | 11 | 0 | 0 |
| Age 0–1 years | 377,842 | 9.39% | 374,678 | 967 | 3,164 |
| Age 1–2 years | 358,097 | 8.90% | 348,973 | 2,486 | 9,124 |
| Age 2–3 years | 326,510 | 8.11% | 284,697 | 9,243 | 41,813 |
| Age 3–4 years | 256,506 | 6.37% | 237,405 | 5,397 | 19,101 |
| Age 4–5 years | 234,058 | 5.82% | 216,882 | 5,262 | 17,176 |
| Age 5–10 years | 881,174 | 21.89% | 828,625 | 21,470 | 52,549 |
| Age 10+ years | 1,590,726 | 39.52% | 1,519,959 | 30,229 | 70,766 |

**Who takes more than their share (part-to-whole)**

| Group | % of company-years | % of deregistrations | Over-representation |
|---|---|---|---|
| Age 0–1 | 10.10% | 1.48% | 0.15 |
| Age 1–2 | 8.66% | 4.27% | 0.49 |
| **Age 2–3** | 7.44% | 19.57% | **2.63** |
| Age 3–4 | 6.19% | 8.94% | 1.44 |
| Age 4–5 | 6.23% | 8.04% | 1.29 |
| Age 5–10 | 21.68% | 24.59% | 1.13 |
| Age 10+ | 39.69% | 33.12% | 0.83 |
| Trading company | 86.62% | 92.25% | 1.07 |
| Super trustee | 12.26% | 6.86% | 0.56 |

**Deregistrations per month**

| Month | Deregistrations | Month | Deregistrations |
|---|---|---|---|
| Nov 2025 (from 10th) | 8,368 | May 2026 | **38,584** |
| Dec 2025 | 12,897 | Jun 2026 | 20,883 |
| Jan 2026 | 15,782 | Jul 2026 | 16,242 |
| Feb 2026 | 11,896 | Aug 2026 | 17,615 |
| Mar 2026 | 11,724 | Sep 2026 | 20,221 |
| Apr 2026 | 15,210 | Oct 2026 | 17,901 |
| | | Nov 2026 (to 9th) | 6,371 |

Total: 213,694.

**Deregistrations by day of the week:** Sunday 41.0% · Wednesday 28.4% · Monday 12.8% · Thursday 7.6% · Friday 7.4% · Tuesday 2.1% · Saturday 0.7%.

*Source: [`exploratory_data_analysis`](notebooks/gold_analysis/exploratory_data_analysis.ipynb) notebook, recalculated on the 9 Nov 2026 snapshot*
</details>

---

## Appendix: Technical Details

### A. Metric definitions

| Metric | Definition | Value (9 Nov 2026 snapshot) |
|---|---|---|
| **Company-years at risk (exposure)** | Time each company was registered inside the observation window, from the later of the window start and its registration date until deregistration or the window end, split at each anniversary into age bands | 3,726,156 |
| **Deregistration rate** | Deregistrations ÷ company-years at risk | 5.73 per 100 company-years |
| **Yearly deregistration probability** | `q = 1 − e^(−rate)`: chance of being deregistered within one year | 5.57% (all ages) |
| **Survival to year N** | `S(N) = (1 − q₁) × … × (1 − q_N)`, equivalently `e^(−Σ rate)`; period method | S(1) 99.2% · S(2) 96.4% · S(3) 82.9% · S(5) 70.9% |
| **Relative risk index** | `(1 − S(5))` of a group ÷ `(1 − S(5))` of the benchmark; age-adjusted. Above 1.25 = higher risk, below 0.80 = lower risk | Trading 1.06 · Super trustee 0.46 · Numbered trading 1.99 |
| **Distress share** | (Strike-off + external administration) ÷ active companies | 1.97% |
| **Over-representation / lift** | Share of deregistrations ÷ share of company-years | Age 2–3: 2.63 · High tier: 3.06 |
| **95% interval on a rate** | `rate × e^(±1.96/√d)`, d = deregistrations (Poisson approximation) | Used to gate risk tiers |
| **Reliability rule** | At least 100 company-years and 10 deregistrations in each age band used | – |

**Definitions**
- **Active:** status Registered, Strike-off action in progress, External administration or Not active.
- **Distressed:** strike-off action in progress (SOFF) or external administration (EXAD).
- **Analysis population:** all companies except cancelled (CNCL) and dissolved (DISS).
- **Age:** full years since registration, counted on anniversaries. Bands: 0–1, 1–2, 2–3, 3–4, 4–5, 5–10, 10+ years.
- **Numbered company:** the company's own ACN appears in its name (e.g. `123 456 789 PTY LTD`).
- **Borrower segment:**

  | Segment | Rule |
  |---|---|
  | Trading company | Proprietary companies (excluding the segments below) |
  | Super trustee | Proprietary superannuation trustee (PSTC) |
  | Not-for-profit | ULSN, PNPC, NLTD |
  | Home unit | HUNT |
  | Other public | Remaining public companies |
  | Foreign company | FNOS |
  | Registrable body | RACN |
  | CCIV | Corporate collective investment vehicles |

### B. Assumptions and caveats

**Assumptions**
- **Deregistration as a proxy:** a deregistered company is treated as a business that stopped operating. It is not loan default.
- **Period method:** survival assumes the last 12 months' deregistration rates at each age continue.
- **Observation window:** computed from each snapshot as the earliest deregistration date in the file to the snapshot date (10 Nov 2025 – 9 Nov 2026, 364 days), because ASIC keeps one year of deregistrations.
- **Status is authoritative:** a deregistration date is only used when the status is Deregistered (a handful of companies with a date but another status are flagged as likely reinstatements).
- **Tier thresholds** (0.8×, 1.25×, 2×) and segment rules are analyst choices, not bank policy.

**Caveats**
- **Deregistration lags failure,** so early-age risk is understated and appears in later years.
- **Deregistration dates are processing dates** (Sunday batches, May–June 2026 spike). The main finding was tested without the batch.
- **No current location:** the register's "previous state" is pre-1991 registration history, so there is no state-level view.
- **ABN held** means an ABN is recorded by ASIC, not that it is currently active.
- **Name history** is recorded at the snapshot and biased towards survivors.
- **Registration date** may be the date a company joined the ASIC register for some post-1991 transfers (333 companies, including 58 Norfolk Island companies all dated 2 Aug 2021).
- **Interpretations, not proven causes:** explanations such as holding vehicles without an ABN or ASIC strike-off batches are readings of the patterns, not tested causes.
- **Public app snapshot:** the public app shows the 9 Nov 2026 snapshot; the Databricks App and the tables refresh weekly, so their numbers move slightly from week to week.

### C. Architecture

The project is a **medallion lakehouse on Databricks**, using Delta Lake tables governed in Unity Catalog, orchestrated as a Databricks Job, with a Streamlit app on top.

```mermaid
flowchart LR
    A["data.gov.au<br/>ASIC Company Dataset<br/>(weekly, tab-delimited)"] -->|CKAN API| B["Unity Catalog volume<br/>source_systems<br/>raw file + _metadata.json"]
    B --> C["Bronze<br/>asic_companies_raw<br/>all snapshots, strings"]
    C --> D["Silver<br/>companies<br/>1 row per company"]
    D --> E["Gold<br/>star schema<br/>5 dimensions + 2 facts"]
    E --> F["SQL analysis<br/>EDA, Q1–Q3"]
    E --> G["Report tables<br/>6 rpt_* tables"]
    G --> H["Databricks App<br/>live tables"]
    G -->|Parquet export| I["Streamlit Community Cloud<br/>public app"]
```

| Layer | Object | Load pattern | What happens |
|---|---|---|---|
| **Landing** | Volume `sme_risk_bronze.source_systems` | New folder per snapshot | Raw ASIC file stored unchanged in `snapshot_date=YYYY-MM-DD/`, with `_metadata.json` (source URL, ASIC last-modified date, size, SHA-256) |
| **Bronze** | `sme_risk_bronze.asic_companies_raw` | Append per snapshot (Delta `replaceWhere`, idempotent) | Every weekly snapshot kept; all 15 source columns as text plus load metadata. **History lives here** |
| **Silver** | `sme_risk_silver.companies` | Overwrite from the latest snapshot | Cleaning, typing, deduplication to one row per company, name history, business flags, code labels, 22 validation checks |
| **Gold** | 5 dimensions + 2 facts in `sme_risk_gold` | Overwrite from Silver | Star schema for analysis, 22 integrity checks, table and column descriptions |
| **Reports** | 6 `rpt_*` tables in `sme_risk_gold` | Overwrite from the star schema | Small, ready-to-chart tables for the app and BI tools, 10 hard stops |
| **App** | Streamlit (`app/`) | Reads the report tables | Databricks App on the live tables; public copy on Parquet exports |

**Star schema**

```mermaid
erDiagram
    dim_company ||--o{ fct_company_snapshot : company_key
    dim_company_classification ||--o{ fct_company_snapshot : classification_key
    dim_status ||--o{ fct_company_snapshot : status_key
    dim_age_band ||--o{ fct_company_snapshot : age_band_key
    dim_date ||--o{ fct_company_snapshot : "registration / deregistration / snapshot date_key"
    dim_company ||--o{ fct_exposure : company_key
    dim_company_classification ||--o{ fct_exposure : classification_key
    dim_status ||--o{ fct_exposure : status_key
    dim_age_band ||--o{ fct_exposure : age_band_key
    dim_date ||--o{ fct_exposure : "window start / snapshot date_key"
```

| Table | Grain | Rows (9 Nov 2026) | Key | Contents |
|---|---|---|---|---|
| `dim_company` | Company | 4,024,917 | `company_key` = ACN as a number | Name, registration date, ABN, numbered flag, former names, date of current name, renamed in last 12 months, previous state |
| `dim_company_classification` | Type + class + sub-class | 35 | `classification_key` (e.g. `APTY-LMSH-PROP`) | ASIC labels and the **borrower segment** |
| `dim_status` | Status code | 6 | `status_key` = status code | Labels, active / distressed / deregistered flags, status group |
| `dim_age_band` | Age band | 8 | `age_band_key` 0–7 | Band label, min/max years, age group |
| `dim_date` | Day (1817–2026) | 76,702 | `date_key` = YYYYMMDD (0 = no date) | Calendar and **Australian financial year** attributes |
| `fct_company_snapshot` | Company × snapshot | 4,024,917 | – | Status, age band, dates; 0/1 measures (active, distressed, deregistered) |
| `fct_exposure` | Company × age band in the window | 5,521,284 | – | Company-years at risk and deregistrations: the input for every survival metric |

Keys are readable and stable from week to week (no generated row numbers), so the same company always has the same key.

**Report tables**

The analysis queries are saved as small summary tables in [`notebooks/gold_reports/report_table`](notebooks/gold_reports/report_table.ipynb), so the app or a BI tool (Power BI, Tableau) reads finished numbers instead of recalculating them from 5.5 million exposure rows. The notebook runs as the last task of the weekly job and ends with **10 hard stops** (row counts, nulls, totals reconciled with the fact tables, survival never increasing, benchmarks equal to 1, no duplicate profiles or ACNs, shares adding to 100%, a lending tier for every company).

| Table | Grain | Rows (9 Nov 2026) | Contents | Used by |
|---|---|---|---|---|
| `rpt_key_metrics` | Metric | 11 | Headline numbers with unit, snapshot date and window start | Overview, sidebar |
| `rpt_monthly_deregistrations` | Month | 13 | Deregistrations per month by segment and age group, change on previous month (`LAG`), running total, partial-month flag | Overview |
| `rpt_survival_curve` | Group × scenario × year 0–5 | 24 | Company-years, deregistrations, yearly probability and survival, with and without the May–June 2026 batch | When is risk highest? |
| `rpt_segment_risk` | Analysis × group | 16 | 5-year deregistration chance, risk index, flag and reliability for segments and warning signs | Who is riskiest? |
| `rpt_profile_risk` | Trading-company profile | 28 | Yearly probability, multiple with 95% interval, tier, shares and tier lift | Risk tiers |
| `rpt_company_lookup` | Company | 4,024,917 | One row per ACN: details, **lending tier** (deregistered, red flag, out of scope or profile tier) and the profile's risk; Z-ordered by ACN | Company lookup |

### D. Pipeline and orchestration

The three layers and the report tables run as one **Databricks Job, `sme_risk_weekly_pipeline`**, on serverless compute, every **Wednesday at 07:00 (Australia/Sydney)** (the day after ASIC publishes its weekly file), with an email alert if any task fails. The job definition is version-controlled as YAML in [`jobs/sme_risk_weekly_pipeline.yml`](jobs/sme_risk_weekly_pipeline.yml).

| Task | Notebook | Depends on | Typical run time |
|---|---|---|---|
| `bronze_layer` | [`notebooks/bronze_ingest`](notebooks/bronze_ingest.ipynb) | – | ~1m 40s (1 retry after 15 min) |
| `silver_layer` | [`notebooks/silver_transform`](notebooks/silver_transform.ipynb) | `bronze_layer` | ~1m 15s |
| `gold_layer` | [`notebooks/gold_build`](notebooks/gold_build.ipynb) | `silver_layer` | ~2m 40s |
| `reports_layer` | [`notebooks/gold_reports/report_table`](notebooks/gold_reports/report_table.ipynb) | `gold_layer` | ~1m 30s |

End to end: **about 7 minutes**. Any failed validation stops the job before later layers run. Rerunning is safe: Bronze skips snapshots it already holds, and the other layers rebuild the same tables.

**Bronze (`bronze_ingest`)**
- Finds the latest file through the data.gov.au CKAN API and downloads it in streamed chunks (`.part` file renamed on completion).
- Loads it with tab delimiter, quoting off and every column as text.
- Stops unless the header matches the 15 documented columns, the row count equals the raw line count and every line has exactly 14 tabs.
- Applies table, column and volume descriptions from the ASIC help file.

**Silver (`silver_transform`)**: PySpark plus SQL
- Filters Bronze to the latest snapshot and renames columns to business names (`type` → `company_type`, `status` → `status_code`, …).
- Cleans text: decodes CSV escaping in names, strips control characters, trims and collapses spaces, turns blanks into nulls (regex functions).
- Parses DD/MM/YYYY dates safely (`try_to_timestamp`, unparseable flags first), turns the ABN placeholder `0` into null and Y/blank flags into booleans.
- Deduplicates to one row per company with SQL CTEs, keeping name history from former-name rows (`COUNT_IF`, `ARRAY_SORT(COLLECT_LIST(...))`, `MAX`).
- Adds business flags and ASIC code labels (`create_map` + `try_element_at`).
- Validates with 22 hard stops, writes the table and applies column descriptions.

**Gold (`gold_build`)**: Spark SQL into DataFrames
- Builds each dimension and fact with one SQL query.
- Generates the date dimension with `explode(sequence(...))`.
- Splits each company's time at risk at its anniversaries with `add_months`, `months_between` and `LATERAL VIEW explode` to build `fct_exposure`.
- Runs 22 integrity checks (duplicate keys, orphan keys with `LEFT ANTI JOIN`, fact-to-Silver reconciliation, exposure totals) and applies descriptions to all 78 Gold columns.

**Reports (`gold_reports/report_table`)**: Spark SQL
- Six report tables built with CTEs, window functions (`LAG`, running `SUM() OVER`, `PARTITION BY` benchmarks), `EXP(-SUM(...) OVER (...))` for survival and Poisson confidence intervals.
- 10 consistency hard stops (no fixed values, so they pass on any snapshot).

**Analysis**: Databricks SQL notebooks on the Gold tables in [`notebooks/gold_analysis/`](notebooks/gold_analysis/) (EDA and Q1–Q3): CTEs, window functions, conditional aggregation, `UNION ALL` and temporary views.

**App and deployment** ([`app/`](app/))
- **Streamlit** multipage app (`st.navigation`) with **Plotly** charts; one data layer (`app/data.py`) with a switch, `DATA_SOURCE = databricks | files`.
- **Databricks App:** `app.yaml` binds a SQL warehouse resource; the app's service principal reads the `rpt_*` tables with `databricks-sql-connector` (parameterised queries, results cached for an hour).
- **Public copy:** [`notebooks/gold_reports/export_app_data`](notebooks/gold_reports/export_app_data.ipynb) exports the report tables to Parquet (the 4M-row lookup as five zstd parts of about 15 MB each, under GitHub's 100 MB limit). On Streamlit Community Cloud, **DuckDB** queries those files directly, so a single-company lookup takes well under a second without loading 4 million rows into memory.

### E. Data source

| Source | Publisher | Format | Rows (9 Nov 2026) | Columns | Update |
|---|---|---|---|---|---|
| ASIC Company Dataset (`asic-companies`) | Australian Securities & Investments Commission, via data.gov.au | Tab-delimited text (named `.csv`) | 4,458,851 | 15 | Weekly |

The file holds every currently registered company, companies deregistered in the past year, and one extra row for each former company name, so one row per **name**, not per company. It contains 4,024,956 distinct ACNs (4,024,917 after removing cancelled companies with no current-name row).

Columns: company name, ACN, type, class, sub-class, status, date of registration, date of deregistration, previous state of registration, state registration number, modified since last report, current name indicator, ABN, current name, current name start date.

### F. Data quality and cleaning

Profiling was done column by column in [`notebooks/silver_profile`](notebooks/silver_profile.ipynb) (first profiled on the 12 Oct 2026 snapshot; sizes below are from that profiling).

| Issue found | Size | Fix applied (Silver) |
|---|---|---|
| One row per company name, not per company | ~434,000 former-name rows | Kept the current-name row per ACN; former names kept as `former_names`, `former_name_count`, `current_name_start_date` |
| ACNs with no current-name row | 39 (all cancelled) | Removed; hard stop if any non-cancelled company ever appears |
| Names wrapped in CSV quotes with doubled inner quotes | 429 | Decoded (verified against the ASIC online register, e.g. `GO "N" OFF PTY LTD`) |
| Leading/trailing spaces in names | 45,798 | Trimmed |
| Repeated spaces in names | 46,776 | Collapsed to one space |
| ABN `0` used for "no ABN" | 1,631,208 (40.6%) | Set to null; `has_abn` flag added |
| Hidden trailing space in state codes (`SA `, `WA `, `NT `) | 47 | Trimmed |
| Character `º` (U+00BA) replacing `\|` in the export | 4 names (1 current) | Flagged (`company_name_has_export_artifact`), not changed |
| Sub-class code not in the ASIC help file (`WHSL`) | 13 rows | Added to the code dictionary with an inferred label |
| Deregistration date on a non-deregistered company | 9 | Status kept as authoritative; flagged (`dereg_date_status_conflict`) |
| Missing registration date | 4 | Kept; age band "Unknown", excluded from age-based metrics |
| Dates as DD/MM/YYYY text | All rows | Parsed to DATE; 0 unparseable, 0 in the future, 0 deregistrations before registration |

**Checked and kept as they are**
- **ACNs:** 100% valid 9-digit numbers including the ASIC check digit (0 failures across 4.45M rows); 15% have leading zeros, so they are stored as text.
- **ABNs:** every real ABN passes the format and mod-89 check digit, and none is shared between companies. 266 are not derived from the company's ACN (charities, foreign companies); they are genuine.
- **Asterisks in names** (e.g. `CREATE*IT PTY LTD`) are genuine and kept.
- **Registration dates** cluster around 30 June each year: the end of the Australian financial year, not placeholder dates.

**Validation summary:** 3 load checks in Bronze, **22 hard stops in Silver** (format and check digits, unknown codes, impossible dates, duplicates, row-count reconciliation), **22 in Gold** (key uniqueness, orphan keys, reconciliation with Silver, exposure totals) and **10 on the report tables**. Every one passes on the 9 Nov 2026 snapshot.

**Known limitations**
- ASIC keeps deregistered companies for one year only, so long-term outcomes cannot be followed company by company.
- The register has no current address or industry, so risk cannot be split by state or industry.
- Code labels for `CCIV` and `WHSL` are not in the ASIC help file and are inferred.
- 333 companies have a pre-1991 state of registration but a registration date after 1991; their age may be understated.

### G. Repository structure

```
├── README.md
├── .streamlit/config.toml            # app theme for Streamlit Community Cloud
├── .databricks/commit_outputs        # which notebooks keep their outputs in Git
├── images/                           # app screenshots used in this README
├── jobs/
│   └── sme_risk_weekly_pipeline.yml  # Databricks Job definition (4 tasks, weekly schedule)
├── notebooks/
│   ├── bronze_ingest.ipynb           # pipeline: download + Bronze load
│   ├── silver_transform.ipynb        # pipeline: clean, deduplicate, validate, write Silver
│   ├── gold_build.ipynb              # pipeline: star schema + integrity checks + descriptions
│   ├── silver_profile.ipynb          # column profiling behind the cleaning decisions
│   ├── gold_analysis/
│   │   ├── exploratory_data_analysis.ipynb  # key metrics, magnitude, change over time, part-to-whole
│   │   ├── Q1.ipynb                  # when is a new company most at risk?
│   │   ├── Q2.ipynb                  # which segments and warning signs carry the most risk?
│   │   └── Q3.ipynb                  # risk tiers, red flags and ACN lookup
│   └── gold_reports/
│       ├── report_table.ipynb        # pipeline: 6 report tables (rpt_*) + 10 hard stops
│       └── export_app_data.ipynb     # manual: export report tables to Parquet for the public app
└── app/
    ├── app.py                        # entry point: page list + sidebar
    ├── data.py                       # data layer: Databricks SQL warehouse or Parquet + DuckDB
    ├── ui.py                         # shared colours, KPI tiles, cards, chart style
    ├── app.yaml                      # Databricks App config (SQL warehouse resource)
    ├── requirements.txt
    ├── .streamlit/config.toml        # app theme for the Databricks App
    ├── views/                        # overview, when_risk, who_risk, risk_tiers, acn_lookup, about
    └── data/                         # Parquet exports for the public app (9 Nov 2026 snapshot)
```

### H. Tech stack

| Area | Tools |
|---|---|
| Languages | Python, PySpark, Spark SQL |
| Platform | Databricks (serverless compute, Jobs, Git folders, Databricks Apps) |
| Storage and governance | Delta Lake, Unity Catalog (catalog, schemas, volumes, table and column descriptions) |
| Ingestion | data.gov.au CKAN API (`requests`), SHA-256 file checksums |
| Modelling | Medallion architecture, star schema (5 dimensions, 2 facts), report tables |
| Analysis | Exposure-based period life table, age-adjusted relative risk index, Poisson confidence intervals, lift / capture analysis, window functions |
| App | Streamlit, Plotly, DuckDB, `databricks-sql-connector`; deployed on Databricks Apps and Streamlit Community Cloud |
| Version control | Git, GitHub |

### I. How to run

**1. Pipeline (Databricks)**
1. In a Databricks workspace (Free Edition works), add this repository as a **Git folder**.
2. Create the Unity Catalog objects: catalog `workspace` with schemas `sme_risk_bronze`, `sme_risk_silver`, `sme_risk_gold`, and the volume `sme_risk_bronze.source_systems`.
3. Run the notebooks in order (`bronze_ingest` → `silver_transform` → `gold_build` → `gold_reports/report_table`), or create the job from [`jobs/sme_risk_weekly_pipeline.yml`](jobs/sme_risk_weekly_pipeline.yml) (update the notebook paths to your workspace) and click **Run now**.

**2. Databricks App (live tables)**
1. **Compute → Apps → Create app → Custom**, and add a **SQL warehouse** resource with permission *Can use* and resource key `sql-warehouse`.
2. Deploy from the `app/` folder of the Git folder.
3. Give the app's service principal read access:
   ```sql
   GRANT USE CATALOG ON CATALOG workspace TO `<service-principal-id>`;
   GRANT USE SCHEMA, SELECT ON SCHEMA workspace.sme_risk_gold TO `<service-principal-id>`;
   ```

**3. Public copy (Parquet files)**
1. Run [`notebooks/gold_reports/export_app_data`](notebooks/gold_reports/export_app_data.ipynb) and download the files from the `app_export` volume into `app/data/` (keep the lookup parts in `app/data/rpt_company_lookup/`).
2. Run locally:
   ```bash
   pip install -r app/requirements.txt
   streamlit run app/app.py
   ```
3. Or deploy on **Streamlit Community Cloud** with main file `app/app.py` and Python 3.11. Without a `DATA_SOURCE` setting the app reads the Parquet files.

## Acknowledgements

Data: **ASIC Company Dataset**, published by the Australian Securities & Investments Commission on [data.gov.au](https://data.gov.au/data/dataset/asic-companies).

## About Me

**Manaswini Doma**

[https://www.linkedin.com/in/domamanaswini/](https://www.linkedin.com/in/domamanaswini/) ·
[domamanaswini@gmail.com](mailto:domamanaswini@gmail.com)
