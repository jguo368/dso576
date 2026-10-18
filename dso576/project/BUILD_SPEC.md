# BUILD_SPEC

## 1. Project Vision

A Medi-Cal access strategy manager at the California Department of Health Care Services (DHCS) must decide which counties and language populations should be prioritized for additional language-access capacity.

The dashboard will help the user compare California counties based on:

- the size of a selected Medi-Cal language population,
- the share of that language population within the county's Medi-Cal population,
- and basic county-level demographic context.

The dashboard is intended to support prioritization and further investigation.

It does not directly prove that a county currently has insufficient interpreters or other language-access services.


## 2. Primary User

The primary user is a Medi-Cal access strategy manager at DHCS.

The user needs a faster way to identify counties where a specific language population is relatively large and may therefore deserve additional attention when planning language-access capacity.


## 3. Decision Supported

The dashboard supports the following decision:

Which counties and language populations should receive the highest priority for further review or additional language-access planning?


## 4. Main User Flow

The user:

1. Selects a month.
2. Selects a language.
3. Views the distribution of that language population across California counties.
4. Compares counties using population count and, where available, population share.
5. Selects a county for more detail.
6. Reviews basic county-level demographic context.


## 5. Data Sources

The analysis uses three Medi-Cal demographic datasets:

1. Medi-Cal Certified Eligibles by Primary Language
2. Medi-Cal Certified Eligibles by Age Group and Sex
3. Medi-Cal Certified Eligibles by Race/Ethnicity and Age Group

These sources are cleaned and reshaped into one canonical analysis-ready dataset.


# 6. Data Contract

## Unit of Analysis

The final cleaned dataset contains:

**one row per month + county**

The unique identifier for each row is:

`month_of_eligibility + county`

There should not be more than one final row for the same month and county.


## Final Dataset Structure

Important fields include:

- `month_of_eligibility`
- `county`
- `county_total_eligibles`
- `county_total_is_complete`

Language variables:

- columns beginning with `language__`

Age and sex variables:

- columns beginning with `age_sex__`

Race/ethnicity and age variables:

- columns beginning with `race_age__`

Suppression tracking variables:

- `language_suppressed_cells`
- `age_sex_suppressed_cells`
- `race_age_suppressed_cells`


# 7. Team Cleaning Agreement

Before creating the final dataset, the team will compare the individual Module 6 cleaning work and agree on one shared cleaning approach.

Any disagreements about missing values, duplicates, category names, data types, joins, exclusions, or derived fields must be resolved before the final cleaning pipeline is merged into the `main` branch.

The rules below represent the final agreed definitions used by the project.


## 7.1 Duplicate Handling

The final combination of:

`month_of_eligibility + county`

must be unique.

The original source datasets may contain multiple rows for the same month and county because they contain different language, age, sex, or race categories.

These are not considered duplicates.

The source data must first be reshaped or aggregated to county-month level.

If duplicate county-month rows remain after this step, the cleaning process should flag them for review rather than silently removing them.


## 7.2 Missing and Suppressed Values

Some Medi-Cal counts are suppressed in the original data.

Suppressed values are not the same as zero.

Therefore:

- suppressed values remain missing,
- suppressed values are not replaced with `0`,
- the full county row is not automatically deleted because one value is suppressed,
- calculations that require a suppressed value should return unavailable rather than an estimated number.

The dashboard should display missing or suppressed results clearly when needed.


## 7.3 Data Types

The final cleaned dataset should use consistent data types.

### `month_of_eligibility`

Stored in one standardized monthly date format.

### `county`

Stored as text/string.

### Population count fields

Stored as numeric values.

Suppressed counts remain missing numeric values.

### `county_total_is_complete`

Stored as a Boolean value:

- `True`
- `False`


## 7.4 Standardized Labels and Categories

Labels must be standardized before aggregation and joining.

Cleaning should:

- remove unnecessary whitespace,
- use one consistent county naming format,
- use one consistent spelling for each language,
- use consistent age, sex, and race/ethnicity category labels.

Unexpected categories should be reviewed before producing the final dataset.


## 7.5 Join Rules

The three original datasets have different units of analysis and must not be directly merged row-by-row.

Before joining:

- the language data must be reshaped to county-month level,
- the age/sex data must be reshaped to county-month level,
- the race/ethnicity data must be reshaped to county-month level.

The prepared tables are then joined using:

`month_of_eligibility + county`

This prevents a many-to-many join from incorrectly multiplying rows.


## 7.6 Exclusions

The dashboard focuses on individual California counties.

Therefore:

- statewide summary rows are excluded from county-level analysis,
- rows with missing or invalid county identifiers are excluded from the canonical county-month dataset,
- rows with invalid month identifiers are excluded,
- suppressed cells are not treated as a reason to delete the entire county-month row.

Any additional exclusion must be documented in the cleaning code.


# 8. Derived Fields

## 8.1 County Total Eligibles

`county_total_eligibles`

This is a derived field representing the total Medi-Cal eligible population in a county for a selected month.

It is derived from the age/sex data after cleaning and aggregation.

It should only be treated as a valid complete total when all required source cells are available.


## 8.2 County Total Completeness

`county_total_is_complete`

This Boolean field identifies whether `county_total_eligibles` can safely be used as a denominator.

If the required source values are suppressed or missing:

`county_total_is_complete = False`


## 8.3 Selected Language Count

The selected-language count comes from the appropriate:

`language__...`

column.

Example:

`language__mandarin`

or

`language__spanish`


## 8.4 Language Share

Language share is calculated as:

`selected_language_count / county_total_eligibles`

This metric should only be calculated when:

- the selected-language value is available, and
- `county_total_is_complete == True`

Otherwise, language share is shown as unavailable.


# 9. Important Interpretation Rule

The language, age/sex, and race/ethnicity datasets describe county populations separately.

They do not provide individual-level cross-tabulations across all variables.

For example, the project can report:

- Mandarin-speaking Medi-Cal eligibles in Los Angeles County
- the overall age distribution of Medi-Cal eligibles in Los Angeles County

But the project cannot claim:

- the age distribution specifically among Mandarin-speaking Medi-Cal eligibles

because the available data do not directly contain a language-by-age cross-tabulation.


# 10. Dashboard Filters

## Month Filter

Source:

`month_of_eligibility`

The selected month updates all dashboard outputs.


## Language Filter

Source:

columns beginning with:

`language__`

The selected language updates:

- county map,
- ranking,
- summary metrics,
- county detail.


# 11. Dashboard Components

## 11.1 California County Map

### Question answered

Where are the largest populations associated with the selected language?

### Required data

- `county`
- selected `language__...` column
- `month_of_eligibility`

### Behavior

Counties are displayed using the selected-language eligible population.

Selecting a county updates the county detail section.


## 11.2 County Ranking

### Question answered

Which counties have the largest selected-language Medi-Cal populations?

### Required data

- `county`
- selected-language count

### Calculation

Counties are sorted in descending order by selected-language count.


## 11.3 Language Share

### Question answered

In which counties does the selected language represent a relatively large share of the overall Medi-Cal population?

### Required data

- selected-language count
- `county_total_eligibles`
- `county_total_is_complete`

### Calculation

`selected_language_count / county_total_eligibles`


## 11.4 County Detail

When a county is selected, the dashboard shows:

- selected-language count
- total county Medi-Cal eligibles
- selected-language share when available
- age/sex context
- race/ethnicity context


# 12. Backend Analysis Requirements

The backend analysis code should provide reusable Python functions or outputs for:

1. available months,
2. available languages,
3. county ranking for a selected month and language,
4. map-ready county data,
5. county summary metrics,
6. selected-language share,
7. age/sex county summary,
8. race/ethnicity county summary.

Backend functions must return reusable values or pandas DataFrames.

They should not only print results.


# 13. Backend and Data Consistency

The backend must follow the same definitions used in this BUILD_SPEC.

Examples:

- suppressed values must not be converted to zero,
- language share must use `county_total_eligibles`,
- language share must not be calculated when `county_total_is_complete == False`,
- county-month must remain the final unit of analysis,
- the backend must not create demographic relationships that are not present in the source data.


# 14. Phase 3 MVP

The minimum Phase 3 dashboard should include:

- month selector,
- language selector,
- California county map,
- county ranking,
- selected county summary,
- language count,
- language share when valid,
- basic demographic context.

Provider-capacity information is not required for the initial MVP unless a reliable additional dataset and join are verified.


# 15. Acceptance Checks

The Phase 2 work is complete when:

- the final dataset contains one row per county-month,
- county-month rows are unique,
- suppressed values are not treated as zero,
- data types are consistent,
- county and category labels are standardized,
- joins do not create duplicated county-month rows,
- exclusions are documented,
- derived fields follow the definitions above,
- the backend can generate every metric required by the dashboard,
- BUILD_SPEC definitions match both the cleaned data and backend code,
- the agreed cleaning pipeline is merged into the `main` branch.