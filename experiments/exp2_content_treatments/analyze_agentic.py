"""Analyse the agentic search experiment (specified in README.md, "Agentic search").

    python3 analyze_agentic.py

Reads data/agentic_<model>.jsonl (never the pilot files) and keeps each model's complete trials (all seven conditions
answered without error). Pre-specified analyses:
  1-2  effects of each treatment against baseline on mentioned, top pick, cited, surfaced and opened, per model and
       pooled (equal weight per model; models with fewer than 60 complete trials are descriptive only)
  3    agentic minus in-context effect for the same models and trials (in-context answers from the main runs)
  4    retrieval with queries held fixed: every query issued in a baseline episode, rerun against each condition's
       pool (cached vectors only); the target's top-five rate for BM25, embedding, and fused ranking
Exploratory: ranker contrasts, answers citing URLs that no search returned, descriptive mention rates by page opening,
MAI-excluded sensitivity results, and keyword stuffing against endorsement within trials.

Writes results/agentic_effects.csv, agentic_vs_context.csv, agentic_fixed_queries.csv, agentic_summary.json and
paper/figures/fig13_agentic.(pdf|png).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import analyze as A  # noqa: E402
from search_pool import CacheOnlyEmbedder, CONDITIONS, Engine, doc_text, episodes, norm_url  # noqa: E402
from aeotools import plotstyle as ps  # noqa: E402

DATA, RES, FIG = HERE / "data", HERE / "results", ROOT / "paper" / "figures"
MODELS = ["openai:gpt-6.1-sol", "azure:gpt-5-mini", "azure:MAI-Thinking-1", "azure:DeepSeek-V4-Pro"]
CONTEXT = {"openai:gpt-6.1-sol": "responses_openai_gpt-6.1-sol.jsonl",
           "azure:gpt-5-mini": "responses_azure_gpt-5-mini.jsonl",
           "azure:MAI-Thinking-1": "responses_azure_mai-thinking-1.jsonl",
           "azure:DeepSeek-V4-Pro": "responses_azure_deepseek-v4-pro.jsonl"}
OUTCOMES = ["mentioned", "top_pick", "cited", "surfaced", "opened"]
TREAT = CONDITIONS[1:]
MIN_TRIALS = 60
_URL = re.compile(r"https?://[^\s\]\)\[<>\"']+")


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(all rows, successful rows of complete trials)."""
    frames = [pd.read_json(f, lines=True) for f in sorted(DATA.glob("agentic_*.jsonl"))
              if "pilot" not in f.name and "embeddings" not in f.name]
    raw = pd.concat(frames, ignore_index=True)
    raw = raw[raw["model"].isin(MODELS)]
    ok = raw[raw["error"].isna()].drop_duplicates(["model", "trial_id", "condition"], keep="last").copy()
    n = ok.groupby(["model", "trial_id"])["condition"].nunique()
    complete = n[n == len(CONDITIONS)].reset_index()[["model", "trial_id"]]
    ok = ok.merge(complete, on=["model", "trial_id"])
    for c in OUTCOMES + ["no_search", "no_brand", "forced", "guide_opened", "guide_surfaced"]:
        ok[c] = ok[c].astype(float)
    return raw, ok


def model_effects(df: pd.DataFrame, outcomes: list[str], pooled_models: list[str]) -> pd.DataFrame:
    """Paired effects against baseline, per model and pooled over pooled_models, with the main design's tests."""
    rows = []
    for oc in outcomes:
        d_all = A.paired(df, oc)
        if d_all.empty:
            continue
        for model in sorted(d_all["model"].unique()) + ["pooled"]:
            d_m = d_all[d_all["model"].isin(pooled_models)] if model == "pooled" else d_all[d_all["model"] == model]
            block = []
            for cond in TREAT:
                d = d_m[d_m["condition"] == cond]
                if d.empty:
                    continue
                if model == "pooled":
                    d = d.groupby(["scenario", "trial_id"], as_index=False)["diff"].mean()
                lo, hi = A.cluster_boot(d)
                block.append({"outcome": oc, "model": model, "condition": cond, "n": len(d),
                              "effect": float(d["diff"].mean()), "ci_low": lo, "ci_high": hi, "p": A.sign_flip_p(d)})
            for row, p_adj in zip(block, A.holm([b["p"] for b in block])):
                row["p_holm"] = p_adj
            rows.extend(block)
    return pd.DataFrame(rows)


def context_frame(ok: pd.DataFrame) -> pd.DataFrame:
    """In-context answers of the same models, restricted to the agentic run's complete trials and conditions."""
    frames = []
    for m in sorted(ok["model"].unique()):
        d = pd.read_json(DATA / CONTEXT[m], lines=True)
        d = d[d["error"].isna() & d["condition"].isin(CONDITIONS)]
        d = d[d["trial_id"].isin(set(ok.loc[ok["model"] == m, "trial_id"]))]
        frames.append(d.assign(model=m))
    ctx = pd.concat(frames, ignore_index=True)
    for c in ("mentioned", "top_pick"):
        ctx[c] = ctx[c].astype(float)
    return ctx


def versus_context(ok: pd.DataFrame, ctx: pd.DataFrame, pooled_models: list[str]) -> pd.DataFrame:
    rows = []
    for oc in ("mentioned", "top_pick"):
        ag = A.paired(ok, oc).rename(columns={"diff": "ag"})
        cx = A.paired(ctx, oc).rename(columns={"diff": "cx"})
        m = ag.merge(cx, on=["model", "scenario", "trial_id", "condition"])
        m["diff"] = m["ag"] - m["cx"]
        for model in sorted(m["model"].unique()) + ["pooled"]:
            d_m = m[m["model"].isin(pooled_models)] if model == "pooled" else m[m["model"] == model]
            for cond in TREAT:
                d = d_m[d_m["condition"] == cond]
                if d.empty:
                    continue
                if model == "pooled":
                    d = d.groupby(["scenario", "trial_id"], as_index=False)[["diff", "ag", "cx"]].mean()
                lo, hi = A.cluster_boot(d)
                rows.append({"outcome": oc, "model": model, "condition": cond, "n": len(d),
                             "agentic": float(d["ag"].mean()), "in_context": float(d["cx"].mean()),
                             "difference": float(d["diff"].mean()), "ci_low": lo, "ci_high": hi,
                             "p": A.sign_flip_p(d)})
    return pd.DataFrame(rows)


def equal_model_mean(d: pd.DataFrame, value: str) -> float:
    """Average each model's trial-level mean with equal model weights."""
    return float(d.groupby("model")[value].mean().mean())


def equal_model_cluster_boot(d: pd.DataFrame, value: str = "diff", n_boot: int = 4000) -> tuple[float, float]:
    """Cluster bootstrap for an estimand that averages model-specific means equally."""
    by = d.groupby(["model", "scenario"])[value].agg(["sum", "count"])
    models = sorted(d["model"].unique())
    scenarios = sorted(d["scenario"].unique())
    sums = by["sum"].unstack("scenario").reindex(index=models, columns=scenarios).fillna(0).to_numpy()
    counts = by["count"].unstack("scenario").reindex(index=models, columns=scenarios).fillna(0).to_numpy()
    if np.any(counts.sum(axis=1) == 0):
        raise ValueError("Each included model must contribute at least one observation")
    estimates = []
    attempts = 0
    while len(estimates) < n_boot:
        attempts += 1
        if attempts > 100:
            raise RuntimeError("Could not draw valid scenario-cluster bootstrap replicates")
        batch = max(2 * (n_boot - len(estimates)), 100)
        indices = A.RNG.integers(0, len(scenarios), size=(batch, len(scenarios)))
        sample_sums = sums[:, indices].sum(axis=2)
        sample_counts = counts[:, indices].sum(axis=2)
        valid = np.all(sample_counts > 0, axis=0)
        if valid.any():
            estimates.extend(np.mean(sample_sums[:, valid] / sample_counts[:, valid], axis=0).tolist())
    means = np.asarray(estimates[:n_boot])
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def equal_model_sign_flip_p(d: pd.DataFrame, value: str = "diff", n_perm: int = 10000) -> float:
    """Scenario-level sign-flip test for the equal-model mean, preserving shared clusters."""
    by = d.groupby(["model", "scenario"])[value].agg(["sum", "count"])
    models = sorted(d["model"].unique())
    scenarios = sorted(d["scenario"].unique())
    sums = by["sum"].unstack("scenario").reindex(index=models, columns=scenarios).fillna(0).to_numpy()
    counts = by["count"].unstack("scenario").reindex(index=models, columns=scenarios).fillna(0).to_numpy()
    denominators = counts.sum(axis=1)
    if np.any(denominators == 0):
        raise ValueError("Each included model must contribute at least one observation")
    observed = float(np.mean(sums.sum(axis=1) / denominators))
    signs = A.RNG.choice([-1.0, 1.0], size=(n_perm, len(scenarios)))
    null = np.mean((sums @ signs.T) / denominators[:, None], axis=0)
    return float((np.sum(np.abs(null) >= abs(observed) - 1e-12) + 1) / (n_perm + 1))


def fixed_query_effects(fq: pd.DataFrame, pooled_models: list[str]) -> pd.DataFrame:
    """Fixed-query retrieval effects, with equal weight per model and scenario-clustered inference."""
    methods = fq["retrieval_method"].drop_duplicates().tolist() if "retrieval_method" in fq else ["fused"]
    rows = []
    for method in methods:
        data = fq[fq["retrieval_method"] == method] if "retrieval_method" in fq else fq
        paired = A.paired(data, "top5")
        available = [m for m in pooled_models if m in set(paired["model"])]
        for model in sorted(paired["model"].unique()) + ["pooled"]:
            block = []
            for cond in TREAT:
                d = paired[paired["condition"] == cond]
                if model == "pooled":
                    d = d[d["model"].isin(available)]
                    if d.empty:
                        continue
                    effect = equal_model_mean(d, "diff")
                    lo, hi = equal_model_cluster_boot(d)
                    p = equal_model_sign_flip_p(d)
                    n_models = int(d["model"].nunique())
                    n_model_trials = int(len(d))
                else:
                    d = d[d["model"] == model]
                    if d.empty:
                        continue
                    lo, hi = A.cluster_boot(d)
                    effect = float(d["diff"].mean())
                    p = A.sign_flip_p(d)
                    n_models, n_model_trials = 1, int(len(d))
                block.append({"outcome": "top5", "model": model, "condition": cond,
                              "n": int(d[["scenario", "trial_id"]].drop_duplicates().shape[0]),
                              "n_model_trials": n_model_trials, "n_models": n_models,
                              "effect": effect, "ci_low": lo, "ci_high": hi, "p": p,
                              "retrieval_method": method})
            for row, p_adj in zip(block, A.holm([b["p"] for b in block])):
                row["p_holm"] = p_adj
            rows.extend(block)
    return pd.DataFrame(rows)


def fixed_queries(ok: pd.DataFrame, pooled_models: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame,
                                                                          pd.DataFrame, list[str], dict[str, int]]:
    """Replay baseline-issued queries against each pool and ranker using cached vectors only."""
    eps, pool = episodes()
    by_key = {(e["trial_id"], e["condition"]): e for e in eps}
    base = ok[ok["condition"] == "baseline"]
    queries_by_trial = {}
    for trial_id, group in base.groupby("trial_id"):
        for _, r in group.iterrows():
            queries = [s["query"] for s in r["steps"] if s["tool"] == "search" and s.get("query")]
            if queries:
                queries_by_trial.setdefault(trial_id, []).append((r, queries))

    emb = CacheOnlyEmbedder()
    page_texts = [doc_text(p) for p in pool.values()]
    page_texts += [doc_text(p) for e in eps for p in e["override"].values()]
    query_texts = [q for records in queries_by_trial.values() for _, qs in records for q in qs]
    emb.get_cached(list(dict.fromkeys(page_texts + query_texts)))

    rows = []
    for trial_id, records in queries_by_trial.items():
        engines = {c: Engine(pool, by_key[(trial_id, c)]["override"], emb) for c in CONDITIONS}
        target = by_key[(trial_id, "baseline")]["target_url"]
        for r, queries in records:
            for cond, eng in engines.items():
                hits = {method: [] for method in ("bm25_only", "embedding_only", "fused")}
                for query in queries:
                    for method, ranking in eng.rankings(query).items():
                        hits[method].append(target in ranking[:5])
                for method, values in hits.items():
                    rows.append({"model": r["model"], "scenario": r["scenario"], "trial_id": trial_id,
                                 "condition": cond, "retrieval_method": method,
                                 "top5": float(np.mean(values)), "n_queries": len(queries)})
    all_fq = pd.DataFrame(rows)
    query_trial_counts = (all_fq[(all_fq["condition"] == "baseline") & (all_fq["retrieval_method"] == "fused")]
                          .groupby("model")["trial_id"].nunique().astype(int).to_dict())
    query_models = [m for m in pooled_models if query_trial_counts.get(m, 0) >= MIN_TRIALS]
    all_effects = fixed_query_effects(all_fq, query_models)
    legacy_fq = all_fq[all_fq["retrieval_method"] == "fused"].drop(columns="retrieval_method").reset_index(drop=True)
    legacy_effects = all_effects[all_effects["retrieval_method"] == "fused"].drop(
        columns="retrieval_method").reset_index(drop=True)
    legacy_effects = legacy_effects[["outcome", "model", "condition", "n", "effect", "ci_low", "ci_high", "p", "p_holm"]]
    return legacy_fq, legacy_effects, all_fq, all_effects, query_models, query_trial_counts


def absolute_rate_table(ok: pd.DataFrame, pooled_models: list[str]) -> pd.DataFrame:
    """Absolute episode-level outcome probabilities, with an equal-model pooled estimate."""
    data = ok.copy()
    data["search_compliant"] = 1 - data["no_search"]
    data["snippet_exposed"] = data["surfaced"]
    measures = {"mentioned": "mentioned", "first_mentioned_brand": "top_pick", "cited": "cited",
                "search_compliant": "search_compliant", "snippet_exposed": "snippet_exposed",
                "target_page_opened": "opened"}
    rows = []
    for measure, column in measures.items():
        for cond in CONDITIONS:
            block = []
            for model in sorted(data.loc[data["model"].isin(pooled_models), "model"].unique()):
                d = data[(data["model"] == model) & (data["condition"] == cond)]
                if d.empty:
                    continue
                values = d[["scenario", "trial_id", column]].rename(columns={column: "diff"})
                lo, hi = A.cluster_boot(values)
                block.append({"measure": measure, "model": model, "condition": cond, "n": len(d),
                              "n_trial_clusters": int(d[["scenario", "trial_id"]].drop_duplicates().shape[0]),
                              "n_models": 1, "rate": float(d[column].mean()), "ci_low": lo, "ci_high": hi})
            d = data[data["model"].isin(pooled_models) & (data["condition"] == cond)]
            if not d.empty:
                lo, hi = equal_model_cluster_boot(d, value=column)
                per_model = d.groupby("model")[column].mean()
                block.append({"measure": measure, "model": "pooled", "condition": cond, "n": len(d),
                              "n_trial_clusters": int(d[["scenario", "trial_id"]].drop_duplicates().shape[0]),
                              "n_models": int(per_model.size), "rate": equal_model_mean(d, column),
                              "ci_low": lo, "ci_high": hi})
            rows.extend(block)
    return pd.DataFrame(rows)


def opened_association_table(ok: pd.DataFrame, pooled_models: list[str]) -> pd.DataFrame:
    """Descriptive mention rates conditional on target opening; not a mediation analysis."""
    rows = []
    for cond in CONDITIONS:
        for opened in (0, 1):
            block = []
            for model in sorted(set(pooled_models) & set(ok["model"])):
                d = ok[(ok["model"] == model) & (ok["condition"] == cond) & (ok["opened"] == opened)]
                if d.empty:
                    continue
                block.append({"model": model, "n": len(d),
                              "n_trial_clusters": int(d[["scenario", "trial_id"]].drop_duplicates().shape[0]),
                              "rate": float(d["mentioned"].mean())})
            if block:
                d = ok[ok["model"].isin([row["model"] for row in block]) & (ok["condition"] == cond)
                       & (ok["opened"] == opened)]
                rows.extend({"condition": cond, "opened": opened, "n_models": 1,
                             "interpretation": "Descriptive conditional association; opening is post-treatment, not a mediation estimate.", **row}
                            for row in block)
                rows.append({"condition": cond, "opened": opened, "interpretation": "Descriptive conditional association; opening is post-treatment, not a mediation estimate.",
                             "model": "pooled", "n": len(d),
                             "n_trial_clusters": int(d[["scenario", "trial_id"]].drop_duplicates().shape[0]),
                             "n_models": len(block), "rate": equal_model_mean(d, "mentioned")})
    return pd.DataFrame(rows)


def fabricated(ok: pd.DataFrame) -> pd.Series:
    """Answers citing a URL that none of the episode's searches returned and the model did not open."""
    out = []
    for _, r in ok.iterrows():
        seen = {u for s in r["steps"] if s["tool"] == "search" for u in s["results"]}
        seen |= {s["page"] for s in r["steps"] if s["tool"] == "open_page" and s.get("page")}
        cited = {norm_url(u.rstrip(".,;")) for u in _URL.findall(r["text"] or "")}
        out.append(any(c not in seen for c in cited))
    return pd.Series(out, index=ok.index, dtype=float)


def fig_agentic(eff: pd.DataFrame, vs: pd.DataFrame, stem: Path) -> None:
    ps.apply()
    fig, axes = ps.plt.subplots(1, 2, figsize=(7.4, 3.3), sharey=True)
    order = (vs[(vs["model"] == "pooled") & (vs["outcome"] == "mentioned")]
             .set_index("condition")["in_context"].sort_values().index.tolist())
    ys = np.arange(len(order))
    p = eff[eff["model"] == "pooled"]
    ctx_eff = vs[(vs["model"] == "pooled") & (vs["outcome"] == "mentioned")].set_index("condition").reindex(order)
    ax = axes[0]
    ag = p[p["outcome"] == "mentioned"].set_index("condition").reindex(order)
    ax.plot(ctx_eff["in_context"] * 100, ys - 0.13, "o", ms=4.6, color="#9a9890", mec=ps.SURFACE, mew=0.7,
            label="Pages given (main design)")
    ax.hlines(ys + 0.13, ag["ci_low"] * 100, ag["ci_high"] * 100, color=ps.INK, lw=1.1)
    ax.plot(ag["effect"] * 100, ys + 0.13, "o", ms=4.6, color=ps.INK, mec=ps.SURFACE, mew=0.7,
            label="Model searches (agentic)")
    ax.set_title("Mentions", fontsize=9)
    ax.set_xlabel("Change from baseline (points)", fontsize=8)
    ax = axes[1]
    for oc, color, dy, name in (("surfaced", ps.SERIES[0], -0.13, "Target surfaced with snippet"),
                                ("opened", ps.SERIES[1], 0.13, "Target page opened")):
        v = p[p["outcome"] == oc].set_index("condition").reindex(order)
        ax.hlines(ys + dy, v["ci_low"] * 100, v["ci_high"] * 100, color=color, lw=1.1)
        ax.plot(v["effect"] * 100, ys + dy, "o", ms=4.6, color=color, mec=ps.SURFACE, mew=0.7, label=name)
    ax.set_title("Retrieval (agentic)", fontsize=9)
    ax.set_xlabel("Change from baseline (points)", fontsize=8)
    for ax in axes:
        ax.axvline(0, color=ps.INK2, lw=0.9, zorder=0)
        ax.set_yticks(ys, [A.LABELS.get(c, c) for c in order], fontsize=7.5)
        ax.tick_params(axis="y", length=0)
        ax.tick_params(axis="x", labelsize=7.5)
        ax.xaxis.grid(True)
        ax.set_axisbelow(True)
        ax.set_ylim(-0.6, len(order) - 0.4)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=6.8, frameon=False,
                  handletextpad=0.3, columnspacing=1.2)
    fig.subplots_adjust(wspace=0.08)
    ps.save(fig, stem)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-trials", type=int, default=MIN_TRIALS, help="pre-specified: 60; lower only for test runs")
    args = ap.parse_args()
    raw, ok = load()
    trials = ok.groupby("model")["trial_id"].nunique()
    pooled_models = [m for m in MODELS if trials.get(m, 0) >= args.min_trials]
    ok["fabricated"] = fabricated(ok)
    eff = model_effects(ok, OUTCOMES, pooled_models)
    ctx = context_frame(ok)
    vs = versus_context(ok, ctx, pooled_models)
    fq, fq_eff, fq_all, fq_all_eff, query_models, query_trial_counts = fixed_queries(ok, pooled_models)
    without_mai = [m for m in pooled_models if m != "azure:MAI-Thinking-1"]
    sensitivity = model_effects(ok, OUTCOMES, without_mai)
    sensitivity = sensitivity[sensitivity["model"] == "pooled"].copy()
    sensitivity["model"] = "pooled_excluding_mai"
    sensitivity["included_models"] = ";".join(without_mai)
    absolute_rates = absolute_rate_table(ok, pooled_models)
    open_associations = opened_association_table(ok, pooled_models)
    RES.mkdir(exist_ok=True)
    eff.to_csv(RES / "agentic_effects.csv", index=False)
    vs.to_csv(RES / "agentic_vs_context.csv", index=False)
    fq.to_csv(RES / "agentic_fixed_queries_rows.csv", index=False)
    fq_eff.to_csv(RES / "agentic_fixed_queries.csv", index=False)
    fq_all.to_csv(RES / "agentic_fixed_query_rankings.csv", index=False)
    fq_all_eff.to_csv(RES / "agentic_fixed_query_ranking_effects.csv", index=False)
    absolute_rates.to_csv(RES / "agentic_absolute_rates.csv", index=False)
    open_associations.to_csv(RES / "agentic_open_associations.csv", index=False)
    sensitivity.to_csv(RES / "agentic_sensitivity_excluding_mai.csv", index=False)

    base = ok[ok["condition"] == "baseline"]
    per_model = {}
    for m in MODELS:
        if m not in trials:
            continue
        d, r = ok[ok["model"] == m], raw[raw["model"] == m]
        b = base[base["model"] == m]
        c = ctx[(ctx["model"] == m) & (ctx["condition"] == "baseline")]
        errs = r["error"].dropna().astype(str).str.split(":").str[0].value_counts().to_dict()
        per_model[m] = {
            "episodes_ok": int(len(d)), "complete_trials": int(trials[m]), "pooled": m in pooled_models,
            "errors": {k: int(v) for k, v in errs.items()}, "cost_usd": round(float(r["cost_usd"].sum()), 2),
            "searches": round(float(d["n_search"].mean()), 2), "opens": round(float(d["n_open"].mean()), 2),
            "forced": round(float(d["forced"].mean()), 3), "no_search": round(float(d["no_search"].mean()), 3),
            "no_brand": round(float(d["no_brand"].mean()), 3), "fabricated": round(float(d["fabricated"].mean()), 3),
            "fabricated_no_search": round(float(d.loc[d["no_search"] == 1, "fabricated"].mean()), 3)
            if (d["no_search"] == 1).any() else None,
            "baseline": {oc: round(float(b[oc].mean()), 3) for oc in OUTCOMES},
            "baseline_in_context_mentioned": round(float(c["mentioned"].mean()), 3),
            "guide_opened_third_party": round(float(d.loc[d["condition"] == "third_party", "guide_opened"].mean()), 3),
            "first_rank_baseline_top5": round(float((b["first_rank"] > 0).mean()), 3),
        }
    # These are descriptive conditional rates; opening is post-treatment and does not identify mediation.
    pooled_open = open_associations[open_associations["model"] == "pooled"]
    mentioned_by_opened = {}
    for cond, group in pooled_open.groupby("condition"):
        mentioned_by_opened[cond] = {str(int(row.opened)): round(float(row.rate), 3)
                                     for row in group.itertuples()}
    summary = {
        "models": per_model, "pooled_models": pooled_models,
        "pooled_baseline": {oc: round(float(base[base["model"].isin(pooled_models)].groupby("model")[oc].mean().mean()), 3)
                            for oc in OUTCOMES},
        "pooled_baseline_in_context": round(float(ctx[ctx["model"].isin(pooled_models) & (ctx["condition"] == "baseline")]
                                                  .groupby("model")["mentioned"].mean().mean()), 3),
        "mentioned_by_opened": mentioned_by_opened,
        "opened_association_interpretation": "Descriptive conditional association; opening is post-treatment, not a mediation estimate.",
        "share_mentions_unopened": round(float(1 - ok[(ok["mentioned"] == 1) & ok["model"].isin(pooled_models)]["opened"].mean()), 3),
        "fixed_query_retrieval_exploratory": {
            "ranking_methods": ["bm25_only", "embedding_only", "fused"],
            "query_trials_by_model": query_trial_counts,
            "equally_weighted_models": query_models,
            "embedding_source": "existing cache only; replay fails if a required vector is absent",
        },
        "sensitivity_excluding_mai_models": without_mai,
        "absolute_rates_file": "agentic_absolute_rates.csv",
        "opened_associations_file": "agentic_open_associations.csv",
    }
    # Exploratory, added after the results: keyword stuffing against endorsement, paired within trials.
    for oc in ("mentioned", "top_pick"):
        w = ok[ok["model"].isin(pooled_models)].pivot_table(index=["model", "scenario", "trial_id"],
                                                            columns="condition", values=oc)
        d = (w["keyword_stuffing"] - w["third_party"]).rename("diff").reset_index()
        d = d.groupby(["scenario", "trial_id"], as_index=False)["diff"].mean()
        lo, hi = A.cluster_boot(d)
        summary[f"stuffing_minus_endorsement_{oc}"] = {"effect": round(float(d["diff"].mean()), 4), "ci_low": round(lo, 4),
                                                       "ci_high": round(hi, 4), "p": round(A.sign_flip_p(d), 4)}
    (RES / "agentic_summary.json").write_text(json.dumps(summary, indent=2))
    fig_agentic(eff, vs, FIG / "fig13_agentic")

    show = eff[eff["model"] == "pooled"].pivot_table(index="condition", columns="outcome", values="effect").round(3)
    print(show.reindex(TREAT).to_string())
    print(vs[(vs["model"] == "pooled") & (vs["outcome"] == "mentioned")][
        ["condition", "agentic", "in_context", "difference", "ci_low", "ci_high", "p"]].round(3).to_string(index=False))
    print(fq_eff[fq_eff["model"] == "pooled"][["condition", "effect", "ci_low", "ci_high", "p_holm"]].round(3).to_string(index=False))
    print(json.dumps(summary, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
