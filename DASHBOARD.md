# Medi-Cal Language Explorer

From the repository root, run:

```bash
.venv/bin/python Project/dashboard.py
```

Open http://127.0.0.1:8050 and keep the terminal running. Stop with Ctrl+C.
Alternatively, from `Project`, run `python dashboard.py` in an environment
with pandas installed (`python -m pip install -r requirements.txt`).
Use `--port 8051` if the default port is busy.

The dashboard reads the full bundled `raw/by-primary-language-certified-eligibles.csv`,
not the 20-row sample. No network, API key, or additional UI packages are needed.
Do not open `web/index.html` directly; it needs the local Python server.

Choose a month and language to compare all 58 counties, inspect a county's
monthly trend, search the table, and download the current month/language
county comparison as CSV. Search only changes the visible table; CSV includes
all counties for the selected month/language. Hover over trend points for values.

Suppressed counts remain unavailable and absent records are labeled separately.
The observed county subtotal includes only published values and is not a complete
statewide total. Statewide and invalid-county records do not enter rankings.
Equal counts receive competition ranks (1, 1, 3), with alphabetical ties.
Unknown and Missing/Unknown remain separate. Source status codes and annotations
are retained. Language shares are unavailable until a verified county-total
denominator is supplied. The original CSV and cleaning notebook are unchanged.

The Phase 2 audit documents a different, pinned Git snapshot. This dashboard
uses the language-only CSV in the current working folder, not that snapshot's
merged county-total dataset.
