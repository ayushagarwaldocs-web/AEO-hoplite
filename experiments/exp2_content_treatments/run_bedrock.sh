#!/usr/bin/env bash
# Run Experiment 2 on Amazon Bedrock: the pre-specified conditions, then the exploratory ones, then analyse.
# Resumes if interrupted. Each step runs twice so throttled or failed calls are retried. The spending
# caps count everything already in each output file; prices are ceilings (BEDROCK_PRICES in aeotools/llm.py).
set -euo pipefail
cd "$(dirname "$0")"
PY=../../.venv-local/bin/python
CLAUDE="bedrock:global.anthropic.claude-sonnet-4-6"
OTHERS="bedrock:openai.gpt-oss-120b-1:0 bedrock:us.meta.llama4-maverick-17b-instruct-v1:0
bedrock:amazon.nova-pro-v1:0 bedrock:global.amazon.nova-2-lite-v1:0 bedrock:mistral.mistral-large-3-675b-instruct
bedrock:deepseek.v3.2 bedrock:qwen.qwen3-32b-v1:0 bedrock:qwen.qwen3-next-80b-a3b bedrock:google.gemma-3-27b-it
bedrock:minimax.minimax-m2.5 bedrock:nvidia.nemotron-super-3-120b"
EXPLORE=$("$PY" -c "from build_corpus import EXPLORATORY; print(' '.join(EXPLORATORY))")
MAIN=data/responses_bedrock.jsonl
EXTRA=data/responses_bedrock_explore.jsonl

# shellcheck disable=SC2086
for pass in 1 2; do
  echo "=== pre-specified conditions, pass $pass ($(date '+%H:%M'))"
  "$PY" run_experiment.py --models $CLAUDE --out $MAIN --max-spend 32 --max-spend-per-model 14
  "$PY" run_experiment.py --models $OTHERS --out $MAIN --max-spend 32 --max-spend-per-model 5
done
# shellcheck disable=SC2086
for pass in 1 2; do
  echo "=== exploratory conditions, pass $pass ($(date '+%H:%M'))"
  "$PY" run_experiment.py --models $CLAUDE --conditions $EXPLORE --out $EXTRA --max-spend 15 --max-spend-per-model 7
  "$PY" run_experiment.py --models $OTHERS --conditions $EXPLORE --out $EXTRA --max-spend 15 --max-spend-per-model 3
done
python3 analyze.py --input $MAIN --tag bedrock
python3 analyze_absorption.py --input $MAIN --tag bedrock
python3 analyze_hypotheses.py --input $MAIN --tag bedrock
python3 analyze_explore.py --tag bedrock
echo "=== all done ($(date '+%H:%M'))"
