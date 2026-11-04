# Medi-Cal language-access planning

Phase 2 delivers one canonical county-month dataset, a reproducible cleaning
pipeline, reusable analysis functions, and the specification for the Phase 3
dashboard. The Phase 3 local dashboard now connects those validated outputs to an interactive county map and detail views.

## Start here

Run from this repository directory (`project/`):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m medi_cal_analysis
```

In this workspace an existing `.venv` is available; use it directly. A fresh
clone should create the environment and install dependencies as shown above.
Python 3.11+ is supported; dependencies are pandas and NumPy. After installation,
tests and backend export run offline without a database, credentials, or notebook state.
The final command exports every dashboard backend output for the latest month,
Spanish, and Los Angeles to `outputs/dashboard_preview.json`. Missing values
serialize as JSON null, never zero.

```bash
.venv/bin/python -m medi_cal_analysis --month 2026-09 \
  --language mandarin --county "Alameda" --output outputs/mandarin_preview.json
```

## Deliverables

| Deliverable | Location |
| --- | --- |
| Authoritative dashboard specification | [BUILD_SPEC.md](BUILD_SPEC.md) |
| Canonical data: 11,658 rows, 58 counties, January 2010–September 2026 | [County-month CSV](dso576/project/medi_cal_merged_county_month.csv) |
| Reproducible raw-source cleaning and source audit | [CLEANING.md](CLEANING.md), [cleaning.py](medi_cal_analysis/cleaning.py), [audit](outputs/cleaning_report.json) |
| Reusable backend and input/output examples | [ANALYSIS.md](ANALYSIS.md), [medi_cal_analysis](medi_cal_analysis/) |
| Validation and submission handoff | [PHASE_2_STATUS.md](PHASE_2_STATUS.md), [tests](tests/) |

The CSV is tracked in Git even though bulk CSV downloads are generally ignored.
Do not use the older language-only cleaning output as the dashboard data source.
The existing `exploration.ipynb`, `data-fit.md`, and other Phase 1 documents are
historical exploration; the BUILD_SPEC records the current narrowed vision.

## Rebuild data

```bash
.venv/bin/python -m medi_cal_analysis.cleaning --download
```

This optional command downloads the three official DHCS source files, validates
their categories and matching publication metadata, and rebuilds the canonical
CSV plus `outputs/cleaning_report.json`. Use it without `--download` to rebuild
from local `data/raw/` inputs. See CLEANING.md for snapshot comparison commands,
source-version limitations, and the available team reconciliation evidence.

Suppressed and absent counts remain unavailable. Language share requires an
observed count and a complete positive county total. County demographic context
describes all county Medi-Cal eligibles, not the selected-language subgroup.
Population comparisons support investigation; they do not measure interpreter
capacity or prove a service shortage.

## Local language dashboard

Run `.venv/bin/python dashboard.py` from this repository folder after installing requirements.
Open http://127.0.0.1:8050. See [DASHBOARD.md](DASHBOARD.md) for features and data limitations.
The dashboard uses the canonical Phase 2 dataset and backend for counts, denominators, shares, rankings, coverage, trends, and county demographic context. Select counties on the map, in the table, or from the dropdown; the views stay synchronized. See `outputs/dashboard_browser_verification.md` for the tested acceptance cases.
