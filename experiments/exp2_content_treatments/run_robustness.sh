#!/usr/bin/env bash
# Robustness checks on Amazon Bedrock (see README, "Robustness checks"). Resumes if interrupted; each step
# runs twice so throttled or failed calls are retried. Caps count everything already in each output file and
# use the ceiling prices in aeotools/llm.py, which run about 20% above what AWS bills.
#
#   ./run_robustness.sh flagship-opus | flagship-kimi | flagship-glm | long | temp
set -euo pipefail
cd "$(dirname "$0")"
PY=../../.venv-local/bin/python
LONG_CONDS="baseline filler third_party statistics citations quotation persuasive keyword_stuffing injection"
TEMP_CONDS="baseline filler third_party statistics citations keyword_stuffing injection"
OTHERS="bedrock:openai.gpt-oss-120b-1:0 bedrock:us.meta.llama4-maverick-17b-instruct-v1:0
bedrock:amazon.nova-pro-v1:0 bedrock:global.amazon.nova-2-lite-v1:0 bedrock:mistral.mistral-large-3-675b-instruct
bedrock:deepseek.v3.2 bedrock:qwen.qwen3-32b-v1:0 bedrock:qwen.qwen3-next-80b-a3b bedrock:google.gemma-3-27b-it
bedrock:minimax.minimax-m2.5 bedrock:nvidia.nemotron-super-3-120b"
TEMP_MODELS="bedrock:us.meta.llama4-maverick-17b-instruct-v1:0 bedrock:deepseek.v3.2
bedrock:mistral.mistral-large-3-675b-instruct bedrock:openai.gpt-oss-120b-1:0"

run_twice() { for pass in 1 2; do echo "=== $1, pass $pass ($(date '+%H:%M'))"; shift_args=("${@:2}"); "$PY" run_experiment.py "${shift_args[@]}" || true; done; }

# shellcheck disable=SC2086
case "${1:-}" in
  flagship-opus) run_twice opus --models bedrock:global.anthropic.claude-opus-4-6-v1 \
                   --out data/responses_flagship_opus.jsonl --max-spend 24 ;;
  flagship-kimi) run_twice kimi --models bedrock:global.moonshotai.kimi-k3 \
                   --out data/responses_flagship_kimi.jsonl --max-spend 26 ;;
  flagship-glm)  run_twice glm --models bedrock:zai.glm-5 --out data/responses_flagship_glm.jsonl --max-spend 4 ;;
  long)          run_twice long --models $OTHERS --long --conditions $LONG_CONDS \
                   --out data/responses_long.jsonl --max-spend 20 --max-spend-per-model 3.5 ;;
  long2)         run_twice long2 --models bedrock:zai.glm-5 bedrock:global.anthropic.claude-sonnet-4-6 --long \
                   --conditions $LONG_CONDS --out data/responses_long2.jsonl --max-spend 18 --max-spend-per-model 13 ;;
  temp)          run_twice temp --models $TEMP_MODELS --temperature 1 --conditions $TEMP_CONDS \
                   --out data/responses_temp.jsonl --max-spend 3 --max-spend-per-model 1 ;;
  *) echo "usage: $0 flagship-opus|flagship-kimi|flagship-glm|long|temp"; exit 2 ;;
esac
echo "=== done ($(date '+%H:%M'))"
