"""Descriptive extras for the separate-site follow-up (not pre-specified; written while it ran, before its outcomes were
analysed).

    python3 analyze_site_extra.py      # writes results/site_extra.json

Arm rates, completeness, failed and truncated calls, the fresh baseline against the main design's baseline in the same
trials, model-level sign counts, and the outside reviewer's arms against the identical arms of the attribution
follow-up, over the models eligible in both runs. Only models meeting the pre-specified completeness rule, and only
complete trials, are used. The guide-citation rates (`guide_citation_rate_by_arm`) were added after the results were
seen, to show where citations went when the sentence moved to the guide; the rates at which answers cited both pages
(`both_pages_cited_rate_by_arm`) were added after the fourth review, to show that the two are not exclusive.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
ARMS = ["site_B", "site_Q0", "site_Q1", "site_T0", "site_T1"]


def main() -> None:
    summary = json.loads((RES / "site_summary.json").read_text())
    eligible = sorted(m for m, v in summary["completeness"].items() if v["eligible"])
    excluded = sorted(m for m, v in summary["completeness"].items() if not v["eligible"])
    raw = pd.read_json(HERE / "data/responses_bedrock_site.jsonl", lines=True)
    ok = raw[raw["error"].isna() & raw.model.isin(eligible)]
    complete = ok.groupby(["model", "trial_id"]).condition.nunique().reset_index()
    complete = complete[complete.condition == 5][["model", "trial_id"]]
    ok = ok.merge(complete, on=["model", "trial_id"])

    rates = pd.DataFrame(summary["absolute_rates"])
    rates = rates[rates.model.isin(eligible)]
    arm_rates = {arm: float(rates[rates.condition == arm].mentioned.mean()) for arm in ARMS}
    guide = ok.groupby(["model", "condition"]).guide_cited.mean().groupby("condition").mean()
    guide_rates = {arm: float(guide[arm]) for arm in ARMS}
    both = (ok.cited.astype(bool) & ok.guide_cited.astype(bool)).groupby([ok.model, ok.condition]).mean()
    both_rates = {arm: float(both.groupby(level="condition").mean()[arm]) for arm in ARMS}

    old = pd.read_json(HERE / "data/responses_bedrock.jsonl", lines=True)
    old = old[(old.condition == "baseline") & old.model.isin(eligible)][["model", "trial_id", "mentioned"]]
    fresh = ok[ok.condition == "site_B"][["model", "trial_id", "mentioned"]]
    pairs = fresh.merge(old, on=["model", "trial_id"], suffixes=("_fresh", "_original"))
    per_model_rates = pairs.groupby("model")[["mentioned_fresh", "mentioned_original"]].mean()

    wide = ok.pivot_table(index=["model", "trial_id"], columns="condition", values="mentioned").reset_index()
    wide["recommending"] = wide.site_T1 - wide.site_Q1
    wide["neutral"] = wide.site_T0 - wide.site_Q0
    by_model = wide.groupby("model")[["recommending", "neutral"]].mean()

    earlier = json.loads((RES / "attribution_summary.json").read_text())
    both = sorted(set(eligible) & {m for m, v in earlier["completeness"].items() if v["eligible"]})
    earlier_rates = pd.DataFrame(earlier["absolute_rates"])
    earlier_rates = earlier_rates[earlier_rates.model.isin(both)]
    rates_both = rates[rates.model.isin(both)]
    same_arms = {"site_B": "attr_B", "site_Q0": "attr_Q0", "site_Q1": "attr_Q1"}
    across_runs = {"models": both,
                   "site": {s: float(rates_both[rates_both.condition == s].mentioned.mean()) for s in same_arms},
                   "attribution": {s: float(earlier_rates[earlier_rates.condition == a].mentioned.mean())
                                   for s, a in same_arms.items()}}

    out = {
        "note": "Descriptive and exploratory; not part of the pre-specified analysis.",
        "eligible_models": eligible,
        "excluded_models": excluded,
        "rows": int(len(raw)),
        "failed_calls": int(raw["error"].notna().sum()),
        "failed_by_model": raw[raw["error"].notna()].groupby("model").size().astype(int).to_dict(),
        "failed_in_excluded_models": int((raw["error"].notna() & raw.model.isin(excluded)).sum()),
        "truncated_successful_answers": raw[raw["error"].isna() & (raw.stop_reason == "max_tokens")][
            ["model", "condition", "trial_id"]].to_dict("records"),
        "complete_blocks": int(len(complete)),
        "equal_model_mention_rate_by_arm": arm_rates,
        "guide_citation_rate_by_arm": guide_rates,
        "guide_citation_note": "Added after the results were seen; descriptive.",
        "both_pages_cited_rate_by_arm": both_rates,
        "both_pages_note": "Added after the fourth review; descriptive.",
        "identical_arms_across_runs": across_runs,
        "baseline_reproduction": {
            "pairs": int(len(pairs)),
            "fresh_mention_rate": float(pairs.mentioned_fresh.mean()),
            "original_mention_rate": float(pairs.mentioned_original.mean()),
            "same_outcome_share": float((pairs.mentioned_fresh == pairs.mentioned_original).mean()),
            "max_abs_model_rate_difference": float((per_model_rates.mentioned_fresh
                                                    - per_model_rates.mentioned_original).abs().max()),
        },
        "model_signs": {
            "recommending_positive": int((by_model.recommending > 0).sum()),
            "recommending_negative": int((by_model.recommending < 0).sum()),
            "neutral_positive": int((by_model.neutral > 0).sum()),
            "neutral_negative": int((by_model.neutral < 0).sum()),
            "n_models": int(len(by_model)),
        },
        "per_model": {m: {k: float(v) for k, v in row.items()} for m, row in by_model.iterrows()},
    }
    (RES / "site_extra.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("excluded_models", "failed_calls", "complete_blocks",
                                          "equal_model_mention_rate_by_arm", "identical_arms_across_runs",
                                          "baseline_reproduction", "model_signs")}, indent=1))


if __name__ == "__main__":
    main()
