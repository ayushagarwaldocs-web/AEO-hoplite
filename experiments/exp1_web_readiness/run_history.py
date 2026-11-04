"""Experiment 1, longitudinal extension: archived robots.txt files, 2023-2026.

For every domain in domains.csv, query the Internet Archive's CDX index for
monthly captures of /robots.txt and download the capture closest to each target
date (the latest within 120 days before it, else the first within 60 days after).
Dates where only HTTP 404 captures exist are recorded as "absent" (no robots.txt).

Records are appended to data/raw/history_*.jsonl, so an interrupted run resumes.
The Archive blocks clients that send requests quickly, so all workers share one
rate limit (a request every --interval seconds) and back off for minutes when
refused. Domains are processed in a fixed random order, so a partial run is a
random subsample.

    python run_history.py
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import random
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from aeotools.audit import BOT_UA  # noqa: E402

RAW = HERE / "data" / "raw"
CAPTURES = RAW / "history_captures.jsonl"
TEXTS = RAW / "history_robots.jsonl"
CDX = "https://web.archive.org/cdx/search/cdx"
# GPTBot was announced in August 2023, so the first target precedes any AI-specific token.
TARGETS = ["2023-07-01", "2024-01-01", "2024-07-01", "2025-07-01", "2026-07-01"]
BEFORE, AFTER = timedelta(days=120), timedelta(days=60)
_lock = threading.Lock()
_rate = threading.Lock()
_last = [0.0]
INTERVAL = [6.0]


def get(url: str, params: dict | None = None, tries: int = 8) -> requests.Response | None:
    for attempt in range(tries):
        with _rate:  # one request start per INTERVAL seconds across all workers
            wait = _last[0] + INTERVAL[0] - time.time()
            if wait > 0:
                time.sleep(wait)
            _last[0] = time.time()
        try:
            r = requests.get(url, params=params, headers={"User-Agent": BOT_UA}, timeout=90)
            if r.status_code not in (429, 500, 502, 503, 504):
                return r
            pause = 60 * (attempt + 1)
        except requests.ConnectionError:
            pause = 900  # refused: the Archive's rate limiter; wait it out
        except requests.RequestException:
            pause = 60
        print(f"  backing off {pause}s ({url[:60]})", flush=True)
        time.sleep(pause)
    return None


def captures(domain: str, status: str) -> list[list[str]] | None:
    r = get(CDX, {"url": f"{domain}/robots.txt", "from": "202302", "to": "202608", "output": "json",
                  "fl": "timestamp,original,statuscode,digest", "filter": f"statuscode:{status}",
                  "collapse": "timestamp:6"})
    if r is None or r.status_code != 200:
        return None
    return r.json()[1:] if r.text.strip() else []


def pick(caps: list[list[str]], target: str) -> list[str] | None:
    t = datetime.fromisoformat(target)
    when = lambda c: datetime.strptime(c[0][:8], "%Y%m%d")  # noqa: E731
    before = [c for c in caps if t - BEFORE <= when(c) <= t]
    if before:
        return before[-1]
    after = [c for c in caps if t < when(c) <= t + AFTER]
    return after[0] if after else None


def append(path: Path, record: dict) -> None:
    with _lock, path.open("a") as fh:
        fh.write(json.dumps(record) + "\n")


def job(domain: str) -> str | None:
    """Returns an error message, or None on success."""
    ok = captures(domain, "200")
    if ok is None:
        return f"{domain}: CDX error"
    picks = {t: pick(ok, t) for t in TARGETS}
    missing = [t for t, p in picks.items() if p is None]
    absent = {}
    if missing:
        gone = captures(domain, "404") or []
        absent = {t: pick(gone, t) for t in missing}
    fetched = set()
    for t, p in picks.items():
        if p is None or p[3] in fetched:
            continue
        ts, original, _, digest = p
        r = get(f"https://web.archive.org/web/{ts}id_/{original}")
        text = r.content[:500_000].decode("utf-8", errors="replace") if r is not None and r.status_code == 200 else None
        append(TEXTS, {"domain": domain, "timestamp": ts, "digest": digest,
                       "status": r.status_code if r is not None else None, "text": text})
        fetched.add(digest)
    append(CAPTURES, {"domain": domain, "n_captures": len(ok),
                      "picks": {t: (p[0], p[3]) if p else None for t, p in picks.items()},
                      "absent": {t: p[0] for t, p in absent.items() if p}})
    return None


def safe_job(domain: str) -> str | None:
    try:
        return job(domain)
    except Exception as exc:  # keep going; the domain stays unqueried and is retried on resume
        return f"{domain}: {type(exc).__name__}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--interval", type=float, default=6.0, help="seconds between request starts")
    args = ap.parse_args()
    INTERVAL[0] = args.interval
    RAW.mkdir(parents=True, exist_ok=True)
    finished = {json.loads(line)["domain"] for line in CAPTURES.open()} if CAPTURES.exists() else set()
    with (HERE / "domains.csv").open() as fh:
        todo = [r["domain"] for r in csv.DictReader(fh) if r["domain"] not in finished]
    random.Random(20261104).shuffle(todo)
    print(f"history: {len(todo)} domains to query", flush=True)
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, err in enumerate(pool.map(safe_job, todo), 1):
            if err:
                print(err, flush=True)
            if i % 25 == 0:
                print(f"  {i}/{len(todo)}  {time.strftime('%H:%M')}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
