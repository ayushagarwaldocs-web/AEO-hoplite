"""Checks for the dated existing-data revisions, not independent outcome validation."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from revision_numbers import revision_macros

ROOT = Path(__file__).resolve().parents[1]
E1 = ROOT / "experiments/exp1_web_readiness/results"
E2 = ROOT / "experiments/exp2_content_treatments/results"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def revision_claims() -> dict[str, bool]:
    access = read_json(E1 / "revision_access.json")
    obstacle = access["potential_first_party_access_obstacles"]
    component = obstacle["components"]
    js = access["javascript_measurement"]
    ranks = access["rank_band_retention_and_estimates"]
    summary = read_json(E2 / "revision_summary.json")["datasets"]
    out = {
        "revision: potential-obstacle composite is 199/569, not an access probability":
            obstacle["composite_observed_positive"] == {"k": 199, "n": 569, "pct": 35.0, "lo": 31.2, "hi": 39.0},
        "revision: browser and bot refusals remain distinct; union adds two sites":
            component["browser_edge_refused"]["k"] == 99
            and component["browser_edge_refused"]["n_attempted"] == 532
            and component["bot_user_agent_challenge"]["k"] == 2
            and component["edge_union"]["k"] == 101
            and component["browser_and_bot_refusal_overlap"]["k"] == 0,
        "revision: JS is positive in 30/269 measured sites; 300 unmeasured":
            js["positive"] == 30 and js["measured"] == 269 and js["unmeasured"] == 300,
        "revision: composite classification sensitivity reaches 352/569, not a true access bound":
            obstacle["composite_if_all_unmeasured_js_are_positive"]["k"] == 352
            and obstacle["unmeasured_js_without_another_observed_obstacle"] == 153,
        "revision: rank sample drew 250 per band, retained 703 and excluded 297":
            all(b["drawn"] == 250 and b["drawn"] == b["retained"] + b["excluded"] for b in ranks["bands"])
            and ranks["drawn"] == 1000 and ranks["retained"] == 703 and ranks["excluded"] == 297,
    }
    history = read_json(E2.parent / "analysis_history.json")["original_results"]
    for tag, expected_old in (("bedrock", .0001), ("flagship", .0008)):
        hypotheses = read_json(E2 / f"hypotheses_{tag}.json")
        h5 = hypotheses["H5"]
        out[f"revision {tag}: corrected shared-trial H5 is not significant; original p retained"] = (
            h5["p_perm"] >= .05 and h5["stratified"]["p_perm"] >= .05
            and "shared" in h5["permutation_unit"]
            and round(history[tag]["H5"]["p_perm"], 4) == expected_old)
        out[f"revision {tag}: positive significant H3 effects contradict the prediction"] = all(
            h["verdict"] == "contradicted" and h["effect"] > 0 and h["p"] < .05
            for h in hypotheses["H3"].values())
        absorption = pd.read_csv(E2 / f"absorption_{tag}.csv")
        out[f"revision {tag}: unconditional absorption uses all successful treated answers"] = bool(
            np.allclose(absorption.absorbed, 100 * absorption.n_absorbed / absorption.n, atol=.051)
            and (absorption.absorbed_if_mentioned_n == absorption.n_mentioned).all())
        pooled = absorption[absorption.model == "pooled"].set_index("condition")
        out[f"revision {tag}: unconditional evidence uptake exceeds persuasive uptake"] = bool(
            min(pooled.loc["statistics", "absorbed"], pooled.loc["citations", "absorbed"])
            > pooled.loc["persuasive", "absorbed"] + 20)

    for cohort, detail in summary.items():
        weights = detail["weighted_effects"]
        ranking = detail["ranking"]
        out[f"revision {cohort}: model and developer weighting keep endorsement largest"] = (
            ranking["equal_model_order"][0] == ranking["equal_developer_order"][0] == "third_party"
            and ranking["spearman_rank_correlation"] > .98
            and ranking["leave_one_developer_out_rank_stability"]["third_party"]["rank_max"] == 1)
        out[f"revision {cohort}: absolute probability differences and ceiling headroom agree"] = all(
            np.isclose(v["treated_probability"] - v["baseline_probability"], v["effect"])
            and np.isclose(1 - v["baseline_probability"], v["ceiling_headroom"])
            and v["n_paired"] + v["n_missing_pairs"] == v["n_expected_pairs"]
            for condition in weights.values() for v in condition.values())
        out[f"revision {cohort}: developer counts match explicit mappings"] = (
            detail["n_developers"] == len(set(detail["developer_map"].values())))
    model = pd.read_csv(E2 / "revision_model_effects.csv")
    sonnet = model[(model.group == "anthropic:claude-sonnet-5-5") & (model.condition == "third_party")].iloc[0]
    out["revision: Sonnet 5.5 ceiling headroom is under ten points"] = sonnet.ceiling_headroom < .1
    length = pd.read_csv(E2 / "revision_target_lengths.csv")
    out["revision: length placebo adds a median 32 words, not matched intervention length"] = bool(
        (length[length.condition == "filler"].median_delta_vs_baseline == 32).all())
    agentic = read_json(E2 / "agentic_summary.json")
    queries = agentic["fixed_query_retrieval_exploratory"]["query_trials_by_model"]
    out["revision: fixed-query replay uses 70 MAI trials versus 90 per other model"] = (
        queries["azure:MAI-Thinking-1"] == 70
        and all(n == 90 for m, n in queries.items() if m != "azure:MAI-Thinking-1"))
    replay = pd.read_csv(E2 / "agentic_fixed_query_ranking_effects.csv")
    out["revision: fixed-query replay contains all three ranking methods"] = (
        set(replay.retrieval_method) == {"bm25_only", "embedding_only", "fused"})
    sensitivity = pd.read_csv(E2 / "agentic_sensitivity_excluding_mai.csv")
    mentions = sensitivity[sensitivity.outcome == "mentioned"].set_index("condition")
    out["revision: endorsement, keywords and summary still raise mentions without MAI"] = all(
        mentions.loc[c, "effect"] > 0 and mentions.loc[c, "p_holm"] < .05
        for c in ("third_party", "keyword_stuffing", "answer_first"))

    numbers = (ROOT / "paper/numbers.tex").read_text()
    for name, value in revision_macros().items():
        if isinstance(value, str) and re.fullmatch(r"[\[\]\d\s,.+-]+", value):
            value = re.sub(r"-(0(?:\.0+)?)(?![\d.])", r"\1", value).replace("-", r"\ensuremath{-}")
        out[f"revision macro {name}: matches generated source"] = f"\\newcommand{{\\{name}}}{{{value}}}" in numbers
    return out
