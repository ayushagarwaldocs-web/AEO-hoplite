import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments/exp2_content_treatments'))
from attribution import ATTRIBUTION, check_templates
from build_corpus import CONDITIONS, build
from followup_common import BudgetLog, effect, holm


def test_mechanical_templates():
    counts = check_templates()
    assert len(counts['attr_B']) == 90
    assert len(CONDITIONS) == 15 and not set(ATTRIBUTION) & set(CONDITIONS)


def test_clustering_does_not_treat_models_as_independent():
    one = pd.DataFrame([dict(model='a', scenario=f's{i}', trial_id=f's{i}', delta=(i % 3) - .5) for i in range(8)])
    two = pd.concat([one, one.assign(model='b')])
    a, b = effect(one, n_boot=100, n_perm=100), effect(two, n_boot=100, n_perm=100)
    assert a['effect'] == b['effect'] and a['ci_low'] == b['ci_low'] and a['p'] == b['p']
    assert holm([.01, .02, .04]) == [.03, .04, .04]


def test_guard_pending_and_fingerprint(tmp_path):
    path = tmp_path / 'paid.jsonl'
    log = BudgetLog(path, 'frozen', 1)
    req = log.start('fake', 'a', .2)
    with pytest.raises(ValueError, match='Unsettled'):
        BudgetLog(path, 'frozen', 1)
    log.finish(req, dict(cost_usd=.1, input_tokens=2, output_tokens=1))
    assert BudgetLog(path, 'frozen', 1).spent == .1
    with pytest.raises(ValueError, match='fingerprint'):
        BudgetLog(path, 'changed', 1)


def test_attribution_completeness_and_contrast_family():
    from analyze_attribution import analyze, MIN_TRIALS
    rows = [dict(model='bedrock:google.gemma-3-27b-it', **{k: i[k] for k in ['trial_id', 'scenario', 'condition']},
                 mentioned=i['condition'] in ('attr_S1', 'attr_Q1'), top_pick=False, cited=False)
            for i in build(3, ATTRIBUTION)]
    result = analyze(rows, n_boot=40, n_perm=50)
    primary = [r for r in result['effects'] if r['family'] == 'primary']
    assert len(primary) == 3 and MIN_TRIALS == 87
    assert primary[0]['effect'] == 1 and primary[1]['effect'] == primary[2]['effect'] == 0
    missing = analyze(rows[20:], n_boot=40, n_perm=50)
    assert missing['status'] == 'no_eligible_models'
    assert len(missing['completeness']['bedrock:google.gemma-3-27b-it']['missing_trials']) == 4
    with pytest.raises(ValueError, match='Duplicate'):
        analyze(rows + [rows[0]])


def test_attribution_runner_fake_resume_and_budget(tmp_path):
    from aeotools.llm import LLMResult
    from attribution_runner import run_blocks
    calls = []
    def fake(spec, system, user, max_tokens):
        calls.append(user)
        return LLMResult(spec, text='No options [1].', input_tokens=20, output_tokens=10, cost_usd=.000001)
    items = build(3, ATTRIBUTION)[:5]
    out = tmp_path / 'responses_bedrock_attribution.jsonl'
    spec = 'bedrock:google.gemma-3-27b-it'
    assert run_blocks(items, [spec], out, {spec: 1}, complete_fn=fake) == 0
    assert len(calls) == 5
    assert run_blocks(items, [spec], out, {spec: 1}, complete_fn=fake) == 0
    assert len(calls) == 5
    assert run_blocks(items, [spec], tmp_path / 'small.jsonl', {spec: .000001}, complete_fn=fake) == 1
    assert len(calls) == 5


def test_followup_no_transport_retries_and_restored_environment(monkeypatch):
    import os
    import requests
    from aeotools import llm
    from followup_common import execution_settings
    calls = []
    def failed(*args, **kwargs):
        calls.append(1)
        raise requests.Timeout('fake timeout')
    monkeypatch.setattr(llm.requests, 'post', failed)
    monkeypatch.setenv('AEO_TEMPERATURE', '0.7')
    monkeypatch.delenv('AEO_NO_RETRIES', raising=False)
    with execution_settings():
        assert llm._post_with_retry('unused', {}, {}) == 'connection: Timeout'
        assert os.environ['AEO_TEMPERATURE'] == '0'
    assert len(calls) == 1
    assert os.environ['AEO_TEMPERATURE'] == '0.7' and 'AEO_NO_RETRIES' not in os.environ


def test_followup_sdk_clients_disable_retries_without_changing_main(monkeypatch):
    # boto3 and anthropic[bedrock] live only in the project's .venv-local, not in the base Python.
    boto3 = pytest.importorskip("boto3")
    anthropic = pytest.importorskip("anthropic")
    from aeotools import llm
    from followup_common import execution_settings
    clients, configs = [], []
    monkeypatch.setattr(llm, '_bedrock_clients', {})
    def runtime(*args, **kwargs):
        configs.append(kwargs['config'].retries)
        value = object()
        clients.append(value)
        return value
    monkeypatch.setattr(boto3, 'client', runtime)
    with execution_settings():
        assert llm._bedrock_runtime_client() is llm._bedrock_runtime_client()
    llm._bedrock_runtime_client()
    assert configs == [{'total_max_attempts': 1}, {'max_attempts': 8, 'mode': 'adaptive'}]
    kwargs_seen = []
    monkeypatch.setattr(anthropic, 'AnthropicBedrockMantle', lambda **kw: kwargs_seen.append(kw) or object())
    with execution_settings():
        llm._bedrock_claude_client()
    llm._bedrock_claude_client()
    assert [kw['max_retries'] for kw in kwargs_seen] == [0, 5]


def test_attribution_cli_is_separate_and_requires_live_plan(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from attribution_runner import from_args
    from plan_followup_costs import plan
    from followup_common import read_jsonl, write_json
    root = Path(__file__).resolve().parents[1] / 'experiments/exp2_content_treatments'
    p = plan(read_jsonl(root / 'data/responses_bedrock.jsonl'))
    plan_path = tmp_path / 'plan.json'
    write_json(plan_path, p)
    args = SimpleNamespace(conditions=ATTRIBUTION, trials=3, long=False, temperature=0,
                           trial_blocks=True, model_caps=plan_path,
                           out=root / 'data/responses_bedrock_attribution.jsonl',
                           models=list(p['attribution']['caps_usd']), max_spend=9, max_tokens=4000, execute=False)
    assert from_args(args, build(3, ATTRIBUTION)) == 0
    args.execute = True
    with pytest.raises(ValueError, match='fresh Bedrock'):
        from_args(args, build(3, ATTRIBUTION))
    args.out = root / 'data/responses_bedrock.jsonl'
    with pytest.raises(ValueError, match='own responses'):
        from_args(args, build(3, ATTRIBUTION))


def test_attribution_part_mode_runs_one_model_under_private(tmp_path):
    from types import SimpleNamespace
    from attribution_runner import from_args
    from plan_followup_costs import plan
    from followup_common import read_jsonl, write_json
    root = Path(__file__).resolve().parents[1] / 'experiments/exp2_content_treatments'
    p = plan(read_jsonl(root / 'data/responses_bedrock.jsonl'))
    plan_path = tmp_path / 'plan.json'
    write_json(plan_path, p)
    model = sorted(p['attribution']['caps_usd'])[0]
    part_out = root / 'data/private/test-part' / 'x' / 'responses_bedrock_attribution.jsonl'
    args = SimpleNamespace(conditions=ATTRIBUTION, trials=3, long=False, temperature=0, trial_blocks=True,
                           model_caps=plan_path, out=part_out, models=[model], max_spend=9, max_tokens=4000,
                           execute=False, part=True)
    assert from_args(args, build(3, ATTRIBUTION)) == 0          # dry run only; no file is written
    assert not part_out.exists()
    args.models = sorted(p['attribution']['caps_usd'])[:2]
    with pytest.raises(ValueError, match='exactly one model'):
        from_args(args, build(3, ATTRIBUTION))
    args.models = [model]
    args.out = tmp_path / 'responses_bedrock_attribution.jsonl'
    with pytest.raises(ValueError, match='data/private'):
        from_args(args, build(3, ATTRIBUTION))
    args.part, args.out = False, part_out
    with pytest.raises(ValueError, match='own responses'):
        from_args(args, build(3, ATTRIBUTION))
