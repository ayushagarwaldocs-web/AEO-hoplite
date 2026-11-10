"""Check the keyword detector of analyze_absorption.py against model judges (README, "Robustness checks").

    python3 analyze_absorption_judge.py prepare                 # sample answers (needs pandas)
    ../../.venv-local/bin/python analyze_absorption_judge.py judge   # ask the judges (needs boto3; resumes)
    python3 analyze_absorption_judge.py report                  # agreement (needs pandas)
    python3 analyze_absorption_judge.py sheet                   # 150 items for an optional human check

From the hosted models' main answers, for each detectable edit (statistics, citations, quotation, limitations,
freshness, persuasive) we draw 120 answers that name the target, plus 40 baseline answers from the same trials as
a false-positive check (the baseline answer never saw the added text). Two judges, Claude Haiku 4.5 and DeepSeek
V3.2, see the added text and the answer and say whether the answer passes on anything specific from it.
Exploratory; not pre-specified.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import re
import random
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

DATA, RES = HERE / "data", HERE / "results"
ITEMS, LABELS_FILE = DATA / "judge_items.jsonl", DATA / "judge_labels.jsonl"
EDITS = ["statistics", "citations", "quotation", "limitations", "freshness", "persuasive"]
N_TREATED, N_BASELINE = 120, 40
JUDGES = ["bedrock:global.anthropic.claude-haiku-4-5-20251001-v1:0", "bedrock:deepseek.v3.2"]
MAX_SPEND = 3.0
SYSTEM_J = "You check whether an AI assistant's answer repeats specific content from a web page. Reply with YES or NO only."


def judge_prompt(brand: str, added: str, answer: str) -> str:
    return (f"Content that was added to {brand}'s web page:\n\"\"\"\n{added}\n\"\"\"\n\n"
            f"The assistant's answer:\n\"\"\"\n{answer}\n\"\"\"\n\n"
            "Does the answer pass on any specific information that appears in the added content (for example its "
            "figures, the organisations or publications it names, the person it quotes or what they said, the "
            "limitation it states, its date, or its promotional claims)? Naming "
            f"{brand} or describing its ordinary features does not count. Reply YES or NO.")


def added_text(sc: dict, b: dict, cond: str) -> str:
    from build_corpus import main_paragraph, target_body
    if cond == "freshness":
        return "Last updated: October 2026.\nPricing (as of October 2026)."
    return target_body(sc, b, cond).replace(main_paragraph(sc, b), "").strip()


def prepare() -> None:
    import pandas as pd
    from analyze_absorption import detectors
    from scenarios import SCENARIOS
    scen = {s["id"]: s for s in SCENARIOS}
    brands = json.loads((DATA / "brands.json").read_text())
    lookup = {(sc, b["core"]): b for sc, v in brands.items() for b in v["brands"]}
    df = pd.read_json(DATA / "responses_bedrock.jsonl", lines=True)
    df = df[df["error"].isna()]
    base = df[df["condition"] == "baseline"].set_index(["model", "trial_id"])
    rng = random.Random(20261106)
    items = []
    for cond in EDITS:
        treated = df[(df["condition"] == cond) & df["mentioned"].astype(bool)]
        rows = treated.sample(n=min(N_TREATED, len(treated)), random_state=rng.randint(0, 10**6))
        for kind, sample in (("treated", rows), ("baseline", rows.head(N_BASELINE))):
            for _, r in sample.iterrows():
                b = lookup[(r["scenario"], r["target"])]
                text = r["text"] if kind == "treated" else base.loc[(r["model"], r["trial_id"]), "text"]
                items.append({"id": f"{cond}|{kind}|{r['model']}|{r['trial_id']}", "condition": cond, "kind": kind,
                              "model": r["model"], "trial_id": r["trial_id"], "brand": b["name"],
                              "added": added_text(scen[r["scenario"]], b, cond), "answer": text,
                              "detector": bool(detectors(b)[cond](text))})
    with ITEMS.open("w") as fh:
        for it in items:
            fh.write(json.dumps(it) + "\n")
    print(f"wrote {len(items)} items to {ITEMS.name}")


def judge() -> None:
    from aeotools.llm import complete
    items = [json.loads(line) for line in ITEMS.open()]
    done, spent = set(), 0.0
    if LABELS_FILE.exists():
        for line in LABELS_FILE.open():
            r = json.loads(line)
            spent += r.get("cost_usd", 0.0)
            if r.get("label") in ("YES", "NO"):
                done.add((r["id"], r["judge"]))
    lock, state = threading.Lock(), {"spent": spent}

    def run(spec: str, it: dict) -> None:
        if state["spent"] >= MAX_SPEND:
            return
        res = complete(spec, SYSTEM_J, judge_prompt(it["brand"], it["added"], it["answer"]), max_tokens=16)
        raw = (res.text or "").strip().upper()
        label = "YES" if raw.startswith("YES") else "NO" if raw.startswith("NO") else ""
        with lock:
            state["spent"] += res.cost_usd
            with LABELS_FILE.open("a") as fh:
                fh.write(json.dumps({"id": it["id"], "judge": spec, "label": label, "raw": raw[:40],
                                     "error": res.error, "cost_usd": res.cost_usd}) + "\n")

    for spec in JUDGES:
        todo = [it for it in items if (it["id"], spec) not in done]
        print(f"{spec}: {len(todo)} items (spent so far ${state['spent']:.2f})", flush=True)
        with cf.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda it: run(spec, it), todo))
    print(f"done; estimated spend ${state['spent']:.2f}")


def kappa(a, b) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def refresh_detector_fields(items: list[dict], responses: list[dict], brands: dict) -> list[dict]:
    """Recompute detector flags for the saved sample without changing its membership or labels."""
    from analyze_absorption import detectors

    response_index = {}
    for response in responses:
        if response.get("error") is None:
            key = (response["model"], response["trial_id"], response["condition"])
            if key in response_index:
                raise ValueError(f"duplicate response row for {key}")
            response_index[key] = response
    lookup = {(scenario, brand["core"]): brand for scenario, group in brands.items()
              for brand in group["brands"]}
    refreshed = []
    for item in items:
        source_condition = item["condition"] if item["kind"] == "treated" else "baseline"
        key = (item["model"], item["trial_id"], source_condition)
        source = response_index.get(key)
        if source is None:
            raise ValueError(f"response source missing for saved judge item {item['id']}")
        brand = lookup.get((source["scenario"], source["target"]))
        if brand is None:
            raise ValueError(f"brand metadata missing for saved judge item {item['id']}")
        siblings = tuple({name for other in brands[source["scenario"]]["brands"]
                          if other["core"] != source["target"]
                          for name in (other["core"], other["name"])})
        updated = dict(item)
        updated["detector"] = bool(detectors(brand, siblings)[item["condition"]](item["answer"]))
        refreshed.append(updated)
    return refreshed


def refresh_stored_detector_fields() -> list[dict]:
    """Refresh only detector values in judge_items.jsonl; keep item rows and labels intact."""
    with (DATA / "responses_bedrock.jsonl").open() as fh:
        responses = [json.loads(line) for line in fh]
    brands = json.loads((DATA / "brands.json").read_text())
    with ITEMS.open() as fh:
        original = [json.loads(line) for line in fh]
    refreshed = refresh_detector_fields(original, responses, brands)
    if any(old.get("detector") != new["detector"] for old, new in zip(original, refreshed)):
        temporary = ITEMS.with_suffix(ITEMS.suffix + ".tmp")
        with temporary.open("w") as fh:
            for item in refreshed:
                fh.write(json.dumps(item) + "\n")
        temporary.replace(ITEMS)
    return refreshed


def report() -> None:
    import pandas as pd
    from analyze import short_name
    items = pd.DataFrame(refresh_stored_detector_fields())
    lab = pd.read_json(LABELS_FILE, lines=True)
    lab = lab[lab["label"].isin(["YES", "NO"])].drop_duplicates(["id", "judge"], keep="last")
    lab["judge_yes"] = lab["label"] == "YES"
    wide = lab.pivot(index="id", columns="judge", values="judge_yes")
    wide.columns = [short_name(c) for c in wide.columns]
    df = items.set_index("id").join(wide, how="inner")
    judges = list(wide.columns)
    rows = []
    for j in judges:
        for cond in EDITS + ["all"]:
            t = df[(df["kind"] == "treated") & ((df["condition"] == cond) if cond != "all" else True)].dropna(subset=[j])
            bl = df[(df["kind"] == "baseline") & ((df["condition"] == cond) if cond != "all" else True)].dropna(subset=[j])
            det, jud = t["detector"].astype(bool).tolist(), t[j].astype(bool).tolist()
            tp = sum(d and x for d, x in zip(det, jud))
            rows.append({"judge": j, "condition": cond, "n": len(t),
                         "detector_rate": round(100 * sum(det) / len(t), 1), "judge_rate": round(100 * sum(jud) / len(t), 1),
                         "agreement": round(100 * sum(d == x for d, x in zip(det, jud)) / len(t), 1),
                         "kappa": round(kappa(det, jud), 2),
                         "precision": round(100 * tp / max(1, sum(det)), 1), "recall": round(100 * tp / max(1, sum(jud)), 1),
                         "fp_detector": round(100 * bl["detector"].astype(bool).mean(), 1),
                         "fp_judge": round(100 * bl[j].astype(bool).mean(), 1), "n_baseline": len(bl)})
    out = pd.DataFrame(rows)
    RES.mkdir(exist_ok=True)
    out.to_csv(RES / "absorption_judge.csv", index=False)
    t = df[df["kind"] == "treated"].dropna(subset=judges)
    between = round(kappa(t[judges[0]].astype(bool).tolist(), t[judges[1]].astype(bool).tolist()), 2) if len(judges) == 2 else None
    summary = {"judges": judges, "n_treated": int((df["kind"] == "treated").sum()),
               "n_baseline": int((df["kind"] == "baseline").sum()), "kappa_between_judges": between,
               "by_judge": {j: out[(out["judge"] == j) & (out["condition"] == "all")].iloc[0].to_dict() for j in judges}}
    (RES / "absorption_judge_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(out.to_string(index=False))
    print("kappa between judges:", between)


HUMAN_SHEET = RES / "human_check_sheet.xlsx"
HUMAN_KEY = DATA / "human_check_key.csv"
HUMAN_COL = "Repeats added content? (YES/NO)"
EVIDENCE_COL = "Evidence for YES (copy the answer's words)"
HUMAN_QUESTION = ("Does the answer pass on any specific information that appears in the added content (for example its "
                  "figures, the organisations or publications it names, the person it quotes or what they said, the "
                  "limitation it states, its date, or its promotional claims)? Naming the brand or describing its "
                  "ordinary features does not count.")
# Round 3 (9 Nov 2026): the returned second-pass labels followed the kind of added content rather than the answer
# (every statistics, citations and quotation row YES, controls included) and often quoted column D as evidence, so the
# new sheet uses 150 answers no rater has seen and names those mistakes up front.
HUMAN_PITFALLS = [
    "READ THIS FIRST: THE MISTAKES THAT MADE EARLIER LABELS UNUSABLE",
    "1. Judging column D instead of column E. The question is about the ANSWER (column E): does it repeat a detail from "
    "column D? Many answers recommend other brands and never mention the brand in column C at all. Those are NO, however "
    "rich column D is.",
    "2. Copying the evidence from column D. Column G must hold words copied from the answer (column E). If no words in E "
    "carry a detail from D, the label is NO.",
    "3. Counting ordinary features, prices or use cases ('dual motors', 'strict SLAs', 'free developer plan', '$34 per "
    "session'). The brand's normal page lists these too, so they do not count, even when they appear inside a quotation.",
    "4. Counting details the answer gives for another brand. A detail counts only if the answer passes it on about the "
    "brand in column C.",
    "5. Writing 'does not repeat' in a note but answering YES. If you doubt it, the label is NO.",
    "Some answers never saw the added content; that is deliberate, and for them the right label is NO.",
    "",
]
HUMAN_INSTRUCTIONS = [
    "HUMAN CHECK: 150 rows, about one hour. Work in the Label tab; the Progress tab counts what is left.",
    "",
    "THE QUESTION FOR EVERY ROW (column F, YES or NO):",
    HUMAN_QUESTION,
    "",
    "HOW TO DO ONE ROW",
    "1. Read column D (Added content) and note its specific details (see the list below).",
    "2. Read column E (Answer). Look for those details; Cmd+F in the browser helps find a number or a name.",
    "3. If the answer repeats at least one detail (exactly or clearly reworded): put YES in F, then copy the words "
    "from column E that carry it and paste them into G. Copy a short phrase from the answer itself, not from D.",
    "4. Otherwise put NO in F and leave G empty.",
    "5. Look at column I. It must say ok. If it says 'these words are not in the answer', copy the phrase again "
    "from column E.",
    "6. Unsure? Decide anyway and write why in column H.",
    "",
    "THE DETAILS TO LOOK FOR, BY KIND OF ADDED CONTENT",
    "Figures ('used by more than 12,000 ... rating of 4.5 out of 5 from 11,793 reviews ... reports ...'): the user "
    "count, the rating, the number of reviews, the reported figure. YES: 'rated 4.5/5', 'over 12,000 developers'. "
    "NO: 'highly rated' with no number, or the price.",
    "Evaluation ('In an independent 2026 evaluation by the X Testing Lab, ... scored 86/100 ... included in Y Review's "
    "buyer's guide'): the lab, the score, the review site, the guide. YES: 'scored 86/100', 'featured in Y Review'.",
    "Quotation ('\"... gets the essentials right ...,\" said Dr. Name, ... at Institution. \"... easier options to "
    "recommend ...\"'): the expert's name, the institution, the quote's own words, or 'an expert recommends it'. The "
    "features named inside the quote do NOT count: they are on the brand's normal page too.",
    "Limitation ('Limitations: ... not the best fit for X, and its Y is more basic than some alternatives'): YES if "
    "the answer says it is not ideal for X or that its Y is basic or limited.",
    "Date ('Last updated: October 2026'): YES only if the answer gives that date or says the page was recently updated.",
    "Claims ('the industry-leading, best-in-class choice that experts and customers trust most. Nothing else ... comes "
    "close'): YES only for these claims, e.g. 'industry-leading', 'best-in-class', 'trusted by experts', 'nothing "
    "comes close'. Ordinary praise such as 'a great option' or 'best for small teams' is NO.",
    "",
    "NEVER COUNTS: the brand's name, its normal features, its price, or who it is for. If the answer does not name "
    "the brand, the label is almost always NO. Some answers never saw the added content; that is deliberate, and "
    "many rows will be NO. There is no target number of YES.",
    "",
    "RULES: start from this blank file, not from earlier labels; decide each row yourself; do not use an AI; do not "
    "open the key or judge files; do not sort, filter, delete rows or rename tabs.",
    "",
    "WHEN DONE: the Progress tab must show 150 rows labelled and 150 rows passing the check. In Google Sheets choose "
    "File > Download > Microsoft Excel (.xlsx) and tell Claude the exact name of the downloaded file.",
]


def human_paths(rnd: int | None) -> tuple[Path, Path]:
    """Sheet and key of a human-check round: rounds 1 and 2 share the first sample; later rounds have their own."""
    if not rnd or rnd <= 2:
        return HUMAN_SHEET, HUMAN_KEY
    return RES / f"human_check_sheet_round{rnd}.xlsx", DATA / f"human_check_key_round{rnd}.csv"


def sheet(rnd: int | None = None) -> None:
    """150 items for a blind human check (specified 6 Nov 2026, before any human label): from the items both judges
    labelled, 20 treated answers per edit (120) and 5 baseline answers per edit (30), shuffled, with the detector's and
    the judges' labels hidden. The rater sees the same added text, answer and question as the judges. From round 3 on,
    the sample leaves out every answer an earlier round showed, so a rater who has seen feedback on those rows starts
    blind again."""
    import pandas as pd
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.worksheet.datavalidation import DataValidation
    sheet_path, key_path = human_paths(rnd)
    items = pd.read_json(ITEMS, lines=True)
    lab = pd.read_json(LABELS_FILE, lines=True)
    both = lab[lab["label"].isin(["YES", "NO"])].groupby("id")["judge"].nunique()
    items = items[items["id"].isin(both[both == 2].index)]
    seed = 7 if not rnd or rnd <= 2 else 1000 + rnd
    if rnd and rnd > 2:
        shown = set()
        for r in range(2, rnd):
            shown |= set(pd.read_csv(human_paths(r)[1])["id"])
        items = items[~items["id"].isin(shown)]
    pick = pd.concat([g.sample(n=min(20 if kind == "treated" else 5, len(g)), random_state=seed)
                      for (kind, _), g in items.groupby(["kind", "condition"])])
    pick = pick.sample(frac=1, random_state=seed).reset_index(drop=True)
    pick["code"] = [f"H{i + 1:03d}" for i in range(len(pick))]  # opaque: the item id would reveal the condition
    if rnd and rnd > 2:
        pick["code"] = [f"R{rnd}-{c}" for c in pick["code"]]
    pick[["code", "id"]].to_csv(key_path, index=False)
    wb = Workbook()
    ins = wb.active
    ins.title = "Instructions"
    # Second pass (7 Nov 2026): the first pass marked YES on half the baseline answers, so the decision rule is spelled
    # out, every YES needs the answer's own words as evidence, and (fresh sheet, 7 Nov evening) a formula column and a
    # Progress tab show the rater whether that evidence occurs in the answer, the same check the scorer makes.
    for line in (HUMAN_PITFALLS if rnd and rnd > 2 else []) + HUMAN_INSTRUCTIONS:
        ins.append([line])
    ins.column_dimensions["A"].width = 130
    ws = wb.create_sheet("Label")
    ws.append(["Row", "Code", "Brand", "Added content", "Answer", HUMAN_COL, EVIDENCE_COL, "Note (optional)",
               "Check (automatic)"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for i, r in pick.iterrows():
        n = i + 2
        check = (f'=IF(F{n}="","to do",IF(F{n}="NO",IF(G{n}="","ok","NO: clear column G"),'
                 f'IF(G{n}="","YES: paste the answer\'s words in G",'
                 f'IF(ISNUMBER(SEARCH(G{n},E{n})),"ok","YES: these words are not in the answer"))))')
        ws.append([i + 1, r["code"], r["brand"], r["added"], r["answer"], "", "", "", check])
    for col, w in zip("ABCDEFGHI", [6, 10, 14, 50, 100, 14, 40, 22, 30]):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    dv = DataValidation(type="list", formula1='"YES,NO"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"F2:F{len(pick) + 1}")
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.styles import PatternFill
    last = len(pick) + 1
    ws.conditional_formatting.add(f"I2:I{last}", FormulaRule(formula=['AND($I2<>"ok",$I2<>"to do")'],
                                                             fill=PatternFill("solid", fgColor="F8D7DA")))
    ws.conditional_formatting.add(f"I2:I{last}", FormulaRule(formula=['$I2="ok"'],
                                                             fill=PatternFill("solid", fgColor="D4EDDA")))
    ws.freeze_panes = "D2"
    pr = wb.create_sheet("Progress")
    for label, formula in [("Rows labelled (need 150)", f"=COUNTA(Label!F2:F{last})"),
                           ("YES", f'=COUNTIF(Label!F2:F{last},"YES")'),
                           ("NO", f'=COUNTIF(Label!F2:F{last},"NO")'),
                           ("Rows passing the check (need 150)", f'=COUNTIF(Label!I2:I{last},"ok")'),
                           ("Rows still to do", f'=COUNTIF(Label!I2:I{last},"to do")'),
                           ("Rows with a problem to fix", f'=COUNTIF(Label!I2:I{last},"*:*")')]:
        pr.append([label, formula])
    pr.column_dimensions["A"].width = 40
    wb.save(sheet_path)
    print(f"wrote {len(pick)} rows to {sheet_path.relative_to(HERE)} "
          f"({(pick['kind'] == 'treated').sum()} treated, {(pick['kind'] == 'baseline').sum()} baseline; labels hidden)")


def human(rnd: int | None = None) -> None:
    """Score the filled human sheet against the detector and both judges (agreement, Cohen's kappa, precision and
    recall of the detector with the human label as reference, false positives on baseline answers)."""
    import pandas as pd
    from analyze import short_name
    sheet_path, key_path = human_paths(rnd)
    sfx = f"_round{rnd}" if rnd and rnd > 2 else ""
    filled = pd.read_excel(sheet_path, sheet_name="Label")
    filled["human"] = filled[HUMAN_COL].astype(str).str.strip().str.upper().map({"YES": True, "NO": False})
    filled = filled.dropna(subset=["human"])
    if filled.empty:
        print("no human labels yet")
        return
    audit = {}
    if EVIDENCE_COL in filled:  # second pass: every YES must quote words that occur in the answer
        norm = lambda t: re.sub(r"[^a-z0-9]+", " ", str(t).lower()).strip()  # noqa: E731
        ev = filled[EVIDENCE_COL].where(filled[EVIDENCE_COL].notna(), "").astype(str).str.strip()
        yes = filled["human"].astype(bool)
        found = [bool(e) and norm(e) in norm(a) for e, a in zip(ev, filled["Answer"])]
        filled["evidence_given"], filled["evidence_found"] = ev.ne("") & yes, pd.Series(found, index=filled.index) & yes
        audit = {"yes": int(yes.sum()), "yes_with_evidence": int(filled["evidence_given"].sum()),
                 "evidence_found_in_answer": int(filled["evidence_found"].sum())}
        filled[["Code", "human", EVIDENCE_COL, "evidence_given", "evidence_found"]].to_csv(
            RES / f"absorption_human_evidence{sfx}.csv", index=False)
        print(f"evidence audit: {audit}")
    items = pd.read_json(ITEMS, lines=True).set_index("id")
    lab = pd.read_json(LABELS_FILE, lines=True)
    lab = lab[lab["label"].isin(["YES", "NO"])].drop_duplicates(["id", "judge"], keep="last")
    lab["yes"] = lab["label"] == "YES"
    wide = lab.pivot(index="id", columns="judge", values="yes")
    wide.columns = [short_name(c) for c in wide.columns]
    key = pd.read_csv(key_path).set_index("code")["id"]
    filled["id"] = filled["Code"].map(key)
    df = filled.set_index("id")[["human"]].join(items, how="inner").join(wide, how="left")
    raters = ["detector"] + list(wide.columns)
    rows = []
    for cond in EDITS + ["all"]:
        sel = (df["condition"] == cond) if cond != "all" else pd.Series(True, index=df.index)
        t, bl = df[sel & (df["kind"] == "treated")], df[sel & (df["kind"] == "baseline")]
        for r in raters:
            tt = t.dropna(subset=[r])
            h, x = tt["human"].astype(bool).tolist(), tt[r].astype(bool).tolist()
            tp = sum(a and b for a, b in zip(h, x))
            rows.append({"rater": r, "condition": cond, "n": len(tt), "human_rate": round(100 * sum(h) / max(1, len(h)), 1),
                         "rater_rate": round(100 * sum(x) / max(1, len(x)), 1),
                         "agreement": round(100 * sum(a == b for a, b in zip(h, x)) / max(1, len(h)), 1),
                         "kappa": round(kappa(h, x), 2) if len(h) else None,
                         "precision": round(100 * tp / max(1, sum(x)), 1), "recall": round(100 * tp / max(1, sum(h)), 1),
                         "n_baseline": len(bl), "fp_human": round(100 * bl["human"].astype(bool).mean(), 1) if len(bl) else None,
                         "fp_rater": round(100 * bl[r].astype(bool).mean(), 1) if len(bl.dropna(subset=[r])) else None})
    out = pd.DataFrame(rows)
    out.to_csv(RES / f"absorption_human{sfx}.csv", index=False)
    allrow = out[out["condition"] == "all"].set_index("rater")
    summary = {"n_labelled": int(len(df)), "n_treated": int((df["kind"] == "treated").sum()),
               "n_baseline": int((df["kind"] == "baseline").sum()),
               "by_rater": {r: allrow.loc[r].to_dict() for r in allrow.index}, "evidence_audit": audit}
    (RES / f"absorption_human_summary{sfx}.json").write_text(json.dumps(summary, indent=1, default=str))
    print(out.to_string(index=False))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    rnd = int(sys.argv[2]) if len(sys.argv) > 2 else None  # sheet/human: the round (3 or later: a new sample)
    if cmd in ("sheet", "human"):
        {"sheet": sheet, "human": human}[cmd](rnd)
    else:
        {"prepare": prepare, "judge": judge, "report": report}[cmd]()
