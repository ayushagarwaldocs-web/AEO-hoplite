"""Separate-site follow-up (specified 10 November 2026): does the same outside reviewer's sentence count for more on
the buyer's guide than on the brand's own page? Same statistics as the attribution follow-up.

    python3 analyze_site.py      # reads data/responses_bedrock_site.jsonl, writes results/site_effects.csv and
                                 # results/site_summary.json
"""
import argparse
import math
from pathlib import Path

import pandas as pd

from attribution import SITE
from build_corpus import build
from analyze_revision import developer_for_model
from followup_common import SCHEMA_VERSION, effect, holm, read_jsonl, write_json

HERE = Path(__file__).resolve().parent
CONTRASTS = {
    'site_recommending': {'site_T1': 1, 'site_Q1': -1},
    'site_neutral': {'site_T0': 1, 'site_Q0': -1},
    'site_by_wording': {'site_T1': 1, 'site_T0': -1, 'site_Q1': -1, 'site_Q0': 1},
}
OUTCOMES = ['mentioned', 'top_pick', 'cited']
MIN_TRIALS = math.ceil(90 * 1300 / 1350)  # 87 complete paired trials, as in the attribution follow-up


def prepare(records):
    expected = {i['trial_id']: i for i in build(3, ['site_B'])}
    successes, seen, attempts = [], set(), set()
    planned_models = {r['model'] for r in read_jsonl(HERE / 'data/responses_bedrock.jsonl')}
    if {r['model'] for r in records} - planned_models:
        raise ValueError('Unplanned model in the site follow-up')
    for row in records:
        if row['condition'] not in SITE:
            raise ValueError('Non-site condition in the site follow-up file')
        if row['trial_id'] not in expected or row['scenario'] != expected[row['trial_id']]['scenario']:
            raise ValueError('Unknown or inconsistent trial/scenario')
        for field in ['target', 'target_index', 'guide_index', 'n_sources']:
            if field in row and row[field] != expected[row['trial_id']][field]:
                raise ValueError('Site metadata differs from the main trial')
        attempt = (row['model'], row['trial_id'], row['condition'])
        if attempt in attempts:
            raise ValueError('Duplicate site attempt; do not select among retries')
        attempts.add(attempt)
        if row.get('error'):
            continue
        if any(row.get(o) not in (True, False, 0, 1) for o in OUTCOMES):
            raise ValueError('Missing/nonbinary site outcome')
        seen.add(attempt)
        successes.append(row)
    data = pd.DataFrame(successes)
    reports, keep = {}, []
    for model in sorted(planned_models):
        d = data[data.model == model] if not data.empty else data
        trials = d.groupby('trial_id').condition.nunique() if not d.empty else pd.Series(dtype=int)
        complete = sorted(trials[trials == 5].index)
        missing = {trial: [c for c in SITE if (model, trial, c) not in seen] for trial in expected if trial not in complete}
        reports[model] = dict(complete_trials=len(complete), complete_answers=5 * len(complete),
                              eligible=len(complete) >= MIN_TRIALS, missing_trials=missing)
        if len(complete) >= MIN_TRIALS:
            keep.append(d[d.trial_id.isin(complete)])
    return pd.concat(keep, ignore_index=True) if keep else pd.DataFrame(), reports


def analyze(records, n_boot=4000, n_perm=10000):
    data, completeness = prepare(records)
    summary = dict(schema_version=SCHEMA_VERSION, study='site-followup-2026-11-10', units='probability_difference',
                   primary_outcome='mentioned', primary_family=list(CONTRASTS), minimum_complete_trials=MIN_TRIALS,
                   completeness=completeness, effects=[])
    if data.empty:
        summary['status'] = 'no_eligible_models'
        return summary
    developers = {m: developer_for_model(m) for m in data.model.unique()}
    summary['status'] = 'analyzed'
    summary['models'] = sorted(developers)
    for outcome in OUTCOMES:
        wide = data.pivot(index=['model', 'scenario', 'trial_id'], columns='condition', values=outcome).astype(float)
        for weighting in ['equal_model', 'equal_developer']:
            family = []
            for name, coefficients in CONTRASTS.items():
                delta = sum(wide[arm] * coef for arm, coef in coefficients.items())
                estimate = effect(delta.rename('delta').reset_index(), n_boot=n_boot, n_perm=n_perm,
                                  developers=developers if weighting == 'equal_developer' else None)
                family.append(dict(contrast=name, outcome=outcome, weighting=weighting,
                                   family='primary' if outcome == 'mentioned' and weighting == 'equal_model' else 'secondary',
                                   **estimate))
            for row, p in zip(family, holm([r['p'] for r in family])):
                row['p_holm'] = p
            summary['effects'].extend(family)
        for arm in SITE[1:]:
            row = effect((wide[arm] - wide.site_B).rename('delta').reset_index(), n_boot=n_boot, n_perm=n_perm)
            row.pop('p')
            summary['effects'].append(dict(contrast=arm + '_vs_B', outcome=outcome, weighting='equal_model',
                                           family='descriptive_baseline', p_holm=None, **row))
    summary['absolute_rates'] = data.groupby(['model', 'condition'])[OUTCOMES].mean().reset_index().to_dict('records')
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--input', type=Path, default=HERE / 'data/responses_bedrock_site.jsonl')
    ap.add_argument('--out-dir', type=Path, default=HERE / 'results')
    args = ap.parse_args()
    result = analyze(read_jsonl(args.input))
    write_json(args.out_dir / 'site_summary.json', result)
    pd.DataFrame(result['effects']).to_csv(args.out_dir / 'site_effects.csv', index=False)
    print(result['status'])


if __name__ == '__main__':
    main()
