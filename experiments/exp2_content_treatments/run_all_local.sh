#!/usr/bin/env bash
# Run Experiment 2 on the three local open-weight models, one after another, then analyse.
# Usage: ./run_all_local.sh [trials-per-scenario]   (default 3; resumes if interrupted)
set -euo pipefail
cd "$(dirname "$0")"
PY=../../.venv-local/bin/python
TRIALS=${1:-3}
for model in mlx-community/Llama-3.2-3B-Instruct-4bit \
             mlx-community/Qwen2.5-3B-Instruct-4bit \
             mlx-community/granite-3.3-2b-instruct-4bit; do
  echo "=== $model ($(date '+%H:%M'))"
  "$PY" run_local_mlx.py --model "$model" --trials "$TRIALS"
done
python3 analyze.py
echo "=== all done ($(date '+%H:%M'))"
