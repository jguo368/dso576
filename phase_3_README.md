# Medi-Cal Language-Access Planning Dashboard

## Project Overview

This interactive dashboard supports Medi-Cal language-access planning across California's 58 counties. It helps county health planners and public health analysts identify populations for further investigation by comparing language-specific eligibility counts, population concentration, historical trends, and countywide demographic characteristics.

The goal is to support evidence-based prioritization of communities for further language-access assessment, rather than directly measure healthcare service shortages.

## Live App and Demo

- **Live Dashboard:** [Open Dashboard](https://interactive-county-dashboard-ekuekfedspp64bznr5it3r.streamlit.app/)
- **Demo Video:** [Insert video link]
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

**Requirements:** Python 3.11 or later.

1. Clone the repository:

   ```bash
   git clone https://github.com/jguo368/dso576.git
   cd dso576
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Launch the Streamlit dashboard:

   ```bash
   streamlit run dashboard.py
   ```

   Alternatively, run the standalone local server:

   ```bash
   python dashboard.py
   ```

   Open `http://127.0.0.1:8050` when using standalone mode.

The dashboard uses bundled data and county geometry. No API keys, database connection, or live external data requests are required during normal operation.

## Current Limitations

- **Incomplete Coverage:** Some county-month-language combinations contain missing or suppressed values. Observed subtotals may not represent complete statewide totals.
- **Missing Denominators:** Language shares are unavailable when a complete and reliable county total cannot be established.
- **Demographic Granularity:** Age, sex, race, and ethnicity charts describe the overall county population rather than language-specific subgroups.
- **Historical Snapshot:** The dashboard uses a fixed dataset through September 2026 rather than automatically retrieving newly published DHCS data.
- **Provider Capacity:** Eligibility counts do not measure interpreter availability, provider capacity, healthcare utilization, or confirmed service shortages.

Future improvements could integrate provider availability, interpreter capacity, and healthcare utilization data to better identify potential language-access gaps.