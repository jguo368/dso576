"""Reusable MVP datasets. All functions accept the output of load_data/prepare_data.

Shares are fractions in [0, 1], not percentages. Missing values are pandas NA.
Demographic context always describes the entire county Medi-Cal population;
it is never a language-specific age/sex/race cross-tabulation.
"""

from numbers import Integral

import pandas as pd

from .data import (
    CALIFORNIA_COUNTIES,
    KEYS,
    SUPPRESSION_COLUMNS,
    normalize_county,
    normalize_month,
)


def get_available_months(data: pd.DataFrame) -> list[str]:
    """Return chronological YYYY-MM selector values."""
    return sorted(data["month_of_eligibility"].dropna().unique().tolist())


def get_available_languages(data: pd.DataFrame) -> list[str]:
    """Return sorted language slugs, e.g. 'mandarin' and 'spanish'."""
    return sorted(c.removeprefix("language__") for c in data if c.startswith("language__"))


def _select_month(data: pd.DataFrame, month: str) -> pd.DataFrame:
    month = normalize_month(month)
    selected = data.loc[data["month_of_eligibility"].eq(month)].copy()
    if selected.empty:
        raise ValueError(f"No county data available for month {month!r}.")
    return selected


def _language_column(data: pd.DataFrame, language: str) -> str:
    slug = str(language).strip().casefold().removeprefix("language__")
    column = f"language__{slug}"
    if column not in data:
        raise ValueError(f"Unknown language {language!r}; use get_available_languages().")
    return column


def _share(counts: pd.Series, totals: pd.Series, complete: pd.Series) -> pd.Series:
    valid = counts.notna() & complete & totals.notna() & totals.gt(0)
    return counts.div(totals.where(valid)).where(valid).astype("Float64")


def get_county_metrics(data: pd.DataFrame, month: str, language: str) -> pd.DataFrame:
    """Return one row per county for the selected month and language.

    Includes selected-language counts, valid county totals, shares, availability
    flags, a share-unavailability reason, and the source suppression counters.
    No county is dropped because a language count or denominator is unavailable.
    """
    column = _language_column(data, language)
    selected = _select_month(data, month)
    columns = KEYS + [column, "county_total_eligibles", "county_total_is_complete"]
    result = selected[columns + SUPPRESSION_COLUMNS].rename(columns={column: "selected_language_count"}).copy()
    result.insert(2, "language", column.removeprefix("language__"))
    counts = result["selected_language_count"]
    totals = result["county_total_eligibles"]
    complete = result["county_total_is_complete"]
    result["language_count_is_available"] = counts.notna()
    result["language_share"] = _share(counts, totals, complete)
    result["language_share_is_available"] = result["language_share"].notna()
    reason = pd.Series(pd.NA, index=result.index, dtype="string")
    reason.loc[totals.le(0).fillna(False)] = "nonpositive_county_total"
    reason.loc[totals.isna()] = "missing_county_total"
    reason.loc[~complete] = "incomplete_county_total"
    reason.loc[counts.isna()] = "missing_language_count"
    result["language_share_unavailable_reason"] = reason
    return result.sort_values("county").reset_index(drop=True)


def get_language_share(data: pd.DataFrame, month: str, language: str) -> pd.DataFrame:
    """Return county shares with their numerator, denominator and validity."""
    return get_county_metrics(data, month, language)[
        KEYS + ["language", "selected_language_count", "county_total_eligibles",
                "county_total_is_complete", "language_share", "language_share_is_available",
                "language_share_unavailable_reason"]
    ].copy()


def get_map_data(data: pd.DataFrame, month: str, language: str) -> pd.DataFrame:
    """Return county-name join keys and metric/tooltip fields, including NA counts.

    Geometry belongs to the Phase 3 interface; join its county names to 'county'.
    """
    return get_county_metrics(data, month, language)


def get_county_ranking(
    data: pd.DataFrame, month: str, language: str, *, limit: int | None = None
) -> pd.DataFrame:
    """Sort counts descending, ties alphabetically; missing counts rank last/NA.

    Equal observed counts share a competition rank (1, 1, 3). By default all
    counties remain present, including unavailable counts. limit is an optional
    positive row limit, applied after sorting.
    """
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, Integral) or limit < 1):
        raise ValueError("limit must be a positive integer or None.")
    result = get_county_metrics(data, month, language)
    result["rank"] = result["selected_language_count"].rank(method="min", ascending=False).astype("Int64")
    result = result.sort_values(["selected_language_count", "county"], ascending=[False, True], na_position="last")
    return result.head(limit).reset_index(drop=True) if limit is not None else result.reset_index(drop=True)


def get_county_summary(data: pd.DataFrame, month: str, language: str, county: str) -> pd.DataFrame:
    """Return a one-row county detail metrics table; missing selections raise."""
    county = normalize_county(county)
    metrics = get_county_metrics(data, month, language)
    result = metrics.loc[metrics["county"].eq(county)]
    if result.empty:
        raise ValueError(f"No data for county {county!r} in month {normalize_month(month)!r}.")
    return result.reset_index(drop=True)


def get_month_summary(data: pd.DataFrame, month: str, language: str) -> pd.DataFrame:
    """Return overview KPIs and explicit coverage, without summing missing as zero.

    observed_language_count is a clearly labeled subtotal of available counties.
    Full totals and their ratio require all 58 counties and all required values.
    This does not average county shares or infer suppressed counts.
    """
    metrics = get_county_metrics(data, month, language)
    counts = metrics["selected_language_count"]
    totals = metrics["county_total_eligibles"]
    county_count = len(metrics)
    all_counties = county_count == len(CALIFORNIA_COUNTIES)
    language_complete = all_counties and bool(counts.notna().all())
    total_complete = all_counties and bool(metrics["county_total_is_complete"].all()) and bool(totals.notna().all())
    language_total = counts.sum(min_count=county_count) if language_complete else pd.NA
    county_total = totals.sum(min_count=county_count) if total_complete else pd.NA
    share = pd.NA
    if language_complete and total_complete and county_total > 0:
        share = language_total / county_total
    return pd.DataFrame([{
        "month_of_eligibility": normalize_month(month),
        "language": _language_column(data, language).removeprefix("language__"),
        "county_count": county_count,
        "missing_counties": len(CALIFORNIA_COUNTIES) - county_count,
        "language_count_available_counties": int(counts.notna().sum()),
        "language_count_missing_counties": int(counts.isna().sum()),
        "language_share_available_counties": int(metrics["language_share_is_available"].sum()),
        "observed_language_count": counts.sum(min_count=1),
        "selected_language_count": language_total,
        "selected_language_count_is_complete": language_complete,
        "county_total_eligibles": county_total,
        "county_total_is_complete": total_complete,
        "language_share": share,
    }])


def _county_row(data: pd.DataFrame, month: str, county: str) -> pd.Series:
    selected = _select_month(data, month)
    county = normalize_county(county)
    selected = selected.loc[selected["county"].eq(county)]
    if selected.empty:
        raise ValueError(f"No data for county {county!r} in month {normalize_month(month)!r}.")
    return selected.iloc[0]


def _demographic_summary(
    data: pd.DataFrame, month: str, county: str, *, prefix: str, category: str, group_by: str
) -> pd.DataFrame:
    row = _county_row(data, month, county)
    records = []
    for column in data:
        if column.startswith(prefix + "__"):
            _, age, label = column.split("__")
            records.append({"age_group": age, category: label, "eligible_count": row[column]})
    cells = pd.DataFrame(records)
    cells["eligible_count"] = cells["eligible_count"].astype("Float64")
    dimensions = ["age_group", category] if group_by == "cells" else [group_by]
    records = []
    for key, group in cells.groupby(dimensions, sort=True, dropna=False):
        # pandas supplies tuple keys when grouping by a list of column names.
        key = key if isinstance(key, tuple) else (key,)
        missing = int(group["eligible_count"].isna().sum())
        records.append({
            **dict(zip(dimensions, key)),
            "eligible_count": group["eligible_count"].sum(min_count=len(group)),
            "is_complete": missing == 0,
            "missing_cells": missing,
            "required_cells": len(group),
        })
    result = pd.DataFrame(records)
    result["eligible_count"] = result["eligible_count"].astype("Float64")
    result.insert(0, "county", row["county"])
    result.insert(0, "month_of_eligibility", row["month_of_eligibility"])
    result["county_total_eligibles"] = pd.Series(row["county_total_eligibles"], index=result.index, dtype="Float64")
    result["county_total_is_complete"] = bool(row["county_total_is_complete"])
    result["share_of_county"] = _share(
        result["eligible_count"], result["county_total_eligibles"], result["county_total_is_complete"]
    )
    return result.reset_index(drop=True)


def get_age_sex_summary(
    data: pd.DataFrame, month: str, county: str, *, group_by: str = "age_sex"
) -> pd.DataFrame:
    """Return overall county context by age/sex, age, or sex.

    group_by: 'age_sex' (8 source cells), 'age' (4 groups), or 'sex' (2).
    Any missing required cell makes that group's aggregate unavailable.
    """
    dimensions = {"age_sex": "cells", "age": "age_group", "sex": "sex"}
    if group_by not in dimensions:
        raise ValueError("group_by must be 'age_sex', 'age', or 'sex'.")
    return _demographic_summary(data, month, county, prefix="age_sex", category="sex", group_by=dimensions[group_by])


def get_race_ethnicity_summary(
    data: pd.DataFrame, month: str, county: str, *, group_by: str = "race"
) -> pd.DataFrame:
    """Return overall county race/ethnicity context, with strict missing propagation.

    group_by: 'race' (6 totals across ages), 'race_age' (24 source cells),
    or 'age' (4 totals across race categories). These are not language subgroups.
    """
    dimensions = {"race": "race_ethnicity", "race_age": "cells", "age": "age_group"}
    if group_by not in dimensions:
        raise ValueError("group_by must be 'race', 'race_age', or 'age'.")
    return _demographic_summary(data, month, county, prefix="race_age", category="race_ethnicity", group_by=dimensions[group_by])
