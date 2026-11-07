#!/usr/bin/env bash
# The full pre-specified design on Microsoft Foundry (Azure) deployments, one answer file per model so they can run
# in parallel. Resumes if interrupted; each run goes twice so throttled or failed calls are retried. Caps use the
# ceiling prices in AZURE_PRICES (aeotools/llm.py).
#
#   ./run_azure.sh <deployment> <max-spend-usd> <workers>
set -euo pipefail
cd "$(dirname "$0")"
PY=../../.venv-local/bin/python
model="$1"; cap="$2"; workers="${3:-8}"
out="data/responses_azure_$(echo "$model" | tr 'A-Z.' 'a-z-').jsonl"
for pass in 1 2; do
  echo "=== azure:$model, pass $pass ($(date '+%H:%M'))"
  "$PY" run_experiment.py --models "azure:$model" --out "$out" --max-spend "$cap" --workers "$workers" || true
done
echo "=== done ($(date '+%H:%M'))"
