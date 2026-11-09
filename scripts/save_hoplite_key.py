"""Move a Hoplite API key from the clipboard into the repo's gitignored .env, without printing it.

    1. In Hoplite (app.hoplite.sh): Settings > API keys > "+ Create" under Personal keys, then copy the key.
    2. python3 scripts/save_hoplite_key.py            (reads the clipboard)
       python3 scripts/save_hoplite_key.py --prompt   (paste the key at a hidden prompt instead)

experiments/exp2_content_treatments/run_hoplite.py uses the key only to archive each question's thread once the
answer is saved (PATCH /api/threads/{id}), which frees the thread's sandbox at once. The key is checked with one
read-only call first and the clipboard is cleared afterwards. Only the key's length and the plan are printed.
"""

import getpass
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / ".env"
API = "https://api.hoplite.sh"

if "--prompt" in sys.argv:
    key = getpass.getpass("Paste the Hoplite API key (hidden) and press Enter: ").strip()
else:
    key = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout.strip()
key = re.sub(r"\x1b\[20[01]~", "", key).strip()  # terminals wrap pasted text in bracketed-paste markers
if not re.fullmatch(r"hop_[^\s\"']{16,300}", key):
    where = "What was pasted" if "--prompt" in sys.argv else "The clipboard"
    raise SystemExit(f"{where} is not a Hoplite API key (they start with hop_; length {len(key)}). Copy it and try again.")


def get(path: str) -> dict:
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {key}",
                                                      "User-Agent": "aeo-handbook-save-key"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


plan = {}
try:
    plan = get("/api/billing/plan").get("plan", {})
except urllib.error.HTTPError as e:
    if e.code == 401:
        raise SystemExit("Hoplite did not accept the key (HTTP 401). Nothing was saved.")
    try:
        get("/api/threads?limit=1")  # the key may lack billing access but still reach threads
    except urllib.error.HTTPError as e2:
        raise SystemExit(f"Hoplite did not accept the key (HTTP {e2.code}). Nothing was saved.")
except urllib.error.URLError as e:
    raise SystemExit(f"Could not reach Hoplite ({e.reason}). Nothing was saved.")

lines = [ln for ln in (ENV.read_text().splitlines() if ENV.exists() else []) if not ln.startswith("HOPLITE_API_KEY=")]
lines.append(f"HOPLITE_API_KEY={key}")
ENV.write_text("\n".join(lines) + "\n")
if "--prompt" not in sys.argv:
    subprocess.run(["pbcopy"], input="", text=True)
extra = f" Plan: {plan.get('plan')}; idle sandboxes are kept {plan.get('sandboxIdleMinutes')} min." if plan else ""
cleared = "" if "--prompt" in sys.argv else " and cleared the clipboard"
print(f"Saved a {len(key)}-character key to .env{cleared}.{extra}")
