# Independent IP&M referee review — round 4

**Rating: 7.0/10, up from 6.5/10. My journal recommendation remains major revision, but the manuscript is now reasonably close to submission-ready as a bounded empirical benchmark.** I would make the focused corrections below before sending this exact snapshot; I would not require another paid experiment or a completed recommendation study as a condition of submitting the narrower paper.

**Reviewed snapshot:** `/tmp/aeo-v4`, branch `review-v4`, commit `82fe67e`, compared with `/tmp/aeo-v3` at `8743de4`.  
**Report:** `/tmp/astra_review_round4.md`.  
**Scope:** report only. No tracked files were edited, and no commits, pushes, pull requests, external contacts or experimental model/API calls were made. Executable checks and generated outputs were isolated under `/tmp/astra-v4-verification/`.

Below, **E2** abbreviates `experiments/exp2_content_treatments/`. Line references refer to the reviewed v4 snapshot.

## 1. Overall assessment and decision odds

The improvement is substantive. The new follow-up compares the same sentence on two supplied pages within one run, has complete data, follows the released estimator, and yields reproducible results. The paper now reports absolute rates, handles the recommending-arm ceiling, reports the previously omitted citation outcome, and substantially improves its chronology and scope disclosures. The recommendation amendment also repairs the logically unattainable version-1 gate rather than pretending that it had only been waiting for human agreement.

The advance is **not** a demonstration that genuinely independent sources are more persuasive, that mentions are favourable recommendations, or that the interventions improve visibility in deployed answer engines. Moving the sentence changes its host document, its position in the supplied context and the number of documents naming the target. The new study narrows an important ambiguity in the earlier experiment, but does not remove all of those distinctions.

The strongest submission is still a paper about **potential first-party access obstacles and conditional content-selection effects across controlled task regimes**. The access audit and the content experiments are complementary measurements, not an estimated causal chain. That positioning is now much clearer.

### Subjective editorial forecast

These are judgment ranges, not calibrated probabilities or journal statistics. “Eventual acceptance” includes subsequent revisions following a submission.

| Submission state | Desk-rejection risk | Eventual acceptance at IP&M |
|---|---:|---:|
| This snapshot, essentially unchanged | 30–45% | 20–35% |
| After the focused scope, provenance-label and release corrections below | 25–35% | 30–45% |

If externally reviewed, major revision remains more plausible than minor revision or acceptance. The main risks are contribution/fit, synthetic-stimulus generalisation and outcome validity—not a failure to reproduce Table 7. A human-checked recommendation analysis could improve the contribution, including through a negative result, but it is optional for a consistently mention-based paper.

## 2. Independent verification

I used the existing Python environment and a scratch archive of the reviewed commit. The environment included Python 3.12.3, pandas 3.1.1, NumPy 2.5.4 and SciPy 1.18.1.

| Check | Result |
|---|---|
| `analyze_site.py` | Exit 0; regenerated the separate-site analysis |
| `analyze_site_extra.py` | Exit 0; regenerated descriptive extras |
| `python attribution.py` | Exit 0; attribution and separate-site prompt checks passed for all 90 trials |
| `paper/make_numbers.py` | Exit 0 |
| `paper/check_claims.py` | Exit 0; **423 checks passed** |
| Full pytest suite | Exit 0; **96 passed**, no skips |
| Separate-site summary and effects CSV | Same structure and values within `1e-12`; maximum numerical difference `5.55e-17` |
| Separate-site descriptive JSON | Exact parsed-value match |
| Rescoring released answers | Recomputed brand/source metrics, including mention, first mention, target-page citation and guide citation, for all **5,400** answers; zero discrepancies |
| Prompt provenance | Every row matches rebuilt item metadata, settings and fingerprint; every model follows the planned randomized block/arm order |
| Existing materials | Main and attribution item digests are identical between v3 and v4 |
| Repository cleanliness | Both reviewed worktrees remained clean |

The author's “95 passed, one skipped” becomes 96 passed here because the environment contains the optional dependencies for the mocked Bedrock test; this is not a disagreement about the test suite.

The unchanged main-item digest is:

`2132d8f751aac9fd32cda2358c60dbfe343960f1eae4e31db0b9380e70fbc51c`

The unchanged attribution-item digest is:

`3355972b0778bd4855e6cd2a7ae56f59ce6f6448f6b53283517d86a232a7d33a`

I also verified that the separate-site Q0/Q1 prompts equal their attribution Q0/Q1 counterparts.

### One regeneration exception

Among the regenerated paper TeX files, only `numbers.tex` differed: the committed, apparently unused macro `SmRhoPawc` is **0.95**, whereas regeneration gives **0.94**. Direct calculation from the released local-model effects gives Spearman's rho **0.9428571428571428**, which rounds to 0.94. This is not merely a last-bit numerical difference.

References: `paper/numbers.tex:1696`; `paper/make_numbers.py:315–317`.

I found no manuscript use of `SmRhoPawc`; the main-text statistic uses the distinct `RhoPawc` macro. This does **not** change the new follow-up's results or the review verdict, but the generated artifact should be synchronized. It also illustrates why 423 passing selected checks do not establish that every generated value matches.

### Paper build and PDF

No `pdflatex`, `xelatex`, `lualatex`, `latexmk` or `tectonic` executable was available on PATH, so I did **not** perform a fresh TeX build. I inspected extracted text from the committed PDF: it has **47 pages**, references begin on **page 24**, and Section 5.4 and Tables 6–7 on pages 19–20 agree with the source and checked headline results. This is a content check of the committed PDF, not fresh compilation or a comprehensive visual-layout review.

The verification logs and the independent row/hash audit are retained under `/tmp/astra-v4-verification/`, including `exits.txt`, `claims.log`, `tests.log` and `site-audit.json`.

## 3. Separate-site specification, provenance and completeness

### What was specified and implemented

The five arms, three primary contrasts, outcome hierarchy, scenario-level inference, completeness threshold and decision rules are coherent and implemented as described.

- B is a fresh baseline.
- Q0/Q1 append the fictional reviewer's neutral/recommending sentence to the target's page.
- T0/T1 append the identical respective sentence to the buyer's guide, leaving the target's page unchanged.
- All arms use the same 30 scenarios, three trials per scenario, six supplied sources and paired source ordering.
- The primary outcome is mention; first mention and target-page citation are secondary.
- Models require at least 87 complete five-arm trials.
- The primary family contains the three stated contrasts, with Holm correction.

References: E2 `README.md:976–1021`; `attribution.py:37–73`; `analyze_site.py:19–95`.

The shared inference utility uses equal-model estimates, 4,000 joint scenario-bootstrap draws and 10,000 scenario-level sign flips. Equal-developer weighting is a sensitivity analysis. It does not treat the models as independently sampled members of a model population. References: E2 `followup_common.py:158–185`.

### Frozen hashes

All nine released code-hash prefixes in the separate-site freeze record match the reviewed files:

| File in E2 | Matching SHA-256 prefix |
|---|---|
| `attribution.py` | `ad59a7d8a8221866` |
| `build_corpus.py` | `f1761247cd906768` |
| `attribution_runner.py` | `fe4d8e646881381d` |
| `run_experiment.py` | `a2b34a96bb2936a2` |
| `analyze_site.py` | `1e0c6e31ee9b6580` |
| `followup_common.py` | `b45f9a1cdc6bb803` |
| `plan_followup_costs.py` | `17055a9a6b711df8` |
| `run_site_parts.sh` | `ce7ef89e3c3e4784` |
| `combine_attribution_parts.py` | `acf9d1b42e64628a` |

The response-file prefix `bcbb2a48a0c5e77f` also matches. Every response contains the rebuilt full items/settings fingerprint beginning `f6bfb0e89f56bffc`.

The private cost plan with prefix `fa48cc93de52fc2c` is unavailable. I cannot verify its contents, projection, exact per-model caps or hash. Matching the public code and response hashes establishes consistency with the released snapshot, **not when those files were frozen**.

### Timing: a better record, still not independently timestamped preregistration

The public responses establish:

- Earliest recorded request start: **17:31:16.042735 IST**.
- Latest recorded response completion: **18:31:51.459921 IST**.
- The README reports a freeze at **17:31:11 IST** and the last model process finishing at **18:31:57 IST**.
- Commit `82fe67e` records a commit time of **19:13:21 IST**, after the run.

Thus the recorded first request is approximately **5.043 seconds after the claimed freeze**. That is internally consistent. However, the freeze time and hashes were committed after execution; neither the timestamp written in the README nor the commit metadata independently establishes that the protocol existed unchanged before the first request.

The six-second difference between the last stored response and the reported process finish is not necessarily contradictory: response completion and process exit are different events. The public answer file verifies the former; the private process-completion log needed to verify the latter is absent. Label these events distinctly rather than calling 18:31:57 the independently verified final-answer time.

References: E2 `README.md:1030–1039`; `paper/appendix_study2.tex:95–103`.

The paper appropriately discloses that this design followed the earlier attribution results and that its public record came later. I would call it an **author-recorded pre-execution specification**, not independently verified preregistration. There is no basis here to allege retrospective alteration, but there is also no basis to certify its absence.

A related claim-check label is too strong: `paper/followup_checks.py:92–93` checks that response timestamps exceed a hard-coded asserted freeze time. It does not verify the historical freeze. Relabel that check accordingly.

### AWS-account change and costs

The initial execution paragraph specifies the second AWS account; the freeze/run record says its smoke calls were refused by an organisation policy and that execution used the first account, also used previously. The manuscript appendix discloses this deviation.

References: E2 `README.md:1023–1035`; `paper/appendix_study2.tex:98–100`.

This is a disclosed administrative deviation, not by itself a reason to reject the within-run contrasts. The released records have consistent model identifiers/settings, and there is no evidence of a treatment-specific account switch. However, they do not authenticate account identity, the refused smoke calls, zero spend on that account, or provider billing.

Summed recorded ceiling-price costs and budget charges both equal **$7.29973264**; no row has unresolved usage. That supports the rounded **$7.30** estimate. It does not verify the approximately **$5.80** bill. The latter is correctly marked unverified. The $7.80 planning projection and private cap allocation remain author-reported.

The original “It runs on the author's second AWS account” paragraph should simply be labelled the original plan so it cannot be mistaken for the executed configuration.

### Completeness

The released dataset contains:

- **5,400 unique model–trial–arm attempts and request IDs**;
- **5,400 successful, nonempty answers**;
- **12 models**, each with **90 complete five-arm trials**;
- **1,080 complete model–trial blocks**, with no exclusions;
- only `end_turn` stop reasons;
- a maximum recorded output length of **1,426 tokens**, below the 4,000-token allowance.

No replacement of failed calls is visible or needed. Full coverage supports “no model stopped short at a cap,” although the private execution journals themselves were not available. Crucially, **1,080 blocks are not 1,080 independently sampled scenarios**: there remain 30 scenario clusters.

## 4. Results and interpretation

### Absolute rates

These are equal-model percentages; all models have complete, balanced data.

| Arm | Target mentioned | Named first | Target page cited | Guide cited, post hoc |
|---|---:|---:|---:|---:|
| B | 50.7 | 18.5 | 43.4 | 69.8 |
| Q0: neutral, brand page | 81.7 | 31.8 | 76.2 | 67.6 |
| Q1: recommending, brand page | 92.9 | 58.1 | 86.9 | 58.6 |
| T0: neutral, guide | 86.3 | 35.3 | 73.0 | 85.5 |
| T1: recommending, guide | 93.7 | 61.2 | 79.2 | 90.6 |

The mention rates in Section 5.4 are correct. The terminology “recommending” describes the **stimulus**, not a human-coded property of the resulting answer.

### All three contrasts and outcomes

Effects and intervals are in percentage points. Intervals are marginal 95% scenario-bootstrap intervals; p-values are Holm-adjusted within each three-contrast outcome family.

| Outcome | Contrast | Effect [95% CI] | Holm p |
|---|---|---:|---:|
| Mention | T1 − Q1 | +0.8 [−0.8, 2.7] | .441 |
| Mention | T0 − Q0 | +4.6 [1.9, 7.4] | .013 |
| Mention | (T1 − T0) − (Q1 − Q0) | −3.8 [−6.7, −1.1] | .031 |
| First mention | T1 − Q1 | +3.1 [−0.5, 6.9] | .271 |
| First mention | T0 − Q0 | +3.5 [1.5, 5.5] | .004 |
| First mention | Interaction | −0.5 [−3.7, 3.1] | .838 |
| Target-page citation | T1 − Q1 | −7.7 [−10.2, −5.3] | <.001 |
| Target-page citation | T0 − Q0 | −3.2 [−6.7, 0.1] | .082 |
| Target-page citation | Interaction | −4.4 [−8.1, −1.0] | .057 |

Table 7 reproduces these results correctly, including leaving the citation interaction unstarred despite its marginal interval excluding zero. Holm adjustment of tests does not turn the bootstrap intervals into simultaneous confidence intervals. The outcome-specific families also do not provide one omnibus correction across every outcome, weighting and earlier experiment.

References: `paper/table_site.tex:6–17`; `paper/results_attribution.tex:64–88`.

### What the experiment adds

**1. The neutral placement effect is supported within this benchmark.** The +4.6-point estimate survives the stated primary correction; the equal-developer estimate is +3.9 points, Holm p .034. Eight models have positive estimates, three negative and one zero. It is neither universal across models nor evidence of a population-wide trust premium.

**2. Total added target-name frequency is matched between Q and T.** Both add the same sentence with one target mention. The distinctive change is that T introduces the target into a **second document**, whereas Q repeats it within its existing document. Calling this merely “an extra mention” without specifying document frequency would obscure a genuine strength of the design. Nevertheless, document dispersion, host-page context and position remain bundled with placement; perceived independence is not separately identified.

**3. The recommending contrast is inconclusive, not equivalent.** Both arms are already near the mention ceiling. The +0.8-point estimate and its interval do not warrant “the source location does not matter.” The manuscript mostly handles this correctly.

**4. The interaction is correctly signed but should be written explicitly.** Algebraically,

`(T1 − T0) − (Q1 − Q0) = (T1 − Q1) − (T0 − Q0).`

Recommending wording adds approximately **11.2 points on the brand page** and **7.4 on the guide**, giving −3.8 points. It is not evidence that recommending wording harms mentions. The equal-developer interaction is −3.3 points, Holm p .070, and ceiling compression is a plausible interpretation, not an identified mechanism.

Section 5.4 discusses the neutral contrast before the recommending contrast, whereas the table/specification list recommending first. Replace “the difference between the first two” with the equation or named contrasts to remove that avoidable ambiguity. Reference: `paper/results_attribution.tex:77–82`.

**5. Citation allocation changed; literal citation transfer is not established.** The pre-specified decrease in target-page citations is supported. Guide-citation rates were added after results and are correctly identified as such in the README, analysis docstring and appendix; the main text calls them descriptive.

However, “citations moved from the brand's page to the guide” is stronger shorthand than necessary. Target-page citation falls 7.7 points, while guide citation rises about 31.9 points; these are not complementary events. My descriptive recomputation finds both pages cited in **54.7% of Q1 answers and 77.8% of T1 answers**. Say “target-page citations decreased while guide citations increased descriptively,” not that the evidence traces a zero-sum transfer or establishes factual attribution.

References: `paper/results_attribution.tex:83–94`; `paper/discussion.tex:26–29`; E2 `analyze_site_extra.py:1–10, 63–75`.

**6. Repeated arms provide descriptive consistency, not another independent confirmation.** Across the 11 models eligible in both follow-ups, the new B/Q0/Q1 rates are 49.7/80.8/92.3%, compared with 49.1/80.8/92.9% previously. These figures are correct. The scenarios and prompts are reused, and the runs differ in time and completeness; neither equivalence nor fresh scenario-level replication follows.

## 5. Reassessment of the round-three requests

| Earlier concern | Round-four assessment |
|---|---|
| Attribution freeze chronology overstated | **Substantially addressed.** The minute-resolution limitation and post-run commit are explicit. Historical pre-query ordering remains unverified, not newly proved. E2 `README.md:603–607`; `paper/appendix_study2.tex:85–94`. |
| “Wording mattered more than source” too general | **Substantially addressed.** Section 5.4 specifies the measured wording/source contrasts, two templates, fictional reviewer and exclusivity of “the option.” `paper/results_attribution.tex:48–52`. |
| Missing absolute rates, denominator and truncation | **Addressed.** The five attribution mention rates are 49.1/79.7/89.8/80.8/92.9%; the text reports 989 complete blocks and the Mistral answer reaching its limit. `paper/results_attribution.tex:13–17, 29–46`. |
| Baseline “reproduction” implied equivalence | **Addressed in the paper.** It now says “close,” reports agreement and explicitly denies an equivalence test. `paper/results_attribution.tex:43–46`. |
| Freshness described as doing nothing | **Addressed.** “Did not outperform the placebo” is the appropriate claim. `paper/discussion.tex:33–34`. |
| Interface observations used to infer answer provenance | **Addressed.** The discussion says the interface does not show the source; the conclusion drops the unsupported earlier-crawl/training comparison. `paper/discussion.tex:10–19`; `paper/conclusion.tex:1–12`. |
| Synthetic endorsement used to establish earned coverage | **Much improved in the manuscript.** It distinguishes stated attribution from independent coverage. The literature comparison can remain, but the linked practitioner summary is still broader than the experiment. `paper/discussion.tex:21–29`; `README.md:44–46`. |
| Every number/claim said to be independently checked | **Addressed in substance.** Generated results and selected checks are distinguished; limitations explicitly exclude independent validation of extraction/all prose. `paper/main.tex:86–90, 480–483`. |
| Pre-specified citation outcome omitted | **Addressed.** Table 6 now includes all three outcomes. The outside-source citation effect is +2.1 points, Holm p .104, and is correctly described as not surviving correction. `paper/results_attribution.tex:39–41`; `paper/table_attribution.tex`. |
| Review log inaccurately said all changes preceded paid queries | **Addressed by a clear dated correction**, while preserving the historical wording. `reviews/2026-11-10-gpt-6-astra-round-2/07-verification.md:8–13`. |
| Superseded README rules looked current | **Improved.** Historical budgets, token limits, no-retry policy and pair threshold are marked. The separate-site account paragraph still needs the same treatment. E2 `README.md:682–687, 867–875, 924–928, 951–965, 1023–1030`. |
| Framework presented as an estimated model | **Addressed.** It is now a decomposition organising the studies, not an estimated model. `paper/main.tex:162–183`. |
| AI assistance inadequately disclosed | **Addressed.** The statement names Astra's design/code contribution as well as review and drafting, and assigns responsibility to the author. `paper/main.tex:520–524`; `submission/journal/declarations.txt:21–28`. |

### Compression: real, but distinguish the intermediate edit from the final snapshot

The findings are now three bullets, the discussion is substantially shorter, the conclusion is focused, and secondary implementation/interface detail has moved to appendices. These are worthwhile changes, not merely typographic compression.

I cannot reproduce a **net 15% reduction for the final v3-to-v4 manuscript** under a consistent approximate source-prose count. Recursively expanding main-text inputs and excluding floats, displayed equations, references and TeX commands gives approximately **10,114 words in v3 and 9,284 in v4: an 8.2% reduction**. This is not an official journal word count. PDF text including tables and other extracted material falls from 13,747 to 13,220 words, approximately 3.8%. Both PDFs remain 47 pages, but references move from page 25 to page 24.

The reported 10,200-to-8,660 reduction may describe the compression pass before the separate-site material was added. Describe the counting convention and version if retaining that claim. Do not discard essential limitations merely to achieve a percentage; nor is another blanket 15–20% cut now a prerequisite.

Reference: `reviews/2026-11-10-gpt-6-astra-round-3/03-changes-after-review.md`, “Compression” and subsequent separate-site additions.

## 6. Recommendation amendment: repaired design, pending human evidence

### What is now sound

The old “57/60 valid but completeness required 60/60” obstruction is explicitly acknowledged and no longer describes the amended gate. The amendment is a transparent post-holdout-exposure revision with fresh checking, not a claim that version 1 passed.

The public implementation supports:

- A new 48-item probability panel and 12-item challenge panel, with six repeats, disjoint from the pilot, practice and retired version-1 holdout.
- Retention of the old 60 items in the eventual census, but not in the new human check.
- Uniform identical-request re-asks after invalid outputs, capped at three calls; the first valid output is used.
- A gate requiring at least 44/48 definite binary agreements, fewer than two observed warning-only false positives, valid human presentations and explicit author error review.
- An 80-valid-pair threshold per model/contrast instead of 87.
- Binding the parser/rubric module's source hash into the amended protocol, with a load-time mismatch check.
- A full-coding runner that requires a passing report for the same judge, protocol and configuration.

References: E2 `README.md:803–847`; `make_recommendation_manifest.py:124–127, 131–199`; `recommendation_protocol.py:35–49`; `run_recommendation_judge.py:15–22, 34–75`; `score_recommendation_human.py:71–93`; `analyze_recommendation.py:67–82`.

The added tests cover the fresh balanced draw, invalid-output re-asks, rejection of a retry after a stored valid output, the three-call limit and the amended gate. They passed. The version-1 challenge-selection refactor preserves the rule in the source diff; this is distinct from authenticating the unavailable historical manifests.

Reducing the pair minimum is defensible for an explicitly exploratory analysis with only 87–88 available pairs after development exclusions. It is nevertheless a relaxation adopted after discovering a feasibility problem, and must remain visible. Fresh holdout checking does not retroactively make the recommendation endpoint confirmatory.

### What is still not verified

There is no `data/private/` directory in this checkout. Therefore I cannot independently verify:

- the 16:42 freeze or the private manifest/workbook actually used;
- the reported amended GPT-5 mini pilot result of 83/84 valid;
- the reported fresh holdout result of 60/60 valid after one re-ask;
- the Qwen pilot's 0/84 validity after 252 calls;
- the 16:55 second-judge decision, spending or absence of human labels/effect inspection at those times.

Those are public author reports, not reproduced private results. References: E2 `README.md:849–865`.

Following the declared fallback's failed formatting gate without changing the parser to admit it is a reasonable documented choice. It establishes neither that Qwen lacks semantic coding ability nor that GPT-5 mini has validated accuracy.

Most importantly, **60/60 format-valid outputs are not a passed human gate**. No completed human-agreement report is available. The status is now **feasible under the amendment, pending human evaluation**, rather than **logically blocked under version 1**.

### Two implementation/reporting limitations to address before using this analysis

1. **Re-asks are not yet reported by condition in the public analysis output.** The README promises this, but `recommendation_data.py:54–61` aggregates re-asked attempts by judge, and `analyze_recommendation.py:91–95` reports final item coverage by model/condition, not retry exposure by condition. Final missingness is not the same as how many attempts were needed. Add the promised breakdown before interpreting condition-dependent coding outcomes.

2. **The historical-attempt validator trusts earlier validity flags.** `recommendation_data.py:21–40` rejects retries after an earlier stored `valid=True`, but only the retained attempt is reparsed at lines 56–69. It therefore does not independently establish that every earlier discarded output was actually invalid under the frozen parser. Revalidate all retained attempt histories when auditing first-valid selection. This is a limitation of the audit guarantee, **not evidence that selective retries occurred**.

Neither issue changes the current mention results. Both matter if recommendation coding is added later. A single rater, six repeats and a 48-item probability panel remain a workflow/feasibility check, not independent gold-standard validation or inter-rater reliability. Keep probability and challenge panels separate, retain initial labels, report uncertainty and invalidity, and do not select a judge or analysis because its treatment effects are favourable.

If the human gate fails, omit the scaled recommendation claim or clearly label any permitted analysis unvalidated and exploratory. If it passes, report the gate and its limits, not merely “validated by a human.” There is no need to hold the narrower paper indefinitely for this optional study.

## 7. Ranked remaining actions

### 1. Keep every public-facing claim within the identified manipulation and outcome

**Importance: highest scientific/communication risk; a focused wording pass, not a required new experiment.**

Retain the manuscript's explicit synthetic-page, mention-only and non-independence caveats. Carry that precision into the short synthesis and linked practitioner material. In particular, the broad “Engines lean on reviews, press, communities and reference sites more than on your own pages” claim in `README.md:44–46` is not established by this experiment. The handbook's corroboration row should distinguish external literature/practical advice from the tested package: `docs/04-content-techniques.md:26`.

Replace citation-transfer shorthand with the measured marginal changes, and write the interaction explicitly. References: `paper/results_attribution.tex:77–94`; `paper/discussion.tex:26–29`; `README.md:100–102`.

**Completion criterion:** no reader is invited to infer an independence premium, favourable recommendation improvement or production-engine efficacy from these results.

### 2. Finish the provenance labels without pretending to repair history retrospectively

**Importance: must fix the overstrong audit language; no new data collection required.**

Label the second-account paragraph as the original plan; distinguish the recorded last response from reported process exit; call the freeze author-recorded; and narrow the automated chronology-check label. Preserve the explicit post-run-publication caveat.

References: E2 `README.md:1023–1039`; `paper/followup_checks.py:92–93`; `paper/appendix_study2.tex:95–103`.

If genuinely pre-existing redacted logs or externally timestamped artifacts are available, preserve them. A new retrospective record cannot supply an old independent timestamp. No credentials, account secrets or private human labels need to be published.

### 3. Treat recommendation readiness as conditional, not as a completed result

**Importance: required only if recommendation findings are included.**

Complete the unchanged human gate before full coding, keep the analysis exploratory, report retry exposure by condition and audit all attempts. Retain the single-rater and single-judge limitations.

References: E2 `README.md:824–865, 907–948`; `recommendation_data.py:21–75`; `run_recommendation_judge.py:15–36`; `analyze_recommendation.py:91–95`.

**Completion criterion:** either no recommendation-improvement claim is made, or it is accompanied by a genuine passing report, coverage, disagreement and missingness evidence. More model calls alone do not satisfy this condition.

### 4. Synchronize generated artifacts and complete submission preflight

**Importance: small release corrections.**

Regenerate the stale unused `SmRhoPawc` macro, build the final paper in a TeX-equipped environment, and check the final PDF after those edits. The current review did not establish a fresh build.

References: `paper/numbers.tex:1696`; `paper/make_numbers.py:315–317`. The cover letter also still contains an arXiv placeholder and confirmation text; `submission/journal/cover-letter.txt` is a template, not a send-ready letter.

### 5. Make only selective further compression and contribution clarification

**Importance: editorial improvement, not another blanket rewrite.**

The paper now has a sensible three-part findings list and a better conclusion. If shortening further, remove repeated implementation history and secondary summaries rather than adding another study. State the final word-count convention if advertising a percentage reduction.

The substantive fit risk remains that the access audit and synthetic benchmark are adjacent rather than empirically linked. Keep the decomposition explicitly organisational and centre the controlled task-regime result. References: `paper/main.tex:76–90, 162–183, 465–504`; `paper/findings.tex:1–21`.

## 8. Bottom line

The fourth version earns **7.0/10** because it fixes important reporting defects and adds a complete, reproducible within-run placement comparison. The strongest new result is that the same neutral attributed sentence produces a modest mention increase when moved to the synthetic guide; the recommending-arm contrast is unresolved near the ceiling, and citation outcomes change.

Most round-three requests are now addressed. The historical freeze remains author-attested, the recommendation study remains human-gate pending, and the final manuscript is shorter but not demonstrably 15% shorter than v3 under a consistent final-snapshot count. None of these facts should be disguised by passing tests or by the additional 5,400 calls.

**I would proceed toward submission after the focused finishing pass above, without requiring another paid experiment. I would still recommend major revision rather than acceptance at IP&M, and would judge the paper as a scoped benchmark—not as validation of independent-source credibility, favourable recommendations or deployed answer-engine optimisation.**
