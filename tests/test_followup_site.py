"""Separate-site follow-up: stimuli, command-line guards and analysis, offline only."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/exp2_content_treatments'))
sys.path.insert(0, str(ROOT))

from attribution import SITE, check_site_templates  # noqa: E402
from build_corpus import build  # noqa: E402
from followup_common import digest, read_jsonl, write_json  # noqa: E402


def test_site_arms_add_the_same_sentence_on_different_pages():
    grouped = check_site_templates()
    assert len(grouped) == 90 and all(set(arms) == set(SITE) for arms in grouped.values())


def test_site_arms_leave_main_and_attribution_prompts_unchanged():
    assert digest(build(3)) == '2132d8f751aac9fd32cda2358c60dbfe343960f1eae4e31db0b9380e70fbc51c'


def test_site_cli_dry_run_and_output_paths(tmp_path):
    from attribution_runner import from_args
    from plan_followup_costs import plan
    exp = ROOT / 'experiments/exp2_content_treatments'
    p = plan(read_jsonl(exp / 'data/responses_bedrock.jsonl'))
    plan_path = tmp_path / 'plan.json'
    write_json(plan_path, p)
    models = list(p['attribution']['caps_usd'])
    args = SimpleNamespace(conditions=SITE, trials=3, long=False, temperature=0, trial_blocks=True,
                           model_caps=plan_path, out=exp / 'data/responses_bedrock_site.jsonl', models=models,
                           max_spend=9, max_tokens=4000, execute=False, part=False)
    assert from_args(args, build(3, SITE), kind='site') == 0
    args.out = exp / 'data/responses_bedrock_attribution.jsonl'
    with pytest.raises(ValueError, match='own responses_bedrock_site'):
        from_args(args, build(3, SITE), kind='site')
    args.part, args.models = True, models[:1]
    args.out = exp / 'data/private/test-site-part/x/responses_bedrock_site.jsonl'
    assert from_args(args, build(3, SITE), kind='site') == 0 and not args.out.exists()
    args.conditions = SITE[:4]
    with pytest.raises(ValueError, match='all five arms'):
        from_args(args, build(3, SITE[:4]), kind='site')


def test_site_analysis_on_fabricated_answers():
    from analyze_site import analyze, CONTRASTS
    items = build(3, SITE)
    models = sorted({r['model'] for r in read_jsonl(ROOT / 'experiments/exp2_content_treatments/data/responses_bedrock.jsonl')})
    rate = {'site_B': 0, 'site_Q0': 0, 'site_Q1': 1, 'site_T0': 1, 'site_T1': 1}
    records = [dict(model=m, trial_id=i['trial_id'], scenario=i['scenario'], condition=i['condition'],
                    target=i['target'], target_index=i['target_index'], guide_index=i['guide_index'],
                    n_sources=i['n_sources'], mentioned=rate[i['condition']], top_pick=0, cited=0)
               for m in models for i in items]
    summary = analyze(records, n_boot=20, n_perm=20)
    assert summary['status'] == 'analyzed' and len(summary['models']) == 12
    primary = [e for e in summary['effects'] if e['family'] == 'primary']
    assert [e['contrast'] for e in primary] == list(CONTRASTS)
    by_name = {e['contrast']: e['effect'] for e in primary}
    assert by_name == {'site_recommending': 0, 'site_neutral': 1, 'site_by_wording': -1}
