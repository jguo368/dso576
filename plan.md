# Data-Cleaning and Validation Plan

## Scope and guardrails

This plan is based on read-only inspection of the project files. It proposes
checks and possible transformations; it does not apply them. The original CSVs
will remain unchanged. A future script will read originals, write derived files
to a separate `outputs/` directory, and log every change.

## 1. Project vision and business question

**Vision.** Help a DHCS Medi-Cal access strategy manager prioritize California
counties and beneficiary language populations for additional language-access
capacity. Provider-capacity data is needed before the project can claim that a
language population has inadequate provider capacity.

**Business question.** Which county-month-language combinations have the
largest reported Medi-Cal certified-eligible populations, and, after a
documented provider-language-capacity merge, where are the largest potential
population-to-capacity gaps?

**Planned metrics.**

- Certified eligibles by county, month, and primary language.
- Share of a complete county total by language, only where the denominator is
  documented as complete and suppression does not invalidate interpretation.
- Later, provider-language capacity and an explicitly defined eligible-to-
  provider-capacity comparison.

The existing files support beneficiary counts, not provider capacity. The plan
will keep the language-population result descriptive until a provider source is
added and validated.

## 2. Define one row

| Dataset | Observed row meaning | Candidate key to test | Important exception |
|---|---|---|---|
| `by-primary-language-certified-eligibles.csv` | A reported count for one month, county, and primary-language category. | `Month of Eligibility`, `County`, `Language` | `STATEWIDE`/invalid-code records must not be treated as ordinary county records without a decision. |
| `by-age-group-and-sex-certified-eligibles.csv` | A reported count for one month, county, age group, and gender. | `Month of Eligibility`, `County`, `Age Group`, `Gender` | Statewide rows use `STATEWIDE` category values. |
| `by-race-ethnicity-and-age-group-certified-eligibles.csv` | A reported count for one month, county, age group, and ethnicity. | `Month of Eligibility`, `County`, `Age Group`, `Ethnicity` | Statewide rows use `STATEWIDE` category values. |
| `medi_cal_merged_county_month.csv` | A derived wide county-month record containing county total, age/sex, language, and race/age values. | `month_of_eligibility`, `county` | Provenance and merge code are not in `exploration.ipynb`; validate before treating this as an authoritative source. |

Read-only checks so far found no repeated candidate keys in the merged table and
no repeated long-table language key. The future process will test the stated
keys for all three long tables and report repeats separately from exact-row
duplicates.

## 3. Preserve the source

Original/received data files are:

- `by-primary-language-certified-eligibles.csv` (13,261,620 bytes; file date
  2026-09-18)
- `by-age-group-and-sex-certified-eligibles.csv` (4,610,876 bytes; file date
  2026-09-18)
- `by-race-ethnicity-and-age-group-certified-eligibles.csv` (14,356,842 bytes;
  file date 2026-09-18)
- `medi_cal_merged_county_month.csv` (2,990,484 bytes; file date 2026-09-18;
  appears derived rather than a direct DHCS download)

Project notes identify DHCS Medi-Cal Certified Eligibles Data by Month with
Demographics as the source family, but they do not record a download date,
portal resource version, or source URL for these exact files. Before analysis,
record that source metadata and a SHA-256 hash for each input. Load paths will
be relative and read-only; no script will write into the source-data directory.

## 4. Inspect columns and data types

All CSV fields currently load as text/object when read conservatively to
preserve blanks, commas, identifiers, and source formatting. The notebook also
loads the three long tables with `pd.read_csv`, but it does not print a saved
schema, convert fields, create the merged file, or perform validation.

| Dataset | Columns and current type | Proposed future type/check (not yet applied) |
|---|---|---|
| Language | `Month of Eligibility`, `County`, `Language`, `Total Eligibles`, `Annotation Code`, `Annotation Description`, `Status`, `Date of Data`, `Difference` - all text/object | Month to datetime using `%Y-%m`; `Date of Data` to datetime using `%d%b%Y` after documenting blank/`.` placeholders; `Total Eligibles` to nullable integer after comma removal; keep county/language/status/annotation fields as strings; inspect whether all-blank `Difference` is a source artifact. |
| Age/sex | `Month of Eligibility`, `County`, `Age Group`, `Gender`, `Total Eligibles`, `Annotation Code`, `Annotation Description`, `Status`, `Date of Data` - all text/object | Same date/count approach; categorical fields remain strings. |
| Race/age | `Month of Eligibility`, `County`, `Age Group`, `Ethnicity`, `Total Eligibles`, `Annotation Code`, `Annotation Description`, `Status`, `Date of Data` - all text/object | Same date/count approach; categorical fields remain strings. |
| Merged county-month | `month_of_eligibility`, `county`, `status`, `date_of_data`, `county_total_eligibles`, `county_total_is_complete`, `age_sex_suppressed_cells`, `language_suppressed_cells`, `race_age_suppressed_cells`, eight `age_sex__age_*__{female,male}` fields, 34 `language__*` fields, and 24 `race_age__age_*__{ai_an,asian,black,hispanic,not_reported,white}` fields - all text/object under conservative loading | Parse the month/date fields; convert count and suppression fields to nullable integers; convert only the literal `True`/`False` completeness field to nullable boolean; preserve county/status as strings. |

Before conversion, capture failed conversion count and the original offending
values by column. The planned parser will remove commas only from the count
field and will never coerce a failed value to zero. Initial inspection found
three language `Total Eligibles` cells containing a single space after comma
removal, so those cells require source/annotation review rather than automatic
numeric conversion.

## 5. Standardize text

Future inspection will compare raw, stripped, and case-folded values without
overwriting the raw columns. It will inspect `County`, `Language`, `Age Group`,
`Gender`, `Ethnicity`, `Status`, annotations, and the corresponding merged
fields.

Findings to carry forward:

- County names have no leading/trailing whitespace or case variants in the
  three long files.
- `Language` has 2,573 values with leading/trailing whitespace; the plan will
  list the raw-to-stripped mapping and verify that stripping does not merge
  meaningfully distinct labels.
- `Date of Data` contains blanks and a whitespace-padded `.` placeholder.
  Preserve the raw date text and create a separate parsed field/placeholder
  flag only after the rule is approved.
- Existing categories include `Missing/Unknown`, `Other Non-Eng`, and `Other
  Chinese`. They must remain separate; no category grouping will occur without
  a documented analytical purpose.
- No IDs with leading zeros were found in these files. Any future provider IDs,
  FIPS, ZIP, or NPI fields must be loaded as strings before joins.

## 6. Investigate duplicates

The process will report both exact duplicate rows and repeated candidate keys,
with example rows and their differing columns. It will not remove any rows by
default.

Current observations:

- Exact duplicate rows: none in the four inspected CSVs.
- Merged county-month key: no repeats across 11,603 rows.
- Language month-county-language key: no repeats across 251,535 rows.

For the age/sex and race/age files, a repeated key may be a valid observation
only when a category, time period, or statewide summary distinguishes it. The
future report will explicitly test the proposed four-column keys before making
any deletion decision.

## 7. Handle missing data

The workflow will write missing count and percent by input column before and
after any approved transformation, distinguishing blank text from suppressed
counts. It will not impute source blanks.

Key findings and proposed handling:

| Issue | Initial evidence | Proposed treatment to validate |
|---|---|---|
| Suppressed/missing `Total Eligibles` | Language: 94,321 blanks; age/sex: 175; race/age: 22,515. Annotation descriptions include small-number and complementary-cell suppression. | Preserve as missing and retain annotation code/description. Do not use as zero in totals or denominators. |
| Missing dates | Language: 138,139 blanks; age/sex: 53,013; race/age: 157,187; each also has whitespace-padded `.` placeholders. | Preserve raw text; flag parsed missingness. Confirm whether the date is reporting metadata before deciding whether it affects analysis. |
| Merged-file missingness | County total blank in 89 rows; language fields have substantial blanks; `date_of_data` blank in 6,614 rows. | Treat blanks as unknown/suppressed unless documentation proves a zero. Use `county_total_is_complete` and suppression counts to control denominator eligibility. |
| All-blank language `Difference` | 251,535 blank values. | Confirm whether the field is unused in the extract; retain raw column until source documentation supports omission from an analysis copy. |

## 8. Check suspicious values

Future validation will separately flag, count, and export suspicious records
before any correction. Checks will include negative counts, failed numeric/date
parses, month range, status/category values, counts larger than applicable
totals, and extreme county-language values reviewed in context.

Initial findings:

- No negative numeric values were found after parsing count-like fields.
- All nonblank month fields parse with `%Y-%m`; all nonblank/non-placeholder
  `Date of Data` values parse with `%d%b%Y`.
- The merged file has three `Invalid County Code` records and 59 county labels,
  while each long source has 60 county labels. This is a geographic coverage
  and merge-provenance issue, not evidence that a record should be deleted.
- Merged status contains `F` (10,906) and `P` (697); source definitions are
  needed before filtering either status.

## 9. Verify merges

Do not merge the three long sources directly at their detailed dimensions:
each represents a different breakdown of the same eligible population. A
direct merge on month/county would multiply rows.

Planned merge design:

1. Keep each source in a separate cleaned long table.
2. Aggregate each source independently to one row per month/county only when
   its suppression policy and denominator are approved.
3. Before every merge, compare normalized key sets and report unmatched keys.
4. Use `validate="one_to_one"` only after aggregation to one row per
   month/county; use `validate="many_to_one"` for a future provider-location
   lookup only if each county/language mapping is unique on the right.
5. Compare row counts, county coverage, and total eligible counts before and
   after each merge; inspect `_merge` results and never use an inner merge by
   default.

The existing wide merged file requires reverse validation against source totals
and a documented creation script before it is reused. County and language key
format mapping must be saved in a crosswalk rather than silently edited.

## 10. Reconcile changes

Each future cleaning run will create an audit table with source rows, rows
after each stage, rows flagged, rows excluded only from a named analysis, and
rows removed (expected to be zero unless a documented duplicate rule is
approved). It will report, before and after:

- total row counts and candidate-key counts;
- count of missing/suppressed cells by column;
- sums of eligible counts, separately for complete, suppressed, invalid-county,
  final-status, and preliminary-status records;
- merge unmatched counts and any row multiplication.

## 11. Check calculations

Later dashboard measures will use explicit denominator and record-count rules:

- A language total is a sum of nonmissing reported cells, not necessarily a
  full county population; report suppressed-cell count alongside it.
- A language share is calculated only where the county total is complete and
  the approved suppression rule permits it; never replace a missing denominator
  with zero.
- Grouped results must retain a visible missing/invalid county group until an
  analysis-exclusion decision is approved.
- Provider-to-eligible ratios require compatible time period, county geography,
  provider definition, and a documented decision on FFS versus managed-care
  coverage. Do not call the result an access rate without those conditions.

## 12. Proposed five individual record checks

These are proposed verification cases only; final expected/actual checks await
approval of cleaning rules.

| Proposed record | Original field(s) to inspect | Expected future result | Why useful |
|---|---|---|---|
| One language row with whitespace around `Language` | Raw language, stripped candidate, all other key fields | Raw value retained; cleaned comparison value differs only by outer whitespace, if validation confirms it is the same label. | Tests text standardization without category merging. |
| A language row whose `Total Eligibles` is a single space | Count, annotation code/description, key fields | Flagged as nonnumeric/missing; never converted to zero. | Tests failed conversion and suppression handling. |
| A `Date of Data` value displayed as whitespace plus `.` | Raw date and parsed-date candidate | Raw retained and parsed date missing with a placeholder flag. | Tests a documented placeholder. |
| `2010-12 | Invalid County Code` in the merged file | County, month, total/completeness/suppression fields | Retained and geographically flagged, pending source correction. | Tests suspicious geographic coverage without deletion. |
| A future county-language/provider merge example | Both raw keys, normalized comparison keys, `_merge` result | Match status recorded; no unexpected row multiplication. | Tests the intended decision-support join. |

## 13. Reproducibility

After plan approval, create a beginner-readable pandas script/notebook with
these stages: load raw CSVs as strings; inspect and save profiles; apply only
approved transformations to copies; write cleaned outputs and audit tables;
run assertions for row counts, keys, conversion failures, and merges; then
write a 50-row difficult-case sample. Use relative paths, fixed input/output
names, `requirements.txt`, and a README command. Restart the environment and
compare output hashes before submission.

## 14. Remaining limitations

| Limitation | Effect on final Medi-Cal analysis |
|---|---|
| No provider-capacity dataset is present in the inspected project folder. | Language populations can be described but cannot identify provider-language capacity gaps. |
| FFS provider profile is described in project notes as incomplete for managed care. | A provider count could understate capacity or misstate access for managed-care members. |
| Suppression and incomplete county totals are present. | Ranking or share estimates may systematically undercount small populations and must disclose denominator eligibility. |
| `F` and `P` status definitions are not supplied in the files. | Filtering by status could unintentionally exclude valid observations or mix preliminary/final reporting. |
| `Invalid County Code` and statewide records lack a documented crosswalk/definition. | County comparisons and merge coverage can be distorted if treated as a California county. |
| Language categories measure certified eligibles' primary language, not a verified need for a particular provider language service. | The output is a planning signal, not proof of unmet access or causation. |

## Proposed Cleaning Decision Log

| Rule | Reason | Validation Check |
|------|--------|------------------|
| Preserve raw source columns and write only derived outputs. | Protects the original data and supports traceability. | Compare input SHA-256 and file timestamps before/after each run. |
| Parse dates into new fields; retain raw month/date text. | Allows type checks without losing source formatting. | Count invalid parses; list raw values causing them. |
| Treat blank/suppressed eligible counts as missing, not zero. | Suppression annotations show that a blank does not reliably mean zero. | Compare blank cells with annotation codes/descriptions and suppression counts. |
| Strip outer whitespace only into a separate comparison/clean field after reviewing mappings. | Language has whitespace cases, but labels must not be merged without evidence. | Export each raw-to-clean mapping and confirm no unintended category collapse. |
| Retain `Invalid County Code`, statewide records, and P status as flagged records. | Their analytical role is unknown; deletion would be unsupported. | Report their row/count totals separately and obtain source definitions. |
| Do not directly merge long demographic tables at row level. | Different breakdown dimensions would multiply records. | Assert expected uniqueness at the chosen aggregate grain and use pandas `validate`. |
| Do not use incomplete/suppressed county totals as share denominators by default. | They can create biased or undefined shares. | Report denominator completeness and compare numerator/denominator coverage. |

## Questions Requiring Human/Domain Decisions

1. What do source status values `F` and `P` mean, and should preliminary rows
   be shown, excluded, or labeled separately in the dashboard?
2. How should `Invalid County Code` records be handled: excluded only from
   county rankings, mapped using source documentation, or retained as an
   unassigned category?
3. What is the approved use of suppressed counts: retain as missing only,
   publish with suppression flags, or use a specific disclosure-control method?
4. Is the existing `medi_cal_merged_county_month.csv` an approved project
   source, and where is the code/provenance that created it?
5. What provider-capacity source and definition will establish language-access
   capacity, including FFS versus managed-care scope and time alignment?
6. Which language categories, if any, may be combined for a policy metric?
   `Other`, `Unknown`, and sign-language categories should not be combined by
   default.
