"""Run Experiment 2 against one or more models.

    python run_experiment.py --models anthropic:claude-haiku-5-5 openai:gpt-5-mini
    python run_experiment.py --models mock:engine --out data/responses_mock.jsonl   # dry run

Each response is scored immediately (brand and source metrics) and appended to
the output file, so an interrupted run resumes without repeating calls. A
spending guard stops new requests once the estimated total cost reaches
--max-spend (default: AEO_MAX_SPEND_USD from .env, else $30). With many models,
--max-spend-per-model also stops any one model at its own cap and moves on.
Both caps count the spend already recorded in the output file.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from build_corpus import ATTRIBUTION, CONDITIONS, EXPLORATORY, SYSTEM, build  # noqa: E402
from aeotools.llm import complete  # noqa: E402
from aeotools.metrics import brand_metrics, source_metrics  # noqa: E402

_lock = threading.Lock()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--conditions", nargs="*", default=CONDITIONS, choices=CONDITIONS + EXPLORATORY + ATTRIBUTION,
                    help="default: the 15 pre-specified conditions; exploratory ones go to their own --out file")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--max-spend", type=float, default=float(os.environ.get("AEO_MAX_SPEND_USD", 30)))
    ap.add_argument("--max-spend-per-model", type=float, default=None)
    ap.add_argument("--out", default=str(HERE / "data" / "responses.jsonl"))
    ap.add_argument("--long", action="store_true", help="long pages (robustness check); use its own --out file")
    ap.add_argument("--temperature", type=float, default=None,
                    help="sampling temperature for Bedrock Converse models (default 0); use its own --out file")
    ap.add_argument("--trial-blocks", action="store_true", help="dated attribution follow-up: serial complete trial blocks")
    ap.add_argument("--model-caps", help="follow-up cost plan JSON with per-model caps")
    ap.add_argument("--execute", action="store_true", help="authorize paid attribution execution (otherwise dry run)")
    ap.add_argument("--part", action="store_true",
                    help="attribution only: one model per process, written under data/private/, for a parallel run")
    args = ap.parse_args()
    if set(args.conditions) & set(ATTRIBUTION):
        from attribution_runner import from_args
        return from_args(args, build(args.trials, args.conditions, long_pages=args.long))
    if args.trial_blocks or args.model_caps:
        ap.error("Follow-up block options apply only to attribution; main study execution is unchanged")
    if args.temperature is not None:
        os.environ["AEO_TEMPERATURE"] = str(args.temperature)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done, spent, by_model = set(), 0.0, {}
    if out.exists():
        for line in out.open():
            r = json.loads(line)
            spent += r.get("cost_usd", 0.0)
            by_model[r["model"]] = by_model.get(r["model"], 0.0) + r.get("cost_usd", 0.0)
            if not r.get("error"):
                done.add((r["model"], r["trial_id"], r["condition"]))

    items = build(args.trials, args.conditions, long_pages=args.long)
    state = {"spent": spent, "stopped": False, "by_model": by_model, "capped": set()}

    def over_model_cap(spec: str) -> bool:
        return args.max_spend_per_model is not None and state["by_model"].get(spec, 0.0) >= args.max_spend_per_model

    def run(spec: str, it: dict) -> None:
        if state["stopped"] or spec in state["capped"]:
            return
        res = complete(spec, SYSTEM, it["user"], max_tokens=args.max_tokens)
        rec = {"model": spec, **{k: it[k] for k in ("trial_id", "scenario", "vertical", "condition", "target",
                                                       "target_index", "guide_index", "n_sources", "target_words")},
               **res.to_dict()}
        rec.pop("spec", None)
        if not res.error:
            rec.update(brand_metrics(res.text, it["brands"], it["target"]))
            rec.update(source_metrics(res.text, it["target_index"], it["n_sources"]))
            rec["guide_cited"] = source_metrics(res.text, it["guide_index"], it["n_sources"])["cited"]
        with _lock:
            state["spent"] += res.cost_usd
            state["by_model"][spec] = state["by_model"].get(spec, 0.0) + res.cost_usd
            if state["spent"] >= args.max_spend:
                state["stopped"] = True
            if over_model_cap(spec):
                state["capped"].add(spec)
            with out.open("a") as fh:
                fh.write(json.dumps(rec) + "\n")

    for spec in args.models:
        todo = [it for it in items if (spec, it["trial_id"], it["condition"]) not in done]
        if over_model_cap(spec):
            print(f"{spec}: per-model cap already reached (${state['by_model'][spec]:.2f}); skipping", flush=True)
            continue
        print(f"{spec}: {len(todo)} prompts to run (spent so far ${state['spent']:.2f})", flush=True)
        with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run, spec, it) for it in todo]
            for i, f in enumerate(cf.as_completed(futures), 1):
                f.result()
                if i % 100 == 0:
                    print(f"  {i}/{len(todo)}  spent ${state['spent']:.2f}", flush=True)
        if state["stopped"]:
            print(f"Spending guard reached (${state['spent']:.2f} >= ${args.max_spend:.2f}); stopping.")
            return 1
        if spec in state["capped"]:
            print(f"  per-model cap reached for {spec} (${state['by_model'][spec]:.2f}); moving on", flush=True)
    print(f"Done. Estimated total spend ${state['spent']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
