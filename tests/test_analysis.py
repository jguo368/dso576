"""Contract and metric tests; run with python -m unittest discover -s tests -v."""

import tempfile
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

import medi_cal_analysis as analysis
from medi_cal_analysis.data import AGE_GROUPS, CALIFORNIA_COUNTIES, RACES, SEXES


def county_row(county="Alameda", month="2025-01"):
    row = {
        "month_of_eligibility": month,
        "county": county,
        "status": "F",
        "date_of_data": "2025-02-10",
        "county_total_eligibles": 240,
        "county_total_is_complete": "True",
        "age_sex_suppressed_cells": 0,
        "language_suppressed_cells": 0,
        "race_age_suppressed_cells": 0,
        "language__spanish": 60,
        "language__mandarin": 0,
    }
    row.update({f"age_sex__{age}__{sex}": 30 for age in AGE_GROUPS for sex in SEXES})
    row.update({f"race_age__{age}__{race}": 10 for age in AGE_GROUPS for race in RACES})
    return row


def example_data():
    rows = [county_row(county) for county in ("Alameda", "Alpine", "Amador", "Butte", "Colusa")]
    rows[1].update({
        "language__spanish": np.nan,
        "language_suppressed_cells": 1,
        "county_total_is_complete": "False",
        "county_total_eligibles": 210,  # A partial total must not be displayed.
        "age_sex__age_00_18__female": np.nan,
        "age_sex_suppressed_cells": 1,
    })
    rows[2].update({"race_age__age_00_18__ai_an": np.nan, "race_age_suppressed_cells": 1})
    rows[3].update({"county_total_eligibles": 0, "language__spanish": 0})
    rows[3].update({f"age_sex__{age}__{sex}": 0 for age in AGE_GROUPS for sex in SEXES})
    rows[3].update({f"race_age__{age}__{race}": 0 for age in AGE_GROUPS for race in RACES})
    rows[4].update({
        "language__spanish": 20,
        "county_total_is_complete": False,
        "age_sex__age_00_18__female": np.nan,
        "age_sex_suppressed_cells": 1,
    })
    rows.append(county_row(month="2025-02"))
    return pd.DataFrame(rows)


class PreparationTests(unittest.TestCase):
    def test_standardization_exclusions_and_no_input_mutation(self):
        raw = pd.DataFrame([
            county_row("  los   ANGELES  ", "2025-01-25"),
            county_row("Invalid County Code"),
            county_row("Statewide"),
            county_row(None),
            county_row("Alpine", "2025-13"),
        ])
        original = raw.copy(deep=True)
        data = analysis.prepare_data(raw)
        assert_frame_equal(raw, original)
        self.assertEqual(data["county"].tolist(), ["Los Angeles"])
        self.assertEqual(data["month_of_eligibility"].tolist(), ["2025-01"])
        self.assertEqual(data.attrs["preparation_report"], {
            "input_rows": 5, "invalid_month_rows": 1, "invalid_county_rows": 3,
            "excluded_rows": 4, "output_rows": 1,
        })
        self.assertEqual(str(data["county"].dtype), "string")
        self.assertEqual(str(data["county_total_is_complete"].dtype), "boolean")
        self.assertEqual(str(data["language__spanish"].dtype), "Float64")

    def test_duplicates_after_normalization_raise(self):
        raw = pd.DataFrame([county_row(), county_row(" alameda ", "2025-01-15")])
        with self.assertRaisesRegex(ValueError, "Duplicate county-month"):
            analysis.prepare_data(raw)

    def test_false_string_and_missing_values_are_preserved(self):
        data = analysis.prepare_data(example_data())
        row = data.loc[data["county"].eq("Alpine")].iloc[0]
        self.assertFalse(row["county_total_is_complete"])
        self.assertTrue(pd.isna(row["county_total_eligibles"]))
        self.assertTrue(pd.isna(row["language__spanish"]))

    def test_invalid_values_fail_explicitly(self):
        cases = [
            ("county_total_is_complete", "maybe", "must contain True or False"),
            ("county_total_is_complete", None, "must contain True or False"),
            ("language__spanish", "suppressed", "numeric counts"),
            ("language__spanish", -1, "nonnegative whole counts"),
            ("language__spanish", 1.5, "nonnegative whole counts"),
            ("language__spanish", np.inf, "nonnegative whole counts"),
            ("language_suppressed_cells", np.nan, "nonnegative whole counts"),
            ("county_total_eligibles", 239, "Complete county totals"),
            ("age_sex__age_00_18__female", np.nan, "Complete county totals"),
            ("language__spanish", 241, "exceeds a complete county total"),
            ("status", "TYPO", "status must contain"),
            ("status", None, "status must contain"),
            ("date_of_data", "not a date", "date_of_data must be"),
            ("date_of_data", "2025-02-30", "invalid calendar date"),
        ]
        for column, value, message in cases:
            with self.subTest(column=column, value=value):
                row = county_row()
                row[column] = value
                with self.assertRaisesRegex(ValueError, message):
                    analysis.prepare_data(pd.DataFrame([row]))

    def test_missing_or_unexpected_demographic_columns_raise(self):
        raw = pd.DataFrame([county_row()])
        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            analysis.prepare_data(raw.drop(columns="age_sex__age_00_18__female"))
        with self.assertRaisesRegex(ValueError, "unexpected demographic categories"):
            analysis.prepare_data(raw.assign(age_sex__unexpected__female=1))
        with self.assertRaisesRegex(ValueError, "At least one language__"):
            analysis.prepare_data(raw.drop(columns=["language__spanish", "language__mandarin"]))

    def test_publication_metadata_is_required_and_normalized(self):
        raw = pd.DataFrame([county_row(), county_row("Alpine"), county_row("Amador")])
        for column in ("status", "date_of_data"):
            with self.subTest(column=column), self.assertRaisesRegex(ValueError, "Missing required columns"):
                analysis.prepare_data(raw.drop(columns=column))
        raw.loc[0, "status"] = " p "
        raw.loc[0, "date_of_data"] = "10FEB2025"
        raw.loc[1, "date_of_data"] = " . "
        raw.loc[2, "date_of_data"] = None
        result = analysis.prepare_data(raw)
        self.assertEqual(result.loc[0, "status"], "P")
        self.assertEqual(result.loc[0, "date_of_data"], "2025-02-10")
        self.assertTrue(result.loc[1:, "date_of_data"].isna().all())

    def test_load_from_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "canonical.csv"
            example_data().to_csv(path, index=False)
            data = analysis.load_data(path)
            self.assertEqual(len(data), 6)
            self.assertFalse(data.duplicated(["month_of_eligibility", "county"]).any())


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.data = analysis.prepare_data(example_data())

    def test_selectors_and_filters(self):
        self.assertEqual(analysis.get_available_months(self.data), ["2025-01", "2025-02"])
        self.assertEqual(analysis.get_available_languages(self.data), ["mandarin", "spanish"])
        result = analysis.get_county_metrics(self.data, "2025-02-14", "language__SPANISH")
        self.assertEqual(result["county"].tolist(), ["Alameda"])
        self.assertEqual(result.iloc[0]["selected_language_count"], 60)
        self.assertEqual(result.iloc[0]["language_share"], 0.25)

    def test_share_requires_count_and_complete_positive_total(self):
        result = analysis.get_language_share(self.data, "2025-01", "spanish").set_index("county")
        self.assertEqual(result.loc["Alameda", "language_share"], 0.25)
        expected = {
            "Alpine": "missing_language_count",
            "Butte": "nonpositive_county_total",
            "Colusa": "incomplete_county_total",
        }
        for county, reason in expected.items():
            self.assertTrue(pd.isna(result.loc[county, "language_share"]))
            self.assertFalse(result.loc[county, "language_share_is_available"])
            self.assertEqual(result.loc[county, "language_share_unavailable_reason"], reason)
        zero = analysis.get_county_summary(self.data, "2025-01", "mandarin", "Alameda")
        self.assertEqual(zero.iloc[0]["language_share"], 0.0)

    def test_ranking_ties_zero_and_missing(self):
        ranked = analysis.get_county_ranking(self.data, "2025-01", "spanish")
        self.assertEqual(ranked["county"].tolist(), ["Alameda", "Amador", "Colusa", "Butte", "Alpine"])
        self.assertEqual(ranked["rank"].dropna().tolist(), [1, 1, 3, 4])
        self.assertTrue(pd.isna(ranked.iloc[-1]["selected_language_count"]))
        self.assertTrue(pd.isna(ranked.iloc[-1]["rank"]))
        self.assertEqual(len(analysis.get_county_ranking(self.data, "2025-01", "spanish", limit=2)), 2)
        for limit in (0, -1, 1.5, True):
            with self.subTest(limit=limit), self.assertRaisesRegex(ValueError, "limit"):
                analysis.get_county_ranking(self.data, "2025-01", "spanish", limit=limit)

    def test_map_and_detail_are_reusable_copies(self):
        original = self.data.copy(deep=True)
        mapped = analysis.get_map_data(self.data, "2025-01", "spanish")
        self.assertEqual(len(mapped), 5)
        self.assertEqual(mapped["county"].nunique(), 5)
        detail = analysis.get_county_summary(self.data, "2025-01", "spanish", " alAMeda ")
        self.assertEqual(len(detail), 1)
        self.assertEqual(detail.iloc[0]["county_total_eligibles"], 240)
        mapped.loc[0, "selected_language_count"] = 999
        assert_frame_equal(self.data, original)

    def test_demographics_aggregate_with_strict_missing_propagation(self):
        cells = analysis.get_age_sex_summary(self.data, "2025-01", "Alpine")
        self.assertEqual(len(cells), 8)
        self.assertEqual(cells["eligible_count"].isna().sum(), 1)
        self.assertTrue(cells["share_of_county"].isna().all())
        ages = analysis.get_age_sex_summary(self.data, "2025-01", "Alpine", group_by="age").set_index("age_group")
        self.assertTrue(pd.isna(ages.loc["age_00_18", "eligible_count"]))
        self.assertFalse(ages.loc["age_00_18", "is_complete"])
        self.assertEqual(ages.loc["age_00_18", "missing_cells"], 1)
        self.assertEqual(ages.loc["age_19_44", "eligible_count"], 60)
        sexes = analysis.get_age_sex_summary(self.data, "2025-01", "Alameda", group_by="sex")
        self.assertEqual(sexes["eligible_count"].tolist(), [120, 120])
        self.assertEqual(sexes["share_of_county"].tolist(), [0.5, 0.5])
        races = analysis.get_race_ethnicity_summary(self.data, "2025-01", "Amador").set_index("race_ethnicity")
        self.assertTrue(pd.isna(races.loc["ai_an", "eligible_count"]))
        self.assertTrue(pd.isna(races.loc["ai_an", "share_of_county"]))
        self.assertEqual(races.loc["asian", "eligible_count"], 40)
        self.assertEqual(races.loc["asian", "required_cells"], 4)
        self.assertEqual(len(analysis.get_race_ethnicity_summary(self.data, "2025-01", "Amador", group_by="race_age")), 24)
        race_ages = analysis.get_race_ethnicity_summary(self.data, "2025-01", "Amador", group_by="age")
        self.assertTrue(pd.isna(race_ages.iloc[0]["eligible_count"]))
        self.assertEqual(race_ages.iloc[1]["eligible_count"], 60)

    def test_month_summary_reports_partial_coverage(self):
        summary = analysis.get_month_summary(self.data, "2025-01", "spanish").iloc[0]
        self.assertEqual(summary["county_count"], 5)
        self.assertEqual(summary["missing_counties"], 53)
        self.assertEqual(summary["language_count_available_counties"], 4)
        self.assertEqual(summary["language_count_missing_counties"], 1)
        self.assertEqual(summary["observed_language_count"], 140)
        self.assertFalse(summary["selected_language_count_is_complete"])
        self.assertTrue(pd.isna(summary["selected_language_count"]))
        self.assertTrue(pd.isna(summary["language_share"]))

    def test_full_coverage_summary_uses_totals_not_average_shares(self):
        raw = pd.DataFrame([county_row(county) for county in CALIFORNIA_COUNTIES])
        raw.loc[0, "age_sex__age_00_18__female"] = 270
        raw.loc[0, "county_total_eligibles"] = 480
        data = analysis.prepare_data(raw)
        summary = analysis.get_month_summary(data, "2025-01", "spanish").iloc[0]
        self.assertEqual(summary["selected_language_count"], 60 * 58)
        self.assertEqual(summary["county_total_eligibles"], 240 * 59)
        self.assertAlmostEqual(summary["language_share"], (60 * 58) / (240 * 59))
        raw["language__spanish"] = np.nan
        missing_summary = analysis.get_month_summary(analysis.prepare_data(raw), "2025-01", "spanish").iloc[0]
        self.assertTrue(pd.isna(missing_summary["observed_language_count"]))
        self.assertTrue(pd.isna(missing_summary["selected_language_count"]))

    def test_invalid_selections_raise_actionable_errors(self):
        for month in ("bad", "2025-13", "2025-01-32", "2024-01"):
            with self.subTest(month=month), self.assertRaises(ValueError):
                analysis.get_map_data(self.data, month, "spanish")
        with self.assertRaisesRegex(ValueError, "Unknown language"):
            analysis.get_map_data(self.data, "2025-01", "fake")
        for county in ("Statewide", "Yolo"):
            with self.subTest(county=county), self.assertRaises(ValueError):
                analysis.get_county_summary(self.data, "2025-01", "spanish", county)
        for function in (analysis.get_age_sex_summary, analysis.get_race_ethnicity_summary):
            with self.assertRaisesRegex(ValueError, "group_by"):
                function(self.data, "2025-01", "Alameda", group_by="language")


class CanonicalDataTests(unittest.TestCase):
    def test_all_mvp_outputs_from_team_csv(self):
        data = analysis.load_data()
        original = data.copy(deep=True)
        self.assertFalse(data.duplicated(["month_of_eligibility", "county"]).any())
        self.assertTrue(data["county"].isin(CALIFORNIA_COUNTIES).all())
        self.assertTrue(data.groupby("month_of_eligibility")["county"].nunique().eq(58).all())
        self.assertEqual(data.attrs["preparation_report"]["output_rows"], len(data))
        months = analysis.get_available_months(data)
        for month in (months[0], months[-1]):
            source = data.loc[data["month_of_eligibility"].eq(month)].set_index("county")
            for language in analysis.get_available_languages(data):
                with self.subTest(month=month, language=language):
                    mapped = analysis.get_map_data(data, month, language).set_index("county")
                    self.assertEqual(len(mapped), len(source))
                    pd.testing.assert_series_equal(
                        mapped["selected_language_count"], source[f"language__{language}"], check_names=False
                    )
                    valid = source["county_total_is_complete"] & source["county_total_eligibles"].gt(0)
                    expected = (source[f"language__{language}"] / source["county_total_eligibles"]).where(valid)
                    pd.testing.assert_series_equal(mapped["language_share"], expected, check_names=False)
                    ranking = analysis.get_county_ranking(data, month, language)
                    self.assertTrue(ranking["selected_language_count"].dropna().is_monotonic_decreasing)
                    self.assertEqual(len(analysis.get_month_summary(data, month, language)), 1)
            for county in source.index:
                age = analysis.get_age_sex_summary(data, month, county, group_by="age")
                race = analysis.get_race_ethnicity_summary(data, month, county)
                self.assertEqual(len(age), 4)
                self.assertEqual(len(race), 6)
        detail = analysis.get_county_summary(data, months[-1], "mandarin", "Los Angeles")
        self.assertEqual(len(detail), 1)
        assert_frame_equal(data, original)


if __name__ == "__main__":
    unittest.main()
