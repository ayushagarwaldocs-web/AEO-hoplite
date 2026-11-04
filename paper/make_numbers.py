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

ROOT = Path(__file__).resolve().parents[1]
E1 = ROOT / "experiments" / "exp1_web_readiness"


def edge_breakdown() -> dict:
    sites = [json.loads(line) for line in (E1 / "data" / "raw" / "sites.jsonl").open()]
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
    return {"attempted": attempted, "ok": ok, "edge": edge, "errors": errors, "other": other}


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
    inf, bar = e["inference"], e["barriers"]
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
# Set by --tag/--responses to draft against an interim analysis (analyze.py --tag interim).
STUDY2 = {"suffix": "", "responses": E2 / "data" / "responses.jsonl"}


def _res(name: str) -> Path:
    stem, ext = name.rsplit(".", 1)
    return E2 / "results" / f"{stem}{STUDY2['suffix']}.{ext}"


def _wilson(k: float, n: float, z: float = 1.96) -> tuple[float, float]:
    p, d = k / n, 1 + z * z / n
    centre, half = (p + z * z / (2 * n)) / d, z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / d
    return 100 * (centre - half), 100 * (centre + half)


def _model_code(model: str) -> str:
    if model == "pooled":
        return "All"
    name = model.split(":", 1)[-1]
    return "".join(ch for ch in name.split("-")[0].split(".")[0] if ch.isalpha()).capitalize()


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
    out["HThreeVerdict"] = "Supported" if all(v["supported"] for v in h["H3"].values()) else "Not supported"
    for c, v in h["H4"].items():
        out[f"HFour{_camel(c)}"] = pp(v["effect"])
        out[f"HFour{_camel(c)}CI"] = f"[{100 * v['ci90'][0]:.1f}, {100 * v['ci90'][1]:.1f}]"
        out[f"HFour{_camel(c)}Verdict"] = "within" if v["supported"] else "not within"
    out["HFourVerdict"] = "Supported" if all(v["supported"] for v in h["H4"].values()) else "Not supported"
    p5 = h["H5"]
    out.update(HFiveChi=p5["chi2"], HFiveP=_fmt_p(p5["p_perm"]))
    strat = p5.get("stratified")
    if strat:
        out.update(HFiveStratChi=strat["chi2"], HFiveStratP=_fmt_p(strat["p_perm"]))
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
    out.update(RhoMenMin=min(rhos), RhoMenMax=max(rhos))
    for code in ("Llama", "Qwen", "Granite"):  # placeholders while a model's run is incomplete (interim drafts)
        for name in ("Men", "Top", "Cit", "AnyCit", "Words", "Brands"):
            out.setdefault(f"Prof{name}{code}", "--")
    eff = pd.read_csv(_res("effects.csv"))
    pooled = eff[eff["model"] == "pooled"].pivot(index="condition", columns="outcome", values="effect")
    out["RhoPawc"] = f"{pooled['pawc'].corr(pooled['mentioned'], method='spearman'):.2f}"
    single = ["statistics", "citations", "quotation", "answer_first", "qa_format", "spec_table", "limitations",
              "freshness", "persuasive", "keyword_stuffing"]
    top = eff[(eff["model"] == "pooled") & (eff["outcome"] == "top_pick") & eff["condition"].isin(single)]
    out["NTopSig"] = _word(int(((top["p_holm"] < 0.05) & (top["effect"] > 0)).sum()))
    out["NTopSigCap"] = out["NTopSig"].capitalize()
    out["NSingle"] = _word(len(single))
    # Access versus content: each model's baseline mention rate against its best edit to the brand's own page
    on_page = ["statistics", "citations", "quotation", "answer_first", "qa_format", "spec_table", "limitations",
               "freshness", "persuasive", "keyword_stuffing", "combined"]
    men = eff[(eff["outcome"] == "mentioned") & (eff["condition"].isin(on_page)) & (eff["model"] != "pooled")]
    best = men.loc[men.groupby("model")["effect"].idxmax()].set_index("model")["effect"] * 100
    base = {m: v["mention"] for m, v in h["profiles"].items()}
    out.update(BestOnPageMin=f"{best.min():.0f}", BestOnPageMax=f"{best.max():.0f}",
               BaseMenMin=f"{min(base.values()):.0f}", BaseMenMax=f"{max(base.values()):.0f}",
               AccessRatioMin=f"{min(base[m] / best[m] for m in best.index):.1f}",
               AccessRatioMax=f"{max(base[m] / best[m] for m in best.index):.1f}")
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
    "persuasive": "Persuasive tone", "keyword_stuffing": "Keyword stuffing", "filler": "Length placebo",
    "injection": "Hidden instruction", "combined": "Combined",
}


def _short(model: str) -> str:
    name = re.sub(r"(?i)-instruct(-4bit)?$", "", model.split(":", 1)[-1])
    return re.sub(r"(\d)b$", r"\1B", name[:1].upper() + name[1:])


def _cell(r: pd.Series, ci: bool = False) -> str:
    star = "$^{*}$" if r["p_holm"] < 0.05 else ""
    text = f"${100 * r['effect']:+.1f}${star}"
    return text + (f" {{\\footnotesize$[{100 * r['ci_low']:.0f}, {100 * r['ci_high']:.0f}]$}}" if ci else "")


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
    (Path(__file__).parent / "table_study2.tex").write_text(head + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")

    # Appendix: every model and outcome, against the baseline and against the length placebo
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
    rows = [f"{r['sector'].replace('&', '\\&')} & {r['sites']} & {fmt(r['GPTBot'])} & {fmt(r['OAI-SearchBot'])} & "
            f"{fmt(r['any_retrieval_block'])} & {fmt(r['llms_txt'])} & {fmt(r['org_entity'])} & {fmt(r['js_dependent'])} \\\\"
            for _, r in sec.iterrows()]
    tex = ("\\begin{tabular}{@{}lrrrrrrr@{}}\n\\toprule\n"
           "Sector & Sites & GPTBot & OAI-Search & Any answer & llms.txt & Org.\\ entity & JS-dep. \\\\\n"
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="", help="read Study 2 results written by analyze.py --tag (drafts only)")
    ap.add_argument("--responses", default=None, help="responses file matching --tag")
    args = ap.parse_args()
    if args.tag:
        STUDY2["suffix"] = f"_{args.tag}"
    if args.responses:
        STUDY2["responses"] = Path(args.responses)
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
    macros.update(study2_macros())
    macros.update(study2_extra_macros())
    macros["StudyTwoInterim"] = 1 if args.tag else 0
    lines = ["% Generated by make_numbers.py; do not edit by hand."]
    for k, v in macros.items():
        if isinstance(v, str) and re.fullmatch(r"[\[\]\d\s,.+-]+", v):  # numbers and intervals: a true minus sign
            v = re.sub(r"-(0(?:\.0+)?)(?![\d.])", r"\1", v).replace("-", "\\ensuremath{-}")
        elif isinstance(v, (int, float)) and v < 0:
            v = f"\\ensuremath{{-}}{-v}"
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    (Path(__file__).parent / "numbers.tex").write_text("\n".join(lines) + "\n")
    write_effects_table()
    write_agents_table()
    write_sectors_table()
    write_materials()
    print("\n".join(lines))


if __name__ == "__main__":
    main()
