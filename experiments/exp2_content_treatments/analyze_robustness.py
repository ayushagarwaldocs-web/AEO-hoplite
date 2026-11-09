"""Robustness checks (README, "Robustness checks"): long pages, sampling temperature, flagship replication.

    python analyze_robustness.py

Long pages and temperature 1 are compared with the same models' main-run answers in the same trials:
for each treatment, the change in its effect is the per-trial difference
(alt treatment - alt baseline) - (main treatment - main baseline), averaged over models with equal weight,
with the cluster bootstrap and sign-flip test of analyze.py and Holm correction across treatments.
The flagship replication is analysed by the standard scripts with --tag flagship; this script only adds
how its ranking of treatments agrees with the main analysis. Nothing here is pre-specified.
"""

from __future__ import annotations

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
from analyze import LABELS, cluster_boot, effects, holm, short_name, sign_flip_p  # noqa: E402

DATA, RES, FIG = HERE / "data", HERE / "results", ROOT / "paper" / "figures"
LONG_CONDS = ["baseline", "filler", "third_party", "statistics", "citations", "quotation", "persuasive",
              "keyword_stuffing", "injection"]
TEMP_CONDS = ["baseline", "filler", "third_party", "statistics", "citations", "keyword_stuffing", "injection"]


def n_answered(path: Path) -> int:
    """Answers without an error, as analyze_all.sh counts them for the 1,300-answer rule."""
    return sum(1 for line in path.open() if line.strip() and json.loads(line).get("error") is None)


def load(path: Path | list[Path]) -> pd.DataFrame:
    paths = [p for p in (path if isinstance(path, list) else [path]) if p.exists()]
    df = pd.concat([pd.read_json(p, lines=True) for p in paths], ignore_index=True)
    df = df[df["error"].isna()].copy()
    df["cited"] = df["cited"].astype(float)
    return df


def compare(main: pd.DataFrame, alt: pd.DataFrame, conds: list[str], label: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Effects in both versions (same models, trials and conditions), and the change in each effect."""
    models = sorted(set(alt["model"]))
    m = main[main["model"].isin(models) & main["condition"].isin(conds)]
    a = alt[alt["model"].isin(models) & alt["condition"].isin(conds)]
    keys = set(map(tuple, a[["model", "trial_id", "condition"]].to_numpy()))
    m = m[[tuple(k) in keys for k in m[["model", "trial_id", "condition"]].to_numpy()]]
    eff = []
    for version, d in (("main", m), (label, a)):
        for ref in ("baseline", "filler"):
            e = effects(d, ref=ref)
            e["version"] = version
            eff.append(e)
    eff = pd.concat(eff, ignore_index=True)
    change = []
    for outcome in ("mentioned", "top_pick"):
        idx = ["model", "scenario", "trial_id"]
        wm = m.pivot_table(index=idx, columns="condition", values=outcome).astype(float)
        wa = a.pivot_table(index=idx, columns="condition", values=outcome).astype(float)
        block = []
        for cond in conds[1:]:
            d = ((wa[cond] - wa["baseline"]) - (wm[cond] - wm["baseline"])).dropna().rename("diff").reset_index()
            d = d.groupby(["scenario", "trial_id"], as_index=False)["diff"].mean()  # equal weight per model
            lo, hi = cluster_boot(d)
            block.append({"version": label, "outcome": outcome, "condition": cond, "n": len(d),
                          "change": float(d["diff"].mean()), "ci_low": lo, "ci_high": hi, "p": sign_flip_p(d)})
        for row, p_adj in zip(block, holm([b["p"] for b in block])):
            row["p_holm"] = p_adj
        change.extend(block)
    return eff, pd.DataFrame(change)


def sign_agreement(eff: pd.DataFrame, label: str) -> dict:
    """Per model and treatment (mentions, against baseline): do the two versions agree in sign?"""
    e = eff[(eff["outcome"] == "mentioned") & (eff["reference"] == "baseline") & (eff["model"] != "pooled")]
    w = e.pivot_table(index=["model", "condition"], columns="version", values="effect")
    both = w.dropna()
    same = (np.sign(both["main"]) == np.sign(both[label])) | (both[["main", label]].abs().max(axis=1) < 0.005)
    return {"pairs": int(len(both)), "same_sign": int(same.sum()),
            "pearson": round(float(both["main"].corr(both[label])), 2)}


def summary_rows(eff: pd.DataFrame, change: pd.DataFrame, label: str) -> dict:
    p = eff[(eff["model"] == "pooled") & (eff["outcome"] == "mentioned")]
    out = {}
    for _, r in p.iterrows():
        key = f"{r['version']}|{r['reference']}|{r['condition']}"
        out[key] = {"effect": round(100 * r["effect"], 1), "ci": [round(100 * r["ci_low"], 1), round(100 * r["ci_high"], 1)],
                    "p_holm": float(r["p_holm"])}
    ch = change[change["outcome"] == "mentioned"]
    out["change"] = {r["condition"]: {"change": round(100 * r["change"], 1),
                                      "ci": [round(100 * r["ci_low"], 1), round(100 * r["ci_high"], 1)],
                                      "p_holm": float(r["p_holm"])} for _, r in ch.iterrows()}
    out["signs"] = sign_agreement(eff, label)
    return out


def baseline_rates(main: pd.DataFrame, alt: pd.DataFrame) -> dict:
    models = sorted(set(alt["model"]))
    b_main = main[main["model"].isin(models) & (main["condition"] == "baseline")].groupby("model")["mentioned"].mean()
    b_alt = alt[alt["condition"] == "baseline"].groupby("model")["mentioned"].mean()
    return {"main": round(100 * b_main.mean(), 1), "alt": round(100 * b_alt.mean(), 1)}


def fig_robustness(parts: list[tuple[str, pd.DataFrame, str]], stem: Path) -> None:
    """Pooled mention effects against baseline: main run and the robustness version, with 95% intervals."""
    ps.apply()
    fig, axes = ps.plt.subplots(1, len(parts), figsize=(3.6 * len(parts), 3.0), sharex=True, squeeze=False)
    for ax, (title, eff, label) in zip(axes[0], parts):
        p = eff[(eff["model"] == "pooled") & (eff["outcome"] == "mentioned") & (eff["reference"] == "baseline")]
        order = (p[p["version"] == "main"].set_index("condition")["effect"].sort_values().index.tolist())
        ys = np.arange(len(order))
        for version, color, dy, name in (("main", "#9a9890", -0.13, "Main design"), (label, ps.INK, 0.13, title)):
            v = p[p["version"] == version].set_index("condition").reindex(order)
            ax.hlines(ys + dy, v["ci_low"] * 100, v["ci_high"] * 100, color=color, lw=1.1)
            ax.plot(v["effect"] * 100, ys + dy, "o", ms=4.6, color=color, mec=ps.SURFACE, mew=0.7, label=name)
        ax.axvline(0, color=ps.INK2, lw=0.9, zorder=0)
        ax.set_yticks(ys, [LABELS.get(c, c) for c in order], fontsize=7.5)
        ax.tick_params(axis="y", length=0)
        ax.tick_params(axis="x", labelsize=7.5)
        ax.xaxis.grid(True)
        ax.set_axisbelow(True)
        ax.set_ylim(-0.6, len(order) - 0.4)
        ax.set_xlabel("Change in mentions from baseline (points)", fontsize=8)
        ax.legend(loc="lower right", fontsize=7, frameon=False)
    fig.subplots_adjust(wspace=0.55)
    ps.save(fig, stem)


# Exploratory: effects weighted by how much each assistant is used. Shares of worldwide generative-AI web visits,
# Similarweb, May 2026 ("The AI market has fragmented", published 29 July 2026): ChatGPT about 53%, Gemini 27-28%,
# Claude about 9%; the remaining ~10.5% is not broken down, so it is split equally over the other assistants whose
# developer we tested. Each assistant is represented by its developer's tested models that are closest to the
# consumer product; models with no consumer assistant (gpt-oss, Gemma, Nova, Nemotron, GLM, MiniMax) are left out.
ASSISTANTS = {
    "ChatGPT": (0.53, ["azure:gpt-5-mini", "openai:gpt-6.1-sol"]),
    "Gemini": (0.275, ["gemini:gemini-3.5-flash", "gemini:gemini-3.6-flash", "gemini:gemini-3.5-flash-lite",
                       "gemini:gemini-4-argon"]),
    "Claude": (0.09, ["bedrock:global.anthropic.claude-sonnet-4-6", "bedrock:global.anthropic.claude-opus-4-6-v1",
                   "anthropic:claude-opus-5-5", "anthropic:claude-sonnet-5-5", "anthropic:claude-haiku-5-5",
                   "anthropic:claude-fable-5-1"]),
    "Copilot": (None, ["azure:MAI-Thinking-1"]),
    "Grok": (None, ["azure:grok-4.6"]),
    "DeepSeek": (None, ["bedrock:deepseek.v3.2", "azure:DeepSeek-V4-Pro"]),
    "Meta AI": (None, ["bedrock:us.meta.llama4-maverick-17b-instruct-v1:0"]),
    "Kimi": (None, ["bedrock:global.moonshotai.kimi-k3", "azure:Kimi-K3.1-Pro"]),
    "Qwen": (None, ["bedrock:qwen.qwen3-32b-v1:0", "bedrock:qwen.qwen3-next-80b-a3b"]),
    "Le Chat": (None, ["bedrock:mistral.mistral-large-3-675b-instruct"]),
}
OTHER_SHARE = 1 - 0.53 - 0.275 - 0.09


def assistant_weights() -> dict[str, float]:
    others = [a for a, (w, _) in ASSISTANTS.items() if w is None]
    return {a: (w if w is not None else OTHER_SHARE / len(others)) for a, (w, _) in ASSISTANTS.items()}


def usage_weighted(short: pd.DataFrame, conds: list[str]) -> pd.DataFrame:
    """Per trial: average each assistant's models, then weight assistants by usage (renormalised over the assistants
    present in that trial). Cluster bootstrap and sign-flip test over scenarios, Holm across treatments."""
    weights = assistant_weights()
    model_to = {m: a for a, (_, ms) in ASSISTANTS.items() for m in ms}
    d0 = short[short["model"].isin(model_to)].copy()
    d0["assistant"] = d0["model"].map(model_to)
    rows = []
    for outcome in ("mentioned", "top_pick"):
        wide = d0.pivot_table(index=["assistant", "model", "scenario", "trial_id"], columns="condition",
                              values=outcome).astype(float)
        block = []
        for cond in conds:
            if cond == "baseline" or cond not in wide:
                continue
            diff = (wide[cond] - wide["baseline"]).dropna().rename("diff").reset_index()
            per_a = diff.groupby(["assistant", "scenario", "trial_id"], as_index=False)["diff"].mean()
            per_a["w"] = per_a["assistant"].map(weights)
            per_t = per_a.groupby(["scenario", "trial_id"]).apply(
                lambda g: (g["diff"] * g["w"]).sum() / g["w"].sum(), include_groups=False).rename("diff").reset_index()
            lo, hi = cluster_boot(per_t)
            equal = per_a.groupby(["scenario", "trial_id"], as_index=False)["diff"].mean()["diff"].mean()
            block.append({"outcome": outcome, "condition": cond, "n": len(per_t), "effect": float(per_t["diff"].mean()),
                          "ci_low": lo, "ci_high": hi, "p": sign_flip_p(per_t), "equal_weight_assistants": float(equal)})
        for row, p_adj in zip(block, holm([b["p"] for b in block])):
            row["p_holm"] = p_adj
        rows.extend(block)
    out = pd.DataFrame(rows)
    out.attrs["assistants_present"] = sorted(d0["assistant"].unique())
    return out


def flagship_agreement() -> dict:
    """How the flagship models' pooled ranking of treatments compares with the main 12-model analysis."""
    f, m = RES / "effects_flagship.csv", RES / "effects_bedrock.csv"
    if not f.exists():
        return {}
    fe, me = pd.read_csv(f), pd.read_csv(m)
    sel = lambda e: e[(e["model"] == "pooled") & (e["outcome"] == "mentioned")].set_index("condition")["effect"]  # noqa: E731
    a, b = sel(fe), sel(me)
    common = a.index.intersection(b.index)
    per = fe[(fe["outcome"] == "mentioned") & (fe["model"] != "pooled")]
    sig = per[(per["p_holm"] < 0.05) & (per["effect"] > 0)].groupby("condition")["model"].nunique()
    return {"spearman_vs_main": round(float(a[common].corr(b[common], method="spearman")), 2),
            "models": sorted(short_name(x) for x in per["model"].unique()),
            "n_sig_models": {c: int(sig.get(c, 0)) for c in common}}


def main() -> int:
    RES.mkdir(exist_ok=True)
    # Short-page answers: the 12 main models plus every replication model (long pages pair with these).
    # The API-run models join as in analyze_all.sh, only with at least 1,300 of 1,350 answers (README, item 5); until
    # 9 November this list left out GPT-6.1 Sol and Claude Sonnet 5.5, although item 5 gives them their assistants'
    # weight. Gemini 3.5 Flash (responses_gemini.jsonl, 16 answers) stays out.
    replication = ([DATA / f"responses_flagship_{m}.jsonl" for m in ("opus", "kimi", "glm")]
                   + sorted(DATA.glob("responses_azure_*.jsonl"))
                   + [p for pat in ("responses_anthropic_*.jsonl", "responses_openai_*.jsonl", "responses_gemini_*.jsonl")
                      for p in sorted(DATA.glob(pat)) if n_answered(p) >= 1300])
    main_df = load([DATA / "responses_bedrock.jsonl"] + replication)
    long_files = [DATA / "responses_long.jsonl", DATA / "responses_long2.jsonl"] + sorted(DATA.glob("responses_long_azure_*.jsonl"))
    summary, parts = {}, []
    for label, paths, conds, title in (("long", long_files, LONG_CONDS, "Long pages"),
                                       ("temp1", [DATA / "responses_temp.jsonl"], TEMP_CONDS, "Temperature 1")):
        if not paths[0].exists():
            print(f"{paths[0].name}: not run yet")
            continue
        alt = load(paths)
        eff, change = compare(main_df, alt, conds, label)
        eff.to_csv(RES / f"robust_{label}_effects.csv", index=False)
        change.to_csv(RES / f"robust_{label}_change.csv", index=False)
        summary[label] = {"models": sorted(short_name(x) for x in alt["model"].unique()), "n_answers": int(len(alt)),
                          "baseline_mention": baseline_rates(main_df, alt), **summary_rows(eff, change, label)}
        if label == "long":
            words = alt.groupby("condition")["target_words"].mean()
            summary[label]["target_words"] = {"baseline": round(float(words["baseline"])),
                                              "main_baseline": round(float(main_df.loc[main_df["condition"] == "baseline",
                                                                                       "target_words"].mean()))}
        parts.append((title, eff, label))
        ch = change[change["outcome"] == "mentioned"].copy()
        for col in ("change", "ci_low", "ci_high"):
            ch[col] = (100 * ch[col]).round(1)
        print(f"== {title}: {len(alt):,} answers from {alt['model'].nunique()} models")
        print(ch[["condition", "change", "ci_low", "ci_high", "p_holm"]].to_string(index=False))
        print("signs:", summary[label]["signs"], "| baseline mention:", summary[label]["baseline_mention"])
    if parts:
        fig_robustness(parts, FIG / "fig12_robustness")
    summary["flagship"] = flagship_agreement()
    from build_corpus import CONDITIONS
    uw = usage_weighted(main_df, CONDITIONS)
    uw.to_csv(RES / "usage_weighted.csv", index=False)
    summary["usage_weighted"] = {"assistants_present": uw.attrs["assistants_present"],
                                 "weights": {a: round(w, 4) for a, w in assistant_weights().items()}}
    show = uw[uw["outcome"] == "mentioned"].copy()
    for col in ("effect", "ci_low", "ci_high", "equal_weight_assistants"):
        show[col] = (100 * show[col]).round(1)
    print("== usage-weighted (assistants present:", ", ".join(uw.attrs["assistants_present"]), ")")
    print(show[["condition", "effect", "ci_low", "ci_high", "p_holm", "equal_weight_assistants"]].to_string(index=False))
    (RES / "robustness_summary.json").write_text(json.dumps(summary, indent=1))
    print("flagship:", summary["flagship"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
