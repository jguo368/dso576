"""Independent Module 9 audit for the month filter and county total.

Run from the repository root:

    PYTHONDONTWRITEBYTECODE=1 python3.13 audits/jonathan_module9_check.py

The check reads a pinned team commit through Git, so it does not depend on the
files checked out on Jonathan's individual branch. It does not modify the team
data or backend.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile

import pandas as pd


if sys.version_info < (3, 10):
    raise SystemExit(
        "This audit loads the team backend, which uses Python 3.10+ syntax. "
        "Run it with the project's Python 3.11+ environment (python3.13 is "
        "available on the auditor's machine)."
    )


ROOT = Path(__file__).resolve().parents[1]
COMMIT = "3afb82b57ca9863a921eae805541846c4d561e46"
CSV_PATH = "dso576/project/medi_cal_merged_county_month.csv"
COUNTY = "Los Angeles"
LANGUAGE = "spanish"
MONTHS = ("2026-08", "2026-09")
AGE_SEX_PREFIX = "age_sex__"


def git_blob(path: str) -> bytes:
    """Read one file from the pinned commit without changing branches."""
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{COMMIT}:{path}"]
    )


passed = 0
failed = 0


def check(label: str, condition: object) -> None:
    global passed, failed
    if bool(condition):
        passed += 1
        print(f"PASS: {label}")
    else:
        failed += 1
        print(f"FAIL: {label}")


csv_bytes = git_blob(CSV_PATH)
raw = pd.read_csv(BytesIO(csv_bytes))
age_sex_columns = [column for column in raw if column.startswith(AGE_SEX_PREFIX)]

print("Auditor: Jonathan Guo")
print("Scope: month-dependent backend outputs and Los Angeles county total")
print("Dashboard limitation: no Phase 3 dashboard files exist in the pinned commit")
print("Commit:", COMMIT)
print("Canonical CSV:", CSV_PATH)
print("Canonical SHA256:", hashlib.sha256(csv_bytes).hexdigest())
print("Python:", sys.version.split()[0], "pandas:", pd.__version__)
print("Age/sex component columns:", age_sex_columns)

check("exactly eight age/sex components found", len(age_sex_columns) == 8)

# This is the independent calculation. It reads the canonical CSV directly and
# sums the eight age/sex cells with Python; it does not call a project metric or
# summary function.
expected: dict[str, int] = {}
stored: dict[str, int] = {}
components: dict[str, list[int]] = {}
for month in MONTHS:
    rows = raw.loc[
        raw["month_of_eligibility"].eq(month) & raw["county"].eq(COUNTY)
    ]
    check(f"{month} has exactly one Los Angeles row", len(rows) == 1)
    row = rows.iloc[0]
    values = [int(row[column]) for column in age_sex_columns]
    components[month] = values
    expected[month] = sum(values)
    stored[month] = int(row["county_total_eligibles"])
    check(f"{month} all eight age/sex cells are observed", all(pd.notna(row[column]) for column in age_sex_columns))
    check(f"{month} stored completeness flag is true", bool(row["county_total_is_complete"]))
    check(f"{month} stored county total equals independent sum", stored[month] == expected[month])

print("\nINDEPENDENT COUNTY-TOTAL CALCULATION")
for month in MONTHS:
    print(
        month,
        "components=",
        components[month],
        "independent_sum=",
        expected[month],
        "stored_total=",
        stored[month],
    )
print("change_2026-09_minus_2026-08=", expected["2026-09"] - expected["2026-08"])

check("August independent total is 3,720,277", expected["2026-08"] == 3_720_277)
check("September independent total is 3,639,204", expected["2026-09"] == 3_639_204)
check(
    "month change is a decrease of 81,073",
    expected["2026-09"] - expected["2026-08"] == -81_073,
)

# Load the project backend from the same pinned commit in an isolated temporary
# directory, then compare its month-filtered outputs with the calculation above.
with tempfile.TemporaryDirectory(prefix=".module9-jonathan-", dir=ROOT) as directory:
    snapshot = Path(directory)
    tracked = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", COMMIT],
        text=True,
    ).splitlines()
    selected_paths = [
        path
        for path in tracked
        if path.startswith(("medi_cal_analysis/", "tests/")) or path == CSV_PATH
    ]
    for path in selected_paths:
        target = snapshot / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git_blob(path))

    sys.path.insert(0, str(snapshot))
    import medi_cal_analysis as api

    data = api.load_data(snapshot / CSV_PATH)
    original = data.copy(deep=True)

    backend_totals: dict[str, int] = {}
    for month in MONTHS:
        summary = api.get_county_summary(data, month, LANGUAGE, COUNTY)
        backend_totals[month] = int(summary.iloc[0]["county_total_eligibles"])
        check(f"{month} county detail returns selected month", summary["month_of_eligibility"].eq(month).all())
        check(f"{month} county detail total matches independent sum", backend_totals[month] == expected[month])

        outputs = {
            "map": api.get_map_data(data, month, LANGUAGE),
            "ranking": api.get_county_ranking(data, month, LANGUAGE),
            "overview": api.get_month_summary(data, month, LANGUAGE),
            "age/sex": api.get_age_sex_summary(data, month, COUNTY),
            "race/ethnicity": api.get_race_ethnicity_summary(data, month, COUNTY),
        }
        for name, frame in outputs.items():
            check(
                f"{month} {name} output contains only selected month",
                frame["month_of_eligibility"].eq(month).all(),
            )

    check("county detail changes after month changes", backend_totals[MONTHS[0]] != backend_totals[MONTHS[1]])
    check("backend calls do not mutate loaded data", data.equals(original))

    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=snapshot,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print("\nEXISTING TEST SUITE")
    print(result.stdout)
    check("existing team test suite exits successfully", result.returncode == 0)

print(f"\nINDIVIDUAL CHECKS: {passed} PASS, {failed} FAIL")
raise SystemExit(1 if failed else 0)
