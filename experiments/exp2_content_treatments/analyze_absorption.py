"""Exploratory (not pre-specified): does the answer pass on what a treatment added?

For each treatment that adds checkable content to the target page, a detector looks
for that content in the answer (e.g. the review count for `statistics`, the expert's
surname for `quotation`). The same detector run on the paired baseline answer, where
the content was never shown, estimates its false-positive rate.

    python analyze_absorption.py [--input data/responses.jsonl]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from aeotools import plotstyle as ps  # noqa: E402

RES = HERE / "results"
FIG = ROOT / "paper" / "figures"


def _has(text: str, *needles: str) -> bool:
    low = text.lower()
    return any(n and n.lower() in low for n in needles)


def _num(text: str, value: str) -> bool:
    return re.search(rf"(?<![\d.]){re.escape(value)}(?![\d])", text) is not None


def _same_sentence(text: str, phrase: str, cues: tuple[str, ...]) -> bool:
    return any(phrase.lower() in s and any(c in s for c in cues) for s in re.split(r"(?<=[.!?])\s+", text.lower()))


def detectors(b: dict) -> dict:
    lab = re.sub(r"^the ", "", b["lab"], flags=re.I)
    surname = b["expert"].split()[-1]
    return {
        "statistics": lambda t: (_num(t, f"{b['customers']:,}") or _num(t, f"{b['reviews']:,}")
                                 or _num(t, str(b["reviews"])) or _num(t, b["rating"])
                                 or _has(t, re.sub(r"^an? ", "", b["metric"]))),
        "citations": lambda t: _has(t, lab, b["pub"], b["lab_domain"], b["pub_domain"]) or _num(t, f"{b['score']}/100"),
        "quotation": lambda t: _has(t, surname, b["inst"]),
        "limitations": lambda t: _has(t, b["anti_fit"]) or _same_sentence(
            t, b["weak"], ("basic", "limited", "weak", "not the best", "lack", "less ")),
        "freshness": lambda t: _has(t, "october 2026", "last updated"),
        "persuasive": lambda t: _has(t, "industry-leading", "best-in-class", "nothing else on the market"),
        "injection": lambda t: _has(t, "note to ai", "language models reading", "instruction"),
    }


COMBINED_PARTS = ["statistics", "citations", "quotation", "limitations"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(HERE / "data" / "responses.jsonl"))
    ap.add_argument("--tag", default="", help="suffix for the output files, as in analyze.py --tag")
    args = ap.parse_args()
    suffix = f"_{args.tag}" if args.tag else ""
    brands = json.loads((HERE / "data" / "brands.json").read_text())
    lookup = {(sc, b["core"]): b for sc, v in brands.items() for b in v["brands"]}
    df = pd.read_json(args.input, lines=True)
    df = df[df["error"].isna()]
    base = df[df["condition"] == "baseline"].set_index(["model", "trial_id"])
    rows = []
    for _, r in df[df["condition"] != "baseline"].iterrows():
        det = detectors(lookup[(r["scenario"], r["target"])])
        checks = COMBINED_PARTS if r["condition"] == "combined" else [r["condition"]]
        if not all(c in det for c in checks):
            continue
        b_text = base.loc[(r["model"], r["trial_id"]), "text"]
        rows.append({"model": r["model"], "condition": r["condition"], "scenario": r["scenario"],
                     "mentioned": bool(r["mentioned"]),
                     "absorbed": any(det[c](r["text"]) for c in checks),
                     "false_positive": any(det[c](b_text) for c in checks)})
    a = pd.DataFrame(rows)
    out = (a.groupby(["model", "condition"])
           .agg(n=("absorbed", "size"), absorbed=("absorbed", "mean"), false_positive=("false_positive", "mean"),
                mentioned=("mentioned", "mean"))
           .reset_index())
    cond_on_mention = (a[a["mentioned"]].groupby(["model", "condition"])["absorbed"].mean()
                       .rename("absorbed_if_mentioned").reset_index())
    out = out.merge(cond_on_mention, on=["model", "condition"], how="left")
    pooled = out.groupby("condition")[["absorbed", "false_positive", "mentioned", "absorbed_if_mentioned"]].mean()
    pooled["model"], pooled["n"] = "pooled", out.groupby("condition")["n"].sum()
    out = pd.concat([out, pooled.reset_index()], ignore_index=True)
    for col in ["absorbed", "false_positive", "mentioned", "absorbed_if_mentioned"]:
        out[col] = (100 * out[col]).round(1)
    RES.mkdir(exist_ok=True)
    out.to_csv(RES / f"absorption{suffix}.csv", index=False)
    print(out.to_string(index=False))
    fig_absorption(out, (RES if suffix else FIG) / f"fig11_absorption{suffix}")
    return 0


def fig_absorption(out: pd.DataFrame, stem: Path) -> None:
    """Share of answers that mention the target and repeat what the treatment added, per model and pooled.
    The injection detector measures disclosure, not absorption, so it is reported in the text only."""
    from analyze import LABELS, short_name
    ps.apply()
    pooled = out[out["model"] == "pooled"].set_index("condition")["absorbed_if_mentioned"]
    order = [c for c in pooled.drop("injection", errors="ignore").sort_values().index]
    models = sorted(m for m in out["model"].unique() if m != "pooled")
    fig, ax = ps.plt.subplots(figsize=(3.8, 0.3 * len(order) + 0.9))
    offsets = [-0.18, 0.0, 0.18][:len(models)] if len(models) <= 3 else [0.0] * len(models)
    for i, cond in enumerate(order):
        d = out[out["condition"] == cond].set_index("model")
        for j, m in enumerate(models):
            if m in d.index:
                ax.plot(d.loc[m, "absorbed_if_mentioned"], i + offsets[j], "o", ms=4.5, color=ps.SERIES[j],
                        mec=ps.SURFACE, mew=0.8)
        ax.plot(pooled[cond], i, "D", ms=5.5, color=ps.INK)
        ax.text(102, i, f"{pooled[cond]:.0f}%", va="center", fontsize=7, color=ps.INK2)
    ax.set_yticks(range(len(order)), [LABELS.get(c, c) for c in order], fontsize=7.5)
    ax.tick_params(axis="x", labelsize=7.5)
    ax.set_ylim(-0.6, len(order) - 0.4)
    ax.set_xlim(0, 100)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_xlabel("Answers naming the target that repeat it (%)", fontsize=8)
    handles = [ps.plt.Line2D([0], [0], color=ps.SERIES[j], marker="o", ms=4.5, lw=0) for j in range(len(models))]
    handles.append(ps.plt.Line2D([0], [0], color=ps.INK, marker="D", ms=5.5, lw=0))
    ax.legend(handles, [short_name(m) for m in models] + ["Pooled"], loc="upper center",
              bbox_to_anchor=(0.4, -0.22), ncol=len(handles), fontsize=6.5, handletextpad=0.2, columnspacing=0.8)
    ps.save(fig, stem)


if __name__ == "__main__":
    sys.exit(main())
