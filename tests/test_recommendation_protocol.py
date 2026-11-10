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


# Amendment 1 (10 November 2026): fresh held-out set, uniform re-asks, missing judge labels count as disagreements.

def _valid_no():
    return dict(named=False, recommended=False, preferred=False, warning=False, uncertain=False,
                evidence={k: [] for k in ['named', 'recommended', 'preferred', 'warning']})


@pytest.fixture
def amended(frozen, tmp_path):
    from followup_common import write_json
    from make_recommendation_manifest import freeze_amendment
    guide = json.loads((frozen / 'practice_guide.json').read_text())
    guide['reviewed'] = True
    for ex in guide['examples']:
        ex.update(named=False, recommended=False, preferred=False, warning=False, evidence='',
                  explanation='Reviewed practice rationale.')
    write_json(frozen / 'practice_guide.json', guide)
    directory = tmp_path / 'amended'
    freeze_amendment(frozen, directory, '15:00 IST')
    return directory


def test_amendment_draws_a_fresh_balanced_holdout(frozen, amended):
    from collections import Counter
    p1, items1, _, s1 = load_frozen(frozen)
    p2, items2, keys2, s2 = load_frozen(amended)
    assert items1 == items2 and s2['pilot'] == s1['pilot'] and s2['practice'] == s1['practice']
    assert s2['retired_holdout'] == s1['probability'] + s1['challenge']
    used = set(s1['pilot'] + s1['practice'] + s1['probability'] + s1['challenge'])
    fresh = set(s2['probability'] + s2['challenge'])
    assert len(s2['probability']) == 48 and len(s2['challenge']) == 12 and len(fresh) == 60 and not fresh & used
    assert len(s2['repeats']) == 6 and set(s2['repeats']) <= fresh
    panel = [k for k in keys2 if k['role'] == 'probability']
    assert set(Counter(k['model'] for k in panel).values()) == {4}
    assert set(Counter(k['condition'] for k in panel).values()) == {8}
    assert p2['amendment'] == 1 and p2['judge_max_attempts'] == 3 and p2['min_pairs'] == 80
    assert p2['previous_protocol_hash'] and p2['checker_hash']


def test_amendment_reasks_invalid_outputs_and_rejects_selective_retries(amended, tmp_path):
    from aeotools.llm import LLMResult
    from followup_common import write_jsonl
    from recommendation_data import validated_judges
    from run_recommendation_judge import run
    calls = {}

    def fake(spec, system, user, max_tokens):
        answer = json.loads(user)['answer']
        n = calls[answer] = calls.get(answer, 0) + 1
        text = 'not json' if n == 1 and len(answer) % 2 == 0 else json.dumps(_valid_no())
        return LLMResult(spec, text=text, input_tokens=10, output_tokens=10, cost_usd=.00001)

    out = tmp_path / 'judge.jsonl'
    assert run(amended, 'azure:gpt-5-mini', out, 'human', 1., complete_fn=fake) == 0
    rows = read_jsonl(out)
    second = {r['item_id'] for r in rows if r['attempt'] == 2}
    assert second and all(not r['valid'] for r in rows if r['attempt'] == 1 and r['item_id'] in second)
    _, _, _, _, labels, audit = validated_judges(amended, [out])
    assert len(labels['azure:gpt-5-mini']) == 60 and audit['azure:gpt-5-mini']['reasked_attempts'] == len(second)
    made = sum(calls.values())
    assert run(amended, 'azure:gpt-5-mini', out, 'human', 1., complete_fn=fake) == 0 and sum(calls.values()) == made
    valid_first = next(r for r in rows if r['valid'] and r['attempt'] == 1)
    tampered = tmp_path / 'tampered.jsonl'
    write_jsonl(tampered, rows + [{**valid_first, 'attempt': 2, 'request_id': 'extra'}])
    with pytest.raises(ValueError, match='valid output'):
        validated_judges(amended, [tampered])


def test_amendment_stops_after_three_attempts(amended, tmp_path):
    from aeotools.llm import LLMResult
    from recommendation_data import validated_judges
    from run_recommendation_judge import run
    _, items, _, splits = load_frozen(amended)
    stubborn = {i['item_id']: i['answer'] for i in items}[splits['probability'][0]]

    def fake(spec, system, user, max_tokens):
        text = 'not json' if json.loads(user)['answer'] == stubborn else json.dumps(_valid_no())
        return LLMResult(spec, text=text, input_tokens=10, output_tokens=10, cost_usd=.00001)

    out = tmp_path / 'judge.jsonl'
    assert run(amended, 'azure:gpt-5-mini', out, 'human', 1., complete_fn=fake) == 2
    rows = read_jsonl(out)
    assert max(r['attempt'] for r in rows) == 3
    _, _, _, _, labels, audit = validated_judges(amended, [out])
    assert splits['probability'][0] not in labels['azure:gpt-5-mini'] and audit['azure:gpt-5-mini']['invalid'] >= 1


def test_amended_gate_counts_missing_judge_labels_as_disagreements(amended, tmp_path):
    from aeotools.llm import LLMResult
    from openpyxl import load_workbook
    from make_recommendation_sheet import make_sheet
    from run_recommendation_judge import run
    from score_recommendation_human import score
    _, items, _, splits = load_frozen(amended)
    stubborn = {i['item_id']: i['answer'] for i in items}[splits['probability'][0]]
    workbook, key = tmp_path / 'rater.xlsx', tmp_path / 'key.json'
    make_sheet(amended, workbook, key)
    wb = load_workbook(workbook)
    for row in wb['Evaluation'].iter_rows(min_row=2):
        for cell in row[4:8]:
            cell.value = 'no'
    wb.save(workbook)

    def fake(spec, system, user, max_tokens):
        text = 'not json' if json.loads(user)['answer'] == stubborn else json.dumps(_valid_no())
        return LLMResult(spec, text=text, input_tokens=10, output_tokens=10, cost_usd=.00001)

    out = tmp_path / 'judge.jsonl'
    run(amended, 'azure:gpt-5-mini', out, 'human', 1., complete_fn=fake)
    result = score(amended, workbook, key, [out], approved_error_review=True)['judges']['azure:gpt-5-mini']
    assert result['judge_missing_on_human_items'] == 1 and result['probability_correct_over_48'] == 47 / 48
    assert result['gate_rule'] == 'amendment-1' and result['gate_pass']


def test_amendment_revalidates_every_attempt_and_reports_reasks_by_condition(amended, tmp_path):
    """Added after the fourth review: discarded attempts are re-parsed, not trusted, and re-asks are broken down by
    model and condition."""
    from aeotools.llm import LLMResult
    from followup_common import write_jsonl
    from recommendation_data import validated_judges
    from run_recommendation_judge import run
    calls = {}

    def fake(spec, system, user, max_tokens):
        answer = json.loads(user)['answer']
        n = calls[answer] = calls.get(answer, 0) + 1
        text = 'not json' if n == 1 and len(answer) % 2 == 0 else json.dumps(_valid_no())
        return LLMResult(spec, text=text, input_tokens=10, output_tokens=10, cost_usd=.00001)

    out = tmp_path / 'judge.jsonl'
    assert run(amended, 'azure:gpt-5-mini', out, 'human', 1., complete_fn=fake) == 0
    rows = read_jsonl(out)
    _, _, _, _, _, audit = validated_judges(amended, [out])
    cells = audit['azure:gpt-5-mini']['reasks_by_model_condition']
    assert sum(c['items'] for c in cells) == 60 and sum(c['invalid'] for c in cells) == 0
    assert sum(c['extra_attempts'] for c in cells) == audit['azure:gpt-5-mini']['reasked_attempts'] > 0
    assert sum(c['reasked_items'] for c in cells) == sum(r['attempt'] == 2 for r in rows)
    # A discarded first attempt whose stored flag says invalid, but which the frozen parser accepts, is rejected.
    reasked = next(r for r in rows if r['attempt'] == 2)
    first = next(r for r in rows if r['item_id'] == reasked['item_id'] and r['attempt'] == 1)
    forged = [r for r in rows if r is not first] + [{**first, 'raw_output': json.dumps(_valid_no()), 'error': None}]
    tampered = tmp_path / 'tampered.jsonl'
    write_jsonl(tampered, forged)
    with pytest.raises(ValueError, match='frozen parser'):
        validated_judges(amended, [tampered])
