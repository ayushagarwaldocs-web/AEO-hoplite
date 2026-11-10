from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "exp2_content_treatments"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(EXP))

from analyze import trial_cluster_intervals
from analyze_absorption import detectors, summary_table
from analyze_hypotheses import h3_verdict, position_test
from analyze_absorption_judge import refresh_detector_fields


def _position_fixture():
    rows = []
    for scenario in ["s1", "s2"]:
        for slot in range(1, 7):
            for model in ["m1", "m2"]:
                rows.append({"model": model, "scenario": scenario, "trial_id": f"{scenario}-{slot}",
                             "condition": "baseline", "target_index": slot,
                             "mentioned": int(slot <= 3)})
    return pd.DataFrame(rows)


def test_position_permutation_shares_trial_assignment_across_models():
    result = position_test(_position_fixture(), n_perm=120, rng=np.random.default_rng(91))
    assert result["permutation_unit"] == "scenario/trial; each assignment shared across models"
    assert result["p_perm"] == result["by_model"]["m1"]["p_perm"] == result["by_model"]["m2"]["p_perm"]
    assert "legacy_independent" not in result


def test_position_test_rejects_trial_position_disagreement():
    data = _position_fixture()
    data.loc[(data["trial_id"] == "s1-1") & (data["model"] == "m2"), "target_index"] = 2
    with pytest.raises(ValueError, match="shared across models"):
        position_test(data, n_perm=5, rng=np.random.default_rng(2))


def test_position_intervals_resample_whole_trials_across_models_and_conditions():
    rows = []
    for scenario in ["s1", "s2"]:
        for slot in range(1, 7):
            for condition, mentioned in [("baseline", slot % 2), ("statistics", (slot + 1) % 2),
                                         ("citations", slot % 2)]:
                rows.append({"model": "m1", "scenario": scenario, "trial_id": f"{scenario}-{slot}",
                             "target_index": slot, "plot_condition": "baseline" if condition == "baseline" else "evidence",
                             "condition": condition, "mentioned": mentioned})
    one = pd.DataFrame(rows)
    duplicate = one.copy()
    duplicate["model"] = "m2"
    two = pd.concat([one, duplicate], ignore_index=True)
    ci_one = trial_cluster_intervals(one, n_boot=250, rng=np.random.default_rng(5))
    ci_two = trial_cluster_intervals(two, n_boot=250, rng=np.random.default_rng(5))
    a = ci_one[ci_one["model"] == "m1"].sort_values(["plot_condition", "target_index"])
    b = ci_two[ci_two["model"] == "m1"].sort_values(["plot_condition", "target_index"])
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))


def test_positive_nonsignificant_h3_result_is_inconclusive():
    assert h3_verdict(0.03, 0.21) == "inconclusive"
    assert h3_verdict(0.03, 0.01) == "contradicted"
    assert h3_verdict(-0.03, 0.01) == "inconclusive"


def test_limitation_signal_is_not_attributed_to_another_brand():
    target = {"core": "Ithatence", "anti_fit": "large-breed puppies", "weak": "price per pound",
              "lab": "the Example Lab", "expert": "Dr. Example Person"}
    detector = detectors(target, ("Wynano",))["limitations"]
    assert not detector("Ithatence is budget-focused. Wynano targets large-breed puppies.")
    assert detector("Ithatence is not a good fit for large-breed puppies.")
    assert detector("Ithatence offers value. It is not suitable for large-breed puppies.")


def test_absorption_reports_unconditional_and_conditional_denominators():
    data = pd.DataFrame([
        {"model": "m1", "condition": "statistics", "mentioned": True, "detected": True,
         "absorbed": True, "false_positive": False},
        {"model": "m1", "condition": "statistics", "mentioned": False, "detected": True,
         "absorbed": True, "false_positive": False},
    ])
    pooled = summary_table(data).query("model == 'pooled'").iloc[0]
    assert pooled["n"] == 2
    assert pooled["n_absorbed"] == 2
    assert pooled["absorbed"] == 100.0
    assert pooled["n_mentioned"] == pooled["absorbed_if_mentioned_n"] == 1
    assert pooled["absorbed_if_mentioned"] == 100.0


def test_judge_detector_refresh_preserves_saved_items_and_uses_target_attribution():
    items = [
        {"id": "limitations|treated|m|s1-0", "condition": "limitations", "kind": "treated",
         "model": "m", "trial_id": "s1-0", "brand": "Ithatence",
         "answer": "Ithatence is budget-focused. Wynano targets large-breed puppies.",
         "detector": True, "saved_extra": "unchanged"},
        {"id": "limitations|baseline|m|s1-0", "condition": "limitations", "kind": "baseline",
         "model": "m", "trial_id": "s1-0", "brand": "Ithatence",
         "answer": "Wynano targets large-breed puppies.", "detector": True},
    ]
    responses = [
        {"model": "m", "trial_id": "s1-0", "condition": "limitations", "scenario": "dogfood_picky",
         "target": "Ithatence", "error": None},
        {"model": "m", "trial_id": "s1-0", "condition": "baseline", "scenario": "dogfood_picky",
         "target": "Ithatence", "error": None},
    ]
    brands = {"dogfood_picky": {"brands": [
        {"core": "Ithatence", "name": "Ithatence", "anti_fit": "large-breed puppies", "weak": "price per pound",
         "lab": "the Example Lab", "expert": "Dr. Example Person"},
        {"core": "Wynano", "name": "Wynano", "anti_fit": "raw-food feeders", "weak": "price per pound",
         "lab": "the Other Lab", "expert": "Dr. Other Person"},
    ]}}
    refreshed = refresh_detector_fields(items, responses, brands)
    assert [row["id"] for row in refreshed] == [row["id"] for row in items]
    assert refreshed[0]["detector"] is False
    assert refreshed[1]["detector"] is False
    assert refreshed[0]["saved_extra"] == "unchanged"
    assert items[0]["detector"] is True
