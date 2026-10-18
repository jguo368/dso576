# Phase 2 reusable analysis

`medi_cal_analysis` implements the backend requirements in
[`BUILD_SPEC.md`](dso576/project/BUILD_SPEC.md), including its metric and architecture contracts.
It has no dashboard framework dependency. Phase 3 can consume its DataFrames
directly for the selectors, map, rankings, overview KPIs, and county detail.

Run from the repository root (`project/`):

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The existing environment can run the checks with
`.venv/bin/python -m unittest discover -s tests -v`.

## Usage

```python
from medi_cal_analysis import (
    load_data,
    get_available_months,
    get_available_languages,
    get_county_ranking,
    get_map_data,
    get_county_summary,
    get_language_share,
    get_month_summary,
    get_age_sex_summary,
    get_race_ethnicity_summary,
)

data = load_data()  # Or load_data(path_to_canonical_csv).
quality_report = data.attrs["preparation_report"]
months = get_available_months(data)
languages = get_available_languages(data)
month, language, county = months[-1], "mandarin", "Los Angeles"

map_data = get_map_data(data, month, language)
ranking = get_county_ranking(data, month, language, limit=10)
overview = get_month_summary(data, month, language)
detail = get_county_summary(data, month, language, county)
shares = get_language_share(data, month, language)
age_sex = get_age_sex_summary(data, month, county)
age_totals = get_age_sex_summary(data, month, county, group_by="age")
sex_totals = get_age_sex_summary(data, month, county, group_by="sex")
race_totals = get_race_ethnicity_summary(data, month, county)
race_by_age = get_race_ethnicity_summary(data, month, county, group_by="race_age")
```

Load/prepare once, then reuse the prepared DataFrame for different selections.
The default CSV path is resolved relative to the package, not the working
directory. Nothing writes to the original CSV or mutates the caller's DataFrame.
Functions return values rather than printing or drawing the interface.

## Output contract

| Function | Return value / dashboard use |
| --- | --- |
| `load_data(path=...)` / `prepare_data(raw)` | Validated county-month DataFrame; preparation report in `.attrs`. |
| `get_available_months(data)` | Sorted list of `YYYY-MM` strings. |
| `get_available_languages(data)` | Sorted language slugs from `language__` columns. |
| `get_county_metrics(data, month, language)` | Shared per-county metric table used by map, ranking, and detail. |
| `get_map_data(data, month, language)` | County names plus metrics/availability/suppression fields; join geometry by `county` in Phase 3. |
| `get_county_ranking(data, month, language, limit=None)` | Metrics sorted by descending count, alphabetical ties, nullable competition `rank`. |
| `get_county_summary(data, month, language, county)` | One-row metrics DataFrame for the selected county. |
| `get_language_share(data, month, language)` | County language share, numerator, denominator, completeness, and availability reason. |
| `get_month_summary(data, month, language)` | One-row overview with observed subtotal, coverage counts, and complete totals/share where valid. |
| `get_age_sex_summary(data, month, county, group_by="age_sex")` | Overall county counts by age/sex, or grouped by `"age"` or `"sex"`. |
| `get_race_ethnicity_summary(data, month, county, group_by="race")` | Overall race totals across ages; also supports `"race_age"` cells or `"age"` totals. |

Month inputs accept `YYYY-MM` or an ISO `YYYY-MM-DD` date. Language inputs accept
slugs or full column names (`mandarin` / `language__mandarin`). County inputs are
case/whitespace normalized. Unknown selections and unavailable county-months
raise `ValueError`; missing counts within a valid selection remain missing.

The county metrics table includes `month_of_eligibility`, `county`, `language`,
`selected_language_count`, `county_total_eligibles`, `county_total_is_complete`,
`language_share`, availability flags, `language_share_unavailable_reason`, and
the three suppression counters. Shares are fractions: `0.25` means 25%.
Suppression counters are source metadata, not estimates of suppressed counts.

Demographic tables contain grouping columns (`age_group`, `sex`, or
`race_ethnicity`), `eligible_count`, `is_complete`, `missing_cells`,
`required_cells`, and `share_of_county`, plus county/month and denominator fields.
Category identifiers retain the canonical CSV slugs. `missing_cells` counts
unavailable source cells; it does not claim every missing value was suppressed.

## Data rules and limits

- Preparation excludes invalid/missing months and all non-California county
  identifiers, including statewide rows and `Invalid County Code`. Exclusion
  counts are returned in the preparation report. There are no other row exclusions.
- Keys and column names are normalized before validation. Duplicate county-month
  keys raise an error instead of being silently dropped or aggregated.
- Counts must be numeric, finite, nonnegative whole values or missing. Output
  counts use nullable `Float64`, suppression counters `Int64`, keys string, and
  the completeness flag Boolean. Strings `True`/`False` are explicitly parsed.
- All 8 age/sex and 24 race/age source columns are required. Unexpected
  demographic category columns raise for review. Language slugs are discovered
  dynamically so the selector includes every supplied language category.
- Publication metadata columns are required: `status` is normalized to F/P,
  and `date_of_data` to ISO date strings or missing. ISO and legacy DHCS
  DDMMMYYYY dates are accepted as input; malformed dates and statuses raise.
- Complete county totals are checked against all eight age/sex source cells.
  An incomplete county total is made unavailable even if a partial number was
  supplied. The backend does not reconstruct suppressed source values.
- Language share requires an observed numerator and a complete, positive county
  total. Missing counts and incomplete/zero denominators produce missing shares.
  A true observed zero produces zero share when the denominator is valid.
- Rankings keep missing counts at the end with missing rank. Ties share a rank
  (`1, 1, 3`); `limit` applies after sorting. Missing is never ranked as zero.
- Demographic aggregates require every cell in that group. For example, if one
  age cell for a race is unavailable, its race total is unavailable. Other race
  totals remain usable. Shares also require a valid county denominator.
- Overview `observed_language_count` is only a subtotal over available counties;
  it is missing if none are observed. Full totals and overview share require
  all 58 counties and complete required values. The share is the ratio of totals,
  not the average of county shares. Coverage fields distinguish missing county
  rows from missing language values in present rows.
- Demographic functions have no language parameter: they describe all Medi-Cal
  eligibles in the county, not the selected-language population. None of these
  measures establishes interpreter/provider capacity or a service shortage.

The backend consumes the canonical wide CSV produced by
`medi_cal_analysis.cleaning`. [CLEANING.md](CLEANING.md) describes the raw-source
pipeline, available individual/team artifact comparison, and source audit.
Runtime preparation validates a copy and never writes to the input file.
The current canonical file excludes invalid geography; the loader also enforces
that rule for custom inputs. Earlier source snapshots remain in Git history.

## Verification

The tests cover key normalization/uniqueness, documented exclusions, input
validation, suppression and zero handling, incomplete denominators, deterministic
rankings, safe demographic aggregation, coverage-aware overview metrics, and
nonmutation. An integration test loads the supplied CSV and exercises every
language for its first/latest months and demographic summaries for all counties
in those months.
