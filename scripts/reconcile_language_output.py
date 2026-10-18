"""Compare an individual long language output with the earlier team Git snapshot."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from medi_cal_analysis.cleaning import _slug
from medi_cal_analysis.data import prepare_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--individual", type=Path, default=ROOT / "outputs/language_cleaning/cleaned_language_eligibles.csv")
    parser.add_argument("--team-revision", default="f8d28e9:dso576/project/medi_cal_merged_county_month.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/reconciliation_report.json")
    args = parser.parse_args()
    team_bytes = subprocess.check_output(["git", "show", args.team_revision], cwd=ROOT)
    team = prepare_data(pd.read_csv(io.BytesIO(team_bytes)))
    individual = pd.read_csv(args.individual, dtype="string")
    valid = individual.loc[individual.map_eligible.str.casefold().eq("true")].copy()
    valid["language"] = valid.language.map(_slug)
    long = team.melt(id_vars=["month_of_eligibility", "county"],
                     value_vars=[c for c in team if c.startswith("language__")],
                     var_name="language", value_name="team_count")
    long["language"] = long.language.str.removeprefix("language__")
    joined = valid.merge(long, left_on=["month", "county", "language"],
                        right_on=["month_of_eligibility", "county", "language"],
                        how="left", validate="one_to_one", indicator=True)
    left = pd.to_numeric(joined.eligible_count).astype("Float64")
    right = pd.to_numeric(joined.team_count).astype("Float64")
    equal = left.eq(right).fillna(False) | (left.isna() & right.isna())
    report = {
        "local_artifact": str(args.individual.relative_to(ROOT)) if args.individual.is_relative_to(ROOT) else str(args.individual),
        "local_artifact_sha256": hashlib.sha256(args.individual.read_bytes()).hexdigest(),
        "team_artifact_git_revision": args.team_revision,
        "team_artifact_sha256": hashlib.sha256(team_bytes).hexdigest(),
        "local_rows": len(individual), "local_map_eligible_rows": len(valid),
        "matched_source_cells": int(joined._merge.eq("both").sum()),
        "unmatched_individual_cells": int(joined._merge.ne("both").sum()),
        "different_counts_or_missingness": int((~equal).sum()),
        "local_suppressed_count_with_numeric_value": int((
            individual.is_suppressed.str.casefold().eq("true")
            & pd.to_numeric(individual.eligible_count).notna()
        ).sum()),
        "limitations": [
            "Individual age/sex and race/ethnicity cleaning scripts were not provided.",
            "Output agreement does not establish all teammates reviewed or approved a shared cleaning approach.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
