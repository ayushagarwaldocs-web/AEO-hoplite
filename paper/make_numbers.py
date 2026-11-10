"""Generate paper/numbers.tex (LaTeX macros) from the experiment outputs.

Every number quoted in main.tex comes from here, so re-running the analyses and
this script keeps the paper consistent with the data.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from revision_numbers import revision_macros, write_revision_tables
from followup_numbers import attribution_macros, write_attribution_table, site_macros, write_site_table

ROOT = Path(__file__).resolve().parents[1]
E1 = ROOT / "experiments" / "exp1_web_readiness"


def edge_breakdown() -> dict:
    """Homepage outcomes behind the edge-refusal numbers. Computed from the raw crawl when it is present (not
    released: it holds third-party page content) and cached as counts in results/edge_breakdown.json, which is
    released, so the paper's numbers can be regenerated without the raw data."""
    raw, cache = E1 / "data" / "raw" / "sites.jsonl", E1 / "results" / "edge_breakdown.json"
    if not raw.exists():
        return json.loads(cache.read_text())
    sites = [json.loads(line) for line in raw.open()]
    attempted = edge = errors = other = ok = 0
    for s in sites:
        rep = s["report"]
        if "homepage_skipped" in rep:
            continue
        attempted += 1
        if rep.get("signals"):
            ok += 1
            continue
        hw = rep["homepage_browser"]
        if hw.get("error"):
            errors += 1
        elif hw.get("status") in (401, 403, 429, 503) or hw.get("challenge"):
            edge += 1
        else:
            other += 1
    out = {"attempted": attempted, "ok": ok, "edge": edge, "errors": errors, "other": other}
    cache.write_text(json.dumps(out, indent=1) + "\n")
    return out


def _word(n: int) -> str:
    """Counts below ten as words, for prose."""
    words = ["none", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
    return words[n] if n < len(words) else str(n)


def _thousands(n: int) -> str:
    return f"{n:,}".replace(",", "{,}")


def _ci(m: dict) -> str:
    return f"[{m['lo']:.1f}, {m['hi']:.1f}]"


def extended_macros() -> dict:
    """Study 1 extensions from analyze_extensions.py: inference, barriers, random sample, history."""
    path = E1 / "results" / "extended.json"
    if not path.exists():
        return {}
    e = json.loads(path.read_text())
    inf = e["inference"]
    bar = json.loads((E1 / "results" / "revision_access.json").read_text())["barriers"]
    out = {}
    pairs = {"Gpt": "GPTBot vs OAI-SearchBot", "Claude": "ClaudeBot vs Claude-SearchBot",
             "Any": "any training vs any answer", "GptUser": "GPTBot vs ChatGPT-User"}
    for code, key in pairs.items():
        t = inf["paired"][key]
        out[f"Pair{code}First"], out[f"Pair{code}Second"] = t["only_first"], t["only_second"]
        out[f"Pair{code}SecondWord"] = _word(t["only_second"])
        out[f"Pair{code}P"] = _fmt_p(t["p"])
    out["PathAnyRetrieval"] = inf["answer_blocked_at_article_path"]["pct"]
    out["PathOnly"], out["NPathOnly"] = inf["answer_blocked_at_path_only"]["pct"], inf["answer_blocked_at_path_only"]["k"]
    st = inf["sector_test"]
    out.update(SectorChi=st["chi2"], SectorDf=st["df"], SectorP=_fmt_p(st["p_perm"]), SectorV=st["cramers_v"])
    for name, m in [("AnyRetrieval", inf["any_retrieval_block"]), ("AnyTrain", inf["any_train_block"]),
                    ("Edge", inf["edge"]), ("Js", inf["js_dependent"]), ("Llms", inf["llms_txt"]),
                    ("Open", inf["policy"]["Open to AI crawlers"]), ("GPTBot", inf["block"]["GPTBot"]),
                    ("OAISearchBot", inf["block"]["OAI-SearchBot"]), ("ClaudeBot", inf["block"]["ClaudeBot"]),
                    ("ClaudeSearchBot", inf["block"]["Claude-SearchBot"]), ("CCBot", inf["block"]["CCBot"]),
                    ("PerplexityBot", inf["block"]["PerplexityBot"])]:
        out[f"CI{name}"] = _ci(m)
    for name, key in [("Any", "any"), ("NoEdge", "any_without_edge"), ("Implicit", "implicit"),
                      ("ImplicitOnly", "implicit_only"), ("ImplicitNoEdge", "implicit_without_edge"),
                      ("Named", "index_named"), ("Inherited", "index_inherited"),
                      ("Unreach", "robots_unreachable"), ("Edge", "edge"), ("Js", "js")]:
        out[f"Bar{name}"], out[f"N{'Bar' + name}"], out[f"CIBar{name}"] = bar[key]["pct"], bar[key]["k"], _ci(bar[key])
    rs = e.get("random_sample")
    if rs:
        out.update(RandDrawn=_thousands(rs["drawn"]), RandSites=rs["websites"])
        for band, n in rs["bands_n"].items():
            code = {"1-1000": "A", "1001-10000": "B", "10001-100000": "C", "100001-1000000": "D"}[band]
            out[f"RandBand{code}"] = n
        for name, key in [("GPTBot", "GPTBot"), ("ClaudeBot", "ClaudeBot"), ("CCBot", "CCBot"),
                          ("OAISearchBot", "OAI-SearchBot"), ("ClaudeSearchBot", "Claude-SearchBot"),
                          ("PerplexityBot", "PerplexityBot"), ("AnyTrain", "any_train_block"),
                          ("AnyRetrieval", "any_retrieval_block"), ("Inherited", "inherited_of_blockers"),
                          ("NamesAI", "names_any_ai"), ("Llms", "llms_txt"), ("ContentSignal", "content_signal"),
                          ("Edge", "edge"), ("Org", "org_entity")]:
            for sample, prefix in (("random", "Rand"), ("purposive", "Purp")):
                m = rs[sample].get(key)
                if m:
                    out[f"{prefix}{name}"], out[f"CI{prefix}{name}"] = m["pct"], _ci(m)
        for sample, prefix in (("random", "Rand"), ("purposive", "Purp")):
            mo = rs[sample]["policy"]["Open to AI crawlers"]
            out[f"{prefix}Open"], out[f"CI{prefix}Open"] = mo["pct"], _ci(mo)
        core = rs["purposive_without_content_sectors"]
        out["PurpCoreAnyRetrieval"], out["PurpCoreAnyTrain"] = core["any_retrieval_block"]["pct"], core["any_train_block"]["pct"]
        out["PurpCoreN"] = core["GPTBot"]["n"]
        for band, m in rs["by_band"].items():
            code = {"1-1000": "A", "1001-10000": "B", "10001-100000": "C", "100001-1000000": "D"}[band]
            out[f"RandAnyRetrieval{code}"] = m["any_retrieval_block"]["pct"]
            out[f"RandLlms{code}"] = m["llms_txt"]["pct"]
            out[f"RandEdge{code}"] = m["edge"]["pct"]
    h = e.get("history")
    if h:
        out.update(HistPanel=h["balanced_panel"], HistQueried=h["domains_queried"],
                   HistGptBlockers=h["gptbot_2024_blockers"], HistStill=h["gptbot_2024_blockers_still_blocking_pct"])
        codes = {"2023-07-01": "A", "2024-01-01": "B", "2024-07-01": "C", "2025-07-01": "D", "2026-07-01": "E",
                 "2026-11-03": "Live"}
        for row in h["series"]:
            c = codes.get(row["date"])
            if not c:
                continue
            for name, key in [("GPTBot", "blocked:GPTBot"), ("CCBot", "blocked:CCBot"),
                              ("ClaudeBot", "blocked:ClaudeBot"), ("GoogleExtended", "blocked:Google-Extended"),
                              ("OAISearchBot", "blocked:OAI-SearchBot"), ("ChatGPTUser", "blocked:ChatGPT-User"),
                              ("PerplexityBot", "blocked:PerplexityBot"), ("ClaudeSearchBot", "blocked:Claude-SearchBot"),
                              ("AnyTrain", "any_train_block"), ("AnyRetrieval", "any_retrieval_block"),
                              ("NamesAI", "names_any_ai"), ("Legacy", "names_legacy"),
                              ("NamedOAISearchBot", "named:OAI-SearchBot"), ("NamedClaudeSearchBot", "named:Claude-SearchBot")]:
                out[f"Hist{name}{c}"] = row[key]
        for date, v in h["oai_searchbot_named_among_live_gptbot_blockers"].items():
            if date in codes:
                out[f"HistSplitNamed{codes[date]}"] = v
    return out


E2 = ROOT / "experiments" / "exp2_content_treatments"
OUTCOME_CODES = {"mentioned": "Men", "top_pick": "Top", "cited": "Cit"}
# Main analysis: the 12 hosted models (analyze.py --tag bedrock). The three local small models
# (untagged results) are a secondary comparison whose macros carry the prefix "Sm".
HOSTED = {"suffix": "_bedrock", "responses": E2 / "data" / "responses_bedrock.jsonl"}
LOCAL = {"suffix": "", "responses": E2 / "data" / "responses.jsonl"}
STUDY2 = dict(HOSTED)
BEDROCK_CODES = {  # letters only, as LaTeX macro names require
    "claude-sonnet-4-6": "Claude", "gpt-oss-120b": "Gptoss", "llama4-maverick": "Maverick", "nova-pro": "Novapro",
    "nova-2-lite": "Novalite", "mistral-large-3": "Mistral", "deepseek.v3.2": "Deepseek", "qwen3-32b": "Qwensmall",
    "qwen3-next-80b": "Qwennext", "gemma-3-27b": "Gemma", "minimax-m2.5": "Minimax", "nemotron-super-3": "Nemotron",
    "claude-opus-4-6": "Opus", "kimi-k3": "Kimi", "glm-5": "Glm",
}
# Robustness checks (README "Robustness checks"): the flagship replication is analysed like the main data
# (prefix "Fl"); long pages, temperature 1 and the detector check come from analyze_robustness.py and
# analyze_absorption_judge.py (prefix "R").
FLAGSHIP = {"suffix": "_flagship", "responses": E2 / "data" / "responses_flagship.jsonl"}


def _res(name: str) -> Path:
    stem, ext = name.rsplit(".", 1)
    return E2 / "results" / f"{stem}{STUDY2['suffix']}.{ext}"


def _wilson(k: float, n: float, z: float = 1.96) -> tuple[float, float]:
    p, d = k / n, 1 + z * z / n
    centre, half = (p + z * z / (2 * n)) / d, z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / d
    return 100 * (centre - half), 100 * (centre + half)


OTHER_CODES = {  # Microsoft Foundry (Azure) and Gemini API models, by exact spec
    "azure:gpt-5-mini": "Gptmini", "azure:grok-4.6": "Grok", "azure:MAI-Thinking-1": "Mai",
    "azure:DeepSeek-V4-Pro": "Deepseekpro", "azure:Kimi-K3.1-Pro": "Kimipro", "gemini:gemini-3.5-flash": "Gemini",
    "gemini:gemini-3.5-flash-lite": "Geminilite",
    "anthropic:claude-opus-5-5": "Opusfive", "anthropic:claude-sonnet-5-5": "Sonnetfive",
    "anthropic:claude-haiku-5-5": "Haikufive", "anthropic:claude-fable-5-1": "Fable",
    "openai:gpt-6.1-sol": "Gptsix",
}


def _model_code(model: str) -> str:
    if model == "pooled":
        return "All"
    if model in OTHER_CODES:
        return OTHER_CODES[model]
    if model.startswith("bedrock:"):
        return next(v for k, v in BEDROCK_CODES.items() if k in model)
    name = model.split(":", 1)[-1]
    return "".join(ch for ch in name.split("-")[0].split(".")[0] if ch.isalpha()).capitalize()


def _peq(p: float) -> str:
    """'< 0.001' or '= 0.260', for '$p \\HFivePEq$' in prose."""
    return "< 0.001" if p < 0.001 else f"= {p:.3f}"


def _fmt_p(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def study2_macros() -> dict:
    """Macros for Study 2 if real-model results exist (mock runs are ignored)."""
    eff_path, resp_path = _res("effects.csv"), STUDY2["responses"]
    if not eff_path.exists() or not resp_path.exists():
        return {"StudyTwoDone": 0}
    eff = pd.read_csv(eff_path)
    placebo = pd.read_csv(_res("effects_vs_placebo.csv"))
    resp = pd.read_json(resp_path, lines=True)
    resp = resp[resp["error"].isna() & resp["model"].isin(set(eff["model"]) - {"pooled"})]
    models = sorted(resp["model"].unique())
    out = {"StudyTwoDone": 1, "NModelsTwo": len(models), "NResponsesTwo": f"{len(resp):,}".replace(",", "{,}")}
    base = resp[resp["condition"] == "baseline"]
    out["BaseMenAll"] = round(100 * base["mentioned"].mean(), 1)
    out["BaseTopAll"] = round(100 * base["top_pick"].mean(), 1)
    for m in models:
        b = base[base["model"] == m]
        out[f"BaseMen{_model_code(m)}"] = round(100 * b["mentioned"].mean(), 1)
    pos = base.groupby("target_index")["mentioned"].agg(["sum", "count"])
    for name, slot in (("First", pos.index.min()), ("Last", pos.index.max())):
        k, n = pos.loc[slot, "sum"], pos.loc[slot, "count"]
        lo, hi = _wilson(k, n)
        out[f"Pos{name}"], out[f"CIPos{name}"] = round(100 * k / n, 1), f"[{lo:.1f}, {hi:.1f}]"
    out["PosTrials"] = int(pos["count"].sum())
    out["NTrialsTwo"] = int(resp["trial_id"].nunique())
    out["NScenariosTwo"] = int(resp["scenario"].nunique())
    for frame, prefix in ((eff, "E"), (placebo, "P")):
        for _, r in frame.iterrows():
            if r["outcome"] not in OUTCOME_CODES:
                continue
            cond = "".join(w.capitalize() for w in r["condition"].split("_"))
            key = f"{prefix}{OUTCOME_CODES[r['outcome']]}{_model_code(r['model'])}{cond}"
            out[key] = f"{100 * r['effect']:+.1f}"
            out[key + "U"] = f"{abs(100 * r['effect']):.1f}"  # unsigned, for prose such as "raised by"
            out[key + "CI"] = f"[{100 * r['ci_low']:.1f}, {100 * r['ci_high']:.1f}]"
            out[key + "P"] = _fmt_p(r["p_holm"])
    return out


def _camel(s: str) -> str:
    return "".join(w.capitalize() for w in s.split("_"))


def study2_extra_macros() -> dict:
    """Hypothesis verdicts, model profiles, cross-model agreement, competition and absorption."""
    hp = _res("hypotheses.json")
    if not hp.exists() or not _res("effects.csv").exists():
        return {}
    h = json.loads(hp.read_text())
    pp = lambda v: f"{100 * v:+.1f}"  # noqa: E731
    out = {"HOneSupported": sum(v["supported"] for v in h["H1"].values())}
    sup = [c for c, v in h["H1"].items() if v["supported"]]
    out["HOneVerdict"] = ("Supported" if len(sup) == len(h["H1"])
                          else ("Partly: " + " and ".join(sup) if sup else "Not supported"))
    for c, v in h["H1"].items():
        out[f"HOne{_camel(c)}P"] = _fmt_p(v["p_baseline"])
        out[f"HOne{_camel(c)}PlaceboP"] = _fmt_p(v["p_placebo"])
    t = h["H2"]
    out.update(HTwoBest=t["best_single"].replace("_", " "), HTwoBestEffect=pp(t["best_single_effect"]),
               HTwoBestEffectU=f"{abs(100 * t['best_single_effect']):.1f}",
               HTwoDiff=pp(t["difference"]["effect"]), HTwoDiffU=f"{abs(100 * t['difference']['effect']):.1f}",
               HTwoDiffCI=f"[{100 * t['difference']['ci_low']:.1f}, {100 * t['difference']['ci_high']:.1f}]",
               HTwoVerdict="Supported" if t["supported"] else "Not supported")
    for c, v in h["H3"].items():
        out[f"HThree{_camel(c)}"] = pp(v["effect"])
        out[f"HThree{_camel(c)}CI"] = f"[{100 * v['ci'][0]:.1f}, {100 * v['ci'][1]:.1f}]"
    out["HThreeVerdict"] = ("Contradicted" if any(v["effect"] > 0 and v["p"] < 0.05
                                                       for v in h["H3"].values()) else "Inconclusive")
    for c, v in h["H4"].items():
        out[f"HFour{_camel(c)}"] = pp(v["effect"])
        out[f"HFour{_camel(c)}CI"] = f"[{100 * v['ci90'][0]:.1f}, {100 * v['ci90'][1]:.1f}]"
        out[f"HFour{_camel(c)}Verdict"] = "within" if v["supported"] else "not within"
    out["HFourVerdict"] = "Supported" if all(v["supported"] for v in h["H4"].values()) else "Not supported"
    p5 = h["H5"]
    out.update(HFiveChi=p5["chi2"], HFiveP=_fmt_p(p5["p_perm"]), HFivePEq=_peq(p5["p_perm"]))
    strat = p5.get("stratified")
    if strat:
        out.update(HFiveStratChi=strat["chi2"], HFiveStratP=_fmt_p(strat["p_perm"]), HFiveStratPEq=_peq(strat["p_perm"]),
                   NHFiveSig=_word(sum(v["p_perm"] < 0.05 for v in p5["by_model"].values())))
        for m, v in p5["by_model"].items():
            code = _model_code(m)
            r = v["rates_by_slot"]
            out.update({f"HFive{code}Chi": v["chi2"], f"HFive{code}P": _fmt_p(v["p_perm"]),
                        f"HFive{code}First": f"{r[min(r, key=int)]:.0f}", f"HFive{code}Last": f"{r[max(r, key=int)]:.0f}"})
        # Holm adjustment over the per-model tests
        ps = sorted((v["p_perm"], m) for m, v in p5["by_model"].items())
        running = 0.0
        for i, (p, m) in enumerate(ps):
            running = max(running, min(1.0, (len(ps) - i) * p))
            out[f"HFive{_model_code(m)}PHolm"] = _fmt_p(running)
    out["HFiveVerdict"] = ("Supported" if p5["p_perm"] < 0.05 else
                           "Model-specific" if strat and strat["p_perm"] < 0.05 else "Not supported")
    rates = p5["rates_by_slot"]
    out.update(HFiveMax=max(rates.values()), HFiveMin=min(rates.values()),
               HFiveMaxSlot=max(rates, key=rates.get), HFiveMinSlot=min(rates, key=rates.get))
    for m, prof in h["profiles"].items():
        code = _model_code(m)
        for k, name in [("mention", "Men"), ("top_pick", "Top"), ("cited", "Cit"), ("any_citation", "AnyCit"),
                        ("median_words", "Words"), ("median_brands", "Brands")]:
            v = prof[k]
            out[f"Prof{name}{code}"] = int(v) if k.startswith("median") else v
        out[f"NResp{code}"] = f"{prof['n_responses']:,}".replace(",", "{,}")
    rhos = [v["rho"] for k, v in h["cross_model_spearman"].items() if k.startswith("mentioned")]
    out.update(RhoMenMin=min(rhos), RhoMenMax=max(rhos), RhoMenMedian=f"{sorted(rhos)[len(rhos) // 2]:.2f}")
    for code in ("Llama", "Qwen", "Granite"):  # placeholders while a model's run is incomplete (interim drafts)
        for name in ("Men", "Top", "Cit", "AnyCit", "Words", "Brands"):
            out.setdefault(f"Prof{name}{code}", "--")
    eff = pd.read_csv(_res("effects.csv"))
    pooled = eff[eff["model"] == "pooled"].pivot(index="condition", columns="outcome", values="effect")
    # Round before ranking so that exactly tied effects stay tied across pandas versions (last-bit float noise can
    # otherwise break a genuine tie and change the rank correlation).
    ranked = pooled[["pawc", "mentioned"]].round(10)
    out["RhoPawc"] = f"{ranked['pawc'].corr(ranked['mentioned'], method='spearman'):.2f}"
    single = ["statistics", "citations", "quotation", "answer_first", "qa_format", "spec_table", "limitations",
              "freshness", "persuasive", "keyword_stuffing"]
    top = eff[(eff["model"] == "pooled") & (eff["outcome"] == "top_pick") & eff["condition"].isin(single)]
    out["NTopSig"] = _word(int(((top["p_holm"] < 0.05) & (top["effect"] > 0)).sum()))
    out["NTopSigCap"] = out["NTopSig"].capitalize()
    out["NSingle"] = _word(len(single))
    base = [v["mention"] for v in h["profiles"].values()]
    out.update(BaseMenMin=f"{min(base):.0f}", BaseMenMax=f"{max(base):.0f}")
    rhos_t = [v["rho"] for k, v in h["cross_model_spearman"].items() if k.startswith("top_pick")]
    out.update(RhoTopMin=min(rhos_t), RhoTopMax=max(rhos_t))
    n_sig = sum(v["n_brands"]["ci_low"] > 0 or v["n_brands"]["ci_high"] < 0 for v in h["competition"].values())
    pi = h.get("position_interaction")
    for m, v in (pi or {}).get("by_model", {}).items():
        code = _model_code(m)
        out.update({f"PosInt{code}Early": f"{100 * v['early']['effect']:.0f}",
                    f"PosInt{code}Late": f"{100 * v['late']['effect']:.0f}",
                    f"PosInt{code}Diff": f"{100 * v['late_minus_early']['effect']:.0f}",
                    f"PosInt{code}DiffCI": f"[{100 * v['late_minus_early']['ci'][0]:.0f}, {100 * v['late_minus_early']['ci'][1]:.0f}]",
                    f"PosBase{code}Early": f"{100 * v['early']['baseline']:.0f}", f"PosBase{code}Late": f"{100 * v['late']['baseline']:.0f}",
                    f"PosTreated{code}Early": f"{100 * v['early']['treated']:.0f}", f"PosTreated{code}Late": f"{100 * v['late']['treated']:.0f}"})
    if pi:
        out.update(PosIntEarly=f"{100 * pi['early']['effect']:.0f}", PosIntLate=f"{100 * pi['late']['effect']:.0f}",
                   PosIntDiff=f"{100 * pi['late_minus_early']['effect']:.0f}",
                   PosIntDiffCI=f"[{100 * pi['late_minus_early']['ci'][0]:.0f}, {100 * pi['late_minus_early']['ci'][1]:.0f}]",
                   PosTreatedEarly=f"{100 * pi['early']['treated']:.0f}", PosTreatedLate=f"{100 * pi['late']['treated']:.0f}",
                   PosBaseEarly=f"{100 * pi['early']['baseline']:.0f}", PosBaseLate=f"{100 * pi['late']['baseline']:.0f}",
                   PosPlaceboLate=f"{100 * pi['late']['placebo']:.0f}")
        out["CompBrandsSig"] = _word(n_sig)
    out["CompMaxBrands"] = f"{max(abs(v['n_brands']['effect']) for v in h['competition'].values()):.1f}"
    out["CompN"] = _word(len(h["competition"]))
    for c, v in h["competition"].items():
        out[f"Comp{_camel(c)}Brands"] = f"{v['n_brands']['effect']:+.2f}"
        out[f"Comp{_camel(c)}BrandsCI"] = f"[{v['n_brands']['ci_low']:.2f}, {v['n_brands']['ci_high']:.2f}]"
        out[f"Comp{_camel(c)}Share"] = pp(v["mention_share"]["effect"])
        out[f"Comp{_camel(c)}ShareU"] = f"{abs(100 * v['mention_share']['effect']):.1f}"
    ab = _res("absorption.csv")
    if ab.exists():
        a = pd.read_csv(ab)
        for _, r in a.iterrows():
            code = _model_code(r["model"])
            out[f"Abs{_camel(r['condition'])}{code}"] = r["absorbed_if_mentioned"]
            out[f"AbsRaw{_camel(r['condition'])}{code}"] = r["absorbed"]
        out["AbsFalsePosMax"] = a["false_positive"].max()
        out["AbsFalsePosText"] = ("never fired on the paired baseline answers" if a["false_positive"].max() == 0 else
                                  f"fired on at most {a['false_positive'].max():.1f}\\% of the paired baseline answers")
    return out


LABELS = {
    "statistics": "Statistics", "citations": "Source citations", "quotation": "Expert quotation",
    "answer_first": "Answer-first summary", "qa_format": "Q\\&A format", "spec_table": "Spec table",
    "limitations": "Stated limitations", "freshness": "Freshness date", "third_party": "Third-party endorsement",
    "persuasive": "Persuasive tone", "keyword_stuffing": "Keyword stuffing", "filler": "Boilerplate placebo",
    "injection": "Source-embedded instruction", "combined": "Combined",
}


def _short(model: str) -> str:
    name = re.sub(r"(?i)-instruct(-4bit)?$", "", model.split(":", 1)[-1])
    return re.sub(r"(\d)b$", r"\1B", name[:1].upper() + name[1:])


def _cell(r: pd.Series, ci: bool = False) -> str:
    star = "$^{*}$" if r["p_holm"] < 0.05 else ""
    text = f"${100 * r['effect']:+.1f}${star}"
    lo, hi = (f"{100 * r[k]:.0f}".replace("-0", "0") if f"{100 * r[k]:.0f}" == "-0" else f"{100 * r[k]:.0f}"
              for k in ("ci_low", "ci_high"))
    return text + (f" {{\\footnotesize$[{lo}, {hi}]$}}" if ci else "")


def write_effects_table() -> None:
    """paper/table_study2.tex (main text) and table_study2_full.tex (appendix), from analyze.py's effects."""
    path = _res("effects.csv")
    if not path.exists():
        return
    import sys
    sys.path.insert(0, str(E2))
    from build_corpus import CONDITIONS
    eff = pd.read_csv(path).set_index(["outcome", "model", "condition"])
    plc = pd.read_csv(_res("effects_vs_placebo.csv")).set_index(["outcome", "model", "condition"])
    models = sorted({m for _, m, _ in eff.index} - {"pooled"})
    conds = [c for c in CONDITIONS[1:] if ("mentioned", "pooled", c) in eff.index]
    head = (r"\begin{tabular}{@{}l" + "r" * (3 + len(models)) + "@{}}\n\\toprule\n"
            + r" & \multicolumn{" + str(1 + len(models)) + r"}{c}{Target mentioned} & Named first & Cited \\"
            + "\n" + r"\cmidrule(lr){2-" + str(2 + len(models)) + r"}\cmidrule(lr){" + str(3 + len(models))
            + "-" + str(3 + len(models)) + r"}\cmidrule(l){" + str(4 + len(models)) + "-" + str(4 + len(models))
            + "}\n" + "Treatment & Pooled [95\\% CI] & " + " & ".join(_model_code(m) for m in models)
            + r" & Pooled & Pooled \\" + "\n\\midrule\n")
    rows = []
    for c in conds:
        cells = [_cell(eff.loc[("mentioned", "pooled", c)], ci=True)]
        cells += [_cell(eff.loc[("mentioned", m, c)]) for m in models]
        cells += [_cell(eff.loc[(o, "pooled", c)]) for o in ("top_pick", "cited")]
        rows.append(LABELS.get(c, c) + " & " + " & ".join(cells) + r" \\")
    (Path(__file__).parent / "table_small.tex").write_text(head + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")

    # Appendix: every model and outcome, against the baseline and against the boilerplate placebo
    lines = [r"\begin{tabular}{@{}ll" + "r" * 6 + "@{}}", r"\toprule",
             r" & & \multicolumn{3}{c}{Versus baseline} & \multicolumn{3}{c}{Versus placebo} \\",
             r"\cmidrule(lr){3-5}\cmidrule(l){6-8}",
             r"Model & Treatment & Mentioned & Named first & Cited & Mentioned & Named first & Cited \\", r"\midrule"]
    for m in models + ["pooled"]:
        for i, c in enumerate(conds):
            cells = [_cell(eff.loc[(o, m, c)]) for o in ("mentioned", "top_pick", "cited")]
            cells += ["--" if c == "filler" else _cell(plc.loc[(o, m, c)]) for o in ("mentioned", "top_pick", "cited")]
            name = ("Pooled" if m == "pooled" else _short(m)) if i == 0 else ""
            lines.append(f"{name} & {LABELS.get(c, c)} & " + " & ".join(cells) + r" \\")
        lines.append(r"\midrule" if m != "pooled" else r"\bottomrule")
    lines.append(r"\end{tabular}")
    (Path(__file__).parent / "table_study2_full.tex").write_text("\n".join(lines) + "\n")


def write_agents_table() -> None:
    """paper/table_agents.tex: the agent registry evaluated in Study 1 (appendix)."""
    import sys
    sys.path.insert(0, str(ROOT))
    from aeotools.bots import BOTS
    names = {"training": "Training", "ai_search": "AI search index", "user_fetch": "User-triggered fetch",
             "search": "Web search", "legacy": "Legacy (retired)", "other": "Other AI"}
    rows = [f"\\agent{{{b.token}}} & {b.operator} & {names[b.category]} & {b.honors_robots} \\\\" for b in BOTS]
    tex = ("\\begin{tabular}{@{}llll@{}}\n\\toprule\nToken & Operator & Purpose & Honours robots.txt \\\\\n"
           "\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")
    (Path(__file__).parent / "table_agents.tex").write_text(tex)


def write_sectors_table() -> None:
    """paper/table_sectors.tex: per-sector composition and key rates (appendix)."""
    sec = pd.read_csv(E1 / "results" / "by_sector.csv")
    fmt = lambda v: "--" if pd.isna(v) else f"{v:.0f}"  # noqa: E731
    sites = pd.read_csv(E1 / "results" / "sites.csv")
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("study_one_labels", E1 / "analyze.py")
    labels = module_from_spec(spec)
    spec.loader.exec_module(labels)
    sites["sector_label"] = sites["sector"].map(labels.SECTOR_LABELS).fillna(sites["sector"])
    measured = sites.groupby("sector_label")["raw_share"].count()
    rows = [f"{r['sector'].replace('&', '\\&')} & {r['sites']} & {fmt(r['GPTBot'])} & {fmt(r['OAI-SearchBot'])} & "
            f"{fmt(r['any_retrieval_block'])} & {fmt(r['llms_txt'])} & {fmt(r['org_entity'])} & {fmt(r['js_dependent'])} ({int(measured.get(r['sector'], 0))}) \\\\"
            for _, r in sec.iterrows()]
    tex = ("\\begin{tabular}{@{}lrrrrrrr@{}}\n\\toprule\n"
           "Sector & Sites & GPTBot & OAI-Search & Any answer & llms.txt & Org.\\ entity & JS-dep. (n) \\\\\n"
           "\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")
    (Path(__file__).parent / "table_sectors.tex").write_text(tex)


def write_materials() -> None:
    """paper/appendix_materials.tex: the engine prompt, one baseline prompt and every treatment text,
    generated from the corpus code so the appendix shows exactly what the models saw."""
    import sys
    sys.path.insert(0, str(E2))
    from build_corpus import CONDITIONS, SCENARIOS, SYSTEM, build, load_brands, target_body

    items = [it for it in build(3) if it["trial_id"] == "pm_agency-0"]
    sc = next(s for s in SCENARIOS if s["id"] == "pm_agency")
    target = next(b for b in load_brands()["pm_agency"]["brands"] if b["core"] == items[0]["target"])
    base = target_body(sc, target, "baseline")
    parts = [r"\subsection*{Engine prompt (system message)}", r"\begin{lstlisting}", SYSTEM, r"\end{lstlisting}",
             r"\subsection*{Example user message (scenario \texttt{pm\_agency}, trial 0, baseline)}",
             r"\begin{lstlisting}", items[0]["user"], r"\end{lstlisting}",
             r"\subsection*{Target page under each treatment}",
             "The target here is source [" + str(items[0]["target_index"]) + "]. Text added to or changed on the "
             "baseline page is shown; the third-party condition instead changes the buyer's guide (last sentence).",
             r"\begin{lstlisting}"]
    for cond in CONDITIONS[1:]:
        if cond == "third_party":
            guide = next(it for it in items if it["condition"] == "third_party")["user"]
            last = [line for line in guide.split("\n") if "In our hands-on testing" in line][0]
            text = last[last.index("In our hands-on testing"):]
        else:
            body = target_body(sc, target, cond)
            text = body.replace(base, "[baseline page]").strip()
        parts += [f"--- {cond} ---", text, ""]
    parts.append(r"\end{lstlisting}")
    (Path(__file__).parent / "appendix_materials.tex").write_text("\n".join(parts) + "\n")


def explore_macros() -> dict:
    """Exploratory endorsement strengths and second wordings (analyze_explore.py), hosted and small models."""
    out = {}
    for sfx, pre in (("_bedrock", ""), ("", "Sm")):
        path = E2 / "results" / f"explore{sfx}.csv"
        if not path.exists():
            continue
        x = pd.read_csv(path)
        x = x[(x["model"] == "pooled")].set_index(["family", "outcome", "condition", "reference"])
        g = lambda f, o, c, r: x.loc[(f, o, c, r)]  # noqa: E731
        for o, oc in (("mentioned", "Men"), ("top_pick", "Top")):
            for c, cc in (("third_party_mention", "Mention"), ("third_party_shared", "Shared")):
                r = g("vs_baseline", o, c, "baseline")
                out[f"{pre}X{oc}{cc}"] = f"{100 * r['effect']:.1f}"
                out[f"{pre}X{oc}{cc}CI"] = f"[{100 * r['ci_low']:.1f}, {100 * r['ci_high']:.1f}]"
                r = g("endorsement", o, "third_party", c)
                out[f"{pre}X{oc}SoleMinus{cc}"] = f"{100 * r['effect']:.1f}"
                out[f"{pre}X{oc}SoleMinus{cc}CI"] = f"[{100 * r['ci_low']:.1f}, {100 * r['ci_high']:.1f}]"
            w = [g("wording", o, f"{c}_b", c) for c in ("statistics", "citations", "quotation", "persuasive", "keyword_stuffing")]
            eff = [100 * r["effect"] for r in w]
            out[f"{pre}XWord{oc}Min"], out[f"{pre}XWord{oc}Max"] = f"{min(eff):.1f}", f"{max(eff):.1f}"
            out[f"{pre}XWord{oc}MinU"], out[f"{pre}XWord{oc}MaxU"] = f"{abs(max(eff)):.1f}", f"{abs(min(eff)):.1f}"
            out[f"{pre}XWord{oc}NSig"] = _word(sum(r["p_holm"] < 0.05 for r in w))
            for c in ("statistics", "citations", "quotation", "persuasive", "keyword_stuffing"):
                r = g("vs_baseline", o, f"{c}_b", "baseline")
                out[f"{pre}X{oc}{_camel(c)}B"] = f"{100 * r['effect']:.1f}"
        summ = json.loads((E2 / "results" / f"explore_summary{sfx}.json").read_text())["wording"]
        out[f"{pre}XWordR"], out[f"{pre}XWordPairs"] = f"{summ['pearson']:.2f}", summ["n_pairs"]
        out[f"{pre}XWordMad"] = f"{summ['mean_abs_diff_points']:.1f}"
    n = sum(len(pd.read_json(E2 / "data" / f, lines=True)) for f in ("responses_bedrock_explore.jsonl", "responses_explore.jsonl"))
    out["NXResponses"] = _thousands(n)
    return out


def hosted_count_macros() -> dict:
    """How many of the hosted models show each effect after Holm correction (mentions and first-mentioned brand)."""
    eff = pd.read_csv(E2 / "results" / "effects_bedrock.csv")
    eff = eff[eff["model"] != "pooled"]
    out = {}
    for o, oc in (("mentioned", "Men"), ("top_pick", "Top")):
        d = eff[eff["outcome"] == o]
        for c, grp in d.groupby("condition"):
            out[f"NSig{oc}{_camel(c)}"] = int(((grp["p_holm"] < 0.05) & (grp["effect"] > 0)).sum())
            out[f"NSig{oc}{_camel(c)}W"] = _word(out[f"NSig{oc}{_camel(c)}"])
            out[f"Min{oc}{_camel(c)}"] = f"{100 * grp['effect'].min():.0f}"
            out[f"Max{oc}{_camel(c)}"] = f"{100 * grp['effect'].max():.0f}"
    return out


def with_dataset(cfg: dict, prefix: str) -> dict:
    STUDY2.update(cfg)
    out = {**study2_macros(), **study2_extra_macros()}
    return {prefix + k: v for k, v in out.items()}


def write_hosted_tables() -> None:
    """table_study2.tex (main text): pooled hosted effects with the small-model comparison;
    table_hosted_models.tex (appendix): every hosted model's effect on mentions."""
    import sys
    sys.path.insert(0, str(E2))
    from analyze import short_name
    from build_corpus import CONDITIONS
    h = pd.read_csv(E2 / "results" / "effects_bedrock.csv").set_index(["outcome", "model", "condition"])
    hp = pd.read_csv(E2 / "results" / "effects_vs_placebo_bedrock.csv").set_index(["outcome", "model", "condition"])
    sm = pd.read_csv(E2 / "results" / "effects.csv").set_index(["outcome", "model", "condition"])
    models = sorted({m for _, m, _ in h.index} - {"pooled"}, key=short_name)
    conds = [c for c in CONDITIONS[1:] if ("mentioned", "pooled", c) in h.index]
    conds.sort(key=lambda c: -h.loc[("mentioned", "pooled", c), "effect"])
    n_sig = lambda c: sum(h.loc[("mentioned", m, c), "p_holm"] < 0.05 and h.loc[("mentioned", m, c), "effect"] > 0  # noqa: E731
                          for m in models)
    fpath = E2 / "results" / "effects_flagship.csv"
    fl = pd.read_csv(fpath).set_index(["outcome", "model", "condition"]) if fpath.exists() else None
    n_rep = len({m for _, m, _ in fl.index} - {"pooled"}) if fl is not None else 0
    lines = [r"\begin{tabular}{@{}lrrrrcrr@{}}", r"\toprule",
             r" & \multicolumn{5}{c}{12 hosted models} & " + f"{n_rep} replication" + r" & 3 small \\",
             r"\cmidrule(lr){2-6}\cmidrule(lr){7-7}\cmidrule(l){8-8}",
             r"Treatment & Mentioned [95\% CI] & vs placebo & Named first & Cited & Models$^{\dagger}$ & Mentioned"
             r" & Mentioned \\",
             r"\midrule"]
    for c in conds:
        rep = _cell(fl.loc[("mentioned", "pooled", c)]) if fl is not None and ("mentioned", "pooled", c) in fl.index else "--"
        cells = [_cell(h.loc[("mentioned", "pooled", c)], ci=True),
                 "--" if c == "filler" else _cell(hp.loc[("mentioned", "pooled", c)]),
                 _cell(h.loc[("top_pick", "pooled", c)]), _cell(h.loc[("cited", "pooled", c)]),
                 f"{n_sig(c)}", rep, _cell(sm.loc[("mentioned", "pooled", c)])]
        lines.append(LABELS.get(c, c) + " & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (Path(__file__).parent / "table_study2.tex").write_text("\n".join(lines) + "\n")
    head = (r"\begin{tabular}{@{}l" + "r" * len(models) + "@{}}\n\\toprule\nTreatment & "
            + " & ".join(r"\rotatebox{70}{" + short_name(m) + "}" for m in models) + r" \\" + "\n\\midrule\n")
    rows = []
    for c in conds:
        rows.append(LABELS.get(c, c) + " & " + " & ".join(_cell(h.loc[("mentioned", m, c)]) for m in models) + r" \\")
    base = pd.read_json(E2 / "data" / "responses_bedrock.jsonl", lines=True)
    base = base[base["error"].isna() & (base["condition"] == "baseline")].groupby("model")["mentioned"].mean()
    rows.append(r"\midrule" + "\nBaseline mention rate (\\%) & " + " & ".join(f"{100 * base[m]:.0f}" for m in models) + r" \\")
    (Path(__file__).parent / "table_hosted_models.tex").write_text(head + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")


def robustness_macros() -> dict:
    """Long pages, temperature 1, flagship agreement and the detector check."""
    out = {}
    path = E2 / "results" / "robustness_summary.json"
    if path.exists():
        s = json.loads(path.read_text())
        for label, pre in (("long", "RLong"), ("temp1", "RTemp")):
            if label not in s:
                continue
            v = s[label]
            out[f"{pre}NModels"] = len(v["models"])
            out[f"{pre}NModelsW"] = _word(len(v["models"]))
            out[f"{pre}N"] = _thousands(v["n_answers"])
            out[f"{pre}BaseMain"], out[f"{pre}BaseAlt"] = v["baseline_mention"]["main"], v["baseline_mention"]["alt"]
            out[f"{pre}Same"], out[f"{pre}Pairs"], out[f"{pre}R"] = v["signs"]["same_sign"], v["signs"]["pairs"], f"{v['signs']['pearson']:.2f}"
            for key, r in v.items():
                if "|" not in key:
                    continue
                version, ref, cond = key.split("|")
                name = f"{pre}{'Alt' if version != 'main' else 'Main'}{'P' if ref == 'filler' else ''}{_camel(cond)}"
                out[name] = f"{r['effect']:+.1f}"
                out[name + "U"] = f"{abs(r['effect']):.1f}"
                out[name + "CI"] = f"[{r['ci'][0]:.1f}, {r['ci'][1]:.1f}]"
                out[name + "P"] = _fmt_p(r["p_holm"])
            for cond, r in v["change"].items():
                name = f"{pre}Change{_camel(cond)}"
                out[name] = f"{r['change']:+.1f}"
                out[name + "U"] = f"{abs(r['change']):.1f}"
                out[name + "CI"] = f"[{r['ci'][0]:.1f}, {r['ci'][1]:.1f}]"
                out[name + "P"] = _fmt_p(r["p_holm"])
            if label == "long":
                out["RLongWords"], out["RLongWordsShort"] = v["target_words"]["baseline"], v["target_words"]["main_baseline"]
        f = s.get("flagship") or {}
        if f:
            out["FlRho"] = f"{f['spearman_vs_main']:.2f}"
            out["FlNModels"] = len(f["models"])
            for cond, k in f["n_sig_models"].items():
                out[f"FlNSig{_camel(cond)}"] = k
                out[f"FlNSig{_camel(cond)}W"] = _word(k)
    upath = E2 / "results" / "usage_weighted.csv"
    if upath.exists():
        u = pd.read_csv(upath)
        for _, r in u[u["outcome"] == "mentioned"].iterrows():
            name = f"RUw{_camel(r['condition'])}"
            out[name] = f"{100 * r['effect']:+.1f}"
            out[name + "U"] = f"{abs(100 * r['effect']):.1f}"
            out[name + "CI"] = f"[{100 * r['ci_low']:.1f}, {100 * r['ci_high']:.1f}]"
            out[name + "P"] = _fmt_p(r["p_holm"])
        uw = json.loads(path.read_text()).get("usage_weighted", {}) if path.exists() else {}
        present = uw.get("assistants_present", [])
        out["RUwNAssistants"] = len(present)
        out["RUwNAssistantsW"] = _word(len(present))
        weights = uw.get("weights", {})
        total = sum(weights.get(a, 0) for a in present)
        if total:  # each present assistant's share after renormalising over those present
            for a in ("ChatGPT", "Gemini", "Claude"):
                if a in present:
                    out[f"RUwShare{a.capitalize()}"] = f"{100 * weights[a] / total:.0f}"
    jpath = E2 / "results" / "absorption_judge.csv"
    if jpath.exists():
        j = pd.read_csv(jpath)
        summ = json.loads((E2 / "results" / "absorption_judge_summary.json").read_text())
        code = lambda name: "Haiku" if "Haiku" in name else "Deepseek"  # noqa: E731
        out["RJudgeN"], out["RJudgeNBase"] = summ["n_treated"], summ["n_baseline"]
        out["RJudgeKappaBetween"] = f"{summ['kappa_between_judges']:.2f}"
        for _, r in j.iterrows():
            jc, cc = code(r["judge"]), "All" if r["condition"] == "all" else _camel(r["condition"])
            out[f"RJudge{jc}{cc}Rate"] = f"{r['judge_rate']:.1f}"
            out[f"RJudge{jc}{cc}Kappa"] = f"{r['kappa']:.2f}"
            out[f"RJudge{jc}{cc}Precision"] = f"{r['precision']:.1f}"
            out[f"RJudge{jc}{cc}Recall"] = f"{r['recall']:.1f}"
            out[f"RJudge{jc}{cc}FP"] = f"{r['fp_judge']:.1f}"
            out[f"RJudgeDetector{cc}Rate"] = f"{r['detector_rate']:.1f}"
            out[f"RJudgeDetector{cc}FP"] = f"{r['fp_detector']:.1f}"
        a = j[j["condition"] == "all"]
        out["RJudgeKappaMin"], out["RJudgeKappaMax"] = f"{a['kappa'].min():.2f}", f"{a['kappa'].max():.2f}"
        out["RJudgePrecisionMin"] = f"{a['precision'].min():.0f}"
        out["RJudgeRecallMin"], out["RJudgeRecallMax"] = f"{a['recall'].min():.0f}", f"{a['recall'].max():.0f}"
        ev = j[j["condition"].isin(["statistics", "citations"])]
        out["RJudgeEvidenceKappaMin"] = f"{ev['kappa'].min():.2f}"
    return out


def audit_macros() -> dict:
    """Live audit of Perplexity and Gemini (analyze_audit.py)."""
    path = E2 / "results" / "audit_summary.json"
    if not path.exists():
        return {}
    a = json.loads(path.read_text())
    p, g = a["perplexity"], a["gemini"]
    out = {"AudNQ": p["questions"], "AudNQW": _word(p["questions"]), "AudPCites": p["citations"],
           "AudPDomains": p["distinct_domains"], "AudPIncog": p.get("incognito_questions", ""), "AudPVendor": p["vendor"], "AudPVendorPct": f"{p['vendor_pct']:.0f}",
           "AudPThirdPct": f"{100 - p['vendor_pct']:.0f}", "AudPVendorMajority": _word(p["questions_vendor_majority"]),
           "AudGSources": g["sources"], "AudGVendor": g["vendor"], "AudGVendorPct": f"{g['vendor_pct']:.0f}"}
    c = a.get("chatgpt")
    if c:
        out.update({"AudCNQ": c["questions"], "AudCNQW": _word(c["questions"]), "AudCCited": c["with_cited_sources"],
                    "AudCCitedW": _word(c["with_cited_sources"]), "AudCSearched": c["searched"],
                    "AudCImages": c["images_only"], "AudCImagesW": _word(c["images_only"]),
                    "AudCLinksQ": c["with_product_links"], "AudCLinksQW": _word(c["with_product_links"]),
                    "AudCLinks": c["product_links"], "AudCTop": c["with_top_pick"], "AudCAsked": c["asked_back"],
                    "AudCAskedW": _word(c["asked_back"])})
    r = p.get("robots")
    if r:
        out.update({"AudPBlocked": r["pplx_blocked"], "AudPBlockedPct": f"{100 * r['pplx_blocked'] / r['checked']:.0f}",
                    "AudPBlockedDomains": len(r["pplx_blocked_domains"]), "AudPBlockedNamed": r.get("pplx_blocked_named", ""),
                    "AudPBlockedUser": r.get("pplx_blocked_user", ""), "AudPBlockedQ": _word(r.get("pplx_blocked_questions", 0))})
    return out



def extra_check_macros() -> dict:
    """Call-out re-scoring (analyze_callouts.py) and minimum detectable effects (analyze_power.py)."""
    res = E2 / "results"
    out = {}
    for tag, pre in (("flagship", "RCallFl"), ("bedrock", "RCallMain")):
        f, j = res / f"injection_callouts_{tag}.csv", res / f"injection_callouts_{tag}.json"
        if not (f.exists() and j.exists()):
            continue
        d, s = pd.read_csv(f), json.loads(j.read_text())
        get = lambda oc, sc, m="pooled": d[(d.outcome == oc) & (d.scoring == sc) & (d.model == m)].iloc[0]  # noqa: E731
        for oc, code in (("mentioned", "Men"), ("top_pick", "Top")):
            for sc, suf in (("as scored", "Raw"), ("call-outs removed", "Clean")):
                out[f"{pre}{code}{suf}"] = f"{100 * get(oc, sc)['effect']:.1f}"
                out[f"{pre}{code}Sig{suf}"] = s[f"{sc}|{oc}|n_sig_positive"]
                out[f"{pre}{code}Sig{suf}W"] = _word(s[f"{sc}|{oc}|n_sig_positive"])
        out[f"{pre}Changed"] = s["answers_changed"]
        rates = s["callout_rate_injection"]
        out[f"{pre}NFlagging"] = _word(sum(v >= 0.05 for v in rates.values()))
        if tag == "flagship":
            son = "anthropic:claude-sonnet-5-5"
            out["RCallSonnetfivePct"] = f"{100 * rates[son]:.0f}"
            out["RCallKimiPct"] = f"{100 * rates['bedrock:global.moonshotai.kimi-k3']:.0f}"
            for oc, code in (("mentioned", "Men"), ("top_pick", "Top")):
                out[f"RCallSonnetfive{code}Raw"] = f"{100 * get(oc, 'as scored', son)['effect']:+.1f}"
                out[f"RCallSonnetfive{code}Clean"] = f"{100 * get(oc, 'call-outs removed', son)['effect']:+.1f}"
        else:
            s46 = "bedrock:global.anthropic.claude-sonnet-4-6"
            out["RCallSonnetfourPct"] = f"{100 * rates[s46]:.0f}"
            out["RCallSonnetfourMenClean"] = f"{100 * get('mentioned', 'call-outs removed', s46)['effect']:+.1f}"
    m = res / "mde_summary.json"
    if m.exists():
        s = json.loads(m.read_text())
        for tag, pre in (("bedrock", "MdeMain"), ("flagship", "MdeFl")):
            if tag in s:
                v = s[tag]
                out.update({f"{pre}Pooled": v["pooled_mde80_median"], f"{pre}PooledMin": v["pooled_mde80_min"],
                            f"{pre}PooledMax": v["pooled_mde80_max"], f"{pre}PooledHolm": v["pooled_mde80_holm_median"],
                            f"{pre}Model": v["per_model_mde80_median"], f"{pre}ModelQlo": v["per_model_mde80_q25"],
                            f"{pre}ModelQhi": v["per_model_mde80_q75"], f"{pre}ModelHolm": v["per_model_mde80_holm_median"]})
    return out


# Agentic search (README "Agentic search"; analyze_agentic.py): prefix "Ag".
AG_MODELS = {"openai:gpt-6.1-sol": ("Sol", "GPT-6.1 Sol"), "azure:gpt-5-mini": ("Mini", "GPT-5 mini"),
             "azure:MAI-Thinking-1": ("Mai", "MAI-Thinking-1"), "azure:DeepSeek-V4-Pro": ("Deepseek", "DeepSeek V4 Pro")}
AG_CONDITIONS = ["third_party", "citations", "statistics", "answer_first", "keyword_stuffing", "injection"]


def agentic_macros() -> dict:
    res = E2 / "results"
    if not (res / "agentic_summary.json").exists():
        return {}
    s = json.loads((res / "agentic_summary.json").read_text())
    e, v = pd.read_csv(res / "agentic_effects.csv"), pd.read_csv(res / "agentic_vs_context.csv")
    fq = pd.read_csv(res / "agentic_fixed_queries.csv")
    pm, models = s["pooled_models"], s["models"]
    pct = lambda x: f"{100 * x:.0f}"  # noqa: E731
    out = {"AgNModels": len(pm), "AgNModelsW": _word(len(pm)),
           "AgNEpisodes": _thousands(sum(d["episodes_ok"] for d in models.values())),
           "AgNTrialsMin": min(models[m]["complete_trials"] for m in pm),
           "AgCost": f"{sum(d['cost_usd'] for d in models.values()):.0f}",
           "AgBaseMenCtx": pct(s["pooled_baseline_in_context"]),
           "AgShareMenUnopened": pct(s["share_mentions_unopened"])}
    for oc, code in (("mentioned", "Men"), ("top_pick", "Top"), ("cited", "Cit"), ("surfaced", "Surf"), ("opened", "Open")):
        out[f"AgBase{code}"] = pct(s["pooled_baseline"][oc])
        sub = e[(e["outcome"] == oc) & (e["model"] == "pooled")].set_index("condition")
        per = e[(e["outcome"] == oc) & e["model"].isin(pm)]
        for c in AG_CONDITIONS:
            if c not in sub.index:
                continue
            r = sub.loc[c]
            out[f"AgE{code}{_camel(c)}"] = f"{100 * r['effect']:+.1f}"
            out[f"AgE{code}{_camel(c)}U"] = f"{100 * r['effect']:.1f}"
            out[f"AgE{code}{_camel(c)}CI"] = f"[{100 * r['ci_low']:.1f}, {100 * r['ci_high']:.1f}]"
            n_sig = int(((per["condition"] == c) & (per["p_holm"] < 0.05) & (per["effect"] > 0)).sum())
            out[f"AgNSig{code}{_camel(c)}"] = n_sig
            out[f"AgNSig{code}{_camel(c)}W"] = _word(n_sig)
    vp = v[(v["model"] == "pooled") & (v["outcome"] == "mentioned")].set_index("condition")
    for c in AG_CONDITIONS:
        if c in vp.index:
            r = vp.loc[c]
            out[f"AgCtxMen{_camel(c)}"] = f"{100 * r['in_context']:+.1f}"
            out[f"AgDiffMen{_camel(c)}"] = f"{100 * r['difference']:+.1f}"
            out[f"AgDiffMen{_camel(c)}U"] = f"{abs(100 * r['difference']):.1f}"
            out[f"AgDiffMen{_camel(c)}CI"] = f"[{100 * r['ci_low']:.1f}, {100 * r['ci_high']:.1f}]"
    fp = fq[fq["model"] == "pooled"].set_index("condition")
    for c in AG_CONDITIONS:
        if c in fp.index:
            out[f"AgFq{_camel(c)}"] = f"{100 * fp.loc[c, 'effect']:+.1f}"
            out[f"AgFq{_camel(c)}U"] = f"{abs(100 * fp.loc[c, 'effect']):.1f}"
            out[f"AgFq{_camel(c)}CI"] = f"[{100 * fp.loc[c, 'ci_low']:.1f}, {100 * fp.loc[c, 'ci_high']:.1f}]"
    for m, (code, _) in AG_MODELS.items():
        if m not in models:
            continue
        d = models[m]
        out.update({f"AgSearch{code}": f"{d['searches']:.1f}", f"AgOpens{code}": f"{d['opens']:.1f}",
                    f"AgNoSearch{code}": pct(d["no_search"]), f"AgFab{code}": pct(d["fabricated"]),
                    f"AgForced{code}": pct(d["forced"]), f"AgNoBrand{code}": pct(d["no_brand"]),
                    f"AgBaseMen{code}": pct(d["baseline"]["mentioned"]), f"AgTrials{code}": d["complete_trials"],
                    f"AgCost{code}": f"{d['cost_usd']:.1f}"})
        if d.get("fabricated_no_search") is not None:
            out[f"AgFabNoSearch{code}"] = pct(d["fabricated_no_search"])
    out["AgGuideOpenTp"] = pct(sum(models[m]["guide_opened_third_party"] for m in pm) / len(pm))
    for oc, code in (("mentioned", "Men"), ("top_pick", "Top")):
        x = s.get(f"stuffing_minus_endorsement_{oc}")
        if x:
            out[f"AgStuffVsTp{code}"] = f"{100 * x['effect']:+.1f}"
            out[f"AgStuffVsTp{code}U"] = f"{abs(100 * x['effect']):.1f}"
            out[f"AgStuffVsTp{code}CI"] = f"[{100 * x['ci_low']:.1f}, {100 * x['ci_high']:.1f}]"
            out[f"AgStuffVsTp{code}P"] = _peq(x["p"])
            out[f"AgTpVsStuff{code}CI"] = f"[{-100 * x['ci_high']:.1f}, {-100 * x['ci_low']:.1f}]"
    mbo = s["mentioned_by_opened"].get("baseline", {})
    if "1" in mbo and "0" in mbo:
        out["AgMenIfOpened"], out["AgMenIfNotOpened"] = pct(mbo["1"]), pct(mbo["0"])
    return out


def write_agentic_table() -> None:
    """table_agentic.tex: mention effects with pages given and when the model searches, per model, and retrieval."""
    res = E2 / "results"
    if not (res / "agentic_summary.json").exists():
        return
    s = json.loads((res / "agentic_summary.json").read_text())
    e = pd.read_csv(res / "agentic_effects.csv").set_index(["outcome", "model", "condition"])
    v = pd.read_csv(res / "agentic_vs_context.csv").set_index(["outcome", "model", "condition"])
    models = [m for m in AG_MODELS if m in s["models"]]
    conds = sorted(AG_CONDITIONS, key=lambda c: -e.loc[("mentioned", "pooled", c), "effect"])
    lines = [r"\setlength{\tabcolsep}{4pt}", r"\begin{tabular}{@{}lrr" + "r" * len(models) + "rr@{}}", r"\toprule",
             r" & \multicolumn{" + str(2 + len(models)) + r"}{c}{Mentions} & \multicolumn{2}{c}{Target page} \\",
             r"\cmidrule(lr){2-" + str(3 + len(models)) + r"}\cmidrule(l){" + f"{4 + len(models)}-{5 + len(models)}" + "}",
             r"Treatment & \shortstack[r]{Pages\\given} & \shortstack[r]{Model searches\\{[}95\% CI{]}} & "
             + " & ".join(r"\rotatebox{70}{" + AG_MODELS[m][1] + "}" for m in models)
             + r" & \shortstack[r]{In\\results} & Opened \\",
             r"\midrule"]
    for c in conds:
        cells = [f"${100 * v.loc[('mentioned', 'pooled', c), 'in_context']:+.1f}$",
                 _cell(e.loc[("mentioned", "pooled", c)], ci=True)]
        cells += [_cell(e.loc[("mentioned", m, c)]) for m in models]
        cells += [_cell(e.loc[("surfaced", "pooled", c)]), _cell(e.loc[("opened", "pooled", c)])]
        lines.append(LABELS.get(c, c) + " & " + " & ".join(cells) + r" \\")
    b = s["pooled_baseline"]
    lines += [r"\midrule", "Baseline rate (\\%) & " + f"{100 * s['pooled_baseline_in_context']:.0f} & {100 * b['mentioned']:.0f} & "
              + " & ".join(f"{100 * s['models'][m]['baseline']['mentioned']:.0f}" for m in models)
              + f" & {100 * b['surfaced']:.0f} & {100 * b['opened']:.0f}" + r" \\", r"\bottomrule", r"\end{tabular}"]
    (Path(__file__).parent / "table_agentic.tex").write_text("\n".join(lines) + "\n")
    rows = [r"\setlength{\tabcolsep}{4pt}", r"\begin{tabular}{@{}lrrrrrrrr@{}}", r"\toprule",
            r"Model & Trials & Searches & \shortstack[r]{Pages\\opened} & \shortstack[r]{No\\search} & "
            r"\shortstack[r]{Unseen\\URL cited} & \shortstack[r]{Call\\limit} & \shortstack[r]{No pool\\brand} & "
            r"Cost (\$) \\", r"\midrule"]
    for m in models:
        d = s["models"][m]
        rows.append(f"{AG_MODELS[m][1]} & {d['complete_trials']} & {d['searches']:.1f} & {d['opens']:.1f} & "
                    f"{100 * d['no_search']:.0f} & {100 * d['fabricated']:.0f} & {100 * d['forced']:.0f} & "
                    f"{100 * d['no_brand']:.0f} & {d['cost_usd']:.2f}" + r" \\")
    rows += [r"\bottomrule", r"\end{tabular}"]
    (Path(__file__).parent / "table_agentic_process.tex").write_text("\n".join(rows) + "\n")


def write_robustness_tables() -> None:
    """table_flagship.tex, table_robustness.tex and table_judge.tex (results and appendix)."""
    import sys
    sys.path.insert(0, str(E2))
    from analyze import short_name
    from build_corpus import CONDITIONS
    res = E2 / "results"
    here = Path(__file__).parent
    if (res / "effects_flagship.csv").exists():
        f = pd.read_csv(res / "effects_flagship.csv").set_index(["outcome", "model", "condition"])
        h = pd.read_csv(res / "effects_bedrock.csv").set_index(["outcome", "model", "condition"])
        models = sorted({m for _, m, _ in f.index} - {"pooled"}, key=short_name)
        conds = [c for c in CONDITIONS[1:] if ("mentioned", "pooled", c) in h.index]
        conds.sort(key=lambda c: -h.loc[("mentioned", "pooled", c), "effect"])
        lines = [r"\begin{tabular}{@{}lr" + "r" * (1 + len(models)) + "@{}}", r"\toprule",
                 r" & 12 hosted models & \multicolumn{" + str(1 + len(models)) + r"}{c}{Replication models} \\",
                 r"\cmidrule(l){3-" + str(3 + len(models)) + "}",
                 "Treatment & Pooled & Pooled [95\\% CI] & "
                 + " & ".join(r"\rotatebox{70}{" + short_name(m) + "}" for m in models) + r" \\",
                 r"\midrule"]
        for c in conds:
            cells = [_cell(h.loc[("mentioned", "pooled", c)]), _cell(f.loc[("mentioned", "pooled", c)], ci=True)]
            cells += [_cell(f.loc[("mentioned", m, c)]) for m in models]
            lines.append(LABELS.get(c, c) + " & " + " & ".join(cells) + r" \\")
        resp = pd.read_json(FLAGSHIP["responses"], lines=True)
        base = resp[resp["error"].isna() & (resp["condition"] == "baseline")].groupby("model")["mentioned"].mean()
        lines += [r"\midrule", "Baseline mention rate (\\%) & " + f"{100 * pd.read_json(HOSTED['responses'], lines=True).query('condition == \"baseline\"')['mentioned'].mean():.0f}"
                  + " & " + f"{100 * base.mean():.0f} & " + " & ".join(f"{100 * base[m]:.0f}" for m in models) + r" \\",
                  r"\bottomrule", r"\end{tabular}"]
        (here / "table_flagship.tex").write_text("\n".join(lines) + "\n")
    parts = {}
    for label in ("long", "temp1"):
        p = res / f"robust_{label}_effects.csv"
        if p.exists():
            parts[label] = (pd.read_csv(p).set_index(["outcome", "reference", "version", "model", "condition"]),
                            pd.read_csv(res / f"robust_{label}_change.csv").set_index(["outcome", "condition"]))
    if parts:
        conds = [c for c in CONDITIONS[1:] if any(("mentioned", "baseline", "main", "pooled", c) in e.index for e, _ in parts.values())]
        lines = [r"\begin{tabular}{@{}l" + "rrr" * len(parts) + "@{}}", r"\toprule"]
        heads = {"long": "Long pages", "temp1": "Temperature 1"}
        lines.append(" & " + " & ".join(r"\multicolumn{3}{c}{" + heads[k] + "}" for k in parts) + r" \\")
        lines.append("".join(r"\cmidrule(lr){" + f"{2 + 3 * i}-{4 + 3 * i}" + "}" for i in range(len(parts))))
        lines.append("Treatment & " + " & ".join(r"Main & Robustness [95\% CI] & Change" for _ in parts) + r" \\")
        lines.append(r"\midrule")
        for c in conds:
            cells = []
            for label, (e, ch) in parts.items():
                key = ("mentioned", "baseline", "main", "pooled", c)
                if key not in e.index:
                    cells += ["--", "--", "--"]
                    continue
                cells += [_cell(e.loc[key]), _cell(e.loc[("mentioned", "baseline", label, "pooled", c)], ci=True),
                          _cell(ch.loc[("mentioned", c)].rename({"change": "effect"}))]
            lines.append(LABELS.get(c, c) + " & " + " & ".join(cells) + r" \\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        (here / "table_robustness.tex").write_text("\n".join(lines) + "\n")
    jpath = res / "absorption_judge.csv"
    if jpath.exists():
        j = pd.read_csv(jpath)
        judges = list(dict.fromkeys(j["judge"]))
        lines = [r"\begin{tabular}{@{}l" + "r" * (2 + 3 * len(judges)) + "@{}}", r"\toprule",
                 r" & \multicolumn{2}{c}{Keyword detector} & " + " & ".join(r"\multicolumn{3}{c}{" + x + "}" for x in judges) + r" \\",
                 r"\cmidrule(lr){2-3}" + "".join(r"\cmidrule(lr){" + f"{4 + 3 * i}-{6 + 3 * i}" + "}" for i in range(len(judges))),
                 "Edit & Repeated & False pos. & " + " & ".join(r"Repeated & False pos. & $\kappa$" for _ in judges) + r" \\",
                 r"\midrule"]
        names = {"statistics": "Statistics", "citations": "Source citations", "quotation": "Expert quotation",
                 "limitations": "Stated limitations", "freshness": "Freshness date", "persuasive": "Persuasive tone", "all": "All six"}
        for cond in ["statistics", "citations", "quotation", "limitations", "freshness", "persuasive", "all"]:
            rows = j[j["condition"] == cond].set_index("judge")
            first = rows.iloc[0]
            cells = [f"{first['detector_rate']:.0f}", f"{first['fp_detector']:.0f}"]
            for x in judges:
                r = rows.loc[x]
                cells += [f"{r['judge_rate']:.0f}", f"{r['fp_judge']:.0f}", f"{r['kappa']:.2f}"]
            lines.append((r"\midrule" + "\n" if cond == "all" else "") + names[cond] + " & " + " & ".join(cells) + r" \\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        (here / "table_judge.tex").write_text("\n".join(lines) + "\n")


def copy_hosted_figures() -> None:
    import shutil
    for src, dst in (("fig5_treatments_bedrock", "fig5_treatments_hosted"), ("fig7_position_bedrock", "fig7_position_hosted"),
                     ("fig11_absorption_bedrock", "fig11_absorption_hosted")):
        for ext in ("pdf", "png"):
            f = E2 / "results" / f"{src}.{ext}"
            if f.exists():
                shutil.copy(f, Path(__file__).parent / "figures" / f"{dst}.{ext}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="", help="read Study 2 results written by analyze.py --tag (drafts only)")
    ap.add_argument("--responses", default=None, help="responses file matching --tag")
    args = ap.parse_args()
    s = json.loads((E1 / "results" / "summary.json").read_text())
    sec = pd.read_csv(E1 / "results" / "by_sector.csv").set_index("sector")
    sites = pd.read_csv(E1 / "results" / "sites.csv")
    eb = edge_breakdown()
    reach = s["reachable_robots"]
    n_llms = int(sites["llms_txt"].sum())
    macros = {
        "NSites": s["sites"], "NSectors": s["sectors"], "NReach": reach,
        "NRobotsOk": s["robots_states"].get("ok", 0), "NRobotsAbsent": s["robots_states"].get("absent", 0),
        "NRobotsHtml": s["robots_states"].get("html", 0), "NRobotsUnreach": s["robots_states"].get("unreachable", 0),
        "PctOpen": s["policy_pct"]["Open to AI crawlers"], "PctTrainOnly": s["policy_pct"]["Blocks training only"],
        "PctSomeRetrieval": s["policy_pct"]["Blocks some retrieval"],
        "PctAllRetrieval": s["policy_pct"]["Blocks all retrieval"],
        "PctAnyTrain": s["any_train_block_pct"], "PctAnyRetrieval": s["any_retrieval_block_pct"],
        "PctInherited": s["retrieval_block_inherited_pct_of_retrieval_blockers"],
        "PctWildcardRoot": s["wildcard_root_blocked_pct"],
        "PctOpenAISplit": s["openai_split_pct_of_gptbot_blockers"],
        "PctAnthropicSplit": s["anthropic_split_pct_of_claudebot_blockers"],
        "PctNamesAnyAI": s["names_any_ai_pct"], "NLegacy": s["legacy_named_sites"],
        "PctLegacyOnly": s["legacy_without_current_anthropic_pct"],
        "NInexact": s["inexact_tokens"]["sites"],
        "PctContentSignal": s["content_signal_pct"], "PctLlms": s["llms_txt_pct"], "NLlms": n_llms,
        "NAttempted": eb["attempted"], "NHomeOk": eb["ok"], "NEdge": eb["edge"], "NErrors": eb["errors"],
        "PctEdge": round(100 * eb["edge"] / eb["attempted"], 1),
        "NSkipped": s["homepage"]["skipped_by_robots"],
        "PctBotWall": s["bot_wall_pct_of_ok"], "PctThinRaw": s["thin_raw_pct_of_ok"],
        "PctSpaRoot": s["spa_empty_root_pct_of_ok"], "MedianRawWords": _thousands(int(s["median_raw_words"])),
        "NRendered": s["rendered_sites"], "MedianRawShare": round(100 * s["median_raw_share"], 1),
        "PctJsDependent": s["js_dependent_pct_of_rendered"],
        "NJsDependent": int(sites["raw_share"].notna().sum() * s["js_dependent_pct_of_rendered"] / 100 + 0.5),
        "PctJsonld": s["jsonld_pct_of_ok"], "PctOrgEntity": s["org_entity_pct_of_ok"],
        "MedianSameAs": int(s["median_same_as_links_with_org"]),
        "ProtegoAgree": s["protego_crosscheck"]["agreement_pct"],
        "ProtegoN": f"{s['protego_crosscheck']['comparisons']:,}".replace(",", "{,}"),
    }
    for bot in ["GPTBot", "ClaudeBot", "Google-Extended", "CCBot", "OAI-SearchBot", "Claude-SearchBot",
                "PerplexityBot", "ChatGPT-User", "Claude-User", "Perplexity-User"]:
        name = "Block" + bot.replace("-", "")
        macros[name] = s["block_rate_pct"][bot]
    for label, key in [("News and media", "News"), ("Social, reviews and UGC", "Social"),
                       ("Reference and science", "Reference"), ("Government and IGOs", "Gov"),
                       ("B2B SaaS", "Saas"), ("AI companies", "AI")]:
        macros[f"Retr{key}"] = sec.loc[label, "any_retrieval_block"]
        macros[f"Llms{key}"] = sec.loc[label, "llms_txt"]
    macros.update(extended_macros())
    macros.update(with_dataset(LOCAL, "Sm"))
    write_effects_table()  # small-model appendix table, from the local results
    macros.update(with_dataset(HOSTED, ""))
    macros.update(explore_macros())
    macros.update(hosted_count_macros())
    if FLAGSHIP["responses"].exists() and (E2 / "results" / "effects_flagship.csv").exists():
        macros.update(with_dataset(FLAGSHIP, "Fl"))
    STUDY2.update(HOSTED)
    macros.update(robustness_macros())
    macros.update(audit_macros())
    macros.update(extra_check_macros())
    macros.update(agentic_macros())
    macros.update(revision_macros())
    macros.update(attribution_macros())
    macros.update(site_macros())
    macros["StudyTwoInterim"] = 1 if args.tag else 0
    lines = ["% Generated by make_numbers.py; do not edit by hand."]
    for k, v in macros.items():
        if isinstance(v, str) and re.fullmatch(r"[\[\]\d\s,.+-]+", v):  # numbers and intervals: a true minus sign
            v = re.sub(r"-(0(?:\.0+)?)(?![\d.])", r"\1", v).replace("-", "\\ensuremath{-}")
        elif isinstance(v, (int, float)) and v < 0:
            v = f"\\ensuremath{{-}}{-v}"
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    (Path(__file__).parent / "numbers.tex").write_text("\n".join(lines) + "\n")
    write_hosted_tables()
    write_robustness_tables()
    write_agentic_table()
    copy_hosted_figures()
    write_agents_table()
    write_sectors_table()
    write_revision_tables()
    write_attribution_table()
    write_site_table()
    write_materials()
    print("\n".join(lines))


if __name__ == "__main__":
    main()
