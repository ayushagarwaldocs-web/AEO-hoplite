#!/usr/bin/env bash
# The full pre-specified design on Claude models through the Anthropic API (key: ANTHROPIC_API_KEY in .env), one
# answer file per model. Same request as the Bedrock Claude runs: no sampling parameters (rejected), effort low.
# Resumes if interrupted; each run goes twice so throttled or failed calls are retried. Caps use PRICES in
# aeotools/llm.py (list prices).
#
#   ./run_claude.sh <model-id> <max-spend-usd> <workers>     e.g. ./run_claude.sh claude-sonnet-5-5 15 4
set -euo pipefail
cd "$(dirname "$0")"
PY=../../.venv-local/bin/python
model="$1"; cap="$2"; workers="${3:-4}"
out="data/responses_anthropic_${model}.jsonl"
# Preflight: one tiny request, so an empty account or a bad key stops here instead of logging 1,350 refusals.
"$PY" - "anthropic:$model" <<'PY' || exit 1
import sys
sys.path.insert(0, "../..")
from aeotools import llm
r = llm.complete(sys.argv[1], "Reply with OK.", "OK?", max_tokens=200)
if r.error:
    sys.exit(f"Preflight failed for {sys.argv[1]}: {r.error[:220]}")
print(f"Preflight ok for {sys.argv[1]}")
PY
for pass in 1 2; do
  echo "=== anthropic:$model, pass $pass ($(date '+%H:%M'))"
  "$PY" run_experiment.py --models "anthropic:$model" --out "$out" --max-spend "$cap" --workers "$workers" || true
done
echo "=== done ($(date '+%H:%M'))"
