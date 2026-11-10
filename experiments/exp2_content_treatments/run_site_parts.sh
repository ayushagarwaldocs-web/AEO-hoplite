#!/usr/bin/env bash
# The dated separate-site follow-up (README, "Separate-site follow-up specification") as one process per model, so the
# twelve-model panel runs in one short window. Each part has the frozen blocks, order and settings, its own per-model
# cap from the live cost plan, and its own spending journal under data/private/. Paid: run only on the author's
# machine, after the freeze. When every part has finished, concatenate them with combine_attribution_parts.py --study site.
#
#   ./run_site_parts.sh            # dry run for every model
#   ./run_site_parts.sh --execute  # paid run
set -euo pipefail
cd "$(dirname "$0")"
PY=../../.venv-local/bin/python
P="${SITE_RUN_DIR:?set SITE_RUN_DIR to a new data/private/<run> folder}"
PLAN="$P/plan-live.json"
EXECUTE="${1:-}"
models=$("$PY" -c "import json; print(' '.join(sorted(json.load(open('$PLAN'))['attribution']['caps_usd'])))")
mkdir -p "$P/site_parts"
for m in $models; do
  slug=$(echo "$m" | tr ':/.' '___')
  out="$P/site_parts/$slug/responses_bedrock_site.jsonl"
  mkdir -p "$(dirname "$out")"
  cap=$("$PY" -c "import json; print(json.load(open('$PLAN'))['attribution']['caps_usd']['$m'])")
  (
    status=0
    "$PY" run_experiment.py --models "$m" --conditions site_B site_Q0 site_Q1 site_T0 site_T1 --trials 3 \
      --workers 1 --temperature 0 --max-tokens 4000 --trial-blocks --part --model-caps "$PLAN" \
      --max-spend "$cap" --out "$out" $EXECUTE > "$P/site_parts/$slug.log" 2>&1 || status=$?
    echo "$(date '+%H:%M:%S') exit $status $m" >> "$P/site_parts/done.txt"
  ) &
done
wait
echo "all parts finished ($(date '+%H:%M'))"
cat "$P/site_parts/done.txt"
