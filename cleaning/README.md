# Medi-Cal project cleaning workflow

This workflow implements the approved cleaning plan. It never changes input CSVs;
all derived artifacts are written to `cleaning/outputs/`.

Business vision: **A Medi-Cal access strategy manager at DHCS must decide which
counties and language populations should be prioritized for additional
language-access capacity.**

## Run

From `project/`:

```powershell
python -m pip install -r cleaning/requirements.txt
python cleaning/clean_medi_cal.py
```

Outputs include full cleaned long and derived tables, missing-value and validation
reports, merge validation, the decision log, checklist evidence, five record
checks, a 50-row difficult-case sample, and an input/output hash manifest.

Run the command twice from a fresh Python process. Compare output hashes except
`source_manifest.csv` (which lists the other output hashes); matching hashes
confirm reproducibility. Assertions stop the run if row counts change, key
coverage has unmatched records, or a record check fails.

Blank/suppressed counts remain missing, language categories are not combined,
and F/P records are retained. Invalid County Code remains in the cleaned data
with a flag; county rankings/maps must filter it at analysis time. No
provider-capacity values are created because no provider dataset is present.

## Submission metadata

- Branch name: `fennie-project`
- Branch URL: `https://github.com/jguo368/dso576/tree/fennie-project`
- Cleaning workflow commit ID: `794e5d6fcce8abe6a8a8fa9a0488ed71ec8ed5e3`

The commit ID identifies the committed cleaning workflow and evidence files used
to prepare the submission PDF. The branch tip may also include the final PDF
packaging commit.
