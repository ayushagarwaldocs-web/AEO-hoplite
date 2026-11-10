"""Read and revalidate frozen exploratory labels without trusting stored flags."""
from followup_common import digest, read_jsonl
from make_recommendation_manifest import load_frozen
from recommendation_protocol import parse_labels, SYSTEM, judge_configuration


def _check_row(row, protocol, item_map, excluded):
    """Every stored attempt must belong to this frozen protocol, judge configuration and evaluation stage."""
    if row.get('stage') not in ('human', 'full') or row['item_id'] in excluded:
        raise ValueError('Development labels cannot enter the frozen evaluation analysis')
    if row.get('protocol_hash') != digest(protocol) or row['item_id'] not in item_map:
        raise ValueError('Judge output belongs to a different frozen protocol')
    settings = row.get('settings', {})
    if settings != judge_configuration(row['judge'], settings.get('max_tokens')):
        raise ValueError('Unexpected judge configuration')
    if row.get('fingerprint') != digest([protocol, settings, SYSTEM, 'frozen_evaluation']):
        raise ValueError('Judge configuration fingerprint mismatch')
    return settings


def _parses(row, answer):
    """Validity as the runner defines it, recomputed with the frozen parser: no API error and parseable labels."""
    if row.get('error'):
        return False
    try:
        parse_labels(row['raw_output'], answer)
    except ValueError:
        return False
    return True


def _final_attempts(rows, max_attempts, item_map=None):
    """Version 1: exactly one attempt per judge and item. Amendment 1: attempts numbered 1..k (k <= max), every
    attempt before the last invalid, so a re-ask only ever follows an invalid output; the last attempt is the one
    that counts. With `item_map`, every stored attempt is re-parsed with the frozen parser instead of trusting its
    stored validity flag (added after the fourth review, before any human label or full coding). Returns the counted
    rows, the number of re-asked attempts per judge and the number of attempts per judge and item."""
    grouped = {}
    for row in rows:
        grouped.setdefault((row['judge'], row['item_id']), []).append(row)
    final, reasked, attempts = [], {}, {}
    for (judge, item_id), group in grouped.items():
        if max_attempts == 1:
            if len(group) > 1:
                raise ValueError('Duplicate judge/item attempts; reconcile explicitly, do not select favourable retries')
        else:
            group.sort(key=lambda r: r.get('attempt', 0))
            if [r.get('attempt') for r in group] != list(range(1, len(group) + 1)) or len(group) > max_attempts:
                raise ValueError('Judge attempts must be numbered 1..k within the allowed maximum')
            if any(r.get('valid') for r in group[:-1]):
                raise ValueError('A re-ask followed a valid output; do not select favourable retries')
            if item_map is not None:
                answer = item_map[item_id]['answer']
                if any(bool(r.get('valid')) != _parses(r, answer) for r in group):
                    raise ValueError('A stored validity flag disagrees with the frozen parser')
                if any(_parses(r, answer) for r in group[:-1]):
                    raise ValueError('A re-ask followed an output the frozen parser accepts as valid')
        reasked[judge] = reasked.get(judge, 0) + len(group) - 1
        attempts[(judge, item_id)] = len(group)
        final.append(group[-1])
    return final, reasked, attempts


def validated_judges(directory, paths):
    protocol, items, keys, splits = load_frozen(directory)
    item_map = {i['item_id']: i for i in items}
    excluded = set(splits["pilot"] + splits["practice"])
    rows = [row for path in paths for row in read_jsonl(path)]
    configurations = {}
    for row in rows:
        settings = _check_row(row, protocol, item_map, excluded)
        if configurations.setdefault(row['judge'], digest(settings)) != digest(settings):
            raise ValueError('Mixed judge configurations cannot enter one evaluation')
    final, reasked, attempts = _final_attempts(rows, int(protocol.get('judge_max_attempts', 1)), item_map)
    key_map = {k['item_id']: k for k in keys}
    labels, audit, by_cell = {}, {}, {}
    for row in final:
        judge, item_id = row['judge'], row['item_id']
        labels.setdefault(judge, {})
        counts = audit.setdefault(judge, dict(attempted=0, valid=0, invalid=0, errors={},
                                              reasked_attempts=reasked.get(judge, 0),
                                              configuration_hash=configurations[judge], settings=row['settings']))
        counts['attempted'] += 1
        # Re-asks by model and condition, so condition-dependent coding difficulty is visible (fourth review).
        key = key_map[item_id]
        cell = by_cell.setdefault(judge, {}).setdefault((key['model'], key['condition']),
                                                        dict(items=0, reasked_items=0, extra_attempts=0, invalid=0))
        cell['items'] += 1
        cell['reasked_items'] += attempts[(judge, item_id)] > 1
        cell['extra_attempts'] += attempts[(judge, item_id)] - 1
        try:
            if row.get('error') or not row.get('valid'):
                raise ValueError(row.get('validation_error') or row.get('error') or 'Invalid stored label')
            parsed = parse_labels(row['raw_output'], item_map[item_id]['answer'])
            if parsed != row['labels']:
                raise ValueError('Stored parsed labels differ from raw output')
            labels[judge][item_id] = parsed
            counts['valid'] += 1
        except ValueError as exc:
            counts['invalid'] += 1
            cell['invalid'] += 1
            message = str(exc)
            counts['errors'][message] = counts['errors'].get(message, 0) + 1
    for judge, cells in by_cell.items():
        audit[judge]['reasks_by_model_condition'] = [dict(model=m, condition=c, **v) for (m, c), v in sorted(cells.items())]
    return protocol, items, keys, splits, labels, audit
