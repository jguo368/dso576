# Medi-Cal language-access planning dashboard

From this repository folder (`/Users/shawnshih/dso576/project`):

```bash
.venv/bin/python dashboard.py
```

Open [http://127.0.0.1:8050](http://127.0.0.1:8050). Stop with Ctrl+C. Use
`--port 8051` if the port is busy. For a fresh environment, follow the README
installation steps; runtime dependencies remain pandas and NumPy. No map tiles,
API key, internet connection, or UI package is required at runtime.

## Connected workflow

The opening view is September 2026 / Spanish / Los Angeles for the bundled
snapshot. Options come from the canonical dataset.

- **Select a county** on the California map, in a table row, in the top-12 quick
  selection, or from the county dropdown. The map outline, table highlight,
  count/total/share, demographics, and trend share that selection.
- **Change month or language** to recompute the overview, map, table, and county
  language metrics. Demographics depend on month/county only.
- **Compare concentration** by sorting the table on language share, language
  count, or county name. Count rank retains its meaning when the sort changes.
- **Search** filters the table, while the CSV includes all 58 counties for the
  chosen month/language. The export includes denominators, fractional shares,
  availability reasons, source status/date, and the source snapshot hash.
- **Use the keyboard**: controls have explicit labels, table choices are native
  buttons, and map counties support Tab followed by Enter or Space. A skip link
  moves to county detail. The county dropdown is an alternative to map selection.
- **Reset view** restores the starting filters, count sorting, and empty search.

Map fill encodes language counts on a sequential blue square-root scale so
smaller populations remain visible. The count legend rescales per selection;
colors cannot be compared between selections. Observed zero is light blue;
unavailable is gray. Hover/focus shows county, count, county total, share, and
availability; an orange outline identifies the selected county.

## Data and interpretation

All runtime metrics use `medi_cal_analysis.DEFAULT_DATA_PATH`:
`dso576/project/medi_cal_merged_county_month.csv`, 11,658 county-month rows,
January 2010–September 2026. SHA-256:
`8bd21b92046753bee440ef290192b8b260fb317953e2e2fca553ff2e3f46d803`.
This is the same snapshot as Shawn's October 26 audit. The older, language-only
`raw/` CSV remains a historical artifact and is not loaded by the dashboard.

Language shares require an observed numerator and a complete positive total
from all eight age/sex cells. Suppressed/absent values stay unavailable; they
are not zero or inferred by subtraction. The observed county subtotal is
labeled separately from a complete statewide count/share. Unknown and
Missing/Unknown remain distinct. County demographic charts describe **All
Medi-Cal eligibles in this county**, not the selected-language subgroup.

P means preliminary (may be revised); F means final. Footer coverage, county
source date, and export provenance refer to the selected, bundled snapshot.
Eligibility populations do not establish interpreter demand or service capacity.

## Implementation and offline boundaries

The existing Python standard-library server serves JSON views computed by the
validated backend. Native HTML/CSS/SVG provides the UI; the earlier proposed
Streamlit/Plotly approach is superseded by this extension of the existing app.
No ranking or denominator arithmetic is duplicated in JavaScript. Data,
geometry, comparisons, and county responses are cached; source-file changes
invalidate the data/geometry caches. An in-session snapshot change requires a
reload so all views use one source version. Invalid data stops startup, and
request failures show an actionable error rather than stale values. Incomplete
county-month grids are rejected before rendering.

Endpoints: `/api/metadata`, `/api/geometry`, `/api/comparison?month=…&language=…`,
`/api/county?month=…&language=…&county=…`, and `/api/export.csv?month=…&language=…`.
Metadata, the selected 58-county comparison, county context/trend, and geometry
replace the previous 40 MB raw-record download. Responses support gzip; selection
requests are canceled/superseded safely when filters change quickly.

The bundled `data/california_counties.geojson` contains all 58 exact county-name
joins, prepared from Census 2025 1:5,000,000 cartographic boundaries and converted
to WGS84. See [data/README.md](data/README.md) for provenance/rebuild instructions.
No boundaries or tiles are downloaded while using the app.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/audit_shawn_shih.py --output /tmp/shawn-audit-current.json
node --check web/app.js
```

The original `outputs/module09_shawn_shih_audit.json` remains pinned to the
original audited commit. Use `--output` to preserve that historical report.
See [outputs/dashboard_browser_verification.md](outputs/dashboard_browser_verification.md)
for actual browser checks, measured scope, and the repeatable acceptance demo.
