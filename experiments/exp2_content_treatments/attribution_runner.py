"""Sequential, complete-block execution for the dated attribution follow-up only."""
import json
import random
from collections import defaultdict
from pathlib import Path

from attribution import ATTRIBUTION
from build_corpus import SYSTEM
from followup_common import BudgetLog, SEED, digest, exclusive, request_ceiling, execution_settings, read_jsonl
from aeotools.metrics import brand_metrics, source_metrics


def ordered_blocks(items, seed=SEED):
    blocks = defaultdict(list)
    for item in items:
        blocks[item['trial_id']].append(item)
    rng = random.Random(seed)
    trials = sorted(blocks)
    rng.shuffle(trials)
    for trial in trials:
        block = sorted(blocks[trial], key=lambda i: i['condition'])
        rng.shuffle(block)
        yield block


def run_blocks(items, models, out, caps, total_cap=9., max_tokens=4000, complete_fn=None):
    from aeotools.llm import complete
    complete_fn = complete_fn or complete
    settings = dict(max_tokens=max_tokens, requested_temperature=0, reasoning='adapter default/low where supported',
                    web_search=False, transport_retries=0, run_order_seed=SEED)
    fingerprint = digest(dict(study='attribution-followup-2026-11-10', items=items, settings=settings))
    with exclusive(out), execution_settings():
        log = BudgetLog(out, fingerprint, total_cap, caps)
        attempted = {(r['model'], r['trial_id'], r['condition']) for r in log.rows}
        stopped = []
        for spec in models:
            if spec not in caps:
                raise ValueError(f'Missing cap for {spec}')
            for block in ordered_blocks(items):
                todo = [i for i in block if (spec, i['trial_id'], i['condition']) not in attempted]
                reserves = [request_ceiling(spec, SYSTEM, i['user'], max_tokens) for i in todo]
                if not log.permits(spec, sum(reserves)):
                    stopped.append(spec)
                    break
                for item, reserve in zip(todo, reserves):
                    req = log.start(spec, item['trial_id'] + '/' + item['condition'], reserve)
                    res = complete_fn(spec, SYSTEM, item['user'], max_tokens=max_tokens)
                    row = {k: v for k, v in item.items() if k not in ('user', 'brands', 'target_fit')}
                    row.update(res.to_dict())
                    if not res.error and not res.text.strip():
                        row['error'] = 'empty_answer'

                    row.pop('spec', None)
                    row.update(settings=settings, study='attribution-followup-2026-11-10')
                    if not row.get('error'):
                        row.update(brand_metrics(res.text, item['brands'], item['target']))
                        row.update(source_metrics(res.text, item['target_index'], item['n_sources']))
                        row['guide_cited'] = source_metrics(res.text, item['guide_index'], item['n_sources'])['cited']
                    log.finish(req, row)
        print(json.dumps(dict(budget_charge_usd=log.spent, by_model=log.by_model, capped_models=stopped), indent=2))
        return 1 if stopped or any(r.get('error') for r in log.rows) else 0


def from_args(args, items):
    if set(args.conditions) != set(ATTRIBUTION) or args.trials != 3 or args.long or args.temperature not in (None, 0):
        raise ValueError('Attribution requires exactly all five arms, 3 trials, short pages and temperature 0')
    if not args.trial_blocks or not args.model_caps:
        raise ValueError('Attribution requires --trial-blocks and --model-caps plan.json')
    here = Path(__file__).resolve().parent
    out = Path(args.out).resolve()
    part = getattr(args, 'part', False)
    if part:
        # One model per process so the panel runs in one short window; each part keeps its own journal and the parts
        # are concatenated afterwards (added at review, 10 November 2026).
        if out.name != 'responses_bedrock_attribution.jsonl' or (here / 'data/private').resolve() not in out.parents:
            raise ValueError('A part run writes data/private/.../responses_bedrock_attribution.jsonl')
        if len(args.models) != 1:
            raise ValueError('A part run covers exactly one model')
    elif out != (here / 'data/responses_bedrock_attribution.jsonl').resolve():
        raise ValueError('Attribution must use its own responses_bedrock_attribution.jsonl')
    plan = json.loads(Path(args.model_caps).read_text())
    caps = plan['attribution']['caps_usd']
    wrong_panel = not set(args.models) <= set(caps) if part else set(args.models) != set(caps)
    if len(args.conditions) != 5 or len(set(args.models)) != len(args.models) or wrong_panel:
        raise ValueError('Run the frozen twelve-model panel with each condition and model exactly once')
    source = read_jsonl(here / 'data/responses_bedrock.jsonl')
    if set(caps) != {r['model'] for r in source} or plan['assumptions']['source_hash'] != digest(source):
        raise ValueError('Cost plan does not match the frozen main source panel')
    if len(caps) != 12 or any(not m.startswith('bedrock:') for m in caps):
        raise ValueError('Attribution requires the twelve Bedrock models')
    from plan_followup_costs import MAX_ATTRIBUTION_BUDGET
    if args.max_spend > MAX_ATTRIBUTION_BUDGET or sum(caps.values()) > MAX_ATTRIBUTION_BUDGET + 1e-9:
        raise ValueError(f'The approved attribution ceiling is ${MAX_ATTRIBUTION_BUDGET:g} total')
    if args.max_tokens != 4000:
        raise ValueError('Attribution uses the frozen 4000-token output limit')
    if not args.execute:
        print(f'DRY RUN: {len(items)} prompts/model; no API calls. Add --execute only on the author machine.')
        return 0
    if not plan.get('bedrock_check_hash') or not plan['attribution']['meets_20_percent_contingency']:
        raise ValueError('Execution requires a fresh Bedrock check projection plus 20% contingency within the cap')
    return run_blocks(items, args.models, args.out, caps, args.max_spend, args.max_tokens)
