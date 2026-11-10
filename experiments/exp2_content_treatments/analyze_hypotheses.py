"""Verdicts for the pre-specified hypotheses H1-H5, model profiles and cross-model consistency.

    python analyze_hypotheses.py

Reads data/responses.jsonl and the effect tables written by analyze.py, and writes
results/hypotheses.json. Uses the same paired differences, cluster bootstrap and
sign-flip tests as analyze.py.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from analyze import RNG, cluster_boot, sign_flip_p  # noqa: E402

RES = HERE / "results"
EVIDENCE = ["statistics", "citations", "quotation"]
SINGLE_ON_PAGE = ["statistics", "citations", "quotation", "answer_first", "qa_format", "spec_table", "limitations",
                  "freshness", "persuasive", "keyword_stuffing"]
ALPHA = 0.05


def pooled_contrast(df: pd.DataFrame, a: str, b: str, outcome: str = "mentioned") -> dict:
    """Paired difference a - b within trial, averaged over models with equal weight."""
    wide = df.pivot_table(index=["model", "scenario", "trial_id"], columns="condition", values=outcome).astype(float)
    d = (wide[a] - wide[b]).rename("diff").reset_index()
    d = d.groupby(["scenario", "trial_id"], as_index=False)["diff"].mean()
    lo, hi = cluster_boot(d)
    return {"effect": float(d["diff"].mean()), "ci_low": lo, "ci_high": hi, "p": sign_flip_p(d)}


def ci90(df: pd.DataFrame, cond: str, outcome: str = "mentioned", n_boot: int = 4000) -> tuple[float, float]:
    wide = df.pivot_table(index=["model", "scenario", "trial_id"], columns="condition", values=outcome).astype(float)
    d = (wide[cond] - wide["baseline"]).rename("diff").reset_index()
    d = d.groupby(["scenario", "trial_id"], as_index=False)["diff"].mean()
    by_s = d.groupby("scenario")["diff"].agg(["sum", "count"])
    sums, counts = by_s["sum"].to_numpy(), by_s["count"].to_numpy()
    idx = RNG.integers(0, len(sums), size=(n_boot, len(sums)))
    means = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    return float(np.percentile(means, 5)), float(np.percentile(means, 95))


def _chi2(pos: np.ndarray, y: np.ndarray) -> float:
    tab = pd.crosstab(pos, y).to_numpy().astype(float)
    exp = tab.sum(1, keepdims=True) * tab.sum(0, keepdims=True) / tab.sum()
    return float(((tab - exp) ** 2 / exp).sum())


def _chi2_batch(pos: np.ndarray, y: np.ndarray, groups: np.ndarray | None = None,
                n_groups: int = 1) -> np.ndarray:
    """Vectorised chi-square statistics, optionally stratified by a row group."""
    n_perm, _ = pos.shape
    if groups is None:
        groups = np.zeros(len(y), dtype=np.int64)
    bins = groups[None, :] * 12 + (pos - 1) * 2 + y[None, :]
    offsets = np.arange(n_perm, dtype=np.int64)[:, None] * (n_groups * 12)
    counts = np.bincount((bins + offsets).ravel(), minlength=n_perm * n_groups * 12)
    counts = counts.reshape(n_perm, n_groups, 6, 2)
    totals = counts.sum(axis=(2, 3), keepdims=True)
    expected = counts.sum(axis=3, keepdims=True) * counts.sum(axis=2, keepdims=True) / np.maximum(totals, 1)
    stats = np.divide((counts - expected) ** 2, expected, out=np.zeros_like(expected), where=expected > 0).sum((2, 3))
    return stats[:, 0] if n_groups == 1 else stats


def h3_verdict(effect: float, p_adjusted: float, alpha: float = ALPHA) -> str:
    """H3 predicts no increase: a positive significant estimate contradicts it; otherwise inconclusive."""
    if effect > 0 and p_adjusted < alpha:
        return "contradicted"
    return "inconclusive"


def position_test(df: pd.DataFrame, n_perm: int = 10_000,
                  rng: np.random.Generator | None = None) -> dict:
    """Test target-position association with shared scenario/trial assignments.

    The original independent-model results are pinned in analysis_history.json; reruns report only the corrected test.
    """
    rng = rng or RNG
    base = df[df["condition"] == "baseline"][["model", "scenario", "trial_id", "target_index", "mentioned"]].copy()
    base["mentioned"] = base["mentioned"].astype(int)
    models = sorted(base["model"].unique())
    trial_cols = ["scenario", "trial_id"]
    trials = base[trial_cols + ["target_index"]].drop_duplicates()
    if trials.duplicated(trial_cols).any():
        raise ValueError("target_index must be shared across models for each scenario/trial")
    trials = trials.reset_index(drop=True)
    trial_index = pd.MultiIndex.from_frame(trials[trial_cols])
    row_codes = trial_index.get_indexer(pd.MultiIndex.from_frame(base[trial_cols]))
    trial_pos = trials["target_index"].to_numpy(dtype=int)
    scenario_values = trials["scenario"].to_numpy()
    scenario_trial_codes = [np.flatnonzero(scenario_values == s) for s in pd.unique(scenario_values)]
    y, row_models = base["mentioned"].to_numpy(dtype=int), base["model"].to_numpy()
    model_codes = {m: np.flatnonzero(row_models == m) for m in models}
    row_model_codes = np.array([models.index(m) for m in row_models], dtype=np.int64)
    obs_pooled = _chi2(base["target_index"].to_numpy(), y)
    obs_model = {m: _chi2(base.iloc[ix]["target_index"].to_numpy(), y[ix]) for m, ix in model_codes.items()}
    null_pooled, null_model = [], {m: [] for m in models}
    for start in range(0, n_perm, 256):
        size = min(256, n_perm - start)
        perm_trials = np.tile(trial_pos, (size, 1))
        for ix in scenario_trial_codes:
            order = rng.random((size, len(ix))).argsort(axis=1)
            perm_trials[:, ix] = trial_pos[ix][order]
        perm_rows = perm_trials[:, row_codes]
        null_pooled.extend(_chi2_batch(perm_rows, y).tolist())
        model_stats = _chi2_batch(perm_rows, y, row_model_codes, len(models))
        for model_index, model in enumerate(models):
            null_model[model].extend(model_stats[:, model_index].tolist())
    p = lambda null, obs: float((1 + np.sum(np.asarray(null) >= obs - 1e-12)) / (n_perm + 1))  # noqa: E731
    strat_null = np.sum([null_model[m] for m in models], axis=0)
    strat_obs = sum(obs_model.values())
    rates = base.groupby("target_index")["mentioned"].mean().mul(100).round(1).to_dict()
    groups = {m: base.iloc[ix] for m, ix in model_codes.items()}
    by_model = {m: {"chi2": round(obs_model[m], 1), "p_perm": p(null_model[m], obs_model[m]),
                    "rates_by_slot": {int(k): v for k, v in
                                      g.groupby("target_index")["mentioned"].mean().mul(100).round(1).items()}}
                for m, g in groups.items()}
    corrected = {"chi2": round(obs_pooled, 1), "p_perm": p(null_pooled, obs_pooled),
                 "rates_by_slot": {int(k): v for k, v in rates.items()},
                 "stratified": {"chi2": round(strat_obs, 1), "p_perm": p(strat_null, strat_obs)},
                 "by_model": by_model,
                 "permutation_unit": "scenario/trial; each assignment shared across models"}
    return corrected


def position_interaction(df: pd.DataFrame, conds: tuple[str, ...] = ("statistics", "citations"),
                         n_boot: int = 4000) -> dict:
    """Exploratory: the evidence edits' effect on mentions by the target's slot, early (1-2) versus late (5-6).

    Pooled over models with equal weight within trial, as for the main effects, and per model; intervals resample
    scenarios."""
    wide = df.pivot_table(index=["model", "scenario", "trial_id", "target_index"], columns="condition",
                          values="mentioned").astype(float).reset_index()
    wide["evidence"] = wide[list(conds)].mean(axis=1)
    wide["diff"] = wide["evidence"] - wide["baseline"]
    groups = {"early": (1, 2), "middle": (3, 4), "late": (5, 6)}
    scen = sorted(wide["scenario"].unique())
    idx = RNG.integers(0, len(scen), size=(n_boot, len(scen)))

    def summarise(d: pd.DataFrame) -> dict:
        out, boot = {}, {}
        for name, (lo, hi) in groups.items():
            g = d[d["target_index"].between(lo, hi)]
            by = g.groupby("scenario")["diff"].agg(["sum", "count"]).reindex(scen, fill_value=0)
            boot[name] = by["sum"].to_numpy()[idx].sum(1) / np.maximum(by["count"].to_numpy()[idx].sum(1), 1)
            out[name] = {"slots": [lo, hi], "n_trials": int(len(g)), "effect": float(g["diff"].mean()),
                         "ci": [float(np.percentile(boot[name], 2.5)), float(np.percentile(boot[name], 97.5))],
                         "baseline": float(g["baseline"].mean()), "treated": float(g["evidence"].mean()),
                         "placebo": float(g["filler"].mean())}
        gap = boot["late"] - boot["early"]
        out["late_minus_early"] = {"effect": out["late"]["effect"] - out["early"]["effect"],
                                   "ci": [float(np.percentile(gap, 2.5)), float(np.percentile(gap, 97.5))]}
        return out

    pooled = wide.groupby(["scenario", "trial_id", "target_index"], as_index=False)[
        ["diff", "baseline", "evidence", "filler"]].mean()
    result = summarise(pooled)
    result["by_model"] = {m: summarise(g) for m, g in wide.groupby("model")}
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(HERE / "data" / "responses.jsonl"))
    ap.add_argument("--tag", default="", help="read and write the tagged files of analyze.py --tag")
    args = ap.parse_args()
    suffix = f"_{args.tag}" if args.tag else ""
    df = pd.read_json(args.input, lines=True)
    df = df[df["error"].isna()]
    eff = pd.read_csv(RES / f"effects{suffix}.csv")
    plc = pd.read_csv(RES / f"effects_vs_placebo{suffix}.csv")
    pick = lambda frame, cond, outcome="mentioned", model="pooled": frame[  # noqa: E731
        (frame["condition"] == cond) & (frame["outcome"] == outcome) & (frame["model"] == model)].iloc[0]
    out: dict = {}

    h1 = {}
    for c in EVIDENCE:
        vb, vp = pick(eff, c), pick(plc, c)
        h1[c] = {"vs_baseline": float(vb["effect"]), "p_baseline": float(vb["p_holm"]),
                 "vs_placebo": float(vp["effect"]), "p_placebo": float(vp["p_holm"]),
                 "supported": bool(vb["effect"] > 0 and vb["p_holm"] < ALPHA and vp["effect"] > 0
                                   and vp["p_holm"] < ALPHA)}
    out["H1"] = h1

    single = {c: float(pick(eff, c)["effect"]) for c in SINGLE_ON_PAGE}
    best = max(single, key=single.get)
    contrast = pooled_contrast(df, "third_party", best)
    out["H2"] = {"third_party": float(pick(eff, "third_party")["effect"]), "best_single": best,
                 "best_single_effect": single[best], "difference": contrast,
                 "supported": bool(contrast["ci_low"] > 0)}

    out["H3"] = {}
    for c in ["keyword_stuffing", "persuasive"]:
        row = pick(eff, c)
        effect, p_adj = float(row["effect"]), float(row["p_holm"])
        verdict = h3_verdict(effect, p_adj)
        out["H3"][c] = {"effect": effect, "ci": [float(row["ci_low"]), float(row["ci_high"])],
                         "p": p_adj, "verdict": verdict, "supported": verdict == "supported"}

    out["H4"] = {}
    for c in ["freshness", "answer_first"]:
        lo, hi = ci90(df, c)
        out["H4"][c] = {"effect": float(pick(eff, c)["effect"]), "ci90": [lo, hi],
                        "supported": bool(lo > -0.05 and hi < 0.05)}

    out["H5"] = position_test(df)

    # Model profiles at baseline
    base = df[df["condition"] == "baseline"].copy()
    base["words"] = base["text"].str.split().str.len()
    out["profiles"] = {m: {"n_responses": int((df["model"] == m).sum()),
                           "mention": round(100 * g["mentioned"].mean(), 1),
                           "top_pick": round(100 * g["top_pick"].mean(), 1),
                           "cited": round(100 * g["cited"].mean(), 1),
                           "any_citation": round(100 * (g["n_citations"] > 0).mean(), 1),
                           "median_words": float(g["words"].median()),
                           "median_brands": float(g["n_brands_mentioned"].median())}
                       for m, g in base.groupby("model")}

    # Do treatments rank the same way across models?
    corr = {}
    for outcome in ["mentioned", "top_pick"]:
        e = eff[(eff["outcome"] == outcome) & (eff["model"] != "pooled")].pivot(
            index="condition", columns="model", values="effect")
        for a, b in itertools.combinations(e.columns, 2):
            rho, p = spearmanr(e[a], e[b])
            corr[f"{outcome}: {a} vs {b}"] = {"rho": round(float(rho), 2), "p": float(p)}
    out["cross_model_spearman"] = corr

    # Zero-sum or additive? Effects on how many brands are named, and on the target's share of them
    out["competition"] = {}
    for c in ["statistics", "citations", "quotation", "third_party", "combined", "injection", "persuasive"]:
        out["competition"][c] = {"n_brands": pooled_contrast(df, c, "baseline", "n_brands_mentioned"),
                                 "mention_share": pooled_contrast(df, c, "baseline", "mention_share")}

    # Exploratory: do the evidence edits offset a poor position?
    out["position_interaction"] = position_interaction(df)

    # How many treatment effects are significant, per model and outcome
    out["n_significant"] = (eff[eff["p_holm"] < ALPHA].groupby(["model", "outcome"]).size()
                            .rename("n").reset_index().to_dict(orient="records"))
    (RES / f"hypotheses{suffix}.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=1)[:5000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
