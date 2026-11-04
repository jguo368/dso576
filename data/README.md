# Offline dashboard display assets

`california_counties.geojson` is a display asset, separate from the DHCS
eligibility data. Its 58 `properties.county` keys exactly match the backend's
California county allowlist; coordinates are WGS84 / EPSG:4326.

Source: [U.S. Census Bureau 2025 county cartographic boundaries, 1:5,000,000](https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_county_5m.zip).
The bundled file includes the source URL, source ZIP SHA-256, vintage, county
GEOIDs, and CRS description. Preparation selects `STATEFP == '06'`, preserves
polygon/island/hole geometry, transforms the published CRS with pyproj, and
rounds coordinates to six decimals. It is not a basemap or service-capacity map.

Optional rebuild (temporary build dependencies; no dashboard runtime changes):

```bash
curl -L --fail -o /tmp/cb_2025_us_county_5m.zip https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_county_5m.zip
uv run --with pyshp --with pyproj --with 'pandas>=2.2,<3' --with 'numpy>=1.26,<3' python scripts/prepare-county-geometry.py /tmp/cb_2025_us_county_5m.zip
```

The builder refuses a geometry-name mismatch. Dashboard tests also verify the
58 exact joins and California longitude/latitude bounds. There is no geometry
network request during dashboard startup or interaction.
