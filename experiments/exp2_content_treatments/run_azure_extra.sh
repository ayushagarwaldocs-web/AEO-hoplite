#!/usr/bin/env bash
# Robustness runs on Microsoft Foundry deployments (README, "Robustness checks"): long pages (9 conditions) or the
# exploratory conditions (7), one answer file per model and mode. Resumes; each runs twice to retry failures.
#
#   ./run_azure_extra.sh long|explore <deployment> <max-spend-usd> <workers>
set -euo pipefail
cd "$(dirname "$0")"
PY=../../.venv-local/bin/python
mode="$1"; model="$2"; cap="$3"; workers="${4:-8}"
slug=$(echo "$model" | tr 'A-Z.' 'a-z-')
LONG_CONDS="baseline filler third_party statistics citations quotation persuasive keyword_stuffing injection"
EXPLORE=$("$PY" -c "from build_corpus import EXPLORATORY; print(' '.join(EXPLORATORY))")
for pass in 1 2; do
  echo "=== azure:$model $mode, pass $pass ($(date '+%H:%M'))"
  if [ "$mode" = long ]; then
    # shellcheck disable=SC2086
    "$PY" run_experiment.py --models "azure:$model" --long --conditions $LONG_CONDS \
      --out "data/responses_long_azure_$slug.jsonl" --max-spend "$cap" --workers "$workers" || true
  else
    # shellcheck disable=SC2086
    "$PY" run_experiment.py --models "azure:$model" --conditions $EXPLORE \
      --out "data/responses_explore_azure_$slug.jsonl" --max-spend "$cap" --workers "$workers" || true
  fi
done
echo "=== done ($(date '+%H:%M'))"
