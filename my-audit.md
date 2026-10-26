# Module 9 individual audit

## Audit identification

- **Auditor:** Jonathan Guo
- **Feature audited:** Month filter propagation to month-dependent views
- **Number audited:** Total Medi-Cal certified eligibles for Los Angeles County in September 2026
- **Version checked:** Team commit `3afb82b57ca9863a921eae805541846c4d561e46` (`origin/main` when audited)
- **Canonical data:** `dso576/project/medi_cal_merged_county_month.csv`
- **Evidence:** `audits/jonathan_module9_check.py` and `audits/jonathan_module9_results.txt`

I chose this scope after checking the available team branches. Fangning Xu audited suppression-preserving cleaning and county-month key coverage. Haopeng Chen audited county ranking and the September 2026 Spanish observed subtotal. My audit contributes different evidence: Month propagation across the reusable views and an independent calculation of one county's all-eligible total.

## Intended user, task, and requirement

The intended user is a DHCS Medi-Cal access strategy manager comparing county and language populations for further language-access review. The user should be able to select another month and have the overview, map, comparison, county language metrics, and county demographic context update to that month.

The relevant requirements in `BUILD_SPEC.md` are that month changes update every dependent view and that county total eligibles equal the sum of all eight age-by-sex cells only when all eight are observed. This total is a count of all Medi-Cal certified eligibles in the selected county and month. It is not the selected-language count, a statewide total, a rate, or a measure of health-care access or provider capacity.

## Feature check: changing the month

### Reproducible steps

From the repository root, run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.13 audits/jonathan_module9_check.py
```

The script reads the pinned commit through Git without changing branches. It requires Python 3.10 or newer because the team backend uses modern type-hint syntax; I ran it with Python 3.13. With county fixed to Los Angeles and language fixed to Spanish, it requests August 2026 and September 2026 separately from the backend functions intended to supply the map, ranking, overview, county detail, age/sex detail, and race/ethnicity detail. For each response, it checks that every returned `month_of_eligibility` equals the selected month. It also checks that the loaded data are not mutated.

### Expected result

Every backend output should contain only the selected month. The Los Angeles county detail total should change when the selection changes because the underlying monthly values differ.

### Actual result

All six tested backend outputs returned only August rows for `2026-08` and only September rows for `2026-09`. The Los Angeles county total changed from **3,720,277** in August to **3,639,204** in September, a decrease of **81,073**. The input DataFrame was unchanged. The team's existing test suite also passed.

This establishes that the reusable backend respects two different month inputs for the tested views and data. It does **not** establish that a browser selector is wired correctly, that visible labels/charts redraw, that stale chart selection state clears, or that response time meets the two-second target. The pinned commit explicitly describes the dashboard as a future Phase 3 deliverable and contains no Streamlit application, chart builders, or browser-testable interface. Therefore, I could not truthfully perform the requested click-level dashboard test on this version.

## Number check: Los Angeles total eligible population

### Definition and independent method

For one county and month, `county_total_eligibles` should be the sum of the eight age/sex cells: four age groups (0–18, 19–44, 45–64, and 65+) crossed with female and male. The unit is eligible people. The denominator is not applicable because this is a count. All eight cells must be observed; otherwise, the total should be unavailable rather than a partial sum.

I independently read the canonical CSV and summed the eight September 2026 Los Angeles cells using ordinary Python addition. I did not call `get_county_summary`, `get_age_sex_summary`, or another project metric function to calculate the expected number.

| Component | September 2026 count |
| --- | ---: |
| Age 0–18, female | 536,454 |
| Age 0–18, male | 565,415 |
| Age 19–44, female | 687,463 |
| Age 19–44, male | 572,622 |
| Age 45–64, female | 403,843 |
| Age 45–64, male | 343,708 |
| Age 65+, female | 319,823 |
| Age 65+, male | 209,876 |
| **Independent sum** | **3,639,204** |

### Expected and actual result

The independently expected total was **3,639,204**. The canonical `county_total_eligibles` value and `get_county_summary(data, "2026-09", "spanish", "Los Angeles")` both returned **3,639,204**, and `county_total_is_complete` was true. As a second small cross-check, the same method produced **3,720,277** for August, matching the stored and backend values.

The number passes the tested definition, units, completeness condition, and independent recomputation. The `spanish` argument does not change this denominator: it is the all-eligible county population used to contextualize a selected language count.

## Conclusion, requested change, and uncertainty

The month-aware backend and the Los Angeles September 2026 total passed the checks at the pinned commit. I found no numerical defect in this scope. I recorded **CR-009-JG-01** because the required user-level dashboard interaction could not be tested: no dashboard implementation was present in the audited commit. Once the Phase 3 app is committed, the team should perform the browser steps in that request before claiming that the month filter works end to end.

Remaining uncertainty includes the unimplemented UI behavior, any unpushed/private build, other county/month combinations, and the accuracy of DHCS source reporting itself. The check validates the canonical data and backend calculation; it does not independently compare the eight source cells with the live DHCS publication.

## Personal contribution and AI use

I selected the audit scope, interpreted what the county total should mean, chose Los Angeles(big relevance) and the two test months, reviewed the expected and actual results, and made the conclusions above. Codex helped inspect the repository and help out with coding and running some test cases. I verified that the final claims match the saved evidence and did not claim a dashboard click test that was not possible.
