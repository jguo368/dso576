"""Reproduce the approved cleaning.ipynb workflow and its validation reports.

Run with: python Project/clean_data.py
Requires pandas. Paths are relative to this script, not the working directory.
The raw CSV is read only. All rows remain in the full cleaned DataFrame;
only the notebook's selected 20-row sample is written to cleaned_sample.csv.
No additional cleaning rules or anomaly thresholds are applied.
"""

from pathlib import Path

import pandas as pd


def main():
    """Clean, report notebook checks, write the sample, and return both frames."""
    project_dir = Path(__file__).resolve().parent

    # Read the source as text, preserving blank fields and source labels.
    file_path = project_dir / "raw" / "by-primary-language-certified-eligibles.csv"

    df_raw = pd.read_csv(
        file_path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig"
    )

    print("Raw shape:", df_raw.shape)

    # Inspect source columns and types.
    print(df_raw.columns.tolist())
    print()
    print(df_raw.dtypes)

    # Inspect the first source records.
    print(df_raw.head(10).to_string())

    # Validate eligibility months without changing their stored text.
    month_parsed = pd.to_datetime(
        df_raw["Month of Eligibility"],
        format="%Y-%m",
        errors="coerce"
    )

    month_failed = month_parsed.isna().sum()

    print("Failed month conversions:", month_failed)
    print("Distinct parsed months:", month_parsed.nunique())
    print("Min month:", month_parsed.min())
    print("Max month:", month_parsed.max())

    # Parse published counts; blank and suppressed counts stay missing.
    total_raw = df_raw["Total Eligibles"]

    total_clean_text = total_raw.str.strip().str.replace(",", "", regex=False)

    total_numeric = pd.to_numeric(
        total_clean_text.replace("", pd.NA),
        errors="coerce"
    )

    print("Nonblank source values:", (total_clean_text != "").sum())
    print("Successful numeric conversions:", total_numeric.notna().sum())
    print("Missing / suppressed after conversion:", total_numeric.isna().sum())
    print("Min numeric value:", total_numeric.min())
    print("Max numeric value:", total_numeric.max())

    # Parse data dates using the notebook's blank and dot handling.
    date_raw = df_raw["Date of Data"].str.strip()

    date_clean = date_raw.replace(
        {
            "": pd.NA,
            ".": pd.NA
        }
    )

    date_parsed = pd.to_datetime(
        date_clean,
        format="%d%b%Y",
        errors="coerce"
    )

    nonmissing_date_source = date_clean.notna().sum()
    successful_date_conversions = date_parsed.notna().sum()
    failed_date_conversions = (
        date_clean.notna() & date_parsed.isna()
    ).sum()

    print("Nonmissing date source values:", nonmissing_date_source)
    print("Successful date conversions:", successful_date_conversions)
    print("Failed date conversions:", failed_date_conversions)
    print("Missing after conversion:", date_parsed.isna().sum())
    print("Min date:", date_parsed.min())
    print("Max date:", date_parsed.max())

    # Inspect categorical values.
    for col in ["County", "Language", "Annotation Code", "Status"]:
        print(f"\n--- {col} ---")
        print("Unique values:", df_raw[col].nunique())
        print(df_raw[col].value_counts(dropna=False).head(20))

    # Review special geography labels and language whitespace.
    print("County special values:")
    print(df_raw.loc[df_raw["County"].isin(["STATEWIDE", "Invalid County Code"]), "County"].value_counts())

    print("\nLanguage values with possible whitespace:")
    print(df_raw.loc[df_raw["Language"].str.startswith(" "), "Language"].value_counts())

    print("\nAnnotation Code values:")
    print(df_raw["Annotation Code"].value_counts(dropna=False))

    print("\nStatus values:")
    print(df_raw["Status"].value_counts(dropna=False))

    # Preserve original language labels and trim whitespace only.
    df_clean = df_raw.copy()

    df_clean["Language_original"] = df_clean["Language"]
    df_clean["Language"] = df_clean["Language"].str.strip()

    changed_language = (
        df_clean["Language_original"] != df_clean["Language"]
    )

    print("Rows changed:", changed_language.sum())

    print("\nBefore:")
    print(df_clean.loc[changed_language, "Language_original"].value_counts())

    print("\nAfter:")
    print(df_clean.loc[changed_language, "Language"].value_counts())

    # Check normalized keys and keep the two unknown categories separate.
    key_cols = ["Month of Eligibility", "County", "Language"]

    duplicate_keys_after = df_clean.duplicated(
        subset=key_cols,
        keep=False
    )

    print("Repeated key rows after text standardization:", duplicate_keys_after.sum())

    print("\nUnknown count:")
    print((df_clean["Language"] == "Unknown").sum())

    print("\nMissing/Unknown count:")
    print((df_clean["Language"] == "Missing/Unknown").sum())

    print("\nUnique language labels after standardization:")
    print(df_clean["Language"].nunique())

    # Check exact duplicates separately from repeated business keys.
    exact_duplicate_rows = df_raw.duplicated(keep=False)
    exact_duplicate_excess = df_raw.duplicated().sum()

    key_cols = ["Month of Eligibility", "County", "Language"]

    repeated_key_rows = df_clean.duplicated(
        subset=key_cols,
        keep=False
    )

    repeated_key_excess = df_clean.duplicated(
        subset=key_cols
    ).sum()

    print("Exact duplicate rows involved:", exact_duplicate_rows.sum())
    print("Exact duplicate excess rows:", exact_duplicate_excess)

    print("\nRepeated business-key rows involved:", repeated_key_rows.sum())
    print("Repeated business-key excess rows:", repeated_key_excess)

    # Count missing values before normalization.
    missing_summary_before = pd.DataFrame({
        "Column": [
            "Total Eligibles",
            "Annotation Code",
            "Annotation Description",
            "Date of Data",
            "Difference"
        ],
        "Missing before": [
            df_raw["Total Eligibles"].str.strip().eq("").sum(),
            df_raw["Annotation Code"].eq("").sum(),
            df_raw["Annotation Description"].eq("").sum(),
            (
                df_raw["Date of Data"].str.strip().isin(["", "."])
            ).sum(),
            df_raw["Difference"].str.strip().eq("").sum()
        ]
    })

    print(missing_summary_before.to_string(index=False))

    # Normalize missing values without dropping any source rows.
    # Normalize missing values without dropping rows

    df_clean["Total Eligibles"] = total_numeric.astype("Int64")

    df_clean["Annotation Code"] = (
        df_clean["Annotation Code"]
        .replace("", pd.NA)
    )

    df_clean["Annotation Description"] = (
        df_clean["Annotation Description"]
        .replace("", pd.NA)
    )

    df_clean["Date of Data"] = date_parsed

    df_clean["Difference"] = (
        df_clean["Difference"]
        .str.strip()
        .replace("", pd.NA)
    )

    missing_summary_after = pd.DataFrame({
        "Column": [
            "Total Eligibles",
            "Annotation Code",
            "Annotation Description",
            "Date of Data",
            "Difference"
        ],
        "Missing after": [
            df_clean["Total Eligibles"].isna().sum(),
            df_clean["Annotation Code"].isna().sum(),
            df_clean["Annotation Description"].isna().sum(),
            df_clean["Date of Data"].isna().sum(),
            df_clean["Difference"].isna().sum()
        ]
    })

    print(missing_summary_after.to_string(index=False))

    # Review special geographies and largest published counts descriptively.
    print("STATEWIDE rows:")
    print((df_clean["County"] == "STATEWIDE").sum())

    print("\nInvalid County Code rows:")
    print((df_clean["County"] == "Invalid County Code").sum())

    print("\nInvalid County Code records:")
    print(
        df_clean.loc[
            df_clean["County"] == "Invalid County Code",
            [
                "Month of Eligibility",
                "County",
                "Language",
                "Total Eligibles",
                "Annotation Code",
                "Annotation Description",
                "Status",
                "Date of Data"
            ]
        ]
    )

    print("\nLargest published Total Eligibles values:")
    print(
        df_clean.loc[df_clean["Total Eligibles"].notna()]
        .sort_values("Total Eligibles", ascending=False)
        .head(10)[
            [
                "Month of Eligibility",
                "County",
                "Language",
                "Total Eligibles",
                "Status"
            ]
        ]
    )

    # Check date conversion failures.
    invalid_eligibility_dates = month_parsed.isna().sum()

    invalid_data_dates = (
        date_clean.notna() & date_parsed.isna()
    ).sum()

    print("Invalid Month of Eligibility values:", invalid_eligibility_dates)
    print("Invalid nonmissing Date of Data values:", invalid_data_dates)

    # Reconcile row counts and published sums.
    starting_rows = len(df_raw)
    final_rows = len(df_clean)

    published_total_before = total_numeric.sum(skipna=True)
    published_total_after = df_clean["Total Eligibles"].sum(skipna=True)

    print("Starting row count:", starting_rows)
    print("Final row count:", final_rows)
    print("Row difference:", final_rows - starting_rows)

    print("\nPublished Total Eligibles sum before cleaning:", published_total_before)
    print("Published Total Eligibles sum after cleaning:", published_total_after)
    print("Difference in published total:", published_total_after - published_total_before)

    # Report published-value calculations and missing keys.
    published_mask = df_clean["Total Eligibles"].notna()

    published_record_count = published_mask.sum()
    suppressed_record_count = df_clean["Total Eligibles"].isna().sum()

    published_sum = df_clean.loc[published_mask, "Total Eligibles"].sum()
    published_average = df_clean.loc[published_mask, "Total Eligibles"].mean()

    missing_county_keys = df_clean["County"].str.strip().eq("").sum()
    missing_language_keys = df_clean["Language"].str.strip().eq("").sum()
    missing_month_keys = df_clean["Month of Eligibility"].str.strip().eq("").sum()

    print("Records used for published sum:", published_record_count)
    print("Records excluded because count is unavailable:", suppressed_record_count)
    print("Published Total Eligibles sum:", published_sum)
    print("Published Total Eligibles average:", published_average)

    print("\nMissing Month keys:", missing_month_keys)
    print("Missing County keys:", missing_county_keys)
    print("Missing Language keys:", missing_language_keys)

    # Verify the same five individual records as the notebook.
    # Select five records for individual verification

    # 1. Published count with comma formatting
    idx1 = df_raw[
        (df_raw["Month of Eligibility"] == "2026-08") &
        (df_raw["County"] == "Alameda") &
        (df_raw["Language"] == "Arabic")
    ].index[0]

    # 2. Suppressed small-number record: Annotation Code 1
    idx2 = df_raw[
        (df_raw["Annotation Code"] == "1")
    ].index[0]

    # 3. Suppressed complementary-cell record: Annotation Code 2
    idx3 = df_raw[
        (df_raw["Annotation Code"] == "2")
    ].index[0]

    # 4. Leading-whitespace language record
    idx4 = df_raw[
        (df_raw["Language"] == " Unknown")
    ].index[0]

    # 5. Invalid County Code record
    idx5 = df_raw[
        (df_raw["County"] == "Invalid County Code")
    ].index[0]


    record_checks = pd.DataFrame([
        {
            "Check": "Published count with comma",
            "Original": df_raw.loc[idx1, "Total Eligibles"],
            "Expected": 2724,
            "Actual": df_clean.loc[idx1, "Total Eligibles"],
            "Match": df_clean.loc[idx1, "Total Eligibles"] == 2724
        },
        {
            "Check": "Suppressed small number (Code 1)",
            "Original": df_raw.loc[idx2, "Total Eligibles"],
            "Expected": "Missing",
            "Actual": "Missing" if pd.isna(df_clean.loc[idx2, "Total Eligibles"]) else df_clean.loc[idx2, "Total Eligibles"],
            "Match": pd.isna(df_clean.loc[idx2, "Total Eligibles"])
        },
        {
            "Check": "Suppressed complementary cell (Code 2)",
            "Original": df_raw.loc[idx3, "Total Eligibles"],
            "Expected": "Missing",
            "Actual": "Missing" if pd.isna(df_clean.loc[idx3, "Total Eligibles"]) else df_clean.loc[idx3, "Total Eligibles"],
            "Match": pd.isna(df_clean.loc[idx3, "Total Eligibles"])
        },
        {
            "Check": "Leading-whitespace language",
            "Original": repr(df_raw.loc[idx4, "Language"]),
            "Expected": "Unknown",
            "Actual": df_clean.loc[idx4, "Language"],
            "Match": df_clean.loc[idx4, "Language"] == "Unknown"
        },
        {
            "Check": "Invalid County Code retained",
            "Original": df_raw.loc[idx5, "County"],
            "Expected": "Invalid County Code",
            "Actual": df_clean.loc[idx5, "County"],
            "Match": df_clean.loc[idx5, "County"] == "Invalid County Code"
        }
    ])

    print(record_checks.to_string(index=False))

    # Select the same sample in source order. Only sample overlaps are deduplicated.
    sample_parts = [
        df_clean[df_clean["Total Eligibles"].notna()].head(5),
        df_clean[df_clean["Annotation Code"] == "1"].head(3),
        df_clean[df_clean["Annotation Code"] == "2"].head(3),
        df_clean[df_clean["Language"] == "Unknown"].head(2),
        df_clean[df_clean["Language"] == "Missing/Unknown"].head(2),
        df_clean[df_clean["County"] == "STATEWIDE"].head(2),
        df_clean[df_clean["County"] == "Invalid County Code"].head(3)
    ]

    cleaned_sample = (
        pd.concat(sample_parts)
        .drop_duplicates()
        .head(20)
    )

    print(cleaned_sample.to_string(index=False))

    # Write the sample beside this script.
    cleaned_sample.to_csv(
        project_dir / "cleaned_sample.csv",
        index=False
    )

    print("Saved cleaned_sample.csv with", len(cleaned_sample), "rows")

    return df_clean, cleaned_sample


if __name__ == "__main__":
    main()
