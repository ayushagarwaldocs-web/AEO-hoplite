"""Concatenate the per-model attribution parts into data/responses_bedrock_attribution.jsonl.

    python3 combine_attribution_parts.py [--parts data/private/round2-20261110/attr_parts]

Run once, after run_attribution_parts.sh has finished for every model. Each part must hold one model only, with no
duplicate (trial, condition) rows; error rows are kept, as the analysis requires. The combined file is never
overwritten.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = {"attribution": "responses_bedrock_attribution.jsonl", "site": "responses_bedrock_site.jsonl"}
OUT = HERE / "data" / FILES["attribution"]


def combine(parts_dir: Path, out: Path = OUT, name: str = FILES["attribution"]) -> dict:
    if out.exists():
        raise SystemExit(f"{out} already exists; refusing to overwrite it")
    files = sorted(parts_dir.glob(f"*/{name}"))
    if len(files) != 12:
        raise SystemExit(f"expected 12 parts, found {len(files)}")
    rows, summary, seen = [], {}, set()
    for f in files:
        part = [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
        models = {r["model"] for r in part}
        if len(models) != 1:
            raise SystemExit(f"{f} holds {len(models)} models")
        for r in part:
            key = (r["model"], r["trial_id"], r["condition"])
            if key in seen:
                raise SystemExit(f"duplicate row {key}")
            seen.add(key)
        model = models.pop()
        summary[model] = dict(rows=len(part), errors=sum(1 for r in part if r.get("error")),
                              by_condition=dict(Counter(r["condition"] for r in part)))
        rows.extend(part)
    with out.open("x") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return dict(out=str(out.relative_to(HERE)), rows=len(rows), models=summary)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--study", choices=sorted(FILES), default="attribution")
    ap.add_argument("--parts", type=Path, help="default: data/private/round2-20261110/attr_parts (attribution)")
    args = ap.parse_args()
    if args.study == "site" and not args.parts:
        raise SystemExit("--parts is required for the site follow-up")
    parts = args.parts or HERE / "data/private/round2-20261110/attr_parts"
    print(json.dumps(combine(parts, HERE / "data" / FILES[args.study], FILES[args.study]), indent=1))


if __name__ == "__main__":
    main()
