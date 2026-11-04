"""Verify the actual dashboard API against the canonical analysis contract."""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlencode

import dashboard
import medi_cal_analysis as analysis
from medi_cal_analysis.data import CALIFORNIA_COUNTIES


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = dashboard.Application()

    def get(self, route, **filters):
        status, mime, body = self.app.response(route + ('?' + urlencode(filters) if filters else ''))
        self.assertEqual(status, 200, body)
        self.assertEqual(mime, 'application/json')
        return json.loads(body)

    def test_comparison_matches_audited_arithmetic_and_coverage(self):
        view = self.get('/api/comparison', month='2026-09', language='spanish')
        self.assertEqual(len(view['counties']), 58)
        self.assertEqual({row['county'] for row in view['counties']}, set(CALIFORNIA_COUNTIES))
        la = next(row for row in view['counties'] if row['county'] == 'Los Angeles')
        self.assertEqual(la['selected_language_count'], 1129822)
        self.assertEqual(la['county_total_eligibles'], 3639204)
        self.assertAlmostEqual(la['language_share'], 1129822/3639204, places=12)
        self.assertEqual(la['status'], 'P')
        self.assertEqual(la['date_of_data'], '2026-09-10')
        self.assertEqual(view['overview']['observed_language_count'], 3505796)
        self.assertEqual(view['overview']['language_count_available_counties'], 56)
        self.assertIsNone(view['overview']['selected_language_count'])
        self.assertIsNone(view['overview']['language_share'])
        self.assertEqual([r['county'] for r in view['counties'][-2:]], ['Alpine','Mono'])
        self.assertTrue(all(r['rank'] is None for r in view['counties'][-2:]))

    def test_county_language_change_preserves_demographic_context(self):
        views = [self.get('/api/county', month='2026-09', language=language, county='Los Angeles') for language in ('spanish','mandarin')]
        self.assertEqual(views[0]['age_sex'], views[1]['age_sex'])
        self.assertEqual(views[0]['race_ethnicity'], views[1]['race_ethnicity'])
        self.assertEqual(views[1]['county']['selected_language_count'], 49336)
        self.assertEqual(len(views[0]['age_sex']), 8)
        self.assertEqual(len(views[0]['race_ethnicity']), 6)
        self.assertEqual(len(views[0]['trend']), 201)
        selected = next(row for row in views[0]['trend'] if row['month_of_eligibility']=='2026-09')
        self.assertEqual(selected['selected_language_count'], views[0]['county']['selected_language_count'])

    def test_unavailable_county_is_retained_without_inferred_zero(self):
        view = self.get('/api/county', month='2026-09', language='spanish', county='Alpine')
        self.assertIsNone(view['county']['selected_language_count'])
        self.assertIsNone(view['county']['language_share'])
        self.assertEqual(view['county']['language_share_unavailable_reason'], 'missing_language_count')
        self.assertTrue(any(row['eligible_count'] is None for row in view['race_ethnicity']))

    def test_observed_count_with_incomplete_denominator_withholds_share(self):
        view = self.get('/api/county', month='2022-05', language='spanish', county='Alpine')
        self.assertEqual(view['county']['selected_language_count'], 12)
        self.assertIsNone(view['county']['county_total_eligibles'])
        self.assertIsNone(view['county']['language_share'])
        self.assertEqual(view['county']['language_share_unavailable_reason'], 'incomplete_county_total')

    def test_all_unavailable_keeps_all_counties_and_null_subtotal(self):
        view = self.get('/api/comparison', month='2026-09', language='unknown')
        self.assertEqual(len(view['counties']),58)
        self.assertEqual(view['overview']['language_count_available_counties'],0)
        self.assertIsNone(view['overview']['observed_language_count'])
        self.assertTrue(all(row['selected_language_count'] is None and row['language_share'] is None and row['rank'] is None for row in view['counties']))

    def test_metadata_has_pinned_provenance_and_distinct_labels(self):
        value = self.get('/api/metadata')
        self.assertEqual(value['defaults']['month'], '2026-09')
        self.assertEqual(value['source']['sha256'], '8bd21b92046753bee440ef290192b8b260fb317953e2e2fca553ff2e3f46d803')
        labels = {row['id']:row['label'] for row in value['languages']}
        self.assertEqual(labels['asl'],'ASL')
        self.assertEqual(labels['missing_unknown'],'Missing/Unknown')
        self.assertEqual(labels['unknown'],'Unknown')

    def test_geojson_matches_canonical_keys_and_has_real_ca_polygons(self):
        geometry = self.get('/api/geometry')
        self.assertEqual(len(geometry['features']), 58)
        self.assertEqual({f['properties']['county'] for f in geometry['features']}, set(CALIFORNIA_COUNTIES))
        def check(coordinates):
            if isinstance(coordinates[0], (float,int)):
                self.assertTrue(-125 < coordinates[0] < -113)
                self.assertTrue(32 < coordinates[1] < 43)
            else:
                for part in coordinates:
                    check(part)
        for feature in geometry['features']:
            check(feature['geometry']['coordinates'])
        self.assertIn('census.gov', geometry['source'])

    def test_csv_includes_all_counties_nulls_denominators_and_provenance(self):
        status, mime, body = self.app.response('/api/export.csv?month=2026-09&language=spanish')
        self.assertEqual((status,mime),(200,'text/csv'))
        rows = list(csv.DictReader(io.StringIO(body.decode('utf-8-sig'))))
        self.assertEqual(len(rows),58)
        alpine = next(row for row in rows if row['county']=='Alpine')
        self.assertEqual(alpine['selected_language_count'],'')
        self.assertEqual(alpine['language_share'],'')
        la = next(row for row in rows if row['county']=='Los Angeles')
        self.assertEqual(float(la['county_total_eligibles']),3639204)
        self.assertEqual(la['source_sha256'],self.get('/api/metadata')['source']['sha256'])

    def test_invalid_selections_fail_without_silently_changing_filters(self):
        for target in ('/api/comparison?month=2026-99&language=spanish',
                       '/api/comparison?month=2026-09&language=invalid',
                       '/api/comparison?month=2026-09&month=2026-08&language=spanish',
                       '/api/county?month=2026-09&language=spanish&county=STATEWIDE',
                       '/api/county?month=2026-09&language=spanish',
                       '/api/comparison?month=2026-09&language='):
            with self.subTest(target=target):
                status,mime,body = self.app.response(target)
                self.assertEqual(status,400)
                self.assertIn('error',json.loads(body))
        self.assertEqual(self.app.response('/raw/by-primary-language-certified-eligibles.csv')[0],404)
        self.assertEqual(self.app.response('/../../.git/config')[0],404)

    def test_filtered_payloads_replace_full_raw_download(self):
        for route in ('/api/metadata','/api/comparison?month=2026-09&language=spanish', '/api/county?month=2026-09&language=spanish&county=Los+Angeles'):
            self.assertLess(len(self.app.response(route)[2]),100000)
        self.assertLess(len(self.app.response('/api/geometry')[2]),500000)

    def test_changed_dataset_file_invalidates_cached_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'snapshot.csv'
            path.write_bytes(analysis.DEFAULT_DATA_PATH.read_bytes())
            first=dashboard.load_dataset(path)
            self.assertIs(first,dashboard.load_dataset(path))
            frame=first.data.copy()
            match=frame['month_of_eligibility'].eq('2026-09') & frame['county'].eq('Los Angeles')
            frame.loc[match,'language__spanish']=1129821
            frame.to_csv(path,index=False)
            second=dashboard.load_dataset(path)
            self.assertIsNot(first,second)
            self.assertNotEqual(first.source['sha256'],second.source['sha256'])
            la=next(row for row in second.comparison('2026-09','spanish')['counties'] if row['county']=='Los Angeles')
            self.assertEqual(la['selected_language_count'],1129821)

    def test_incomplete_county_grid_fails_before_rendering(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'incomplete.csv'
            dashboard.load_dataset().data.iloc[1:].to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, 'all 58 county rows'):
                dashboard.load_dataset(path)


if __name__ == '__main__':
    unittest.main()
