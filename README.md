Module 6 Data Cleaning:

GitHub branch: Jonathan
Branch URL: https://github.com/jguo368/dso576/tree/Jonathan
Commit ID: dcaf9421f06536835b79f8fe820ce95d11fb2a86


# Goal and question

This submission cleans the California Department of Health Care Services
(DHCS) Medi-Cal Certified Eligibles by Primary Language file for analysis and
a future dashboard. The working question is: Which California counties and
primary-language groups have the largest numbers of Medi-Cal certified
eligibles and may warrant closer review for language-access planning?

The data supports descriptive comparisons only. It does not directly measure
health-care access, provider language capacity, use of services, or causal
effects.

# Data source

California Department of Health Care Services
https://lab.data.ca.gov/dataset/medi-cal-certified-eligibles-data-by-month-with-demographics
Resource: By Primary Language, Certified Eligibles
Resource URL: https://data.chhs.ca.gov/dataset/8c897320-ba87-4574-bc37-bae974191c35/resource/b698c8d7-aacd-43c6-a7dd-737ff5692284/download/t5_eligibility_by_language_201001_202609.csv
- Resource version: September 12, 2026
- Coverage in the local file: January 2010–August 2026

# Setup and run instructions
From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python clean_data.py
jupyter nbconvert --to notebook --execute --inplace data_cleaning.ipynb
python build_report.py
```

`clean_data.py` stops with an assertion error if a required validation fails.
The notebook deliberately reruns the same pipeline from the untouched source.

# Expected generated outputs

- `output/by-primary-language-certified-eligibles-cleaned.csv` — complete
  cleaned data (251,535 rows; intentionally ignored by Git because it can be
  recreated).
- `cleaned_data_sample.csv` — 50 submitted rows selected deterministically from
  invalid-county, disclosure-suppressed, whitespace-normalized, extreme-value,
  preliminary, and ordinary final records.
- `evidence/source_profile.json`
- `evidence/validation_summary.json`
- `evidence/missingness_before_after.csv`
- `evidence/cleaning_decision_log.csv`
- `evidence/record_checks.csv`
- `Module_6_Cleaning_Report.pdf`
