# GPT-6 Astra's third review: the committed version (10 November 2026)

- Reviewer: GPT-6 Astra (OpenAI), reasoning level Extra high, in the same thread as round 2
  (`thr_1e8d3bd617294e43b459e36bdbfc8e2c`; 47 tool calls), so it knew its earlier review and build.
- Reviewed: the author's local commit `8743de4` (with `9f808f6`), sent as a git bundle over the public `d2bfbf2`
  (bundle SHA-256 8168b726...d5a6, verified in the sandbox). No API keys; no edits, commits or pushes.
- Brief: [01-brief.md](01-brief.md), exactly as sent.
- Copied byte for byte from `/tmp/astra_review_round3.md` in Astra's sandbox (SHA-256 5e03760c...880c).

---

# Independent IP&M referee review — round 3

**Reviewed snapshot:** `/tmp/aeo-v3`, branch `review-v3`, commit `8743de4`.  
**Report:** `/tmp/astra_review_round3.md`.  
**Scope:** report only; committed paper, attribution data and analyses, implementation changes, and recommendation-study readiness. No experimental model/API calls, repository edits, commits or pushes were made. The `hop` repository was not accessed.

## 1. Verdict and revised rating

**My rating is 6.5/10, up from 6/10. My recommendation remains major revision, not acceptance, and I would not submit this exact version to IP&M.** The increase is earned by a genuinely useful attribution follow-up, reproducible numerical results, and substantially better separation of measured outcomes from practical claims. It is not earned merely by more calls, another table, or the coordinator's assessment.

The paper now offers a credible controlled benchmark: intervention packages affect synthetic-brand mentions, and their effects depend on the supplied-page versus searchable-corpus task. The new experiment separates recommendation wording from a stated external-source cue **within a brand's own supplied page**. That is a meaningful improvement over attributing the original guide-endorsement effect to provenance.

What still limits the paper is the gap between this contribution and a general account of answer-engine optimisation. Mention is not favourable recommendation; an invented reviewer attribution is not independent evidence; the search-task contrast changes several things besides retrieval; and the website audit is not empirically linked to the content experiment. A 47-page manuscript also asks readers to follow too many secondary narratives.

There are two immediate audit issues:

1. The public record does not independently establish the exact ordering of the attribution freeze and the first query. It is consistent with a pre-query freeze, but does not prove one.
2. The recommendation study is not merely waiting for a human to pass its gate: the documented **57/60 valid held-out judge outputs already fail the implemented completeness requirement**.

### Rough decision odds

These are subjective editorial forecasts, not journal acceptance statistics or calibrated probabilities. Eventual acceptance means acceptance at IP&M after whatever revisions follow this submission.

| Submission state | Desk-rejection risk | Eventual acceptance at IP&M |
|---|---:|---:|
| This committed version, essentially unchanged | 35–50% | 15–30% |
| After the focused corrections and compression below, with honest resolution or omission of the recommendation analysis | 25–40% | 25–40% |

If sent to reviewers, major revision or rejection is much more plausible than minor revision. A well-executed recommendation analysis could help, but a favourable treatment result is neither necessary nor a guarantee of acceptance. A negative or discordant result can improve the paper by showing where mention-based conclusions stop.

## 2. What I independently verified

I reran the attribution analysis into `/tmp/astra-v3-verification`, redirected the descriptive-extra analysis to that directory, reran `paper/check_claims.py`, and ran the full pytest suite. The successful verification used the existing `/tmp/aeo-venv` environment: Python 3.12.3, NumPy 2.5.4, pandas 3.1.1 and pytest 9.2.0. An initial confirmation attempt with system Python lacked dependencies; the environment-backed reruns below completed successfully.

| Check | Verified result |
|---|---|
| `analyze_attribution.py` and `analyze_attribution_extra.py` | Both completed; analysis chain exit 0 |
| Generated versus committed attribution summary | Same structure and values within `1e-12`; 32 float differences, maximum absolute difference `5.55e-17` |
| Attribution effects CSV | All 30 rows matched within `1e-12` |
| Descriptive-extra JSON | Exact parsed-value match |
| `paper/check_claims.py` | Exit 0; **258 checks passed** |
| Full pytest suite | Exit 0; **88 passed**, no skips, in 26.24 seconds |
| Mechanical attribution-template checks | Passed for all 90 trials; fresh baseline prompts exactly equal the main baseline |
| Independent recomputation of stored outcomes | Recomputed mention, first mention and citation for all **5,374 successful responses**; zero discrepancies |
| Prompt/order provenance within the released records | Every row's fingerprint matches the rebuilt attribution design; every model follows the same randomized trial/condition sequence, or its prefix |
| Main-study materials versus the round-2 handoff | All 1,350 generated main items have the same canonical digest: `2132d8f751aac9fd32cda2358c60dbfe343960f1eae4e31db0b9380e70fbc51c` |

I also checked the extracted committed PDF: Section 5.4 and Table 6 on pages 19–20 agree with the source and regenerated headline results. The PDF contains 47 pages. This was a content check, not a fresh LaTeX build or comprehensive visual-layout review.

These checks establish reproducibility of the released calculations. They do **not** independently validate every sentence, the semantic interpretation of outcomes, provider billing, historical pre-specification, or unavailable private pilot records. The paper correctly acknowledges some of these distinctions, but its introduction's claim that every reported number is regenerated and checked is too absolute.

### Counts, exclusions and settings

- There are **5,385 unique model/trial/condition attempts**, out of 5,400 planned.
- **5,374 succeeded; 11 failed:** ten Nemotron and one Claude Sonnet 4.6.
- Nemotron has 435 attempts and **81 complete five-arm trials**, below the required 87; its exclusion follows the stated rule.
- Claude has **89 complete trials**; the other ten included models have 90 each.
- The analysis therefore uses **989 complete model–trial blocks**, or 4,945 successful answers, across 11 models and 30 scenarios. This is not 989 independent scenarios.
- All rows record the same requested settings: 4,000 output tokens, temperature 0, no web search, zero transport retries and order seed 20261110. Requested settings are not proof that every backend implements temperature identically.
- One successful Mistral response reached 4,000 tokens. It was scored as written; this deserves a short disclosure alongside the failures.
- Summed recorded token-cost estimates are **$7.3104**; conservative budget charges total **$7.4251**, including reservations for unresolved usage. Neither sum independently verifies the reported roughly $5.90 provider bill. Do not describe reservation charges as confirmed billing for failed requests.

## 3. Attribution results: correct numbers, bounded interpretation

### Primary and selected secondary effects

All estimates below are percentage-point differences. Intervals are marginal 95% scenario-cluster bootstrap intervals; the displayed p-values are Holm-adjusted within the relevant three-contrast family.

| Contrast | Mention effect | Adjusted p | First-mention effect, secondary | Adjusted p |
|---|---:|---:|---:|---:|
| S1 − S0: recommending versus neutral wording, brand as source | **+10.1 [6.7, 13.8]** | 0.000300 | +23.3 [17.9, 29.4] | 0.000300 |
| Q1 − S1: external reviewer versus brand, recommending wording | **+3.1 [1.4, 4.9]** | 0.002600 | +4.9 [2.9, 6.8] | 0.000300 |
| (Q1 − Q0) − (S1 − S0): interaction | **+2.0 [−0.6, 4.6]** | 0.150385 | +3.2 [1.2, 5.4] | 0.008399 |

Table 6, the abstract and the findings list reproduce the headline estimates correctly. Equal-developer weighting gives mention effects of approximately +9.7, +3.2 and +1.7 points, with the same significance decisions. These are sensitivity results, not independent replications.

The paired analysis, shared scenario resampling, shared sign flips, equal-model weighting and three-test primary Holm family are appropriate for the stated conditional estimand. I found no material arithmetic or pairing error. Models are a fixed panel; the bootstrap does not turn them into a random sample of developers or production assistants. The sign-flip calculation also relies on its scenario-level exchangeability/symmetry rationale; shared signs address dependence, not every inferential assumption.

### The five arm levels belong next to the effects

Equal-model mention rates are:

| Arm | Mention rate |
|---|---:|
| Fresh baseline B | 49.14% |
| Brand, neutral S0 | 79.68% |
| Brand, recommending S1 | 89.79% |
| Outside reviewer, neutral Q0 | 80.79% |
| Outside reviewer, recommending Q1 | 92.92% |

This is essential context. **S0 − B is +30.5 points [25.7, 35.5]**, descriptively. The nominally neutral addition is not inert: it repeats the target, directly matches the scenario's need, adds text and carries a review-team frame. B deliberately lacks these additions. Its effect cannot be allocated separately to repetition, relevance, length or framing.

Consequently, the follow-up isolates the S/Q contrasts better than the original endorsement package, but does not decompose that original package completely. Moving the manipulation onto the brand page changes the setting. A +3.1-point external-attribution increment at an S1 baseline near 90% should not be dismissed as universally unimportant: the binary outcome has little remaining headroom. Ten of eleven models already mention the target in at least 85% of S1 answers.

The defensible conclusion is:

> In these supplied synthetic pages, recommending rather than neutral wording produced a larger estimated absolute increase in target mentions than changing the stated source of that recommendation from the brand's team to one fictional outside team. The external-source cue nevertheless increased mentions. The interaction for mentions remained unresolved.

That is narrower and better than “what a recommendation says mattered more than who was said to make it.” The experiment tests two wording templates and one evaluator identity, not provenance in general, verified independence, reputation, credibility, factual merit, or publication on a separate site. “The option” versus “one/an option” also packages exclusivity with recommending language.

### Baseline reproduction and consistency

The descriptive extra correctly reports **49.1405% fresh versus 49.7472% original** mentions over the same 989 retained pairs, with **87.4621%** pairwise agreement. The largest absolute model-level rate difference is 6.67 points. This is reassuring aggregate stability, not equivalence testing or proof of deterministic reproduction. Replace “reproduced the original one” with “was close to the original aggregate mention rate.”

All eleven model-level S1 − S0 estimates are positive. Q1 − S1 is positive in nine and zero in two. These are descriptive sign counts, not eleven or nine separately established significant effects. Their post-run status is disclosed appropriately.

Finally, the citation outcome does not mirror every mention result: the external-attribution citation contrast has adjusted p approximately **0.104**. The first-mention interaction is secondary and cannot rescue the nonsignificant primary mention interaction. Keep outcomes separate.

## 4. Audit of Claude's amendments and chronology

### Changes themselves

| Amendment | Referee assessment |
|---|---|
| Replace references to “the question above” with the scenario's stated need | Sensible improvement in webpage realism and separation from an instruction-to-the-model manipulation. It changes the actual stimulus, so the amended wording—not the draft—must define the executed protocol. |
| Replace coded evaluator names with “Neralin” | Reasonable removal of placeholder-like wording. Matching survives, but inference is now conditional on one invented external identity. |
| Raise the cap from $9 to $10 and use the larger of smoke-test and historical average cost | Sensible feasibility amendment if made before follow-up outcomes. Cost-based planning is not outcome-based model selection. Public records support the resulting incomplete panel, but the private plan and journals are unavailable here. |
| Add per-model `--part` execution and parallel launch | Does not inherently compromise pairing. Released row order and fingerprints support unchanged within-model designs. Update the stale fixed-model-order wording and preserve per-model logs. |
| Increase judge output allowance from 256 to 1,024 tokens | A justified development-pilot response to documented truncation, not a reason to discard inconvenient treatment effects. The configurations must remain distinct, and the larger allowance must be frozen and budgeted before evaluation. |
| Normalize evidence spans and permit absent evidence keys for non-true labels | A real parser/protocol relaxation, even if motivated by formatting rather than semantics. Reasonable on development data; not accurately described as unchanged strict verbatim/schema validation. |
| Drop MAI after its pilot | Defensible on the reported usability and cost evidence. This removes cross-judge sensitivity evidence; a human check does not replace it. Decide fallback use on the declared feasibility/budget basis, before treatment-effect inspection. |
| Rewrite the workbook in plain language | Beneficial if definitions and blindness are preserved. Claude-labelled practice examples need genuine author review; they are training examples, not independent validation. |

The optional-dependency test adjustment is not concealing a failure in this review: with dependencies available, all 88 tests execute and pass. The main prompts are unchanged.

### What the timestamps establish

The README records the attribution freeze at **14:24 IST**. The earliest released request started at **14:24:35.194838 IST**, and the last completed at **15:25:02.020019 IST**. The two commits are timestamped **15:39:54** and **15:40:25 IST**, after completion.

All six published source-hash prefixes match the current files. That supports identification of the documented code, but hashes printed in a subsequently committed README do not independently establish when the document existed. Minute-level “14:24” is insufficient to order the freeze against a query at 14:24:35. Nor does the listed freeze cover every analysis or orchestration file and the actual private cost plan.

**This is an evidentiary limitation, not evidence that results were used to tune the protocol.** There is no basis here to accuse the author of retrospective specification. There is also no basis to certify the unqualified “before any query” claim independently.

Best remedy: retain any genuine contemporaneous timestamped freeze artifact and identify exactly what it binds. If none exists, say that the author records the protocol as fixed immediately before execution, with the first-query time disclosed, and acknowledge that the public commit followed the run. Do not create a retrospective artifact and present it as contemporaneous registration.

The recommendation timeline needs a separate treatment: the manifest reportedly froze at 13:53 IST; pilot-driven amendments and evaluation configuration were recorded by 14:34; 60 held-out outputs were then generated before human labels. “Before human labels” is not the same as “before held-out judge exposure.” The private records are absent from this checkout, so I cannot independently establish that ordering or verify the reported pilot counts. The blanket review-log description “before any paid query” cannot literally encompass changes motivated by paid pilots; distinguish pilot, attribution and held-out stages explicitly.

### Disclosure adequacy

Appendix E is substantially better: it names wording/name changes, the $10 cap, parallel execution, failures, exclusion, and post-hoc descriptive extras. It still needs a compact chronology distinguishing **initial draft → execution amendment → run → post-run analysis**, with the $9-to-$10 change stated explicitly and the temporal-evidence qualification above. The README should label old $9 tables, 256-token defaults and superseded execution instructions clearly as historical rather than competing operational specifications.

## 5. Recommendation study: useful, optional, and currently blocked

### Is it required for submission?

**Not for a consistently framed mention/selection paper. Yes, credible semantic measurement is needed if the paper claims that the interventions improve favourable recommendations or preference.** The current abstract's explicit mention-versus-recommendation distinction is a major improvement. A good recommendation analysis would strengthen construct validity, but an under-validated analysis would not.

It must remain a **post-hoc exploratory endpoint**, not a retroactive replacement for the original mention outcome. The planned unconditional definite-recommendation estimand, warning distinction, separate preference outcome, unknown-label bounds and treatment–baseline pairing are sensible. Neither first mention nor an evidence substring proves favourable recommendation or semantic correctness.

### The existing holdout cannot pass the current gate

The README reports 57 valid judge outputs among the 60 held-out human items. In `score_recommendation_human.py:77–85`, `complete` requires every probability and challenge item to exist in both the human and valid judge labels. `gate_pass` requires `complete`. `recommendation_data.py` excludes invalid judge records; the full runner requires a passing report bound to the same protocol and configuration.

Therefore, **on the documented 57/60 state, even perfect human agreement cannot pass**. The 44/48 agreement rule is not a waiver of the separate completeness rule.

Before spending on scaled coding, either stop and omit the outcome, or transparently amend the development/evaluation plan and obtain genuinely fresh checking appropriate to that amendment. Do not selectively retry the three failures, relabel the holdout, silently reinterpret missing as NO, or weaken the gate after seeing these results and call the original protocol satisfied. The one-hour check can still diagnose problems, but cannot certify passage of the current gate.

There is a second feasibility warning: each full-analysis contrast needs 87 valid pairs per model after pilot/practice exclusions. Even the reported 82/84 pilot validity is not automatically sufficient. Illustratively, if approximately 88 candidate pairs remained and each side had independent validity 82/84, expected valid pairs would be about **84**, below 87. This is not a prediction of the actual missingness pattern; it is a reason to resolve feasibility prospectively rather than pay for thousands of labels and discover widespread exclusions. Do not lower the threshold opportunistically after effect inspection.

### The frozen hashes do not freeze the checker

`make_recommendation_manifest.py` hashes `CODEBOOK` and `SYSTEM`; judge configuration hashes cover settings. They do **not** hash `parse_labels` or its normalization implementation. Thus the rubric and configuration hashes alone cannot certify an unchanged acceptance rule. Current reparsing and stored-label comparisons are useful checks, but do not replace a frozen parser/source artifact.

For a renewed study, bind the checker version/source hash, full configuration, split manifest and amendment history before fresh held-out work. Describe evidence as **format-normalized answer substrings**, not byte-verbatim spans. Explain the change from 67/84 to 82/84 valid pilot outputs and the two remaining invalid outputs without equating syntactic validity with semantic accuracy.

### What a one-hour check can support

One blinded non-expert rater can assess rubric usability, obvious warning-as-recommendation errors and limited observed agreement. Six repeats assess within-rater consistency, not inter-rater reliability. Forty-eight probability items and twelve selected challenges cannot establish gold-standard accuracy, treatment-specific validity across all seven conditions, or validity for the attribution corpus. Keyword stuffing is absent from the probability panel.

If the gate eventually passes under an honestly revised protocol, report confusion tables, uncertainty, missingness, warning errors, repeat consistency, actual annotation time and prior familiarity. Preserve initial labels before adjudication. A single primary judge is reportable, but weaker than the originally hoped-for two-judge sensitivity analysis. Never choose a judge according to which treatment effects look preferable.

If the gate fails and scaled coding is omitted, suitable wording is:

> We did not establish sufficiently reliable favourable-recommendation coding under the planned validation procedure. Our primary results concern target mentions and first mentions, not whether an answer endorses or prefers the target. Pilot coding is not used as confirmatory outcome evidence.

If exploratory labels are nevertheless discussed, identify them explicitly as unvalidated and keep them out of headline practical claims.

## 6. Remaining manuscript issues

### Highest-priority claim corrections

1. **Section 5.4 and Discussion:** replace the general “wording mattered more than source” claim with the bounded estimated-effect statement in Section 3 of this report. Show five-arm absolute rates and retain the ceiling explanation.
2. **Baseline paragraph:** say the aggregate rate was close, not that the original baseline was reproduced in an equivalence sense. Retain 989 paired observations and disclose that this comparison is descriptive and conditional on the retained panel.
3. **Discussion, implications:** “freshness stamps, which did nothing here” conflicts with the reported roughly four-point baseline effect and failure to beat placebo. Say they did not outperform the boilerplate control; do not convert nonsignificance into absence of effect.
4. **Conclusion/interface interpretation:** no visible search does not establish the relative contribution of training, earlier crawls, caches or undisclosed retrieval. Remove the inference that earlier crawls/training “may matter as much as the live page” for that product. Report only observed interface behaviour.
5. **Earned-media language:** the synthetic guide and fictional reviewer do not demonstrate the value of genuinely independent coverage. Separate plausible practitioner advice from tested results, particularly “which is one reason earned coverage mattered” and “earn coverage from independent sources.”
6. **Reproducibility claim:** replace “every reported number … checked by script” with a precise account of generated tables/macros and selected automated claims. Raw crawl remeasurement and prose/construct validation remain outside that guarantee.

The abstract's numerical attribution sentence is acceptable with its existing outcome caveat; it need not carry every limitation. The main text must supply the missing scope. The conclusion should give the new follow-up a bounded synthesis sentence rather than giving the weak interface snapshot disproportionate final emphasis.

### What still constrains novelty and validity

- **Study 1:** a useful descriptive access audit, not measured exclusion from answers. Purposive organisational sampling, equally allocated Tranco bands, reachability selection, research-client edge refusals and the JavaScript proxy prevent population/access-probability interpretations. Parser repairs do not retroactively remeasure absent raw crawl records.
- **Study 2:** a controlled benchmark of packages in short synthetic pages, not isolated “quality” improvements. Thirty scenarios remain the material replication units despite many models and calls.
- **Search task:** valuable evidence of regime dependence, not retrieval mediation. Pool size, snippets, tools, budgets and model search compliance all change. Preserve the existing caveats and MAI-exclusion sensitivity.
- **Synthesis:** the chain rule is a useful organising identity, not an empirically estimated causal theory linking the audit to brand selection.

These are not fatal to the narrower paper. They are fatal to broader claims of validated recommendation improvement, real-world source independence, causal retrieval mediation, or demonstrated production-engine optimisation.

## 7. Ranked pre-submission plan

### Priority 1 — Resolve integrity/readiness issues before more spending

- Correct the chronology claim to match the available evidence; preserve any genuine earlier artifacts.
- Treat the recommendation gate as blocked, not merely pending human agreement. Choose omission or a transparently revised, freshly checked protocol.
- Bind any renewed parser/configuration freeze properly. Keep failures and initial labels; do not curate a passing holdout.

**Completion criterion:** the paper and repository distinguish what was planned, amended, observed and independently verifiable, without claiming an unpassed gate.

### Priority 2 — Make the new result the strongest version of itself

- Keep Section 5.4 and Table 6 in the main text.
- Add the five absolute mention rates, the 989-block denominator and a concise missingness/truncation disclosure.
- Present the +30.5-point neutral-addition contrast as descriptive; foreground the mention ceiling.
- Restrict the conclusion to wording and a stated source cue on supplied synthetic pages. Do not claim decomposition of real third-party credibility.

**Completion criterion:** a reader can understand exactly what +10.1 and +3.1 compare without consulting code or confusing them with recommendation outcomes.

### Priority 3 — Fix the six prose claims above

This is a small, high-value pass. Keep the existing distinctions between mentions, first mentions, citations, detector absorption and recommendation. A passing claim checker is not a substitute for this pass.

### Priority 4 — Compress and rebalance by section

In ranked order:

1. **Introduction/findings:** replace the eight-item results catalogue with three central findings and a clear contribution statement. Move model-family exceptions, position diagnostics and interface observations to their results sections.
2. **Discussion/Conclusion:** cut repeated numerical summaries. Move most of the six-step practitioner checklist and standards recommendations to the handbook or appendix. End on controlled selection effects, regime dependence and the bounded attribution finding.
3. **Section 5.2 and robustness appendices:** retain the main replication summary and longer-page result; move detailed model availability, cost/quota history, small-model comparisons, decoding details and secondary absorption diagnostics out of the main narrative.
4. **Study 1/Background:** retain the component-separated obstacle result, denominator caveats and training-versus-search distinction. Move exhaustive token/operator, sector and standards details to appendices where possible.
5. **Section 3:** shorten the chain-rule framework and call it a conceptual decomposition, not a separately validated model.
6. **Interface audit and Appendix E:** keep the interface snapshot supplementary and proportionate to its design; replace sprawling chronology prose with a compact stage/deviation table while preserving the detailed repository record.

Aim to remove roughly 15–20% of main-text exposition, not to delete essential design limitations or numerical audit trails. I am not asserting a current IP&M page-limit rule.

### Priority 5 — Add semantic evidence only if it is methodologically ready

A feasible, honestly frozen exploratory recommendation study is the highest-value optional addition. Report discordance with mention effects if it occurs. Do not add another model cohort or a broad new production experiment merely to make the submission larger; neither is the shortest route to a stronger version of this paper.

## 8. Bottom line

The third version is a real improvement: **the attribution result survives independent regeneration and raw-response rescoring, and the complete test and claim-check suites pass**. The new experiment earns its place in the paper, but supports a narrower conclusion than a general ranking of wording versus provenance.

I would keep this as one paper, centre the controlled selection and task-regime results, retain Study 1 as a bounded descriptive contribution, and submit only after the focused chronology, gate, wording and compression pass. **6.5/10 is justified; acceptance readiness is not yet justified.** The recommendation study is optional for that narrower paper, but its current holdout cannot satisfy the frozen gate and must not be presented as if only human agreement remains to be obtained.
