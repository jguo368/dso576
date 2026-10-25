"""Independent, read-only checks supporting the Module 9 audit.

Run from the project directory:
    python cleaning/audit_module9_check.py

This deliberately uses only Python's standard-library csv module instead of
the cleaning workflow's pandas functions.  It checks (1) a suppressed source
record remains blank in the source and (2) county-month key coverage between
the language source and the derived table.
"""

from __future__ import annotations

import csv
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
LANGUAGE = PROJECT / "by-primary-language-certified-eligibles.csv"
DERIVED = PROJECT / "medi_cal_merged_county_month.csv"


def main() -> None:
    target = {
        "Month of Eligibility": "2026-08",
        "County": "Alameda",
        "Language": "Hebrew",
    }
    language_keys: set[tuple[str, str]] = set()
    target_rows: list[dict[str, str]] = []

    with LANGUAGE.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            if row["County"] != "STATEWIDE":
                language_keys.add((row["Month of Eligibility"], row["County"]))
            if all(row[column] == value for column, value in target.items()):
                target_rows.append(row)

    if len(target_rows) != 1:
        raise AssertionError(f"Expected exactly one target record; found {len(target_rows)}")
    target_row = target_rows[0]
    if target_row["Total Eligibles"].strip() != "":
        raise AssertionError("The selected suppressed source count is not blank.")
    if target_row["Annotation Description"] != "Cell suppressed for small numbers":
        raise AssertionError("The selected source record does not have the expected suppression annotation.")

    with DERIVED.open(newline="", encoding="utf-8-sig") as file:
        derived_keys = {(row["month_of_eligibility"], row["county"]) for row in csv.DictReader(file)}

    source_only = language_keys - derived_keys
    derived_only = derived_keys - language_keys
    if source_only or derived_only:
        raise AssertionError(
            f"County-month key coverage failed: source_only={len(source_only)}, derived_only={len(derived_only)}"
        )

    print("Suppression check: PASS")
    print("  2026-08 | Alameda | Hebrew has a blank count and the source annotation: "
          "Cell suppressed for small numbers.")
    print("County-month coverage check: PASS")
    print(f"  source non-statewide unique keys = {len(language_keys):,}")
    print(f"  derived unique keys = {len(derived_keys):,}")
    print("  source_only = 0; derived_only = 0")


if __name__ == "__main__":
    main()
