"""Build the offline county display asset from Census 2025 cartographic boundaries.

Optional build dependencies only: uv run --with pyshp --with pyproj python
scripts/prepare-county-geometry.py /path/to/cb_2025_us_county_5m.zip
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

import shapefile
from pyproj import CRS, Transformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from medi_cal_analysis.data import CALIFORNIA_COUNTIES

SOURCE = 'https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_county_5m.zip'


def convert(coordinates, transform):
    if isinstance(coordinates[0], (float, int)):
        x, y = transform(*coordinates[:2])
        return [round(x, 6), round(y, 6)]
    return [convert(part, transform) for part in coordinates]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'data/california_counties.geojson')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        with zipfile.ZipFile(args.archive) as archive:
            for name in archive.namelist():
                if Path(name).name != name:
                    raise ValueError('Expected flat Census archive')
            archive.extractall(directory)
        source = next(Path(directory).glob('*.shp'))
        transform = Transformer.from_crs(CRS.from_wkt(source.with_suffix('.prj').read_text()), 'EPSG:4326', always_xy=True)
        reader = shapefile.Reader(str(source))
        features = []
        for item in reader.iterShapeRecords():
            record = item.record.as_dict()
            if record['STATEFP'] != '06':
                continue
            geometry = item.shape.__geo_interface__
            geometry['coordinates'] = convert(geometry['coordinates'], transform.transform)
            features.append({'type': 'Feature', 'properties': {'county': record['NAME'], 'geoid': record['GEOID']}, 'geometry': geometry})
    assert len(features) == 58 and {f['properties']['county'] for f in features} == set(CALIFORNIA_COUNTIES)
    result = {'type': 'FeatureCollection', 'source': SOURCE, 'source_sha256': hashlib.sha256(args.archive.read_bytes()).hexdigest(), 'vintage': '2025', 'crs_description': 'WGS84 / EPSG:4326', 'features': sorted(features, key=lambda f: f['properties']['county'])}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, separators=(',', ':')) + '\n')
    print(f'Validated all 58 counties: {args.output} ({args.output.stat().st_size:,} bytes)')


if __name__ == '__main__':
    main()
