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


def report() -> None:
    import pandas as pd
    from analyze import short_name
    items = pd.read_json(ITEMS, lines=True)
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
HUMAN_QUESTION = ("Does the answer pass on any specific information that appears in the added content (for example its "
                  "figures, the organisations or publications it names, the person it quotes or what they said, the "
                  "limitation it states, its date, or its promotional claims)? Naming the brand or describing its "
                  "ordinary features does not count.")


def sheet() -> None:
    """150 items for a blind human check (specified 6 Nov 2026, before any human label): from the items both judges
    labelled, 20 treated answers per edit (120) and 5 baseline answers per edit (30), shuffled, with the detector's and
    the judges' labels hidden. The rater sees the same added text, answer and question as the judges."""
    import pandas as pd
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.worksheet.datavalidation import DataValidation
    items = pd.read_json(ITEMS, lines=True)
    lab = pd.read_json(LABELS_FILE, lines=True)
    both = lab[lab["label"].isin(["YES", "NO"])].groupby("id")["judge"].nunique()
    items = items[items["id"].isin(both[both == 2].index)]
    pick = pd.concat([g.sample(n=min(20 if kind == "treated" else 5, len(g)), random_state=7)
                      for (kind, _), g in items.groupby(["kind", "condition"])])
    pick = pick.sample(frac=1, random_state=7).reset_index(drop=True)
    pick["code"] = [f"H{i + 1:03d}" for i in range(len(pick))]  # opaque: the item id would reveal the condition
    pick[["code", "id"]].to_csv(HUMAN_KEY, index=False)
    wb = Workbook()
    ins = wb.active
    ins.title = "Instructions"
    for line in ["Human check of the absorption measure (about 1 hour; 150 rows).",
                 "",
                 "Each row shows content that was added to one brand's web page and an AI assistant's answer.",
                 "For each row, answer this question in the 'Repeats added content?' column with YES or NO:",
                 HUMAN_QUESTION,
                 "",
                 "Some answers never saw the added content; that is deliberate. Judge only what you read in the row.",
                 "Do not look up the detector's or the AI judges' labels before you finish. Leave a note if unsure.",
                 "When done, save the file in place and tell Claude; `python3 analyze_absorption_judge.py human` scores it."]:
        ins.append([line])
    ins.column_dimensions["A"].width = 120
    ws = wb.create_sheet("Label")
    ws.append(["Row", "Code", "Brand", "Added content", "Answer", HUMAN_COL, "Note (optional)"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for i, r in pick.iterrows():
        ws.append([i + 1, r["code"], r["brand"], r["added"], r["answer"], "", ""])
    for col, w in zip("ABCDEFG", [6, 14, 14, 50, 100, 16, 30]):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    dv = DataValidation(type="list", formula1='"YES,NO"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"F2:F{len(pick) + 1}")
    ws.freeze_panes = "D2"
    wb.save(HUMAN_SHEET)
    print(f"wrote {len(pick)} rows to {HUMAN_SHEET.relative_to(HERE)} "
          f"({(pick['kind'] == 'treated').sum()} treated, {(pick['kind'] == 'baseline').sum()} baseline; labels hidden)")


def human() -> None:
    """Score the filled human sheet against the detector and both judges (agreement, Cohen's kappa, precision and
    recall of the detector with the human label as reference, false positives on baseline answers)."""
    import pandas as pd
    from analyze import short_name
    filled = pd.read_excel(HUMAN_SHEET, sheet_name="Label")
    filled["human"] = filled[HUMAN_COL].astype(str).str.strip().str.upper().map({"YES": True, "NO": False})
    filled = filled.dropna(subset=["human"])
    if filled.empty:
        print("no human labels yet")
        return
    items = pd.read_json(ITEMS, lines=True).set_index("id")
    lab = pd.read_json(LABELS_FILE, lines=True)
    lab = lab[lab["label"].isin(["YES", "NO"])].drop_duplicates(["id", "judge"], keep="last")
    lab["yes"] = lab["label"] == "YES"
    wide = lab.pivot(index="id", columns="judge", values="yes")
    wide.columns = [short_name(c) for c in wide.columns]
    key = pd.read_csv(HUMAN_KEY).set_index("code")["id"]
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
    out.to_csv(RES / "absorption_human.csv", index=False)
    allrow = out[out["condition"] == "all"].set_index("rater")
    summary = {"n_labelled": int(len(df)), "n_treated": int((df["kind"] == "treated").sum()),
               "n_baseline": int((df["kind"] == "baseline").sum()),
               "by_rater": {r: allrow.loc[r].to_dict() for r in allrow.index}}
    (RES / "absorption_human_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(out.to_string(index=False))


if __name__ == "__main__":
    {"prepare": prepare, "judge": judge, "report": report, "sheet": sheet, "human": human}[
        sys.argv[1] if len(sys.argv) > 1 else "report"]()
