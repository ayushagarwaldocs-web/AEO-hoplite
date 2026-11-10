"""Score the blinded single-rater check; never call it a gold standard."""
import argparse
import json
from pathlib import Path

from openpyxl import load_workbook

from followup_common import agreement, digest, write_json
from make_recommendation_sheet import HEADERS
from recommendation_data import validated_judges


def human_labels(workbook, presentation_key, protocol):
    key = json.loads(Path(presentation_key).read_text())
    if key['protocol_hash'] != digest(protocol):
        raise ValueError('Human key belongs to another protocol')
    wb = load_workbook(workbook, data_only=True)
    labels, repeats, invalid = {}, [], []
    for sheet in ['Practice', 'Evaluation']:
        if list(next(wb[sheet].values)) != HEADERS:
            raise ValueError('Workbook headers changed')
        expected_count = sum(p['sheet'] == sheet for p in key['presentations']) + 1
        if wb[sheet].max_row != expected_count:
            raise ValueError('Workbook rows added/deleted')
    for p in key['presentations']:
        values = [wb[p['sheet']].cell(p['row'], c).value for c in range(1, 11)]
        if digest(values[:4]) != p['context_hash']:
            raise ValueError('Workbook context/order changed')
        if p['sheet'] == 'Practice':
            continue
        raw = values[4:8]
        if raw[0] not in ('yes', 'no') or any(v not in ('yes', 'no', 'uncertain') for v in raw[1:]):
            invalid.append(dict(item_number=p['item_number'], reason='missing/invalid labels'))
            continue
        labels_row = {f: None if v == 'uncertain' else v == 'yes' for f, v in zip(['named', 'recommended', 'preferred', 'warning'], raw)}
        if not labels_row['named'] and any(labels_row[f] is True for f in ['recommended', 'preferred', 'warning']):
            invalid.append(dict(item_number=p['item_number'], reason='positive judgment without target identification'))
            continue
        if labels_row['preferred'] is True and labels_row['recommended'] is not True:
            invalid.append(dict(item_number=p['item_number'], reason='preference without recommendation'))
            continue
        if any(v is True for v in labels_row.values()) and (not isinstance(values[8], str) or not values[8].strip() or values[8] not in values[3]):
            invalid.append(dict(item_number=p['item_number'], reason='positive label needs verbatim answer evidence'))
            continue
        row = dict(item_id=p['item_id'], role=p['role'], labels=labels_row, notes=values[9])
        if p['repeat']:
            repeats.append(row)
        else:
            labels[p['item_id']] = row
    return labels, repeats, invalid


def score(directory, workbook, key, judge_paths, approved_error_review=False):
    protocol, items, keys, splits, judges, audit = validated_judges(directory, judge_paths)
    human, repeats, invalid = human_labels(workbook, key, protocol)
    result = dict(schema_version=1, study='recommendation-post-hoc-exploratory', protocol_hash=digest(protocol),
                  human_design='single non-expert; feasibility/agreement, not independent gold-standard accuracy',
                  expected_probability_n=48, expected_challenge_n=12, valid_unique_n=len(human),
                  invalid_presentations=invalid, error_review_approved=approved_error_review, judges={})
    pairs = [(human[r['item_id']]['labels']['recommended'], r['labels']['recommended']) for r in repeats if r['item_id'] in human]
    result['within_rater_repeat_agreement'] = agreement([p[0] for p in pairs], [p[1] for p in pairs])
    for judge, labels in judges.items():
        by_panel = {}
        for panel in ['probability', 'challenge']:
            ids = [i for i in splits[panel] if i in human and i in labels]
            by_panel[panel] = {field: agreement([human[i]['labels'][field] for i in ids], [labels[i][field] for i in ids])
                               for field in ['named', 'recommended', 'preferred', 'warning']}
            by_panel[panel]['paired_items'] = len(ids)
            by_panel[panel]['human_uncertain_recommendation'] = sum(human[i]['labels']['recommended'] is None for i in ids)
            by_panel[panel]['judge_uncertain_recommendation'] = sum(labels[i]['recommended'] is None for i in ids)
        correct = sum(i in human and i in labels and human[i]['labels']['recommended'] is not None and
                      labels[i]['recommended'] is not None and human[i]['labels']['recommended'] == labels[i]['recommended']
                      for i in splits['probability'])
        warning_errors = [i for i in splits['probability'] + splits['challenge'] if i in human and i in labels
                          and human[i]['labels']['warning'] is True and human[i]['labels']['recommended'] is False
                          and labels[i]['recommended'] is True]
        complete = all(i in human and i in labels for i in splits['probability'] + splits['challenge'])
        result['judges'][judge] = dict(panels=by_panel, configuration_hash=audit[judge]['configuration_hash'],
                                      disagreements=[dict(item_id=i, panel=human[i]['role'], human=human[i]['labels'], judge=labels[i])
                                                     for i in human if i in labels and any(human[i]['labels'][f] != labels[i][f] for f in ['named', 'recommended', 'preferred', 'warning'])],
                                      probability_correct_over_48=correct / 48,
                                      warning_as_recommendation_errors=len(warning_errors),
                                      recurring_warning_error=len(warning_errors) >= 2,
                                      gate_pass=bool(complete and not invalid and correct / 48 >= .9 and
                                                     len(warning_errors) < 2 and approved_error_review),
                                      gate_note='Missing/uncertain items do not count as correct; >=2 warning-only false positives is recurring; author must review all errors')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--directory', type=Path, required=True)
    ap.add_argument('--sheet', type=Path, required=True)
    ap.add_argument('--key', type=Path, required=True)
    ap.add_argument('--judges', type=Path, nargs='+', required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--approve-error-review', action='store_true', help='author confirms no unresolved systematic coding failures')
    args = ap.parse_args()
    from followup_common import require_private
    require_private(args.directory, args.sheet, args.key, args.out, *args.judges)
    result = score(args.directory, args.sheet, args.key, args.judges, args.approve_error_review)
    write_json(args.out, result)
    print(json.dumps({j: r['gate_pass'] for j, r in result['judges'].items()}))


if __name__ == '__main__':
    main()
