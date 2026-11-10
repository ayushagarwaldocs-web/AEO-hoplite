"""Claim checks for the attribution follow-up: each name states what the paper says, and the test reads the data."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from followup_numbers import E2, attribution_macros, site_macros


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
    out["attribution: citation of the target page rises with recommending wording after Holm; the outside source's does not"] = (
        row("cited", "self_recommendation")["effect"] > 0 and row("cited", "self_recommendation")["p_holm"] < .05
        and row("cited", "external_attribution")["effect"] > 0 and row("cited", "external_attribution")["p_holm"] >= .05)
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
    rates = extra["equal_model_mention_rate_by_arm"]
    out["attribution: arm mention rates rise B < S0 < Q0 and S0 < S1 < Q1; 989 complete blocks; one truncated answer"] = (
        rates["attr_B"] < rates["attr_S0"] < rates["attr_Q0"] and rates["attr_S0"] < rates["attr_S1"] < rates["attr_Q1"]
        and extra["complete_blocks"] == 989 and len(extra["truncated_successful_answers"]) == 1)
    numbers = (Path(__file__).parent / "numbers.tex").read_text()
    for name, value in attribution_macros().items():
        out[f"attribution macro {name}: matches generated source"] = (
            f"\\newcommand{{\\{name}}}{{{value}}}" in numbers
            or f"\\newcommand{{\\{name}}}{{{str(value).replace('-', chr(92) + 'ensuremath{-}')}}}" in numbers)
    return out


def site_claims() -> dict[str, bool]:
    """Claims about the separate-site follow-up; the result claims are added in site_result_claims()."""
    res = E2 / "results"
    if not (res / "site_summary.json").exists():
        return {}
    summary = json.loads((res / "site_summary.json").read_text())
    extra = json.loads((res / "site_extra.json").read_text())
    comp = summary["completeness"]
    records = [json.loads(line) for line in (E2 / "data/responses_bedrock_site.jsonl").open() if line.strip()]
    failed = [r for r in records if r.get("error")]
    out = {}
    out["site: the same 87-trial completeness rule; every eligible model has at least 87 complete five-arm trials"] = (
        summary["minimum_complete_trials"] == 87
        and all(v["complete_trials"] >= 87 for v in comp.values() if v["eligible"])
        and all(v["complete_trials"] < 87 for v in comp.values() if not v["eligible"]))
    out["site: one row per model, trial and arm; failed calls kept, not retried"] = (
        len({(r["model"], r["trial_id"], r["condition"]) for r in records}) == len(records)
        and len(failed) == extra["failed_calls"])
    out["site: every row is a site arm of the 12 planned models and the 90 main trials"] = (
        {r["condition"] for r in records} <= {"site_B", "site_Q0", "site_Q1", "site_T0", "site_T1"}
        and len({r["model"] for r in records}) == 12 and len({r["trial_id"] for r in records}) == 90)
    out["site: the first query ran after the 17:31:11 IST freeze (12:01:11 UTC)"] = (
        min(r["started_at"] for r in records) > "2026-11-10T12:01:11")
    numbers = (Path(__file__).parent / "numbers.tex").read_text()
    for name, value in site_macros().items():
        out[f"site macro {name}: matches generated source"] = (
            f"\\newcommand{{\\{name}}}{{{value}}}" in numbers
            or f"\\newcommand{{\\{name}}}{{{str(value).replace('-', chr(92) + 'ensuremath{-}')}}}" in numbers)
    return out


def site_result_claims() -> dict[str, bool]:
    """What Section 5.4, the findings, the discussion and the conclusion say about the separate-site follow-up."""
    res = E2 / "results"
    if not (res / "site_summary.json").exists():
        return {}
    summary = json.loads((res / "site_summary.json").read_text())
    extra = json.loads((res / "site_extra.json").read_text())
    eff = pd.read_csv(res / "site_effects.csv")

    def row(outcome, contrast, weighting="equal_model"):
        return eff[(eff.outcome == outcome) & (eff.weighting == weighting) & (eff.contrast == contrast)].iloc[0]

    def sig_positive(outcome, contrast, weighting="equal_model"):
        r = row(outcome, contrast, weighting)
        return r["effect"] > 0 and r["p_holm"] < .05

    rates, guide = extra["equal_model_mention_rate_by_arm"], extra["guide_citation_rate_by_arm"]
    across = extra["identical_arms_across_runs"]
    out = {}
    out["site: all 5,400 calls succeeded, none reached the token limit; all 12 models and 1,080 complete blocks"] = (
        extra["rows"] == 5400 and extra["failed_calls"] == 0 and not extra["truncated_successful_answers"]
        and len(extra["eligible_models"]) == 12 and not extra["excluded_models"] and extra["complete_blocks"] == 1080
        and summary["status"] == "analyzed")
    out["site: on the guide the neutral sentence raised mentions after Holm, with both weightings; positive in 8 models"] = (
        sig_positive("mentioned", "site_neutral") and sig_positive("mentioned", "site_neutral", "equal_developer")
        and extra["model_signs"]["neutral_positive"] == 8)
    out["site: on the guide the neutral sentence raised first mentions after Holm"] = sig_positive("top_pick", "site_neutral")
    out["site: for the recommending sentence the guide-vs-brand difference in mentions was not resolved"] = all(
        row("mentioned", "site_recommending", w)["p_holm"] >= .05 for w in ("equal_model", "equal_developer"))
    out["site: the recommending sentences were close to the ceiling in both places (at least 90%)"] = (
        rates["site_Q1"] >= .9 and rates["site_T1"] >= .9)
    out["site: the third contrast is the first minus the second, negative after Holm with equal model weights only"] = (
        abs(row("mentioned", "site_by_wording")["effect"]
            - (row("mentioned", "site_recommending")["effect"] - row("mentioned", "site_neutral")["effect"])) < 1e-9
        and row("mentioned", "site_by_wording")["effect"] < 0 and row("mentioned", "site_by_wording")["p_holm"] < .05
        and row("mentioned", "site_by_wording", "equal_developer")["p_holm"] >= .05)
    out["site: on the guide the recommending sentence lowered citations of the target page after Holm"] = (
        row("cited", "site_recommending")["effect"] < 0 and row("cited", "site_recommending")["p_holm"] < .05)
    out["site: descriptively, the guide was cited more when it carried the recommending sentence"] = (
        guide["site_T1"] > guide["site_Q1"])
    out["site: the arms repeated from the attribution follow-up came out within one point of it (11 models)"] = (
        len(across["models"]) == 11
        and all(abs(across["site"][a] - across["attribution"][a]) < .01 for a in ("site_B", "site_Q0", "site_Q1")))
    return out
