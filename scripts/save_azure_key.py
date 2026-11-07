"""Move a Microsoft Foundry API key from the clipboard into the repo's gitignored .env, without printing it.

    1. In Foundry (ai.azure.com), on the project's Home page, click "Copy API key".
    2. python3 scripts/save_azure_key.py            (reads the clipboard)
       python3 scripts/save_azure_key.py --prompt   (paste the key at a hidden prompt instead)

The clipboard is cleared afterwards. Only the key's length is printed.
"""

import getpass
import re
import subprocess
import sys
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / ".env"
ENDPOINT = "<your Foundry endpoint>"

if "--prompt" in sys.argv:
    key = getpass.getpass("Paste the Foundry API key (hidden) and press Enter: ").strip()
else:
    key = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout.strip()
key = re.sub(r"\x1b\[20[01]~", "", key).strip()  # terminals wrap pasted text in bracketed-paste markers
if key.startswith("http"):
    raise SystemExit("That is the endpoint URL, not the key. Copy KEY 1 (the long string under 'Keys') and try again.")
if not re.fullmatch(r"[A-Za-z0-9_\-+/=]{32,200}", key):
    where = "What was pasted" if "--prompt" in sys.argv else "The clipboard"
    raise SystemExit(f"{where} is not an API key (length {len(key)}). Copy KEY 1 and try again.")
lines = [ln for ln in ENV.read_text().splitlines() if not ln.startswith(("AZURE_FOUNDRY_API_KEY=", "AZURE_FOUNDRY_ENDPOINT="))]
lines += [f"AZURE_FOUNDRY_ENDPOINT={ENDPOINT}", f"AZURE_FOUNDRY_API_KEY={key}"]
ENV.write_text("\n".join(lines) + "\n")
subprocess.run(["pbcopy"], input="", text=True)
print(f"Saved a {len(key)}-character key to .env and cleared the clipboard.")
