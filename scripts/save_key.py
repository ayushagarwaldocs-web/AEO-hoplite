"""Save an API key into the repo's gitignored .env without printing it.

    python3 scripts/save_key.py GEMINI_API_KEY            # reads the key from the clipboard (copy it first)
    python3 scripts/save_key.py GEMINI_API_KEY --prompt   # paste it at a hidden prompt instead

Replaces any existing line for that variable, clears the clipboard, and prints only the key's length.
"""

import getpass
import re
import subprocess
import sys
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / ".env"
if len(sys.argv) < 2 or not re.fullmatch(r"[A-Z][A-Z0-9_]+", sys.argv[1]):
    raise SystemExit("usage: python3 scripts/save_key.py VARIABLE_NAME [--prompt]")
name = sys.argv[1]
if "--prompt" in sys.argv:
    key = getpass.getpass(f"Paste {name} (hidden) and press Enter: ")
else:
    key = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
key = re.sub(r"\x1b\[20[01]~", "", key).strip()
if key.startswith("http") or not re.fullmatch(r"[A-Za-z0-9_\-+/=.]{20,300}", key):
    raise SystemExit(f"That doesn't look like an API key (length {len(key)}). Copy the key itself and try again.")
lines = [ln for ln in ENV.read_text().splitlines() if not ln.startswith(f"{name}=")]
lines.append(f"{name}={key}")
ENV.write_text("\n".join(lines) + "\n")
subprocess.run(["pbcopy"], input="", text=True)
print(f"Saved a {len(key)}-character {name} to .env and cleared the clipboard.")
