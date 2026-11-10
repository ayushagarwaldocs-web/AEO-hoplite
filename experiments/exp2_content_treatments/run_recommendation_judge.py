"""Resumable one-answer-per-call coding of a frozen post-hoc exploratory outcome."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from aeotools.llm import complete
from followup_common import BudgetLog, digest, exclusive, request_ceiling, execution_settings
from make_recommendation_manifest import load_frozen
from recommendation_protocol import SYSTEM, judge_input, parse_labels, judge_configuration, DEFAULT_MAX_TOKENS


def check_gate(protocol, judge, settings, human_report):
    if not human_report:
        raise ValueError('Full main coding requires a passing human report')
    report = json.loads(Path(human_report).read_text())
    checked = report.get('judges', {}).get(judge, {})
    if (report.get('protocol_hash') != digest(protocol) or not checked.get('gate_pass')
            or checked.get('configuration_hash') != digest(settings)):
        raise ValueError('Human gate has not passed for this judge, protocol and configuration')


def run(directory, judge, output, stage, cap, max_tokens=DEFAULT_MAX_TOKENS, complete_fn=None, human_report=None):
    protocol, items, keys, splits = load_frozen(directory)
    if stage not in ('pilot', 'human', 'full'):
        raise ValueError('Unknown judge stage')
    chosen = set(splits['pilot'] if stage == 'pilot' else splits['probability'] + splits['challenge'])
    excluded = set(splits['pilot'] + splits['practice'])
    todo = [i for i in items if i['item_id'] not in excluded] if stage == 'full' else [i for i in items if i['item_id'] in chosen]
    if not todo:
        raise ValueError('No items for requested stage')
    settings = judge_configuration(judge, max_tokens)
    if stage == 'full' and protocol['dataset'] == 'main':
        check_gate(protocol, judge, settings, human_report)
    fingerprint = digest([protocol, settings, SYSTEM, 'development' if stage == 'pilot' else 'frozen_evaluation'])
    complete_fn = complete_fn or complete
    with exclusive(output), execution_settings():
        log = BudgetLog(output, fingerprint, cap)
        attempted = {(r['model'], r['item_id']) for r in log.rows}
        for item in todo:
            if (judge, item['item_id']) in attempted:
                continue
            user = judge_input(item)
            reserve = request_ceiling(judge, SYSTEM, user, max_tokens)
            if not log.permits(judge, reserve):
                print(f'Budget guard stopped before another call; charged ${log.spent:.4f}')
                return 1
            req = log.start(judge, item['item_id'], reserve)
            result = complete_fn(judge, SYSTEM, user, max_tokens=max_tokens)
            row = result.to_dict()
            row.pop('spec', None)
            row.update(judge=judge, raw_output=row.pop('text'), labels=None, valid=False,
                       stage=stage, settings=settings, protocol_hash=digest(protocol),
                       study='recommendation-post-hoc-exploratory')
            try:
                if result.error:
                    raise ValueError('API error: ' + result.error)
                row['labels'] = parse_labels(result.text, item['answer'])
                row['valid'] = True
                row['validation_error'] = None
            except ValueError as exc:
                row['validation_error'] = str(exc)
            log.finish(req, row)
        print(f'Completed stage {stage}; charged ${log.spent:.4f}; invalid attempts are not silently retried')
        return 0 if all(r['valid'] for r in log.rows if r['model'] == judge) else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--directory', type=Path, required=True)
    ap.add_argument('--judge', required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--stage', choices=['pilot', 'human', 'full'], required=True)
    ap.add_argument('--max-spend', type=float, required=True)
    ap.add_argument('--max-tokens', type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument('--human-report', type=Path)
    ap.add_argument('--execute', action='store_true')
    args = ap.parse_args()
    from followup_common import require_private
    require_private(args.directory, args.out)
    protocol, _, _, _ = load_frozen(args.directory)
    if args.stage == 'full' and protocol['dataset'] == 'main':
        check_gate(protocol, args.judge, judge_configuration(args.judge, args.max_tokens), args.human_report)
    if not args.execute:
        print('DRY RUN: no model calls. Add --execute only on the author machine.')
        return 0
    return run(args.directory, args.judge, args.out, args.stage, args.max_spend, args.max_tokens, human_report=args.human_report)


if __name__ == '__main__':
    raise SystemExit(main())
