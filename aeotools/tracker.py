"""Track brand visibility across a prompt set and several models.

    python -m aeotools.tracker templates/prompt-set.csv --brand Acme \\
        --competitors Rival "Other Co" --models anthropic:claude-sonnet-5-5 gemini:gemini-2.5-flash \\
        --runs 5 --web-search --out tracking.jsonl

For each model it reports mention rate (with a 95% Wilson interval), top-pick
rate and share of voice, overall and per intent, plus the domains cited most
often when search grounding is on. Answers from APIs approximate, but do not
equal, what consumer apps show: rerun regularly and watch trends.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from urllib.parse import urlparse

from .llm import complete
from .metrics import brand_metrics

SYSTEM = ("You are a helpful assistant. Answer the user's question directly. When the user asks for "
          "recommendations, name specific products, companies or services and explain briefly why.")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def domain(url: str) -> str:
    host = urlparse(url).netloc or url
    return host.lower().removeprefix("www.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompts", help="CSV with at least id and prompt columns")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--competitors", nargs="*", default=[])
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--web-search", action="store_true", help="ground answers in live search where supported")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="tracking.jsonl")
    args = ap.parse_args(argv)

    with open(args.prompts) as fh:
        prompts = list(csv.DictReader(fh))
    brands = [args.brand] + args.competitors
    jobs = [(m, p, r) for m in args.models for p in prompts for r in range(args.runs)]
    print(f"Running {len(jobs)} requests ({len(prompts)} prompts x {args.runs} runs x {len(args.models)} models)")

    def run(job):
        spec, p, r = job
        res = complete(spec, SYSTEM, p["prompt"], max_tokens=3000, web_search=args.web_search)
        rec = {"model": spec, "prompt_id": p["id"], "intent": p.get("intent", ""), "run": r, **res.to_dict()}
        if not res.error:
            rec.update(brand_metrics(res.text, brands, args.brand))
            mentioned = [b for b in brands if brand_metrics(res.text, brands, b)["mentioned"]]
            rec["brands_mentioned"] = mentioned
        return rec

    records = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool, open(args.out, "a") as out:
        for rec in pool.map(run, jobs):
            out.write(json.dumps(rec) + "\n")
            records.append(rec)

    for spec in args.models:
        ok = [r for r in records if r["model"] == spec and not r.get("error")]
        errors = sum(1 for r in records if r["model"] == spec and r.get("error"))
        n = len(ok)
        k = sum(r["mentioned"] for r in ok)
        lo, hi = wilson(k, n)
        top = sum(r["top_pick"] for r in ok)
        voice = Counter(b for r in ok for b in r["brands_mentioned"])
        total_voice = sum(voice.values()) or 1
        print(f"\n{spec}  ({n} answers, {errors} errors)")
        print(f"  mention rate   {k / max(n, 1):6.1%}  (95% CI {lo:.0%}-{hi:.0%})")
        print(f"  top-pick rate  {top / max(n, 1):6.1%}")
        print("  share of voice " + ", ".join(f"{b} {voice[b] / total_voice:.0%}" for b in brands))
        by_intent = defaultdict(list)
        for r in ok:
            by_intent[r["intent"] or "all"].append(r["mentioned"])
        for intent, vals in sorted(by_intent.items()):
            print(f"    {intent:<12} mention rate {sum(vals) / len(vals):.0%} (n={len(vals)})")
        cited = Counter(domain(u) for r in ok for u in r.get("cited_urls", []))
        if cited:
            print("  most-cited domains: " + ", ".join(f"{d} ({c})" for d, c in cited.most_common(8)))
    print(f"\nRaw answers appended to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
