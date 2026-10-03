
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_DIR / "by-primary-language-certified-eligibles.csv"
KEY_SOURCE = ["Month of Eligibility", "County", "Language"]
KEY_CLEAN = ["month_of_eligibility", "county", "language"]


def load_source(path: Path) -> pd.DataFrame:
    """Load all fields as nullable strings so source markers remain visible."""
    return pd.read_csv(path, dtype="string", keep_default_na=True, low_memory=False)


def _count_json(series: pd.Series) -> dict[str, int]:
    counts = series.fillna("<MISSING>").value_counts(dropna=False).sort_index()
    return {str(key): int(value) for key, value in counts.items()}


def profile_source(raw: pd.DataFrame, source_path: Path) -> dict[str, Any]:
    total_text = raw["Total Eligibles"].str.strip().str.replace(",", "", regex=False)
    total_numeric = pd.to_numeric(total_text.mask(total_text.eq("")), errors="coerce")
    date_text = raw["Date of Data"].str.strip().replace({"": pd.NA, ".": pd.NA})
    parsed_date = pd.to_datetime(date_text, format="%d%b%Y", errors="coerce")
    parsed_month = pd.to_datetime(
        raw["Month of Eligibility"], format="%Y-%m", errors="coerce"
    )
    meaningful_total = total_text.notna() & total_text.ne("")
    meaningful_date = date_text.notna()

    return {
        "source_file": source_path.name,
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "source_download_date": "2026-10-02",
        "rows": int(len(raw)),
        "columns": int(raw.shape[1]),
        "column_names": raw.columns.tolist(),
        "missing_by_column": {k: int(v) for k, v in raw.isna().sum().items()},
        "exact_duplicate_rows": int(raw.duplicated().sum()),
        "duplicate_key_rows_excess": int(raw.duplicated(KEY_SOURCE).sum()),
        "duplicate_key_rows_involved": int(raw.duplicated(KEY_SOURCE, keep=False).sum()),
        "month_parse_failures": int(parsed_month.isna().sum()),
        "total_parse_failures_meaningful": int(
            (meaningful_total & total_numeric.isna()).sum()
        ),
        "date_parse_failures_meaningful": int(
            (meaningful_date & parsed_date.isna()).sum()
        ),
        "whitespace_only_totals": int(total_text.eq("").fillna(False).sum()),
        "dot_date_markers": int(raw["Date of Data"].str.strip().eq(".").fillna(False).sum()),
        "language_values_with_outer_whitespace": int(
            raw["Language"].ne(raw["Language"].str.strip()).fillna(False).sum()
        ),
        "difference_nonmissing": int(raw["Difference"].notna().sum()),
        "month_min": raw["Month of Eligibility"].min(),
        "month_max": raw["Month of Eligibility"].max(),
        "county_categories": int(raw["County"].nunique(dropna=False)),
        "language_categories": int(raw["Language"].nunique(dropna=False)),
        "county_counts": _count_json(raw["County"]),
        "language_counts": _count_json(raw["Language"]),
        "status_counts": _count_json(raw["Status"]),
        "annotation_code_counts": _count_json(raw["Annotation Code"]),
        "annotation_description_counts": _count_json(raw["Annotation Description"]),
        "invalid_county_rows": int(raw["County"].eq("Invalid County Code").sum()),
        "statewide_rows": int(
            (raw["County"].eq("STATEWIDE") | raw["Language"].eq("STATEWIDE")).sum()
        ),
    }


def clean_data(raw: pd.DataFrame) -> pd.DataFrame:
    """Apply only the rules documented in plan.md; no source row is removed."""
    cleaned = pd.DataFrame(index=raw.index)
    cleaned["source_row_number"] = pd.Series(raw.index + 2, dtype="Int64")
    cleaned["month_of_eligibility"] = pd.to_datetime(
        raw["Month of Eligibility"], format="%Y-%m", errors="coerce"
    )
    cleaned["county"] = raw["County"].str.strip()
    cleaned["language"] = raw["Language"].str.strip()

    total_text = raw["Total Eligibles"].str.strip().str.replace(",", "", regex=False)
    cleaned["total_eligibles"] = pd.to_numeric(
        total_text.mask(total_text.eq("")), errors="coerce"
    ).astype("Int64")

    cleaned["annotation_code"] = raw["Annotation Code"].str.strip()
    cleaned["annotation_description"] = raw["Annotation Description"].str.strip()
    cleaned["status"] = raw["Status"].str.strip()
    cleaned["status_label"] = cleaned["status"].map(
        {"F": "Final", "P": "Preliminary"}
    ).astype("string")

    date_text = raw["Date of Data"].str.strip().replace({"": pd.NA, ".": pd.NA})
    cleaned["date_of_data"] = pd.to_datetime(
        date_text, format="%d%b%Y", errors="coerce"
    )

    cleaned["is_suppressed"] = cleaned["annotation_code"].isin(["1", "2"])
    cleaned["is_statewide"] = cleaned["county"].eq("STATEWIDE") | cleaned[
        "language"
    ].eq("STATEWIDE")
    cleaned["has_valid_county"] = ~cleaned["county"].eq("Invalid County Code")
    cleaned["is_preliminary"] = cleaned["status"].eq("P")
    return cleaned


def validate(raw: pd.DataFrame, cleaned: pd.DataFrame) -> dict[str, Any]:
    """Return evidence and raise AssertionError if a required invariant fails."""
    raw_total_text = raw["Total Eligibles"].str.strip().str.replace(",", "", regex=False)
    raw_total = pd.to_numeric(raw_total_text.mask(raw_total_text.eq("")), errors="coerce")
    clean_total = cleaned["total_eligibles"]

    nonblank_source_total = raw_total_text.notna() & raw_total_text.ne("")
    total_failures = nonblank_source_total & clean_total.isna()
    meaningful_date = raw["Date of Data"].str.strip().replace({"": pd.NA, ".": pd.NA})
    date_failures = meaningful_date.notna() & cleaned["date_of_data"].isna()
    invalid_status = ~cleaned["status"].isin(["F", "P"])
    negative_counts = clean_total.lt(0).fillna(False)
    suppression_mismatch = cleaned["is_suppressed"].ne(clean_total.isna())

    final_rows = cleaned.loc[cleaned["status"].eq("F")]
    latest_final_month = final_rows["month_of_eligibility"].max()
    latest_final = final_rows.loc[
        final_rows["month_of_eligibility"].eq(latest_final_month)
    ]
    latest_final_county = latest_final.loc[
        ~latest_final["is_statewide"] & latest_final["has_valid_county"]
    ]

    numeric = clean_total.dropna()
    q = numeric.quantile([0, 0.25, 0.5, 0.75, 0.95, 0.99, 1])
    result: dict[str, Any] = {
        "rows_before": int(len(raw)),
        "rows_after": int(len(cleaned)),
        "row_difference": int(len(cleaned) - len(raw)),
        "columns_before": int(raw.shape[1]),
        "columns_after": int(cleaned.shape[1]),
        "exact_duplicates_before": int(raw.duplicated().sum()),
        "exact_duplicates_after": int(cleaned.duplicated().sum()),
        "duplicate_keys_before": int(raw.duplicated(KEY_SOURCE).sum()),
        "duplicate_keys_after": int(cleaned.duplicated(KEY_CLEAN).sum()),
        "month_parse_failures": int(cleaned["month_of_eligibility"].isna().sum()),
        "total_parse_failures_meaningful": int(total_failures.sum()),
        "date_parse_failures_meaningful": int(date_failures.sum()),
        "invalid_status_rows": int(invalid_status.sum()),
        "negative_total_rows": int(negative_counts.sum()),
        "suppression_missingness_mismatches": int(suppression_mismatch.sum()),
        "language_values_changed_by_trim": int(
            raw["Language"].ne(cleaned["language"]).fillna(False).sum()
        ),
        "county_values_changed_by_trim": int(
            raw["County"].ne(cleaned["county"]).fillna(False).sum()
        ),
        "missing_total_before": int(raw["Total Eligibles"].isna().sum()),
        "missing_total_after": int(clean_total.isna().sum()),
        "suppressed_rows": int(cleaned["is_suppressed"].sum()),
        "statewide_rows": int(cleaned["is_statewide"].sum()),
        "invalid_county_rows": int((~cleaned["has_valid_county"]).sum()),
        "preliminary_rows": int(cleaned["is_preliminary"].sum()),
        "numeric_record_count": int(numeric.count()),
        "numeric_min": int(numeric.min()),
        "numeric_max": int(numeric.max()),
        "numeric_sum_all_rows_lower_bound": int(numeric.sum()),
        "numeric_quantiles": {str(k): float(v) for k, v in q.items()},
        "raw_numeric_sum": int(raw_total.sum()),
        "latest_final_month": latest_final_month.strftime("%Y-%m"),
        "latest_final_rows": int(len(latest_final)),
        "latest_final_valid_county_rows": int(len(latest_final_county)),
        "latest_final_valid_county_numeric_records": int(
            latest_final_county["total_eligibles"].count()
        ),
        "latest_final_valid_county_sum_lower_bound": int(
            latest_final_county["total_eligibles"].sum()
        ),
        "month_min": cleaned["month_of_eligibility"].min().strftime("%Y-%m"),
        "month_max": cleaned["month_of_eligibility"].max().strftime("%Y-%m"),
        "date_of_data_min": cleaned["date_of_data"].min().strftime("%Y-%m-%d"),
        "date_of_data_max": cleaned["date_of_data"].max().strftime("%Y-%m-%d"),
        "clean_language_categories": int(cleaned["language"].nunique(dropna=False)),
        "clean_county_categories": int(cleaned["county"].nunique(dropna=False)),
    }

    required = {
        "row count preserved": result["row_difference"] == 0,
        "month conversions succeeded": result["month_parse_failures"] == 0,
        "meaningful numeric conversions succeeded": result[
            "total_parse_failures_meaningful"
        ]
        == 0,
        "meaningful date conversions succeeded": result[
            "date_parse_failures_meaningful"
        ]
        == 0,
        "expected key remains unique": result["duplicate_keys_after"] == 0,
        "status values are recognized": result["invalid_status_rows"] == 0,
        "counts are nonnegative": result["negative_total_rows"] == 0,
        "missing counts match suppression": result[
            "suppression_missingness_mismatches"
        ]
        == 0,
        "numeric sum unchanged": result["raw_numeric_sum"]
        == result["numeric_sum_all_rows_lower_bound"],
    }
    result["required_checks"] = required
    failed = [name for name, passed in required.items() if not passed]
    assert not failed, f"Required validation checks failed: {failed}"
    return result


def build_missingness_table(raw: pd.DataFrame, cleaned: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "Month of Eligibility": "month_of_eligibility",
        "County": "county",
        "Language": "language",
        "Total Eligibles": "total_eligibles",
        "Annotation Code": "annotation_code",
        "Annotation Description": "annotation_description",
        "Status": "status",
        "Date of Data": "date_of_data",
    }
    rows = []
    for source, output in mapping.items():
        rows.append(
            {
                "source_column": source,
                "clean_column": output,
                "missing_before": int(raw[source].isna().sum()),
                "missing_after": int(cleaned[output].isna().sum()),
                "explanation": (
                    "Three whitespace-only complementary-suppression cells become missing."
                    if source == "Total Eligibles"
                    else "Publisher '.' markers are standardized to missing."
                    if source == "Date of Data"
                    else "No missingness change."
                ),
            }
        )
    rows.append(
        {
            "source_column": "Difference",
            "clean_column": "<dropped>",
            "missing_before": int(raw["Difference"].isna().sum()),
            "missing_after": pd.NA,
            "explanation": "Dropped because every source value is missing; no rows dropped.",
        }
    )
    return pd.DataFrame(rows)


def build_decision_log() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("Preserve all rows", "Unusual does not mean erroneous.", "Row count before equals after."),
            ("Parse month as YYYY-MM", "Month is a time field, not free text.", "Zero failed meaningful conversions."),
            ("Trim outer text whitespace", "Remove formatting artifacts only.", "2,573 language values change; categories are reviewed."),
            ("Keep Unknown separate from Missing/Unknown", "No data dictionary evidence supports merging them.", "Both categories remain present."),
            ("Convert totals to nullable integers", "Counts require numeric operations while allowing suppression.", "No meaningful conversion failures; all values are whole and nonnegative."),
            ("Do not impute suppressed totals", "Suppression is unknown, not zero.", "Missing totals align exactly with suppression flags."),
            ("Convert '.' date marker to missing", "The marker is not a calendar date.", "Zero failures among meaningful date strings."),
            ("Retain and flag invalid county", "A county cannot be inferred safely.", "Four records retained with has_valid_county=False."),
            ("Retain and flag statewide rows", "They are useful totals but would double count county aggregation.", "200 records retained with is_statewide=True."),
            ("Preserve F/P status and add label", "Preliminary and final releases must be distinguishable.", "All statuses map to Final or Preliminary."),
            ("Drop Difference column only", "It contains no observed values.", "251,535/251,535 values missing; row count unchanged."),
        ],
        columns=["rule", "reason", "check"],
    )


def build_record_checks(raw: pd.DataFrame, cleaned: pd.DataFrame) -> pd.DataFrame:
    """Evaluate five expectations written from the plan before checking output."""
    selections = [
        (
            "regular numeric record",
            raw["Total Eligibles"].notna()
            & raw["Annotation Code"].isna()
            & raw["County"].ne("STATEWIDE"),
            "Count converts to the same integer; row remains unsuppressed.",
        ),
        (
            "small-cell suppression",
            raw["Annotation Code"].eq("1"),
            "Count remains missing and is_suppressed is True.",
        ),
        (
            "complementary suppression",
            raw["Annotation Code"].eq("2"),
            "Whitespace/blank count becomes missing and is_suppressed is True.",
        ),
        (
            "legacy language whitespace",
            raw["Language"].ne(raw["Language"].str.strip()).fillna(False),
            "Language becomes Unknown, remains distinct from Missing/Unknown.",
        ),
        (
            "invalid county code",
            raw["County"].eq("Invalid County Code"),
            "Row is retained and has_valid_county is False.",
        ),
    ]
    rows = []
    for name, mask, expected in selections:
        indices = raw.index[mask]
        assert len(indices), f"No source record found for check: {name}"
        idx = indices[0]
        source = raw.loc[idx]
        actual = cleaned.loc[idx]
        if name == "regular numeric record":
            expected_number = int(str(source["Total Eligibles"]).strip().replace(",", ""))
            passed = (
                actual["total_eligibles"] == expected_number
                and not bool(actual["is_suppressed"])
            )
        elif name in {"small-cell suppression", "complementary suppression"}:
            passed = pd.isna(actual["total_eligibles"]) and bool(actual["is_suppressed"])
        elif name == "legacy language whitespace":
            passed = actual["language"] == "Unknown" and actual["language"] != "Missing/Unknown"
        else:
            passed = actual["county"] == "Invalid County Code" and not bool(
                actual["has_valid_county"]
            )
        rows.append(
            {
                "check": name,
                "source_row_number": int(actual["source_row_number"]),
                "original_count": source["Total Eligibles"],
                "original_count_is_missing": bool(pd.isna(source["Total Eligibles"])),
                "original_count_repr": repr(source["Total Eligibles"]),
                "original_county": source["County"],
                "original_language": source["Language"],
                "original_annotation_code": source["Annotation Code"],
                "expected_before_checking": expected,
                "actual_count": actual["total_eligibles"],
                "actual_count_is_missing": bool(pd.isna(actual["total_eligibles"])),
                "actual_county": actual["county"],
                "actual_language": actual["language"],
                "actual_is_suppressed": bool(actual["is_suppressed"]),
                "actual_has_valid_county": bool(actual["has_valid_county"]),
                "matches_expected": bool(passed),
            }
        )
    checks = pd.DataFrame(rows)
    assert checks["matches_expected"].all(), "At least one record check failed"
    return checks


def build_difficult_sample(raw: pd.DataFrame, cleaned: pd.DataFrame) -> pd.DataFrame:
    """Select difficult cases deterministically, then ordinary comparison rows."""
    raw_total = raw["Total Eligibles"].str.strip()
    groups = [
        cleaned.index[~cleaned["has_valid_county"]],
        cleaned.index[raw_total.eq("").fillna(False)],
        cleaned.index[cleaned["annotation_code"].eq("1")][:10],
        cleaned.index[raw["Language"].ne(raw["Language"].str.strip()).fillna(False)][:10],
        cleaned["total_eligibles"].nlargest(5).index,
        cleaned.index[cleaned["is_preliminary"]][:5],
        cleaned.index[cleaned["status"].eq("F")][:5],
    ]
    ordered: list[int] = []
    for group in groups:
        for idx in group:
            if int(idx) not in ordered:
                ordered.append(int(idx))
    # Add evenly spaced ordinary rows if difficult cases total fewer than 50.
    if len(ordered) < 50:
        step = max(len(cleaned) // (50 - len(ordered)), 1)
        for idx in cleaned.index[::step]:
            if int(idx) not in ordered:
                ordered.append(int(idx))
            if len(ordered) == 50:
                break
    return cleaned.loc[ordered[:50]].copy()


def write_outputs(
    raw: pd.DataFrame,
    cleaned: pd.DataFrame,
    source_profile: dict[str, Any],
    validation: dict[str, Any],
    project_dir: Path,
) -> dict[str, Path]:
    output_dir = project_dir / "output"
    evidence_dir = project_dir / "evidence"
    output_dir.mkdir(exist_ok=True)
    evidence_dir.mkdir(exist_ok=True)

    paths = {
        "cleaned_full": output_dir / "by-primary-language-certified-eligibles-cleaned.csv",
        "sample": project_dir / "cleaned_data_sample.csv",
        "source_profile": evidence_dir / "source_profile.json",
        "validation": evidence_dir / "validation_summary.json",
        "missingness": evidence_dir / "missingness_before_after.csv",
        "decisions": evidence_dir / "cleaning_decision_log.csv",
        "record_checks": evidence_dir / "record_checks.csv",
    }
    cleaned.to_csv(paths["cleaned_full"], index=False, date_format="%Y-%m-%d")
    build_difficult_sample(raw, cleaned).to_csv(
        paths["sample"], index=False, date_format="%Y-%m-%d"
    )
    paths["source_profile"].write_text(
        json.dumps(source_profile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    paths["validation"].write_text(
        json.dumps(validation, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    build_missingness_table(raw, cleaned).to_csv(paths["missingness"], index=False)
    build_decision_log().to_csv(paths["decisions"], index=False)
    build_record_checks(raw, cleaned).to_csv(paths["record_checks"], index=False)
    return paths


def run_pipeline(source_path: Path = DEFAULT_INPUT) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw = load_source(source_path)
    source_profile = profile_source(raw, source_path)
    cleaned = clean_data(raw)
    validation = validate(raw, cleaned)
    paths = write_outputs(raw, cleaned, source_profile, validation, PROJECT_DIR)
    print(f"Rows: {validation['rows_before']:,} -> {validation['rows_after']:,}")
    print(
        "Missing total_eligibles: "
        f"{validation['missing_total_before']:,} source nulls -> "
        f"{validation['missing_total_after']:,} cleaned missing values"
    )
    print(f"All {len(validation['required_checks'])} required checks passed.")
    for label, path in paths.items():
        print(f"{label}: {path.relative_to(PROJECT_DIR)}")
    return cleaned, validation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    run_pipeline(args.input.resolve())


if __name__ == "__main__":
    main()
