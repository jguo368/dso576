"""Offline Medi-Cal language-access planning. Run: .venv/bin/python dashboard.py"""
from functools import lru_cache
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
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


def _format_count(value):
    """Format nullable dashboard values for Streamlit metric cards."""
    return 'Unavailable' if value is None or pd.isna(value) else f'{int(value):,}'


def _format_percent(value):
    """Format nullable fractional shares as percentages."""
    return 'Unavailable' if value is None or pd.isna(value) else f'{float(value):.1%}'


def streamlit_main():
    """Render the dashboard inside Streamlit without starting a second server."""
    import streamlit as st

    st.set_page_config(
        page_title='Medi-Cal language-access planning',
        page_icon='🏥',
        layout='wide',
    )
    st.markdown(
        """
        <style>
        .block-container {max-width: 1400px; padding-top: 2rem;}
        [data-testid="stMetric"] {background: #f4f8f5; border: 1px solid #dce7df;
            border-radius: .5rem; padding: .8rem 1rem;}
        .dashboard-note {color: #52665b; font-size: .92rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    try:
        dataset = load_dataset()
        geometry = load_geometry()
    except (OSError, ValueError, KeyError) as error:
        st.error(f'Cannot load the bundled dashboard data: {error}')
        st.stop()

    metadata = dataset.metadata()
    language_labels = {item['id']: item['label'] for item in metadata['languages']}

    st.caption('58 COUNTIES · ONE CONNECTED VIEW')
    st.title('Medi-Cal language-access planning')
    st.write(
        'Find populations to examine more closely. Choose a month, primary '
        'language, and county to compare language count, concentration, and '
        'countywide demographic context.'
    )

    filter_columns = st.columns(3)
    with filter_columns[0]:
        month = st.selectbox(
            'Eligibility month',
            options=list(reversed(metadata['months'])),
            index=0,
        )
    with filter_columns[1]:
        language = st.selectbox(
            'Primary language',
            options=metadata['languages'],
            index=next(
                (index for index, item in enumerate(metadata['languages'])
                 if item['id'] == metadata['defaults']['language']),
                0,
            ),
            format_func=lambda item: item['label'],
        )['id']
    with filter_columns[2]:
        county = st.selectbox(
            'Selected county',
            options=metadata['counties'],
            index=metadata['counties'].index(metadata['defaults']['county']),
        )

    comparison = dataset.comparison(month, language)
    county_view = dataset.county(month, language, county)
    overview = comparison['overview']
    county_detail = county_view['county']
    language_label = language_labels[language]

    st.subheader('Statewide coverage')
    metrics = st.columns(4)
    metrics[0].metric('Observed county subtotal', _format_count(overview['observed_language_count']))
    metrics[1].metric(
        'Published language counts',
        f"{overview['language_count_available_counties']} / {overview['county_count']} counties",
    )
    metrics[2].metric(
        'Counties with usable shares',
        f"{overview['language_share_available_counties']} / {overview['county_count']}",
    )
    metrics[3].metric('Complete statewide share', _format_percent(overview['language_share']))
    st.markdown(
        '<p class="dashboard-note">The observed subtotal includes published '
        'county values only. Unavailable counts are not treated as zero.</p>',
        unsafe_allow_html=True,
    )

    comparison_frame = pd.DataFrame(comparison['counties'])
    metric_by_county = comparison_frame.set_index('county').to_dict('index')
    mapped_features = []
    for feature in geometry['features']:
        name = feature['properties']['county']
        row = metric_by_county[name]
        mapped_features.append({
            **feature,
            'county': name,
            'selected_language_count': row['selected_language_count'],
            'county_total_eligibles': row['county_total_eligibles'],
            'language_share': row['language_share'],
        })

    map_column, detail_column = st.columns([1.15, 1])
    with map_column:
        st.subheader('Explore California')
        st.caption(f'{month} · {language_label}. Use the county selector above to update the detail.')
        map_spec = {
            'data': {'values': mapped_features},
            'mark': {'type': 'geoshape', 'stroke': '#ffffff', 'strokeWidth': 0.55},
            'projection': {'type': 'mercator'},
            'encoding': {
                'color': {
                    'field': 'selected_language_count', 'type': 'quantitative',
                    'scale': {'scheme': 'blues'}, 'legend': {'title': 'Language count'},
                },
                'tooltip': [
                    {'field': 'county', 'type': 'nominal', 'title': 'County'},
                    {'field': 'selected_language_count', 'type': 'quantitative', 'title': 'Language count', 'format': ','},
                    {'field': 'county_total_eligibles', 'type': 'quantitative', 'title': 'County total', 'format': ','},
                    {'field': 'language_share', 'type': 'quantitative', 'title': 'Language share', 'format': '.1%'},
                ],
            },
            'height': 520,
        }
        st.vega_lite_chart(map_spec, width='stretch')
        st.caption('Blue encodes published language counts. Counties with unavailable counts are gray.')

    with detail_column:
        st.subheader(f'{county} County')
        detail_metrics = st.columns(3)
        detail_metrics[0].metric(f'{language_label} count', _format_count(county_detail['selected_language_count']))
        detail_metrics[1].metric('County total eligibles', _format_count(county_detail['county_total_eligibles']))
        detail_metrics[2].metric('Language share', _format_percent(county_detail['language_share']))
        if county_detail['language_share'] is None:
            reason = county_detail.get('language_share_unavailable_reason') or 'unavailable source value'
            st.info('Language share unavailable: ' + reason.replace('_', ' ') + '.')
        st.caption(
            f"Source status: {county_detail.get('status') or 'not supplied'} · "
            f"Data date: {county_detail.get('date_of_data') or 'not supplied'}"
        )
        st.markdown('#### Language count over time')
        trend = pd.DataFrame(county_view['trend']).rename(columns={
            'month_of_eligibility': 'Month',
            'selected_language_count': language_label,
        })
        trend['Month'] = pd.to_datetime(trend['Month'], format='%Y-%m')
        st.line_chart(trend, x='Month', y=language_label, color='#276a8c')
        st.caption('Gaps indicate unavailable counts; monthly observations are not unique people across time.')

    st.subheader('Compare all counties')
    table = comparison_frame[[
        'rank', 'county', 'selected_language_count', 'county_total_eligibles',
        'language_share', 'language_share_unavailable_reason',
    ]].rename(columns={
        'rank': 'Count rank', 'county': 'County',
        'selected_language_count': f'{language_label} count',
        'county_total_eligibles': 'County total',
        'language_share': 'Language share',
        'language_share_unavailable_reason': 'Unavailable reason',
    })
    st.dataframe(
        table,
        width='stretch',
        hide_index=True,
        column_config={
            'Language share': st.column_config.NumberColumn(format='percent'),
        },
    )
    export_status, _, export_body = Application().response(
        '/api/export.csv?' + urlencode({'month': month, 'language': language})
    )
    if export_status == 200:
        st.download_button(
            'Download county comparison CSV',
            data=export_body,
            file_name=f'medi-cal-{month}-{language}.csv',
            mime='text/csv',
        )

    st.subheader('All Medi-Cal eligibles in this county')
    st.caption(
        'These charts describe the whole county eligible population, not the '
        'selected-language subgroup. Changing language does not change them.'
    )
    demographic_columns = st.columns(2)
    age_sex = pd.DataFrame(county_view['age_sex']).rename(columns={
        'age_group': 'Age group', 'sex': 'Sex', 'eligible_count': 'Eligible count',
    })
    race = pd.DataFrame(county_view['race_ethnicity']).rename(columns={
        'race_ethnicity': 'Race/ethnicity', 'eligible_count': 'Eligible count',
    })
    with demographic_columns[0]:
        st.markdown('#### Age and sex')
        st.bar_chart(age_sex, x='Age group', y='Eligible count', color='Sex')
    with demographic_columns[1]:
        st.markdown('#### Race and ethnicity')
        st.bar_chart(race, x='Race/ethnicity', y='Eligible count', horizontal=True)

    st.divider()
    st.markdown('**Read the data carefully.**')
    st.caption(
        'Language share requires an observed primary-language count and a '
        'complete, positive county denominator. Suppressed or absent values '
        'remain unavailable. Population comparisons do not measure interpreter '
        'demand, provider capacity, or proven service shortages.'
    )
    st.caption(
        f"Source: {metadata['source']['publisher']} · {metadata['source']['file']} · "
        f"{metadata['source']['first_month']} through {metadata['source']['last_month']}"
    )


def running_in_streamlit():
    """Return true only when Streamlit is executing this file as an app."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        return False
    return get_script_run_ctx(suppress_warning=True) is not None


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
    if running_in_streamlit():
        streamlit_main()
    else:
        main()
