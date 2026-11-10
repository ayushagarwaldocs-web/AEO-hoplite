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


def _sentence_parts(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _brand_in_sentence(sentence: str, brand: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(brand)}(?!\w)", sentence, flags=re.I))


def _target_attributed(text: str, target: str, phrase: str, cues: tuple[str, ...] = (),
                       other_brands: tuple[str, ...] = ()) -> bool:
    """Require same-sentence target attribution or an unambiguous adjacent continuation."""
    sentences = _sentence_parts(text)
    for i, sentence in enumerate(sentences):
        low = sentence.lower()
        if phrase.lower() not in low or (cues and not any(cue in low for cue in cues)):
            continue
        if _brand_in_sentence(sentence, target):
            return True
        has_competitor = any(_brand_in_sentence(sentence, name) for name in other_brands if name != target)
        if i and not has_competitor and _brand_in_sentence(sentences[i - 1], target):
            previous_has_competitor = any(_brand_in_sentence(sentences[i - 1], name)
                                           for name in other_brands if name != target)
            if not previous_has_competitor:
                return True
    return False


def detectors(b: dict, other_brands: tuple[str, ...] = ()) -> dict:
    """Detect treatment content; limitation signals must be attributable to the target brand."""
    lab = re.sub(r"^the ", "", b["lab"], flags=re.I)
    surname = b["expert"].split()[-1]
    return {
        "statistics": lambda t: (_num(t, f"{b['customers']:,}") or _num(t, f"{b['reviews']:,}")
                                 or _num(t, str(b["reviews"])) or _num(t, b["rating"])
                                 or _has(t, re.sub(r"^an? ", "", b["metric"]))),
        "citations": lambda t: _has(t, lab, b["pub"], b["lab_domain"], b["pub_domain"]) or _num(t, f"{b['score']}/100"),
        "quotation": lambda t: _has(t, surname, b["inst"]),
        "limitations": lambda t: _target_attributed(t, b["core"], b["anti_fit"], other_brands=other_brands)
        or _target_attributed(t, b["core"], b["weak"],
                              ("basic", "limited", "weak", "not the best", "lack", "less "), other_brands),
        "freshness": lambda t: _has(t, "october 2026", "last updated"),
        "persuasive": lambda t: _has(t, "industry-leading", "best-in-class", "nothing else on the market"),
        "injection": lambda t: _has(t, "note to ai", "language models reading", "instruction"),
    }


COMBINED_PARTS = ["statistics", "citations", "quotation", "limitations"]


def summary_table(a: pd.DataFrame) -> pd.DataFrame:
    """Return unconditional detector rates and mention-conditional rates with denominators."""
    out = (a.groupby(["model", "condition"])
           .agg(n=("absorbed", "size"), n_absorbed=("absorbed", "sum"),
                n_mentioned=("mentioned", "sum"), absorbed=("absorbed", "mean"),
                false_positive=("false_positive", "mean"), mentioned=("mentioned", "mean"))
           .reset_index())
    conditional = (a[a["mentioned"]].groupby(["model", "condition"])
                   .agg(absorbed_if_mentioned=("detected", "mean"),
                        absorbed_if_mentioned_n=("detected", "size")).reset_index())
    out = out.merge(conditional, on=["model", "condition"], how="left")
    pooled = out.groupby("condition").agg(
        n=("n", "sum"), n_absorbed=("n_absorbed", "sum"), n_mentioned=("n_mentioned", "sum"),
        absorbed=("absorbed", "mean"), false_positive=("false_positive", "mean"),
        mentioned=("mentioned", "mean"), absorbed_if_mentioned=("absorbed_if_mentioned", "mean"),
        absorbed_if_mentioned_n=("absorbed_if_mentioned_n", "sum"),
    ).reset_index()
    pooled["model"] = "pooled"
    out = pd.concat([out, pooled], ignore_index=True)
    for col in ["absorbed", "false_positive", "mentioned", "absorbed_if_mentioned"]:
        out[col] = (100 * out[col]).round(1)
    return out


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
        brand = lookup[(r["scenario"], r["target"])]
        siblings = tuple({name for item in brands[r["scenario"]]["brands"] if item["core"] != r["target"]
                          for name in (item["core"], item["name"])})
        det = detectors(brand, siblings)
        checks = COMBINED_PARTS if r["condition"] == "combined" else [r["condition"]]
        if not all(c in det for c in checks) or (r["model"], r["trial_id"]) not in base.index:
            continue  # nothing to detect, or no paired baseline answer (an incomplete run)
        b_text = base.loc[(r["model"], r["trial_id"]), "text"]
        detected = any(det[c](r["text"]) for c in checks)
        rows.append({"model": r["model"], "condition": r["condition"], "scenario": r["scenario"],
                     "mentioned": bool(r["mentioned"]), "detected": detected,
                     "absorbed": detected,
                     "false_positive": any(det[c](b_text) for c in checks)})
    a = pd.DataFrame(rows)
    out = summary_table(a)
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
                ax.plot(d.loc[m, "absorbed_if_mentioned"], i + offsets[j], "o", ms=4.5,
                        color=ps.SERIES[j] if len(models) <= len(ps.SERIES) else "#9a9890", mec=ps.SURFACE, mew=0.8)
        ax.plot(pooled[cond], i, "D", ms=5.5, color=ps.INK)
        ax.text(102, i, f"{pooled[cond]:.0f}%", va="center", fontsize=7, color=ps.INK2)
    ax.set_yticks(range(len(order)), [LABELS.get(c, c) for c in order], fontsize=7.5)
    ax.tick_params(axis="x", labelsize=7.5)
    ax.set_ylim(-0.6, len(order) - 0.4)
    ax.set_xlim(0, 100)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_xlabel("Among target-mentioned answers, treatment signal detected (%)", fontsize=8)
    if len(models) <= len(ps.SERIES):
        handles = [ps.plt.Line2D([0], [0], color=ps.SERIES[j], marker="o", ms=4.5, lw=0) for j in range(len(models))]
        names = [short_name(m) for m in models]
    else:  # too many models to colour: grey dots, one legend entry
        handles, names = [ps.plt.Line2D([0], [0], color="#9a9890", marker="o", ms=4.5, lw=0)], ["Single models"]
    handles.append(ps.plt.Line2D([0], [0], color=ps.INK, marker="D", ms=5.5, lw=0))
    ax.legend(handles, names + ["Pooled"], loc="upper center",
              bbox_to_anchor=(0.4, -0.22), ncol=len(handles), fontsize=6.5, handletextpad=0.2, columnspacing=0.8)
    ps.save(fig, stem)


if __name__ == "__main__":
    sys.exit(main())
