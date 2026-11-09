# Medi-Cal Language-Access Planning Dashboard
## Final Submission Version

The final Phase 3 dashboard code is on the `codex/interactive-county-dashboard` branch.

- [Final source code](https://github.com/jguo368/dso576/tree/codex/interactive-county-dashboard)
- Entry point: `dashboard.py`
- Run the Streamlit version using the instructions below to reproduce the interface shown in the live app and demo video.
Please use this branch rather than `main` when running the app locally.

## Project Overview

This interactive dashboard supports Medi-Cal language-access planning across California's 58 counties. It helps county health planners and public health analysts identify populations for further investigation by comparing language-specific eligibility counts, population concentration, historical trends, and countywide demographic characteristics.

The goal is to support evidence-based prioritization of communities for further language-access assessment, rather than directly measure healthcare service shortages.

## Live App and Demo

- **Live Dashboard:** [Open Dashboard](https://interactive-county-dashboard-ekuekfedspp64bznr5it3r.streamlit.app/)
- **Demo Video:** [Open video link](https://drive.google.com/file/d/1xF0m-0uGG4BvhucTaFMF2zHE_f5vRczc/view?usp=drive_link)
- **GitHub Repository:** [jguo368/dso576](https://github.com/jguo368/dso576)

## Intended Users and Decisions

The dashboard is designed for county health planners and public health analysts seeking to:

- Identify counties with the largest populations reporting a selected primary language.
- Compare language counts and shares to distinguish population size from concentration.
- Examine historical changes in language-specific eligible populations.
- Prioritize counties for further language-access planning and investigation.

## Dashboard Features

- **Interactive Filters:** Select an eligibility month, primary language, and county.
- **Statewide Coverage:** Review observed language counts, available county coverage, and data completeness.
- **Interactive County Map:** Visualize language-specific populations across California's 58 counties.
- **County Comparison:** Sort counties by language count, language share, or county name.
- **Historical Trends:** Explore monthly changes in language-specific eligible populations.
- **Demographic Context:** Examine age, sex, race, and ethnicity distributions for the overall county eligible population.
- **CSV Export:** Download county-level comparisons with availability indicators and source information.
- **Missing-Data Handling:** Clearly distinguish unavailable or suppressed values from observed zeros.

## Data Scope

**Source:** California Department of Health Care Services (DHCS)

**Coverage:** January 2010 – September 2026

**Dataset:** 11,658 county-month observations across 58 counties and 201 months, with 74 columns.

The dashboard uses the complete cleaned project dataset, integrating three DHCS demographic resources:

- Primary Language
- Age Group and Sex
- Race/Ethnicity and Age Group

No additional sampling or geographic subset is used in the deployed dashboard.

Key metrics include:

- **Language Count:** Number of Medi-Cal eligible individuals reporting the selected primary language.
- **County Total:** Total eligible population, calculated when all required age/sex observations are available.
- **Language Share:** Selected-language count divided by a complete, positive county total.

Demographic charts describe all Medi-Cal eligible individuals in the selected county, not only the selected-language subgroup.

The dataset preserves preliminary and final publication statuses. Missing or suppressed counts remain unavailable rather than being treated as zero.

## Run Locally

Requires Python 3.11 or later and Git.

### 1. Clone the final submission branch

```bash
git clone --branch codex/interactive-county-dashboard --single-branch https://github.com/jguo368/dso576.git
cd dso576
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies and launch the app

```bash
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py
```

Open the Local URL printed in the terminal, normally http://localhost:8501.

The app uses bundled data and county geometry. No API keys or database connection are required.

## Current Limitations

- **Incomplete Coverage:** Some county-month-language combinations contain missing or suppressed values. Observed subtotals may not represent complete statewide totals.
- **Missing Denominators:** Language shares are unavailable when a complete and reliable county total cannot be established.
- **Demographic Granularity:** Age, sex, race, and ethnicity charts describe the overall county population rather than language-specific subgroups.
- **Historical Snapshot:** The dashboard uses a fixed dataset through September 2026 rather than automatically retrieving newly published DHCS data.
- **Provider Capacity:** Eligibility counts do not measure interpreter availability, provider capacity, healthcare utilization, or confirmed service shortages.

Future improvements could integrate provider availability, interpreter capacity, and healthcare utilization data to better identify potential language-access gaps.
