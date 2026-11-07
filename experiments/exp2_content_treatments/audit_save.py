"""Append one live-audit record (JSON on stdin) to data/audit/<assistant>.jsonl, with a timestamp.

    python3 audit_save.py perplexity pm_agency <<'JSON'
    {"url": "...", "urls": [...], "answer": "..."}
    JSON
"""
import datetime
import json
import sys
from pathlib import Path

assistant, scenario = sys.argv[1], sys.argv[2]
rec = json.loads(sys.stdin.read())
rec.update(assistant=assistant, scenario=scenario, collected_at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
out = Path(__file__).resolve().parent / "data" / "audit" / f"{assistant}.jsonl"
with out.open("a") as fh:
    fh.write(json.dumps(rec) + "\n")
print(f"saved {scenario}: {len(rec.get('urls', []))} sources -> {out.name}")
