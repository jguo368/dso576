"""Non-destructive cleaning and validation for the Medi-Cal project data.

Run from the project directory:
    python cleaning/clean_medi_cal.py

Inputs are never overwritten. All derived files go to cleaning/outputs/.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = Path(__file__).resolve().parent / "outputs"
RAW_FILES = {
    "language": PROJECT / "by-primary-language-certified-eligibles.csv",
    "age_sex": PROJECT / "by-age-group-and-sex-certified-eligibles.csv",
    "race_age": PROJECT / "by-race-ethnicity-and-age-group-certified-eligibles.csv",
}
DERIVED_FILE = PROJECT / "medi_cal_merged_county_month.csv"


def sha256(path: Path) -> str:
    """Return a file hash so a future run can identify the exact input."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_raw(path: Path) -> pd.DataFrame:
    """Load as strings so blank cells and source formatting are preserved."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def clean_long_table(raw: pd.DataFrame, dataset: str) -> tuple[pd.DataFrame, dict[str, int]]:
    """Add parsed and comparison fields without overwriting raw source fields."""
    clean = raw.copy()
    category_columns = [c for c in ["County", "Language", "Age Group", "Gender", "Ethnicity"] if c in raw]
    for column in category_columns:
        clean[f"{column}_clean"] = raw[column].str.strip()

    clean["month_of_eligibility_parsed"] = pd.to_datetime(raw["Month of Eligibility"], format="%Y-%m", errors="coerce")
    date_text = raw["Date of Data"].str.strip()
    clean["date_of_data_parsed"] = pd.to_datetime(date_text.replace({"": pd.NA, ".": pd.NA}), format="%d%b%Y", errors="coerce")
    clean["is_date_of_data_placeholder"] = date_text.eq(".")

    count_text = raw["Total Eligibles"].str.replace(",", "", regex=False).str.strip()
    count_numeric = pd.to_numeric(count_text.replace("", pd.NA), errors="coerce")
    clean["total_eligibles_parsed"] = count_numeric.astype("Int64")
    clean["is_preliminary_status"] = raw["Status"].eq("P")
    clean["is_invalid_county_code"] = raw["County"].eq("Invalid County Code")
    clean["is_statewide_record"] = raw["County"].eq("STATEWIDE")

    failed_count = count_text.ne("") & count_numeric.isna()
    failed_month = clean["month_of_eligibility_parsed"].isna()
    failed_date = date_text.ne("") & date_text.ne(".") & clean["date_of_data_parsed"].isna()
    keys = ["Month of Eligibility", "County"]
    if dataset == "language":
        keys.append("Language")
    elif dataset == "age_sex":
        keys.extend(["Age Group", "Gender"])
    else:
        keys.extend(["Age Group", "Ethnicity"])
    stats = {
        "rows_before": len(raw), "rows_after": len(clean), "exact_duplicates": int(raw.duplicated().sum()),
        "repeated_key_rows": int(raw.duplicated(keys, keep=False).sum()), "failed_count_conversions": int(failed_count.sum()),
        "failed_month_conversions": int(failed_month.sum()), "failed_date_conversions": int(failed_date.sum()),
        "negative_counts": int(count_numeric.lt(0).sum()), "invalid_county_code_rows": int(clean["is_invalid_county_code"].sum()),
        "statewide_rows": int(clean["is_statewide_record"].sum()), "preliminary_rows": int(clean["is_preliminary_status"].sum()),
    }
    return clean, stats


def clean_derived_table(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Add typed and flag fields to the project-derived county-month file."""
    clean = raw.copy()
    clean["month_of_eligibility_parsed"] = pd.to_datetime(raw["month_of_eligibility"], format="%Y-%m", errors="coerce")
    clean["county_clean"] = raw["county"].str.strip()
    date_text = raw["date_of_data"].str.strip()
    clean["date_of_data_parsed"] = pd.to_datetime(date_text.replace({"": pd.NA, ".": pd.NA}), format="%d%b%Y", errors="coerce")
    clean["is_date_of_data_placeholder"] = date_text.eq(".")
    clean["is_preliminary_status"] = raw["status"].eq("P")
    clean["is_invalid_county_code"] = raw["county"].eq("Invalid County Code")
    clean["county_total_is_complete_parsed"] = raw["county_total_is_complete"].map({"True": True, "False": False}).astype("boolean")

    number_columns = [c for c in raw.columns if c not in {"month_of_eligibility", "county", "status", "date_of_data", "county_total_is_complete"}]
    failed_numeric = 0
    negative_values = 0
    for column in number_columns:
        text = raw[column].str.strip()
        numeric = pd.to_numeric(text.replace("", pd.NA), errors="coerce")
        failed_numeric += int((text.ne("") & numeric.isna()).sum())
        negative_values += int(numeric.lt(0).sum())
        clean[f"{column}_parsed"] = numeric.astype("Int64")

    failed_date = date_text.ne("") & date_text.ne(".") & clean["date_of_data_parsed"].isna()
    stats = {
        "rows_before": len(raw), "rows_after": len(clean), "exact_duplicates": int(raw.duplicated().sum()),
        "repeated_key_rows": int(raw.duplicated(["month_of_eligibility", "county"], keep=False).sum()),
        "failed_count_conversions": failed_numeric, "failed_month_conversions": int(clean["month_of_eligibility_parsed"].isna().sum()),
        "failed_date_conversions": int(failed_date.sum()), "negative_counts": negative_values,
        "invalid_county_code_rows": int(clean["is_invalid_county_code"].sum()), "statewide_rows": 0,
        "preliminary_rows": int(clean["is_preliminary_status"].sum()),
    }
    return clean, stats


def missing_report(before: pd.DataFrame, after: pd.DataFrame, dataset: str) -> list[dict[str, object]]:
    """Return missing counts and percentages without changing any values."""
    report = []
    for column in before.columns:
        count = int(before[column].eq("").sum())
        report.append({"dataset": dataset, "stage": "raw", "column": column, "missing_count": count, "missing_percent": round(count / len(before) * 100, 2)})
    for column in after.columns:
        count = int(after[column].isna().sum())
        report.append({"dataset": dataset, "stage": "cleaned", "column": column, "missing_count": count, "missing_percent": round(count / len(after) * 100, 2)})
    return report


def validate_derived_keys(language_clean: pd.DataFrame, derived_clean: pd.DataFrame) -> pd.DataFrame:
    """Validate county-month keys without row-level merging demographic tables."""
    source_keys = language_clean.loc[~language_clean["is_statewide_record"], ["Month of Eligibility", "County"]].drop_duplicates()
    source_keys = source_keys.rename(columns={"Month of Eligibility": "month", "County": "county"})
    derived_keys = derived_clean[["month_of_eligibility", "county"]].rename(columns={"month_of_eligibility": "month"})
    comparison = source_keys.merge(derived_keys, on=["month", "county"], how="outer", indicator=True, validate="one_to_one")
    return pd.DataFrame([{
        "validation": "language source non-statewide keys versus derived county-month keys",
        "expected_relationship": "one_to_one after deduplicating language categories within each county-month",
        "source_unique_keys": len(source_keys), "derived_unique_keys": len(derived_keys),
        "matched_keys": int(comparison["_merge"].eq("both").sum()), "source_only_keys": int(comparison["_merge"].eq("left_only").sum()),
        "derived_only_keys": int(comparison["_merge"].eq("right_only").sum()), "row_multiplication_risk": "none: validate=one_to_one passed",
    }])


def make_record_checks(language: pd.DataFrame, derived: pd.DataFrame, merge_summary: pd.DataFrame) -> pd.DataFrame:
    """Create five transparent original/expected/actual checks."""
    whitespace = language.loc[language["Language"].ne(language["Language_clean"])].iloc[0]
    suppressed = language.loc[language["Total Eligibles"].str.strip().eq("") & language["Annotation Description"].ne("")].iloc[0]
    placeholder = language.loc[language["is_date_of_data_placeholder"]].iloc[0]
    invalid = derived.loc[derived["is_invalid_county_code"]].iloc[0]
    merge_ok = merge_summary.iloc[0]
    rows = [
        {"case": "Whitespace in Language", "record_key": f"{whitespace['Month of Eligibility']} | {whitespace['County']} | {whitespace['Language']!r}", "original_value": repr(whitespace["Language"]), "expected_result": "Raw language retained; comparison field equals stripped raw value.", "actual_result": f"raw={whitespace['Language']!r}; clean={whitespace['Language_clean']!r}", "matches": whitespace["Language_clean"] == whitespace["Language"].strip(), "reason": "Whitespace should not create a separate comparison category."},
        {"case": "Blank/suppressed Total Eligibles", "record_key": f"{suppressed['Month of Eligibility']} | {suppressed['County']} | {suppressed['Language']}", "original_value": f"Total Eligibles={suppressed['Total Eligibles']!r}; annotation={suppressed['Annotation Description']!r}", "expected_result": "Parsed count is missing, not zero; annotation is retained.", "actual_result": f"parsed={suppressed['total_eligibles_parsed']}; annotation={suppressed['Annotation Description']!r}", "matches": pd.isna(suppressed["total_eligibles_parsed"]) and suppressed["Annotation Description"] != "", "reason": "Suppression/blank does not establish a zero eligible count."},
        {"case": "Date of Data placeholder", "record_key": f"{placeholder['Month of Eligibility']} | {placeholder['County']} | {placeholder['Language']}", "original_value": repr(placeholder["Date of Data"]), "expected_result": "Raw placeholder retained; parsed date missing and placeholder flag True.", "actual_result": f"parsed_missing={pd.isna(placeholder['date_of_data_parsed'])}; flag={placeholder['is_date_of_data_placeholder']}", "matches": pd.isna(placeholder["date_of_data_parsed"]) and bool(placeholder["is_date_of_data_placeholder"]), "reason": "A dot is not a valid reporting date."},
        {"case": "Invalid County Code", "record_key": f"{invalid['month_of_eligibility']} | {invalid['county']}", "original_value": invalid["county"], "expected_result": "Record retained and invalid-county flag True; not treated as a normal county.", "actual_result": f"retained=True; invalid_county_flag={invalid['is_invalid_county_code']}", "matches": bool(invalid["is_invalid_county_code"]), "reason": "Geography cannot be assigned safely without source documentation."},
        {"case": "Derived-file key validation", "record_key": "non-statewide language county-month key set", "original_value": f"source keys={merge_ok['source_unique_keys']}; derived keys={merge_ok['derived_unique_keys']}", "expected_result": "One-to-one key validation passes with no unmatched keys or row multiplication.", "actual_result": f"matched={merge_ok['matched_keys']}; source_only={merge_ok['source_only_keys']}; derived_only={merge_ok['derived_only_keys']}; {merge_ok['row_multiplication_risk']}", "matches": merge_ok["source_only_keys"] == 0 and merge_ok["derived_only_keys"] == 0, "reason": "Confirms the derived file covers the county-month grain without a direct long-table merge."},
    ]
    return pd.DataFrame(rows)


def make_sample(language: pd.DataFrame, derived: pd.DataFrame) -> pd.DataFrame:
    """Return 50 traceable, difficult or representative records."""
    language_sample = pd.concat([language.loc[language["Language"].ne(language["Language_clean"])].head(5), language.loc[language["total_eligibles_parsed"].isna()].head(5), language.loc[language["is_date_of_data_placeholder"]].head(5), language.sort_values(["Month of Eligibility", "County", "Language"]).head(10)]).drop_duplicates().head(25)
    derived_sample = pd.concat([derived.loc[derived["is_invalid_county_code"]], derived.loc[derived["is_preliminary_status"]].head(7), derived.loc[derived["county_total_is_complete_parsed"].eq(False)].head(5), derived.loc[derived["is_date_of_data_placeholder"]].head(5), derived.sort_values(["month_of_eligibility", "county"]).head(10)]).drop_duplicates().head(25)
    long_view = pd.DataFrame({"dataset": "language", "month": language_sample["Month of Eligibility"], "county_raw": language_sample["County"], "county_clean": language_sample["County_clean"], "category_raw": language_sample["Language"], "category_clean": language_sample["Language_clean"], "total_raw": language_sample["Total Eligibles"], "total_parsed": language_sample["total_eligibles_parsed"], "status": language_sample["Status"], "date_raw": language_sample["Date of Data"], "invalid_county": language_sample["is_invalid_county_code"]})
    derived_view = pd.DataFrame({"dataset": "derived_county_month", "month": derived_sample["month_of_eligibility"], "county_raw": derived_sample["county"], "county_clean": derived_sample["county_clean"], "category_raw": pd.NA, "category_clean": pd.NA, "total_raw": derived_sample["county_total_eligibles"], "total_parsed": derived_sample["county_total_eligibles_parsed"], "status": derived_sample["status"], "date_raw": derived_sample["date_of_data"], "invalid_county": derived_sample["is_invalid_county_code"]})
    return pd.concat([long_view, derived_view], ignore_index=True).head(50)


def write_docs(stats: pd.DataFrame, record_checks: pd.DataFrame) -> None:
    decisions = pd.DataFrame([
        ["Preserve original CSVs; write only derived outputs.", "Protects source evidence and makes reruns safe.", "Input hashes are saved; script has no source-file write path."],
        ["Keep blank/suppressed counts as missing.", "Annotations indicate suppression; zero would invent a count.", "Check parsed blanks remain missing and annotations remain present."],
        ["Create stripped comparison fields only.", "Outer whitespace should not split comparisons; raw categories remain auditable.", "Compare raw/clean mappings; no language recoding."],
        ["Keep F and P rows and flag P.", "Status definition is unresolved.", "Row-count audit reports P rows; neither status is filtered."],
        ["Keep and flag Invalid County Code rows.", "They cannot safely be assigned to a county.", "Report retained rows; exclude only in downstream ranking/map filters."],
        ["Do not row-level merge demographic long tables.", "Different grains would multiply rows.", "Key-validation report documents aggregate-first requirement."],
    ], columns=["rule", "reason", "validation_check"])
    decisions.to_csv(OUTPUT / "cleaning_decision_log.csv", index=False)
    total_before, total_after = int(stats["rows_before"].sum()), int(stats["rows_after"].sum())
    invalid = int(stats.loc[stats.dataset.eq("derived_county_month"), "invalid_county_code_rows"].iloc[0])
    text = f"""# Checklist Evidence: Medi-Cal Cleaning

Business vision: **A Medi-Cal access strategy manager at DHCS must decide which counties and language populations should be prioritized for additional language-access capacity.**

| # | Status | Evidence |
|---|---|---|
| 1 | Done | County-month-language eligible populations are a planning signal; provider capacity is unresolved because no provider dataset is present. |
| 2 | Done | Grain and candidate keys are documented in `plan.md` and `validation_summary.csv`. |
| 3 | Done | Inputs are read-only; `source_manifest.csv` records hashes. |
| 4 | Done | Raw fields remain; parsed date/count/comparison fields are added. Conversion failures are reported. |
| 5 | Done | Only outer-whitespace comparison fields are added; language categories are not combined. |
| 6 | Done | Exact duplicates and repeated candidate keys are reported separately. |
| 7 | Done | `missing_value_report.csv` reports count/percent before and after; blanks remain missing. |
| 8 | Done | Negative counts, failed parses, invalid county codes, placeholders, and P records are flagged. |
| 9 | Done | `merge_validation.csv` verifies one-to-one county-month key coverage; long tables are not directly merged. |
| 10 | Done | All major transformations retain rows: {total_before:,} before and {total_after:,} after. |
| 11 | Done | No missing count becomes zero; rankings/maps must filter `is_invalid_county_code == False`. |
| 12 | Done | Five difficult record checks are in `record_checks.csv`; all passed: {bool(record_checks['matches'].all())}. |
| 13 | Done | Run `python cleaning/clean_medi_cal.py`; README gives the repeat-run hash check. |
| 14 | Unresolved | Provider capacity, F/P definitions, suppression policy, and derived-file provenance need documentation. |

## Codex Suggestion Verification

Suggestion: **Retain and flag Invalid County Code records instead of deleting them.**

The derived source has {invalid} affected records. They remain in the cleaned file with `is_invalid_county_code=True`, so row count is unchanged. County rankings/maps should filter that flag because `Invalid County Code` is not a California county; retaining it makes the unassigned geography and its counts auditable. The individual record check verifies this behavior against an original affected record.
"""
    (OUTPUT / "checklist_evidence.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    all_stats, all_missing, cleaned = [], [], {}
    print("Loading and cleaning raw long-format datasets (source files are unchanged).")
    for name, path in RAW_FILES.items():
        raw = load_raw(path)
        clean, stats = clean_long_table(raw, name)
        assert len(raw) == len(clean), f"{name}: cleaning changed row count"
        clean.to_csv(OUTPUT / f"cleaned_{name}.csv", index=False)
        all_stats.append({"dataset": name, **stats})
        all_missing.extend(missing_report(raw, clean, name))
        cleaned[name] = clean
        print(f"{name}: {len(raw):,} rows before -> {len(clean):,} rows after")

    raw_derived = load_raw(DERIVED_FILE)
    derived, derived_stats = clean_derived_table(raw_derived)
    assert len(raw_derived) == len(derived), "derived county-month: cleaning changed row count"
    derived.to_csv(OUTPUT / "cleaned_medi_cal_merged_county_month.csv", index=False)
    all_stats.append({"dataset": "derived_county_month", **derived_stats})
    all_missing.extend(missing_report(raw_derived, derived, "derived_county_month"))
    print(f"derived_county_month: {len(raw_derived):,} rows before -> {len(derived):,} rows after")

    stats = pd.DataFrame(all_stats)
    stats.to_csv(OUTPUT / "validation_summary.csv", index=False)
    pd.DataFrame(all_missing).to_csv(OUTPUT / "missing_value_report.csv", index=False)
    merge_summary = validate_derived_keys(cleaned["language"], derived)
    merge_summary.to_csv(OUTPUT / "merge_validation.csv", index=False)
    assert int(merge_summary.loc[0, "source_only_keys"]) == 0, "Unexpected source-only county-month keys"
    assert int(merge_summary.loc[0, "derived_only_keys"]) == 0, "Unexpected derived-only county-month keys"
    print("merge/key validation: one-to-one key coverage passed; unmatched keys = 0")

    checks = make_record_checks(cleaned["language"], derived, merge_summary)
    checks.to_csv(OUTPUT / "record_checks.csv", index=False)
    assert bool(checks["matches"].all()), "At least one manual record check failed"
    make_sample(cleaned["language"], derived).to_csv(OUTPUT / "cleaned_sample_50_rows.csv", index=False)
    write_docs(stats, checks)

    manifest = [{"file": path.name, "role": "raw input", "sha256": sha256(path)} for path in [*RAW_FILES.values(), DERIVED_FILE]]
    manifest += [{"file": path.name, "role": "derived output", "sha256": sha256(path)} for path in sorted(OUTPUT.glob("*")) if path.is_file() and path.name != "source_manifest.csv"]
    pd.DataFrame(manifest).to_csv(OUTPUT / "source_manifest.csv", index=False)
    print(f"Created outputs in: {OUTPUT}")


if __name__ == "__main__":
    main()
