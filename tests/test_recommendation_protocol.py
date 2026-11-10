import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/exp2_content_treatments'))
from followup_common import read_jsonl
from make_recommendation_manifest import freeze, load_frozen
from recommendation_protocol import parse_labels


def test_strict_labels_and_spans():
    value = dict(named=True, recommended=True, preferred=False, warning=False, uncertain=False,
                 evidence=dict(named=['Acme'], recommended=['Consider Acme'], preferred=[], warning=[]))
    assert parse_labels(json.dumps(value), 'Consider Acme.') == value
    with pytest.raises(ValueError, match='verbatim'):
        parse_labels(json.dumps(value), 'Another answer')
    with pytest.raises(ValueError):
        parse_labels('```json\n' + json.dumps(value) + '\n```', 'Consider Acme.')
    value['preferred'] = 'yes'
    with pytest.raises(ValueError, match='boolean'):
        parse_labels(json.dumps(value), 'Consider Acme.')


def test_span_matching_ignores_formatting_but_not_words():
    value = dict(named=True, recommended=True, preferred=False, warning=False, uncertain=False,
                 evidence=dict(named=['Acme'], recommended=['acme is a strong choice'], preferred=[], warning=[]))
    answer = 'Overall, **Acme** is a  strong choice — and cheap.'
    assert parse_labels(json.dumps(value), answer)['recommended'] is True
    value['evidence']['recommended'] = ['Acme is the best choice']
    with pytest.raises(ValueError, match='verbatim'):
        parse_labels(json.dumps(value), answer)


def test_missing_evidence_list_only_allowed_for_non_positive_labels():
    value = dict(named=True, recommended=True, preferred=False, warning=False, uncertain=False,
                 evidence=dict(named=['Acme'], recommended=['Consider Acme']))
    parsed = parse_labels(json.dumps(value), 'Consider Acme.')
    assert parsed['evidence'] == dict(named=['Acme'], recommended=['Consider Acme'], preferred=[], warning=[])
    value['evidence'] = dict(named=['Acme'])
    with pytest.raises(ValueError, match='evidence'):
        parse_labels(json.dumps(value), 'Consider Acme.')
    value['evidence'] = dict(named=['Acme'], recommended=['Consider Acme'], extra=[])
    with pytest.raises(ValueError, match='four fields'):
        parse_labels(json.dumps(value), 'Consider Acme.')


@pytest.fixture
def frozen(tmp_path):
    records = read_jsonl(ROOT / 'experiments/exp2_content_treatments/data/responses_bedrock.jsonl')
    directory = tmp_path / 'frozen'
    freeze(records, directory, '12:00 IST')
    return directory


def test_manifest_balanced_disjoint_and_blind(frozen):
    from collections import Counter
    p, items, keys, s = load_frozen(frozen)
    assert p['n_items'] == 7560 and len(s['pilot']) == 84
    assert all(set(i) == {'item_id', 'query', 'target', 'answer'} for i in items)
    groups = [set(s[k]) for k in ['pilot', 'practice', 'probability', 'challenge']]
    assert sum(map(len, groups)) == len(set.union(*groups)) == 150
    panel = [k for k in keys if k['role'] == 'probability']
    assert set(Counter(k['model'] for k in panel).values()) == {4}
    assert set(Counter(k['condition'] for k in panel).values()) == {8}
    assert all(k['selection_probability'] > 0 for k in panel)
    assert len(s['repeats']) == 6 and set(s['repeats']) <= groups[2] | groups[3]
    (frozen / 'manifest.jsonl').write_text('{}\n')
    with pytest.raises(ValueError, match='changed'):
        load_frozen(frozen)


def test_judge_fake_blinding_validation_resume(frozen, tmp_path):
    from aeotools.llm import LLMResult
    from run_recommendation_judge import run
    calls = []
    def fake(spec, system, user, max_tokens):
        payload = json.loads(user)
        assert set(payload) == {'query', 'target', 'answer'}
        calls.append(payload)
        output = dict(named=False, recommended=False, preferred=False, warning=False, uncertain=False,
                      evidence={k: [] for k in ['named', 'recommended', 'preferred', 'warning']})
        return LLMResult(spec, text=json.dumps(output), input_tokens=10, output_tokens=10, cost_usd=.00001)
    out = tmp_path / 'judge.jsonl'
    assert run(frozen, 'azure:gpt-5-mini', out, 'pilot', 1., complete_fn=fake) == 0
    assert len(calls) == 84
    assert run(frozen, 'azure:gpt-5-mini', out, 'pilot', 1., complete_fn=fake) == 0
    assert len(calls) == 84
    with pytest.raises(ValueError, match='fingerprint'):
        run(frozen, 'azure:gpt-5-mini', out, 'human', 1., complete_fn=fake)


def test_uncertainty_bounds_and_pairing():
    from analyze_recommendation import summarize
    rows = []
    for i in range(4):
        for c in ['baseline', 'third_party']:
            rows.append(dict(model='a', scenario=f's{i}', trial_id=f's{i}', condition=c,
                             recommended=None if c == 'baseline' else True, preferred=False, warning=False))
    result = summarize(rows, {'third_party_vs_baseline': {'third_party': 1, 'baseline': -1}},
                       n_boot=40, n_perm=50, minimum_pairs=1)
    rec = result[0]
    assert rec['effect'] == 1 and rec['uncertainty_effect_low'] == 0 and rec['uncertainty_effect_high'] == 1
    assert rec['uncertain_labels'] == 4 and rec['n_pairs'] == 4


def test_sheet_roundtrip_tampering_and_repeat_separation(frozen, tmp_path):
    from openpyxl import load_workbook
    from make_recommendation_sheet import make_sheet
    from score_recommendation_human import human_labels
    p, items, keys, s = load_frozen(frozen)
    guide = json.loads((frozen / 'practice_guide.json').read_text())
    guide['reviewed'] = True
    for ex in guide['examples']:
        ex.update(named=False, recommended=False, preferred=False, warning=False, evidence='', explanation='A reviewed practice example.')
    (frozen / 'practice_guide.json').write_text(json.dumps(guide))
    out, key = tmp_path / 'rater.xlsx', tmp_path / 'sheet_key.json'
    presentations = make_sheet(frozen, out, key)
    assert len(presentations) == 72
    wb = load_workbook(out)
    for row in wb['Evaluation'].iter_rows(min_row=2):
        for cell in row[4:8]:
            cell.value = 'no'
    wb.save(out)
    labels, repeats, errors = human_labels(out, key, p)
    assert len(labels) == 60 and len(repeats) == 6 and not errors
    wb['Evaluation']['B2'] = 'Changed query'
    wb.save(out)
    with pytest.raises(ValueError, match='context'):
        human_labels(out, key, p)


def test_human_gate_and_aggregate_analysis(frozen, tmp_path):
    from aeotools.llm import LLMResult
    from openpyxl import load_workbook
    from make_recommendation_sheet import make_sheet
    from run_recommendation_judge import run
    from score_recommendation_human import score
    from analyze_recommendation import analyze
    from followup_common import write_json
    guide = json.loads((frozen / 'practice_guide.json').read_text())
    guide['reviewed'] = True
    for ex in guide['examples']:
        ex.update(named=False, recommended=False, preferred=False, warning=False, evidence='', explanation='Reviewed practice rationale.')
    write_json(frozen / 'practice_guide.json', guide)
    workbook, key = tmp_path / 'rater.xlsx', tmp_path / 'key.json'
    make_sheet(frozen, workbook, key)
    wb = load_workbook(workbook)
    for row in wb['Evaluation'].iter_rows(min_row=2):
        for cell in row[4:8]:
            cell.value = 'no'
    wb.save(workbook)
    def fake(spec, system, user, max_tokens):
        output = dict(named=False, recommended=False, preferred=False, warning=False, uncertain=False,
                      evidence={k: [] for k in ['named', 'recommended', 'preferred', 'warning']})
        return LLMResult(spec, text=json.dumps(output), input_tokens=10, output_tokens=10, cost_usd=.00001)
    out = tmp_path / 'judge.jsonl'
    run(frozen, 'azure:gpt-5-mini', out, 'human', 1, complete_fn=fake)
    result = score(frozen, workbook, key, [out], approved_error_review=True)
    assert result['judges']['azure:gpt-5-mini']['gate_pass']
    assert result['judges']['azure:gpt-5-mini']['panels']['probability']['recommended']['n'] == 48
    assert not score(frozen, workbook, key, [out])['judges']['azure:gpt-5-mini']['gate_pass']
    # Half an annotation dataset must not silently become a completed inference dataset.
    summary = analyze(frozen, [out], n_boot=20, n_perm=20)
    assert all(r['status'] == 'no_eligible_pairs' for r in summary['judges']['azure:gpt-5-mini']['effects']['all'])
    json.dumps(summary, allow_nan=False)
    report_path = tmp_path / 'human_report.json'
    write_json(report_path, result)
    with pytest.raises(ValueError, match='configuration'):
        run(frozen, 'azure:gpt-5-mini', out, 'full', 1, max_tokens=1024, complete_fn=fake, human_report=report_path)
    with pytest.raises(ValueError, match='human report'):
        run(frozen, 'azure:gpt-5-mini', out, 'full', 1, complete_fn=fake)
    assert run(frozen, 'azure:gpt-5-mini', out, 'full', 1, complete_fn=fake, human_report=report_path) == 0
    protocol, _, _, splits = load_frozen(frozen)
    saved = read_jsonl(out)
    assert len(saved) == 7470
    assert not {r['item_id'] for r in saved} & set(splits['pilot'] + splits['practice'])
    summary = analyze(frozen, [out], report_path, n_boot=20, n_perm=20)
    judge = summary['judges']['azure:gpt-5-mini']
    assert judge['missing_items'] == 0 and summary['excluded_development_items'] == 90
    assert all(r['effect'] == 0 for r in judge['effects']['all'])
    assert all(r['n_models'] == 12 for r in judge['effects']['all'])
    write_json(tmp_path / 'recommendation_summary.json', summary)
    import pandas as pd
    pd.DataFrame(judge['effects']['all']).to_csv(tmp_path / 'recommendation_effects.csv', index=False)
    assert len(pd.read_csv(tmp_path / 'recommendation_effects.csv')) == 18


def test_private_paths_and_unknown_annotations(tmp_path):
    from followup_common import require_private
    with pytest.raises(ValueError, match='Private'):
        require_private(tmp_path / 'public-key.json')
    value = dict(named=False, recommended=None, preferred=None, warning=None, uncertain=True,
                 evidence={k: [] for k in ['named', 'recommended', 'preferred', 'warning']})
    assert parse_labels(json.dumps(value), 'No target here')['uncertain'] is True


def test_pilot_projections_use_prices_without_models():
    from plan_followup_costs import plan
    from aeotools.llm import price
    records = read_jsonl(ROOT / 'experiments/exp2_content_treatments/data/responses_bedrock.jsonl')
    result = plan(records)
    assert sum(result['attribution']['caps_usd'].values()) == pytest.approx(9)
    assert result['attribution']['projected_total_usd'] < 9
    assert result['recommendation']['main_calls_per_judge'] == 7560
    assert all(tuple(j['ceiling_usd_per_million']) == price(j['judge']) for j in result['recommendation']['judges'])


def test_empty_judge_reports_declared_family_and_missing_models():
    from analyze_recommendation import summarize
    result = summarize([], {'third_party_vs_baseline': {'third_party': 1, 'baseline': -1}}, planned_models=['missing'])
    assert len(result) == 3
    assert all(r['status'] == 'no_eligible_pairs' and r['missing_or_excluded_models'] == ['missing'] for r in result)
