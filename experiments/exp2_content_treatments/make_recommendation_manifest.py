"""Freeze private blinded inputs and disjoint splits for the exploratory outcome."""
import argparse
import hashlib
import random
import re
from collections import defaultdict
from pathlib import Path

from build_corpus import build
from followup_common import SEED, digest, read_jsonl, write_json, write_jsonl, timestamp
from recommendation_protocol import CONDITIONS, PANEL_CONDITIONS, CODEBOOK, SYSTEM
from attribution import ATTRIBUTION
from scenarios import SCENARIOS

HERE = Path(__file__).resolve().parent


def freeze(records, directory, freeze_time, dataset='main'):
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d IST', freeze_time):
        raise ValueError('Supply actual freeze time HH:MM IST, not the placeholder')
    directory = Path(directory)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError('Manifest directory is immutable; choose a new empty directory')
    wanted = CONDITIONS if dataset == 'main' else ATTRIBUTION
    queries = {s['id']: s['query'] for s in SCENARIOS}
    canonical = {i['trial_id']: i for i in build(3, ['baseline'])}
    selected = [r for r in records if r['condition'] in wanted and not r.get('error')]
    selected.sort(key=lambda r: (r['model'], r['condition'], r['trial_id']))
    keys, manifest, cells = [], [], defaultdict(list)
    seen = set()
    for r in selected:
        identity = [r['model'], r['condition'], r['trial_id']]
        if tuple(identity) in seen:
            raise ValueError('Duplicate successful source response')
        seen.add(tuple(identity))
        if r['trial_id'] not in canonical or r['scenario'] != canonical[r['trial_id']]['scenario'] or r['target'] != canonical[r['trial_id']]['target']:
            raise ValueError('Response does not match frozen main trial/scenario/target')
        item_id = digest([SEED, dataset, identity])[:24]
        manifest.append(dict(item_id=item_id, query=queries[r['scenario']], target=r['target'], answer=r['text']))
        keys.append(dict(item_id=item_id, dataset=dataset, model=r['model'], condition=r['condition'],
                         trial_id=r['trial_id'], scenario=r['scenario'], role='remaining',
                         selection_probability=None, selection_design='census'))
        cells[(r['model'], r['condition'])].append(item_id)
    models = sorted({r['model'] for r in selected})
    if dataset == 'main' and (len(models) != 12 or len(selected) != 7560 or any(len(v) != 90 for v in cells.values())):
        raise ValueError('Main recommendation manifest requires 12 models x 90 trials x 7 conditions')
    if not selected:
        raise ValueError('No successful answers')
    key = {r['item_id']: r for r in keys}
    lookup = {r['item_id']: r for r in manifest}
    rng = random.Random(SEED)
    splits = dict(pilot=[], practice=[], probability=[], challenge=[], repeats=[])

    def take(ids, role, probability=None, design='purposive diagnostic'):
        for item in ids:
            key[item].update(role=role, selection_probability=probability, selection_design=design)
        splits[role].extend(ids)

    if dataset == 'main':
        for cell in sorted(cells):
            take([rng.choice(cells[cell])], 'pilot', 1 / 90, 'one random item per model x condition cell')
        shuffled_models, shuffled_conditions = models[:], PANEL_CONDITIONS[:]
        rng.shuffle(shuffled_models)
        rng.shuffle(shuffled_conditions)
        for c, condition in enumerate(shuffled_conditions):
            for j in range(8):
                model = shuffled_models[(2 * c + j) % 12]
                eligible = [i for i in cells[(model, condition)] if key[i]['role'] == 'remaining']
                take([rng.choice(eligible)], 'probability', (8 / 12) / len(eligible),
                     'conditional on pilot: randomized balanced cell allocation, then SRS within cell')
        for condition in PANEL_CONDITIONS:
            eligible = [r['item_id'] for r in keys if r['condition'] == condition and r['role'] == 'remaining']
            take([rng.choice(eligible)], 'practice', 1 / len(eligible), 'random practice, not evaluation')
        candidates = [i for i in lookup if key[i]['role'] == 'remaining']
        rng.shuffle(candidates)
        def challenge_score(i):
            text = lookup[i]['answer'].lower()
            target = lookup[i]['target'].lower()
            if target not in text:
                return 0
            warning = bool(re.search(r'\b(inject\w*|manipulat\w*|avoid|warn\w*|not recommend|ignore)\b', text))
            recommendation = bool(re.search(r'\b(recommend\w*|choose|pick|shortlist|consider)\b', text))
            conditional = bool(re.search(r'\b(if|unless|however|but)\b', text))
            return 4 * warning + 2 * (not recommendation) + conditional
        candidates.sort(key=lambda i: -challenge_score(i))
        take(candidates[:12], 'challenge')
        for i in splits['challenge']:
            key[i]['challenge_score'] = challenge_score(i)
        splits['repeats'] = rng.sample(splits['probability'] + splits['challenge'], 6)
    directory.mkdir(parents=True, exist_ok=True)
    write_jsonl(directory / 'manifest.jsonl', manifest)
    write_jsonl(directory / 'key.jsonl', keys)
    write_json(directory / 'splits.json', splits)
    protocol = dict(schema_version=1, study='recommendation-post-hoc-exploratory', dataset=dataset,
                    specified_date='2026-11-10', frozen_at=timestamp(), freeze_time=freeze_time, seed=SEED, n_items=len(manifest),
                    conditions=wanted, models=models, source_hash=digest(records),
                    manifest_hash=digest(manifest), key_hash=digest(keys), splits_hash=digest(splits),
                    rubric_hash=digest([CODEBOOK, SYSTEM]),
                    probability_panel_excludes='keyword_stuffing' if dataset == 'main' else None,
                    probability_note='48 random items: 8 per six conditions, 4 per model; keyword stuffing remains in pilot and full coding',
                    split_counts={k: len(v) for k, v in splits.items()})
    write_json(directory / 'protocol.json', protocol)
    write_json(directory / 'practice_guide.json', dict(reviewed=False, examples=[dict(item_id=i,
               explanation='AUTHOR: review this practice answer and supply worked labels and an explanation.',
               named=None, recommended=None, preferred=None, warning=None, evidence='') for i in splits['practice']]))
    return protocol


def load_frozen(directory):
    import json
    directory = Path(directory)
    p = json.loads((directory / 'protocol.json').read_text())
    items = read_jsonl(directory / 'manifest.jsonl')
    keys = read_jsonl(directory / 'key.jsonl')
    splits = json.loads((directory / 'splits.json').read_text())
    for name, data in [('manifest', items), ('key', keys), ('splits', splits)]:
        if digest(data) != p[name + '_hash']:
            raise ValueError(f'Frozen {name} changed')
    if digest([CODEBOOK, SYSTEM]) != p['rubric_hash']:
        raise ValueError('Rubric changed: create a new frozen protocol and separate judge output')
    return p, items, keys, splits


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, default=HERE / 'data/responses_bedrock.jsonl')
    ap.add_argument('--directory', type=Path, default=HERE / 'data/private/recommendation_main')
    ap.add_argument('--dataset', choices=['main', 'attribution'], default='main')
    ap.add_argument('--freeze-time', required=True)
    args = ap.parse_args()
    from followup_common import require_private
    require_private(args.directory)
    print(freeze(read_jsonl(args.input), args.directory, args.freeze_time, args.dataset))


if __name__ == '__main__':
    main()
