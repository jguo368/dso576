"""Run every Phase 2 output in a new process and export a reviewable example."""

import argparse
import json
from pathlib import Path

from . import (
    DEFAULT_DATA_PATH, get_age_sex_summary, get_available_languages,
    get_available_months, get_county_ranking, get_county_summary,
    get_language_share, get_map_data, get_month_summary,
    get_race_ethnicity_summary, load_data,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--month", help="Defaults to the latest available month")
    parser.add_argument("--language", default="spanish")
    parser.add_argument("--county", default="Los Angeles")
    parser.add_argument("--output", type=Path, default=Path("outputs/dashboard_preview.json"))
    args = parser.parse_args(argv)
    data = load_data(args.data)
    month = args.month or get_available_months(data)[-1]
    outputs = {
        "overview": get_month_summary(data, month, args.language),
        "map": get_map_data(data, month, args.language),
        "ranking": get_county_ranking(data, month, args.language),
        "county_detail": get_county_summary(data, month, args.language, args.county),
        "language_share": get_language_share(data, month, args.language),
        "age_sex_context": get_age_sex_summary(data, month, args.county),
        "race_ethnicity_context": get_race_ethnicity_summary(data, month, args.county),
    }
    result = {
        "available_months": get_available_months(data),
        "available_languages": get_available_languages(data),
        **{name: json.loads(frame.to_json(orient="records")) for name, frame in outputs.items()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Verified all backend outputs for {month} / {args.language} / {args.county}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
