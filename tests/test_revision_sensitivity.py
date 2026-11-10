"""Tests for exploratory Study 2 weighting and length diagnostics."""

import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "experiments" / "exp2_content_treatments"
sys.path.insert(0, str(SCRIPT_DIR))

from analyze_revision import (  # noqa: E402
    aggregate_trials,
    analyze_dataset,
    developer_for_model,
    paired_rows,
    target_length_summaries,
)


def _rows():
    rows = []
    model_names = [
        "bedrock:anthropic.claude-test",
        "bedrock:anthropic.claude-test-2",
        "bedrock:openai.test-model",
    ]
    for model_index, model in enumerate(model_names):
        for scenario in ("scenario_a", "scenario_b"):
            for trial in (0, 1):
                j = (0 if scenario == "scenario_a" else 2) + trial
                if model_index == 0:
                    baseline, treated = False, True
                elif model_index == 1:
                    baseline = treated = (j % 2 == 0)
                else:
                    baseline, treated = True, False
                trial_id = f"{scenario}-{trial}"
                rows.extend([
                    {"model": model, "scenario": scenario, "trial_id": trial_id,
                     "condition": "baseline", "mentioned": baseline, "target_words": 100,
                     "error": None},
                    {"model": model, "scenario": scenario, "trial_id": trial_id,
                     "condition": "third_party", "mentioned": treated, "target_words": 130,
                     "error": None},
                ])
    return rows


def test_model_developer_mapping_uses_developer_not_api_host():
    assert developer_for_model("bedrock:global.anthropic.claude-sonnet-4-6") == "Anthropic"
    assert developer_for_model("bedrock:openai.gpt-oss-120b-1:0") == "OpenAI"
    assert developer_for_model("azure:DeepSeek-V4-Pro") == "DeepSeek"
    assert developer_for_model("azure:Kimi-K3.1-Pro") == "Moonshot AI"
    assert developer_for_model("azure:MAI-Thinking-1") == "Microsoft"
    with pytest.raises(ValueError, match="explicit model-developer mapping"):
        developer_for_model("azure:unknown-model")


def test_paired_estimates_exclude_failed_and_unmatched_answers():
    rows = _rows()
    rows = [row for row in rows if not (
        row["model"] == "bedrock:openai.test-model"
        and row["condition"] == "third_party"
        and row["trial_id"] in {"scenario_a-0", "scenario_b-1"}
    )]
    rows.append({"model": "bedrock:openai.test-model", "scenario": "scenario_a",
                 "trial_id": "scenario_a-0", "condition": "third_party",
                 "mentioned": True, "target_words": 130, "error": "timeout"})
    pairs = paired_rows(pd.DataFrame(rows), "third_party")
    assert len(pairs) == 10
    assert not ((pairs.model == "bedrock:openai.test-model") & (pairs.trial_id == "scenario_a-0")).any()
    assert not ((pairs.model == "bedrock:openai.test-model") & (pairs.trial_id == "scenario_b-1")).any()
    assert (pairs["diff"] == 0).sum() == 4


def test_equal_developer_and_equal_model_weights_are_distinct_and_absolute():
    pairs = paired_rows(pd.DataFrame(_rows()), "third_party")
    model = aggregate_trials(pairs, "equal_model").iloc[0]
    developer = aggregate_trials(pairs, "equal_developer").iloc[0]
    assert model.baseline_mentioned == pytest.approx(0.5)
    assert model.treated_mentioned == pytest.approx(0.5)
    assert model["diff"] == pytest.approx(0.0)
    assert developer.baseline_mentioned == pytest.approx(0.625)
    assert developer.treated_mentioned == pytest.approx(0.375)
    assert developer["diff"] == pytest.approx(-0.25)


def test_equal_developer_is_developer_mean_of_model_means_with_unbalanced_pairs():
    rows = _rows()
    rows = [row for row in rows if not (
        row["model"] == "bedrock:openai.test-model"
        and row["condition"] == "third_party"
        and row["trial_id"] in {"scenario_a-0", "scenario_b-1"}
    )]
    pairs = paired_rows(pd.DataFrame(rows), "third_party")
    developer = aggregate_trials(pairs, "equal_developer").iloc[0]
    assert len(pairs) == 10
    # OpenAI retains a full developer weight despite having fewer successful pairs.
    assert developer.baseline_mentioned == pytest.approx(0.625)
    assert developer.treated_mentioned == pytest.approx(0.375)
    assert developer["diff"] == pytest.approx(-0.25)


def test_length_summaries_are_paired_and_deduplicate_model_copies():
    lengths = target_length_summaries(pd.DataFrame(_rows()), "fixture").set_index("condition")
    assert lengths.loc["baseline", "n_pages"] == 4
    assert lengths.loc["third_party", "n_pages"] == 4
    assert lengths.loc["third_party", "median_words"] == 130
    assert lengths.loc["third_party", "n_paired_pages"] == 4
    assert lengths.loc["third_party", "mean_delta_vs_baseline"] == 30
    assert lengths.loc["third_party", "median_delta_vs_baseline"] == 30


def test_dataset_analysis_reports_finite_lodo_intervals_and_weighted_rates():
    result = analyze_dataset(pd.DataFrame(_rows()), "fixture", "fixture.jsonl", bootstrap_samples=100)
    effects = result["developer_effects"]
    pooled = effects[
        (effects.condition == "third_party")
        & effects.weighting.isin(["equal_model", "equal_developer"])
    ]
    assert set(pooled.weighting) == {"equal_model", "equal_developer"}
    assert pooled.ci_low.notna().all() and pooled.ci_high.notna().all()
    assert (pooled.ceiling_headroom >= 0).all()
    lodo = result["leave_one_developer_out"]
    assert set(lodo.excluded_developer) == {"Anthropic", "OpenAI"}
    assert lodo.ci_low.notna().all() and lodo.ci_high.notna().all()
    assert "OpenAI" in result["summary"]["developer_map"].values()
    estimand = result["summary"]["estimand"]["equal_developer"]
    assert "successful paired trials" in estimand and "average developer means equally" in estimand


def test_missing_filler_pair_is_counted_not_imputed_as_a_nonmention():
    rows = _rows()
    for row in _rows():
        if row["condition"] == "third_party":
            copy = dict(row, condition="filler")
            if not (copy["model"] == "bedrock:openai.test-model" and copy["trial_id"] == "scenario_a-0"):
                rows.append(copy)
    result = analyze_dataset(pd.DataFrame(rows), "fixture", "fixture.jsonl", bootstrap_samples=20)
    filler = result["summary"]["weighted_effects"]["filler"]["equal_developer"]
    assert filler["n_expected_pairs"] == 12
    assert filler["n_paired"] == 11
    assert filler["n_missing_pairs"] == 1
