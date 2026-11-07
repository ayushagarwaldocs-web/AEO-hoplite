"""Exploratory analysis of the conditions added after the pre-specified plan (EXPLORATORY in build_corpus.py).

    python analyze_explore.py                   # data/responses.jsonl + data/responses_explore.jsonl
    python analyze_explore.py --tag bedrock     # data/responses_bedrock.jsonl + data/responses_bedrock_explore.jsonl

Each exploratory answer is paired with answers from the same trial in the main responses file:
- endorsement: a neutral mention and a shared recommendation against the baseline page, and the
  sole recommendation of the pre-specified third_party condition against each of them;
- wording: each second wording against the baseline and against the first wording.
Intervals, p-values and pooling follow analyze.py. Holm correction runs within each family, per
model and outcome. None of this is part of the pre-specified analysis.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from analyze import cluster_boot, holm, short_name, sign_flip_p  # noqa: E402
from build_corpus import EXPLORATORY  # noqa: E402

RES = HERE / "results"
OUTCOMES = ["mentioned", "top_pick"]
EDITS = ["statistics", "citations", "quotation", "persuasive", "keyword_stuffing"]
FAMILIES = {
    "vs_baseline": [(c, "baseline") for c in EXPLORATORY],
    "endorsement": [("third_party", "third_party_mention"), ("third_party", "third_party_shared")],
    "wording": [(f"{e}_b", e) for e in EDITS],
}


def load(main: Path, explore: Path) -> pd.DataFrame:
    ex = pd.read_json(explore, lines=True)
    df = pd.concat([pd.read_json(main, lines=True), ex], ignore_index=True)
    df = df[df["error"].isna() & df["model"].isin(set(ex["model"]))]
    return df


def contrasts(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for outcome in OUTCOMES:
        wide = df.pivot_table(index=["model", "scenario", "trial_id"], columns="condition", values=outcome).astype(float)
        models = sorted(wide.index.get_level_values("model").unique())
        for family, pairs in FAMILIES.items():
            for model in models + ["pooled"]:
                block = []
                for cond, ref in pairs:
                    if cond not in wide or ref not in wide:
                        continue
                    d = (wide[cond] - wide[ref]).dropna().rename("diff").reset_index()
                    if model == "pooled":  # equal weight per model, as in analyze.py
                        d = d.groupby(["scenario", "trial_id"], as_index=False)["diff"].mean()
                    else:
                        d = d[d["model"] == model]
                    if d.empty:
                        continue
                    lo, hi = cluster_boot(d)
                    block.append({"family": family, "outcome": outcome, "model": model, "condition": cond,
                                  "reference": ref, "n": len(d), "effect": float(d["diff"].mean()),
                                  "ci_low": lo, "ci_high": hi, "p": sign_flip_p(d)})
                for row, p_adj in zip(block, holm([b["p"] for b in block])):
                    row["p_holm"] = p_adj
                rows.extend(block)
    return pd.DataFrame(rows)


def wording_agreement(df: pd.DataFrame) -> dict:
    """How closely the two wordings of each edit agree, across models and edits (effects on mentions)."""
    wide = df.pivot_table(index=["model", "scenario", "trial_id"], columns="condition", values="mentioned").astype(float)
    pairs = []
    for model in sorted(wide.index.get_level_values("model").unique()):
        w = wide.xs(model, level="model")
        for e in EDITS:
            if {e, f"{e}_b", "baseline"} <= set(w.columns):
                a = (w[e] - w["baseline"]).mean()
                b = (w[f"{e}_b"] - w["baseline"]).mean()
                pairs.append({"model": short_name(model), "edit": e, "first": 100 * a, "second": 100 * b})
    p = pd.DataFrame(pairs)
    if len(p) < 3:
        return {"n_pairs": len(p)}
    return {"n_pairs": len(p), "pearson": round(float(p["first"].corr(p["second"])), 2),
            "spearman": round(float(p["first"].corr(p["second"], method="spearman")), 2),
            "mean_abs_diff_points": round(float((p["first"] - p["second"]).abs().mean()), 1), "pairs": pairs}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="", help="read data/responses_<tag>.jsonl and data/responses_<tag>_explore.jsonl")
    ap.add_argument("--main", default=None)
    ap.add_argument("--explore", default=None)
    args = ap.parse_args()
    stem = f"responses_{args.tag}" if args.tag else "responses"
    main_path = Path(args.main or HERE / "data" / f"{stem}.jsonl")
    explore_path = Path(args.explore or HERE / "data" / f"{stem}_explore.jsonl")
    if not explore_path.exists():
        print(f"No exploratory responses yet ({explore_path.name}).")
        return 1
    df = load(main_path, explore_path)
    suffix = f"_{args.tag}" if args.tag else ""
    out = contrasts(df)
    RES.mkdir(exist_ok=True)
    out.to_csv(RES / f"explore{suffix}.csv", index=False)
    summary = {"models": sorted(short_name(m) for m in df["model"].unique()), "wording": wording_agreement(df)}
    (RES / f"explore_summary{suffix}.json").write_text(json.dumps(summary, indent=1))
    show = out[(out["model"] == "pooled") & (out["outcome"] == "mentioned")].copy()
    for col in ("effect", "ci_low", "ci_high"):
        show[col] = (100 * show[col]).round(1)
    print(f"{len(df):,} answers from {len(summary['models'])} model(s): {', '.join(summary['models'])}")
    print(show[["family", "condition", "reference", "effect", "ci_low", "ci_high", "p_holm"]].to_string(index=False))
    print("wording agreement:", {k: v for k, v in summary["wording"].items() if k != "pairs"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
