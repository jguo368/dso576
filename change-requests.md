# Change requests

## Claims

| Auditor | Feature audited | Number audited | Evidence contributed |
|---|---|---|---|
| Fangning Xu | Suppression-preserving language-count cleaning | County-month key coverage (11,603 unique keys) | `cleaning/audit_module9_check.py` independently checks the source record and key sets. |

## Findings

### CR-009-01 - Suppressed language counts remain unavailable

- **Status:** Verified; no code change requested.
- **Finding:** The source record `2026-08 | Alameda | Hebrew` has a blank `Total Eligibles` value and the annotation `Cell suppressed for small numbers`. The cleaning workflow parses that blank as a missing value rather than zero.
- **Evidence:** `cleaning/audit_module9_check.py` verifies the raw record and annotation. `cleaning/outputs/record_checks.csv` records the cleaned result as `parsed=<NA>`.
- **Why it matters:** Treating a suppressed value as zero would understate a language population and could distort county prioritization.
- **Remaining uncertainty:** This check establishes the handling of the selected record; it does not independently test every suppression annotation or the downstream dashboard display.

### CR-009-02 - County-month key coverage matches the language source

- **Status:** Verified; no code change requested.
- **Finding:** The non-statewide language source and the derived county-month table each contain 11,603 unique `(month, county)` keys, with zero keys found only on either side.
- **Evidence:** `python cleaning/audit_module9_check.py` performs a separate standard-library CSV set comparison. It agrees with `cleaning/outputs/merge_validation.csv`.
- **Why it matters:** Matching coverage supports use of the derived table at the county-month grain and reduces the risk of silently dropping or adding county-month records.
- **Remaining uncertainty:** Key coverage does not prove that every derived measure is numerically correct or that categories were aggregated according to the intended policy.
