#!/bin/zsh
# Agentic search experiment: the four models in parallel, each with its pre-specified cap (README.md, "Agentic search").
cd "$(dirname "$0")"
PY=../../.venv-local/bin/python
run() {  # model cap workers
  local log="data/run_agentic_${1//[:\/]/_}.log"
  for pass in 1 2 3; do  # later passes retry only the episodes that failed (rate limits, timeouts)
    echo "=== $1 pass $pass ($(date +%H:%M))" >> "$log"
    $PY run_agentic.py --model "$1" --cap "$2" --workers "$3" >> "$log" 2>&1
    grep -q "Cap reached" "$log" && break
  done
  echo "=== done ($(date +%H:%M))" >> "$log"
}
run azure:gpt-5-mini 8 8 &
run azure:MAI-Thinking-1 22 6 &
run openai:gpt-6.1-sol 11 4 &
run azure:DeepSeek-V4-Pro 20 3 &
wait
