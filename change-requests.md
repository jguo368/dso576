# Team change requests

Copy this template into your team's repository if no shared change-request file exists. Do not replace an existing file. Keep your individual audit in the module folder.

## Claims

| Author | Feature | Number | Distinct scope or new evidence |
| --- | --- | --- | --- |
| Haopeng Chen | County Ranking — descending order, alphabetical tie-breaking, and competition ranking, implemented in get_county_ranking(). | September 2026 Spanish observed eligible subtotal, independently calculated from the canonical CSV and compared against get_month_summary(). | Phase 2 backend only. The Phase 3 dashboard has not been implemented. |

## Requests

Copy the following block for each actionable finding. Agree on a unique ID with your team. A check that finds no defect can stay in the individual audit; do not invent a bug to fill a request.

### Haopeng Chen — completed Phase 2 audit (no defect found)

- Author: Haopeng Chen
- Status: verified; no backend fix required
- App version or commit checked: `3afb82b57ca9863a921eae805541846c4d561e46` from `origin/main`, tested in a temporary snapshot while my working branch stayed `haopeng-chen`.
- Feature and intended behavior: `get_county_ranking(data, "2026-09", "spanish")` must sort observed counts descending, break ties alphabetically, use competition ranks (1, 1, 3), and retain missing counties last/unranked, as required by `BUILD_SPEC.md`.
- Inputs and reproduction steps: run the command below from `Project`. The check reads the pinned canonical `dso576/project/medi_cal_merged_county_month.csv`, independently calculates the subtotal with pandas, compares all 58 ranking rows, exercises a synthetic tie case, and runs the existing tests.

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/comarea/dso576/.venv/bin/python audits/haopeng_module9_check.py
```

- Expected result: all 58 real-data `(county, count, rank)` tuples match an independently sorted reference. Synthetic input county/count pairs, in input order, are Amador/100, Butte/0, Alameda/100, Alpine/NA, Colusa/50; expected output is Alameda/100/1, Amador/100/1, Colusa/50/3, Butte/0/4, Alpine/NA/NA. All synthetic rows use September 2026, a county total of 200, completeness True, and all three suppression counters 0.
- Actual result: both ranking comparisons matched exactly. Independent September Spanish observed subtotal and `get_month_summary().observed_language_count` both equal **3,505,796**. All 58 counties are present; 56 have observed counts and Alpine/Mono are unavailable. The full Spanish count and statewide share remain NA; completeness is False.
- Evidence and likely cause, if established: [audit check](audits/haopeng_module9_check.py) and [saved exact results](audits/haopeng_module9_results.txt). **15 individual checks passed, 0 failed; 22 existing tests passed, 0 failed.** No defect or defect cause was established.
- Requested change: none; **no backend fix is required** for the tested behavior. For future Phase 3 verification, confirm the display labels 3,505,796 as an observed subtotal with 56/58 coverage, keeps missing values unavailable rather than zero, and does not label it a complete statewide Spanish total. This is an existing future requirement, not a confirmed dashboard defect or a new backend implementation request.
- Verification check: rerun the pinned audit command and inspect the saved expected/actual rows. The canonical CSV SHA-256 is `8bd21b92046753bee440ef290192b8b260fb317953e2e2fca553ff2e3f46d803`.
- Implementation commit and verification result, when built: no implementation change; Phase 2 verification passed at the audited commit. Phase 3 UI verification is pending because the dashboard was not implemented in that version.
- Limitations and claim check: no overlapping ranking claim was found in available local and fetched team branches. Fangning Xu's claim on `origin/fennie-project` concerns language cleaning/key coverage. Unpushed work, private files, Brightspace, and verbal claims could not be checked. This audit verifies selected backend behavior against the canonical CSV; it does not independently revalidate DHCS source values, all month/language combinations, or a dashboard.

### AUDIT-XX Short description

- Author:
- Status: open
- App version or commit checked:
- Feature and intended behavior:
- Inputs and reproduction steps:
- Expected result:
- Actual result:
- Evidence and likely cause, if established:
- Requested change:
- Verification check:
- Implementation commit and verification result, when built:

## Follow through

One teammate can ask Codex to implement open requests one at a time. For each, rerun the evidence, commit with its ID, and mark it built only after checking the result. File a request rather than undoing someone else's work.
