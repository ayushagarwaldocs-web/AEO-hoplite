#!/usr/bin/env bash
# Rebuild every Study 2 analysis from the answer files, then the paper's numbers, claim checks and PDF.
#
#   ./analyze_all.sh          # everything
#   ./analyze_all.sh --no-pdf # skip the LaTeX build
set -euo pipefail
cd "$(dirname "$0")"

# Replication set: the strongest Bedrock models plus the Azure and Gemini models, in one file (tag "flagship").
parts=()
for f in data/responses_flagship_opus.jsonl data/responses_flagship_kimi.jsonl data/responses_flagship_glm.jsonl \
         data/responses_azure_*.jsonl; do
  [ -f "$f" ] && parts+=("$f")
done
# Gemini 3.5 Flash joins only if its run is (nearly) complete; the free tier stopped it at 16 of 1,350 answers.
if [ -f data/responses_gemini.jsonl ] && [ "$(grep -vc '"error": "' data/responses_gemini.jsonl)" -ge 1300 ]; then
  parts+=(data/responses_gemini.jsonl)
fi
# Claude (Anthropic API), GPT (OpenAI API) and Gemini (Gemini API, one file per model) models join the same way.
for f in data/responses_anthropic_*.jsonl data/responses_openai_*.jsonl data/responses_gemini_*.jsonl; do
  [ -f "$f" ] && [ "$(grep -vc '"error": "' "$f")" -ge 1300 ] && parts+=("$f")
done
cat "${parts[@]}" > data/responses_flagship.jsonl

# Exploratory conditions on the Azure models, paired with their main answers.
explore=(data/responses_explore_azure_*.jsonl)
if [ -f "${explore[0]}" ]; then
  cat data/responses_azure_*.jsonl > data/responses_replication.jsonl
  cat "${explore[@]}" > data/responses_replication_explore.jsonl
fi

for tag in bedrock flagship; do
  python3 analyze.py --input "data/responses_$tag.jsonl" --tag "$tag" > /dev/null
  python3 analyze_absorption.py --input "data/responses_$tag.jsonl" --tag "$tag" > /dev/null
  python3 analyze_hypotheses.py --input "data/responses_$tag.jsonl" --tag "$tag" > /dev/null
done
python3 analyze_explore.py --tag bedrock > /dev/null
[ -f data/responses_replication_explore.jsonl ] && python3 analyze_explore.py --tag replication > /dev/null
python3 analyze_robustness.py
for tag in bedrock flagship; do
  python3 analyze_callouts.py --input "data/responses_$tag.jsonl" --tag "$tag" > /dev/null
done
python3 analyze_power.py > /dev/null
ls data/agentic_*-*.jsonl > /dev/null 2>&1 && python3 analyze_agentic.py > /dev/null  # agentic search design
[ -f results/human_check_sheet.xlsx ] && python3 analyze_absorption_judge.py human > /dev/null 2>&1 || true
python3 analyze_absorption_judge.py report > /dev/null

cd ../../paper
python3 make_numbers.py > /dev/null
python3 check_claims.py
[ "${1:-}" = "--no-pdf" ] || tectonic main.tex
