"""Claim checks for the attribution follow-up: each name states what the paper says, and the test reads the data."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from followup_numbers import E2, attribution_macros


def attribution_claims() -> dict[str, bool]:
    res = E2 / "results"
    if not (res / "attribution_summary.json").exists():
        return {}
    summary = json.loads((res / "attribution_summary.json").read_text())
    extra = json.loads((res / "attribution_extra.json").read_text())
    eff = pd.read_csv(res / "attribution_effects.csv")
    comp = summary["completeness"]

    def row(outcome, contrast, weighting="equal_model"):
        return eff[(eff.outcome == outcome) & (eff.weighting == weighting) & (eff.contrast == contrast)].iloc[0]

    out = {}
    out["attribution: 11 models meet the 87-trial rule; Nemotron 3 Super falls below it and is excluded"] = (
        summary["minimum_complete_trials"] == 87
        and sorted(m for m, v in comp.items() if not v["eligible"]) == ["bedrock:nvidia.nemotron-super-3-120b"]
        and comp["bedrock:nvidia.nemotron-super-3-120b"]["complete_trials"] < 87
        and sum(v["eligible"] for v in comp.values()) == 11)
    out["attribution: recommending wording and the outside source raise mentions after Holm; the interaction does not"] = all(
        row("mentioned", c, w)["effect"] > 0 and row("mentioned", c, w)["p_holm"] < .05
        for c in ("self_recommendation", "external_attribution") for w in ("equal_model", "equal_developer")) and all(
        row("mentioned", "attribution_by_recommendation", w)["p_holm"] >= .05 for w in ("equal_model", "equal_developer"))
    out["attribution: recommending wording does more than the outside source"] = (
        row("mentioned", "self_recommendation")["effect"] > row("mentioned", "external_attribution")["effect"])
    out["attribution: for first mentions all three contrasts are positive after Holm (secondary)"] = all(
        row("top_pick", c)["effect"] > 0 and row("top_pick", c)["p_holm"] < .05
        for c in ("self_recommendation", "external_attribution", "attribution_by_recommendation"))
    cons = extra["model_consistency"]
    out["attribution: recommending wording raises mentions in every model; the outside source in 9, lowers none"] = (
        cons["recommendation_positive"] == cons["n_models"] == 11 and cons["external_positive"] == 9
        and cons["external_negative"] == 0)
    out["attribution: most models already name the brand when it recommends itself (>= 85% in 10 of 11)"] = (
        extra["self_recommendation_mention_rate"]["models_at_or_above_85pct"] == 10)
    base = extra["baseline_reproduction"]
    out["attribution: the fresh baseline reproduces the original within one point"] = (
        abs(base["fresh_mention_rate"] - base["original_mention_rate"]) < .01 and base["same_outcome_share"] > .85)
    out["attribution: a neutral statement alone raises mentions by more than recommending wording adds to it"] = (
        row("mentioned", "attr_S0_vs_B")["effect"] > row("mentioned", "self_recommendation")["effect"])
    records = [json.loads(line) for line in (E2 / "data/responses_bedrock_attribution.jsonl").open() if line.strip()]
    failed = [r for r in records if r.get("error")]
    out["attribution: 5,385 of 5,400 calls made; 11 failed and were not retried, 10 of them Nemotron's, which hit its cap"] = (
        len(records) == 5385 and len(failed) == 11
        and sum(r["model"] == "bedrock:nvidia.nemotron-super-3-120b" for r in failed) == 10
        and len({(r["model"], r["trial_id"], r["condition"]) for r in records}) == len(records))
    numbers = (Path(__file__).parent / "numbers.tex").read_text()
    for name, value in attribution_macros().items():
        out[f"attribution macro {name}: matches generated source"] = (
            f"\\newcommand{{\\{name}}}{{{value}}}" in numbers
            or f"\\newcommand{{\\{name}}}{{{str(value).replace('-', chr(92) + 'ensuremath{-}')}}}" in numbers)
    return out
