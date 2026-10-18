# Canonical Medi-Cal data

The canonical runtime dataset is `dso576/project/medi_cal_merged_county_month.csv`.
It is tracked in Git despite the general ignore rule for CSV downloads.
The current build uses all three official DHCS resources from the same release:
January 2010–September 2026, 58 California counties, 11,658 rows, 74 columns.
Exact source URLs, byte sizes, SHA-256 hashes, and counts are in
[the cleaning audit](outputs/cleaning_report.json).

## Team cleaning agreement

**Meeting:** October 18, 2026, at 2:45 p.m. PDT (America/Los_Angeles).
**Agreement:** All team members agreed to the shared cleaning rules documented
in this file, as confirmed by a team member in this project session.

The agreed approach covers the county-month unit of analysis, duplicate handling,
missing and suppressed counts, data types, standardized labels, one-to-one joins,
exclusions, and derived county totals and language shares. These rules govern the
canonical January 2010–September 2026 dataset and the analysis backend.

The artifact comparisons supporting these decisions are documented below.

## Rebuild

From the repository root, after installing `requirements.txt`:

```bash
# Download the three pinned official source files and rebuild the canonical CSV.
.venv/bin/python -m medi_cal_analysis.cleaning --download

# Rebuild from local raw files without network access.
.venv/bin/python -m medi_cal_analysis.cleaning

# Write a candidate and compare with the current canonical file before replacing it.
.venv/bin/python -m medi_cal_analysis.cleaning --output outputs/candidate.csv \
  --report outputs/candidate_audit.json \
  --compare dso576/project/medi_cal_merged_county_month.csv
```

Raw files live at `data/raw/language.csv`, `age_sex.csv`, and `race_age.csv` and
are intentionally untracked. Do not confuse the older August snapshot
`t5_eligibility_by_language_201001_202609.csv` with the September-release inputs.
The online publisher can revise or replace downloads; compare source hashes
against the committed audit before claiming a byte-identical reproduction.
No network connection is needed to use the committed canonical data/backend.

The build validates the full result before atomically replacing the canonical
CSV. Unknown categories, malformed counts, duplicate source cells, inconsistent
metadata, and mismatched county-month source coverage stop the build for review.

## Cleaning decisions and evidence

| Issue | Shared implementation rule | Actual inspection |
| --- | --- | --- |
| Unit / joins | Pivot each file to county-month, then validate one-to-one joins | All three prepared tables have 11,658 matching keys |
| Duplicates | Duplicate source cell or final county-month is an error | No source-cell or final-key duplicates in the checked release |
| Geography | Normalize valid county names; exclude every non-California-county row | 205 excluded rows per raw source: 201 statewide summary rows and 4 invalid-code rows |
| Missing / suppression | Annotation 1/2 stays missing; absent category stays missing; observed zero stays zero | 94,823 language, 170 age/sex, 22,591 race/age suppressed cells retained as missing |
| Absent categories | Reindex known category columns, retaining missing cells | 132,036 absent language cells and 2,780 absent race/age cells; no absent age/sex cells |
| Labels | Whitespace/case normalization and explicit category allowlists | 33 language, 8 age/sex, 24 race/age columns; Missing/Unknown and Unknown kept distinct |
| Types | Monthly string keys, nullable whole-valued numeric counts, Boolean completeness, integer counters | Loader enforces types and rejects negative, fractional, infinite, or malformed counts |
| Denominator | Sum all 8 observed age/sex cells; otherwise unavailable | 85 county-month totals incomplete; no partial totals used for shares |
| Metadata | Require source agreement on F/P status and source data date | Agreement checked for every shared key; dates standardized to ISO |

The full audit distinguishes explicit suppression from absence; a suppression
counter is not a count of every missing wide-table cell. No row is removed merely
because one of its demographic counts is unavailable. Demographic families remain
separate summaries; joining them by county-month creates no individual cross-tabs.

## Reconciliation of available individual and team work

The local workspace contains an individual language-cleaning output at
`outputs/language_cleaning/cleaned_language_eligibles.csv` and a team merged
snapshot committed as `f8d28e9` by Fangning Xu. Both describe the earlier
January 2010–August 2026 release. The individual Python source is absent;
the `.pyc` cache is not a reproducible source file and was not executed.
The individual CSV is ignored by Git and is not included in a fresh clone;
the committed reconciliation report preserves the comparison and artifact hashes.

The individual output contains 251,535 long-format rows. Its 251,331 map-eligible
language cells match the team snapshot's corresponding values and missingness
exactly; **zero disagreements** were found. Its explicitly suppressed cells
contain no numeric values. The remaining 204 individual rows were marked
ineligible for county mapping. The earlier wide team snapshot retained three
invalid-county rows; the canonical pipeline now excludes invalid geography at
the cleaning step instead of relying on a runtime filter.

[The reconciliation report](outputs/reconciliation_report.json) records this
comparison. With the individual artifact still available locally, reproduce it
using `.venv/bin/python scripts/reconcile_language_output.py`. Supply the individual
CSV at the documented path (or pass `--individual /path/to/file.csv`) to rerun
this optional comparison in another clone. The script reads the earlier
team snapshot from Git history and records both artifact hashes. This verifies
the available outputs. Individual age/sex and race/ethnicity cleaning scripts
were not supplied for independent comparison. Full-team approval of the shared
rules was subsequently confirmed for the meeting recorded above; the unavailable
scripts are not represented as independently compared.

## Refresh from the earlier team snapshot

The previous valid snapshot had 11,600 county-month rows. The current official
release adds 58 September rows and removes no valid keys. On the common keys,
7,396 language, 4,346 age/sex, and 13,170 race/age cells changed in value or
availability. These are measured differences between publisher snapshots;
their causes are not inferred. The earlier snapshot remains recoverable from
Git history (`f8d28e9`), and the comparison is preserved in the cleaning audit.

The dashboard should use the single current canonical file. The individual
language-only output is reconciliation evidence, not another runtime source.
