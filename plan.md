# Project Data Cleaning Plan

## Selected project vision and scope

A Medi-Cal access strategy manager at DHCS must decide which counties and language populations should be prioritized for additional language-access capacity. In the interface, the manager selects a primary language and eligibility month, then interacts with a California county map to review relevant figures for each county.

**Proposed analytical question:** For a selected eligibility month and primary language, how many certified eligibles are reported in each county, and which county-language combinations may warrant further review for language-access capacity?

The primary map measure is the reported certified-eligible count for the selected county, month, and language. Show the corresponding source annotation/status where relevant. Suppressed values must be represented as suppressed or unavailable, never as zero. Shares or rates are secondary measures only if a complete, documented county-month denominator is verified.

The DHCS file measures eligible-population language counts; it does not, by itself, measure access barriers or a shortage in provider language capacity. Therefore, map results can surface potential areas for review, but cannot prove that a county lacks language services or that additional capacity will improve access. Before presenting a need-versus-capacity comparison, verify whether the core provider profile's `Threshold_Languages` and `Other_Languages` fields have usable definitions, completeness, and categories compatible with DHCS language labels.

## Source and observed structure

- Publisher: California Department of Health Care Services (DHCS).
- Resource: By Primary Language, Certified Eligibles.
- Resource URL: <https://data.chhs.ca.gov/dataset/8c897320-ba87-4574-bc37-bae974191c35/resource/b698c8d7-aacd-43c6-a7dd-737ff5692284/download/t5_eligibility_by_language_201001_202609.csv>
- Keep a downloaded original unchanged. The filename suffix says `202609`, but full-file inspection and publisher metadata confirm observed coverage ends at 2026-08. Record download date, URL, and SHA-256 in the README.
- Observed row grain: one county, eligibility month, and language category.
- Observed columns: `Month of Eligibility`, `County`, `Language`, `Total Eligibles`, `Annotation Code`, `Annotation Description`, `Status`, `Date of Data`, and `Difference`.
- The source contains comma-formatted counts (for example, `2,724`) and suppressed cells with a blank count plus a suppression annotation. Do not treat those blanks as zero.
- Full-file inspection of the unchanged download found 251,535 data records, covering 2010-01 through 2026-08. Publisher metadata confirms January 2010-August 2026 coverage and warns that eligibility data is preliminary and subject to change for one year.
- The file contains 60 county labels: 58 California counties, `STATEWIDE`, and `Invalid County Code`. Retain every source record in the cleaned table; map only the 58 counties, keep statewide rows separate, and flag invalid-county rows as unmappable.
- There are 34 distinct language labels. The raw label ` Unknown` has leading whitespace; trim surrounding whitespace but preserve the resulting `Unknown` separately from `Missing/Unknown`.
- There are 157,211 reported counts and 94,324 blank counts; every blank has a suppression annotation (93,681 code `1`, small numbers; 643 code `2`, complementary cell). The full scan found no unexplained blank counts, invalid numeric counts, or zero counts.
- No exact duplicate rows or repeated `(Month of Eligibility, County, Language)` keys were found. `Status` is `F` through 2025-08 and `P` from 2025-09 through 2026-08. Preserve these source codes; no official code legend was found. Show the publisher's preliminary-data caveat for recent periods.
- `Date of Data` has 138,139 empty cells and 3,736 `.` markers; valid dates range from 2020-10-19 through 2026-08-11. `Difference` is empty in all 251,535 records. The cleaner produces separate raw-blank and cleaned-missing counts for each field.
- The reproducible cleaner retained all 251,535 rows, performed no row drops or fills, and passed five record checks. Its 49-row sample includes suppressed cells, formatted counts, trimmed text, special geography labels, and both status codes.

## Cleaning Rules and Evidence

Rules were recorded before implementation and tested against the full source. The table records the applied rule and the evidence supporting it.

| Field or issue | Proposed rule | Check and decision still needed |
| --- | --- | --- |
| CSV/header encoding | Read as UTF-8 with BOM handling so the first column name is `Month of Eligibility`. Keep the nine parsed columns and verify row widths. | Confirm the full file parses without malformed rows or extra header lines. |
| `Month of Eligibility` | Parse as a monthly period or consistently formatted year-month value. Do not invent a day of month. | Count parse failures and confirm minimum/maximum month. |
| `County` | Strip surrounding whitespace only; preserve the published county label. Do not fuzzy-match or silently rename counties. | List distinct values; investigate blanks or unexpected labels and define any cross-source county mapping separately. |
| `Language` | Strip surrounding whitespace only; preserve the published category labels and distinctions. | Full scan found 34 labels and leading whitespace in ` Unknown`; preserve `Unknown` separately from `Missing/Unknown`. Do not combine categories. |
| `Total Eligibles` | Strip surrounding whitespace, remove display commas, and parse reported values as nullable, nonnegative whole-number counts. | Full scan found 157,211 reported counts and 94,324 blanks, all suppression-annotated (codes `1` and `2`); do not impute zero. Recheck conversions in the cleaning script. |
| `Annotation Code`, `Annotation Description` | Preserve the published fields. Interpret annotations before treating blanks in the count as ordinary missingness. | Count suppression annotations and check that suppressed rows have no reported count. Investigate any inconsistent combinations. |
| `Status` | Preserve source codes and retain every status. | Full scan found `F` through 2025-08 and `P` from 2025-09 onward. No official code legend was found; do not expand or filter the codes. Show the publisher's preliminary-data caveat for recent periods. |
| `Date of Data` | Preserve the source value and parse a separate date after trimming whitespace; treat empty strings and `.` as missing. | Full scan found 138,139 empty values, 3,736 `.` markers, and valid dates from 2020-10-19 through 2026-08-11. Count parse failures in the cleaning script. |
| `Difference` | Preserve the source field and do not use it in metrics. | Full scan found it empty in all 251,535 records. |
| Special county labels | Retain all records and add a map-eligibility flag. | `STATEWIDE` (200 records) and `Invalid County Code` (4 records) do not identify county polygons; exclude only from county-map use and report separately. Validate other county labels against the selected boundary file. |
| Duplicates | Count exact duplicate rows and repeated `(Month of Eligibility, County, Language)` keys separately. Do not deduplicate until repeated keys are understood. | Check whether repeated keys represent revisions, statuses, or actual duplicate records; report the chosen action and row-count effect. |
| Missing values | Report missingness by field, separately identifying suppression-coded counts from unannotated blanks. | Explain every fill, retention, or exclusion. Default: do not fill suppressed counts or drop rows solely because the count is suppressed. |

## Derived measures and limits

- Start with reported counts by month, county, and language. Track the number of reported and suppressed cells in every summary.
- Use the selected eligibility month and language to filter the map. County selection should expose the county name, reported count (or suppression state), and relevant source status/annotation. Verify the county-boundary geometry source and county-name/code matching before building the map; the eligibility CSV itself supplies labels, not map shapes.
- Do not calculate language shares using a denominator formed by summing language counts until it is established that suppressed cells cannot make that sum incomplete. Prefer a published county-month total or a documented suppression-aware method if available.
- Do not combine language categories or label a category “non-English” without a documented, reviewed mapping.
- Do not join the provider profile until county names, reporting periods, and the provider file's language fields (if any) have been checked for compatible meanings. If provider-language fields are absent or unusable, keep the result focused on population-language counts and state that capacity matching is unresolved.
- Provider counts are not appointment availability, and certified eligibles are not necessarily actual service users. Avoid claims that the data proves unmet need or intervention impact.

## Verification and deliverables

For the full source and cleaned output, record:

- Starting and final row counts, with every row addition/removal explained.
- Exact duplicate rows and repeated key counts before any resolution.
- Missing counts by field before and after, including suppression counts.
- Distinct county, language, and status values; date range; count minimum, maximum, and distribution for reported counts.
- Any change in important totals, with a clear warning if suppression prevents exact reconciliation.
- Five record checks with the original values, expected outcome and reason written before checking, actual cleaned values, and match result. Include difficult cases such as a suppressed cell and a comma-formatted count.
- A cleaned sample of up to 50 rows, including difficult cases, with the selection method stated. Label any synthetic sample clearly if the real data cannot be shared.
- A restart-and-run check from the unchanged original source using the listed dependencies; confirm the output matches the submitted file.

Keep raw data unchanged. Place scripts, notebook, a permitted sample, dependency file, and run instructions in the project branch. The README and PDF must include the exact branch name, branch URL, and submitted commit ID; fill these in after pushing the individual branch.

## Assignment checklist evidence map

Complete each status and cite the result or file section in the final PDF. Do not mark an item Done based only on the sample inspected so far.

| Item | Evidence to produce |
| --- | --- |
| 1. Vision and question | State the selected decision, narrowed question, and primary metric. |
| 2. One row | State county-month-language as the row grain and test the proposed composite key. |
| 3. Preserve source | Give publisher, URL, download date/version, raw-file location, and load instructions. |
| 4. Columns and types | Report parsed fields, conversions, and failed-conversion counts. |
| 5. Standardize text | Show before/after examples and state which category distinctions were preserved. |
| 6. Duplicates | Report exact duplicate rows and repeated composite keys separately; explain any action. |
| 7. Missing data | Give before/after counts by affected field and distinguish suppression from other blanks. |
| 8. Suspicious values | Check invalid months/dates, unexpected categories/statuses, and invalid counts; explain corrections or flags. |
| 9. Merges | If no tables are merged, mark Not applicable and explain why. If merged, report keys, expected relationship, unmatched keys, and row counts. |
| 10. Reconcile changes | Report starting/final rows and explain changes to counts or totals, including suppression limits. |
| 11. Calculations | Define eligible records and denominator for every metric; explain suppression and missing-group-key handling. |
| 12. Five records | Show original, expected result/reason, actual result, and match for five difficult or representative records. |
| 13. Reproducibility | Document a clean restart/run command or notebook sequence and confirm outputs match. |
| 14. Limitations | List unresolved source, suppression, geographic, population, and provider-capacity limitations and their effect on conclusions. |

## Remaining checks before the map

1. Select a documented California county-boundary source and test its identifiers against the 58 county labels in this file.
2. If a provider-capacity comparison remains in scope, verify the definitions and completeness of the core profile's language fields and whether their categories can be compared with DHCS primary-language categories.
3. For any language-share measure, identify a complete county-month denominator and show how suppressed cells affect it. The map's current primary measure remains the reported count.
4. Fill in the exact branch name, branch URL, and submitted commit ID after the individual branch is pushed.