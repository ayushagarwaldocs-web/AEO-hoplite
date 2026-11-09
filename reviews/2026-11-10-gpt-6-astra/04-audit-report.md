# GPT-6 Astra's code and statistics audit (10 November 2026)

- Auditor: GPT-6 Astra (OpenAI), reasoning level Medium, run as an agent thread on the Hoplite platform
  (thread `thr_4e620cfcb46445c3bbcdf45c9fbd1d62`; it worked for about 20 minutes, reran the Study 2 pipeline offline
  in its own sandbox and tested the parsers on small examples).
- Audited: commit `d2bfbf2`, against `paper/main.pdf`.
- Brief: [03-audit-brief.md](03-audit-brief.md).
- Copied verbatim from the thread's final message, converted from the rendered page back to Markdown. Two
  formatting repairs: inline maths is shown in parentheses, and the p-value table in A1, which the page flattened into
  one line, is rebuilt as a Markdown table with the same values.
- These are findings to check, not accepted facts. What was done with each one is recorded in [README.md](README.md).

---

# Report-only audit: AEO-hoplite

**The offline Study 2 pipeline reproduces the principal treatment estimates, but the pooled position test has a consequential dependence error.** Preserving the source order shared across models changes its reported significance from (p<0.001) to approximately (p=0.40) and (p=0.59), undermining the paper’s pooled H5 conclusion.

## Scope and reproduction

Audited [`ayushagarwaldocs-web/AEO-hoplite`](https://github.com/ayushagarwaldocs-web/AEO-hoplite/tree/d2bfbf2a37431432798cce83375e4719f76b3e0f), pinned to commit `d2bfbf2a37431432798cce83375e4719f76b3e0f`, against `paper/main.pdf`.

All execution occurred under a temporary directory. No tracked source files were edited, no commits or pull requests were created, and no language-model APIs were called. The reproduction used a separate temporary copy with Python network connections blocked.

**Verification:**

- `experiments/exp2_content_treatments/analyze_all.sh --no-pdf` completed successfully; **116 claim checks passed**.
- **30 selected offline unit tests passed**: HTML signals, logs, metrics, robots, and templates.
- Of 113 compared tracked Study 2 result files and `paper/numbers.tex`, **87 were byte-identical and 26 differed**: 11 CSVs, two JSONs, 12 plot files, and the numbers file.
- Changed CSV values differed by no more than (10^{-12}); the largest JSON difference was (3.33\times10^{-16}). Plot byte differences alone were not treated as substantive discrepancies.
- `paper/numbers.tex:1696` changed `\SmRhoPawc` from `0.95` to `0.94`. That macro is unused in the paper sources, so this does not change the paper’s displayed claims. Reproduction is therefore numerically close, **not byte-for-byte exact**.

Below, **E2/** means `experiments/exp2_content_treatments/`; **E1/** means `experiments/exp1_web_readiness/`. Paper line references identify the corresponding TeX sources.

## A. Bugs

### A1. H5 permutations break the shared trial-level randomization — consequential

**Location:** `E2/analyze_hypotheses.py:60–87`, especially lines 65 and 73; source-order construction at `E2/build_corpus.py:629–663`.

The test drops scenario/trial identifiers and independently permutes target positions within each model. However, all models receive the same source order for a given trial. I verified one shared target position per trial across models in all 90 baseline trials of both datasets.

**Concrete scenario:** A particular target is attractive to many models and happens to occupy slot 2. Independently shuffling each model’s positions destroys that shared trial-level association, making the pooled null distribution too concentrated.

Using the same pooled chi-square statistic and 10,000 permutations, but moving each trial’s position jointly across models:

| Dataset | Committed p-value | Shared-trial permutation | Shared-trial, within-scenario permutation |
|---|---|---|---|
| Bedrock | 0.000100 | 0.411 | 0.403 |
| Replication | 0.000800 | 0.595 | 0.591 |

**Effect:** The pooled evidence supporting H5 disappears under these dependence-preserving checks. This directly affects `paper/results_study2.tex:59–60` and `paper/results_robust.tex:13`. It does **not** establish that position never matters, nor invalidate the separately computed paired treatment effects.

**Confidence:** High on the randomization-unit error and reproduced sensitivity; these are Monte Carlo p-values, not exact tests.

### A2. Absorption detector can attribute a competitor’s text to the target

**Location:** `E2/analyze_absorption.py:54–55`.

The limitations detector searches the entire answer for the target’s `anti_fit` phrase without requiring attribution to that target.

**Concrete input:** “Ithatence is budget-focused. Wynano targets large-breed puppies.” This triggers Ithatence’s limitations detector because its anti-fit phrase is “large-breed puppies,” although the sentence describes Wynano.

The stored validation sample contains the corresponding failure: item `limitations|treated|bedrock:minimax.minimax-m2.5|dogfood_picky-2` is detector-positive but both judges label it NO.

**Effect:** Upward misclassification of absorption. That item contributes approximately **0.83 percentage points** to the 120-answer treated-limitations validation sample. Its contribution to the full-data estimate is not established. Judge labels are corroborating annotations, not infallible ground truth.

**Confidence:** High for the attribution defect; uncertain population prevalence.

### A3. “Visible text” includes explicitly hidden content

**Location:** `aeotools/html_signals.py:50–55`; `E1/run_measurement.py:67–71`; classification at `E1/analyze.py:126`.

`visible_text()` removes selected tags, then uses BeautifulSoup’s text extraction. It does not respect the HTML `hidden` attribute or CSS visibility.

**Concrete input:** A hidden `<div>` containing 200 words plus a visible paragraph containing 10 words returns **210**, not 10, words.

If JavaScript subsequently reveals those 200 words, both snapshots still score 210. The measured raw/rendered ratio is 1 rather than approximately 0.048, missing JavaScript dependence under the paper’s threshold.

**Effect:** Can undercount JavaScript-dependent sites in this scenario; other DOM changes can produce different biases. The prevalence and aggregate effect cannot be measured without the original HTML/render snapshots.

**Confidence:** High for the demonstrated behavior; unknown study-level magnitude.

### A4. Robots path matching omits required encoding normalization

**Location:** `aeotools/robots.py:35–42,79–91`.

Patterns and paths are compared directly, without the normalization required by [RFC 9309 §2.2.2](https://www.rfc-editor.org/rfc/rfc9309.html#section-2.2.2).

**Concrete inputs:**

- `Disallow: /private` incorrectly allows `/%70rivate`.
- `Disallow: /café` incorrectly allows `/caf%C3%A9`.

I reproduced both; Protego denies both.

**Effect:** These disallow examples understate blocking for encoded paths. Equivalent problems involving allow rules can reverse the direction. This is not evidence of a material error in the paper’s root-path block rates: the demonstrated paths are not `/`, and raw crawl inputs were unavailable.

**Confidence:** High on the parser defect; unquantified empirical impact.

## B. Statistical choices a referee could question

### B1. Position-plot intervals treat correlated answers as independent

**Location:** `E2/analyze.py:159–174`; explicitly disclosed in `paper/appendix_results.tex:17–19`.

The pooled position plot uses binomial Wilson intervals over answers, although models share trials and the evidence curve combines statistics/citation answers from those same trials.

**Concrete scenario:** One unusually suitable target is mentioned by many models in both evidence conditions. Those observations are not independent replications of a source-order assignment.

**Effect:** With positive within-trial dependence, intervals are too narrow. A Bedrock baseline trial contributes 12 model answers; the evidence curve can contribute 24 answers from that same trial. Those counts describe repeated observations, not 12 or 24 independent trial assignments. Corrected interval widths were not estimated here.

**Confidence:** High on ignored dependence; magnitude uncertain. This is disclosed, unlike an undocumented implementation discrepancy, and accompanies A1 rather than constituting separate evidence for H5.

### B2. “Top pick” measures first mention, not recommendation

**Location:** `aeotools/metrics.py:52–63`; disclosed at `paper/main.tex:378–382`.

**Concrete input:** “Do not pick Alpha. Choose Beta.” scores Alpha as `top_pick=True`.

**Effect:** Warning-first, comparison-first, or rejection-first answers can inflate the target’s measured “top pick” despite recommending against it. The callout sensitivity addresses part of this problem, but does not turn first mention into a semantic recommendation measure. Overall magnitude remains unquantified.

**Confidence:** High. This is a construct-validity concern, **not a paper/code mismatch**, because the paper defines the proxy.

### B3. Detector rates are not established lower bounds

**Location:** `paper/appendix_results.tex:100–105`, referring to the detector and stored judge validation.

The paper infers that detector rates are lower bounds because judges recognize missed paraphrases. A2 demonstrates that false positives also occur.

**Concrete scenario:** A detector misses several genuine paraphrases but also counts competitor descriptions. Higher judge-positive rates do not establish one-sided detector error.

**Effect:** The net error may still be downward, but “lower bounds” is stronger than the validation supports. No defensible numerical correction follows from this audit alone.

**Confidence:** High that a strict lower-bound interpretation is unsupported; uncertain net bias.

## C. Paper-description/code mismatches and validation gaps

### C1. Fixed-query pooling is not equal weighting of model-level effects

**Location:** `E2/analyze_agentic.py:65–83,137–145`; equal-weight description at `paper/appendix_results.tex:179–183`.

Baseline episodes without searches are excluded from the fixed-query analysis. This leaves **70 trials for MAI-Thinking-1 versus 90 for each other model**. Pooling averages available models within each trial and then averages trials; it does not average the four model-level effects equally.

**Concrete result:** For citations’ effect on top-five retrieval:

- Implemented pooled estimate: **+4.49 percentage points**.
- Equal average of the four reported model-level effects: **+2.86 points**.

**Effect:** The implemented estimate is **1.64 points higher** for this contrast. This does not demonstrate a significance reversal; the reported pooled contrast is nonsignificant. A confidence interval for the alternative estimand would require corresponding resampling.

**Confidence:** High. The analogous imbalance in the main replication data is much smaller: one missing filler response changes its mention-effect pooling by about **0.009 points**.

### C2. The barrier aggregate excludes observed bot-only refusals

**Location:** `E1/analyze.py:77–81`; `E1/analyze_extensions.py:113–116`; paper definitions at `paper/main.tex:196–208,260–274`.

A successful browser-user-agent fetch makes `scripted_blocked=False`, so a bot-only refusal is excluded from `edge_refused` and consequently from the barrier aggregate.

**Concrete stored cases:** `canva.com` and `rei.com` have `bot_wall=True`, but `edge=False` and `any=False`.

**Effect:** If “at least one barrier” includes these observed bot-specific refusals, the aggregate becomes **199/569 = 35.0%**, rather than **197/569 = 34.6%**; edge cases rise from 99 to 101.

**Confidence:** High on the stored-data omission and arithmetic. Whether to include them is a definition choice: the results section explicitly describes refusals under both user agents and separately mentions bot-only refusals. This is a small scope inconsistency, not evidence that either site blocks verified production AI crawlers.

### C3. A passing claim check does not verify its named visit-share claim

**Location:** `paper/check_claims.py:200`; associated prose at `paper/appendix_results.tex:115–118`.

The check labeled “Gemini and ChatGPT carry their visit shares” only tests whether `"Gemini"` appears in `assistants_present`.

**Concrete scenario:** ChatGPT could be missing, or either weight could be wrong, and this assertion would still pass.

**Effect:** No demonstrated error in the current shares, but false assurance from the successful claim-check count. Passing all 116 checks is not independent validation of every sentence they describe.

**Confidence:** High.

## Where nothing serious was found

- Rescoring successful main and replication answers reproduced stored brand and citation metrics without discrepancies. No successful duplicate model/trial/condition rows were found in those datasets.
- Main Bedrock responses contained no errors. Replication logs contain failed attempts, but included models retain 1,349–1,350 successful answers; failed attempts were not found contaminating the analyzed outcomes.
- No further serious implementation issue was identified in the reviewed robustness or callout analyses.
- No serious macro-wiring problem was identified in `paper/make_numbers.py`; the sole regenerated macro discrepancy is unused.
- The audit did not uncover a material numerical failure in the principal paired treatment estimates. **The strongest adverse finding is narrower: the paper’s pooled position-significance claim is not supported by a permutation procedure preserving the shared trial structure.**
