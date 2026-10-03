import os
import pandas as pd


RAW_PATH = "data/raw/t5_eligibility_by_language_201001_202609 (1).csv"
CLEAN_PATH = "data/cleaned/medi_cal_eligibility_language_clean.csv"


def main():
    # Load the raw data
    raw = pd.read_csv(RAW_PATH)

    # Normalize column names and clean obvious formatting issues
    raw.columns = [col.strip() for col in raw.columns]
    raw = raw.rename(columns={
        "Month of Eligibility": "month",
        "County": "county",
        "Language": "language",
        "Total Eligibles": "total_eligibles",
        "Annotation Code": "annotation_code",
        "Annotation Description": "annotation_description",
        "Status": "status",
        "Date of Data": "date_of_data",
        "Difference": "difference",
    })

    # Convert numeric text like "2,724" to integers and keep missing values as NaN
    raw["total_eligibles"] = raw["total_eligibles"].astype(str)
    raw["total_eligibles"] = raw["total_eligibles"].str.replace(",", "", regex=False)
    raw["total_eligibles"] = pd.to_numeric(raw["total_eligibles"], errors="coerce")

    # Parse month and date fields to standard datetime values
    raw["month"] = pd.to_datetime(raw["month"], format="%Y-%m", errors="coerce")
    raw["date_of_data"] = pd.to_datetime(raw["date_of_data"], format="%d%b%Y", errors="coerce")

    # Keep only rows that are useful for analysis: county-language counts with valid values
    clean = raw[
        raw["county"].notna() &
        raw["language"].notna() &
        raw["total_eligibles"].notna() &
        raw["status"].notna()
    ].copy()

    # Remove row-level annotation summaries that are not county-language records
    clean = clean[~clean["annotation_description"].fillna("").str.contains("Statewide Total by MOE", na=False)]

    # Retain only final counts, excluding preliminary records if the goal is a clean analytic table
    clean = clean[clean["status"] == "F"].copy()

    # Standardize text values
    clean["county"] = clean["county"].str.strip()
    clean["language"] = clean["language"].str.strip()
    clean["status"] = clean["status"].str.strip()

    # Sort for predictability and save cleaned data
    clean = clean.sort_values(["month", "county", "language"]).reset_index(drop=True)
    os.makedirs(os.path.dirname(CLEAN_PATH), exist_ok=True)
    clean.to_csv(CLEAN_PATH, index=False)

    print(f"Raw rows: {len(raw)}")
    print(f"Cleaned rows: {len(clean)}")
    print(f"Saved cleaned file: {CLEAN_PATH}")
    print(clean.head().to_string(index=False))


if __name__ == "__main__":
    main()
