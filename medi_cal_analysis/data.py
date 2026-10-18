"""Load and validate the county-month contract in BUILD_SPEC.md."""

from pathlib import Path
import re

import numpy as np
import pandas as pd


DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "dso576/project/medi_cal_merged_county_month.csv"
)
KEYS = ["month_of_eligibility", "county"]
SUPPRESSION_COLUMNS = [
    "language_suppressed_cells",
    "age_sex_suppressed_cells",
    "race_age_suppressed_cells",
]
AGE_GROUPS = ("age_00_18", "age_19_44", "age_45_64", "age_65_plus")
SEXES = ("female", "male")
RACES = ("ai_an", "asian", "black", "hispanic", "not_reported", "white")
CALIFORNIA_COUNTIES = tuple(
    "Alameda|Alpine|Amador|Butte|Calaveras|Colusa|Contra Costa|Del Norte|"
    "El Dorado|Fresno|Glenn|Humboldt|Imperial|Inyo|Kern|Kings|Lake|Lassen|"
    "Los Angeles|Madera|Marin|Mariposa|Mendocino|Merced|Modoc|Mono|Monterey|"
    "Napa|Nevada|Orange|Placer|Plumas|Riverside|Sacramento|San Benito|"
    "San Bernardino|San Diego|San Francisco|San Joaquin|San Luis Obispo|"
    "San Mateo|Santa Barbara|Santa Clara|Santa Cruz|Shasta|Sierra|Siskiyou|"
    "Solano|Sonoma|Stanislaus|Sutter|Tehama|Trinity|Tulare|Tuolumne|Ventura|"
    "Yolo|Yuba".split("|")
)
_COUNTY_LOOKUP = {county.casefold(): county for county in CALIFORNIA_COUNTIES}


def normalize_month(value: str) -> str:
    """Accept YYYY-MM or an ISO date; return its YYYY-MM month identifier."""
    text = str(value).strip()
    if not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", text):
        raise ValueError(f"Invalid month {value!r}; use YYYY-MM or YYYY-MM-DD.")
    try:
        return pd.Timestamp(text).strftime("%Y-%m")
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid month {value!r}.") from exc


def normalize_county(value: str) -> str:
    """Standardize case/whitespace, rejecting non-California county labels."""
    label = " ".join(str(value).split()).casefold()
    try:
        return _COUNTY_LOOKUP[label]
    except KeyError as exc:
        raise ValueError(f"Unknown California county: {value!r}.") from exc


def _month_or_missing(value: object) -> object:
    try:
        return normalize_month(value)
    except ValueError:
        return pd.NA


def _county_or_missing(value: object) -> object:
    try:
        return normalize_county(value)
    except ValueError:
        return pd.NA


def _numeric_counts(values: pd.Series, *, allow_missing: bool = True) -> pd.Series:
    # Invalid text is an error, not a newly manufactured suppressed value.
    try:
        result = pd.to_numeric(values, errors="raise").astype("Float64")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{values.name} must contain numeric counts or missing values.") from exc
    observed = result.dropna()
    if (
        not np.isfinite(observed.to_numpy(dtype=float)).all()
        or observed.lt(0).any()
        or observed.mod(1).ne(0).any()
        or (not allow_missing and result.isna().any())
    ):
        raise ValueError(f"{values.name} must contain finite, nonnegative whole counts.")
    return result


def prepare_data(raw: pd.DataFrame) -> pd.DataFrame:
    """Return a validated copy with one row per California county-month.

    Documented exclusions (BUILD_SPEC 7.6): missing/invalid months and any
    county label outside the 58 California counties, including statewide
    summaries and 'Invalid County Code'. No other rows are excluded. Counts
    remain nullable; suppression never becomes zero. Duplicate keys raise.

    ``result.attrs['preparation_report']`` records input/output and exclusion
    counts. Invalid-month and invalid-county counts can overlap on one row.
    """
    data = raw.copy(deep=True)
    data.columns = [str(column).strip().lower() for column in data.columns]
    if not data.columns.is_unique:
        raise ValueError("Duplicate column names after standardization.")

    age_columns = [f"age_sex__{age}__{sex}" for age in AGE_GROUPS for sex in SEXES]
    race_columns = [f"race_age__{age}__{race}" for age in AGE_GROUPS for race in RACES]
    required = KEYS + ["status", "date_of_data", "county_total_eligibles", "county_total_is_complete"]
    required += SUPPRESSION_COLUMNS + age_columns + race_columns
    missing = sorted(set(required) - set(data.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    language_columns = [c for c in data if c.startswith("language__")]
    if not language_columns:
        raise ValueError("At least one language__ column is required.")
    unexpected = [
        c for c in data
        if (c.startswith("age_sex__") and c not in age_columns)
        or (c.startswith("race_age__") and c not in race_columns)
        or (c.startswith("language__") and not re.fullmatch(r"language__[a-z][a-z0-9_]*", c))
    ]
    if unexpected:
        raise ValueError(f"Review unexpected demographic categories: {unexpected}")

    data["month_of_eligibility"] = data["month_of_eligibility"].map(_month_or_missing).astype("string")
    data["county"] = data["county"].map(_county_or_missing).astype("string")
    invalid_month = data["month_of_eligibility"].isna()
    invalid_county = data["county"].isna()
    exclude = invalid_month | invalid_county
    report = {
        "input_rows": len(data),
        "invalid_month_rows": int(invalid_month.sum()),
        "invalid_county_rows": int(invalid_county.sum()),
        "excluded_rows": int(exclude.sum()),
        "output_rows": int((~exclude).sum()),
    }
    data = data.loc[~exclude].copy()
    duplicates = data.duplicated(KEYS, keep=False)
    if duplicates.any():
        examples = data.loc[duplicates, KEYS].head().to_dict("records")
        raise ValueError(f"Duplicate county-month rows require review: {examples}")

    data["status"] = data["status"].astype("string").str.strip().str.upper()
    if not data["status"].isin(["F", "P"]).all():
        raise ValueError("status must contain F (final) or P (preliminary).")
    dates = data["date_of_data"].astype("string").str.strip().replace({"": pd.NA, ".": pd.NA})
    iso_dates = dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)
    source_dates = dates.str.fullmatch(r"\d{2}[A-Za-z]{3}\d{4}", na=False)
    if not (dates.isna() | iso_dates | source_dates).all():
        raise ValueError("date_of_data must be an ISO date, DHCS DDMMMYYYY date, or missing.")
    try:
        parsed = pd.to_datetime(dates.where(iso_dates), format="%Y-%m-%d", errors="raise")
        source_parsed = pd.to_datetime(dates.where(source_dates), format="%d%b%Y", errors="raise")
        data["date_of_data"] = parsed.fillna(source_parsed).dt.strftime("%Y-%m-%d").astype("string")
    except (ValueError, OverflowError) as exc:
        raise ValueError("date_of_data contains an invalid calendar date.") from exc

    # Explicit parsing avoids bool('False') == True.
    flags = data["county_total_is_complete"].astype("string").str.strip().str.casefold()
    if not flags.isin(["true", "false"]).all():
        raise ValueError("county_total_is_complete must contain True or False, with no missing values.")
    data["county_total_is_complete"] = flags.eq("true").astype("boolean")
    for column in ["county_total_eligibles"] + language_columns + age_columns + race_columns:
        data[column] = _numeric_counts(data[column])
    for column in SUPPRESSION_COLUMNS:
        data[column] = _numeric_counts(data[column], allow_missing=False).astype("Int64")

    complete = data["county_total_is_complete"]
    age_totals = data[age_columns].sum(axis=1, min_count=len(age_columns))
    inconsistent = complete & (
        data["county_total_eligibles"].isna()
        | age_totals.isna()
        | data["county_total_eligibles"].ne(age_totals)
        | data["age_sex_suppressed_cells"].gt(0)
    )
    if inconsistent.any():
        raise ValueError("Complete county totals must equal the sum of all available age/sex cells.")
    # Incomplete source totals are not safe totals for display or denominators.
    data.loc[~complete, "county_total_eligibles"] = pd.NA
    for column in language_columns:
        if (complete & data[column].gt(data["county_total_eligibles"])).any():
            raise ValueError(f"{column} exceeds a complete county total; review source data.")

    data = data.sort_values(KEYS).reset_index(drop=True)
    data.attrs["preparation_report"] = report
    return data


def load_data(path: str | Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Read the team's canonical CSV, then enforce the analysis contract."""
    return prepare_data(pd.read_csv(path))
