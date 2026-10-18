# BUILD_SPEC: Medi-Cal language-access planning

## Vision and scope

A DHCS Medi-Cal access strategy manager uses this tool to decide which county-language populations deserve further review or additional language-access planning. It replaces manual comparison of separate demographic files with consistent county comparisons and explicit data-availability indicators.

Phase 1 considered provider recruitment, telehealth, and transportation. The current scope is language-population prioritization using three eligibility datasets. These data describe population size and composition, not interpreter supply, appointment access, service shortages, or intervention effects. Provider-capacity integration is outside this MVP.

**Phase 2 deliverables:** canonical data, reusable backend, and this specification. **Phase 3 instruction:** build the local dashboard below using the existing backend. Do not redo analysis inside UI components. The interface is not a Phase 2 deliverable.

## Use cases and supporting views

| User selects/inputs | Dashboard shows | User decides | Supporting feature |
| --- | --- | --- | --- |
| Month and language | All counties' selected-language counts and geographic distribution | Which counties have the largest populations to review? | Map, count ranking, overview coverage |
| County comparisons for that month/language | Count, county total, and valid language share side by side | Which counties have both substantial volume and a relatively concentrated language population? | Sortable comparison table with share column |
| County, through map, ranking, or selector | Selected-language metrics and overall county age/sex and race/ethnicity context | What county context should inform the next planning discussion? | County detail and demographic charts |
| Another month or language | All affected views update consistently, retaining county where available | Does the review priority differ under the new selection? | Shared filter state and visible selection labels |

There is no combined priority score or automatic recommendation: volume and share remain separate evidence for the manager's judgment.

## Starting view and interactions

Use one page titled **Medi-Cal language-access planning**. Start with the latest available month, Spanish, and Los Angeles County. Derive months/languages/counties from loaded data. If a default is absent, use the latest month and first alphabetic available language/county.

1. Sidebar: month, language, and county selectors. Show readable language names; keep canonical slugs as values. Preserve ASL and distinguish Missing/Unknown from Unknown. Age labels are 0–18, 19–44, 45–64, 65+; race labels expand AI/AN to American Indian/Alaska Native and retain the source's other labels.
2. Overview: selected month/language, observed language-count subtotal, number of counties with an observed count out of 58, and number with a valid share out of 58. Label the subtotal **Observed count across available counties**. Show a complete statewide count/share only when the backend marks it complete.
3. Comparison: California county map beside a table containing rank, county, language count, county total, and language share. Default table order is descending count with alphabetical ties; allow sorting by share for concentration comparisons. Include all 58 counties, with unavailable values at the end. Use the county selector as an accessible alternative to chart selection.
4. County detail: selected county heading, language count, total eligibles, valid language share, overall county age-by-sex grouped bars, and race/ethnicity bars aggregated across ages. Always label demographic charts **All Medi-Cal eligibles in this county**. They are not demographics of the selected-language population.
5. Footer: DHCS source attribution, snapshot month coverage, preliminary/final status explanation, and the population-versus-capacity limitation above.

Changing month/language updates overview, map, table, and county language metrics. County context changes with month/county; it does not depend on language. Map or table selection updates the same county state used by the selector. Clear stale chart selections on filter changes so they do not override the user's county choice. If the retained county is unavailable in a new month, select the first available county and display a brief explanation.

Map: sequential blue scale of raw selected-language counts, with a new scale for each selection and an explicit count legend. Keep unavailable counties gray in a separate trace, including county hover labels; gray must differ from an observed zero. Highlight the selected county with an outline. Hover shows county, count, total, and share. Do not imply cross-month color comparability.

Formatting: counts use comma-separated integers; shares use percentages with one decimal, while a positive share below 0.1% displays `<0.1%`. Backend shares are fractions. Display missing values as **Unavailable** with a reason where known; never as zero, blank bars, or an inferred suppressed number. Missing demographic groups get an explicit unavailable label instead of a zero-height bar. If every count for a language is unavailable, retain the county map/table and explain that no observed counts can be ranked.

## Canonical data and sources

Runtime file: `dso576/project/medi_cal_merged_county_month.csv`, resolved by `medi_cal_analysis.DEFAULT_DATA_PATH` independently of the current working directory. This is the only canonical runtime dataset; older language-only outputs and `exploration.ipynb` are exploratory artifacts.

The checked snapshot contains **11,658 rows × 74 columns**, **58 counties × 201 months**, January 2010–September 2026. Counts for recent months can be preliminary and later revised. `status` is F (final) or P (preliminary); `date_of_data` is an ISO source date or missing. Do not claim the filename's date is the publication date.

Three DHCS [Medi-Cal Certified Eligibles demographic resources](https://data.ca.gov/@california-department-of-health-care-services/medi-cal-certified-eligibles-data-by-month-with-demographics) are inputs:

| Source | Original source cell | Canonical family |
| --- | --- | --- |
| By Primary Language | month + county + language | 33 `language__...` columns |
| By Age Group and Sex | month + county + age group + gender | 8 `age_sex__{age}__{sex}` columns |
| By Race/Ethnicity and Age Group | month + county + age group + ethnicity | 24 `race_age__{age}__{race}` columns |

Exact URLs, source hashes, exclusions, and snapshot comparison are in `outputs/cleaning_report.json`; reproducible commands and reconciliation evidence are in `CLEANING.md`.

### Cleaning contract

- Final unit: one row per `month_of_eligibility + county`; duplicate keys after normalization are errors requiring review.
- Months are `YYYY-MM` strings. County names use the 58-name California allowlist. Normalize whitespace/case and reject statewide, invalid county, missing county, and invalid month rows. Keep otherwise valid rows even when individual cells are suppressed.
- Normalize categories to documented lowercase slugs. Keep source categories separate, including `missing_unknown` and `unknown`. Unexpected categories, malformed count tokens, and source-cell duplicates stop the build.
- Counts are nonnegative numeric whole values or missing. Nullable numeric output preserves missingness; CSV empty cells mean unavailable. Suppressed primary/complementary counts (annotation codes 1/2) stay missing. Absent source categories also stay missing; absence does not establish zero.
- Pivot each source to county-month before joining, require matching county-month coverage and publication metadata, and validate every join as one-to-one. Never merge the raw demographic rows directly.
- `language_suppressed_cells`, `age_sex_suppressed_cells`, and `race_age_suppressed_cells` count explicitly suppressed source cells, not every missing canonical cell. Their values are nonnegative integers.
- `county_total_eligibles` is the sum of all eight age/sex cells only when every required cell is observed. Otherwise it is missing and `county_total_is_complete` is False. Completeness is a Boolean, not truthiness of a CSV string. The checked snapshot has 85 incomplete totals.
- Available source counts are retained; do not recover or estimate suppressed values by subtraction. Population dimensions are separate county summaries, not an individual language-by-age-by-race cross-tabulation.

`CLEANING.md` records available team artifacts and unresolved team-review evidence. Do not represent unavailable individual cleaning scripts or absent teammate approval as verified agreement.

## Metric and visual definitions

All county comparisons use the selected month and language. Demographic context uses selected month and county only.

| Metric / visual and question | Source columns | Calculation / missing behavior | Backend output |
| --- | --- | --- | --- |
| Month and language options: what can be selected? | `month_of_eligibility`, `language__*` | Distinct months chronological; language slugs alphabetical | `get_available_months`, `get_available_languages` |
| Map / count ranking: where are the largest selected-language populations? | County, selected `language__*` | Direct count; descending count; ties alphabetical and competition rank (1, 1, 3); missing last with no rank | `get_map_data`, `get_county_ranking` |
| County total: what is the eligible population denominator? | Eight `age_sex__*`, completeness flag | Complete sum only; otherwise unavailable | `get_county_metrics`, `get_county_summary` |
| Language share: where is this population relatively concentrated? | Selected count, county total, completeness flag | Count / total only if count observed, total complete and positive; otherwise unavailable | `get_language_share` |
| Overview: how much of the selected language population is observed? | All selected-month county counts | Observed subtotal with explicit coverage; full count requires all 58 observed; full share requires all 58 counts and complete positive total | `get_month_summary` |
| Age/sex context: how is the county population distributed? | Eight `age_sex__*` | Eight direct cells; optional age/sex aggregation requires every cell in its group | `get_age_sex_summary` |
| Race context: what is overall county race/ethnicity composition? | 24 `race_age__*` | Six race totals across four ages; any unavailable component makes its group unavailable | `get_race_ethnicity_summary` |

Demographic `share_of_county` uses the same complete positive age/sex denominator. The overview ratio is a ratio of complete totals, never an average of county shares. `get_county_metrics` includes availability flags and share-unavailability reasons. Full input/output contracts and executable examples are in `ANALYSIS.md`; analysis implementations belong in Python files, not here.

## Architecture and technical choices

Use Python 3.11+ with pandas for the backend; the existing environment uses Python 3.13. For Phase 3 use Streamlit and Plotly. CSV plus an in-memory DataFrame fits this small dataset; no database, remote query service, credentials, or live DHCS calls are needed at dashboard runtime.

| Component | One job | Input → output / boundary |
| --- | --- | --- |
| `medi_cal_analysis/cleaning.py` | Rebuild and audit three raw sources | Raw CSVs → canonical CSV + JSON audit; separate offline command |
| `medi_cal_analysis/data.py` | Load and validate data contract | Path/DataFrame → typed, validated, sorted county-month DataFrame |
| `medi_cal_analysis/analysis.py` | Compute reusable dashboard datasets | Validated DataFrame + explicit filters → lists/DataFrames; no UI state or drawing |
| Phase 3 `dashboard/charts.py` | Build figures | Backend results + geometry → Plotly figures; no file reads or metric recomputation |
| Phase 3 `dashboard/app.py` | Compose page and manage filters | Selectors/selection events → backend calls, rendering, shared county state |
| Phase 3 geometry adapter | Load and check geographic join | Local county boundaries → GeoJSON with unique county names |

For the Phase 3 geometry adapter, use Census [2025 county cartographic boundaries at 1:5,000,000](https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_county_5m.zip). Filter `STATEFP == '06'`, transform NAD83 to WGS84/EPSG:4326, and write local `data/california_counties.geojson` once during setup. Preserve `NAME` as `properties.county`; join the backend's `county` to that property. Require exactly 58 unique matching county names and zero unmatched backend keys. Geometry is a display asset, never a population data source. No live tile/boundary download is required during dashboard use.

Load/validate data and geometry once with [Streamlit data caching](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data), including file modification time in cache inputs. Reuse prepared data across calls; restrict chart/table computations to the selected month's 58 rows. Keep all state in Streamlit session state, separate from pure analysis functions. Use supported [chart selection events](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart) and selectable comparison rows to set county state. Map selection must be checked in the Phase 3 browser test; the county selector always remains available.

Show actionable load/validation errors and stop dependent rendering; do not display stale metrics after failure. Keep charts independently testable with prepared DataFrames. Check that warm filter updates complete within two seconds locally on the development machine; record measurements during Phase 3 rather than promising a deployment latency.

## Build order

1. Run the backend tests and cold-start example from `README.md`; inspect cleaning audit and canonical coverage. Resolve any changed-source validation error before UI work.
2. Prepare and validate the local 58-county geometry asset. Build selectors and shared state, loading the canonical data once.
3. Render overview, map, and comparison table from backend outputs; verify observed zero versus unavailable values.
4. Wire map/table/selector county synchronization and filter resets; add county detail and demographic figures.
5. Add readable labels, missing-value explanations, source notes, and responsive layout; test the actual browser interactions and document setup/run instructions.

## Acceptance checks

Phase 2 checks (automated where possible):

- Canonical keys unique; exactly 58 valid counties for each of the 201 checked months; no statewide or invalid county identifiers.
- Every complete county total equals all eight observed age/sex cells; incomplete totals unavailable; suppressed and absent cells never converted to zero.
- All three sources reshaped before one-to-one joins; source coverage/vintage mismatch, unknown category, malformed count, and duplicate source cell raise review errors.
- Every required backend output runs for real data, including each of the 33 languages in the first/latest month and demographic summaries for every county in those months.
- Fixtures verify true zero, missing numerator, incomplete/zero denominator, tied ranking, partial demographic groups, and incomplete overview coverage. Calls do not mutate input data.
- Code, canonical data, audit, spec, and README agree. Commit the reconciled result to local `main`; no claim of remote submission or teammate sign-off without evidence.

Phase 3 checks:

- Startup displays latest month / Spanish / Los Angeles and all specified views without additional data decisions.
- Changing filters updates every dependent view; selecting a county from map, table, or selector keeps detail synchronized without stale selection overrides.
- Map has 58 matched counties, observed count colors, gray unavailable counties, correct hover values, and selection highlighting.
- County language share matches backend values; unavailable values have explanations; demographics clearly refer to the overall county population.
- All-unavailable language and incomplete small-county totals render clearly. No suppressed value is estimated; no population measure is labeled interpreter capacity or shortage.
- A fresh coding agent can follow this spec without important product/data/metric guesses. Record questions and fixes in `PHASE_2_STATUS.md`; distinguish a true independent-agent review from a scripted cold-start check.
