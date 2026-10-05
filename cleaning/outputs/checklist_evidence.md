# Checklist Evidence: Medi-Cal Cleaning

Business vision: **A Medi-Cal access strategy manager at DHCS must decide which counties and language populations should be prioritized for additional language-access capacity.**

| # | Status | Evidence |
|---|---|---|
| 1 | Done | County-month-language eligible populations are a planning signal; provider capacity is unresolved because no provider dataset is present. |
| 2 | Done | Grain and candidate keys are documented in `plan.md` and `validation_summary.csv`. |
| 3 | Done | Inputs are read-only; `source_manifest.csv` records hashes. |
| 4 | Done | Raw fields remain; parsed date/count/comparison fields are added. Conversion failures are reported. |
| 5 | Done | Only outer-whitespace comparison fields are added; language categories are not combined. |
| 6 | Done | Exact duplicates and repeated candidate keys are reported separately. |
| 7 | Done | `missing_value_report.csv` reports count/percent before and after; blanks remain missing. |
| 8 | Done | Negative counts, failed parses, invalid county codes, placeholders, and P records are flagged. |
| 9 | Done | `merge_validation.csv` verifies one-to-one county-month key coverage; long tables are not directly merged. |
| 10 | Done | All major transformations retain rows: 631,980 before and 631,980 after. |
| 11 | Done | No missing count becomes zero; rankings/maps must filter `is_invalid_county_code == False`. |
| 12 | Done | Five difficult record checks are in `record_checks.csv`; all passed: True. |
| 13 | Done | Run `python cleaning/clean_medi_cal.py`; README gives the repeat-run hash check. |
| 14 | Unresolved | Provider capacity, F/P definitions, suppression policy, and derived-file provenance need documentation. |

## Codex Suggestion Verification

Suggestion: **Retain and flag Invalid County Code records instead of deleting them.**

The derived source has 3 affected records. They remain in the cleaned file with `is_invalid_county_code=True`, so row count is unchanged. County rankings/maps should filter that flag because `Invalid County Code` is not a California county; retaining it makes the unassigned geography and its counts auditable. The individual record check verifies this behavior against an original affected record.
