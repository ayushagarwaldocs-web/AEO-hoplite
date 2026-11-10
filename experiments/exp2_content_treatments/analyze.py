"""Analyse Experiment 2 (pre-specified plan in README.md).

    python analyze.py                                   # data/responses.jsonl
    python analyze.py --input data/responses_mock.jsonl --tag mock

For every model and treatment, the effect is the paired difference from the
baseline in the same trial (same scenario, target and source order). Intervals
are 95% cluster-bootstrap intervals over scenarios; p-values come from a
scenario-level sign-flip permutation test with Holm correction across the 14
treatments, separately per model and outcome.
"""

from __future__ import annotations

import argparse
import re
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from aeotools import plotstyle as ps  # noqa: E402
from build_corpus import CONDITIONS  # noqa: E402

OUTCOMES = ["mentioned", "top_pick", "cited", "pawc"]
LABELS = {
    "statistics": "Statistics", "citations": "Source citations", "quotation": "Expert quotation",
    "answer_first": "Answer-first summary", "qa_format": "Q&A format", "spec_table": "Spec table",
    "limitations": "Stated limitations", "freshness": "Freshness date", "third_party": "Third-party endorsement",
    "persuasive": "Persuasive tone", "keyword_stuffing": "Keyword stuffing", "filler": "Boilerplate placebo",
    "injection": "Source-embedded instruction", "combined": "Combined",
}
RNG = np.random.default_rng(20261103)


BEDROCK_NAMES = {
    "claude-sonnet-4-6": "Claude Sonnet 4.6", "claude-sonnet-5-5": "Claude Sonnet 5.5",
    "claude-haiku-5-5": "Claude Haiku 5.5", "claude-opus-5-5": "Claude Opus 5.5",
    "gpt-oss-120b": "gpt-oss-120b", "gpt-oss-20b": "gpt-oss-20b", "gpt-6.1-sol": "GPT-6.1 Sol",
    "gpt-6-luna": "GPT-6 Luna", "gpt-6-astra": "GPT-6 Astra", "llama4-maverick": "Llama 4 Maverick",
    "nova-pro": "Nova Pro", "nova-2-lite": "Nova 2 Lite", "mistral-large-3": "Mistral Large 3",
    "deepseek.v3.2": "DeepSeek V3.2", "qwen3-32b": "Qwen3 32B", "qwen3-next-80b": "Qwen3 Next 80B",
    "gemma-3-27b": "Gemma 3 27B", "minimax-m2.5": "MiniMax M2.5", "nemotron-super-3": "Nemotron 3 Super",
    "claude-opus-4-6": "Claude Opus 4.6", "claude-haiku-4-5": "Claude Haiku 4.5", "kimi-k3": "Kimi K3",
    "glm-5": "GLM 5",
}


# Models reached through Microsoft Foundry (Azure) and the Gemini API, by exact spec.
OTHER_NAMES = {
    "azure:gpt-5-mini": "GPT-5 mini", "azure:grok-4.6": "Grok 4.6", "azure:MAI-Thinking-1": "MAI-Thinking-1",
    "azure:DeepSeek-V4-Pro": "DeepSeek V4 Pro", "azure:Kimi-K3.1-Pro": "Kimi K3.1 Pro",
    "gemini:gemini-3.5-flash": "Gemini 3.5 Flash", "gemini:gemini-3.6-flash": "Gemini 3.6 Flash",
    "gemini:gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite",
    "anthropic:claude-opus-5-5": "Claude Opus 5.5", "anthropic:claude-sonnet-5-5": "Claude Sonnet 5.5",
    "anthropic:claude-haiku-5-5": "Claude Haiku 5.5", "anthropic:claude-fable-5-1": "Claude Fable 5.1",
    "openai:gpt-6.1-sol": "GPT-6.1 Sol",
}


def short_name(model: str) -> str:
    """'mlx:Llama-3.2-3B-Instruct-4bit' -> 'Llama-3.2-3B'; 'bedrock:deepseek.v3.2' -> 'DeepSeek V3.2'."""
    if model in OTHER_NAMES:
        return OTHER_NAMES[model]
    if model.startswith("bedrock:"):
        return next((v for k, v in BEDROCK_NAMES.items() if k in model), model.split(":", 1)[1])
    name = re.sub(r"(?i)-instruct(-4bit)?$", "", model.split(":", 1)[-1])
    return re.sub(r"(\d)b$", r"\1B", name[:1].upper() + name[1:])


def paired(df: pd.DataFrame, outcome: str, ref: str = "baseline") -> pd.DataFrame:
    wide = df.pivot_table(index=["model", "scenario", "trial_id"], columns="condition", values=outcome)
    wide = wide.astype(float)
    rows = []
    for cond in CONDITIONS[1:]:
        if cond not in wide or cond == ref:
            continue
        d = (wide[cond] - wide[ref]).dropna().rename("diff").reset_index()
        d["condition"] = cond
        rows.append(d)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def cluster_boot(d: pd.DataFrame, n_boot: int = 4000) -> tuple[float, float]:
    by_s = d.groupby("scenario")["diff"].agg(["sum", "count"])
    sums, counts = by_s["sum"].to_numpy(), by_s["count"].to_numpy()
    idx = RNG.integers(0, len(sums), size=(n_boot, len(sums)))
    means = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def sign_flip_p(d: pd.DataFrame, n_perm: int = 10000) -> float:
    s = d.groupby("scenario")["diff"].mean().to_numpy()
    observed = abs(s.mean())
    flips = RNG.choice([-1.0, 1.0], size=(n_perm, len(s)))
    null = np.abs((flips * s).mean(axis=1))
    return float((np.sum(null >= observed - 1e-12) + 1) / (n_perm + 1))


def holm(pvals: list[float]) -> list[float]:
    order = np.argsort(pvals)
    adj = np.empty(len(pvals))
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(pvals) - rank) * pvals[i])
        adj[i] = min(1.0, running)
    return adj.tolist()


def effects(df: pd.DataFrame, ref: str = "baseline") -> pd.DataFrame:
    rows = []
    for outcome in OUTCOMES:
        d_all = paired(df, outcome, ref)
        if d_all.empty:
            continue
        models = sorted(d_all["model"].unique())
        for model in models + ["pooled"]:
            d_m = d_all if model == "pooled" else d_all[d_all["model"] == model]
            block = []
            for cond in CONDITIONS[1:]:
                d = d_m[d_m["condition"] == cond]
                if d.empty:
                    continue
                if model == "pooled":  # equal weight per model: average model-level diffs per trial
                    d = d.groupby(["scenario", "trial_id"], as_index=False)["diff"].mean()
                lo, hi = cluster_boot(d)
                block.append({"outcome": outcome, "reference": ref, "model": model, "condition": cond, "n": len(d),
                              "effect": float(d["diff"].mean()), "ci_low": lo, "ci_high": hi,
                              "p": sign_flip_p(d)})
            for row, p_adj in zip(block, holm([b["p"] for b in block])):
                row["p_holm"] = p_adj
            rows.extend(block)
    return pd.DataFrame(rows)


def baseline_rates(df: pd.DataFrame) -> pd.DataFrame:
    base = df[df["condition"] == "baseline"]
    return base.groupby("model")[OUTCOMES].mean().reset_index()


def position_effect(df: pd.DataFrame) -> pd.DataFrame:
    base = df[df["condition"] == "baseline"]
    return base.groupby(["model", "target_index"])["mentioned"].agg(["mean", "count"]).reset_index()


def wilson(k: float, n: float, z: float = 1.96) -> tuple[float, float]:
    p, d = k / n, 1 + z * z / n
    centre, half = (p + z * z / (2 * n)) / d, z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return centre - half, centre + half


def trial_cluster_intervals(df: pd.DataFrame, n_boot: int = 4000,
                            rng: np.random.Generator | None = None) -> pd.DataFrame:
    """Bootstrap rates by scenario/trial clusters, retaining every row per trial."""
    rng = rng or RNG
    group_cols = ["model", "plot_condition", "target_index"]
    cluster_cols = ["scenario", "trial_id"]
    grouped = df.groupby(cluster_cols + group_cols, observed=True)["mentioned"].agg(["sum", "count"])
    cells = grouped.reset_index()[group_cols].drop_duplicates().sort_values(group_cols).reset_index(drop=True)
    trials = df[cluster_cols].drop_duplicates().reset_index(drop=True)
    trial_index, cell_index = pd.MultiIndex.from_frame(trials), pd.MultiIndex.from_frame(cells)
    sums = (grouped["sum"].unstack(group_cols).reindex(index=trial_index, columns=cell_index)
            .fillna(0).to_numpy(dtype=float))
    counts = (grouped["count"].unstack(group_cols).reindex(index=trial_index, columns=cell_index)
              .fillna(0).to_numpy(dtype=float))
    by_scenario = trials["scenario"].to_numpy()
    draws = np.concatenate([
        rng.choice(np.flatnonzero(by_scenario == scenario),
                   size=(n_boot, int(np.sum(by_scenario == scenario))), replace=True)
        for scenario in pd.unique(by_scenario)
    ], axis=1)
    boot_sums, boot_counts = sums[draws].sum(axis=1), counts[draws].sum(axis=1)
    rates = np.divide(boot_sums, boot_counts, out=np.full_like(boot_sums, np.nan), where=boot_counts > 0)
    point = sums.sum(axis=0) / counts.sum(axis=0)
    return pd.DataFrame([
        {**cell, "rate": point[i], "ci_low": float(np.nanpercentile(rates[:, i], 2.5)),
         "ci_high": float(np.nanpercentile(rates[:, i], 97.5)), "n": int(counts[:, i].sum())}
        for i, cell in cells.iterrows()
    ])


def fig_position(df: pd.DataFrame, stem: Path, evidence: tuple[str, ...] = ("statistics", "citations")) -> None:
    """Mention rates by target slot with intervals from a shared trial-cluster bootstrap."""
    models = sorted(df["model"].unique())
    if len(models) > 4:  # too many panels to read: pool all models into one
        df = df.assign(model="pooled")
        models = ["pooled"]
    plot_df = df[df["condition"].eq("baseline") | df["condition"].isin(evidence)].copy()
    plot_df["plot_condition"] = np.where(plot_df["condition"].eq("baseline"), "Baseline page",
                                         "With statistics or citations")
    intervals = trial_cluster_intervals(plot_df)
    fig, axes = ps.plt.subplots(1, len(models), figsize=(2.4 * len(models) + 0.4, 2.5), sharey=True, squeeze=False)
    for ax, model in zip(axes[0], models):
        d = plot_df[plot_df["model"] == model]
        for label, color, dx in [("Baseline page", ps.SERIES[0], -0.1),
                                 ("With statistics or citations", ps.SERIES[1], 0.1)]:
            sub = d[d["plot_condition"] == label]
            rates = sub.groupby("target_index")["mentioned"].agg(["sum", "count"])
            xs = rates.index.to_numpy() + dx
            ci = intervals[(intervals["model"] == model) & (intervals["plot_condition"] == label)].set_index("target_index")
            ax.vlines(xs, ci.loc[rates.index, "ci_low"].to_numpy() * 100,
                      ci.loc[rates.index, "ci_high"].to_numpy() * 100, color=color, lw=1.0, alpha=0.6)
            ax.plot(xs, rates["sum"] / rates["count"] * 100, "o-", color=color, ms=4, lw=1.3, mec=ps.SURFACE,
                    mew=0.7, label=label)
        ax.set_xlim(0.5, 6.5)
        ax.set_ylim(0, 100)
        ax.yaxis.grid(True)
        ax.set_axisbelow(True)
        ax.set_xticks(range(1, 7))
        ax.tick_params(labelsize=7.5)
        ax.set_title("All hosted models" if model == "pooled" else short_name(model), loc="left", fontsize=8.5, color=ps.INK2, fontweight="normal")
        ax.set_xlabel("Position of the target's page", fontsize=8)
    axes[0][0].set_ylabel("Target mentioned (%)", fontsize=8)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=2, fontsize=7.5)
    fig.subplots_adjust(wspace=0.08)
    ps.save(fig, stem)


def effects_table(eff: pd.DataFrame, outcome: str) -> pd.DataFrame:
    sub = eff[eff["outcome"] == outcome].copy()
    sub["cell"] = sub.apply(lambda r: f"{r['effect'] * 100:+.1f}{'*' if r['p_holm'] < 0.05 else ''}", axis=1)
    return sub.pivot_table(index="condition", columns="model", values="cell", aggfunc="first").reindex(CONDITIONS[1:])


def injection_flags(df: pd.DataFrame) -> pd.DataFrame:
    inj = df[df["condition"] == "injection"].copy()
    pattern = r"(?i)(note to ai|instruction|manipulat|prompt injection|told to recommend|asks? (ai|assistants))"
    inj["flagged_injection"] = inj["text"].fillna("").str.contains(pattern, regex=True)
    return inj.groupby("model")["flagged_injection"].mean().reset_index()


def forest(eff: pd.DataFrame, stem: Path, outcomes: tuple[str, ...] = ("mentioned", "top_pick")) -> None:
    """One panel per outcome: the pooled effect with its 95% CI, and each model's point estimate."""
    sub = eff[eff["outcome"].isin(outcomes)]
    if sub.empty:
        return
    models = [m for m in sorted(sub["model"].unique()) if m != "pooled"]
    order = (sub[(sub["model"] == "pooled") & (sub["outcome"] == outcomes[0])].set_index("condition")["effect"]
             .reindex(CONDITIONS[1:]).dropna().sort_values().index.tolist())
    fig, axes = ps.plt.subplots(1, len(outcomes), figsize=(7.2, 0.3 * len(order) + 1.3), sharey=True)
    lo = min(sub["ci_low"].min(), sub["effect"].min()) * 100 - 3
    hi = max(sub["ci_high"].max(), sub["effect"].max()) * 100 + 3
    offsets = np.linspace(-0.22, 0.22, len(models)) if len(models) > 1 else [0.0]
    titles = {"mentioned": "Target mentioned", "top_pick": "First-mentioned brand", "cited": "Target page cited"}
    for ax, outcome in zip(axes, outcomes):
        o = sub[sub["outcome"] == outcome]
        pooled = o[o["model"] == "pooled"].set_index("condition").reindex(order)
        ys = np.arange(len(order))
        ax.hlines(ys, pooled["ci_low"] * 100, pooled["ci_high"] * 100, color="#cfcec6", lw=6, zorder=1)
        many = len(models) > len(ps.SERIES)  # too many models to colour: grey dots, one legend entry
        for i, model in enumerate(models):
            m = o[o["model"] == model].set_index("condition").reindex(order)
            ax.plot(m["effect"] * 100, ys + offsets[i], "o", ms=3.4 if many else 4.2,
                    color="#9a9890" if many else ps.SERIES[i], mec=ps.SURFACE, mew=0.6 if many else 0.8, zorder=2,
                    label=("Single models" if i == 0 else None) if many else short_name(model))
        sig = pooled["p_holm"].to_numpy() < 0.05
        ax.plot(pooled["effect"][sig] * 100, ys[sig], "D", ms=5.5, color=ps.INK, zorder=3, label="Pooled, Holm p < 0.05")
        ax.plot(pooled["effect"][~sig] * 100, ys[~sig], "D", ms=5.5, color=ps.SURFACE, mec=ps.INK, mew=1.1, zorder=3,
                label="Pooled, not significant")
        for y, (_, row) in zip(ys, pooled.iterrows()):
            ax.text(1.01, y, f"{row['effect'] * 100:+.0f}", transform=ax.get_yaxis_transform(), va="center",
                    fontsize=7.5, color=ps.INK2)
        ax.axvline(0, color=ps.INK2, lw=0.9, zorder=0)
        ax.set_xlim(lo, hi)
        ax.set_ylim(-0.6, len(order) - 0.4)
        ax.xaxis.grid(True)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", length=0)
        ax.set_title(titles.get(outcome, outcome), loc="left", fontsize=9, color=ps.INK2, fontweight="normal")
        ax.set_xlabel("Change from baseline (points)")
    axes[0].set_yticks(range(len(order)), [LABELS.get(c, c) for c in order])
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=len(labels), fontsize=7.5,
               handletextpad=0.3, columnspacing=1.2)
    fig.subplots_adjust(wspace=0.12)
    ps.save(fig, stem)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(HERE / "data" / "responses.jsonl"))
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    ps.apply()
    df = pd.read_json(args.input, lines=True)
    df = df[df["error"].isna()].copy()
    df["cited"] = df["cited"].astype(float)
    suffix = f"_{args.tag}" if args.tag else ""
    res = HERE / "results"
    res.mkdir(exist_ok=True)
    eff = effects(df)
    eff.to_csv(res / f"effects{suffix}.csv", index=False)
    effects(df, ref="filler").to_csv(res / f"effects_vs_placebo{suffix}.csv", index=False)
    effects_table(eff, "mentioned").to_csv(res / f"effects_table_mentioned{suffix}.csv")
    effects_table(eff, "top_pick").to_csv(res / f"effects_table_top_pick{suffix}.csv")
    baseline_rates(df).to_csv(res / f"baseline_rates{suffix}.csv", index=False)
    position_effect(df).to_csv(res / f"position_effect{suffix}.csv", index=False)
    injection_flags(df).to_csv(res / f"injection_flags{suffix}.csv", index=False)
    fig_dir = (ROOT / "paper" / "figures") if not args.tag else res
    forest(eff, fig_dir / f"fig5_treatments{suffix}")
    fig_position(df, fig_dir / f"fig7_position{suffix}")
    pooled = eff[(eff["model"] == "pooled") & (eff["outcome"] == "mentioned")]
    print(f"{len(df)} scored responses from {df['model'].nunique()} model(s)")
    print(pooled[["condition", "effect", "ci_low", "ci_high", "p_holm"]].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
