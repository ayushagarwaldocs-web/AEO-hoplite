"""Offline price-ceiling projections; optional input from a fresh check_bedrock.py smoke run."""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from aeotools.llm import price, estimate_cost
from followup_common import digest, read_jsonl, write_json, timestamp
from recommendation_protocol import CONDITIONS, JUDGES, SYSTEM, judge_input, DEFAULT_MAX_TOKENS
from scenarios import SCENARIOS


# The ceiling prices run about 21% above Bedrock's billed prices, so a $10 ceiling-price cap is about $7.90 billed.
MAX_ATTRIBUTION_BUDGET = 10.


def plan(records, budget=9., check=None, output_tokens=DEFAULT_MAX_TOKENS):
    if (not math.isfinite(budget) or not 0 < budget <= MAX_ATTRIBUTION_BUDGET or type(output_tokens) is not int
            or output_tokens <= 0):
        raise ValueError(f'Use a positive attribution budget <= ${MAX_ATTRIBUTION_BUDGET:g} and a positive judge token limit')
    successful = [r for r in records if not r.get('error')]
    models = sorted({r['model'] for r in successful})
    inputs = {}
    if check is not None:
        inputs = {r['model']: r for r in check if r.get('ok')}
        if set(models) - set(inputs):
            raise ValueError('Live check must contain a successful observation for every main model')
    if len(models) != 12:
        raise ValueError('Cost planning requires the twelve-model main panel')
    generation = []
    for model in models:
        base = [r for r in successful if r['model'] == model and r['condition'] == 'baseline']
        hist_in = sum(r['input_tokens'] for r in base) / len(base)
        hist_out = sum(r['output_tokens'] for r in base) / len(base)
        # With a live check, take the larger of its one observation and the historical baseline mean, so a short
        # smoke-test answer cannot set a cap below a model's usual cost (changed at review, 10 November 2026).
        pin = max(inputs[model]['input_tokens'], hist_in) if inputs else hist_in
        pout = max(inputs[model]['output_tokens'], hist_out) if inputs else hist_out
        if pin <= 0 or pout <= 0:
            raise ValueError('Nonzero input and output usage required for planning')
        pin += 32 * 4 / 5  # ~20 words plus markup, in four of the five arms.
        generation.append(dict(model=model, calls=450, input_tokens_per_call=pin, output_tokens_per_call=pout,
                               ceiling_usd_per_million=list(price(model)), projected_usd=450 * estimate_cost(model, pin, pout)))
    total = sum(r['projected_usd'] for r in generation)
    caps = {r['model']: budget * r['projected_usd'] / total for r in generation}
    queries = {s['id']: s['query'] for s in SCENARIOS}
    answers = [r for r in successful if r['condition'] in CONDITIONS]
    token_estimates = [(len(SYSTEM) + len(judge_input(dict(query=queries[r['scenario']], target=r['target'], answer=r['text'])))) / 4 + 64
                       for r in answers]
    judges = []
    for judge in JUDGES + ['bedrock:qwen.qwen3-32b-v1:0', 'azure:grok-4.6', 'azure:Kimi-K3.1-Pro',
                           'bedrock:zai.glm-5', 'bedrock:global.anthropic.claude-haiku-4-5-20251001-v1:0']:
        mean_input = sum(token_estimates) / len(token_estimates)
        costs = {str(out): len(answers) * estimate_cost(judge, mean_input, out) for out in [output_tokens, 1024]}
        judges.append(dict(judge=judge, preferred=judge in JUDGES, calls=len(answers),
                           estimated_input_tokens=mean_input, assumed_output_tokens=output_tokens,
                           ceiling_usd_per_million=list(price(judge)), projected_usd=costs[str(output_tokens)],
                           output_1024_sensitivity_usd=costs['1024'],
                           evaluation_7470_usd=7470 * estimate_cost(judge, mean_input, output_tokens),
                           pilot_84_usd=84 * estimate_cost(judge, mean_input, output_tokens)))
    return dict(schema_version=1, generated_at=timestamp(), bedrock_check_hash=digest(check) if check is not None else None, study='dated-attribution-followup-and-post-hoc-recommendation',
                assumptions=dict(prices='aeotools.llm.price ceilings; not verified live quotes',
                                 generation_tokens='max(fresh check, historical baseline mean) + 25.6 input tokens' if inputs else 'historical baseline means + 25.6 input tokens',
                                 recommendation_tokens='(system + serialized input) characters / 4 + 64 overhead',
                                 output_tokens=output_tokens, source_hash=digest(records),
                                 note='Planning only; runners reserve byte-count input + 256 and the full output cap before calls. Hidden reasoning/retries may change spend.'),
                attribution=dict(models=generation, projected_total_usd=total, total_cap_usd=budget,
                                 caps_usd=caps, meets_20_percent_contingency=total * 1.2 <= budget),
                recommendation=dict(judges=judges, preferred_judges=JUDGES, main_calls_per_judge=len(answers), evaluation_calls_per_judge=7470, development_calls_per_judge=84))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, default=HERE / 'data/responses_bedrock.jsonl')
    ap.add_argument('--bedrock-check', type=Path, help='JSON from a fresh check_bedrock.py smoke run, copied privately')
    ap.add_argument('--attribution-budget', type=float, default=9.)
    ap.add_argument('--judge-output-tokens', type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--judge-logs', type=Path, nargs='*', default=[], help='private pilot logs for observed token/cost projections')
    args = ap.parse_args()
    from followup_common import require_private
    require_private(args.out)
    result = plan(read_jsonl(args.input), args.attribution_budget,
                  json.loads(args.bedrock_check.read_text()) if args.bedrock_check else None, args.judge_output_tokens)
    result['recommendation']['pilot_projections'] = []
    for path in args.judge_logs:
        rows = read_jsonl(path)
        for judge in sorted({r['judge'] for r in rows}):
            selected = [r for r in rows if r['judge'] == judge]
            mean = sum(r['budget_charge_usd'] for r in selected) / len(selected)
            result['recommendation']['pilot_projections'].append(dict(judge=judge, attempts=len(selected),
                valid=sum(r['valid'] for r in selected), pilot_spent_usd=sum(r['budget_charge_usd'] for r in selected),
                projected_full_usd=7470 * mean, projected_full_with_20_percent_usd=7470 * mean * 1.2,
                complete_pilot=len(selected) == 84))
    write_json(args.out, result)
    for r in result['attribution']['models']:
        print(f"{r['model']}: ${r['projected_usd']:.3f}; cap ${result['attribution']['caps_usd'][r['model']]:.3f}")
    print(f"Attribution projected total: ${result['attribution']['projected_total_usd']:.3f}; cap ${args.attribution_budget:.2f}")
    for r in result['recommendation']['judges']:
        print(f"{r['judge']}: ${r['projected_usd']:.2f} at {r['assumed_output_tokens']} output tokens; "
              f"${r['output_1024_sensitivity_usd']:.2f} at 1024; pilot ${r['pilot_84_usd']:.3f}")


if __name__ == '__main__':
    main()
