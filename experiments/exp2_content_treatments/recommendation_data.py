"""Read and revalidate frozen exploratory labels without trusting stored flags."""
from followup_common import digest, read_jsonl
from make_recommendation_manifest import load_frozen
from recommendation_protocol import parse_labels, SYSTEM, judge_configuration


def validated_judges(directory, paths):
    protocol, items, keys, splits = load_frozen(directory)
    item_map = {i['item_id']: i for i in items}
    labels, audit = {}, {}
    excluded = set(splits["pilot"] + splits["practice"])
    seen = set()
    for path in paths:
        for row in read_jsonl(path):
            judge, item_id = row['judge'], row['item_id']
            if row.get('stage') not in ('human', 'full') or item_id in excluded:
                raise ValueError('Development labels cannot enter the frozen evaluation analysis')
            if row.get('protocol_hash') != digest(protocol) or item_id not in item_map:
                raise ValueError('Judge output belongs to a different frozen protocol')
            settings = row.get('settings', {})
            if settings != judge_configuration(judge, settings.get('max_tokens')):
                raise ValueError('Unexpected judge configuration')
            if row.get('fingerprint') != digest([protocol, settings, SYSTEM, 'frozen_evaluation']):
                raise ValueError('Judge configuration fingerprint mismatch')
            if judge in audit and audit[judge]['configuration_hash'] != digest(settings):
                raise ValueError('Mixed judge configurations cannot enter one evaluation')
            if (judge, item_id) in seen:
                raise ValueError('Duplicate judge/item attempts; reconcile explicitly, do not select favourable retries')
            seen.add((judge, item_id))
            labels.setdefault(judge, {})
            counts = audit.setdefault(judge, dict(attempted=0, valid=0, invalid=0, errors={}, configuration_hash=digest(settings), settings=settings))
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
