"""Haopeng Chen's Phase 2 audit. Run from Project:
PYTHONDONTWRITEBYTECODE=1 /Users/comarea/dso576/.venv/bin/python audits/haopeng_module9_check.py
Requires pandas/numpy and the pinned commit in this repository's Git objects.
Reads Git blobs, not the older raw language-only CSV. No network or backend edits.
A temporary snapshot inside Project is removed automatically. Output is the evidence.
"""
from pathlib import Path
import hashlib
import inspect
import os
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '3afb82b57ca9863a921eae805541846c4d561e46'
CSV = 'dso576/project/medi_cal_merged_county_month.csv'
MONTH, LANGUAGE = '2026-09', 'spanish'

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def blob(path):
    return git('show', f'{COMMIT}:{path}')

def check(label, condition):
    global passed, failed
    if bool(condition):
        passed += 1
        print('PASS:', label)
    else:
        failed += 1
        print('FAIL:', label)

passed = failed = 0
if git('branch', '--show-current').decode().strip() != 'haopeng-chen':
    raise SystemExit('Run on haopeng-chen only')
print('Auditor: Haopeng Chen; Phase 2 backend only; no dashboard test')
print('Commit:', COMMIT)
print('Python:', sys.version.split()[0], 'pandas:', pd.__version__, 'numpy:', np.__version__)
print('Canonical path:', CSV)
print('Canonical SHA256:', hashlib.sha256(blob(CSV)).hexdigest())
print('BUILD_SPEC requirements: descending counts; alphabetical ties; competition ranks; missing last/unranked; observed subtotal with coverage; complete total requires 58 observed counties.')
print('Inspected existing tests: tests/test_analysis.py — test_ranking_ties_zero_and_missing, test_month_summary_reports_partial_coverage, test_full_coverage_summary_uses_totals_not_average_shares, test_all_mvp_outputs_from_team_csv.')
print('\nAVAILABLE BRANCH CLAIM SEARCH (local refs at execution time):')
refs = git('for-each-ref', '--format=%(refname)', 'refs/heads', 'refs/remotes/origin').decode().splitlines()
for ref in refs:
    files = git('ls-tree', '-r', '--name-only', ref).decode().splitlines()
    hits = []
    for path in files:
        if path.endswith(('.md', '.py', '.ipynb')):
            text = git('show', f'{ref}:{path}').decode(errors='replace')
            if any(term in path.lower() for term in ('audit', 'change-request', 'claim')) or ('get_county_ranking' in text and 'claim' in text.lower()):
                hits.append(path)
                if 'change-request' in path.lower():
                    print(ref, path, '\n', text)
    print(ref, 'candidate audit/claim files:', hits)
print('Working-tree claim:\n' + (ROOT / 'change-requests.md').read_text())
print('Limitations: only published/fetched branches and available working files; cannot inspect teammates\' unpushed/local work, private files, Brightspace, or verbal claims. Search is file/name/content based; absence is not proof of no claim.')
with tempfile.TemporaryDirectory(prefix='.module9-snapshot-', dir=ROOT) as directory:
    snapshot = Path(directory)
    files = git('ls-tree', '-r', '--name-only', COMMIT).decode().splitlines()
    for path in files:
        if path.startswith(('medi_cal_analysis/', 'tests/')) or path in (CSV, 'BUILD_SPEC.md'):
            target = snapshot / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob(path))
    sys.path.insert(0, str(snapshot))
    import medi_cal_analysis as api
    from medi_cal_analysis.data import CALIFORNIA_COUNTIES, SUPPRESSION_COLUMNS
    print('\nSIGNATURES:', inspect.signature(api.get_county_ranking), inspect.signature(api.get_month_summary))
    # Independent CSV calculation: no load_data, prepare_data, or summary API.
    raw = pd.read_csv(snapshot / CSV)
    print('CSV shape:', raw.shape, 'columns:', raw.columns.tolist())
    expected_counties = set(CALIFORNIA_COUNTIES)  # contract allowlist only; no metric helper
    independent = raw.loc[raw['month_of_eligibility'].eq(MONTH) & raw['county'].isin(expected_counties), ['county', 'language__spanish']].copy()
    independent['language__spanish'] = pd.to_numeric(independent['language__spanish'], errors='raise')
    check('independent county keys unique', not independent['county'].duplicated().any())
    subtotal = independent['language__spanish'].sum(min_count=1)
    observed = independent['language__spanish'].notna().sum()
    missing_names = sorted(independent.loc[independent['language__spanish'].isna(), 'county'])
    absent_names = sorted(expected_counties - set(independent['county']))
    print('\nEXACT NUMBER INPUT: CSV above; month_of_eligibility == 2026-09; language__spanish; county in 58-county contract allowlist; observed values summed with min_count=1.')
    print('Independent expected:', {'subtotal': subtotal, 'county_rows': len(independent), 'observed_counties': observed, 'missing_value_counties': missing_names, 'absent_counties': absent_names})
    data = api.load_data(snapshot / CSV)
    original = data.copy(deep=True)
    summary = api.get_month_summary(data, MONTH, LANGUAGE)
    print('Actual summary columns:', summary.columns.tolist())
    print('Actual summary:\n' + summary.to_string(index=False))
    s = summary.iloc[0]
    for column, value in [('observed_language_count', subtotal), ('county_count', len(independent)), ('missing_counties', len(absent_names)), ('language_count_available_counties', observed), ('language_count_missing_counties', len(missing_names))]:
        check('number/coverage ' + column, s[column] == value)
    check('real input has incomplete language coverage', len(missing_names) > 0)
    check('incomplete statewide count flagged false', not s['selected_language_count_is_complete'])
    check('full statewide count unavailable', pd.isna(s['selected_language_count']))
    check('statewide language share unavailable', pd.isna(s['language_share']))
    # Independent Python ordering and competition positions, not pandas rank.
    def expected_ranking(rows):
        ordered = sorted(rows, key=lambda x: (pd.isna(x[1]), -x[1] if pd.notna(x[1]) else 0, x[0]))
        first = {}
        output = []
        for position, (county, count) in enumerate(ordered, 1):
            rank = None if pd.isna(count) else first.setdefault(count, position)
            output.append((county, None if pd.isna(count) else int(count), rank))
        return output
    def actual_ranking(frame):
        return [(r.county, None if pd.isna(r.selected_language_count) else int(r.selected_language_count), None if pd.isna(r.rank) else int(r.rank)) for r in frame.itertuples()]
    expected = expected_ranking(list(independent.itertuples(index=False, name=None)))
    ranking = api.get_county_ranking(data, MONTH, LANGUAGE)
    actual = actual_ranking(ranking)
    print('\nActual ranking columns:', ranking.columns.tolist())
    print('REAL RANKING exact expected/actual (county, count, competition rank):')
    for e, a in zip(expected, actual):
        print('expected=', e, 'actual=', a)
    check('real descending order/alphabetical ties/competition ranks/missing last', actual == expected)
    check('ranking preserves exact county coverage', set(ranking['county']) == set(independent['county']))
    # Minimal valid metrics input: explicitly typed; deliberately unsorted ties,
    # observed zero and missing. No canonical count is changed.
    synthetic = pd.DataFrame({'month_of_eligibility': [MONTH]*5, 'county': ['Amador','Butte','Alameda','Alpine','Colusa'], 'language__spanish': pd.array([100, 0, 100, None, 50], dtype='Float64'), 'county_total_eligibles': pd.array([200]*5, dtype='Float64'), 'county_total_is_complete': pd.array([True]*5, dtype='boolean'), **{c: [0]*5 for c in SUPPRESSION_COLUMNS}})
    print('\nSYNTHETIC exact input:\n' + synthetic.to_string(index=False))
    expected_tie = [('Alameda',100,1), ('Amador',100,1), ('Colusa',50,3), ('Butte',0,4), ('Alpine',None,None)]
    actual_tie = actual_ranking(api.get_county_ranking(synthetic, MONTH, LANGUAGE))
    print('Synthetic expected:', expected_tie)
    print('Synthetic actual:  ', actual_tie)
    check('synthetic descending order, alphabetical tie, ranks 1/1/3/4, zero observed, NA last/unranked', actual_tie == expected_tie)
    check('backend did not mutate canonical prepared input', data.equals(original))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=snapshot, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print('\nEXISTING SUITE COMMAND: python -m unittest discover -s tests -v (in pinned snapshot)\n' + result.stdout)
    check('existing suite exit status zero', result.returncode == 0)
print(f'\nINDIVIDUAL CHECKS: {passed} PASS, {failed} FAIL')
raise SystemExit(1 if failed else 0)
