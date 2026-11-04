"""Check the qualitative statements in the Study 2 text against the results.

    python check_claims.py [--tag interim]

Each line is a claim the prose makes; a FAIL means the wording must change.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

E2 = Path(__file__).resolve().parents[1] / "experiments" / "exp2_content_treatments" / "results"
LEGIT = ["statistics", "citations", "quotation", "answer_first", "qa_format", "spec_table", "limitations",
         "freshness", "third_party", "persuasive", "keyword_stuffing", "combined"]
ON_PAGE = [c for c in LEGIT if c != "third_party"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    sfx = f"_{ap.parse_args().tag}" if ap.parse_args().tag else ""
    eff = pd.read_csv(E2 / f"effects{sfx}.csv")
    plc = pd.read_csv(E2 / f"effects_vs_placebo{sfx}.csv")
    h = json.loads((E2 / f"hypotheses{sfx}.json").read_text())
    ab = pd.read_csv(E2 / f"absorption{sfx}.csv")
    pooled = lambda frame, o="mentioned": frame[(frame["model"] == "pooled") & (frame["outcome"] == o)].set_index("condition")  # noqa: E731
    m, t, pm = pooled(eff), pooled(eff, "top_pick"), pooled(plc)
    sig = lambda c, f=m: f.loc[c, "p_holm"] < 0.05  # noqa: E731
    pos = lambda c, f=m: f.loc[c, "effect"] > 0  # noqa: E731
    per_model = eff[(eff["outcome"] == "mentioned") & (eff["model"] != "pooled")]
    pi = h["position_interaction"]
    base_rates = {k: v["mention"] for k, v in h["profiles"].items()}
    best = per_model[per_model["condition"].isin(ON_PAGE)].groupby("model")["effect"].max() * 100
    prof = {k.split(":")[-1].split("-")[0].lower(): v for k, v in h["profiles"].items()}
    by5 = {k.split(":")[-1].split("-")[0].lower(): v for k, v in h["H5"]["by_model"].items()}
    pim = {k.split(":")[-1].split("-")[0].lower(): v for k, v in pi["by_model"].items()}
    pm_model = lambda mod, c, f=per_model: f[(f["model"].str.lower().str.contains(mod)) & (f["condition"] == c)].iloc[0]  # noqa: E731
    top_model = eff[(eff["outcome"] == "top_pick") & (eff["model"] != "pooled")]
    first_last = lambda r: (r[min(r, key=int)], r[max(r, key=int)])  # noqa: E731
    absorb = ab[ab["model"] == "pooled"].set_index("condition")["absorbed_if_mentioned"]
    eff_m = per_model.pivot(index="condition", columns="model", values="effect")
    granite_col = [c for c in eff_m.columns if "granite" in c.lower()][0]
    single = ["statistics", "citations", "quotation", "answer_first", "qa_format", "spec_table", "limitations",
              "freshness", "persuasive", "keyword_stuffing"]
    top_sig = {c for c in single if sig(c, t) and pos(c, t)}
    claims = {
        # Baselines
        "Llama and Granite name the same median number of brands": prof["llama"]["median_brands"] == prof["granite"]["median_brands"],
        "Qwen usually names one brand": prof["qwen2.5"]["median_brands"] == 1,
        # Endorsement and page edits
        "third_party has the largest mention effect of the legitimate edits": m.loc[LEGIT, "effect"].idxmax() == "third_party",
        "third_party significant (pooled, mentions)": sig("third_party"),
        "combined significant and positive": sig("combined") and pos("combined"),
        "no single edit significant on mentions (Holm)": not any(sig(c) and pos(c) for c in single),
        "statistics and citations raise mentions (uncorrected CI above zero)": all(m.loc[c, "ci_low"] > 0 for c in ["statistics", "citations"]),
        "keyword stuffing raises mentions less than statistics and citations, by 0-6 points": all(0 < m.loc[c, "effect"] - m.loc["keyword_stuffing", "effect"] < 0.06 for c in ["statistics", "citations"]),
        "keyword stuffing beats placebo (Holm)": sig("keyword_stuffing", pm) and pos("keyword_stuffing", pm),
        "top pick raised (Holm) by exactly stats, citations, quotation, answer_first, spec_table, persuasive, keywords": top_sig == {"statistics", "citations", "quotation", "answer_first", "spec_table", "persuasive", "keyword_stuffing"},
        "keyword stuffing has the largest top-pick effect of the single edits": t.loc[single, "effect"].idxmax() == "keyword_stuffing",
        "qa_format, freshness, limitations do nothing (mentions and top pick)": not any((sig(c) and pos(c)) or (sig(c, t) and pos(c, t)) for c in ["qa_format", "freshness", "limitations"]),
        "placebo not significant, estimate negative": not sig("filler") and m.loc["filler", "effect"] < 0,
        # Hypotheses
        "H1 none supported": not any(v["supported"] for v in h["H1"].values()),
        "H1: statistics, citations, quotation all beat placebo, none beats baseline (Holm)": all(v["p_placebo"] < 0.05 and v["p_baseline"] >= 0.05 for v in h["H1"].values()),
        "H2 supported": h["H2"]["supported"],
        "H3 holds for mentions, both raise top pick": h["H3"]["keyword_stuffing"]["supported"] and h["H3"]["persuasive"]["supported"] and all(sig(c, t) and pos(c, t) for c in ["keyword_stuffing", "persuasive"]),
        "H4: neither freshness nor answer_first significant on mentions": not any(sig(c) for c in ["freshness", "answer_first"]),
        "H4: both 90% intervals extend beyond 5 points": all(v["ci90"][0] < -0.05 or v["ci90"][1] > 0.05 for v in h["H4"].values()),
        "H5: pooled and stratified tests not significant": h["H5"]["p_perm"] >= 0.05 and h["H5"]["stratified"]["p_perm"] >= 0.05,
        "H5: only Llama significant per model, also after Holm over three": [k for k, v in by5.items() if v["p_perm"] < 0.05] == ["llama"] and by5["llama"]["p_perm"] * len(by5) < 0.05,
        "Llama: primacy (first > last), p >= 0.001 so prose writes p =": first_last(by5["llama"]["rates_by_slot"])[0] > first_last(by5["llama"]["rates_by_slot"])[1] and by5["llama"]["p_perm"] >= 0.001,
        # Position x evidence (exploratory)
        "evidence does not offset position (pooled late-minus-early CI includes zero)": pi["late_minus_early"]["ci"][0] <= 0 <= pi["late_minus_early"]["ci"][1],
        # Competition and absorption
        "brands named change by at most 0.25 for every treatment": all(abs(v["n_brands"]["effect"]) <= 0.25 for v in h["competition"].values()),
        "target's share of brand mentions rises for every treatment": all(v["mention_share"]["ci_low"] > 0 for v in h["competition"].values()),
        "evidence repeated far more than persuasive (20+ points)": min(absorb["statistics"], absorb["citations"]) > absorb["persuasive"] + 20,
        "freshness almost never repeated (pooled absorbed < 2%)": ab[(ab["condition"] == "freshness") & (ab["model"] == "pooled")]["absorbed"].iloc[0] < 2,
        "absorption false positives at most 2%": (ab["false_positive"] <= 2).all(),
        "keywords and persuasion move top pick about as much as evidence (within 6)": abs((t.loc["keyword_stuffing", "effect"] + t.loc["persuasive", "effect"]) / 2 - (t.loc["statistics", "effect"] + t.loc["citations", "effect"]) / 2) < 0.06,
        # Hidden instruction
        "injection has the largest pooled mention effect": m["effect"].idxmax() == "injection",
        "injection has the largest pooled top-pick effect": t["effect"].idxmax() == "injection",
        "injection beats every legitimate edit in mentions": m.loc["injection", "effect"] > m.loc[LEGIT, "effect"].max(),
        "injection significant for exactly two models (Llama, Qwen)": [pm_model(x, "injection")["p_holm"] < 0.05 for x in ["llama", "qwen", "granite"]] == [True, True, False],
        "Granite: injection raises top pick (Holm)": pm_model("granite", "injection", top_model)["p_holm"] < 0.05 and pm_model("granite", "injection", top_model)["effect"] > 0,
        # Agreement and model differences
        "cross-model rho at least 0.5": min(v["rho"] for v in h["cross_model_spearman"].values()) >= 0.5,
        "Granite's effect smallest of the three for at least half the treatments": (eff_m.idxmin(axis=1) == granite_col).sum() >= len(eff_m) / 2,
        # Discussion
        "access: every model's baseline rate >= its best on-page edit": all(base_rates[k] >= best[k] for k in best.index),
        "quotation, persuasive, keyword stuffing not significant on mentions": not any(sig(c) for c in ["quotation", "persuasive", "keyword_stuffing"]),
    }
    for k, v in claims.items():
        print(f"{'ok  ' if v else 'FAIL'}  {k}")
    return 0 if all(claims.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
