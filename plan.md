# Data Cleaning Plan

## Goal

I want to inspect and clean the Medi-Cal "By Primary Language, Certified Eligibles" dataset so that it can be used reliably for our county- and language-level analysis and dashboard.

The dashboard will allow a user to select a month and primary language, compare California counties by the number of Medi-Cal certified eligibles in that language, and calculate the selected-language population as a share of the county's total Medi-Cal eligible population.

The original source file must remain unchanged. All cleaning decisions should be documented and validated before producing a cleaned output.

## Scope and inspection baseline

This is a proposed cleaning plan only. No cleaning has been implemented and no cleaned dataset has been produced. Findings below come from a read-only inspection of `raw/by-primary-language-certified-eligibles.csv` on October 4, 2026. Source definitions that cannot be established from the CSV remain verification tasks, not assumed facts.

- 251,535 data rows and nine columns. Every parsed record has nine fields. The file has a UTF-8 byte-order mark (BOM), which should be handled on import so it does not become part of the first column name.
- 200 consecutive eligibility months, January 2010 through August 2026. All month strings parse as `YYYY-MM`.
- 60 county labels: 58 county names, `STATEWIDE` (200 rows), and `Invalid County Code` (four rows). All 58 named counties appear in every month, but individual language combinations are not complete.
- 34 language labels, including `STATEWIDE`, `Missing/Unknown`, and the leading-space label ` Unknown`. There are no case/trim collisions in county or language labels and no county whitespace issues.
- Exact duplicates across all nine original fields: **0** excess rows. Repeated `(Month of Eligibility, County, Language)` keys: **0** groups and **0** excess rows. A diagnostic comparison using trimmed, case-insensitive county/language labels also finds no repeated keys.
- Source SHA-256: `004f5baeba56ff297d44d11e40a4b3d8db861e2df2c7b838b3f039fe32329da7`. Recheck this after any future work to confirm the raw file remains unchanged.

### Missing values by column

Counts distinguish empty fields from other representations. CSV values are text at import, so blank columns must not acquire an inferred numeric meaning by accident.

| Column | Exactly empty fields | Other missing-like values | Interpretation for the plan |
| --- | ---: | --- | --- |
| Month of Eligibility | 0 | None found | Required month key. |
| County | 0 | Four `Invalid County Code` records | Present text, but unusable as a county assignment. |
| Language | 0 | 11,572 `Missing/Unknown`; 2,573 ` Unknown` | Explicit source categories, not blank cells. Keep separate. |
| Total Eligibles | 94,321 | Three single-space fields | 94,324 unavailable counts, all annotated as suppressed. |
| Annotation Code | 157,211 | None found | Blank means no code recorded, not a missing population count. |
| Annotation Description | 157,011 | None found | Blank means no description recorded. |
| Status | 0 | None found | Only `F` and `P`. |
| Date of Data | 138,139 | 3,736 fields contain eight spaces followed by `.` | 141,875 unavailable dates if the dot sentinel is confirmed as missing. |
| Difference | 251,535 | None found | Entirely empty; meaning and units cannot be inferred. |

## Column-by-column proposed rules

Retain original field values and a stable source-record reference alongside any future typed or normalized fields. Record each change with the original value, proposed value, rule, reason, evidence, and validation result. Flag unexpected values before deciding their disposition. None of the rules below authorizes silently deleting a row.

### 1. Month of Eligibility

- **Proposed type and transformation:** Parse strictly as a monthly period. Preserve the original `YYYY-MM` text. If a downstream tool requires a date, use the first day only as a documented month identifier, not as an observed eligibility day.
- **Reason:** Monthly filters, sorting, and joins must use consistent periods and must not confuse eligibility month with data-extraction date.
- **Validation:** Round-trip every parsed period to the original text. Confirm 200 distinct consecutive months from `2010-01` to `2026-08`, zero parse failures, and unchanged key counts. Flag future or malformed months in later refreshes rather than guessing dates. Do not add absent language rows or interpolate months automatically.

### 2. County

- **Observed issues:** No leading/trailing whitespace or capitalization variants were found. `STATEWIDE` and `Invalid County Code` are not individual counties.
- **Proposed rule:** Preserve county names as categorical text. Add a geography classification for named county, statewide aggregate, and unresolved county. Retain all records in the prepared master data. Exclude the 200 statewide records and four invalid-county records only from county comparisons, with their exclusion reasons recorded. Never assign an invalid record to a guessed county.
- **Reason:** Mixing geographic levels would distort rankings and totals. The four unresolved records are suppressed English records in December 2010 and September 2025, and suppressed English and Spanish records in December 2011.
- **Validation:** Check names against a verified county reference before any mapping. Expect 58 named counties, 251,331 county-detail rows, 200 statewide rows, and four unresolved rows in this snapshot. Confirm the groups partition all 251,535 records and preserve every original label. Any future spelling correction needs an explicit old-to-new mapping and a repeated-key check afterward.

### 3. Language

- **Observed categories:** `ASL`, `Arabic`, `Armenian`, `Cambodian`, `Cantonese`, `English`, `Farsi`, `French`, `Hebrew`, `Hindi`, `Hmong`, `Ilocano`, `Italian`, `Japanese`, `Korean`, `Lao`, `Mandarin`, `Mien`, `Missing/Unknown`, `Other Chinese`, `Other Non-Eng`, `Other Sign`, `Polish`, `Portuguese`, `Punjabi`, `Russian`, `Samoan`, `Spanish`, `STATEWIDE`, `Tagalog`, `Thai`, `Turkish`, ` Unknown`, and `Vietnamese`.
- **Proposed transformation:** Trim the leading space in ` Unknown` to create the normalized label `Unknown`, preserving the original label. This affects 2,573 records and corrects presentation whitespace only. Explicitly preserve `Unknown` and `Missing/Unknown` as separate categories in prepared data and dashboard results unless source documentation proves they are equivalent. Any future merger would require a documented mapping and validation. Do not modernize names, expand abbreviations, or combine Chinese or sign-language categories without a documented mapping and rationale.
- **Proposed classification:** Keep `Missing/Unknown` and normalized `Unknown` as separately identified unknown categories. Preserve `Other Chinese`, `Other Non-Eng`, and `Other Sign` as source groupings, without assuming they overlap or nesting them under other rows. Keep `STATEWIDE` as an aggregate marker outside the selectable primary-language list. All 200 such records also have County `STATEWIDE`.
- **Reason:** Category semantics affect both comparisons and denominator coverage. ` Unknown` appears from February 2020 through June 2025; Hindi and Punjabi first appear in July 2025. These boundaries flag possible coding changes, not proof that earlier populations were zero.
- **Validation:** Expect 34 labels in the master data after trimming and zero new key collisions. Compare category frequencies before/after and verify exactly 2,573 label changes, with 2,573 `Unknown` records and 11,572 `Missing/Unknown` records remaining separate. Review source category definitions and their effective dates before interpreting trends across July 2025. Keep absent month-county-language combinations distinct from recorded zero, suppression, and unknown language.

### 4. Total Eligibles

- **Observed type issue:** Counts are text with and without thousands separators. All 157,211 nonblank, non-whitespace values parse as whole numbers under a strict digit/comma format. No negative, zero, decimal, malformed nonblank numeric token, or nonfinite value was found. The only extra nonnumeric token is a single space on three records.
- **Proposed transformation:** Validate comma grouping before removing separators, then store valid counts as nullable integers. Preserve units as the number of Medi-Cal certified eligibles for that row's month and geography. Do not rescale to thousands, round counts, or sum months as unique people.
- **Proposed missing rule:** Treat the 94,321 empty fields and three whitespace-only fields as unavailable counts with suppression reasons retained. The three whitespace records are August 2026 Alpine–English, Inyo–Missing/Unknown, and Riverside–Italian, all code `2`. Do not replace suppressed counts with zero, averages, a threshold, or values inferred by subtraction.
- **Reason:** Missingness is tied to suppression: 93,681 code `1` records and 643 code `2` records account for all 94,324 unavailable counts. Numeric coercion that silently fills or drops these values would bias county comparisons.
- **Validation:** Expect 157,211 exact integer conversions and 94,324 null numeric values, each linked to its original suppression annotation. Round-trip numeric values against the comma-free source text. Confirm nonnegative integral counts and preserve valid zeros if they occur in a future release; this snapshot contains none. Unexpected negative/fractional/malformed values should be flagged and withheld from affected calculations pending review, with their source records retained.
- **Unusual-value review:** Published counts range from 11 to 16,051,565 across all geographic levels. Named-county detail ranges from 11 to 2,750,687; the maximum is Los Angeles–English in May 2023. Review statewide and county distributions separately. Large counts alone are not errors and should not be capped or removed.
- **Descriptive temporal review:** Inspect month-to-month patterns within the same county and language when both adjacent months have published counts. Describe unusual changes in context and flag them for review before deciding whether to keep or correct them. Do not introduce a numerical anomaly threshold unless supported by source documentation or explicit project requirements. Compare flagged records with source revisions, annotations, and category changes; retain unless evidence establishes an error. This review helps distinguish reporting or category changes from possible data errors. Validate that comparisons skip missing months and suppressed counts, preserve `Unknown` and `Missing/Unknown` as separate series, and log the evidence and each keep/correct decision. Corrections require source-backed replacement values and rechecking affected comparisons.

### 5. Annotation Code

- **Proposed type and rule:** Store as nullable categorical text, preserving `1` and `2` as codes rather than measurements. Normalize empty fields to null only in the typed copy, with the meaning “no annotation code recorded.” Add a suppression indicator derived from the code/description pair.
- **Reason:** Codes explain unavailable counts and must survive numeric parsing and dashboard filtering.
- **Validation:** Expect code `1` on 93,681 rows, code `2` on 643, and no code on 157,211. Check that `1` pairs with `Cell suppressed for small numbers`, `2` pairs with `Cell suppressed for complementary cell`, and every suppressed record has an unavailable count. Flag new codes or inconsistent pairs without guessing their meaning. Do not infer the suppression threshold from the observed minimum of 11.

### 6. Annotation Description

- **Proposed type and rule:** Preserve as nullable text. Represent empty fields as null in the typed copy without filling a fabricated description. Retain all three nonempty labels exactly, including `Statewide Total by MOE` on 200 rows with no annotation code.
- **Reason:** A description can indicate aggregation rather than suppression; nonempty description does not automatically mean an unavailable count.
- **Validation:** Check the two suppression mappings above and verify that all 200 statewide descriptions have both geography and language labeled `STATEWIDE` and a published numeric count. Expect 157,011 blank descriptions. Flag new or mismatched descriptions for review.

### 7. Status

- **Proposed type and rule:** Preserve categorical text `F` and `P`. Retain both in the master data and carry status into dashboard results. Verify source definitions before expanding these codes into display labels such as final or provisional.
- **Reason:** Status can affect interpretation and revisions. Dropping `P` would remove recent months required by the dashboard.
- **Validation:** Expect 235,009 `F` records spanning January 2010–August 2025 and 16,526 `P` records spanning September 2025–August 2026. Check status consistency within reporting months and between any numerator and denominator source. Flag unexpected codes or unexplained status changes; do not automatically rewrite them.

### 8. Date of Data

- **Observed type issue:** Mixed text dates, empty fields, and the padded dot token prevent consistent date typing. All 109,660 actual date strings parse as `DDMONYYYY`, ranging from October 19, 2020 to August 11, 2026.
- **Proposed transformation:** Parse valid tokens strictly to nullable calendar dates, preserving the original text and displaying typed dates as `YYYY-MM-DD`. Flag the 3,736 padded dot tokens as missing-date sentinels; confirm their source meaning before documenting conversion to null. Keep sentinel-derived nulls distinguishable from the 138,139 originally empty fields. Do not fill dates from nearby records or from eligibility month.
- **Reason:** This is release/extraction metadata whose exact definition needs confirmation. A missing metadata date should not delete an otherwise useful observation.
- **Validation:** Expect 109,660 parsed dates, no failed actual date strings, and 141,875 nulls if the sentinel mapping is confirmed. Round-trip parsed dates to their original date tokens. Review unusual relationships between data date and eligibility month against source reporting practice before flagging them as errors; never force the two dates to match.

### 9. Difference

- **Proposed rule:** Retain the entirely empty source column as nullable, undefined metadata in the master data and omit it from dashboard measures. Do not infer that it is an integer, a percentage, or a month-over-month change, and do not fill it with zero.
- **Reason:** The file provides no populated examples or definition. A derived change metric would be a new calculation with its own name and documented units.
- **Validation:** Confirm all 251,535 fields remain missing. If future releases populate this field, review its definition, type, and units before using it. Omission from a dashboard view must not remove source records or the archived field.

## Duplicate handling and row retention

1. **Exact duplicates:** Continue checking all nine original fields before normalization. None currently require removal. If future identical records appear, flag them and establish whether they are accidental copies. Only then may a prepared view retain one representative, with a log of each excluded source-record reference and validation that one copy per exact group remains.
2. **Repeated business keys:** Check month-county-language keys separately before and after normalization. There are none now. Future repeated keys may differ in counts, status, annotation, or data date. Do not sum them, keep an arbitrary first row, or automatically select the latest date. Resolve revision semantics using source evidence, retain the original records, and document which version feeds the dashboard. Validate uniqueness and reconcile affected counts afterward.
3. **Other flagged records:** Retain suppressed, unknown-language, unresolved-county, missing-date, and unusual-value records in the master data. Exclusions from specific dashboard calculations need an explicit reason and count. If an unresolved problem makes a measure unusable, show it as unavailable instead of deleting the underlying observation.

## County totals and language-share requirements

The exact county-share denominator is a material data gap. The file contains 200 statewide totals, but no explicit county-total language category. Suppression occurs in 11,400 of the 11,600 named county-month groups. Summing available language counts would generally understate county totals. Even groups without suppression require confirmation that the categories are exhaustive and mutually exclusive and that omitted combinations are understood.

- **Proposed denominator source:** Obtain a verified county-by-month total for the same certified-eligible population, units, and reporting vintage/status. Retain its provenance and join on county and eligibility month. Do not use statewide totals as county denominators or treat a sum of published language counts as an exact county total.
- **Reason and validation:** The requested share is the published selected-language count divided by the matching county total. Require exactly one valid denominator per county-month and check join cardinality, coverage, status/vintage alignment, positive denominator, and numerator no greater than denominator. Missing or suppressed numerators, missing/nonpositive denominators, and unresolved mismatches produce an unavailable share with a reason. Until a suitable denominator is verified, counts can be displayed where published, but exact county shares remain unavailable.
- **Units and display:** Store a derived share as a fraction from 0 to 1 and label its dashboard display as a percentage from 0% to 100%. This is a new measure, not a conversion of `Total Eligibles`. Validate bounds and manually reconcile representative county-language-month results to both source inputs.
- **Aggregate controls:** Keep statewide rows for contextual checks, outside county rankings and primary-language selection. Compare published county detail sums with matching statewide controls as partial-coverage diagnostics only. Suppression and unresolved counties prevent assuming equality. Never recover suppressed values from residuals or combine statewide totals with county detail in a sum.
- **Coverage behavior:** An absent language key means no published row, not zero. Do not create zero-filled county-language grids. If a dashboard displays all 58 counties, identify absent and suppressed values explicitly. Retain unknown and other categories in any future validated denominator definition rather than excluding them because a named language is selected.

## Validation gates before any cleaned output

1. Confirm the raw-file checksum and preserve the original nine fields and source-record references. Handle the BOM on import and verify the exact nine expected headers.
2. Reproduce the row count, missing-value table, category frequencies, and both duplicate checks. Every normalization must have a documented before/after mapping and a reason.
3. Reconcile all rows across county detail, statewide, and unresolved-geography classifications. Reconcile published and suppressed counts exactly. No unexplained row loss, category merging, numeric change, or unit change is acceptable.
4. Review flagged values first. Record whether each is kept, corrected using evidence, or excluded from a specific calculation, and rerun the relevant type, key, category, and total checks after any approved correction.
5. Resolve source definitions for unknown-language categories, suppression rules, status codes, dot date markers, category changes, and denominator coverage before relying on them in dashboard calculations. Unresolved definitions must remain documented limitations.
6. Spot-check future dashboard results for a published count, each suppression type, an absent language key, each unknown category, a provisional-status record, and a missing denominator. Confirm unavailable values never become zero and aggregation rows never enter county rankings.

No dataset transformations, row removals, or dashboard calculations are implemented by this document.
