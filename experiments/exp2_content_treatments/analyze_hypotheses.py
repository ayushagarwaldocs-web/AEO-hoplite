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


def position_test(df: pd.DataFrame, n_perm: int = 10_000) -> dict:
    """Does the target's slot (1-6) change baseline mention rates?

    Pooled: one chi-square over all models, permuting slots within model. Because models can favour opposite ends of
    the list, also per model, and stratified (the sum of the per-model statistics, permuted within model)."""
    base = df[df["condition"] == "baseline"][["model", "target_index", "mentioned"]].copy()
    base["mentioned"] = base["mentioned"].astype(int)
    models = sorted(base["model"].unique())
    groups = {m: base[base["model"] == m] for m in models}
    obs_pooled = _chi2(base["target_index"].to_numpy(), base["mentioned"].to_numpy())
    obs_model = {m: _chi2(g["target_index"].to_numpy(), g["mentioned"].to_numpy()) for m, g in groups.items()}
    null_pooled, null_model = [], {m: [] for m in models}
    for _ in range(n_perm):
        perm = base.groupby("model")["target_index"].transform(lambda s: RNG.permutation(s.to_numpy()))
        null_pooled.append(_chi2(perm.to_numpy(), base["mentioned"].to_numpy()))
        for m, g in groups.items():
            null_model[m].append(_chi2(perm.loc[g.index].to_numpy(), g["mentioned"].to_numpy()))
    p = lambda null, obs: float((1 + np.sum(np.array(null) >= obs - 1e-12)) / (n_perm + 1))  # noqa: E731
    strat_null = np.sum([null_model[m] for m in models], axis=0)
    strat_obs = sum(obs_model.values())
    rates = base.groupby("target_index")["mentioned"].mean().mul(100).round(1).to_dict()
    by_model = {m: {"chi2": round(obs_model[m], 1), "p_perm": p(null_model[m], obs_model[m]),
                    "rates_by_slot": {int(k): v for k, v in
                                      g.groupby("target_index")["mentioned"].mean().mul(100).round(1).items()}}
                for m, g in groups.items()}
    return {"chi2": round(obs_pooled, 1), "p_perm": p(null_pooled, obs_pooled),
            "rates_by_slot": {int(k): v for k, v in rates.items()},
            "stratified": {"chi2": round(strat_obs, 1), "p_perm": p(strat_null, strat_obs)},
            "by_model": by_model}


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

    out["H3"] = {c: {"effect": float(pick(eff, c)["effect"]), "ci": [float(pick(eff, c)["ci_low"]),
                                                                      float(pick(eff, c)["ci_high"])],
                     "p": float(pick(eff, c)["p_holm"]),
                     "supported": not (pick(eff, c)["effect"] > 0 and pick(eff, c)["p_holm"] < ALPHA)}
                 for c in ["keyword_stuffing", "persuasive"]}

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
