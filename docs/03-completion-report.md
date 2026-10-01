# Project 06 — U.S. Federal Contracting Intelligence
## Completion report

Built on the USAspending.gov Award Data Archive, *All Contracts (Full)* FY2025.
Every figure in the report reconciles to the DuckDB build of the source archive.

---

## 1. Pages delivered

| # | Page | Analytical role | Key visuals |
|---|---|---|---|
| 01 | **Executive brief** | Scale, time-shape, concentration | Monthly obligations, largest departments, action-size split, largest parent companies |
| 02 | **Market structure** | How dollars are actually transacted | Monthly obligations stacked by action class, pricing arrangement, action type |
| 03 | **Agencies** | Who commands the money, how they differ | Top 10 sub-agencies, top 8 departments, per-department behaviour table |
| 04 | **Contractors** | Market concentration | Top 10 recipients, top 8 parent groups, small-business comparison table |
| 05 | **Categories** | What is bought and how | Top 12 PSC categories, NAICS sectors, extent of competition |
| 06 | **Geography** | Where the work is performed | Top 12 states, region split, performance outside the US |
| 07 | **Award explorer** | Row-level evidence + drill-through target | Award table scoped to actions ≥ $100m |
| 08 | **Method & sources** | Provenance, grain, quality decisions, limitations | Six-panel editorial methodology page |

Two hidden tooltip pages (`Tooltip - recipient`, `Tooltip - agency`) also ship — see limitations.

## 2. Navigation

- **Rail** — 8 entries on every page, active item marked with a brass rule. Verified working
  (Ctrl+click in Edit mode, single click in View/published mode).
- **Drill-through** — right-click any recipient or department → *Drill through → Award explorer*.
  **Verified end to end**: Lockheed Martin → $50.8bn, 82 actions, 42 awards, $620m average action.
- **Back button** on the explorer returns to the originating page.
- **Cross-filtering** between visuals is on by default within each page.

## 3. Model

| | |
|---|---|
| Fact rows | 6,639,176 (one prime-contract action each) |
| Awards | 5,832,578 |
| Recipients | 104,476 |
| Dimensions | 11 + a measures table |
| Measures | 58 |
| VertiPaq size | **187.2 MB** |
| Full refresh | **~2 minutes** (82 s measured back-to-back on a warm engine; ~4 min on a cold open where Desktop loads concurrently) |
| Peak `msmdsrv` RAM | ~1.2 GB |

## 4. Data validation — every page

All checked with live DAX against the DuckDB baselines. Exact matches:

| Figure | Value |
|---|---|
| Obligations | $793,189,920,124.27 |
| Contract actions | 6,639,176 |
| Awards | 5,832,578 |
| Recipients | 104,476 |
| Base award vs modification | $327.6bn / $465.5bn |
| De-obligations | −$53.36bn |
| Awarding organisations | 168 |
| Cross-serviced | $75.7bn |
| Defense share | 61.996% |
| September share | 18.966% |
| Actions ≥ $100m | 823, carrying 37.054% |
| Top 10 parent share | 28.735% |
| Market concentration (HHI) | 139 |
| Small business share | 21.348% |
| Competed share | 66.866% |
| Set-aside share | 7.549% |
| US / foreign performance | $744.2bn / $34.3bn |
| States & territories / districts | 62 / 460 |

## 5. Power BI limitations encountered, and what was done

| Limitation | Resolution |
|---|---|
| Button and shape formatting is silently dropped without `{"selector": {"id": "default"}}` | Mirrored the JSON Desktop itself writes; applies to every button and shape |
| `stackedColumnChart` is not a valid visual type name | The built-in stacked column is `columnChart` with a Series role |
| Custom theme silently ignored | `customTheme.name` must equal the resource item name **including `.json`**. This also fixed dark-on-dark tables |
| `VAR Rank` and `VAR Key` are reserved DAX keywords | Renamed to `Rnk` / `AwardUrlKey` |
| RANKX over a different column than the chart's axis makes every row rank first | Each ranked measure now ranks over the exact column its chart groups by |
| **Map visuals disabled** by a global security setting on this machine | Geography page uses a ranked state bar instead of a choropleth — same data, no dependency on a tenant setting |
| Grouping a table by `DimAward[Award PIID]` (5.83m rows) times out | Explorer scoped to actions ≥ $100m and the table narrowed to four columns; measured at ~1.8 s |
| Slicers rendered headers with no item list | Replaced with page scope + the native filter pane + drill-through, rather than fighting the control |
| Inline visual `filterConfig` rejects `$schema` although the published schema requires it | Omitted inline; the local validator suppresses that one rule |
| Desktop writes newer PBIR schema versions than the docs show | Generator pinned to `visualContainer 2.12.0`, `page 2.1.0`, `report 3.3.0`, `versionMetadata 2.0.0` |

## 6. Known limitations

1. **Single fiscal year.** FY2025 only — no year-over-year comparison is possible.
2. **Prime contracts only.** No sub-awards, grants, loans or direct payments.
3. **Custom tooltip pages are not bound.** Both tooltip pages exist, are hidden, and are correctly
   typed, but Power BI keeps showing the default tooltip. The default is still informative
   (entity, obligations, drill-through hint). To bind: select a chart → Format visual → Tooltips →
   Type *Report page* → pick the page. Two clicks per visual.
4. **Explorer is scoped to actions ≥ $100m by default.** Widening it is a filter-pane change; the
   scope exists because a 5.83m-row award dimension cannot be grouped interactively.
5. **Map visuals unavailable** in this environment (global security setting, not a report defect).
6. **Parent-company mapping** follows FPDS registration and occasionally names a foreign subsidiary
   as the corporate parent (RTX entities appear under Rockwell Collins Australia).
7. **Offers-received** is recorded on only 32% of actions and carries a 999 bulk-reporting value, so
   single-offer share is reported over actions with a recorded count only.

## 7. QA status

| Gate | Result |
|---|---|
| PBIR schema validation | **PASS** — 388 files (1 page not locally checkable: the drill-through binding references a schema version absent from the offline mirror; Desktop accepts it) |
| Project opens | **PASS** |
| All 8 pages render | **PASS** |
| Data reconciliation | **PASS** — every headline figure matches source |
| Navigation | **PASS** — rail + drill-through + back, all clicked and verified |
| Broken visuals | **None** |
| Layout defects | None observed at 1440×900 |
| Performance | Model 187.2 MB, refresh ~2 min, no regression |
