"""Experiment 1, external-validity extension: a random sample of popular websites.

Draws a rank-stratified random sample from the Tranco top-1M list (Le Pochat et
al., NDSS 2019), excluding the purposive sample, and measures it with exactly
the same audit as phase A of run_measurement.py (robots.txt, llms.txt and two
homepage fetches; no rendering).

    python run_random_sample.py --sample      # draw random_sample.csv from the Tranco list
    python run_random_sample.py               # measure it (resumes if interrupted)
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import io
import json
import random
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from aeotools import audit as A  # noqa: E402
from run_measurement import append, done  # noqa: E402

RAW = HERE / "data" / "raw"
TRANCO = RAW / "tranco"
SAMPLE = HERE / "random_sample.csv"
SITES = RAW / "random_sites.jsonl"
ROBOTS = RAW / "random_robots_raw.jsonl"
BANDS = [(1, 1_000), (1_001, 10_000), (10_001, 100_000), (100_001, 1_000_000)]
PER_BAND = 250
SEED = 20261104


def draw() -> None:
    with zipfile.ZipFile(TRANCO / "top-1m.csv.zip") as z, z.open("top-1m.csv") as fh:
        ranked = [(int(r), d) for r, d in csv.reader(io.TextIOWrapper(fh))]
    with (HERE / "domains.csv").open() as fh:
        purposive = {r["domain"] for r in csv.DictReader(fh)}
    rng = random.Random(SEED)
    rows = []
    for lo, hi in BANDS:
        pool = [(r, d) for r, d in ranked if lo <= r <= hi and d not in purposive]
        rows += [(d, r, f"{lo}-{hi}") for r, d in sorted(rng.sample(pool, PER_BAND))]
    list_id = (TRANCO / "list_id.txt").read_text().strip()
    with SAMPLE.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["domain", "rank", "band", "tranco_list"])
        w.writerows([(d, r, b, list_id) for d, r, b in rows])
    print(f"wrote {len(rows)} domains from Tranco list {list_id} to {SAMPLE.name}")


def measure(domain: str, rank: str, band: str) -> str:
    started = time.time()
    rep = A.audit(domain, keep_robots_text=True)
    text = rep["robots"].pop("text", "")
    append(ROBOTS, {"domain": domain, "status": rep["robots"]["status"],
                    "state": rep["robots"].get("state"), "text": text})
    append(SITES, {"domain": domain, "sector": "random", "rank": int(rank), "band": band,
                   "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "seconds": round(time.time() - started, 1), "report": rep})
    return domain


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    if args.sample:
        draw()
        return 0
    finished = done(SITES)
    with SAMPLE.open() as fh:
        todo = [(r["domain"], r["rank"], r["band"]) for r in csv.DictReader(fh) if r["domain"] not in finished]
    print(f"random sample: {len(todo)} domains to measure", flush=True)
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(measure, *row) for row in todo]
        for i, fut in enumerate(cf.as_completed(futures), 1):
            try:
                fut.result()
            except Exception as exc:  # keep going; the domain stays unmeasured
                print("error:", exc, flush=True)
            if i % 100 == 0:
                print(f"  {i}/{len(todo)}  {time.strftime('%H:%M')}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
