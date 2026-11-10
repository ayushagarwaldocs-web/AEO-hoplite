"""Macros and the results table for the dated attribution follow-up (specified 10 November 2026)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
E2 = ROOT / "experiments/exp2_content_treatments"
PAPER = ROOT / "paper"
CONTRASTS = [("self_recommendation", "Rec", "Recommending vs neutral wording, brand as source"),
             ("external_attribution", "Ext", "Outside reviewer vs brand, recommending wording"),
             ("attribution_by_recommendation", "Int", "Difference between the two sources' wording effects")]
WORDS = ["none", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]


def _p(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def _available() -> bool:
    return all((E2 / "results" / f).exists() for f in
               ("attribution_effects.csv", "attribution_summary.json", "attribution_extra.json"))


def _effects() -> pd.DataFrame:
    return pd.read_csv(E2 / "results/attribution_effects.csv")


def attribution_macros() -> dict:
    if not _available():
        return {"AttrDone": 0}
    eff = _effects()
    summary = json.loads((E2 / "results/attribution_summary.json").read_text())
    extra = json.loads((E2 / "results/attribution_extra.json").read_text())
    records = [json.loads(line) for line in (E2 / "data/responses_bedrock_attribution.jsonl").open() if line.strip()]
    failed = [r for r in records if r.get("error")]
    excluded = [m for m, v in summary["completeness"].items() if not v["eligible"]]
    out = {"AttrDone": 1, "AttrNModels": len(extra["eligible_models"]), "AttrNModelsW": WORDS[len(extra["eligible_models"])],
           "AttrNRows": f"{len(records):,}".replace(",", "{,}"), "AttrMinTrials": summary["minimum_complete_trials"],
           "AttrNFailed": len(failed), "AttrNFailedW": WORDS[len(failed)] if len(failed) < len(WORDS) else str(len(failed)),
           "AttrNFailedExcluded": sum(1 for r in failed if r["model"] in excluded),
           "AttrNFailedExcludedW": WORDS[sum(1 for r in failed if r["model"] in excluded)]}
    for outcome, prefix in [("mentioned", "Attr"), ("top_pick", "AttrTop"), ("cited", "AttrCit")]:
        for weighting, tag in [("equal_model", ""), ("equal_developer", "Dev")]:
            for contrast, code, _ in CONTRASTS:
                r = eff[(eff.outcome == outcome) & (eff.weighting == weighting) & (eff.contrast == contrast)].iloc[0]
                name = f"{prefix}{tag}{code}"
                out[name] = f"{100 * r['effect']:+.1f}"
                out[name + "U"] = f"{abs(100 * r['effect']):.1f}"
                out[name + "CI"] = f"[{100 * r['ci_low']:.1f}, {100 * r['ci_high']:.1f}]"
                out[name + "P"] = _p(r["p_holm"])
        for arm, code in [("attr_S0", "SZero"), ("attr_S1", "SOne"), ("attr_Q0", "QZero"), ("attr_Q1", "QOne")]:
            r = eff[(eff.outcome == outcome) & (eff.weighting == "equal_model") & (eff.contrast == f"{arm}_vs_B")].iloc[0]
            out[f"{prefix}{code}VB"] = f"{100 * r['effect']:+.1f}"
            out[f"{prefix}{code}VBU"] = f"{abs(100 * r['effect']):.1f}"
    base = extra["baseline_reproduction"]
    out.update({"AttrBaseNew": f"{100 * base['fresh_mention_rate']:.1f}",
                "AttrBaseOld": f"{100 * base['original_mention_rate']:.1f}",
                "AttrBaseAgree": f"{100 * base['same_outcome_share']:.1f}",
                "AttrBasePairs": base["pairs"],
                "AttrBaseMaxDiff": f"{100 * base['max_abs_model_rate_difference']:.1f}"})
    rates = extra["equal_model_mention_rate_by_arm"]
    for arm, code in [("attr_B", "B"), ("attr_S0", "SZero"), ("attr_S1", "SOne"), ("attr_Q0", "QZero"),
                      ("attr_Q1", "QOne")]:
        out[f"AttrRate{code}"] = f"{100 * rates[arm]:.1f}"
    out["AttrBlocks"] = extra["complete_blocks"]
    out["AttrNTruncatedW"] = WORDS[len(extra["truncated_successful_answers"])]
    cons = extra["model_consistency"]
    out.update({"AttrRecPos": cons["recommendation_positive"], "AttrExtPos": cons["external_positive"],
                "AttrExtPosW": WORDS[cons["external_positive"]], "AttrExtZero": cons["external_zero"]})
    ceiling = extra["self_recommendation_mention_rate"]
    out.update({"AttrSOneMin": f"{100 * ceiling['min']:.0f}", "AttrSOneMax": f"{100 * ceiling['max']:.0f}",
                "AttrSOneMedian": f"{100 * ceiling['median']:.0f}", "AttrSOneHigh": ceiling["models_at_or_above_85pct"],
                "AttrSOneHighW": WORDS[ceiling["models_at_or_above_85pct"]]})
    return out


OUTCOME_GROUPS = [("mentioned", "Target mentioned (primary)"), ("top_pick", "Named first (secondary)"),
                  ("cited", "Target page cited (secondary)")]


def _effects_table(eff: pd.DataFrame, contrasts: list) -> str:
    """Equal-model effects in points, one row per contrast, grouped by outcome; Holm within each outcome."""
    lines = []
    for outcome, title in OUTCOME_GROUPS:
        lines.append(f"\\multicolumn{{4}}{{@{{}}l}}{{\\emph{{{title}}}}} \\\\")
        for contrast, _, label in contrasts:
            r = eff[(eff.outcome == outcome) & (eff.weighting == "equal_model") & (eff.contrast == contrast)].iloc[0]
            star = "$^{*}$" if r["p_holm"] < 0.05 else ""
            lo, hi = (f"{100 * r[k]:.1f}".replace("-0.0", "0.0") for k in ("ci_low", "ci_high"))
            lines.append(f"\\quad {label} & ${100 * r['effect']:+.1f}${star} & $[{lo}, {hi}]$ & {_p(r['p_holm'])} \\\\")
    return ("% Generated by make_numbers.py; do not edit.\n"
            "\\begin{tabular}{@{}lrrr@{}}\n\\toprule\n"
            "Contrast & Effect & 95\\% CI & Holm $p$ \\\\\n\\midrule\n"
            + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")


def write_attribution_table() -> None:
    if not _available():
        return
    (PAPER / "table_attribution.tex").write_text(_effects_table(_effects(), CONTRASTS))


# ---------------------------------------------------------------------------------------------------------------------
# Separate-site follow-up (specified and frozen on 10 November 2026; run after the attribution follow-up).

SITE_CONTRASTS = [("site_recommending", "Rec", "Recommending sentence on the guide vs the brand page"),
                  ("site_neutral", "Neu", "Neutral sentence on the guide vs the brand page"),
                  ("site_by_wording", "Int", "Difference between the two pages' wording effects")]


def _site_available() -> bool:
    return all((E2 / "results" / f).exists() for f in ("site_effects.csv", "site_summary.json", "site_extra.json"))


def site_macros() -> dict:
    if not _site_available():
        return {"SiteDone": 0}
    eff = pd.read_csv(E2 / "results/site_effects.csv")
    summary = json.loads((E2 / "results/site_summary.json").read_text())
    extra = json.loads((E2 / "results/site_extra.json").read_text())
    n = len(extra["eligible_models"])
    out = {"SiteDone": 1, "SiteNModels": n, "SiteNModelsW": WORDS[n], "SiteNRows": f"{extra['rows']:,}".replace(",", "{,}"),
           "SiteNFailed": extra["failed_calls"],
           "SiteNFailedW": WORDS[extra["failed_calls"]] if extra["failed_calls"] < len(WORDS) else str(extra["failed_calls"]),
           "SiteBlocks": f"{extra['complete_blocks']:,}".replace(",", "{,}"), "SiteMinTrials": summary["minimum_complete_trials"],
           "SiteNTruncated": len(extra["truncated_successful_answers"])}
    for outcome, prefix in [("mentioned", "Site"), ("top_pick", "SiteTop"), ("cited", "SiteCit")]:
        for weighting, tag in [("equal_model", ""), ("equal_developer", "Dev")]:
            for contrast, code, _ in SITE_CONTRASTS:
                r = eff[(eff.outcome == outcome) & (eff.weighting == weighting) & (eff.contrast == contrast)].iloc[0]
                name = f"{prefix}{tag}{code}"
                out[name] = f"{100 * r['effect']:+.1f}"
                out[name + "U"] = f"{abs(100 * r['effect']):.1f}"
                out[name + "CI"] = f"[{100 * r['ci_low']:.1f}, {100 * r['ci_high']:.1f}]"
                out[name + "P"] = _p(r["p_holm"])
    for arm, code in [("site_B", "B"), ("site_Q0", "QZero"), ("site_Q1", "QOne"), ("site_T0", "TZero"), ("site_T1", "TOne")]:
        out[f"SiteRate{code}"] = f"{100 * extra['equal_model_mention_rate_by_arm'][arm]:.1f}"
        out[f"SiteGuideCit{code}"] = f"{100 * extra['guide_citation_rate_by_arm'][arm]:.1f}"
        out[f"SiteBothCit{code}"] = f"{100 * extra['both_pages_cited_rate_by_arm'][arm]:.1f}"
    arm_rates = extra["equal_model_mention_rate_by_arm"]
    out["SiteWordQ"] = f"{100 * (arm_rates['site_Q1'] - arm_rates['site_Q0']):.1f}"
    out["SiteWordT"] = f"{100 * (arm_rates['site_T1'] - arm_rates['site_T0']):.1f}"
    across = extra["identical_arms_across_runs"]
    out.update({"SiteAcrossN": len(across["models"]), "SiteAcrossNW": WORDS[len(across["models"])]})
    for arm, code in [("site_B", "B"), ("site_Q0", "QZero"), ("site_Q1", "QOne")]:
        out[f"SiteAcross{code}"] = f"{100 * across['site'][arm]:.1f}"
        out[f"SiteEarlier{code}"] = f"{100 * across['attribution'][arm]:.1f}"
    base = extra["baseline_reproduction"]
    out.update({"SiteBaseNew": f"{100 * base['fresh_mention_rate']:.1f}",
                "SiteBaseOld": f"{100 * base['original_mention_rate']:.1f}",
                "SiteBaseAgree": f"{100 * base['same_outcome_share']:.1f}",
                "SiteBasePairs": f"{base['pairs']:,}".replace(",", "{,}"),
                "SiteBaseMaxDiff": f"{100 * base['max_abs_model_rate_difference']:.1f}"})
    out.update({"SiteNExcluded": len(extra["excluded_models"]), "SiteNExcludedW": WORDS[len(extra["excluded_models"])],
                "SiteNFailedExcluded": extra["failed_in_excluded_models"]})
    signs = extra["model_signs"]
    out.update({"SiteRecPos": signs["recommending_positive"], "SiteRecNeg": signs["recommending_negative"],
                "SiteNeuPos": signs["neutral_positive"], "SiteNeuNeg": signs["neutral_negative"]})
    return out


def write_site_table() -> None:
    if not _site_available():
        return
    (PAPER / "table_site.tex").write_text(_effects_table(pd.read_csv(E2 / "results/site_effects.csv"), SITE_CONTRASTS))
