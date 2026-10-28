"""Local Medi-Cal dashboard. Run: python Project/dashboard.py"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import argparse
import json

import pandas as pd

ROOT = Path(__file__).resolve().parent


def load_records(path=None):
    """Apply the existing notebook's text/count normalization without writing data."""
    frame = pd.read_csv(path or ROOT / 'raw/by-primary-language-certified-eligibles.csv',
                        dtype=str, keep_default_na=False, encoding='utf-8-sig')
    frame['Language'] = frame['Language'].str.strip()
    if frame.duplicated(['Month of Eligibility', 'County', 'Language']).any():
        raise ValueError('Duplicate month/county/language keys; review source before display.')
    text = frame['Total Eligibles'].str.strip()
    valid = text.eq('') | text.str.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)')
    if not valid.all():
        raise ValueError('Unexpected count format; review source before display.')
    frame['count'] = pd.to_numeric(text.str.replace(',', '', regex=False).replace('', pd.NA)).astype('Int64')
    detail = frame.loc[~frame['County'].isin(['STATEWIDE', 'Invalid County Code'])].copy()
    return {
        'months': sorted(detail['Month of Eligibility'].unique()),
        'languages': sorted(detail['Language'].unique()),
        'counties': sorted(detail['County'].unique()),
        'records': [dict(month=r['Month of Eligibility'], county=r['County'], language=r['Language'],
                         count=None if pd.isna(r['count']) else int(r['count']),
                         annotation=r['Annotation Description'], code=r['Annotation Code'],
                         status=r['Status'], data_date=r['Date of Data'])
                    for r in detail.to_dict('records')],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8050)
    args = parser.parse_args()
    payload = json.dumps(load_records(), allow_nan=False).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route = urlparse(self.path).path
            assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                      '/styles.css': ('styles.css', 'text/css')}
            if route == '/api/data':
                content, mime = payload, 'application/json'
            elif route in assets:
                name, mime = assets[route]
                content = (ROOT / 'web' / name).read_bytes()
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Medi-Cal dashboard: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
