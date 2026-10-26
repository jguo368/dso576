# Team change requests

## Claims

| Author | Feature | Number | Distinct scope or new evidence |
| --- | --- | --- | --- |
| Jonathan Guo | Month filter propagation across map, ranking, overview, county detail, age/sex, and race/ethnicity backend outputs | Los Angeles County total certified eligibles for September 2026 | Independently sums all eight age/sex cells and compares August with September; records the absence of a browser-testable dashboard at the pinned commit. |

## Requests

### CR-009-JG-01 — Complete and test the dashboard month interaction

- **Author:** Jonathan Guo
- **Status:** Open; backend verified, user-interface verification pending
- **App version or commit checked:** `3afb82b57ca9863a921eae805541846c4d561e46` from `origin/main`
- **Feature and intended behavior:** A month selection should update the overview, map, ranking/comparison, county language metrics, and county demographic context while retaining a valid county selection and clearing stale chart selections as specified in `BUILD_SPEC.md`.
- **Inputs and reproduction steps:** Run `PYTHONDONTWRITEBYTECODE=1 python3.13 audits/jonathan_module9_check.py` (or use the project's Python 3.11+ environment). The automated evidence checks August and September 2026 with Los Angeles and Spanish. For the pending UI check, launch the committed dashboard, select Los Angeles and Spanish, switch from August 2026 to September 2026, and inspect every dependent view.
- **Expected result:** All displayed month labels and values update to September. Los Angeles's all-eligible county total changes from 3,720,277 to 3,639,204. The selected county remains Los Angeles, and no view retains August data or stale chart state.
- **Actual result:** The pinned backend passed: every tested output contained only the requested month, the county totals matched the independent sums, and the existing test suite passed. However, the pinned commit contains no Streamlit app, chart builders, or other dashboard UI, so the browser selection and visible redraw could not be tested.
- **Evidence and likely cause:** `audits/jonathan_module9_check.py`, `audits/jonathan_module9_results.txt`, and `my-audit.md`. This is a missing Phase 3 implementation/test artifact, not evidence of an incorrect backend calculation. `BUILD_SPEC.md` explicitly states that the interface was not a Phase 2 deliverable.
- **Requested change:** Commit the Phase 3 dashboard build, document its launch command, and add an end-to-end or recorded manual check for the month-change scenario above. Do not mark the interaction verified from backend tests alone.
- **Verification check:** Repeat the browser steps for August and September, confirm the six dependent areas, and rerun the audit script. Record the tested app commit and result here.
- **Implementation commit and verification result, when built:** Pending.

## Follow through

Do not replace a teammate's findings or claim a user-interface pass without a runnable dashboard. When the app is added, update the request with the implementation commit and the browser verification result.
