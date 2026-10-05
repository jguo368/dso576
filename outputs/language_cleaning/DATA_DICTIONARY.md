# Dashboard data contract

Run `UV_CACHE_DIR=/private/tmp/dso576-uv-cache uv run python clean_language_data.py`
from the project directory to regenerate every CSV in this directory.

## Use these files

- `county_language_month_map.csv` is the map fact table. Filter it to exactly
  one `month` and one `language`; it then has one row per California county.
  Join county boundary geometry with `county_fips`, retaining its leading zero.
- `california_counties.csv` is the 58-row county lookup for validating that
  geography join. It does not provide boundary geometry.
- `month_language_coverage.csv` reports how many county rows the source
  actually supplied for each selectable month/language combination. Use it to
  flag selectors whose map is incomplete; a missing county row must not be
  displayed as zero or as a suppressed count.
- `suspicious_values.csv` documents source anomalies before their cleaning
  decisions are applied; `transformation_report.csv` reports the row and value
  effects after each major pipeline stage.
- `eligible_count_distribution.csv` gives the distribution of reported counts
  only. Suppressed values are excluded rather than treated as zero.
- `cleaned_language_eligibles.csv` is the complete audit-preserving output. It
  retains statewide and invalid-county source rows, which are intentionally
  absent from the map fact table.

## Map fact fields

| Field | Meaning and dashboard use |
| --- | --- |
| `month` | Source eligibility month in `YYYY-MM`; use as the month/year selector. |
| `county`, `county_fips` | Published county label and five-digit California ANSI/FIPS join key. |
| `language` | Published primary-language category; use as the language selector without combining categories. |
| `eligible_count` | Nullable whole-number count. Display only when `count_availability` is `reported`. |
| `count_availability` | `reported` or `suppressed`. A suppressed value is unknown, not zero. |
| `annotation_code`, `annotation_description` | Source suppression context for a suppressed cell. |
| `status`, `data_date`, `difference` | Preserved source fields. Status codes are not expanded because no official legend was verified. |
| `is_suppressed` | Boolean equivalent of the count-availability flag, retained for analysis. |

`month_language_coverage.csv` distinguishes three states: a reported county
row, a suppression-coded county row, and `counties_without_source_row` (no
published record). Only `complete_58_county_coverage = true` selectors can
fill every county polygon from the source fact table.

## Guardrails

Do not sum reported county cells into a population total or calculate language
shares from them: suppressed cells make such sums incomplete. The counts
describe certified eligibles by primary language, not provider language
capacity, service use, or appointment availability. They can identify locations
for capacity review, not prove unmet need.
