"""Analyse the agentic search experiment (specified in README.md, "Agentic search").

    python3 analyze_agentic.py

Reads data/agentic_<model>.jsonl (never the pilot files) and keeps each model's complete trials (all seven conditions
answered without error). Pre-specified analyses:
  1-2  effects of each treatment against baseline on mentioned, top pick, cited, surfaced and opened, per model and
       pooled (equal weight per model; models with fewer than 60 complete trials are descriptive only)
  3    agentic minus in-context effect for the same models and trials (in-context answers from the main runs)
  4    retrieval with queries held fixed: every query issued in a baseline episode, rerun against each condition's
       pool (no model calls); the target's top-five rate
Exploratory: answers citing URLs that no search returned (fabricated citations), mentions by whether the target
page was opened, and (added after the results) keyword stuffing against endorsement within trials.

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
from search_pool import CONDITIONS, Embedder, Engine, episodes, norm_url  # noqa: E402
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


def fixed_queries(ok: pd.DataFrame, pooled_models: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Target's top-five rate per condition, with each baseline episode's queries held fixed (analysis 4)."""
    eps, pool = episodes()
    by_key = {(e["trial_id"], e["condition"]): e for e in eps}
    emb, rows = Embedder(), []
    base = ok[ok["condition"] == "baseline"]
    for trial_id, group in base.groupby("trial_id"):
        engines = {c: Engine(pool, by_key[(trial_id, c)]["override"], emb) for c in CONDITIONS}
        target = by_key[(trial_id, "baseline")]["target_url"]
        for _, r in group.iterrows():
            queries = [s["query"] for s in r["steps"] if s["tool"] == "search" and s.get("query")]
            if not queries:
                continue
            for cond, eng in engines.items():
                hits = [target in eng.rank(q)[:5] for q in queries]
                rows.append({"model": r["model"], "scenario": r["scenario"], "trial_id": trial_id,
                             "condition": cond, "top5": float(np.mean(hits)), "n_queries": len(queries)})
    fq = pd.DataFrame(rows)
    return fq, model_effects(fq, ["top5"], pooled_models)


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
    for oc, color, dy, name in (("surfaced", ps.SERIES[0], -0.13, "Target in search results"),
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
    fq, fq_eff = fixed_queries(ok, pooled_models)
    RES.mkdir(exist_ok=True)
    eff.to_csv(RES / "agentic_effects.csv", index=False)
    vs.to_csv(RES / "agentic_vs_context.csv", index=False)
    fq.to_csv(RES / "agentic_fixed_queries_rows.csv", index=False)
    fq_eff.to_csv(RES / "agentic_fixed_queries.csv", index=False)

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
    # Exploratory: mention rates by whether the target page was opened (conditions on a post-treatment variable).
    by_open = (ok[ok["model"].isin(pooled_models)].groupby(["condition", "opened"])["mentioned"].mean()
               .unstack().round(3))
    summary = {
        "models": per_model, "pooled_models": pooled_models,
        "pooled_baseline": {oc: round(float(base[base["model"].isin(pooled_models)].groupby("model")[oc].mean().mean()), 3)
                            for oc in OUTCOMES},
        "pooled_baseline_in_context": round(float(ctx[ctx["model"].isin(pooled_models) & (ctx["condition"] == "baseline")]
                                                  .groupby("model")["mentioned"].mean().mean()), 3),
        "mentioned_by_opened": {c: {str(int(k)): v for k, v in row.dropna().items()} for c, row in by_open.iterrows()},
        "share_mentions_unopened": round(float(1 - ok[(ok["mentioned"] == 1) & ok["model"].isin(pooled_models)]["opened"].mean()), 3),
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
