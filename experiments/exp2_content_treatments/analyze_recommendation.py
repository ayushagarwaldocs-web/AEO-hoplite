"""Post-hoc exploratory recommendation effects, never part of main-study claims."""
import argparse
import itertools
import json
from pathlib import Path

import pandas as pd

from analyze_attribution import CONTRASTS, MIN_TRIALS
from analyze_revision import developer_for_model
from followup_common import agreement, digest, effect, holm, write_json
from recommendation_data import validated_judges
from recommendation_protocol import CONDITIONS, JUDGES


def summarize(rows, contrasts, n_boot=4000, n_perm=10000, minimum_pairs=MIN_TRIALS, planned_models=None):
    results = []
    data = pd.DataFrame(rows, columns=['model', 'scenario', 'trial_id', 'condition', 'recommended', 'preferred', 'warning'])
    expected_models = set(planned_models) if planned_models is not None else set(data.model)
    for outcome in ['recommended', 'preferred', 'warning']:
        family = []
        for name, coefficients in contrasts.items():
            required = list(coefficients)
            d = data[data.condition.isin(required)]
            counts = d.groupby(['model', 'scenario', 'trial_id']).condition.nunique()
            complete = counts[counts == len(required)].index
            paired = d.set_index(['model', 'scenario', 'trial_id']).loc[complete].reset_index() if len(complete) else d.iloc[:0]
            n_by_model = paired.groupby('model').trial_id.nunique()
            eligible = n_by_model[n_by_model >= minimum_pairs].index
            paired = paired[paired.model.isin(eligible)]
            if paired.empty:
                family.append(dict(contrast=name, outcome=outcome, status='no_eligible_pairs', p=None,
                                   pair_counts=n_by_model.to_dict(), missing_or_excluded_models=sorted(expected_models - set(eligible))))
                continue
            wide = paired.pivot(index=['model', 'scenario', 'trial_id'], columns='condition', values=outcome)
            lower = wide.apply(lambda col: col.map(lambda v: float(v is True)))
            upper = wide.apply(lambda col: col.map(lambda v: float(v is True or v is None or pd.isna(v))))
            delta = sum(lower[c] * a for c, a in coefficients.items())
            estimate = effect(delta.rename('delta').reset_index(), n_boot=n_boot, n_perm=n_perm)
            bound_low = sum((lower[c] if a > 0 else upper[c]) * a for c, a in coefficients.items())
            bound_high = sum((upper[c] if a > 0 else lower[c]) * a for c, a in coefficients.items())
            # Bounds use the same equal-model weighting as the estimand, not pooled answer counts.
            point = lambda x: float(x.groupby('model').mean().mean())
            uncertain = int(paired[outcome].isna().sum())
            family.append(dict(contrast=name, outcome=outcome, status='analyzed', **estimate,
                               uncertainty_effect_low=point(bound_low), uncertainty_effect_high=point(bound_high),
                               uncertain_labels=uncertain, valid_paired_answers=len(paired), pair_counts=n_by_model.to_dict(),
                               missing_or_excluded_models=sorted(expected_models - set(eligible))))
        # Keep the full declared family size even if a contrast is unestimable.
        adjusted = holm([r['p'] if r['p'] is not None else 1. for r in family])
        for r, p in zip(family, adjusted):
            r['p_holm'] = p if r['p'] is not None else None
        results.extend(family)
    return results


def analyze(directory, paths, human_report=None, n_boot=4000, n_perm=10000):
    protocol, items, keys, splits, judges, audit = validated_judges(directory, paths)
    key_map = {r['item_id']: r for r in keys}
    dataset = protocol['dataset']
    contrasts = {c + '_vs_baseline': {c: 1, 'baseline': -1} for c in CONDITIONS[1:]} if dataset == 'main' else CONTRASTS
    result = dict(schema_version=1, study='recommendation-post-hoc-exploratory', dataset=dataset,
                  protocol_hash=digest(protocol), units='probability_difference',
                  primary_judge=JUDGES[0], primary_outcome='recommended' if dataset == 'main' else None,
                  estimand='definite favourable recommendation over all valid paired answers, including uncertain answers in denominator',
                  uncertainty_note='Unknown labels are not asserted negative: lower/upper identification bounds are reported separately; intervals/tests concern definite positives',
                  family_size=len(contrasts), minimum_pairs_per_model=int(protocol.get('min_pairs', MIN_TRIALS)),
                  expected_items=len(items) - len(splits['pilot']) - len(splits['practice']),
                  excluded_development_items=len(splits['pilot']) + len(splits['practice']), audit=audit, judges={}, between_judges={})
    if human_report:
        human = json.loads(Path(human_report).read_text())
        if human['protocol_hash'] != digest(protocol):
            raise ValueError('Human report protocol mismatch')
        result['human_agreement'] = {**human, 'judges': {j: {k: v for k, v in r.items() if k != 'disagreements'} for j, r in human['judges'].items()}}
    for judge, labels in judges.items():
        rows = [{**key_map[i], **{k: lab[k] for k in ['recommended', 'preferred', 'warning']}} for i, lab in labels.items()]
        own = developer_for_model(judge)
        variants = dict(all=rows, excluding_judge_developer=[r for r in rows if developer_for_model(r['model']) != own])
        minimum = int(protocol.get('min_pairs', MIN_TRIALS))  # amendment 1: 80 of the 87-88 pairs that exist
        estimates = {name: summarize(r, contrasts, n_boot, n_perm, minimum_pairs=minimum,
                                     planned_models=[m for m in protocol['models']
                                                     if name == 'all' or developer_for_model(m) != own])
                     for name, r in variants.items()}
        absolute = []
        for (model, condition), group in itertools.groupby(sorted(rows, key=lambda r: (r['model'], r['condition'])),
                                                           key=lambda r: (r['model'], r['condition'])):
            group = list(group)
            absolute.append(dict(model=model, condition=condition, n=len(group),
                                 recommended=sum(r['recommended'] is True for r in group) / len(group),
                                 uncertain=sum(r['recommended'] is None for r in group) / len(group)))
        result['judges'][judge] = dict(developer=own, effects=estimates, absolute_rates=absolute,
                                      missing_items=result['expected_items'] - len(labels),
                                      item_coverage_by_model_condition=[dict(model=m, condition=c, expected=sum(k['model'] == m and k['condition'] == c and k['role'] not in ('pilot', 'practice') for k in keys),
                                                                            valid=sum(k['model'] == m and k['condition'] == c and k['item_id'] in labels for k in keys))
                                                                        for m in protocol['models'] for c in protocol['conditions']])
    for a, b in itertools.combinations(sorted(judges), 2):
        paired = sorted(set(judges[a]) & set(judges[b]))
        subsets = {'all': paired, **{c: [i for i in paired if key_map[i]['condition'] == c] for c in protocol['conditions']}}
        result['between_judges'][a + ' | ' + b] = {
            subset: {field: {**agreement([judges[a][i][field] for i in ids], [judges[b][i][field] for i in ids]),
                             'paired_valid': len(ids),
                             'disagreement_including_uncertainty': sum(judges[a][i][field] != judges[b][i][field] for i in ids) / len(ids) if ids else None}
                     for field in ['named', 'recommended', 'preferred', 'warning']} for subset, ids in subsets.items()}
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--directory', type=Path, required=True)
    ap.add_argument('--judges', type=Path, nargs='+', required=True)
    ap.add_argument('--human-report', type=Path)
    ap.add_argument('--out-dir', type=Path, required=True)
    args = ap.parse_args()
    from followup_common import require_private
    require_private(args.directory, *args.judges)
    result = analyze(args.directory, args.judges, args.human_report)
    write_json(args.out_dir / 'recommendation_summary.json', result)
    csv = [{**row, 'judge': j, 'analysis': variant} for j, data in result['judges'].items()
           for variant, rows in data['effects'].items() for row in rows]
    pd.DataFrame(csv).to_csv(args.out_dir / 'recommendation_effects.csv', index=False)
    print(f"Analyzed {len(result['judges'])} judges; dataset={result['dataset']}")


if __name__ == '__main__':
    main()
