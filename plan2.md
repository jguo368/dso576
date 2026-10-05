# DHCS Primary-Language Data Cleaning Plan

## Purpose and non-negotiable safeguards

This plan prepares the DHCS certified-eligibles-by-primary-language file for a
county map with month and language selectors. The unit remains a count of
certified eligibles; no units are converted. Every one of the 251,535 source
rows is retained in the audit-preserving output. The map-only derivative may
exclude the 200 statewide summaries and four invalid-county rows, but those
rows remain available in the full cleaned table with a reason flag.

Every run writes `suspicious_values.csv` before resolution and
`transformation_report.csv` after each major stage. No category is combined,
renamed, or inferred except for removal of surrounding whitespace documented
below.

## Inspected source profile

The input has nine text columns and covers 2010-01 through 2026-08. It has 60
county labels (58 California counties, `STATEWIDE`, and `Invalid County Code`),
34 language labels, 157,211 reported count strings, and 94,324 blank or
whitespace-only count strings after whitespace inspection. (94,321 are exactly
blank in the raw file; three code-`2` cells contain spaces.) There are no duplicate source rows, repeated
month-county-language keys, invalid month strings, invalid count strings,
negative counts, fractional counts, or zero counts.

## Column-level rules

| Column | Cleaning rule | Retention and interpretation |
| --- | --- | --- |
| `Month of Eligibility` | Preserve `YYYY-MM`; add a parsed month only for validation/filtering. | Do not invent a reporting day. |
| `County` | Strip surrounding whitespace only; map the 58 real counties to five-digit FIPS codes. | Preserve `STATEWIDE` and `Invalid County Code`; flag them as not map eligible. |
| `Language` | Strip surrounding whitespace only. The 2,573 raw ` Unknown` labels become `Unknown`. | Preserve `Unknown`, `Missing/Unknown`, and every other language category separately. |
| `Total Eligibles` | Strip whitespace, remove display commas, parse nullable nonnegative integer counts. | Blank/suppressed values stay unknown, never zero. The count unit is unchanged. |
| `Annotation Code` | Preserve text values; codes `1` and `2` flag suppression. | Retain source code rather than expanding its meaning. |
| `Annotation Description` | Preserve after trimming. | Retain source descriptions as the explanation for suppression or statewide totals. |
| `Status` | Preserve `F` and `P` without expansion. | No official code legend has been verified. |
| `Date of Data` | Preserve normalized text and add a nullable ISO date. Treat blank and `.` as missing. | Do not impute missing dates. |
| `Difference` | Preserve as a nullable field. | It is blank in every source row and is excluded from metrics. |

## Suspicious values to flag before resolution

- 94,324 blank or whitespace count cells, including 93,681 code-`1` and 643
  code-`2` suppression-coded records.
- Three code-`2` records with whitespace-only counts; they look nonblank before
  trimming but become blank after normalization and remain suppressed.
- 2,573 leading-space language values.
- 3,736 `.` date markers and 138,139 blank date values.
- 200 statewide summary records and four invalid-county records.
- A fully blank `Difference` field.
- Month/language selectors with fewer than 58 published county rows. Missing
  source rows are neither zero nor suppressed.

## Transformation reports and acceptance checks

The cleaner reports raw profiling, text normalization, type conversion,
suppression validation, geography/FIPS matching, and dashboard-output creation.
Each report includes input/output rows, affected rows, and the reason for the
action. It must assert identical full-table input/output row counts, zero
repeated composite keys, valid FIPS for every map-eligible row, and no numeric
value for suppressed records. It also writes reported-count ranges and
percentiles without substituting suppressed values for zero. The dashboard must use the coverage file to show
reported, suppressed, and absent-source states separately.
