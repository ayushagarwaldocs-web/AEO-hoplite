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


def _final_attempts(rows, max_attempts):
    """Version 1: exactly one attempt per judge and item. Amendment 1: attempts numbered 1..k (k <= max), every
    attempt before the last invalid, so a re-ask only ever follows an invalid output; the last attempt is the one
    that counts. Returns the counted rows and the number of re-asked attempts per judge."""
    grouped = {}
    for row in rows:
        grouped.setdefault((row['judge'], row['item_id']), []).append(row)
    final, reasked = [], {}
    for (judge, _), group in grouped.items():
        if max_attempts == 1:
            if len(group) > 1:
                raise ValueError('Duplicate judge/item attempts; reconcile explicitly, do not select favourable retries')
        else:
            group.sort(key=lambda r: r.get('attempt', 0))
            if [r.get('attempt') for r in group] != list(range(1, len(group) + 1)) or len(group) > max_attempts:
                raise ValueError('Judge attempts must be numbered 1..k within the allowed maximum')
            if any(r.get('valid') for r in group[:-1]):
                raise ValueError('A re-ask followed a valid output; do not select favourable retries')
        reasked[judge] = reasked.get(judge, 0) + len(group) - 1
        final.append(group[-1])
    return final, reasked


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
    final, reasked = _final_attempts(rows, int(protocol.get('judge_max_attempts', 1)))
    labels, audit = {}, {}
    for row in final:
        judge, item_id = row['judge'], row['item_id']
        labels.setdefault(judge, {})
        counts = audit.setdefault(judge, dict(attempted=0, valid=0, invalid=0, errors={},
                                              reasked_attempts=reasked.get(judge, 0),
                                              configuration_hash=configurations[judge], settings=row['settings']))
        counts['attempted'] += 1
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
            message = str(exc)
            counts['errors'][message] = counts['errors'].get(message, 0) + 1
    return protocol, items, keys, splits, labels, audit
