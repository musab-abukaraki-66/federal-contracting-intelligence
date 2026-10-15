# Page 01 — Executive brief · Visual QA log

Audit performed against the **rendered** page in Power BI Desktop 2.158.1177.0, not against the JSON.

## Issues found and fixed

| # | Issue | Cause | Fix |
|---|---|---|---|
| 1 | Navigation rail rendered as a solid bright-blue block | Button formatting properties were written without a state selector, so Power BI discarded them and fell back to the stock blue button style | Every button formatting object now carries `"selector": {"id": "default"}` (plus a `hover` state). Confirmed against JSON that Desktop itself writes |
| 2 | Rail background, rules and separators also rendered blue | Same root cause on the `shape` visual | Shape `fill` / `outline` objects given the same state selector |
| 3 | KPI values clipped top and bottom (`$793.2bn` cut off) | Card height 54 px with a 28 pt value and the card's own title competing for vertical space | Label and context line moved out into separate textboxes; card height 66 px, value 26 pt, card owns nothing but the number |
| 4 | Recipients displayed as `104K` | `labelDisplayUnits: 0` means *Auto*, not *None* | Set to `1` (None) → `104,476` |
| 5 | Auto-generated subtitles leaking field names (`Obligations and Obligations FYTD by Month Short`) | Power BI adds a subtitle from the field list unless suppressed | `subTitle.show = false` is now the default on every visual |
| 6 | Hero combo chart: monthly columns squashed to near-nothing | Cumulative FYTD line (up to $793 bn) shared scale with monthly columns (max $150 bn) | Cumulative line removed. The monthly column chart is now the hero and the September spike reads instantly; the cumulative fact lives in the annotation line |
| 7 | Legend consumed plot area for a single series | Legend left on | Legend off on single-series charts |
| 8 | Value axis labelled in `$0.5T` | Auto display units | Axis pinned to billions, 0 decimals |
| 9 | Bar charts scrolled — 7 of 8 and 7 of 10 categories visible | Insufficient height per category | Vertical rhythm rebalanced (hero row 228 px, supporting row 268 px), `innerPadding` reduced, departments panel given the full right column |
| 10 | Long parent-company names truncated (`UNITEDHEALTH GROUP INCORPORA…`) | Category label area too narrow | `maxMarginFactor` raised to 60 and the panel widened to two macro columns; all eight names render in full |
| 11 | Ten parents did not fit at executive-page height | Category count vs available height | New `Obligations · Top 8 Parents` measure. Eight rather than ten is a rendering decision, documented in the measure description |
| 12 | `Department of Defense` bar label clipped off the plot | DoD is 6× the next department, so the outside label overflowed | Data labels removed from that panel and the value axis switched on — no clipped text, scale still readable |
| 13 | Negative de-obligation bar collided with its own category label | Single axis mixing −$53.4 bn with +$293.9 bn | Visual-level filter excludes the *De-obligation* and *Zero dollar* bands; the chart now answers "how obligated dollars split by size". The de-obligation figure is still on the page, in the KPI context line |
| 14 | Two panels (`Competed vs not competed`, `Products/services/R&D`) rendered as empty boxes | 106 px tall was below the minimum render height | Removed from Page 01. Competition is stated numerically in the annotation; both belong on their own pages |
| 15 | Annotation text clipped at two lines | Textbox height too small | Height and column span corrected |

## Power BI limitations encountered, and the workaround used

| Limitation | Workaround |
|---|---|
| Button and shape formatting silently ignored without a state selector — undocumented in the JSON schema | Captured the JSON Power BI Desktop itself writes for a styled button, and mirrored its `selector` structure |
| `"Apply external changes"` reloads the **report** definition only, never the semantic model | Model edits are applied to the live engine over XMLA *and* written to TMDL, so both stay in sync without a reopen |
| The published `filterConfiguration` schema marks `$schema` as required, but Desktop rejects it on an inline visual `filterConfig` | `$schema` omitted inline; the local validator suppresses that one rule with a comment explaining why Desktop is authoritative |
| `.pbip` / PBIR schema versions in the docs are older than what this build writes | Generated a reference PBIP from Desktop and pinned the generator to the versions it actually emits (`visualContainer 2.12.0`, `page 2.1.0`, `report 3.3.0`, `versionMetadata 2.0.0`) |
| `report.json` no longer accepts `layoutOptimization` | Property removed |

## Current state

- **Model**: 186.5 MB, full refresh ≈ 2 min, peak `msmdsrv` RAM ≈ 1.2 GB
- **All baseline KPIs reconcile exactly** against the DuckDB source of truth
- **PBIR schema validation**: 175/175 files pass
- Page 01 renders with no overlap, no clipping, no truncation, no scrollbars and no default-blue styling

## Deliberately not done on Page 01

- Data labels on the departments panel (the axis carries the scale; labels clipped against the DoD bar)
- Competition and category breakdowns (moved to their own pages)
- Any high-cardinality column or expensive calculation added for visual reasons
