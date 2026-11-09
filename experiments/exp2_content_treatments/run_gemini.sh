#!/usr/bin/env bash
# The full pre-specified design on a Gemini model through the Gemini API (key: GEMINI_API_KEY in .env), one answer
# file per model. Same request as the Gemini 3.5 Flash run: thinking level low, temperature at Google's default.
# Resumes if interrupted; each run goes twice so throttled or failed calls are retried. Caps use PRICES in
# aeotools/llm.py.
#
#   ./run_gemini.sh <model-id> <max-spend-usd> <workers>     e.g. ./run_gemini.sh gemini-4-argon 40 4
set -euo pipefail
cd "$(dirname "$0")"
PY=../../.venv-local/bin/python
model="$1"; cap="$2"; workers="${3:-4}"
out="data/responses_gemini_${model}.jsonl"
# Preflight: one tiny request, so a key without access or billing stops here instead of logging 1,350 refusals.
"$PY" - "gemini:$model" <<'PY' || exit 1
import sys
sys.path.insert(0, "../..")
from aeotools import llm
r = llm.complete(sys.argv[1], "Reply with OK.", "OK?", max_tokens=200)
if r.error:
    sys.exit(f"Preflight failed for {sys.argv[1]}: {r.error[:220]}")
print(f"Preflight ok for {sys.argv[1]}: {r.input_tokens} in, {r.output_tokens} out")
PY
for pass in 1 2; do
  echo "=== gemini:$model, pass $pass ($(date '+%H:%M'))"
  "$PY" run_experiment.py --models "gemini:$model" --out "$out" --max-spend "$cap" --workers "$workers" || true
done
echo "=== done ($(date '+%H:%M'))"
