#!/usr/bin/env bash
# The dated attribution follow-up (README, "Dated attribution follow-up specification") as one process per model, so the
# twelve-model panel runs in one short window. Each part has the frozen blocks, order and settings, its own per-model
# cap from the live cost plan, and its own spending journal under data/private/. Paid: run only on the author's
# machine, after the freeze. When every part has finished, concatenate them with combine_attribution_parts.py.
#
#   ./run_attribution_parts.sh            # dry run for every model
#   ./run_attribution_parts.sh --execute  # paid run
set -euo pipefail
cd "$(dirname "$0")"
PY=../../.venv-local/bin/python
P=data/private/round2-20261110
PLAN="$P/plan-live.json"
EXECUTE="${1:-}"
models=$("$PY" -c "import json; print(' '.join(sorted(json.load(open('$PLAN'))['attribution']['caps_usd'])))")
mkdir -p "$P/attr_parts"
for m in $models; do
  slug=$(echo "$m" | tr ':/.' '___')
  out="$P/attr_parts/$slug/responses_bedrock_attribution.jsonl"
  mkdir -p "$(dirname "$out")"
  cap=$("$PY" -c "import json; print(json.load(open('$PLAN'))['attribution']['caps_usd']['$m'])")
  (
    status=0
    "$PY" run_experiment.py --models "$m" --conditions attr_B attr_S0 attr_S1 attr_Q0 attr_Q1 --trials 3 \
      --workers 1 --temperature 0 --max-tokens 4000 --trial-blocks --part --model-caps "$PLAN" \
      --max-spend "$cap" --out "$out" $EXECUTE > "$P/attr_parts/$slug.log" 2>&1 || status=$?
    echo "$(date '+%H:%M:%S') exit $status $m" >> "$P/attr_parts/done.txt"
  ) &
done
wait
echo "all parts finished ($(date '+%H:%M'))"
cat "$P/attr_parts/done.txt"
