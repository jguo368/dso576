# Module 6 Data Cleaning Plan

## Goal

Prepare the California Department of Health Care Services (DHCS) Medi-Cal
Certified Eligibles by Primary Language data for reproducible analysis and a
future dashboard. The intended business question is: **Which California
counties and primary-language groups have the largest numbers of Medi-Cal
certified eligibles, and therefore may warrant closer review for
language-access planning?**

The main metric is `total_eligibles`, compared across county, primary language,
and month. Results will remain descriptive: eligibility counts do not measure
health-care access, language-service capacity, or causal effects.

## Source and unit of observation

- Input file: `by-primary-language-certified-eligibles.csv`
- Publisher: California Department of Health Care Services (DHCS)
- Dataset: Medi-Cal Certified Eligibles Data by Month with Demographics,
  primary-language resource
- Local download date used for this assignment: October 2, 2026
- Source period in the file: January 2010 through August 2026
- One row: one unique month × county/geography label × primary-language label
  observation.
- Expected key: `Month of Eligibility`, `County`, `Language`

The source CSV will be read but never overwritten. Cleaning outputs will be
written to `output/` and submission evidence to `evidence/`.

## Non-negotiable rules

1. Do not delete any source row. If a record is unusual, retain and flag it.
2. Do not impute disclosure-suppressed counts. Suppression is not the same as
   zero.
3. Do not change count units or combine language categories.
4. Preserve both `Unknown` and `Missing/Unknown` as distinct source categories.
5. Report row counts, missing counts, duplicates, important totals, and failed
   conversions before and after cleaning.
6. Keep statewide totals separate from county-level records in analysis to
   avoid double counting.
7. Treat preliminary (`P`) and final (`F`) records as different publication
   statuses; do not silently mix them when selecting a reporting month.

## Column-by-column rules

| Source column | Output column | Proposed rule | Validation |
|---|---|---|---|
| `Month of Eligibility` | `month_of_eligibility` | Parse exact `YYYY-MM` values as month-start dates. Retain the source row and flag any failed parse. | Count parse failures; report min/max. |
| `County` | `county` | Trim surrounding whitespace only. Do not remove `STATEWIDE` or `Invalid County Code`; add flags for them. | Compare categories before/after; expect 60 categories. |
| `Language` | `language` | Trim surrounding whitespace. This changes legacy `" Unknown"` to `"Unknown"` but does not merge it with `Missing/Unknown`. | Count changed values (expected 2,573); compare categories before/after. |
| `Total Eligibles` | `total_eligibles` | Trim whitespace, remove thousands separators if present, and convert to nullable integer. Whitespace-only and suppressed values remain missing. Never fill them with zero. | Count failures among nonblank, nonsuppressed source values; check nonnegative integers and min/max. |
| `Annotation Code` | `annotation_code` | Preserve as a nullable string because it is a categorical disclosure code, not a quantity. | Cross-check code/description/count missingness. |
| `Annotation Description` | `annotation_description` | Trim whitespace and preserve the publisher's categories. | List categories and frequencies. |
| `Status` | `status` | Preserve `F` and `P`; add readable `status_label` (`Final`, `Preliminary`). | Reject/flag values outside `F`, `P`. |
| `Date of Data` | `date_of_data` | Trim whitespace; treat publisher marker `.` as missing; parse `DDMONYYYY`. | Count parse failures among meaningful values; report min/max. |
| `Difference` | — | Drop from the analytic output because all 251,535 source values are missing. Record this column-level removal; no row is removed. | Confirm 100% missing before removal. |

## Added audit fields

- `is_suppressed`: annotation code is `1` or `2`.
- `is_statewide`: county or language is `STATEWIDE`.
- `has_valid_county`: false only for `Invalid County Code`.
- `is_preliminary`: status is `P`.
- `source_row_number`: original CSV row number, starting at 2 to account for
  the header, so every cleaned record can be traced to the source.

## Suspicious values to flag before deciding

- Four records use `Invalid County Code`: retain and flag because no reliable
  county can be inferred.
- 200 statewide rows: retain and flag; exclude from county sums to prevent
  double counting.
- Suppressed counts (annotation codes 1 and 2): retain as missing, never zero.
- Three whitespace-only count strings: treat as missing; their complementary
  suppression annotation explains them.
- `Date of Data` values equal to `.`: treat as missing markers, not failed
  dates.
- High counts: inspect the largest records. Statewide totals are expected to
  be much larger than county-language cells and should not be called errors
  solely because they are outliers.

## Duplicate decision

Count exact duplicates and duplicate expected keys separately. If found, do not
automatically discard them: write them to evidence, inspect publication status
and annotations, and document a rule. Initial inspection found zero of both, so
the planned action is to retain all rows.

## Validation and evidence

The script and notebook will produce:

- starting and final row/column counts;
- missing counts before and after;
- exact duplicate and repeated-key counts;
- text-category comparisons;
- date and numeric conversion failures;
- numeric min, max, quantiles, and totals, always with nonmissing record counts;
- annotation consistency checks;
- five predeclared record checks covering a regular record, small-cell
  suppression, complementary suppression, whitespace normalization, and an
  invalid county;
- a deterministic sample of no more than 50 cleaned rows emphasizing difficult
  cases; and
- an evidence JSON/CSV bundle used to write the submission report.

## Implementation sequence

1. Load the original CSV as strings and capture a pre-cleaning profile.
2. Flag suspicious source values before modifying any fields.
3. Apply the documented conversions and flags in a pure `clean_data` function.
4. Validate invariants and stop with an error if a required check fails.
5. Write the complete cleaned CSV, validation evidence, and difficult-case
   sample.
6. Restart and execute the notebook from the original input.
7. Generate the individual PDF report from the verified evidence.

## Human decisions recorded for this submission

- Suppressed values remain missing because DHCS intentionally withholds them;
  zero-imputation would bias totals downward and falsely claim precision.
- `Unknown` and `Missing/Unknown` remain separate because the source may encode
  different collection histories, and no data dictionary evidence justifies a
  merge.
- The four invalid-county records remain available but are excluded from valid
  county comparisons using `has_valid_county`.
- The 200 statewide rows remain available but must not be added to county rows.
- No merge is part of this assignment, so merge verification is explicitly
  marked not applicable rather than invented.
