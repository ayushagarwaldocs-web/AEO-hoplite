"""Experiment 1: AI-readiness measurement across organisational websites.

Phase A (default): robots.txt, llms.txt and homepage fetches for every domain.
Phase B (--render): headless-Chrome render of each fetchable homepage.

Records are appended to data/raw/*.jsonl, so an interrupted run resumes where
it stopped. The crawler identifies itself, honours robots.txt for its own
token before touching a homepage, and sends at most five requests per site.

    python run_measurement.py            # phase A
    python run_measurement.py --render   # phase B
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from aeotools import audit as A  # noqa: E402
from aeotools.html_signals import visible_text, word_count  # noqa: E402

RAW = HERE / "data" / "raw"
SITES = RAW / "sites.jsonl"
ROBOTS = RAW / "robots_raw.jsonl"
RENDERS = RAW / "renders.jsonl"
_lock = threading.Lock()


def append(path: Path, record: dict) -> None:
    with _lock, path.open("a") as fh:
        fh.write(json.dumps(record) + "\n")


def done(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {json.loads(line)["domain"] for line in path.open() if line.strip()}


def load_domains() -> list[tuple[str, str]]:
    with (HERE / "domains.csv").open() as fh:
        return [(r["domain"], r["sector"]) for r in csv.DictReader(fh)]


def phase_a(domain: str, sector: str) -> str:
    started = time.time()
    rep = A.audit(domain, keep_robots_text=True)
    text = rep["robots"].pop("text", "")
    append(ROBOTS, {"domain": domain, "status": rep["robots"]["status"],
                    "state": rep["robots"].get("state"), "text": text})
    append(SITES, {"domain": domain, "sector": sector,
                   "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "seconds": round(time.time() - started, 1), "report": rep})
    return domain


def phase_b(domain: str, url: str, raw_words: int, chrome: str) -> str:
    dom = A.render(url, chrome)
    rendered = word_count(visible_text(dom)) if dom else None
    append(RENDERS, {"domain": domain, "url": url, "raw_words": raw_words,
                     "rendered_words": rendered, "ok": dom is not None})
    return domain


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)

    if not args.render:
        todo = [(d, s) for d, s in load_domains() if d not in done(SITES)]
        print(f"phase A: {len(todo)} domains to measure", flush=True)
        with cf.ThreadPoolExecutor(max_workers=args.workers or 24) as pool:
            futures = [pool.submit(phase_a, d, s) for d, s in todo]
            for i, fut in enumerate(cf.as_completed(futures), 1):
                try:
                    fut.result()
                except Exception as exc:  # keep going; the domain stays unmeasured
                    print("error:", exc, flush=True)
                if i % 50 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)
        return 0

    chrome = A.find_chrome()
    if not chrome:
        print("Chrome not found; cannot render.")
        return 1
    rendered = done(RENDERS)
    todo = []
    for line in SITES.open():
        rec = json.loads(line)
        sig = rec["report"].get("signals")
        if sig and rec["domain"] not in rendered:
            url = rec["report"]["homepage_browser"]["final_url"] or rec["report"]["origin"] + "/"
            todo.append((rec["domain"], url, sig["words"]))
    print(f"phase B: {len(todo)} homepages to render", flush=True)
    with cf.ThreadPoolExecutor(max_workers=args.workers or 6) as pool:
        futures = [pool.submit(phase_b, d, u, w, chrome) for d, u, w in todo]
        for i, fut in enumerate(cf.as_completed(futures), 1):
            try:
                fut.result()
            except Exception as exc:
                print("error:", exc, flush=True)
            if i % 25 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
