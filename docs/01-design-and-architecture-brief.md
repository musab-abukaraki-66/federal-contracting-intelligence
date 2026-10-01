# Project 06 — U.S. Federal Contracting Intelligence
## Design & Architecture Brief

**Source of record:** USAspending.gov Award Data Archive — *All Contracts (Full), FY2025*
(`FY2025_All_Contracts_Full_20260906.zip`, 1.79 GB compressed / 13.6 GB uncompressed, 7 CSV parts)
**Extraction date:** 2026-09-29 · **Coverage:** 2024-10-01 → 2025-09-30 (US federal fiscal year 2025)
**Profiling engine:** DuckDB 1.5.6 over the full 6.64 M-row extract (no sampling).

---

## 1. Dataset inventory

| File | Type | Size | Rows | Role |
|---|---|---:|---:|---|
| `FY2025_All_Contracts_Full_20260906.zip` → 7 × CSV | CSV, 297 columns | 13.6 GB unzipped | 6,639,176 | Prime-contract transactions (fact source) |
| `toptier_agencies.json` | USAspending API reference | 52 KB | 111 agencies | Agency abbreviations, slugs, budget context |
| `data_dictionary.json` | USAspending API reference | 358 KB | 457 element definitions | Column definitions for the methodology page |
| `Data_Dictionary_Crosswalk.xlsx` | Official crosswalk | 110 KB | — | Cross-reference of element names |

The archive splits at exactly 1,000,000 rows per CSV part (6 full parts + 639,176 rows).

## 2. Grain — validated, not assumed

**One row = one prime-contract transaction (a contract action: base award, modification, option exercise,
funding action, termination, close-out).**

Evidence:
- `contract_transaction_unique_key`: 6,639,176 distinct over 6,639,176 rows → **unique, zero duplicates**.
- `contract_award_unique_key`: 5,832,578 distinct → a contract award averages 1.14 transactions.
- `action_type` is blank on 80.8 % of rows (FPDS convention for a **base** action) and carries
  modification semantics on the rest (option exercise, change order, termination, close-out).

Consequence for the model: **only `federal_action_obligation` is additive.**
`total_dollars_obligated`, `current_total_value_of_award` and `potential_total_value_of_award` are
award-level snapshots repeated on every transaction of that award — 132,427 awards carry *differing*
snapshot values across their own transactions. Summing them would double-count. They are excluded from
the fact table and surfaced only at award grain (latest transaction per award) in `DimAward`.

## 3. Data-quality audit (full population, not a sample)

| Finding | Measured | Treatment |
|---|---|---|
| Duplicate transactions | 0 | none needed |
| Negative obligations | 268,758 rows, −$53.36 B | **Kept.** De-obligations, terminations, close-outs are real accounting events. Exposed as its own measure. |
| Zero-dollar transactions | 694,741 rows | **Kept.** Administrative actions (address change, close-out). Counted separately from dollar flow. |
| Extreme values | min −$4.29 B, max $14.15 B (single action) | **Kept.** Legitimate large defence/health actions. |
| Dates outside FY2025 | 0 rows | data is clean on period |
| `action_type` blank | 80.8 % | **Structural**, not missing: FPDS leaves it blank for base awards. Relabelled "Base award" in `DimActionType`. |
| `type_of_set_aside` blank | 77.4 % | **Structural**: no set-aside applied. Relabelled "No set-aside recorded". |
| `idv_type` blank | 95.3 % | **Structural**: only IDV rows carry it. |
| Place-of-performance country blank | 4.70 % (311,910 rows) | **Structural**: exactly equals the IDV row count — IDVs have no performance location. Assigned an explicit "Not applicable (IDV)" member. |
| `number_of_offers_received` blank | 67.9 % | Reported only for competed actions. Measures using it are scoped to non-blank rows and labelled as such. |
| Recipient name inconsistency | `recipient_uei` → multiple `recipient_name`: **0 cases** | UEI is a reliable key. Recipient dimension is keyed on UEI, not name. |
| Parent-company mapping quirk | `ROCKWELL COLLINS AUSTRALIA PTY LIMITED` appears as parent of Raytheon/RTX entities ($32.8 B) | **Real FPDS registration artefact, not corrupt data.** Documented on the methodology page; recipient and parent are presented as two explicitly labelled views, never silently merged. |
| Award spanning agencies | 3,768 awards (0.065 %) touch >1 sub-agency | Documented; agency analysis is done at transaction grain, where it is exact. |
| Recipient state blank | 1.97 % | Assigned an "Unknown" member; never silently dropped. |

No record is deleted, imputed or corrected. Every exclusion is a column-level design decision, stated above.

## 4. Headline facts the data actually supports

- **$793.19 B** obligated across **6.64 M** transactions and **5.83 M** awards to **104,476** recipients.
- **September 2025 alone = $150.43 B (19.0 % of the year)** — the fiscal year-end obligation surge.
- **Department of Defense = $491.75 B (62.0 %)**; Navy $176.56 B, Army $107.45 B, Air Force $98.45 B.
- **823 transactions of ≥ $100 M carry $293.91 B — 37.1 % of all dollars from 0.012 % of the rows.**
  Conversely 4.65 M transactions under $10 K carry 0.65 % of the dollars.
- **Concentration:** top 10 parent recipients = 28.3 % of obligations; top 100 = 56.3 %; top 1,000 = 80.0 %.
- **Small business = $172.96 B (21.8 %)** of obligations but 51 % of transactions.
- **Competed dollars ≈ 66.8 %**; "Not competed" carries $214.05 B.
- Defense Logistics Agency issues **3.91 M transactions (59 % of all rows) for $55.94 B** — a high-volume,
  low-value supply channel, structurally different from the rest of federal contracting.

## 5. Model architecture — star schema

```
                 DimDate (365 rows, FY2025)
                        |
 DimAgency (awarding)   |   DimAgency (funding, role-playing)
          \             |             /
           \            |            /
 DimRecipient ----- FactContractTransactions ----- DimAward
 (104 K, UEI key)       |      |      |            (5.83 M, award grain)
                        |      |      |
        DimNaics (1.1 K)|      |      | DimPsc (2.4 K)
                        |      |
        DimCompetition  |  DimPlaceOfPerformance
        DimContractType |  DimActionType
```

**FactContractTransactions** — 6,639,176 rows, integer surrogate keys only, plus `Obligation` (decimal).
No text columns. No award-level snapshot amounts.

**Dimensions**

| Dimension | Rows | Key | Notes |
|---|---:|---|---|
| `DimDate` | 365 | DateKey (yyyymmdd) | Fiscal-year attributes (FY, fiscal quarter, fiscal month index), marked as date table |
| `DimAgency` | ~170 | AgencyKey | Agency + sub-agency, enriched with `abbreviation` from `toptier_agencies.json` |
| `DimRecipient` | 104,476 | RecipientKey (UEI) | Name, parent UEI + parent name, city/state/country, business size, socio-economic flags |
| `DimAward` | 5,832,578 | AwardKey | PIID, parent PIID, award-or-IDV, ceiling values from the award's **latest** FY2025 transaction, USAspending permalink |
| `DimNaics` | 1,140 | NaicsKey | Code, description, 2-digit sector (official NAICS structure) |
| `DimPsc` | 2,428 | PscKey | Code, description, first-character category (official PSC structure: products / services / R&D) |
| `DimCompetition` | small | CompetitionKey | Junk dim: extent competed, solicitation procedures, set-aside, derived "Competed (Y/N)" |
| `DimContractType` | small | ContractTypeKey | Junk dim: award-or-IDV flag, award type, IDV type, pricing type, pricing family (fixed / cost / other) |
| `DimActionType` | ~22 | ActionTypeKey | Base award vs modification class |
| `DimPlaceOfPerformance` | ~20 K | PlaceKey | Country, state, county, congressional district |

Role-playing: funding agency is a second, inactive relationship to `DimAgency`, activated by
`USERELATIONSHIP` in dedicated measures rather than duplicating the dimension.

Every dimension is derived from the data itself; none exists only to enlarge the diagram.

## 6. Transformation strategy

1. **Extraction** — the 1.79 GB zip is never modified. CSVs stream to a scratch area on `D:`
   (`<SCRATCH>`), outside the raw-data folder.
2. **Column pruning at read time** — 297 columns → 63 retained at staging (78 % dropped: contact details,
   81 of 90 socio-economic booleans, officer-compensation blocks, treasury/object-class strings,
   duplicated code/description pairs).
3. **Staging** — Parquet, ZSTD, 300 K-row groups: 13.6 GB → ~600 MB on disk.
4. **Star build in DuckDB** — dimensions built by `DISTINCT`, assigned dense integer surrogate keys;
   the fact is rewritten with keys only. Power Query does no heavy lifting; it reads finished Parquet.
   This keeps refresh viable on a 7.8 GB / 4-core machine.
5. **Excluded from the model** — `transaction_description` (4.68 M distinct values), recipient address
   lines, phone/fax, officer names and amounts, treasury/federal-account strings. Rationale:
   cardinality cost with no analytical role at this altitude.
6. **Type discipline** — money as decimal, dates as date, all keys as 32-bit integers, codes as text
   only inside dimensions.

## 7. Performance strategy

- Fact holds **integer keys + one decimal measure**; VertiPaq compresses this tightly.
- No calculated columns on the fact table; all business logic lives in DAX measures.
- High-cardinality text lives once, in a dimension, never repeated 6.6 M times.
- `DimAward` (5.8 M rows) is the single large dimension; it exists so transaction drill-through is honest.
  It is hidden from the field list except on the detail page and carries five columns.
- Every visual aggregates; row-level detail appears only on the drill-through page under a mandatory
  filter context.
- Target: model under 1 GB in memory, page render under 2 s on the target machine.

## 8. Analytical questions the report answers

1. What is the shape and scale of FY2025 federal contract obligations, and how does the fiscal
   year-end surge distort it?
2. Which agencies and sub-agencies command the money, and how differently do they buy?
3. How concentrated is the contractor market, and who sits at the top?
4. How much is genuinely competed, and where does non-competition concentrate?
5. What is bought (PSC / NAICS), and how does the product-versus-service split differ by agency?
6. Where is the work performed, and which states depend most on federal contracting?
7. What does a single transaction look like, with full provenance back to USAspending?

## 9. Visual direction — "Federal Ledger"

Editorial-intelligence aesthetic: dark, restrained, typographic — closer to a printed institutional
report than to a SaaS dashboard. Density is earned, not decorative.

- Layered dark neutrals (true warm greys, never pure black); hairline separators instead of shadowed cards.
- One metal accent (brass) reserved for the primary value in any view; everything else neutral.
- Charts sit on the page background, not inside boxes. Structure comes from alignment and rules.
- Translucency used **once**: a single header band on the executive page over a duotone photograph.
  Nowhere else. No glassmorphism.
- No gradients on data marks, no shadows on data marks, no non-functional icons.

**Grid** — canvas 1440 × 900. 76 px left navigation rail. 24 px outer margin, 12 columns, 16 px gutters.
Every element snaps to the grid; vertical rhythm on an 8 px baseline.

## 10. Typography

Three roles, all Power BI-safe faces so rendering is identical in Desktop and Service:

| Role | Face | Treatment |
|---|---|---|
| Section / page titles, narrative | **Georgia** | Serif, editorial gravitas, sentence case, generous leading |
| KPI values, axes, labels, UI | **Segoe UI Light / Semibold** | KPI numerals in Light at 40–56 px; labels in Semibold at 10–11 px, uppercase, wide tracking |
| Codes (PIID, UEI, NAICS, PSC) | **Consolas** | Monospace so identifiers align and read as data |

Number formatting is fixed report-wide: `$0.0 B` above a billion, `$0.0 M` above a million, `#,##0` for
counts, one decimal maximum, percentages to one decimal.

## 11. Color system

| Token | Hex | Use |
|---|---|---|
| `bg/base` | `#0D0F12` | page background |
| `bg/surface` | `#14171C` | header band, drill-through panels |
| `bg/elevated` | `#1B1F26` | hover and selected states |
| `line/hairline` | `#262B33` | separators, gridlines |
| `text/primary` | `#E8EAED` | values, titles |
| `text/secondary` | `#9AA3AE` | labels |
| `text/muted` | `#5F6873` | source notes, footnotes |
| `accent/brass` | `#D4A843` | the single highlighted value per view |
| `accent/steel` | `#6FA8C7` | secondary series |
| series | `#D4A843 · #6FA8C7 · #8FB98A · #C77E6B · #9B8FC0 · #7D8894` | categorical, maximum 6 |
| `positive` | `#7FB069` | obligations up / competed |
| `negative` | `#C25B4E` | de-obligations / not competed |

Sequential ramps derive from brass; the diverging scale runs steel ↔ clay. No rainbow palettes, never
more than six categorical colors in one visual.

## 12. Image direction

One photograph only, on the executive page header, treated as a duotone in `bg/base` + `accent/brass`
at low opacity behind the title block. Subject: US federal architecture / infrastructure.
Source restricted to **public-domain US government works** (Library of Congress, NASA, DoD), credited on
the methodology page. No stock-photo collage; no imagery on analytical pages.

## 13. Page architecture (7 pages + 2 tooltip pages)

| # | Page | Question it answers |
|---|---|---|
| 01 | **Executive Brief** | Scale, shape, concentration and the year-end surge, in one screen |
| 02 | **Agencies & Departments** | Who commands the money and how their buying differs |
| 03 | **Contractor Intelligence** | Market concentration, top recipients, small-business reality |
| 04 | **Competition & Contract Structure** | How much is competed, pricing mix, set-asides, IDV structure |
| 05 | **Geography** | Where performance happens; state dependence |
| 06 | **Transaction Explorer** | Row-level drill-through with provenance links |
| 07 | **Method & Dictionary** | Source, extraction, transformations, assumptions, limitations, field definitions |
| T1 | *Tooltip — Recipient* | Recipient profile on hover |
| T2 | *Tooltip — Agency* | Agency profile on hover |

Seven pages because the data supports seven distinct questions — not to hit a target count.

## 14. Known limitations (stated in the report, not hidden)

1. **Single fiscal year.** FY2025 only, so no year-over-year growth. All trend analysis is intra-year.
2. **Prime contracts only.** No sub-awards, grants, loans or direct payments.
3. **Transaction grain, not award lifecycle.** An award that began before FY2025 appears only through its
   FY2025 actions.
4. **Parent-company mapping** follows FPDS registration and occasionally names a foreign subsidiary as the
   corporate parent (documented case: RTX / Rockwell Collins Australia).
5. **Agency-reported data** carries reporting lag and correction; the archive is a 2026-09-06 snapshot.
6. **Ceiling values** in `DimAward` are those recorded on the award's latest FY2025 transaction, not a
   full contract-lifecycle ceiling.

## 15. Expected final deliverable

```
06_US_Federal_Contracting_Intelligence/
└── 02_PowerBI_Ready/
    ├── data/     curated Parquet star schema (fact + 10 dimensions)
    ├── pbip/     PBIP project
    │   ├── FederalContracting.SemanticModel/   TMDL model, relationships, measures
    │   └── FederalContracting.Report/          PBIR pages, visuals, theme, bookmarks
    ├── design/   theme JSON, image assets
    ├── docs/     this brief, data-quality findings, QA log
    └── scripts/  reproducible build scripts (extract → stage → star)
```
