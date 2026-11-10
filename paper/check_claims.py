"""Check the qualitative statements in the Study 2 text against the results.

    python check_claims.py

Hosted models (results/*_bedrock.*) are the main analysis; the small local models (untagged results) are the
comparison. Each line is a claim the prose makes; a FAIL means the wording must change.
"""

from __future__ import annotations

import json
import sys
import numpy as np
from pathlib import Path

import pandas as pd

from revision_checks import revision_claims
from followup_checks import attribution_claims

E2 = Path(__file__).resolve().parents[1] / "experiments" / "exp2_content_treatments" / "results"
LEGIT = ["statistics", "citations", "quotation", "answer_first", "qa_format", "spec_table", "limitations",
         "freshness", "third_party", "persuasive", "keyword_stuffing", "combined"]
ON_PAGE = [c for c in LEGIT if c != "third_party"]
SINGLE = [c for c in ON_PAGE if c != "combined"]


def load(sfx: str):
    eff = pd.read_csv(E2 / f"effects{sfx}.csv")
    plc = pd.read_csv(E2 / f"effects_vs_placebo{sfx}.csv")
    h = json.loads((E2 / f"hypotheses{sfx}.json").read_text())
    ab = pd.read_csv(E2 / f"absorption{sfx}.csv")
    x = pd.read_csv(E2 / f"explore{sfx}.csv")
    return eff, plc, h, ab, x


def pooled(frame, o="mentioned"):
    return frame[(frame["model"] == "pooled") & (frame["outcome"] == o)].set_index("condition")


def usage_weights_checked() -> bool:
    sys.path.insert(0, str(E2.parent))
    from analyze_robustness import ASSISTANTS, assistant_weights
    weights = assistant_weights()
    if not (weights["ChatGPT"] == 0.53 and weights["Gemini"] == 0.275 and np.isclose(sum(weights.values()), 1)):
        return False
    summary = json.loads((E2 / "robustness_summary.json").read_text())["usage_weighted"]
    if not {"ChatGPT", "Gemini"}.issubset(summary["assistants_present"]):
        return False
    frames = [pd.read_json(E2.parent / "data" / f"responses_{tag}.jsonl", lines=True)
              for tag in ("bedrock", "flagship")]
    raw = pd.concat(frames, ignore_index=True)
    raw = raw[raw["error"].isna()]
    model_to = {m: a for a, (_, models) in ASSISTANTS.items() for m in models}
    raw = raw[raw["model"].isin(model_to)].copy()
    raw["assistant"] = raw["model"].map(model_to)
    actual = pd.read_csv(E2 / "usage_weighted.csv")
    for outcome, rows in actual.groupby("outcome"):
        wide = raw.pivot_table(index=["assistant", "model", "scenario", "trial_id"],
                               columns="condition", values=outcome).astype(float)
        for _, row in rows.iterrows():
            diffs = (wide[row["condition"]] - wide["baseline"]).dropna()
            per_a = diffs.groupby(level=["assistant", "scenario", "trial_id"]).mean().reset_index(name="diff")
            per_a["weight"] = per_a["assistant"].map(weights)
            per_a["weighted"] = per_a["diff"] * per_a["weight"]
            per_t = per_a.groupby(["scenario", "trial_id"])[["weighted", "weight"]].sum()
            expected = (per_t["weighted"] / per_t["weight"]).mean()
            if not np.isclose(expected, row["effect"], atol=1e-12):
                return False
    return True


def main() -> int:
    eff, plc, h, ab, x = load("_bedrock")
    s_eff, s_plc, s_h, s_ab, s_x = load("")
    m, t, pm = pooled(eff), pooled(eff, "top_pick"), pooled(plc)
    sm, spm = pooled(s_eff), pooled(s_plc)
    sig = lambda c, f=m: f.loc[c, "p_holm"] < 0.05 and f.loc[c, "effect"] > 0  # noqa: E731
    per = eff[(eff["outcome"] == "mentioned") & (eff["model"] != "pooled")]
    nsig = lambda c: int(((per["condition"] == c) & (per["p_holm"] < 0.05) & (per["effect"] > 0)).sum())  # noqa: E731
    one = lambda key, c: per[per["model"].str.contains(key) & (per["condition"] == c)].iloc[0]  # noqa: E731
    absorb = ab[ab["model"] == "pooled"].set_index("condition")
    s_absorb = s_ab[s_ab["model"] == "pooled"].set_index("condition")
    xp = x[(x["model"] == "pooled") & (x["outcome"] == "mentioned")].set_index(["family", "condition", "reference"])
    s_xp = s_x[(s_x["model"] == "pooled") & (s_x["outcome"] == "mentioned")].set_index(["family", "condition", "reference"])
    wording = xp.loc["wording"]
    xb = xp.loc["vs_baseline"].xs("baseline", level="reference")
    top_sig = {c for c in SINGLE if sig(c, t)}
    base = {k: v["mention"] for k, v in h["profiles"].items()}
    best = per[per["condition"].isin(ON_PAGE)].groupby("model")["effect"].max() * 100
    words = {k: v["median_words"] for k, v in h["profiles"].items()}
    by5 = h["H5"]["by_model"]
    claims = {
        # Baselines
        "Nova Pro has the lowest and Qwen3 Next the highest baseline": min(base, key=base.get).endswith("nova-pro-v1:0") and "qwen3-next" in max(base, key=base.get),
        "Nova Pro shortest, Claude longest answers": "nova-pro" in min(words, key=words.get) and "claude" in max(words, key=words.get),
        # Endorsement
        "third_party largest legitimate mention effect": m.loc[LEGIT, "effect"].idxmax() == "third_party",
        "third_party significant in all 12 models": nsig("third_party") == 12,
        "combined significant": sig("combined"),
        # Evidence
        "stats, citations, quotation beat baseline and placebo (Holm)": all(sig(c) and sig(c, pm) for c in ["statistics", "citations", "quotation"]),
        "citations strongest single edit": m.loc[SINGLE, "effect"].idxmax() == "citations",
        "placebo not significant": not sig("filler"),
        # Emphasis
        "keyword stuffing and persuasive significant": sig("keyword_stuffing") and sig("persuasive"),
        "keyword stuffing about as well as statistics (within 3 points)": abs(m.loc["keyword_stuffing", "effect"] - m.loc["statistics", "effect"]) < 0.03,
        "keyword first-mention effect as large as stats/citations (within 1 point)": all(abs(t.loc["keyword_stuffing", "effect"] - t.loc[c, "effect"]) < 0.01 for c in ["statistics", "citations"]),
        "first-mentioned brand raised by exactly stats, citations, quotation, persuasive, keywords": top_sig == {"statistics", "citations", "quotation", "persuasive", "keyword_stuffing"},
        "answer_first, qa_format, spec_table not significant": not any(m.loc[c, "p_holm"] < 0.05 for c in ["answer_first", "qa_format", "spec_table"]),
        "freshness and limitations about 4 points, not above placebo": all(0.03 < m.loc[c, "effect"] < 0.05 and pm.loc[c, "p_holm"] >= 0.05 for c in ["freshness", "limitations"]),
        # Hypotheses
        "H1 supported": all(v["supported"] for v in h["H1"].values()),
        "H2 supported": h["H2"]["supported"],
        "H3 not supported (both raise mentions)": not h["H3"]["keyword_stuffing"]["supported"] and not h["H3"]["persuasive"]["supported"],
        "H4 supported for answer_first only": h["H4"]["answer_first"]["supported"] and not h["H4"]["freshness"]["supported"],
        "H5 shared-trial pooled and stratified tests not significant": h["H5"]["p_perm"] >= 0.05 and h["H5"]["stratified"]["p_perm"] >= 0.05 and not any(v["p_perm"] < 0.05 for v in by5.values()),
        "H5 descriptive rates: first slot highest, last slot lowest": max(h["H5"]["rates_by_slot"], key=h["H5"]["rates_by_slot"].get) == "1" and min(h["H5"]["rates_by_slot"], key=h["H5"]["rates_by_slot"].get) == "6",
        "evidence not weaker late (late >= early)": h["position_interaction"]["late"]["effect"] >= h["position_interaction"]["early"]["effect"],
        # Competition, absorption
        "brands named change by at most 0.25": all(abs(v["n_brands"]["effect"]) <= 0.25 for v in h["competition"].values()),
        "target's share rises for every treatment": all(v["mention_share"]["ci_low"] > 0 for v in h["competition"].values()),
        "evidence repeated far more than persuasive (30+ points)": min(absorb.loc["statistics", "absorbed_if_mentioned"], absorb.loc["citations", "absorbed_if_mentioned"]) > absorb.loc["persuasive", "absorbed_if_mentioned"] + 30,
        "freshness almost never repeated (< 2%)": absorb.loc["freshness", "absorbed"] < 2,
        "false positives at most 2%": (ab["false_positive"] <= 2).all(),
        # Injection
        "injection largest pooled first-mention effect": t["effect"].idxmax() == "injection",
        "injection significant in 10 models": nsig("injection") == 10,
        "Claude negative and n.s.; MiniMax n.s.": one("claude", "injection")["effect"] < 0 and one("claude", "injection")["p_holm"] >= 0.05 and one("minimax", "injection")["p_holm"] >= 0.05,
        "Claude the only model with a negative injection estimate": (per[per["condition"] == "injection"]["effect"] < 0).sum() == 1,
        "injection rarely disclosed (< 5%)": absorb.loc["injection", "absorbed"] < 5,
        # Agreement
        "median cross-model rho at least 0.7": sorted(v["rho"] for k, v in h["cross_model_spearman"].items() if k.startswith("mentioned"))[33] >= 0.7,
        # Discussion
        # Small models
        "small: endorsement and injection significant": sig("third_party", sm) and sig("injection", sm),
        "small: stats and citations beat placebo, not baseline": all(sig(c, spm) and not sig(c, sm) for c in ["statistics", "citations"]),
        "small: H1 not supported": not any(v["supported"] for v in s_h["H1"].values()),
        "small: placebo negative": sm.loc["filler", "effect"] < 0,
        "small: position only for Llama": [k for k, v in s_h["H5"]["by_model"].items() if v["p_perm"] < 0.05] == [k for k in s_h["H5"]["by_model"] if "Llama" in k],
        "small: evidence repeated far more than persuasive": min(s_absorb.loc["statistics", "absorbed_if_mentioned"], s_absorb.loc["citations", "absorbed_if_mentioned"]) > s_absorb.loc["persuasive", "absorbed_if_mentioned"] + 20,
        "small: evidence effects smaller than hosted": all(sm.loc[c, "effect"] < m.loc[c, "effect"] for c in ["statistics", "citations", "quotation"]),
        # Exploratory
        "mention and shared endorsement significant": all(xp.loc[("vs_baseline", c, "baseline"), "p_holm"] < 0.05 for c in ["third_party_mention", "third_party_shared"]),
        "sole recommendation beats both weaker forms": all(xp.loc[("endorsement", "third_party", r), "ci_low"] > 0 for r in ["third_party_mention", "third_party_shared"]),
        "sole minus mention about equal to mention effect (within 5)": abs(xp.loc[("endorsement", "third_party", "third_party_mention"), "effect"] - xp.loc[("vs_baseline", "third_party_mention", "baseline"), "effect"]) < 0.05,
        "small: same endorsement pattern": all(s_xp.loc[("endorsement", "third_party", r), "ci_low"] > 0 for r in ["third_party_mention", "third_party_shared"]),
        "every second wording significant vs baseline": all(xp.loc[("vs_baseline", f"{c}_b", "baseline"), "p_holm"] < 0.05 and xp.loc[("vs_baseline", f"{c}_b", "baseline"), "effect"] > 0 for c in ["statistics", "citations", "quotation", "persuasive", "keyword_stuffing"]),
        "citations_b strongest second wording": xb.loc[[f"{c}_b" for c in ["statistics", "citations", "quotation", "persuasive", "keyword_stuffing"]], "effect"].idxmax() == "citations_b",
        "every second wording weaker than first": (wording["effect"] < 0).all(),
    }
    claims.update(robustness_claims(m))
    claims.update(agentic_claims())
    claims.update(revision_claims())
    claims.update(attribution_claims())
    for k, v in claims.items():
        print(f"{'ok  ' if v else 'FAIL'}  {k}")
    return 0 if all(claims.values()) else 1


def robustness_claims(m: pd.DataFrame) -> dict:
    """Claims of sec:robust, the abstract, findings, discussion and conclusion about the replication and checks."""
    res = E2
    out = {}
    if (res / "effects_flagship.csv").exists():
        f = pd.read_csv(res / "effects_flagship.csv")
        fp = pd.read_csv(res / "effects_vs_placebo_flagship.csv")
        fm, fpm = pooled(f), pooled(fp)
        fper = f[(f["outcome"] == "mentioned") & (f["model"] != "pooled")]
        fh = json.loads((res / "hypotheses_flagship.json").read_text())
        fab = pd.read_csv(res / "absorption_flagship.csv")
        fab = fab[fab["model"] == "pooled"].set_index("condition")
        fsig = lambda c, fr=fm: fr.loc[c, "p_holm"] < 0.05 and fr.loc[c, "effect"] > 0  # noqa: E731
        fone = lambda key, c: fper[fper["model"].str.contains(key) & (fper["condition"] == c)].iloc[0]  # noqa: E731
        main_per = pd.read_csv(res / "effects_bedrock.csv")
        main_per = main_per[(main_per["outcome"] == "mentioned") & (main_per["model"] != "pooled") & (main_per["condition"] == "injection")]
        rho = fm.loc[LEGIT + ["filler", "injection"], "effect"].corr(m.loc[LEGIT + ["filler", "injection"], "effect"], method="spearman")
        n_inj = int(((fper["condition"] == "injection") & (fper["p_holm"] < 0.05) & (fper["effect"] > 0)).sum()) + \
            int(((main_per["p_holm"] < 0.05) & (main_per["effect"] > 0)).sum())
        n_models = fper["model"].nunique() + main_per["model"].nunique()
        out.update({
            "rep: third_party largest legitimate effect and significant": fm.loc[LEGIT, "effect"].idxmax() == "third_party" and fsig("third_party"),
            "rep: H2 supported": fh["H2"]["supported"],
            "rep: citations and statistics beat baseline and placebo, quotation does not": all(fsig(c) and fsig(c, fpm) for c in ["statistics", "citations"]) and not (fsig("quotation") and fsig("quotation", fpm)),
            "rep: keyword stuffing and persuasive raise mentions (H3 not supported)": fsig("keyword_stuffing") and fsig("persuasive"),
            "rep: H4 holds for both; freshness slightly negative": fh["H4"]["answer_first"]["supported"] and fh["H4"]["freshness"]["supported"] and -5 < fm.loc["freshness", "effect"] < 0,
            "rep: H5 shared-trial pooled not significant; first slot highest descriptively": fh["H5"]["p_perm"] >= 0.05 and max(fh["H5"]["rates_by_slot"], key=fh["H5"]["rates_by_slot"].get) == "1" and fh["H5"]["stratified"]["p_perm"] >= 0.05,
            "rep: ranking agrees with main (rho >= 0.8)": rho >= 0.8,
            "rep: evidence repeated far more than persuasive (30+ points)": min(fab.loc["statistics", "absorbed_if_mentioned"], fab.loc["citations", "absorbed_if_mentioned"]) > fab.loc["persuasive", "absorbed_if_mentioned"] + 30,
            "rep: Claude Opus moves against injection (significant)": fone("opus-4-6", "injection")["effect"] < 0 and fone("opus-4-6", "injection")["p_holm"] < 0.05,
            "rep: Kimi K3.1 Pro injection effect not significant": fone("Kimi-K3.1", "injection")["p_holm"] >= 0.05,
            "rep: Claude Opus persuasive negative but not significant": fone("opus-4-6", "persuasive")["effect"] < 0 and fone("opus-4-6", "persuasive")["p_holm"] >= 0.05,
            "both Claude models negative on injection": fone("opus-4-6", "injection")["effect"] < 0 and main_per[main_per["model"].str.contains("claude")]["effect"].iloc[0] < 0,
            "injection works on most models (main + replication)": n_inj > n_models / 2,
        })
    rpath = res / "robustness_summary.json"
    if rpath.exists():
        s = json.loads(rpath.read_text())
        L = s["long"]
        g = lambda v, ref, c: L[f"{v}|{ref}|{c}"]  # noqa: E731
        lm, la = (lambda c: g("main", "baseline", c)["effect"]), (lambda c: g("long", "baseline", c)["effect"])  # noqa: E731
        ch = L["change"]
        out.update({
            "long: baseline mention barely moves (< 3 points)": abs(L["baseline_mention"]["alt"] - L["baseline_mention"]["main"]) < 3,
            "long: endorsement, citations, statistics, injection fall significantly": all(ch[c]["change"] < 0 and ch[c]["p_holm"] < 0.05 for c in ["third_party", "citations", "statistics", "injection"]),
            "long: endorsement still significant": g("long", "baseline", "third_party")["p_holm"] < 0.05,
            "long: evidence effects about half (ratio 0.3-0.7)": all(0.3 <= la(c) / lm(c) <= 0.7 for c in ["citations", "statistics"]),
            "long: persuasive indistinguishable from zero": g("long", "baseline", "persuasive")["p_holm"] >= 0.05 and abs(la("persuasive")) < 3,
            "long: keyword stuffing rises significantly": ch["keyword_stuffing"]["change"] > 0 and ch["keyword_stuffing"]["p_holm"] < 0.05,
            "long: keyword stuffing about as large as endorsement (within 3 points or larger)": la("keyword_stuffing") > la("third_party") - 3,
            "long: prediction wrong, endorsement changes most among legitimate edits": ch["third_party"]["change"] <= min(ch[c]["change"] for c in ["statistics", "citations", "quotation"]),
        })
        T = s["temp1"]
        tch = T["change"]
        t_main_sig = [c for c in tch if T[f"main|baseline|{c}"]["p_holm"] < 0.05 and T[f"main|baseline|{c}"]["effect"] > 0]
        out.update({
            "temp: every treatment that raised mentions still does": all(T[f"temp1|baseline|{c}"]["p_holm"] < 0.05 and T[f"temp1|baseline|{c}"]["effect"] > 0 for c in t_main_sig),
            "temp: no change survives correction": all(v["p_holm"] >= 0.05 for v in tch.values()),
            "temp: largest change is citations": min(tch, key=lambda c: -abs(tch[c]["change"])) == "citations",
        })
    jpath = res / "absorption_judge.csv"
    if jpath.exists():
        j = pd.read_csv(jpath)
        jj = lambda c: j[j["condition"] == c].set_index("judge")  # noqa: E731
        out.update({
            "judge: detector never fires on baseline answers": (j["fp_detector"] == 0).all(),
            "judge: judges find more limitations than the detector": (jj("limitations")["judge_rate"] > jj("limitations")["detector_rate"]).all(),
            "judge: evidence repeated far more than persuasive under both judges": all(min(jj("statistics").loc[x, "judge_rate"], jj("citations").loc[x, "judge_rate"]) > jj("persuasive").loc[x, "judge_rate"] + 30 for x in j["judge"].unique()),
            "judge: quotation false positives high (> 20%)": (jj("quotation")["fp_judge"] > 20).all(),
        })
    upath = res / "usage_weighted.csv"
    if upath.exists():
        u = pd.read_csv(upath)
        u = u[u["outcome"] == "mentioned"].set_index("condition")
        out.update({
            "usage: third_party largest legitimate": u.loc[LEGIT, "effect"].idxmax() == "third_party",
            "usage: endorsement, citations, statistics, keywords and persuasive significant": all(u.loc[c, "p_holm"] < 0.05 and u.loc[c, "effect"] > 0 for c in ["third_party", "citations", "statistics", "keyword_stuffing", "persuasive"]),
            "usage: ChatGPT/Gemini shares and weighted estimates match the specified calculation": usage_weights_checked(),
        })
    apath = res / "audit_summary.json"
    if apath.exists():
        a = json.loads(apath.read_text())
        p, g = a["perplexity"], a["gemini"]
        out.update({
            "audit: third parties hold most Perplexity citations": p["vendor_pct"] < 50,
            "audit: vendors hold most citations in only a few questions": p["questions_vendor_majority"] <= 3,
            "audit: Gemini vendors exactly half, not a third-party majority": g["vendor_pct"] == 50,
            "audit: about a fifth of Perplexity citations blocked for PerplexityBot (15-25%)": 15 <= 100 * p["robots"]["pplx_blocked"] / p["robots"]["checked"] <= 25,
            "audit: almost all blocks name PerplexityBot": p["robots"]["pplx_blocked_named"] >= p["robots"]["pplx_blocked"] - 2,
        })
        c = a.get("chatgpt")
        if c:
            out.update({
                "audit: ChatGPT displayed no text search or source citations": c["with_cited_sources"] == 0 and c["searched"] == 0,
                "audit: ChatGPT linked brands' own sites in about half the answers (10-14)": 10 <= c["with_product_links"] <= 14,
            })
    if (res / "effects_flagship.csv").exists():
        f = pd.read_csv(res / "effects_flagship.csv")
        b = pd.read_csv(res / "baseline_rates_flagship.csv").set_index("model")
        legit = ["statistics", "citations", "quotation", "answer_first", "qa_format", "spec_table", "limitations",
                 "freshness", "third_party", "persuasive", "keyword_stuffing"]
        g6 = f[(f.outcome == "mentioned") & (f.model == "openai:gpt-6.1-sol")].set_index("condition")
        s5 = f[(f.outcome == "mentioned") & (f.model == "anthropic:claude-sonnet-5-5")]
        out.update({
            "rep: GPT-6.1 Sol's largest legitimate effect is endorsement, significant": g6.loc[legit, "effect"].idxmax() == "third_party" and g6.loc["third_party", "p_holm"] < 0.05,
            "rep: Claude Sonnet 5.5 at ceiling (>= 90% baseline) and no significant mention effect": b.loc["anthropic:claude-sonnet-5-5", "mentioned"] >= 0.9 and (s5["p_holm"] >= 0.05).all(),
        })
    cf, cm = res / "injection_callouts_flagship.json", res / "injection_callouts_bedrock.json"
    if cf.exists() and cm.exists():
        sf, sm = json.loads(cf.read_text()), json.loads(cm.read_text())
        df_ = pd.read_csv(res / "injection_callouts_flagship.csv")
        dm_ = pd.read_csv(res / "injection_callouts_bedrock.csv")
        g = lambda d, oc, sc, mo: d[(d.outcome == oc) & (d.scoring == sc) & (d.model == mo)].iloc[0]  # noqa: E731
        son, s46 = "anthropic:claude-sonnet-5-5", "bedrock:global.anthropic.claude-sonnet-4-6"
        out.update({
            "callouts: Sonnet 5.5 calls out the instruction in most answers (> 80%)": sf["callout_rate_injection"][son] > 0.8,
            "callouts: Sonnet 5.5 first-mention effect is an artifact (raw > 40, clean < 5)": g(df_, "top_pick", "as scored", son)["effect"] > 0.4 and g(df_, "top_pick", "call-outs removed", son)["effect"] < 0.05,
            "callouts: replication count of models following the instruction unchanged on mentions": sf["as scored|mentioned|n_sig_positive"] == sf["call-outs removed|mentioned|n_sig_positive"],
            "callouts: main count drops by one; Sonnet 4.6 significantly negative once cleaned": sm["as scored|mentioned|n_sig_positive"] - sm["call-outs removed|mentioned|n_sig_positive"] == 1 and g(dm_, "mentioned", "call-outs removed", s46)["p_holm"] < 0.05 and g(dm_, "mentioned", "call-outs removed", s46)["effect"] < 0,
            "callouts: pooled effects change by under 2 points on mentions": abs(g(df_, "mentioned", "as scored", "pooled")["effect"] - g(df_, "mentioned", "call-outs removed", "pooled")["effect"]) < 0.02 and abs(g(dm_, "mentioned", "as scored", "pooled")["effect"] - g(dm_, "mentioned", "call-outs removed", "pooled")["effect"]) < 0.02,
        })
    mp = res / "mde_summary.json"
    if mp.exists():
        s = json.loads(mp.read_text())["bedrock"]
        out["mde: pooled about 3-6 points, single model about 10-16"] = 3 <= s["pooled_mde80_median"] <= 6 and 10 <= s["per_model_mde80_median"] <= 16
    return out


def agentic_claims() -> dict:
    """Claims about the agentic search design (sec:agentic, abstract, findings, discussion, conclusion)."""
    res = E2
    if not (res / "agentic_summary.json").exists():
        return {}
    s = json.loads((res / "agentic_summary.json").read_text())
    e = pd.read_csv(res / "agentic_effects.csv")
    v = pd.read_csv(res / "agentic_vs_context.csv")
    fq = pd.read_csv(res / "agentic_fixed_queries.csv")
    P = lambda oc: e[(e["outcome"] == oc) & (e["model"] == "pooled")].set_index("condition")  # noqa: E731
    men, top, surf, opn = P("mentioned"), P("top_pick"), P("surfaced"), P("opened")
    vm = v[(v["model"] == "pooled") & (v["outcome"] == "mentioned")].set_index("condition")
    fqp = fq[fq["model"] == "pooled"].set_index("condition")
    sig = lambda f, c: f.loc[c, "p_holm"] < 0.05 and f.loc[c, "effect"] > 0  # noqa: E731
    M = s["models"]
    sol, mini, mai, ds = (M[k] for k in ("openai:gpt-6.1-sol", "azure:gpt-5-mini", "azure:MAI-Thinking-1",
                                         "azure:DeepSeek-V4-Pro"))
    legit = ["third_party", "citations", "statistics", "answer_first", "keyword_stuffing"]
    by_open = s["mentioned_by_opened"]["baseline"]
    return {
        "ag: all four models pooled (>= 60 complete trials)": len(s["pooled_models"]) == 4,
        "ag: GPT-5 mini searched more and opened fewer than GPT-6.1 Sol": mini["searches"] > sol["searches"] and mini["opens"] < sol["opens"],
        "ag: DeepSeek searched and opened the most": ds["searches"] == max(d["searches"] for d in M.values()) and ds["opens"] == max(d["opens"] for d in M.values()),
        "ag: every MAI no-search answer cited unseen pages": mai["fabricated_no_search"] == 1.0,
        "ag: baseline mention far below in-context (at least 20 points)": s["pooled_baseline_in_context"] - s["pooled_baseline"]["mentioned"] >= 0.20,
        "ag: target page seldom opened at baseline (< 20%)": s["pooled_baseline"]["opened"] < 0.20,
        "ag: descriptive equal-model mentions > 80% if opened, < 15% if not": by_open["1"] > 0.8 and by_open["0"] < 0.15,
        "ag: citations, statistics, injection no longer raise mentions": not any(sig(men, c) for c in ["citations", "statistics", "injection"]),
        "ag: P4 citations/statistics/injection smaller than in context, p < 0.001": all(vm.loc[c, "difference"] < 0 and vm.loc[c, "p"] < 0.001 for c in ["citations", "statistics", "injection"]),
        "ag: P5 fails (injection not significant)": not sig(men, "injection"),
        "ag: P2 stuffing raises surfaced and opened; citations, statistics raise neither": sig(surf, "keyword_stuffing") and sig(opn, "keyword_stuffing") and not any(sig(f, c) for f in (surf, opn) for c in ["citations", "statistics"]),
        "ag: P3 answer-first raises surfaced": sig(surf, "answer_first"),
        "ag: fixed queries: stuffing and summary raise top-five rate, citations and statistics do not": sig(fqp, "keyword_stuffing") and sig(fqp, "answer_first") and not sig(fqp, "citations") and not sig(fqp, "statistics"),
        "ag: stuffing and summary raise mentions (significant)": sig(men, "keyword_stuffing") and sig(men, "answer_first"),
        "ag: stuffing and summary at least as large as in context, difference n.s.": all(vm.loc[c, "difference"] >= 0 and vm.loc[c, "p"] >= 0.05 for c in ["keyword_stuffing", "answer_first"]),
        "ag: endorsement raises mentions and first-mentioned brand (significant)": sig(men, "third_party") and sig(top, "third_party"),
        "ag: endorsement the only significant first-mention effect": [c for c in top.index if sig(top, c)] == ["third_party"],
        "ag: endorsement smaller than in context (significant)": vm.loc["third_party", "difference"] < 0 and vm.loc["third_party", "p"] < 0.05,
        "ag: stuffing vs endorsement: no difference on mentions, endorsement better on first-mentioned brand": s["stuffing_minus_endorsement_mentioned"]["p"] >= 0.05 and s["stuffing_minus_endorsement_top_pick"]["effect"] < 0 and s["stuffing_minus_endorsement_top_pick"]["p"] < 0.05,
        "ag: P1 in part (endorsement significant, stuffing estimate larger)": sig(men, "third_party") and men.loc["keyword_stuffing", "effect"] > men.loc["third_party", "effect"],
        "ag: endorsement not clearly the largest legitimate effect": men.loc[legit, "effect"].idxmax() != "third_party",
        "ag: injection effect near zero (|effect| < 3 points)": abs(men.loc["injection", "effect"]) < 0.03,
        "ag: stuffing and summary make the page far easier to find (> 40 and > 15 points)": surf.loc["keyword_stuffing", "effect"] > 0.40 and surf.loc["answer_first", "effect"] > 0.15,
    }


if __name__ == "__main__":
    raise SystemExit(main())
