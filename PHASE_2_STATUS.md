# Phase 2 handoff

## Deliverable status

- **Specification:** complete product behavior, use cases, metric definitions,
  missing-data rules, architecture, technology choices, build order, and concrete
  acceptance checks are in `dso576/project/BUILD_SPEC.md`.
- **Canonical data:** rebuilt from three same-release official DHCS resources;
  11,658 unique county-month rows, 58 counties, 201 months through September 2026.
  Source hashes, exclusions, and differences from the earlier team snapshot are
  in `outputs/cleaning_report.json`.
- **Reconciliation evidence:** 251,331 eligible individual language cells agree
  exactly with the earlier team snapshot. No numerical or missingness conflicts
  were found. See `CLEANING.md` and `outputs/reconciliation_report.json`.
- **Backend:** all planned selector, overview, map, ranking, county detail,
  language-share, age/sex, and race/ethnicity outputs are reusable functions.
- **Verification:** automated contract, metric, raw-cleaning, and real-data
  integration checks are included. All **22 tests pass** on the refreshed data.
- **Dashboard:** intentionally a Phase 3 deliverable; the build spec describes
  exactly how to implement it using this backend.

## Questions and gaps resolved during implementation

| Previously open choice | Resolution |
| --- | --- |
| Which dataset is canonical? | The tracked wide CSV; language-only artifacts are evidence only |
| What is the latest snapshot? | September 2026 official release for all three sources together |
| Invalid-county rows in merged data? | Exclude during cleaning, with explicit raw-source audit counts |
| Missing category versus suppression? | Both unavailable; suppression counters count only annotated cells |
| Safe demographic aggregates? | Require every component in the requested group |
| Zero or incomplete denominator? | Language share unavailable; observed zero numerator remains zero |
| Starting dashboard state? | Latest month, Spanish, Los Angeles; explicit fallback rules |
| Geographic source and join? | Census 2025 county boundaries, California filter, county-name join, 58-name check |
| Ranking ties and unavailable counties? | Competition rank, alphabetical tie order, missing last/unranked |
| Overview coverage? | Clearly labeled observed subtotal; complete totals require all 58 counties |
| UI / backend coupling? | Pure DataFrame analysis; separate chart builders and session-state composition |

## Independent review

An independent agent, given the repository and BUILD_SPEC without the preceding
conversation, completed a read-only review on October 18, 2026. It found no
blocking defect or important unresolved Phase 3 product, metric, data-source, or
architecture decision. It checked source hashes, rebuilt all three sources in
memory, matched canonical values/missingness and audit counts, and exercised all
seven output families from `/private/tmp` to check working-directory independence.

The review found one loader gap: custom CSVs could omit or corrupt `status` and
`date_of_data` even though the raw cleaner enforced those fields. The loader now
requires both, validates F/P status, normalizes ISO and legacy DDMMMYYYY dates,
preserves missing dates, and rejects malformed or impossible dates. Regression
tests were added. The independent agent reviewed the correction and confirmed
that its finding was resolved with no further defect found.

A separate command-line rebuild produced a byte-identical canonical CSV, SHA-256
`8bd21b92046753bee440ef290192b8b260fb317953e2e2fca553ff2e3f46d803`.
The final suite passed 22 tests in 3.577 seconds using Python 3.13.15, pandas
2.3.3, and NumPy 2.5.3. `git diff --check` also passed.

The command-line cold-start export (`python -m medi_cal_analysis`) generates
`outputs/dashboard_preview.json` for review. September Spanish results provide
a concrete suppression check: 56/58 counties have observed counts; their subtotal
is 3,505,796, while the full statewide count/share remain unavailable. Los Angeles
has 1,129,822 Spanish-language eligibles / 3,639,204 total eligibles, approximately
31.0%. The `unknown` language category is entirely unavailable in the latest
month, providing a real all-unavailable case for Phase 3.

No interface/browser test is claimed: the dashboard and its interaction checks
belong to Phase 3. The independent review assessed build readiness and backend
correctness, not a finished dashboard.

## Human submission steps

The available artifacts support an output-level comparison. Individual age/sex
and race/ethnicity cleaning scripts and a record of unanimous teammate approval
were not supplied. The team should review and confirm the documented cleaning
rules before claiming that the assignment's team agreement step is complete.
No teammate confirmation is fabricated.

These deliverables are prepared on local `main`; identify the handoff commit with
`git log -1`. No remote push, teammate message, or course submission is performed.
