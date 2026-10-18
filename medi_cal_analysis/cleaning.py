"""Rebuild the canonical county-month CSV from three DHCS demographic files.

Run ``python -m medi_cal_analysis.cleaning --help`` from the repository root.
The pinned source URLs and SHA-256 hashes in the report identify the snapshot.
Missing categories and suppression are both unavailable, never assumed zero.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.request import urlopen

import pandas as pd

from .data import (
    AGE_GROUPS, CALIFORNIA_COUNTIES, DEFAULT_DATA_PATH, KEYS, RACES, SEXES,
    normalize_county, normalize_month, prepare_data,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://data.chhs.ca.gov/dataset/8c897320-ba87-4574-bc37-bae974191c35/resource/"
SOURCE_URLS = {
    "language": BASE + "b698c8d7-aacd-43c6-a7dd-737ff5692284/download/t5_eligibility_by_language_201001_sept2026.csv",
    "age_sex": BASE + "cc08b60f-393f-4e37-9b3e-976d7a9f2a72/download/t1_eligibility_by_age_group_sex_201001_sept2026.csv",
    "race_age": BASE + "29a8f949-5c12-4e42-92db-39fa5ea12b8e/download/t4_eligibility_by_race_ethnicity_age_group_201001_sept2026.csv",
}
LANGUAGES = tuple(sorted(
    "asl arabic armenian cambodian cantonese english farsi french hebrew hindi "
    "hmong ilocano italian japanese korean lao mandarin mien missing_unknown "
    "other_chinese other_non_eng other_sign polish portuguese punjabi russian "
    "samoan spanish tagalog thai turkish unknown vietnamese".split()
))
DIMENSIONS = {
    "language": ["language"],
    "age_sex": ["age_group", "gender"],
    "race_age": ["age_group", "ethnicity"],
}


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().casefold()).strip("_")


def _safe_normalize(value, function):
    try:
        return function(value)
    except ValueError:
        return pd.NA


def _expected_columns(kind):
    if kind == "language":
        return [f"language__{language}" for language in LANGUAGES]
    labels = SEXES if kind == "age_sex" else RACES
    return [f"{kind}__{age}__{label}" for age in AGE_GROUPS for label in labels]


def clean_source(raw: pd.DataFrame, kind: str):
    """Return (county-month wide table, metadata table, audit dict).

    Source-cell duplicates are errors even when their counts agree. There is
    no silent deduplication or summing across incompatible demographic groups.
    Annotation codes 1/2 mean primary/complementary suppression respectively.
    """
    if kind not in DIMENSIONS:
        raise ValueError(f"Unknown source kind: {kind}")
    data = raw.copy(deep=True)
    data.columns = [_slug(c) for c in data.columns]
    if not data.columns.is_unique:
        raise ValueError("Duplicate source column names after normalization")
    needed = ["month_of_eligibility", "county", "total_eligibles", "annotation_code", "status", "date_of_data"] + DIMENSIONS[kind]
    if missing := sorted(set(needed) - set(data.columns)):
        raise ValueError(f"{kind}: missing source columns {missing}")
    month_lookup = {value: _safe_normalize(value, normalize_month) for value in data.month_of_eligibility.dropna().unique()}
    county_lookup = {value: _safe_normalize(value, normalize_county) for value in data.county.dropna().unique()}
    data["month_of_eligibility"] = data.month_of_eligibility.map(month_lookup)
    data["county"] = data.county.map(county_lookup)
    invalid_month = data.month_of_eligibility.isna()
    invalid_county = data.county.isna()
    exclude = invalid_month | invalid_county
    audit = {
        "input_rows": len(data), "invalid_month_rows": int(invalid_month.sum()),
        "invalid_county_rows": int(invalid_county.sum()), "excluded_rows": int(exclude.sum()),
        "retained_source_rows": int((~exclude).sum()),
    }
    data = data.loc[~exclude].copy()
    if data.empty:
        raise ValueError(f"{kind}: no valid California county data")
    for column in DIMENSIONS[kind]:
        data[column] = data[column].map(_slug)
    # Canonical age identifiers retain the source's '+' as an explicit 'plus'.
    if "age_group" in data:
        data["age_group"] = data.age_group.replace({"age_65": "age_65_plus"})
    dimensions = DIMENSIONS[kind]
    data["cell"] = kind + "__" + data[dimensions[0]]
    for dimension in dimensions[1:]:
        data["cell"] = data["cell"] + "__" + data[dimension]
    expected = _expected_columns(kind)
    if unexpected := sorted(set(data.cell) - set(expected)):
        raise ValueError(f"{kind}: review unexpected categories {unexpected}")
    if data.duplicated(KEYS + ["cell"]).any():
        raise ValueError(f"{kind}: duplicate source cells require review")

    annotations = data.annotation_code.astype("string").str.strip().replace("", pd.NA)
    if not annotations.dropna().isin(["1", "2"]).all():
        raise ValueError(f"{kind}: unexpected annotation code")
    suppressed = annotations.isin(["1", "2"])
    tokens = data.total_eligibles.astype("string").str.strip().replace("", pd.NA)
    if not tokens.dropna().str.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)").all():
        raise ValueError(f"{kind}: invalid count token; review instead of coercing to NA")
    counts = pd.to_numeric(tokens.str.replace(",", "", regex=False)).astype("Int64")
    if (suppressed & counts.notna()).any():
        raise ValueError(f"{kind}: suppressed cell contains a numeric count")
    data["count"] = counts.mask(suppressed)
    data["is_suppressed"] = suppressed.astype(int)
    wide = data.pivot(index=KEYS, columns="cell", values="count").reindex(columns=expected)
    wide.columns.name = None
    counters = data.groupby(KEYS).is_suppressed.sum().rename(f"{kind}_suppressed_cells")
    wide = wide.join(counters, validate="one_to_one")

    data["status"] = data.status.astype("string").str.strip().str.upper()
    if not data.status.isin(["F", "P"]).all():
        raise ValueError(f"{kind}: review unexpected publication status")
    dates = data.date_of_data.astype("string").str.strip().replace({"": pd.NA, ".": pd.NA})
    data["date_of_data"] = pd.to_datetime(dates, format="%d%b%Y", errors="raise").dt.strftime("%Y-%m-%d").astype("string")
    if data.groupby(KEYS)[["status", "date_of_data"]].nunique(dropna=False).gt(1).any().any():
        raise ValueError(f"{kind}: inconsistent county-month source metadata")
    metadata = data[KEYS + ["status", "date_of_data"]].drop_duplicates().set_index(KEYS).sort_index()
    audit.update({
        "county_months": len(wide), "suppressed_cells": int(suppressed.sum()),
        "missing_unannotated_source_cells": int((counts.isna() & ~suppressed).sum()),
        "absent_category_cells": int(wide[expected].isna().sum().sum() - counts.isna().sum()),
        "category_columns": len(expected),
    })
    return wide, metadata, audit


def build_canonical(sources: dict[str, pd.DataFrame]):
    """Reshape each source before validated one-to-one joins; return data/report."""
    if set(sources) != set(DIMENSIONS):
        raise ValueError("Supply exactly language, age_sex, and race_age sources")
    tables, metadata, audit = {}, {}, {}
    for kind in DIMENSIONS:
        tables[kind], metadata[kind], audit[kind] = clean_source(sources[kind], kind)
    reference = metadata["age_sex"]
    for kind in ("language", "race_age"):
        if not reference.index.equals(metadata[kind].index):
            raise ValueError(f"{kind}: county-month coverage differs across sources; review before joining")
        if not reference.fillna("").equals(metadata[kind].fillna("")):
            raise ValueError(f"{kind}: publication metadata differs across sources; do not mix vintages")
    combined = reference.join(tables["age_sex"], validate="one_to_one")
    combined = combined.join(tables["language"], validate="one_to_one")
    combined = combined.join(tables["race_age"], validate="one_to_one")
    age_columns = _expected_columns("age_sex")
    combined["county_total_is_complete"] = combined[age_columns].notna().all(axis=1)
    combined["county_total_eligibles"] = combined[age_columns].sum(axis=1, min_count=8).astype("Int64")
    ordered = KEYS + ["status", "date_of_data", "county_total_eligibles", "county_total_is_complete"]
    ordered += [f"{kind}_suppressed_cells" for kind in ("age_sex", "language", "race_age")]
    ordered += age_columns + _expected_columns("language") + _expected_columns("race_age")
    canonical = prepare_data(combined.reset_index()[ordered])
    audit["canonical"] = {
        "rows": len(canonical), "columns": len(canonical.columns),
        "months": canonical.month_of_eligibility.nunique(),
        "first_month": canonical.month_of_eligibility.min(), "last_month": canonical.month_of_eligibility.max(),
        "counties": canonical.county.nunique(), "duplicate_keys": int(canonical.duplicated(KEYS).sum()),
        "incomplete_county_totals": int((~canonical.county_total_is_complete).sum()),
        "counties_per_month": canonical.groupby("month_of_eligibility").size().value_counts().to_dict(),
        "missing_california_counties": sorted(set(CALIFORNIA_COUNTIES) - set(canonical.county)),
    }
    return canonical, audit


def compare_snapshot(previous: pd.DataFrame, canonical: pd.DataFrame):
    """Count changed demographic cells without implying why a publisher revised them."""
    prior = prepare_data(previous).set_index(KEYS)
    current = canonical.set_index(KEYS)
    common = prior.index.intersection(current.index)
    columns = [c for c in prior if c in current and c.startswith(("language__", "age_sex__", "race_age__"))]
    left, right = prior.loc[common, columns], current.loc[common, columns]
    changed = ~(left.eq(right).fillna(False) | (left.isna() & right.isna()))
    return {
        "previous_valid_rows": len(prior), "common_rows": len(common),
        "added_rows": len(current.index.difference(prior.index)),
        "removed_rows": len(prior.index.difference(current.index)),
        "changed_demographic_cells_by_family": {
            family: int(changed.filter(regex=f"^{family}__").sum().sum())
            for family in DIMENSIONS
        },
        "note": "Official source snapshots differ in vintage; changed cells are reported, not inferred or overwritten with estimates.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--output", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--report", type=Path, default=ROOT / "outputs/cleaning_report.json")
    parser.add_argument("--compare", type=Path, help="Optional earlier merged CSV to audit against")
    parser.add_argument("--download", action="store_true", help="Fetch the pinned official URLs before building")
    args = parser.parse_args(argv)
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    manifest, sources = {}, {}
    for kind, url in SOURCE_URLS.items():
        path = args.raw_dir / f"{kind}.csv"
        if args.download:
            with urlopen(url, timeout=120) as response:
                payload = response.read()
            # Validate the download before replacing an existing source file.
            if not payload.startswith(b"Month of Eligibility,"):
                raise ValueError(f"{url}: response is not the expected CSV")
            path.write_bytes(payload)
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}; run with --download or supply --raw-dir")
        manifest[kind] = {"url": url, "file": path.name, "bytes": path.stat().st_size,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        sources[kind] = pd.read_csv(path, dtype="string")
    canonical, report = build_canonical(sources)
    report["sources"] = manifest
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    if args.compare:
        report["previous_snapshot_comparison"] = compare_snapshot(pd.read_csv(args.compare), canonical)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".csv.tmp")
    canonical.to_csv(temporary, index=False)
    temporary.replace(args.output)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["canonical"], indent=2))
    return canonical, report


if __name__ == "__main__":
    main()
