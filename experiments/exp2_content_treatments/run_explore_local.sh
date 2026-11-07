#!/usr/bin/env bash
# Run the exploratory conditions (EXPLORATORY in build_corpus.py) on the three local models, then analyse.
# Answers go to data/responses_explore.jsonl; resumes if interrupted.
set -euo pipefail
cd "$(dirname "$0")"
PY=../../.venv-local/bin/python
CONDS=$("$PY" -c "from build_corpus import EXPLORATORY; print(' '.join(EXPLORATORY))")
for model in mlx-community/Llama-3.2-3B-Instruct-4bit \
             mlx-community/Qwen2.5-3B-Instruct-4bit \
             mlx-community/granite-3.3-2b-instruct-4bit; do
  echo "=== $model ($(date '+%H:%M'))"
  # shellcheck disable=SC2086
  "$PY" run_local_mlx.py --model "$model" --conditions $CONDS --out data/responses_explore.jsonl
done
python3 analyze_explore.py
echo "=== all done ($(date '+%H:%M'))"
