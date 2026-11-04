"""Offline Medi-Cal language-access planning. Run: .venv/bin/python dashboard.py"""
from functools import lru_cache
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import argparse
import csv
import gzip
import io
import json
import time

import pandas as pd
import medi_cal_analysis as analysis
from medi_cal_analysis.data import CALIFORNIA_COUNTIES, normalize_county, normalize_month

ROOT = Path(__file__).resolve().parent
GEOMETRY_PATH = ROOT / 'data/california_counties.geojson'
LANGUAGE_LABELS = {
    'asl': 'ASL', 'missing_unknown': 'Missing/Unknown', 'unknown': 'Unknown',
    'other_non_eng': 'Other non-English', 'other_sign': 'Other sign language',
}


def records(frame):
    """Keep nullable pandas values as JSON null, including all-unavailable sums."""
    return json.loads(frame.to_json(orient='records', double_precision=15))


class Dataset:
    def __init__(self, path):
        self.data = analysis.load_data(path)
        self.months = analysis.get_available_months(self.data)
        self.languages = analysis.get_available_languages(self.data)
        if any(set(group['county']) != set(CALIFORNIA_COUNTIES) for _, group in self.data.groupby('month_of_eligibility')):
            raise ValueError('The dashboard requires all 58 county rows in each month. Rebuild or restore the canonical snapshot.')
        self.source = {
            'file': str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name,
            'sha256': sha256(path.read_bytes()).hexdigest(),
            'rows': len(self.data), 'first_month': self.months[0], 'last_month': self.months[-1],
            'publisher': 'California Department of Health Care Services',
        }

    def metadata(self):
        return {
            'months': self.months,
            'languages': [{'id': item, 'label': LANGUAGE_LABELS.get(item, item.replace('_', ' ').title())} for item in self.languages],
            'counties': list(CALIFORNIA_COUNTIES), 'source': self.source,
            'defaults': {'month': self.months[-1], 'language': 'spanish' if 'spanish' in self.languages else self.languages[0], 'county': 'Los Angeles'},
        }

    @lru_cache(maxsize=128)
    def comparison(self, month, language):
        ranking = analysis.get_county_ranking(self.data, month, language)
        publication = self.data[['month_of_eligibility', 'county', 'status', 'date_of_data']]
        ranking = ranking.merge(publication, on=['month_of_eligibility', 'county'], validate='one_to_one')
        return {'source_sha256': self.source['sha256'], 'month': month, 'language': language,
                'overview': records(analysis.get_month_summary(self.data, month, language))[0], 'counties': records(ranking)}

    @lru_cache(maxsize=512)
    def county(self, month, language, county):
        detail = records(analysis.get_county_summary(self.data, month, language, county))[0]
        publication = self.data.loc[self.data['month_of_eligibility'].eq(month) & self.data['county'].eq(county), ['status', 'date_of_data']]
        detail.update(records(publication)[0])
        # The trend uses the same validated numerator as the comparison, without
        # re-reading a different raw snapshot or summing monthly observations.
        trend = self.data.loc[self.data['county'].eq(county), ['month_of_eligibility', f'language__{language}']].rename(columns={f'language__{language}': 'selected_language_count'})
        return {'source_sha256': self.source['sha256'], 'county': detail,
                'age_sex': records(analysis.get_age_sex_summary(self.data, month, county)),
                'race_ethnicity': records(analysis.get_race_ethnicity_summary(self.data, month, county)),
                'trend': records(trend.sort_values('month_of_eligibility'))}


@lru_cache(maxsize=2)
def _dataset(path, modified, size):
    return Dataset(Path(path))


def load_dataset(path=analysis.DEFAULT_DATA_PATH):
    path = Path(path).resolve()
    stat = path.stat()
    return _dataset(str(path), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=2)
def _geometry(path, modified, size):
    geometry = json.loads(Path(path).read_text())
    features = geometry.get('features', [])
    names = [feature['properties']['county'] for feature in features]
    if geometry.get('type') != 'FeatureCollection' or len(names) != 58 or set(names) != set(CALIFORNIA_COUNTIES):
        raise ValueError('County geometry must match all 58 canonical California county names exactly.')
    for feature in features:
        if feature['geometry']['type'] not in {'Polygon', 'MultiPolygon'}:
            raise ValueError('County geometry must contain polygons.')
    return geometry


def load_geometry(path=GEOMETRY_PATH):
    path = Path(path).resolve()
    stat = path.stat()
    return _geometry(str(path), stat.st_mtime_ns, stat.st_size)


class Application:
    """Small same-origin JSON views; analysis and validity rules stay in Python."""
    def __init__(self, data_path=analysis.DEFAULT_DATA_PATH, geometry_path=GEOMETRY_PATH):
        self.data_path, self.geometry_path = data_path, geometry_path

    def response(self, target):
        route = urlparse(target)
        try:
            if route.path in {'/', '/app.js', '/styles.css'}:
                name, mime = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/styles.css': ('styles.css', 'text/css')}[route.path]
                return 200, mime, (ROOT / 'web' / name).read_bytes()
            if route.path == '/api/geometry':
                value = load_geometry(self.geometry_path)
            elif route.path in {'/api/metadata', '/api/comparison', '/api/county', '/api/export.csv'}:
                dataset = load_dataset(self.data_path)
                if route.path == '/api/metadata':
                    value = dataset.metadata()
                else:
                    query = parse_qs(route.query, keep_blank_values=True)
                    expected = {'month', 'language', 'county'} if route.path == '/api/county' else {'month', 'language'}
                    if set(query) != expected or any(len(values) != 1 or not values[0] for values in query.values()):
                        raise ValueError('Choose one valid value for each required filter: ' + ', '.join(sorted(expected)))
                    month, language = normalize_month(query['month'][0]), query['language'][0]
                    if month not in dataset.months or language not in dataset.languages:
                        raise ValueError('The selected month or language is unavailable. Reload to refresh filter options.')
                    if route.path == '/api/county':
                        value = dataset.county(month, language, normalize_county(query['county'][0]))
                    else:
                        value = dataset.comparison(month, language)
                        if route.path == '/api/export.csv':
                            stream = io.StringIO(newline='')
                            fields = ['month_of_eligibility', 'language', 'county', 'rank', 'selected_language_count', 'county_total_eligibles', 'county_total_is_complete', 'language_share', 'language_share_unavailable_reason', 'status', 'date_of_data', 'source_sha256']
                            writer = csv.DictWriter(stream, fields, extrasaction='ignore', lineterminator='\r\n')
                            writer.writeheader()
                            for row in value['counties']:
                                writer.writerow({**row, 'source_sha256': dataset.source['sha256']})
                            return 200, 'text/csv', stream.getvalue().encode('utf-8-sig')
            else:
                return 404, 'application/json', b'{"error":"Page not found."}'
            return 200, 'application/json', json.dumps(value, allow_nan=False, separators=(',', ':')).encode()
        except ValueError as error:
            return 400, 'application/json', json.dumps({'error': str(error)}).encode()
        except (OSError, KeyError):
            return 503, 'application/json', json.dumps({'error': 'The local dataset or county boundaries could not be loaded. Check the files and restart the dashboard.'}).encode()


def make_handler(application):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            status, mime, content = application.response(self.path)
            self.send_response(status)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Vary', 'Accept-Encoding')
            if 'gzip' in self.headers.get('Accept-Encoding', '') and len(content) > 1024:
                content = gzip.compress(content)
                self.send_header('Content-Encoding', 'gzip')
            if urlparse(self.path).path == '/api/export.csv' and status == 200:
                self.send_header('Content-Disposition', 'attachment; filename="medi-cal-county-comparison.csv"')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                pass  # A newer filter request superseded this response.
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8050)
    args = parser.parse_args()
    started = time.perf_counter()
    try:
        load_dataset()
        load_geometry()
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'Cannot start dashboard: {error}\nCheck the canonical CSV and data/california_counties.geojson.\n')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(Application()))
    print(f'Medi-Cal dashboard: http://127.0.0.1:{args.port} (validated startup {time.perf_counter()-started:.2f}s)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
