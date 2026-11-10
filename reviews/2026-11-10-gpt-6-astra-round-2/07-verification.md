# Review of Astra's build, and what happened before the runs (10 November 2026)

Astra's patch is [06-astra-build.diff](06-astra-build.diff) (SHA-256 3ae72fa8...c3b2, byte-identical to the sandbox copy).
Its own account is [05-astra-build-log.md](05-astra-build-log.md). Claude applied the patch to the uncommitted branch,
reviewed it, and changed the items below before any paid query. Each change is also recorded in the experiment
README, with times.

> **Correction (added 10 November 2026, after the third review).** "Before any paid query" and "before any query" are
> not accurate for every item below. The attribution items (templates, evaluator name, `.gitignore`, cost caps, part
> mode) were changed before the attribution run's first query. The judge output limit, the evidence-span checker and
> the second-judge decision followed paid pilot calls of the recommendation judges (GPT-5 mini and MAI-Thinking-1, after
> the manifest froze at 13:53 IST); they were recorded by 14:34 IST, before the held-out stage and before any human
> label. The original wording is kept below.

## Checks

- **Patch.** It applied cleanly over the current tree. Astra's own tests passed except one, which imports `boto3`, a
  package that exists only in the project's `.venv-local`. That test now skips when the package is missing. The retry
  switch it covers was checked by hand there: the main study keeps 8 Bedrock retries, and follow-up mode makes 1
  attempt. The suite after all changes: 87 passed, 1 skipped.
- **`aeotools/llm.py`.** This is outside the requested scope. The change is a no-retry mode, switched on only by the
  `AEO_NO_RETRIES` environment variable; the defaults are unchanged.
- **Main study.** Its prompts are unchanged: Astra reports the same canonical hash for all 1,350 prompts, and
  `attr_B` reproduces the baseline exactly.

## Changed at review, before any query

| Item | Why |
|---|---|
| **Attribution templates.** They referred to "the needs described in the question" and "For the question above". Both now use the scenario's stated need, for example "Halorence is the option recommended for small online stores". | A web page would not refer to the reader's question, and text addressed to the model resembles the source-embedded instruction condition (+28.3 points in the main study). The four arms of a trial still share identical text apart from source and stance. The mechanical check passes: added text is 14–22 words, equal within a trial, with one target mention at the page end. |
| **Evaluator name.** It was `NeralinAA` to `NeralinBD`; it is now one plain name, "the Neralin review team". | Coded suffixes read as placeholders and could make the external source look less credible. The name appears in no main-study prompt. |
| **`.gitignore`.** Astra ignored the attribution answers and all new results; now only `data/private/` (the blinded key and private judge files) is ignored. | The paper promises that all data are released. |
| **Cost caps.** They were scaled from one smoke-test answer per model. They now use the larger of each model's smoke-test cost and its historical baseline cost, and the cap is $10 instead of $9, at the repository's ceiling prices. | With the original caps, Nova 2 Lite and Mistral Large 3 had almost no headroom over their usual cost and would probably have stopped short of the 87 trials a model needs. The live projection is $8.22, about $6.50 at billed prices; the cap of $10 is about $7.90 billed. |
| **`--part` mode and `run_attribution_parts.sh`.** These add one process per model, each with its own spending journal under `data/private/`. | The runner was strictly sequential across all 12 models: about 6–7 hours at the smoke-test latencies. The design within each model is unchanged. A test covers the mode. |
| **Judge output limit.** It was 256 tokens; it is now 1,024. | At 256, 49 of 84 GPT-5 mini pilot outputs were cut off by hidden reasoning. |
| **Evidence-span checker.** It now ignores Markdown emphasis, quotes, dashes, whitespace and case, and treats a missing evidence list as empty when the label is not true. | The 17 failures at 1,024 tokens were all formatting (for example, a quote missing the answer's `**bold**` markers). Validity went from 67/84 to 82/84, which passes the 80/84 gate. A span with different words still fails. Tests were added. |
| **Second judge.** MAI-Thinking-1 is used only in its pilot. | It wrote a median of 956 tokens, 23 of 84 outputs were cut off at 1,024, and it cost $0.76 for 84 items: about $67 for the held-out set. Whether the declared fallback, Qwen 3 32B, codes the full set is decided after the human gate, on budget alone. |
| **Rater workbook.** `v2` restates the codebook in plain language and shows worked labels as Yes/No. | The first draft pasted the judges' JSON codebook (null, boolean, evidence lists) into a human's instructions. The first draft was never sent. Neither version contains item IDs, conditions or model names. |
| **Practice examples.** Labelled by Claude under the codebook. | The labels and reasons are in `practice_guide.json` (private) and in the workbook's worked examples. |

## Paid steps so far

All costs are in the runners' ceiling-price accounting.

| Step | Calls | Cost |
|---|---|---|
| GPT-5 mini pilot, 256 tokens | 84 | $0.051 |
| GPT-5 mini pilot, 1,024 tokens | 84 | $0.051 |
| MAI-Thinking-1 pilot, 1,024 tokens | 84 | $0.757 |
| GPT-5 mini, 60 held-out human items | 60 | $0.040 |
| Bedrock smoke check | 12 | about $0.02 |
| Attribution run | started 14:24 IST, 12 models in parallel | capped at $10 |
