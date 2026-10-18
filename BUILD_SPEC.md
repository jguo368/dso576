# BUILD_SPEC: Medi-Cal language-access planning

## Vision and use cases

A DHCS Medi-Cal access strategy manager uses this tool to decide which county-language populations deserve further review or language-access planning. It replaces manual comparison of separate demographic files with consistent county comparisons and visible data-availability indicators.

Phase 1 considered provider recruitment, telehealth, and transportation. The current scope is population prioritization using eligibility demographics. These data do not measure interpreter supply, appointment availability, service shortages, or intervention effects; provider-capacity integration is outside this MVP.

**Phase 2:** canonical data, reusable backend, and this specification. **Phase 3:** build the dashboard below using the existing backend. The interface is not a Phase 2 deliverable.

| User selects/inputs | Dashboard shows | User decides | Supporting feature |
| --- | --- | --- | --- |
| Month and language | County counts and geographic distribution | Which counties have the largest populations to review? | Map, ranking, overview coverage |
| County comparisons | Count, county total, and valid language share | Which counties have substantial volume or concentration? | Sortable comparison table |
| County through map, table, or selector | Language metrics and overall county demographic context | What local context should inform planning? | County detail, age/sex and race charts |
| Another month or language | All dependent views update, retaining county where available | Does the review priority change? | Shared filter state |

Keep count and share separate; do not invent a combined priority score.

## Starting view and interactions

Use one page titled **Medi-Cal language-access planning**. Default to the latest available month, Spanish, and Los Angeles. Derive options from loaded data; if a default is absent, use the latest month and first alphabetic available language/county.

| Section | Content and behavior |
| --- | --- |
| Sidebar | Month, language, and county selectors. Show readable labels while retaining canonical identifiers. Preserve ASL; distinguish Missing/Unknown from Unknown. |
| Overview | Selected month/language, **Observed count across available counties**, counties with observed counts out of 58, and counties with valid shares out of 58. Show a complete statewide count/share only when valid under the metric rules below. |
| Comparison | California county map beside a table of rank, county, language count, county total, and language share. Default order is descending count; allow share sorting. Retain all 58 counties, placing unavailable values last. |
| County detail | Language count, county total, share, age-by-sex grouped bars, and race/ethnicity bars summed across ages. Label demographic charts **All Medi-Cal eligibles in this county**. |
| Footer | DHCS attribution, snapshot coverage, preliminary/final status explanation, and the population-versus-capacity limitation above. |

Month/language changes update overview, map, comparison, and county language metrics. Demographic context depends on month/county only. Map, table, and selector share one county selection; clear stale chart selections on filter changes. If the county is unavailable in a new month, select the first available county and explain the change. Keep the selector as an accessible alternative to chart selection.

Map colors encode raw selected-language counts using a sequential blue scale recalculated for each selection, with a count legend. Keep unavailable counties gray and distinct from observed zero, outline the selected county, and include county/count/total/share in hover. Colors are not comparable across filter selections.

Format counts as comma-separated integers and shares as percentages with one decimal; show positive shares below 0.1% as `<0.1%`. Missing results display **Unavailable**, with a reason where known. Missing demographic bars need explicit unavailable labels. If all counts are unavailable, retain the county map/table and explain that no observed counts can be ranked. Age labels are 0–18, 19–44, 45–64, 65+; expand AI/AN to American Indian/Alaska Native.

## Data contract

Runtime file: `dso576/project/medi_cal_merged_county_month.csv`, resolved by `medi_cal_analysis.DEFAULT_DATA_PATH`. The checked snapshot has **11,658 rows × 74 columns: 58 counties × 201 months, January 2010–September 2026**. Older language-only outputs and notebooks are exploratory artifacts.

The three [DHCS demographic resources](https://data.ca.gov/@california-department-of-health-care-services/medi-cal-certified-eligibles-data-by-month-with-demographics) become:

| Source | Original source cell | Canonical columns |
| --- | --- | --- |
| Primary Language | month + county + language | 33 `language__*` |
| Age Group and Sex | month + county + age + gender | 8 `age_sex__{age}__{sex}` |
| Race/Ethnicity and Age Group | month + county + age + ethnicity | 24 `race_age__{age}__{race}` |

Final keys are unique `month_of_eligibility + county`: monthly `YYYY-MM` strings and standardized names from the 58-county allowlist. Counts are nullable, nonnegative whole-valued numerics; `county_total_is_complete` is Boolean. Publication metadata is `status` F/P and `date_of_data` ISO-or-missing; recent preliminary counts may be revised.

Pivot each source before one-to-one joins and require matching coverage/publication metadata. Exclude statewide, invalid/missing county, and invalid month rows. Duplicate source cells or final keys, unknown categories, and malformed counts require review. Preserve distinct source labels, including `missing_unknown` and `unknown`.

Annotation codes 1/2 identify primary/complementary suppression; suppressed and absent category cells stay unavailable. An observed zero remains zero. The `language_suppressed_cells`, `age_sex_suppressed_cells`, and `race_age_suppressed_cells` counters count explicitly suppressed source cells, not every missing canonical cell. Do not estimate suppressed values by subtraction.

[CLEANING.md](CLEANING.md) records the detailed rules, available individual/team artifact comparisons, and full-team agreement at the October 18, 2026, 2:45 p.m. PDT meeting. [The audit](outputs/cleaning_report.json) records exact source URLs, hashes, exclusions, and snapshot differences.

## Metrics and backend contracts

County comparisons use selected month/language; demographic context uses selected month/county. Demographic families are separate summaries of the same county eligible population, not individual language-by-age-by-race cross-tabulations. Backend shares are fractions.

| Question / output | Source and calculation | Backend |
| --- | --- | --- |
| What can be selected? | Distinct months chronological; language slugs alphabetical from `language__*` | `get_available_months`, `get_available_languages` |
| Where are the largest language populations? | Selected language column; descending count, alphabetical ties, competition rank (1, 1, 3); missing last/unranked | `get_map_data`, `get_county_ranking` |
| What is the county denominator? | `county_total_eligibles` sums all eight age/sex cells only when all are observed; otherwise missing and completeness False | `get_county_metrics`, `get_county_summary` |
| Where is the language concentrated? | Observed language count / complete positive county total; otherwise unavailable | `get_language_share` |
| How much is observed statewide? | Subtotal over observed counties with coverage counts. Full count needs all 58 observed; full share also needs all 58 complete totals and a positive denominator. Use ratio of totals, never average county shares | `get_month_summary` |
| What is the county age/sex context? | Eight direct cells; optional age/sex aggregates require every component in their group | `get_age_sex_summary` |
| What is the county race context? | Six race totals across four ages; a missing component makes its group unavailable | `get_race_ethnicity_summary` |

Demographic `share_of_county` uses the same complete positive denominator. [ANALYSIS.md](ANALYSIS.md) defines returned columns, grouping options, availability reasons, and examples. All functions return reusable lists/DataFrames without mutating input; implementations remain in Python.

## Architecture and technical choices

Use Python 3.11+, pandas, and NumPy for the backend; Streamlit and Plotly for Phase 3. The small canonical CSV fits an in-memory DataFrame. No database, credentials, remote queries, or live DHCS calls are needed at dashboard runtime.

| Component | Job and boundary |
| --- | --- |
| `cleaning.py` | Three raw CSVs → canonical CSV and audit; separate offline rebuild command |
| `data.py` | Path/DataFrame → typed, validated county-month data |
| `analysis.py` | Validated data + explicit filters → reusable outputs; no UI state/drawing |
| Phase 3 chart builders | Backend outputs + geometry → figures; no file reads or duplicated analysis |
| Phase 3 app | Controls and selection events → backend calls, shared county state, rendering |
| Phase 3 geometry adapter | Local boundaries → GeoJSON with unique matching county names |

Prepare geometry once from [Census 2025 county boundaries at 1:5,000,000](https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_county_5m.zip): filter `STATEFP == '06'`, transform to WGS84/EPSG:4326, and save `data/california_counties.geojson`. Preserve `NAME` as `properties.county`; require 58 matching names and no unmatched backend keys. Geometry is a display asset; no live boundary/tile download is required during use.

Cache validated data and geometry using [Streamlit data caching](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data), invalidating when files change. Reuse prepared data and compute views from the selected month's 58 rows. Keep selection state in the app and use supported [chart selection events](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart). On load/validation failure, show an actionable error and stop dependent rendering. Target warm filter updates within two seconds locally; measure during Phase 3.

## Build order and acceptance

1. Run the README tests and cold-start example; inspect canonical coverage and cleaning audit.
2. Validate local geometry, then build selectors and shared state with cached loading.
3. Render overview/map/comparison from backend outputs; add county detail and synchronized selections.
4. Verify unavailable/zero cases, readable labels, responsive layout, and browser interactions; document the launch command.

Phase 2 acceptance: unique keys; all 58 counties in every checked month; source pivots and one-to-one joins validated; complete totals and safe shares agree with source cells. Tests cover suppression, absence, true zero, incomplete/zero denominators, tied ranks, partial demographic groups, coverage, and nonmutation. Exercise every language in the first/latest month and demographics for every county in those months. Canonical data, code, audit, and spec must agree on `main`.

Phase 3 acceptance: specified startup and all views render; every filter updates dependent views; map/table/selector keep county detail synchronized without stale overrides; all 58 geometry joins match; hover values and chart metrics match the backend. Check an all-unavailable language and an incomplete small-county total. Confirm demographic labels refer to the whole county and missing values are never inferred or displayed as zero.

A fresh agent must be able to begin Phase 3 without important product/data/metric/interaction guesses. Record review questions and fixes in [PHASE_2_STATUS.md](PHASE_2_STATUS.md); distinguish readiness review from an actual dashboard/browser test.
