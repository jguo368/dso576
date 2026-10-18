"""Raw-source integration checks for suppression, category pivots, and joins."""

import unittest

import pandas as pd

from medi_cal_analysis.cleaning import build_canonical, clean_source, compare_snapshot
from medi_cal_analysis.data import AGE_GROUPS, RACES, SEXES


def source_fixture():
    sources = {name: [] for name in ("language", "age_sex", "race_age")}
    ages = dict(zip(AGE_GROUPS, ["Age 00-18", "Age 19-44", "Age 45-64", "Age 65+"]))
    for county in [" alameda ", "Alpine"]:
        base = {"Month of Eligibility": "2025-01", "County": county,
                "Annotation Code": None, "Status": "F", "Date of Data": "10FEB2025"}
        for language, count in [("Spanish", "1,000"), ("Mandarin", "0")]:
            sources["language"].append({**base, "Language": language, "Total Eligibles": count})
        for age in AGE_GROUPS:
            for sex in SEXES:
                sources["age_sex"].append({**base, "Age Group": ages[age], "Gender": sex.title(), "Total Eligibles": "250"})
            for race in RACES:
                sources["race_age"].append({**base, "Age Group": ages[age], "Ethnicity": race.replace("_", "/" if race == "ai_an" else " ").upper(), "Total Eligibles": "80"})
    return {kind: pd.DataFrame(rows) for kind, rows in sources.items()}


class RawCleaningTests(unittest.TestCase):
    def test_one_to_one_join_complete_totals_and_observed_zero(self):
        sources = source_fixture()
        data, report = build_canonical(sources)
        self.assertEqual(data.shape, (2, 74))
        self.assertEqual(data.county.tolist(), ["Alameda", "Alpine"])
        self.assertEqual(data.county_total_eligibles.tolist(), [2000, 2000])
        self.assertTrue(data.county_total_is_complete.all())
        self.assertEqual(data.language__mandarin.tolist(), [0, 0])
        self.assertTrue(data.language__arabic.isna().all())
        self.assertEqual(report["canonical"]["duplicate_keys"], 0)
        self.assertEqual(data.date_of_data.tolist(), ["2025-02-10", "2025-02-10"])
        self.assertEqual(len(sources["age_sex"]), 16)

    def test_primary_complementary_and_absent_cells_remain_unavailable(self):
        sources = source_fixture()
        sources["language"].loc[0, ["Total Eligibles", "Annotation Code"]] = [None, "1"]
        sources["age_sex"].loc[0, ["Total Eligibles", "Annotation Code"]] = [None, "2"]
        # A category absent entirely from one county is also not a zero.
        sources["race_age"] = sources["race_age"].drop(index=0)
        data, report = build_canonical(sources)
        row = data.iloc[0]
        self.assertTrue(pd.isna(row.language__spanish))
        self.assertFalse(row.county_total_is_complete)
        self.assertTrue(pd.isna(row.county_total_eligibles))
        self.assertEqual(row.language_suppressed_cells, 1)
        self.assertEqual(row.age_sex_suppressed_cells, 1)
        self.assertEqual(row.race_age_suppressed_cells, 0)
        self.assertEqual(report["race_age"]["absent_category_cells"], 1)

    def test_exclusions_happen_before_category_validation(self):
        source = source_fixture()["language"]
        extra = source.iloc[[0]].copy()
        extra["County"] = "STATEWIDE"
        extra["Language"] = "STATEWIDE"
        source = pd.concat([source, extra], ignore_index=True)
        wide, _, report = clean_source(source, "language")
        self.assertEqual(len(wide), 2)
        self.assertEqual(report["invalid_county_rows"], 1)
        self.assertEqual(report["excluded_rows"], 1)

    def test_duplicate_unknown_and_malformed_source_cells_fail(self):
        for mutation, message in [
            (lambda d: pd.concat([d, d.iloc[[0]]]), "duplicate source cells"),
            (lambda d: d.assign(Language="unreviewed category"), "unexpected categories"),
            (lambda d: d.assign(**{"Total Eligibles": "1,00"}), "invalid count token"),
            (lambda d: d.assign(**{"Annotation Code": "3"}), "annotation code"),
            (lambda d: d.assign(**{"Annotation Code": "1"}), "suppressed cell contains"),
        ]:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                clean_source(mutation(source_fixture()["language"]), "language")

    def test_mismatched_coverage_or_vintage_fails_before_merge(self):
        sources = source_fixture()
        sources["language"] = sources["language"].iloc[:2]
        with self.assertRaisesRegex(ValueError, "coverage differs"):
            build_canonical(sources)
        sources = source_fixture()
        sources["language"]["Date of Data"] = "11FEB2025"
        with self.assertRaisesRegex(ValueError, "metadata differs"):
            build_canonical(sources)

    def test_comparison_counts_missing_to_observed_and_changed_counts(self):
        data, _ = build_canonical(source_fixture())
        previous = data.copy()
        previous.loc[0, "language__mandarin"] = pd.NA
        previous.loc[1, "language__spanish"] = 999
        comparison = compare_snapshot(previous, data)
        self.assertEqual(comparison["changed_demographic_cells_by_family"]["language"], 2)
        self.assertEqual(comparison["added_rows"], 0)


if __name__ == "__main__":
    unittest.main()
