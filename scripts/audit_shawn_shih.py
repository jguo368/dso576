"""Reproduce Shawn Shih's Module 9 audit without modifying application inputs.

Run from project/: .venv/bin/python scripts/audit_shawn_shih.py
The CSV/Decimal oracle does not call backend preparation or metric helpers.
Synthetic inputs are new audit cases, independent of the existing test fixtures.
"""

import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from pandas.testing import assert_frame_equal

import medi_cal_analysis as app


def number(text):
    return None if text.strip() == "" else Decimal(text)


def check_equal(actual, expected):
    if expected is None:
        assert pd.isna(actual), (actual, expected)
    else:
        assert not pd.isna(actual), (actual, expected)
        assert math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12), (actual, expected)


def audit_snapshot(data, rows, month, language):
    raw = [r for r in rows if r["month_of_eligibility"] == month]
    assert len(raw) == 58 and len({r["county"] for r in raw}) == 58
    expected = {}
    for row in raw:
        count = number(row[f"language__{language}"])
        # Explicitly enumerate the eight disjoint age/sex cells in the spec.
        cells = [number(row[f"age_sex__{age}__{sex}"])
                 for age in ("age_00_18", "age_19_44", "age_45_64", "age_65_plus")
                 for sex in ("female", "male")]
        complete = row["county_total_is_complete"].lower() == "true"
        total = sum(cells, Decimal(0)) if all(c is not None for c in cells) else None
        assert complete == (total is not None)
        check_equal(float(row["county_total_eligibles"]) if row["county_total_eligibles"] else pd.NA, total)
        share = count / total if count is not None and total is not None and total > 0 else None
        expected[row["county"]] = (count, total, share)

    ranked = app.get_county_ranking(data, month, language)
    order = sorted(expected, key=lambda c: (expected[c][0] is None, -(expected[c][0] or Decimal(0)), c))
    assert ranked["county"].tolist() == order
    for actual in ranked.to_dict("records"):
        count, total, share = expected[actual["county"]]
        check_equal(actual["selected_language_count"], count)
        check_equal(actual["county_total_eligibles"], total)
        check_equal(actual["language_share"], share)
        rank = None if count is None else 1 + sum(v[0] is not None and v[0] > count for v in expected.values())
        check_equal(actual["rank"], rank)
        if share is not None:
            assert Decimal(0) <= share <= Decimal(1)

    summary = app.get_month_summary(data, month, language).iloc[0]
    observed = [v[0] for v in expected.values() if v[0] is not None]
    subtotal = sum(observed, Decimal(0)) if observed else None
    check_equal(summary["observed_language_count"], subtotal)
    assert summary["language_count_available_counties"] == len(observed)
    assert summary["language_share_available_counties"] == sum(v[2] is not None for v in expected.values())
    check_equal(summary["selected_language_count"], subtotal if len(observed) == 58 else None)
    totals = [v[1] for v in expected.values()]
    total = sum(totals, Decimal(0)) if all(v is not None for v in totals) else None
    check_equal(summary["county_total_eligibles"], total)
    statewide_share = subtotal / total if len(observed) == 58 and total is not None and total > 0 else None
    check_equal(summary["language_share"], statewide_share)
    la = expected["Los Angeles"]
    return {
        "month": month, "language": language, "county_rows": len(raw),
        "observed_counties": len(observed), "observed_subtotal": str(subtotal) if subtotal is not None else None,
        "missing_count_counties": sorted(c for c, v in expected.items() if v[0] is None),
        "statewide_share": str(statewide_share) if statewide_share is not None else None,
        "los_angeles": {k: str(v) if v is not None else None for k, v in zip(("count", "total", "share"), la)},
        "first_five_counties": order[:5],
        "result": "PASS: all 58 counts, denominators, shares, ranks, order, and overview checked against CSV oracle",
    }


def audit_small_cases():
    age_cells = [f"age_sex__{age}__{sex}"
                 for age in ("age_00_18", "age_19_44", "age_45_64", "age_65_plus")
                 for sex in ("female", "male")]
    cases = [
        ("Alameda", 25, 100, "normal", .25),
        ("Alpine", 0, 100, "observed_zero", 0),
        ("Amador", None, 100, "missing_count", None),
        ("Butte", 25, 100, "incomplete_total", None),
        ("Colusa", 0, 0, "zero_total", None),
        ("Del Norte", 25, 100, "tie", .25),
        ("Fresno", 25, 200, "different_denominator", .125),
    ]
    rows = []
    for county, count, total, case, expected in cases:
        row = {"county": county, "month_of_eligibility": "2026-09", "status": "P",
               "date_of_data": "2026-09-10", "county_total_eligibles": total,
               "county_total_is_complete": case != "incomplete_total",
               "language__spanish": count, "language__mandarin": 0,
               "language_suppressed_cells": int(count is None),
               "age_sex_suppressed_cells": int(case == "incomplete_total"),
               "race_age_suppressed_cells": 0}
        # Seven cells of 10 and one of 30 sum to 100; 20*7+60=200.
        row.update({c: 0 if total == 0 else total // 10 for c in age_cells})
        row[age_cells[-1]] = total - sum(row[c] for c in age_cells[:-1])
        if case == "incomplete_total":
            row[age_cells[0]] = None  # A supplied partial total cannot be a denominator.
        row.update({f"race_age__{age}__{race}": 0
                    for age in ("age_00_18", "age_19_44", "age_45_64", "age_65_plus")
                    for race in ("ai_an", "asian", "black", "hispanic", "not_reported", "white")})
        rows.append(row)
    data = app.prepare_data(pd.DataFrame(rows))
    actual = app.get_county_metrics(data, "2026-09", "spanish").set_index("county")
    reasons = {"Amador": "missing_language_count", "Butte": "incomplete_county_total", "Colusa": "nonpositive_county_total"}
    result = []
    for county, count, total, case, expected in cases:
        check_equal(actual.loc[county, "language_share"], expected)
        if county in reasons:
            assert actual.loc[county, "language_share_unavailable_reason"] == reasons[county]
        result.append({"case": case, "county": county, "input_count": count, "input_total": total,
                       "expected_share": expected, "actual_share": None if pd.isna(actual.loc[county, "language_share"]) else float(actual.loc[county, "language_share"]), "result": "PASS"})
    check_equal(actual.loc["Butte", "county_total_eligibles"], None)
    ranked = app.get_county_ranking(data, "2026-09", "spanish")
    assert ranked["county"].tolist() == ["Alameda", "Butte", "Del Norte", "Fresno", "Alpine", "Colusa", "Amador"]
    assert ranked["rank"].dropna().tolist() == [1, 1, 1, 1, 5, 5]
    assert pd.isna(ranked.iloc[-1]["rank"])
    return result


def main():
    path = app.DEFAULT_DATA_PATH
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    data = app.load_data()
    original = data.copy(deep=True)
    months = sorted({r["month_of_eligibility"] for r in rows})
    checks = [audit_snapshot(data, rows, month, language) for month, language in (
        (months[0], "spanish"), (months[-1], "spanish"),
        (months[-1], "mandarin"), (months[-1], "unknown"))]
    assert_frame_equal(data, original)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    # Repeating a prior selection after switching must return the same values.
    assert_frame_equal(app.get_county_ranking(data, months[-1], "spanish"),
                       app.get_county_ranking(original, months[-1], "spanish"))
    result = {
        "checked_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_file": str(path.relative_to(ROOT)), "source_sha256": before,
        "source_shape": [len(rows), len(rows[0])],
        "snapshot_checks": checks, "synthetic_cases": audit_small_cases(),
        "nonmutation": "PASS: prepared input and source CSV unchanged",
        "interface_scope": "No browser test: this checkout is the documented Phase 2 backend; Phase 3 interface is absent.",
        "result": "PASS",
    }
    output = ROOT / "outputs/module09_shawn_shih_audit.json"
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
