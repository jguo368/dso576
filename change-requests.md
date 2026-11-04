# Team change requests

Original audit: application code/data checked at `3afb82b57ca9863a921eae805541846c4d561e46`. The findings below retain that historical scope; the November 4 implementation and verification are recorded separately.

## Claims

| Author | Feature | Number | Distinct scope or new evidence |
| --- | --- | --- | --- |
| Shawn Shih | County comparison with month/language selection; backend versus browser availability | September 2026 Los Angeles Spanish share and statewide coverage guard | New CSV/Decimal oracle covering 232 county metric records, seven synthetic cases, and explicit Phase 2/Phase 3 scope check. No other claims were present locally; overlap elsewhere is unconfirmed. |

## Requests

### AUDIT-SS-01 Complete the county-comparison browser feature

- **Author:** Shawn Shih, prepared with Codex assistance.
- **Status:** implemented and locally verified November 4, 2026, on `codex/interactive-county-dashboard`; not yet merged into main.
- **App version or commit checked:** `3afb82b57ca9863a921eae805541846c4d561e46`.
- **Feature and intended behavior:** A DHCS manager selects month/language, compares all 58 counties by count or share, and selects county detail through map, table, or selector. See `BUILD_SPEC.md`, lines 22-36.
- **Inputs and steps to reproduce:** Inspect `git ls-files` and README launch instructions. Run `.venv/bin/python -m medi_cal_analysis --month 2026-09 --language spanish --county "Los Angeles" --output /tmp/module09-spanish-preview.json`. Run `.venv/bin/python scripts/audit_shawn_shih.py` for backend checks.
- **Expected result:** A Phase 3 browser workflow with selectors, sortable comparison/map, synchronized county detail, and readable unavailable-value labels, matching backend metrics.
- **Actual result at the original audited commit:** This checkout provides JSON/DataFrame outputs but no dashboard entry point, rendered comparison page, or county geometry asset. The manager cannot complete the browser workflow here. Checked backend metrics pass.
- **Evidence:** `BUILD_SPEC.md`, line 9, explicitly defers the interface to Phase 3; lines 22-36 specify the desired interactions. `medi_cal_analysis/__main__.py`, `main`, lines 15-42, accepts CLI flags and writes JSON. `medi_cal_analysis/analysis.py`, `get_county_ranking`, lines 96-110, implements the ranking data. The tracked-file inventory has no dashboard implementation. Reproducible evidence is in `scripts/audit_shawn_shih.py` and `outputs/module09_shawn_shih_audit.json`.
- **Likely cause and remaining uncertainty:** Documented unfinished Phase 3 scope, not an established Phase 2 regression. A newer branch/deployment may implement it; none was inspected in this local audit.
- **Requested change:** Implement the specified Phase 3 comparison workflow using the existing backend/local geometry and document its launch command. Retain all counties, separate count/share, display missing as Unavailable, and show coverage. If a newer implementation exists, bring its verified version into the team checkout and record its location instead.
- **Verification check and expected result:** Launch in a browser; default to latest month (2026-09 in this snapshot), Spanish, Los Angeles. Confirm 58 county rows and Los Angeles count 1,129,822, total 3,639,204, share 31.0%. First five counties: Los Angeles, Orange, San Diego, Riverside, San Bernardino. Alpine and Mono Spanish values are unavailable/unranked and last. Overview: observed subtotal 3,505,796, coverage 56/58, complete Spanish count/share unavailable. Change to Mandarin: Los Angeles 49,336 and about 1.4%, coverage 36/58. Change to `unknown`: retain 58 unavailable counties and explain that none can be ranked. Change back to Spanish and verify selection/metrics synchronize. Check count/share sorting, map/table/selector county selection, observed zero and incomplete denominators. Run the audit script and existing tests. If the data intentionally change, record the new commit/hash and update expected values.
- **Implementation commit and verification result:** `d6e8e73b266e9e6e24b8515067771a78677c0bea`. Canonical-backend dashboard, local 58-county map, linked map/table/selector/bar selection, totals/shares, sorting, demographic context, trends, and provenance/coverage labels implemented. All 22 backend tests, 12 dashboard API tests, 22 actual browser checks, and the independent arithmetic audit pass. See [browser verification](outputs/dashboard_browser_verification.md), [verification record](outputs/dashboard_verification.json), and [current backend audit](outputs/dashboard_backend_audit.json). The October report remains unchanged; its no-browser finding applies to the pinned original commit.

## Checks with no change requested

Language-share arithmetic, complete denominators, missing versus zero, and checked
rankings passed. Details belong in Shawn's individual `my-audit.md`; no numerical
defect is claimed.
