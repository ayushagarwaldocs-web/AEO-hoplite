"""Descriptive extras for the attribution follow-up (not pre-specified; added after the run, 10 November 2026).

    python3 analyze_attribution_extra.py      # writes results/attribution_extra.json

1. Baseline reproduction: the fresh `attr_B` prompts are byte-identical to the main design's baseline prompts, so the
   same trials can be compared directly with the answers collected four to six days earlier.
2. Model-level consistency of the two significant primary contrasts, and the ceiling they ran into.
Only models that meet the pre-specified completeness rule, and only complete trials, are used.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RES = HERE / "results"


def main() -> None:
    summary = json.loads((RES / "attribution_summary.json").read_text())
    eligible = sorted(m for m, v in summary["completeness"].items() if v["eligible"])
    excluded = sorted(m for m, v in summary["completeness"].items() if not v["eligible"])
    new = pd.read_json(HERE / "data/responses_bedrock_attribution.jsonl", lines=True)
    new = new[new.model.isin(eligible) & new["error"].isna()]
    complete = new.groupby(["model", "trial_id"]).condition.nunique().reset_index()
    complete = complete[complete.condition == 5][["model", "trial_id"]]
    new = new.merge(complete, on=["model", "trial_id"])

    old = pd.read_json(HERE / "data/responses_bedrock.jsonl", lines=True)
    old = old[(old.condition == "baseline") & old.model.isin(eligible)][["model", "trial_id", "mentioned"]]
    fresh = new[new.condition == "attr_B"][["model", "trial_id", "mentioned"]]
    pairs = fresh.merge(old, on=["model", "trial_id"], suffixes=("_fresh", "_original"))
    per_model_rates = pairs.groupby("model")[["mentioned_fresh", "mentioned_original"]].mean()

    wide = new.pivot_table(index=["model", "trial_id"], columns="condition", values="mentioned").reset_index()
    wide["recommendation"] = wide.attr_S1 - wide.attr_S0
    wide["external"] = wide.attr_Q1 - wide.attr_S1
    by_model = wide.groupby("model")[["recommendation", "external", "attr_S1"]].mean()

    rates = pd.DataFrame(summary["absolute_rates"])
    rates = rates[rates.model.isin(eligible)]
    arm_rates = {arm: float(rates[rates.condition == arm].mentioned.mean())
                 for arm in ["attr_B", "attr_S0", "attr_S1", "attr_Q0", "attr_Q1"]}
    raw = pd.read_json(HERE / "data/responses_bedrock_attribution.jsonl", lines=True)
    truncated = raw[raw["error"].isna() & (raw.stop_reason == "max_tokens")]
    out = {
        "note": "Descriptive and exploratory; not part of the pre-specified analysis.",
        "complete_blocks": int(len(complete)),
        "equal_model_mention_rate_by_arm": arm_rates,
        "truncated_successful_answers": truncated[["model", "condition", "trial_id"]].to_dict("records"),
        "eligible_models": eligible,
        "excluded_models": excluded,
        "baseline_reproduction": {
            "pairs": int(len(pairs)),
            "fresh_mention_rate": float(pairs.mentioned_fresh.mean()),
            "original_mention_rate": float(pairs.mentioned_original.mean()),
            "same_outcome_share": float((pairs.mentioned_fresh == pairs.mentioned_original).mean()),
            "max_abs_model_rate_difference": float((per_model_rates.mentioned_fresh
                                                    - per_model_rates.mentioned_original).abs().max()),
        },
        "model_consistency": {
            "recommendation_positive": int((by_model.recommendation > 0).sum()),
            "recommendation_negative": int((by_model.recommendation < 0).sum()),
            "external_positive": int((by_model.external > 0).sum()),
            "external_zero": int((by_model.external == 0).sum()),
            "external_negative": int((by_model.external < 0).sum()),
            "n_models": int(len(by_model)),
        },
        "self_recommendation_mention_rate": {
            "min": float(by_model.attr_S1.min()), "max": float(by_model.attr_S1.max()),
            "median": float(by_model.attr_S1.median()),
            "models_at_or_above_85pct": int((by_model.attr_S1 >= 0.85).sum()),
        },
        "per_model": {m: {k: float(v) for k, v in row.items()} for m, row in by_model.iterrows()},
    }
    (RES / "attribution_extra.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("excluded_models", "baseline_reproduction", "model_consistency",
                                          "self_recommendation_mention_rate")}, indent=1))


if __name__ == "__main__":
    main()
