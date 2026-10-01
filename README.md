# U.S. Federal Contracting Intelligence — FY2025

A Power BI analytics product built on the complete record of U.S. federal prime-contract
spending for fiscal year 2025: **6,639,176 contract actions** totalling
**$793,189,920,124.27**, modelled from a 13.6 GB official source archive into a
**187 MB** semantic model that refreshes in about two minutes on a laptop.

Every figure in this repository is reconciled against the source data. Nothing is
estimated, modelled or imputed.

---

## 1. Business problem

U.S. federal contract spending is published in full, but it is published as a 13.6 GB
flat file of 297 columns at transaction grain. In that form it answers almost nothing.
The questions that actually matter to a market analyst, a bid team or an oversight
function are structural:

- How much was obligated, and how is it distributed across the fiscal year?
- Which agencies command the money, and how differently do they buy?
- How concentrated is the contractor market?
- How much of it is genuinely competed?
- What is bought, and where is the work performed?
- Can any headline number be traced back to an individual award?

This project turns the raw archive into an eight-page executive intelligence product
that answers those questions, with the data engineering and validation to make the
answers defensible.

---

## 2. Source data

| | |
|---|---|
| Publisher | USAspending.gov — Award Data Archive |
| Dataset | *All Contracts (Full)*, fiscal year 2025 |
| Archive date | 2026-09-06 |
| Retrieved | 2026-09-29 |
| Compressed | 1.79 GB (ZIP) |
| Uncompressed | 13.6 GB across 7 CSV parts |
| Columns | 297 |
| Rows | 6,639,176 |
| Period | 2024-10-01 → 2025-09-30 |
| Reference data | USAspending `toptier_agencies` and `data_dictionary` API endpoints |

SHA-256 digests and retrieval metadata for every file are recorded in
[`provenance/source-manifest.md`](provenance/source-manifest.md).

The archive splits at exactly 1,000,000 rows per CSV part — six full parts plus
639,176 rows.

**Raw data is not committed to this repository.** It is public and reproducible; see
§10.

---

## 3. Grain

> **One row = one prime-contract transaction (a contract action).**

This was proven, not assumed:

- `contract_transaction_unique_key` — **6,639,176 distinct over 6,639,176 rows**, zero duplicates
- `contract_award_unique_key` — 5,832,578 distinct, so an award averages 1.14 actions
- `action_type` is blank on 80.8% of rows, which is the FPDS convention for a *base* action

**The consequence that shaped the whole model:** only `federal_action_obligation` is
additive. `total_dollars_obligated`, `current_total_value_of_award` and
`potential_total_value_of_award` are award-level snapshots repeated on every transaction
of that award — **132,427 awards carry differing snapshot values across their own
transactions**. Summing them would double-count. They are excluded from the fact table
and surfaced only at award grain.

---

## 4. Data quality

Profiled across the full population in DuckDB. No sampling.

| Finding | Measured | Treatment |
|---|---|---|
| Duplicate transactions | 0 | — |
| Negative obligations | 268,758 rows, −$53,358,044,843.32 | **Kept.** De-obligations and terminations are real accounting events |
| Zero-dollar actions | 694,741 rows | **Kept**, counted separately from dollar flow |
| Rows outside FY2025 | 0 | Period is clean |
| `action_type` blank | 80.8% | **Structural** — FPDS leaves it blank for base awards. Relabelled "Base award" |
| `type_of_set_aside` blank | 77.4% | **Structural** — no set-aside applied |
| Place-of-performance country blank | 4.70% (311,910 rows) | **Structural** — equals the IDV row count *exactly*; IDVs have no performance location |
| `recipient_uei` → multiple names | **0 cases** | UEI is a reliable key; the recipient dimension is keyed on it, not on name |
| Awards spanning sub-agencies | 3,768 (0.065%) | Documented; agency analysis runs at transaction grain where it is exact |
| Parent-company mapping | `ROCKWELL COLLINS AUSTRALIA PTY LIMITED` appears as parent of RTX entities | **Genuine FPDS registration artefact.** Recipient and parent are presented as two explicitly labelled views, never silently merged |

No record is deleted, imputed or corrected. Every exclusion is a documented
column-level or visual-level decision.

---

## 5. Data engineering

```
ZIP (1.79 GB)
  └─ stream, never modified
      └─ 7 CSV parts (13.6 GB, 297 cols)
          └─ column pruning at read time → 63 cols
              └─ Parquet staging (ZSTD)
                  └─ DuckDB star build + integrity assertions
                      └─ partitioned Parquet (~160 MB)
                          └─ Power BI import, zero transformation
```

**Why DuckDB.** The build machine has 7.8 GB RAM and 4 cores. DuckDB streams, spills to
disk and runs the entire star build under a 3 GB memory cap in seconds. Power Query
cannot do this work at this scale on this hardware.

**Column reduction.** 297 → 63 at staging → 14 in the fact table. Dropped: contact
details, 81 of 90 socio-economic booleans, officer-compensation blocks, treasury and
object-class strings, duplicated code/description pairs, and `transaction_description`
(4,682,984 distinct values).

**Integrity assertions run on every build** — the build fails loudly otherwise:

- fact rows == staged rows
- obligation total preserved to < $0.50
- no null foreign keys
- every `DateKey` resolves in `DimDate`

---

## 6. Semantic model

A conventional star. 13 tables, 12 relationships, 58 measures.

```
                      DimDate (365)
                           │
 DimAgency (315) ──────────┤────────── DimAgency  (funding, inactive role-playing)
                           │
 DimRecipient (104,476) ───┼─── FactContractTransactions (6,639,176) ─── DimAward (5,832,578)
                           │
      DimNaics (1,141) ────┤──── DimPsc (2,429)
      DimCompetition (222) ┤──── DimContractType (155)
      DimActionType (22) ──┤──── DimPlaceOfPerformance (3,912)
                           └──── DimActionSize (8)
```

**Fact table** — integer surrogate keys plus one decimal measure and one nullable
integer. No text columns. No award-level snapshot amounts.

**Role-playing** — funding agency is a second, inactive relationship to `DimAgency`,
activated by `USERELATIONSHIP` in dedicated measures rather than duplicating the
dimension.

**Junk dimensions** — `DimCompetition` (222 rows) and `DimContractType` (155 rows)
collapse low-cardinality attribute clusters that would otherwise be eight wide columns
on a 6.6 M-row fact.

Authored through the Power BI modelling API and serialised to TMDL, so the model
definition is text, diffable and reviewable.

---

## 7. Analytics (DAX)

58 measures organised into display folders: Core, Flow, Competition, Market,
Perspective, Time, Geography, Provenance and ranked presentation helpers.

Representative patterns:

```dax
-- The only additive money column in the source
Obligations = SUM ( FactContractTransactions[Obligation] )

-- Market concentration, Herfindahl–Hirschman, scaled 0–10,000
Market Concentration (HHI) =
VAR Total = CALCULATE ( [Obligations], ALLSELECTED ( DimRecipient ) )
RETURN
    SUMX (
        VALUES ( DimRecipient[Parent Company] ),
        VAR Share = DIVIDE ( [Obligations], Total )
        RETURN Share * Share * 10000
    )

-- Award permalink built at query time. Storing this per award would have cost
-- 445 MB of dictionary text for no analytical gain.
USAspending Link =
VAR AwardUrlKey = SELECTEDVALUE ( DimAward[Award Unique Key] )
RETURN
    IF ( NOT ISBLANK ( AwardUrlKey ),
         "https://www.usaspending.gov/award/" & AwardUrlKey & "/" )
```

**Ranked presentation helpers.** Charts that show a "top N" use a measure that blanks
everything below rank N, which removes those categories from the visual without a
hard-coded filter. Each one ranks over *the exact column its chart groups by* — ranking
over a different column silently returns rank 1 for every row.

---

## 8. Performance

The first working model never completed a refresh. Both causes were found by
measurement, not assumption.

**Cause 1 — a derivable high-cardinality column.** `DimAward` stored a USAspending URL
per award:

| Column | Distinct | Avg length | Raw dictionary text |
|---|---:|---:|---:|
| `USAspending Link` | 5,832,578 | 80 | **445.0 MB** |
| `Award Unique Key` | 5,832,578 | 45 | 250.3 MB |
| `Award PIID` | 5,819,433 | 13.1 | 72.6 MB |

That single column was larger than the rest of the model combined, and it was pure
derivation. Removed, rebuilt as a DAX measure.

**Cause 2 — auto-generated attribute hierarchies.** Power BI builds a sort/slice
hierarchy for every column. On hidden surrogate keys these cost 44.5 MB *each* and serve
no purpose. Disabled via `isAvailableInMdx: false`.

**Ingestion benchmark** — same engine, back-to-back, 6,639,176 rows:

| Arm | Configuration | Time |
|---|---|---:|
| A | Parquet, 1 partition | 44.7 s |
| B | **Parquet, 8 partitions** | **37.4 s** |
| C | CSV, 8 partitions | 117.6 s |

Parquet beats CSV by 3×. Partitioning adds a further 16%. The initial hypothesis that
Power Query's Parquet reader was the bottleneck was **wrong**, and the benchmark is what
proved it.

**Result**

| Metric | Before | After |
|---|---|---|
| Full refresh | never completed (> 21 min) | **~2 min** |
| Model size | 395.3 MB* | **187.2 MB** |
| Peak engine RAM | ~2.5 GB | ~1.2 GB |
| CPU during refresh | ~1 core of 4 | ~1.8 cores |

\* measured *after* the URL column was already removed; the original never finished
loading, so no exact figure exists for it.

---

## 9. Report

Eight pages plus two tooltip pages, 374 visual containers, generated from code against
the PBIR schema so the design system is applied consistently rather than by hand.

| # | Page | Question it answers |
|---|---|---|
| 01 | Executive brief | Scale, time-shape and concentration in one screen |
| 02 | Market structure | How dollars are actually transacted — new awards vs modifications |
| 03 | Agencies | Who commands the money, and how differently they buy |
| 04 | Contractors | Market concentration and who sits at the top |
| 05 | Categories | What is bought, and how competitively |
| 06 | Geography | Where the contracted work is performed |
| 07 | Award explorer | Row-level evidence; drill-through target |
| 08 | Method & sources | Provenance, grain, quality decisions, limitations |

**Design direction** — a dark editorial system: layered neutrals, hairline separators
instead of shadowed cards, a single brass accent reserved for the primary value in any
view, serif titles against a functional sans, and a 4-column grid on a 1440 × 900 canvas.
The full system is documented in
[`docs/01-design-and-architecture-brief.md`](docs/01-design-and-architecture-brief.md).

**Interaction** — a persistent navigation rail on every page, cross-filtering within
pages, and drill-through from any recipient or department to the Award explorer.

> In Power BI **Desktop**, navigation buttons require **Ctrl+click** (a plain click
> selects the button for editing). A plain click works in the Power BI Service and in
> the mobile app.

---

## 10. Validation

Every headline figure was computed independently in DuckDB and then checked against the
live model with DAX. These are exact matches, not approximations.

| Figure | Value |
|---|---|
| Obligations | $793,189,920,124.27 |
| Contract actions | 6,639,176 |
| Awards | 5,832,578 |
| Recipients (UEI) | 104,476 |
| Awarding organisations | 168 |
| New awards vs modifications | $327.6 bn / $465.5 bn |
| De-obligations | −$53.36 bn |
| Cross-serviced obligations | $75.7 bn |
| Department of Defense share | 61.996% |
| September share of the year | 18.966% |
| Actions ≥ $100 M | 823, carrying 37.054% of all dollars |
| Top 10 parent companies | 28.735% |
| Market concentration (HHI) | 139 |
| Small business share | 21.348% |
| Competed share | 66.866% |
| Set-aside share | 7.549% |
| Performed in US / abroad | $744.2 bn / $34.3 bn |
| States & territories / congressional districts | 62 / 460 |

Report definition files are additionally validated against Microsoft's published PBIR
JSON schemas — 388 files checked.

---

## 11. Limitations

Stated here and on the report's own methodology page.

1. **Single fiscal year.** FY2025 only, so no year-over-year comparison is possible.
2. **Prime contracts only.** No sub-awards, grants, loans or direct payments.
3. **Transaction grain, not award lifecycle.** An award that began before FY2025 appears
   only through its FY2025 actions.
4. **Parent-company mapping** follows FPDS registration and occasionally names a foreign
   subsidiary as the corporate parent.
5. **Offers-received** is populated on only 32% of actions and carries a 999
   bulk-reporting value, so single-offer share is reported over actions with a recorded
   count only.
6. **The Award explorer is scoped to actions ≥ $100 M by default** (823 of them). This is
   a performance boundary: grouping a table by a 5.83 M-row award dimension does not
   return interactively. Widening the scope is a filter-pane change.
7. **Custom tooltip pages are not bound.** Both tooltip pages exist, are hidden and are
   correctly typed, but Power BI continues to show the default tooltip. The default is
   still informative. Binding is a two-click change per visual.
8. **Map visuals were unavailable** on the build machine because of a global Power BI
   security setting, so the geography page uses a ranked bar rather than a choropleth.
   This is an environment constraint, not a data constraint.

---

## 12. Reproducing this project

Requires Python 3.13, `duckdb`, `pyarrow`, and Power BI Desktop (built against
**2.158.1177.0**).

```bash
# 1. Point the pipeline at your local folders
set P06_ROOT=C:\your\path\06_US_Federal_Contracting_Intelligence
set P06_SCRATCH=D:\scratch\p06

# 2. Download the source archive from USAspending.gov
#    https://www.usaspending.gov/download_center/award_data_archive
#    file: FY2025_All_Contracts_Full_<date>.zip   (~1.79 GB)

# 3. Extract and stage
python pipeline/extract.py          # zip -> CSV parts on the scratch drive
python pipeline/stage_build.py      # 297 cols -> 63, CSV -> Parquet

# 4. Profile and prove the grain (optional but recommended)
python pipeline/profile.py
python pipeline/profile2.py

# 5. Build the star schema and assert integrity
python pipeline/build_star.py
python pipeline/add_sizeband.py
python pipeline/fix_dimdate.py
python pipeline/rebuild_data.py     # slim DimAward + partitioned output

# 6. Verify against the independent baseline
python pipeline/validate.py

# 7. Generate the report definition and validate it against the PBIR schemas
python pipeline/build_report.py
python pipeline/validate_pbir.py
```

Then open `powerbi/FederalContracting.pbip`, set the **DataFolder** parameter to your
local `data` folder (Home → Transform data → Edit parameters), and refresh.

`pipeline/validate_pbir.py` expects Microsoft's published PBIR JSON schemas in a local
folder; they are available at
[github.com/microsoft/json-schemas](https://github.com/microsoft/json-schemas).

---

## 13. Repository layout

```
powerbi/      PBIP project — report definition (PBIR) and semantic model (TMDL)
pipeline/     Python build pipeline: extract → stage → star → validate → report
design/       Power BI theme defining the design system
docs/         Design brief, visual QA log, completion report
provenance/   Source manifest with SHA-256 digests and retrieval metadata
```

Raw data, curated Parquet, Power BI caches and machine-local settings are deliberately
excluded — see [`.gitignore`](.gitignore).

---

## 14. Documentation

- [Design & architecture brief](docs/01-design-and-architecture-brief.md) — data inventory, grain proof, quality audit, model architecture, design system
- [Visual QA log](docs/02-visual-qa-log.md) — every rendering defect found and fixed, with the Power BI limitations hit and the workaround used for each
- [Completion report](docs/03-completion-report.md) — final state, validation table, known limitations

---

**Source:** USAspending.gov Award Data Archive, *All Contracts (Full)* FY2025 (archive
dated 2026-09-06, retrieved 2026-09-29). U.S. federal government works are in the public
domain.
