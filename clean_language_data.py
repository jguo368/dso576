"""Clean DHCS certified-eligible counts by county, month, and language."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "t5_eligibility_by_language_201001_202609.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "outputs" / "language_cleaning"

SOURCE_COLUMNS = [
    "Month of Eligibility",
    "County",
    "Language",
    "Total Eligibles",
    "Annotation Code",
    "Annotation Description",
    "Status",
    "Date of Data",
    "Difference",
]
SPECIAL_COUNTIES = {"STATEWIDE", "Invalid County Code"}

# Stable join keys for California county boundary files. Keep this explicit
# dimension so a dashboard never needs to join geometries on display text.
COUNTY_FIPS = {
    "Alameda": "06001", "Alpine": "06003", "Amador": "06005", "Butte": "06007",
    "Calaveras": "06009", "Colusa": "06011", "Contra Costa": "06013",
    "Del Norte": "06015", "El Dorado": "06017", "Fresno": "06019", "Glenn": "06021",
    "Humboldt": "06023", "Imperial": "06025", "Inyo": "06027", "Kern": "06029",
    "Kings": "06031", "Lake": "06033", "Lassen": "06035", "Los Angeles": "06037",
    "Madera": "06039", "Marin": "06041", "Mariposa": "06043", "Mendocino": "06045",
    "Merced": "06047", "Modoc": "06049", "Mono": "06051", "Monterey": "06053",
    "Napa": "06055", "Nevada": "06057", "Orange": "06059", "Placer": "06061",
    "Plumas": "06063", "Riverside": "06065", "Sacramento": "06067", "San Benito": "06069",
    "San Bernardino": "06071", "San Diego": "06073", "San Francisco": "06075",
    "San Joaquin": "06077", "San Luis Obispo": "06079", "San Mateo": "06081",
    "Santa Barbara": "06083", "Santa Clara": "06085", "Santa Cruz": "06087",
    "Shasta": "06089", "Sierra": "06091", "Siskiyou": "06093", "Solano": "06095",
    "Sonoma": "06097", "Stanislaus": "06099", "Sutter": "06101", "Tehama": "06103",
    "Trinity": "06105", "Tulare": "06107", "Tuolumne": "06109", "Ventura": "06111",
    "Yolo": "06113", "Yuba": "06115",
}


def _json_record(record: pd.Series) -> dict[str, object]:
    result: dict[str, object] = {}
    for column, value in record.items():
        if pd.isna(value):
            result[column] = None
        elif hasattr(value, "item"):
            result[column] = value.item()
        else:
            result[column] = value
    return result


def _select_one(mask: pd.Series, description: str, raw: pd.DataFrame) -> int:
    matching_indices = raw.index[mask]
    if matching_indices.empty:
        raise AssertionError(f"Could not find record for check: {description}")
    return int(matching_indices[0])


def _record_checks(raw: pd.DataFrame, cleaned: pd.DataFrame) -> pd.DataFrame:
    checks = [
        (
            "small_cell_suppression",
            raw["Month of Eligibility"].eq("2026-08")
            & raw["County"].eq("Alameda")
            & raw["Language"].eq("Hebrew"),
            "Count remains unknown; code 1 annotation is retained; county row remains map-eligible.",
            lambda row: pd.isna(row["eligible_count"])
            and row["annotation_code"] == "1"
            and row["is_suppressed"]
            and row["map_eligible"],
        ),
        (
            "comma_formatted_count",
            raw["Month of Eligibility"].eq("2026-08")
            & raw["County"].eq("Alameda")
            & raw["Language"].eq("Arabic"),
            "The source text 2,724 becomes integer 2724 and Alameda has the stable FIPS map key 06001.",
            lambda row: row["eligible_count"] == 2724
            and row["county_fips"] == "06001"
            and row["count_availability"] == "reported",
        ),
        (
            "trimmed_language_label",
            raw["Language"].eq(" Unknown"),
            "Leading whitespace is removed; Unknown remains distinct from Missing/Unknown.",
            lambda row: row["language"] == "Unknown",
        ),
        (
            "statewide_summary",
            raw["County"].eq("STATEWIDE") & raw["Language"].eq("STATEWIDE"),
            "The statewide summary is retained but marked ineligible for the county map.",
            lambda row: row["county"] == "STATEWIDE"
            and row["language"] == "STATEWIDE"
            and not row["map_eligible"],
        ),
        (
            "invalid_county_suppression",
            raw["County"].eq("Invalid County Code"),
            "The source record is retained, its suppressed count stays unknown, and it is not mapped.",
            lambda row: pd.isna(row["eligible_count"])
            and row["is_suppressed"]
            and not row["map_eligible"],
        ),
    ]

    results = []
    for check_name, selector, expected, matches_expected in checks:
        index = _select_one(selector, check_name, raw)
        actual = cleaned.loc[index]
        matches = bool(matches_expected(actual))
        results.append(
            {
                "check": check_name,
                "original_record": json.dumps(_json_record(raw.loc[index]), ensure_ascii=False),
                "expected_result_and_reason": expected,
                "actual_cleaned_record": json.dumps(
                    _json_record(actual), ensure_ascii=False
                ),
                "matches": matches,
            }
        )

    result_frame = pd.DataFrame(results)
    if not result_frame["matches"].all():
        failures = result_frame.loc[~result_frame["matches"], "check"].tolist()
        raise AssertionError(f"Record checks failed: {failures}")
    return result_frame


def _suspicious_values(raw: pd.DataFrame) -> pd.DataFrame:
    """Document source conditions before any normalization or interpretation."""
    count_is_blank_or_whitespace = raw["Total Eligibles"].str.strip().eq("")
    code_two_whitespace_count = raw["Annotation Code"].eq("2") & (
        raw["Total Eligibles"].ne("") & count_is_blank_or_whitespace
    )
    records = [
        {
            "issue": "blank_or_whitespace_eligible_count",
            "affected_rows": int(count_is_blank_or_whitespace.sum()),
            "source_condition": "Total Eligibles is empty or whitespace-only before cleaning.",
            "decision": "Retain the row; parse the count as unknown, never zero.",
        },
        {
            "issue": "code_1_suppression",
            "affected_rows": int(raw["Annotation Code"].eq("1").sum()),
            "source_condition": "Annotation Code is 1.",
            "decision": "Retain source code and mark count availability as suppressed.",
        },
        {
            "issue": "code_2_suppression",
            "affected_rows": int(raw["Annotation Code"].eq("2").sum()),
            "source_condition": "Annotation Code is 2.",
            "decision": "Retain source code and mark count availability as suppressed.",
        },
        {
            "issue": "whitespace_only_code_2_count",
            "affected_rows": int(code_two_whitespace_count.sum()),
            "source_condition": "Code-2 record has a whitespace-only count before trimming.",
            "decision": "Normalize whitespace first, then retain as an unknown suppressed count.",
        },
        {
            "issue": "leading_whitespace_language",
            "affected_rows": int(raw["Language"].ne(raw["Language"].str.strip()).sum()),
            "source_condition": "Language label has surrounding whitespace.",
            "decision": "Trim whitespace only; do not merge categories.",
        },
        {
            "issue": "missing_or_dot_data_date",
            "affected_rows": int(raw["Date of Data"].str.strip().isin({"", "."}).sum()),
            "source_condition": "Date of Data is blank or a dot marker.",
            "decision": "Retain source row and parse the derived date as missing.",
        },
        {
            "issue": "special_geography",
            "affected_rows": int(raw["County"].isin(SPECIAL_COUNTIES).sum()),
            "source_condition": "County is STATEWIDE or Invalid County Code.",
            "decision": "Retain in full output and mark not eligible for county map output.",
        },
        {
            "issue": "all_blank_difference",
            "affected_rows": int(raw["Difference"].eq("").sum()),
            "source_condition": "Difference field is blank.",
            "decision": "Retain as nullable source field; exclude from metrics.",
        },
    ]
    return pd.DataFrame(records)


def _clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    if raw.columns.tolist() != SOURCE_COLUMNS:
        raise ValueError(
            "Unexpected source columns. Expected "
            f"{SOURCE_COLUMNS!r}; received {raw.columns.tolist()!r}."
        )

    raw = raw.copy()
    clean = raw.copy()
    text_columns = clean.columns.tolist()
    for column in text_columns:
        clean[column] = clean[column].str.strip()

    trim_changes = {
        column: int(raw[column].ne(clean[column]).sum()) for column in text_columns
    }

    month_dates = pd.to_datetime(
        clean["Month of Eligibility"], format="%Y-%m", errors="coerce"
    )
    invalid_months = month_dates.isna()
    if invalid_months.any():
        examples = clean.loc[invalid_months, "Month of Eligibility"].head(5).tolist()
        raise ValueError(f"Invalid eligibility months: {examples}")

    count_text = clean["Total Eligibles"].str.replace(",", "", regex=False)
    numeric_counts = pd.to_numeric(count_text.mask(count_text.eq("")), errors="coerce")
    nonempty_counts = count_text.ne("")
    invalid_numeric_counts = nonempty_counts & (
        numeric_counts.isna()
        | numeric_counts.lt(0).fillna(False)
        | numeric_counts.mod(1).ne(0).fillna(True)
    )
    if invalid_numeric_counts.any():
        examples = clean.loc[invalid_numeric_counts, "Total Eligibles"].head(5).tolist()
        raise ValueError(f"Invalid eligible counts: {examples}")
    eligible_count = numeric_counts.astype("Int64")

    annotation_code = clean["Annotation Code"]
    annotation_description = clean["Annotation Description"]
    is_suppressed = annotation_code.isin({"1", "2"})
    suppression_description = annotation_description.str.startswith("Cell suppressed")
    blank_count = count_text.eq("")
    if (is_suppressed != suppression_description).any():
        raise ValueError("Suppression codes and descriptions do not agree.")
    if (blank_count != is_suppressed).any():
        raise ValueError("Blank counts and suppression annotations do not agree.")

    source_data_date = clean["Date of Data"]
    missing_data_date = source_data_date.isin({"", "."})
    parsed_data_date = pd.to_datetime(
        source_data_date.mask(missing_data_date),
        format="%d%b%Y",
        errors="coerce",
    )
    invalid_data_date = ~missing_data_date & parsed_data_date.isna()
    if invalid_data_date.any():
        examples = source_data_date.loc[invalid_data_date].head(5).tolist()
        raise ValueError(f"Invalid data dates: {examples}")
    data_date = parsed_data_date.dt.strftime("%Y-%m-%d").astype("string")

    county = clean["County"]
    language = clean["Language"]
    map_eligible = ~county.isin(SPECIAL_COUNTIES) & language.ne("STATEWIDE")
    county_fips = county.map(COUNTY_FIPS).astype("string")
    unmapped_map_counties = sorted(county.loc[map_eligible & county_fips.isna()].unique())
    if unmapped_map_counties:
        raise ValueError(
            "Map-eligible county labels have no county FIPS mapping: "
            f"{unmapped_map_counties}"
        )
    cleaned = pd.DataFrame(
        {
            "month": clean["Month of Eligibility"],
            "county": county,
            "county_fips": county_fips,
            "language": language,
            "eligible_count": eligible_count,
            "annotation_code": annotation_code,
            "annotation_description": annotation_description,
            "status": clean["Status"],
            "data_date": data_date,
            "difference": clean["Difference"].mask(clean["Difference"].eq("")),
            "is_suppressed": is_suppressed,
            "count_availability": pd.Series(
                "reported", index=clean.index, dtype="string"
            ).mask(is_suppressed, "suppressed"),
            "map_eligible": map_eligible,
        }
    )

    key_columns = ["month", "county", "language"]
    duplicate_keys = cleaned.duplicated(subset=key_columns, keep=False)
    if duplicate_keys.any():
        examples = cleaned.loc[duplicate_keys, key_columns].head(5).to_dict("records")
        raise ValueError(f"Cleaning created repeated keys: {examples}")

    if len(cleaned) != len(raw):
        raise AssertionError("Cleaning changed the source row count.")

    reported_counts = eligible_count.dropna()
    summary: dict[str, object] = {
        "input_rows": int(len(raw)),
        "output_rows": int(len(cleaned)),
        "row_change": int(len(cleaned) - len(raw)),
        "source_columns": SOURCE_COLUMNS,
        "output_columns": cleaned.columns.tolist(),
        "source_blank_cells_by_column": {
            column: int(raw[column].eq("").sum()) for column in text_columns
        },
        "cleaned_missing_cells_by_column": {
            column: int(cleaned[column].isna().sum()) for column in cleaned.columns
        },
        "text_values_trimmed_by_column": trim_changes,
        "source_date_dot_markers": int(raw["Date of Data"].str.strip().eq(".").sum()),
        "parsed_data_date_missing": int(data_date.isna().sum()),
        "data_date_parse_failures": int(invalid_data_date.sum()),
        "month_min": month_dates.min().strftime("%Y-%m"),
        "month_max": month_dates.max().strftime("%Y-%m"),
        "data_date_min": parsed_data_date.min().strftime("%Y-%m-%d"),
        "data_date_max": parsed_data_date.max().strftime("%Y-%m-%d"),
        "county_labels": sorted(county.unique().tolist()),
        "language_labels": sorted(language.unique().tolist()),
        "status_counts": {
            str(key): int(value) for key, value in clean["Status"].value_counts().items()
        },
        "exact_duplicate_excess_rows": int(raw.duplicated().sum()),
        "repeated_key_excess_rows": int(duplicate_keys.sum()),
        "reported_count_rows": int(reported_counts.size),
        "suppressed_count_rows": int(is_suppressed.sum()),
        "suppression_code_counts": {
            str(key): int(value)
            for key, value in annotation_code.loc[is_suppressed].value_counts().items()
        },
        "reported_count_min": int(reported_counts.min()),
        "reported_count_max": int(reported_counts.max()),
        "reported_cell_sum_across_all_rows_not_a_single_period_total": int(
            reported_counts.sum()
        ),
        "zero_count_rows": int(reported_counts.eq(0).sum()),
        "invalid_count_rows": int(invalid_numeric_counts.sum()),
        "special_county_row_counts": {
            county_label: int(county.eq(county_label).sum())
            for county_label in sorted(SPECIAL_COUNTIES)
        },
        "map_eligible_rows": int(map_eligible.sum()),
        "map_county_count": int(cleaned.loc[map_eligible, "county"].nunique()),
        "map_counties_missing_fips": unmapped_map_counties,
    }
    return cleaned, summary


def _cleaned_sample(raw: pd.DataFrame, cleaned: pd.DataFrame) -> pd.DataFrame:
    specifications = [
        (raw["Annotation Code"].eq("1"), "small-cell suppression", 10),
        (raw["Annotation Code"].eq("2"), "complementary suppression", 8),
        (
            raw["Total Eligibles"].str.contains(",", regex=False),
            "comma-formatted count",
            12,
        ),
        (raw["Language"].ne(raw["Language"].str.strip()), "trimmed language label", 6),
        (raw["County"].eq("STATEWIDE"), "statewide summary row", 4),
        (raw["County"].eq("Invalid County Code"), "invalid county code row", 4),
        (raw["Status"].eq("F"), "status F example", 3),
        (raw["Status"].eq("P"), "status P example", 3),
    ]
    reasons: dict[int, list[str]] = {}
    for mask, reason, limit in specifications:
        for index in raw.index[mask][:limit]:
            reasons.setdefault(int(index), []).append(reason)

    sample = cleaned.loc[list(reasons)].copy()
    sample["sample_selection_reason"] = [
        "; ".join(reasons[index]) for index in sample.index
    ]
    if len(sample) > 50:
        raise AssertionError("The cleaned sample exceeds the 50-row assignment limit.")
    return sample.reset_index(drop=True)


def _transformation_report(
    raw: pd.DataFrame,
    cleaned: pd.DataFrame,
    summary: dict[str, object],
    map_fact: pd.DataFrame,
    selector_coverage: pd.DataFrame,
) -> pd.DataFrame:
    """Report effects at each major stage; this never substitutes for raw data."""
    return pd.DataFrame(
        [
            {
                "stage": "01_raw_profile",
                "input_rows": len(raw),
                "output_rows": len(raw),
                "affected_rows": 0,
                "what_changed": "No values changed; source schema and anomalies were profiled first.",
            },
            {
                "stage": "02_text_normalization",
                "input_rows": len(raw),
                "output_rows": len(raw),
                "affected_rows": int(sum(summary["text_values_trimmed_by_column"].values())),
                "what_changed": "Surrounding whitespace was removed; no categories were merged or renamed.",
            },
            {
                "stage": "03_type_conversion",
                "input_rows": len(raw),
                "output_rows": len(cleaned),
                "affected_rows": int(
                    raw["Total Eligibles"].str.contains(",", regex=False).sum()
                ),
                "what_changed": "Display commas were removed only for nullable integer parsing; units remain certified-eligible counts.",
            },
            {
                "stage": "04_suppression_handling",
                "input_rows": len(cleaned),
                "output_rows": len(cleaned),
                "affected_rows": int(summary["suppressed_count_rows"]),
                "what_changed": "Suppressed values remain unknown and are flagged; no missing count was filled with zero.",
            },
            {
                "stage": "05_geography_and_map_keys",
                "input_rows": len(cleaned),
                "output_rows": len(cleaned),
                "affected_rows": int((~cleaned["map_eligible"]).sum()),
                "what_changed": "All rows retained; special geography rows receive no county FIPS and are flagged as not map eligible.",
            },
            {
                "stage": "06_map_derivative",
                "input_rows": len(cleaned),
                "output_rows": len(map_fact),
                "affected_rows": int(len(cleaned) - len(map_fact)),
                "what_changed": "Map-only fact table excludes special geography rows; full cleaned output still retains them.",
            },
            {
                "stage": "07_selector_coverage",
                "input_rows": len(map_fact),
                "output_rows": len(selector_coverage),
                "affected_rows": int((~selector_coverage["complete_58_county_coverage"]).sum()),
                "what_changed": "Each month/language selector is flagged when it lacks one or more of 58 county source rows.",
            },
        ]
    )


def _eligible_count_distribution(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Describe reported counts without treating suppressed values as zero."""
    reported = cleaned.loc[cleaned["count_availability"].eq("reported"), "eligible_count"]
    bins = [0, 11, 50, 100, 1_000, 10_000, 100_000, float("inf")]
    labels = [
        "1-10",
        "11-49",
        "50-99",
        "100-999",
        "1,000-9,999",
        "10,000-99,999",
        "100,000+",
    ]
    bucket = pd.cut(reported.astype("float64"), bins=bins, labels=labels, right=False)
    result = (
        bucket.value_counts(sort=False)
        .rename_axis("eligible_count_range")
        .reset_index(name="reported_row_count")
    )
    result["share_of_reported_rows"] = result["reported_row_count"] / len(reported)
    return result


def clean_file(input_path: Path, output_dir: Path) -> dict[str, object]:
    raw = pd.read_csv(
        input_path,
        dtype="string",
        keep_default_na=False,
        encoding="utf-8-sig",
    )
    suspicious_values = _suspicious_values(raw)
    cleaned, summary = _clean(raw)
    checks = _record_checks(raw, cleaned)
    sample = _cleaned_sample(raw, cleaned)

    digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    summary["input_file"] = str(input_path)
    summary["input_sha256"] = digest
    summary["record_check_count"] = int(len(checks))
    summary["record_checks_passed"] = bool(checks["matches"].all())
    summary["sample_rows"] = int(len(sample))
    summary["sample_selection"] = (
        "Deterministic source-order selection of suppressed cells, comma-formatted counts, "
        "trimmed language labels, statewide and invalid-county records, and both statuses."
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output_dir / "cleaned_language_eligibles.csv", index=False)
    # One row per selectable month-county-language combination. This is the
    # dashboard fact table; special geography rows stay in the full audit table.
    map_fact = cleaned.loc[cleaned["map_eligible"]].copy()
    map_fact.to_csv(output_dir / "county_language_month_map.csv", index=False)
    county_dimension = pd.DataFrame(
        [
            {
                "county": county,
                "county_fips": county_fips,
                "county_display": f"{county} County",
            }
            for county, county_fips in COUNTY_FIPS.items()
        ]
    ).sort_values("county_fips")
    county_dimension.to_csv(output_dir / "california_counties.csv", index=False)
    selector_coverage = (
        map_fact.groupby(["month", "language"], as_index=False)
        .agg(
            county_rows=("county_fips", "size"),
            county_count=("county_fips", "nunique"),
            reported_county_rows=(
                "count_availability",
                lambda values: int(values.eq("reported").sum()),
            ),
            suppressed_county_rows=(
                "count_availability",
                lambda values: int(values.eq("suppressed").sum()),
            ),
        )
        .assign(
            counties_without_source_row=lambda frame: 58 - frame["county_count"],
            complete_58_county_coverage=lambda frame: frame["county_count"].eq(58),
        )
    )
    selector_coverage.to_csv(output_dir / "month_language_coverage.csv", index=False)
    transformation_report = _transformation_report(
        raw, cleaned, summary, map_fact, selector_coverage
    )
    count_distribution = _eligible_count_distribution(cleaned)
    suspicious_values.to_csv(output_dir / "suspicious_values.csv", index=False)
    transformation_report.to_csv(output_dir / "transformation_report.csv", index=False)
    count_distribution.to_csv(output_dir / "eligible_count_distribution.csv", index=False)
    summary["map_fact_rows"] = int(len(map_fact))
    summary["county_dimension_rows"] = int(len(county_dimension))
    summary["month_language_selector_rows"] = int(len(selector_coverage))
    summary["complete_58_county_month_language_rows"] = int(
        selector_coverage["complete_58_county_coverage"].sum()
    )
    summary["suspicious_value_checks"] = int(len(suspicious_values))
    summary["transformation_report_stages"] = int(len(transformation_report))
    summary["eligible_count_distribution_rows"] = int(len(count_distribution))
    summary["eligible_count_percentiles_reported_only"] = {
        str(percentile): float(value)
        for percentile, value in cleaned.loc[
            cleaned["count_availability"].eq("reported"), "eligible_count"
        ].quantile([0.25, 0.5, 0.75, 0.9, 0.99]).items()
    }
    sample.to_csv(output_dir / "cleaned_language_sample.csv", index=False)
    checks.to_csv(output_dir / "record_checks.csv", index=False)
    (output_dir / "qa_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    arguments = parser.parse_args()
    summary = clean_file(arguments.input, arguments.output_dir)
    print(
        f"Wrote {summary['output_rows']} cleaned rows and "
        f"{summary['sample_rows']} sample rows to {arguments.output_dir}."
    )
    print(
        f"Suppressed counts: {summary['suppressed_count_rows']}; "
        f"map counties: {summary['map_county_count']}; "
        f"record checks passed: {summary['record_checks_passed']}."
    )


if __name__ == "__main__":
    main()
