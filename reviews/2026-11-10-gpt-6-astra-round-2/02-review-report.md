# GPT-6 Astra's second referee and strategy report (10 November 2026)

- Reviewer: GPT-6 Astra (OpenAI), reasoning level Extra high, run as an agent thread in the author's own Hoplite
  workspace (thread `thr_1e8d3bd617294e43b459e36bdbfc8e2c`; 72 tool calls; about $9.24 of the plan's included usage).
  It is a new account, so Astra had no memory of the first round.
- Reviewed: the current, unpublished version (46 pages), uploaded into its sandbox over the public commit `d2bfbf2`
  (archive SHA-256 dcd2cd74...6a1f, checked on both sides). No API keys; no commits, pushes or pull requests.
- Brief: [01-brief.md](01-brief.md), exactly as sent.
- Copied byte for byte from `/tmp/astra_review_round2.md` in Astra's sandbox (SHA-256 0ba92264...a630). Astra's final
  chat message carried the same report with minor formatting differences.
- These are suggestions. What was done with each one will be recorded in [README.md](README.md).

---

# Independent second-round referee and strategy report

**Manuscript:** *Crawler Access and Content Effects in Answer Engine Optimization: A Website Audit and Controlled Experiments*  
**Version reviewed:** Current uploaded 46-page PDF and accompanying code/data, reconstructed over commit `d2bfbf2`; 10 November 2026. Page references below are PDF pages.  
**Target:** *Information Processing & Management* (IP&M); proposed preprint category `cs.IR`.

## 1. Verdict and submission strategy

**The revision is materially better, but I would still recommend major revision rather than acceptance. My overall assessment is 6/10: a credible, unusually reproducible empirical benchmark whose interpretation and outcome validation remain weaker than its implementation.** I would not submit this exact version to IP&M before one focused validation-and-framing pass.

The earlier report's most damaging statistical objection has been addressed: the corrected position test no longer supports H5. The paper also now distinguishes potential access obstacles from demonstrated exclusion, labels first mention honestly, acknowledges compound interventions, and separates searchable-corpus effects from claims about retrieval mediation. These are substantive repairs, not cosmetic disclaimers.

The remaining acceptance risk is **what the paper establishes beyond a large collection of synthetic brand-mention effects**. A citation package supplies favourable information; a guide recommendation explicitly tells the model which product to prefer. Finding that these change answers is credible, but not by itself a strong account of provenance, information quality, or production-engine optimisation. Human-supported recommendation measurement and one tightly controlled attribution experiment would add more than another model cohort.

### Fit and odds

The topic fits IP&M's information-retrieval, information-use and evaluation remit; the [publisher's journal description](https://shop.elsevier.com/journals/information-processing-and-management/0306-4573) supports that broad fit. The strongest positioning is **measurement and evaluation of information access and answer selection**, not a practitioner recipe for increasing brand exposure. `cs.IR` is a sensible preprint category, although category assignment is not guaranteed.

My subjective editorial estimates—not journal statistics or calibrated predictions—are:

| Submission state | Desk-rejection risk | Eventual acceptance at IP&M |
|---|---:|---:|
| Current manuscript, followed by ordinary revision opportunities | Approximately 35–50% | Approximately 15–25% |
| Focused revision with defensible outcome checking, sharper contribution, and an informative matched attribution study | Approximately 20–35% | Approximately 25–40% |

Conditional on the current version reaching reviewers, **rejection or major revision** is much more likely than minor revision. These ranges reflect uncertainty about novelty thresholds, reviewer selection and editorial priorities; they are not promises that adding experiments buys acceptance. An inconclusive but well-designed follow-up can improve credibility without producing a stronger substantive result.

I would keep one paper rather than split it now, but make Study 1 a carefully bounded measurement contribution and Study 2 the inferential centre. The chain-rule decomposition connects the questions conceptually; it does not empirically connect the two datasets or establish a causal access-to-visibility model. Forty-six pages are not automatically disqualifying, especially with substantial appendices, but the competing narratives increase editorial risk. I did not verify an exact current journal length limit or submission-format requirement.

## 2. What I verified—and what verification does not establish

I checked the current PDF, earlier referee report, code audit, revision records and supporting implementation. The uploaded archive matched the supplied SHA-256. All work remained under `/tmp`; no model APIs were called, and no commit, push or pull request was made.

The offline Study 2 rebuild completed with `analyze_all.sh --no-pdf`. A separate current run of `paper/check_claims.py` passed **162/162 checks**, and the test suite passed **68/68 tests**. I did not rebuild the PDF in this second review or rerun live website measurements. Passing these checks establishes consistency with implemented definitions, not construct validity or independent confirmation of every prose assertion.

| Claim or quantity | Check and assessment |
|---|---|
| **35.0% potential obstacles; 19.0% without research-client edge refusals** | Derived site records contain 199/569 and 108/569 respectively. The arithmetic checks. Neither is measured exclusion from answers. |
| **JavaScript dependence** | There are 30 flagged sites among 269 measured homepages, with 300 of 569 unmeasured. The missing-JS sensitivity scenario gives 352/569 = 61.9% for the composite; it is not an upper bound on actual exclusion. |
| **Main experiment size** | 16,200 successful answers: 12 models × 90 trials × 15 conditions, including baseline. No duplicate model/trial/condition keys in the checked data. |
| **Mention measurement** | Independent case-insensitive whole-word rescoring matched the stored main and replication mention flags. This checks implementation of the literal-name outcome, not whether a mention is favourable. |
| **Main pooled effects** | Baseline 51.0%; endorsement 88.4%, citations 72.1%, statistics 64.7%. Independently formed paired effects reproduce **+37.4, +21.1 and +13.7 percentage points**. |
| **Other important effects** | Keyword stuffing **+12.4**, source-embedded instruction **+28.3**, combined package **+23.6**, boilerplate placebo **+1.8** points. The current estimates are preserved. |
| **Additional-model replication** | 14,849 successful answers across 11 models, with one missing filler answer. Baseline 61.0%; endorsement +30.5, citations +18.2, statistics +11.8 points. Missingness should remain explicit. |
| **H5** | The corrected code moves position assignments jointly across models within scenarios. The reported pooled **p = 0.411** supports “not supported,” not “position does not matter.” The earlier p = 0.0001 was not valid evidence for H5. |
| **Endorsement versus a simple mention in the guide** | Existing exploratory answers give approximately **+20.3** points for guide mention versus baseline and **+17.1** additional points for exclusive recommendation versus guide mention. This is useful decomposition, but not identification of provenance. |
| **Endorsement versus single on-page edits** | My additional paired check found endorsement above each of the ten ordinary single-edit conditions. Against citations, the difference was +16.3 points, with an exploratory scenario-bootstrap interval of approximately [12.6, 20.1]. This supports the pooled ranking, not an “every model, every edit” claim. |
| **Placebo length** | The generated checks confirm a median addition of 32 words, versus single-edit medians of 8–44 and 149 for the combined package. Being inside that range does not make the placebo individually length-matched. |

The search-task results and fixed-query replay are reproducible within the supplied analysis. They do not establish that a production retriever behaves similarly or that retrieval alone caused the difference between task regimes.

## 3. Comparison with the earlier referee report

| Earlier objection | Current assessment |
|---|---|
| Access obstacles presented as a discoverability/exclusion rate; numerical access-remediation payoff comparison | **Substantially repaired.** The abstract and §3 now make the distinction, and the unsupported remediation comparison is gone. A few stronger phrases remain in the discussion. |
| Shared-trial dependence broken in the position test | **Repaired.** The correction changes the conclusion and is disclosed in Appendix E. This deserves credit. |
| Nonsignificance treated as support for the small-model H3 null | **Repaired.** The current verdict logic uses “inconclusive” rather than treating failure to reject as support. |
| “Top pick” actually means first mention | **Terminology repaired; substantive outcome gap remains.** There is still no independently validated favourable-recommendation outcome. |
| Bundled information, provenance, repetition and length | **Acknowledged, not experimentally resolved.** Appendix H helps with endorsement strength, but the provenance question remains open. |
| Search comparison presented as retrieval mediation | **Largely repaired.** The task-regime distinction, process outcomes and retriever sensitivity analyses are useful. Do not demand mediation evidence for the valid within-task treatment effects. |
| Sampling, JavaScript missingness and model weighting | **Much better documented.** Rank-band retention, sensitivity scenarios, absolute rates and developer-weighting checks improve transparency; they do not recover missing observations or make the samples representative. |
| Model judges treated as validation of absorption | **Better qualified, still weak.** Unconditional rates and explicit limitations help, but no reliable independent human check has been completed. |
| Consumer-interface observations overinterpreted | **Partly repaired.** The detailed audit is appropriately cautious; some introductory and concluding language still runs ahead of interface observability. |

The current paper should not be reviewed as if none of these changes happened. Conversely, accepting a limitation in prose does not resolve it when the same limitation undermines the central explanation.

## 4. Major concerns

### 4.1 The practical interpretation outruns the measured outcome

**Where:** Outcomes, pp. 10–11; Table 4, p. 14; absorption, pp. 15–16 and 39–41; discussion and conclusion, pp. 20–23.

Literal brand mention is a legitimate, reproducible visibility measure. The problem is not that regex measurement is inherently unacceptable. The problem is moving from “named” to “recommended,” “selected as a good option,” or “useful information was incorporated.” A warning, rejected option and favourable recommendation can all increase the primary outcome. First mention does not solve this.

This is **acceptance-threatening for the practical AEO interpretation**, but not fatal to a narrowly framed mention benchmark. Add recommendation coding on existing answers, with modest human checking, or narrow the paper's claims further. Keep faithful transmission separate: detecting a source name or number does not establish correct attribution, support, or truth.

Table 12 is especially important. The judges label 35–40% of quotation-baseline answers positive despite those answers not receiving the added quotation. Those rates undermine any simple “the judges validate absorption” story. For generic overlapping content, baseline positivity also need not be a pure annotation error: it can reveal that the definition does not identify transmission of newly supplied information. Two judges agreeing at κ = 0.84 does not eliminate shared mistakes.

### 4.2 The strongest treatment is not yet a provenance result

**Where:** Table 3, p. 10; §5.1, pp. 13–15; Appendix H, p. 39; discussion, p. 20.

The third-party package adds another target occurrence, changes which document carries information, and supplies an explicit favourable recommendation. Citation and statistics packages also add favourable product claims. The experiment therefore identifies effects of **particular information packages**, not the independent value of citations, truth, third-party origin or formatting.

The guide-mention follow-up is valuable: it shows that merely adding coverage accounts for substantial movement and exclusive endorsement adds more. It does not compare equivalent information attributed to the brand versus an outside evaluator. This is the highest-value new experimental gap because closing it could turn a descriptive ranking into an interpretable contribution.

Do not describe artificial guide insertion as real-world “earned media” without qualification. Nor can the experiment show that models reward reliable evidence: the evidence-looking claims are synthetic and their truth is not independently tested.

### 4.3 Study 1 is a bounded measurement audit, not an estimate of usable access

**Where:** §§4.1–4.2, pp. 5–9; discussion, pp. 19–20; limitations, pp. 22–23; Appendix L, pp. 44–45.

The revised treatment of purposive sampling and missingness is appropriate. Important unresolved limitations are structural: a research client is not a verified crawler; homepage word counts are not task-relevant information availability; JavaScript coverage is incomplete; and Tranco retention excludes unreachable robots files without recoverable per-domain exclusion reasons.

One remaining phrase needs correction: calling the research-client edge-refusal rate an **“upper-bound proxy”** for verified-agent refusal is not justified without an ordering assumption. A site might allow this research client but block a verified crawler, or do the reverse. Call it a **client-specific observation**, not a bound.

The hidden-text parser repair also does not retroactively repair saved crawl measurements. Do not imply that passing new parser tests revalidates the measured JavaScript prevalence. A new crawl would be a new dated measurement, not silent correction of the old snapshot.

These issues are manageable if the audit remains a clearly scoped dataset contribution. They become fatal to claims that fixing access causes a specified visibility gain or outperforms content editing.

### 4.4 The search task is useful but does not identify the mechanism behind attenuation

**Where:** §5.3, pp. 18–19; Appendix J, pp. 41–42; Table 19, p. 46.

The within-task randomised comparisons are meaningful. The cross-task contrast also changes competition, source presentation, snippets, tool choices and budgets. Baseline mention rates of 53% versus 22% cannot be assigned to retrieval alone. Opening is post-treatment and selected, so opening/mention associations are not causal effects of opening.

The new BM25/embedding/fused replay and exclusion of MAI-Thinking-1 are worthwhile robustness checks, not redundant analysis. Their scope should remain explicit: baseline-query replay fixes queries that would themselves sometimes change under treatment, and the tested retriever's design makes query-matching additions particularly consequential.

A matched-pool context-delivery experiment would strengthen the mechanism claim, but is not mandatory if the paper consistently claims a **task-regime contrast** instead.

### 4.5 Reproducibility is stronger than the unifying research contribution

**Where:** Introduction, pp. 1–3; framework, pp. 4–5; discussion and conclusion, pp. 19–23.

The research questions improve organisation, but the paper still contains a website audit, intervention benchmark, several model replications, absorption study, interface audit, retrieval experiment and practitioner guidance. They are related, but not all provide evidence for one explanation.

Lead with a contribution about **how information packages affect observable answer outcomes under different access and delivery conditions**. Treat the crawler audit as context and measurement, not causal corroboration of Study 2. Move transient model-procurement details and most practitioner prescriptions to the supplement. The consumer-interface snapshot should not carry a headline equal to the controlled experiment.

None of these concerns requires discarding the dataset. The acceptance-threatening combination is broad claims plus uncertain outcomes plus an unresolved mechanism—not a demonstrated collapse of the main treatment arithmetic.

## 5. Minor and targeted corrections

1. **p. 3:** “The most used assistant showed no retrieval in our audit” should become “No visible text-search activity or source citations were observed in these 26 sessions.” The detailed p. 18 account already explains why stronger inference is unavailable.
2. **p. 20:** Blocking a training crawler does not establish that the organisation's pages are absent from all future training data. Describe restriction of that documented collection route, not comprehensive control over training provenance.
3. **pp. 2 and 20:** “Best edit” needs its comparison class. Citations are the strongest ordinary single on-page package, but the combined package and source-embedded instruction have larger pooled mention effects.
4. **p. 6:** “Configuration errors” should not automatically include deliberate wildcard policies. Distinguish documented parser/token problems from policies whose intent is unknown.
5. **p. 11:** Interval-derived “power” is better described as an approximate detectable-effect calculation. A nonsignificant model-level test does not, by itself, “rule out” effects; the interval does the limiting. State whether calculations are unadjusted or account for the testing family.
6. **pp. 10 and 45:** Keep “approximately comparable in added length,” not “length controlled.” Regression adjustment for observed length would not identify an isolated length effect when length is bundled with treatment content.
7. **pp. 11, 34–36:** Preserve the distinction between pre-specified hypotheses, exploratory outcomes and later follow-ups. A newly frozen annotation protocol does not retroactively make recommendation an original confirmatory outcome.
8. Keep the current distinction between nominal confidence intervals and Holm-adjusted tests. Readers should not mistake an interval excluding zero for a corrected discovery.
9. Reduce repetition across abstract, introductory findings, discussion and conclusion. Removing the consumer snapshot from the abstract would create space for the actual outcome and design limitations without adding another caveat paragraph.
10. Apply attribution research operationally: [ALCE](https://aclanthology.org/2023.emnlp-main.398/) separates citation-related evaluation dimensions, and [AIS](https://aclanthology.org/2023.cl-4.2/) offers a basis for human attribution assessment. Merely adding references is not a substitute for defining what a positive label means.

## 6. Ranked improvements by resource type

Effort estimates below are planning judgments, not measured completion times. Dollar costs for new model work are discussed separately.

### A. Text-only changes

| Rank | Change | Referee benefit | Effort | Downside or risk |
|---|---|---|---|---|
| 1 | Align every headline with literal mentions, potential obstacles and task-regime contrasts | Very high; removes easy rejection arguments | Several focused hours | Less sweeping practical story |
| 2 | Make one evaluation contribution central; shorten interface and practitioner narratives | High; improves novelty and journal fit | About half a day | Some appealing descriptive findings move out of the main text |
| 3 | Repair the residual claims listed above, especially edge “bounds” and invisible retrieval | High relative to effort | A few hours | None beyond narrower claims |
| 4 | Explain the relationship to GEO, attribution and retrieval evaluation through constructs and estimands | Moderate–high | Half a day | More literature does not create missing identification |

### B. Existing-data analysis, no new model calls

| Rank | Change | Referee benefit | Effort | Downside or risk |
|---|---|---|---|---|
| 1 | Assemble a frozen answer/annotation manifest with paired keys, target names, queries, model IDs and condition mappings kept separately | Essential foundation for valid outcome checking | Half a day | Care is needed not to leak conditions to raters |
| 2 | Analyse current scenario-level contrast variability for the follow-up; specify estimands and multiplicity before spending | High; prevents underpowered mechanistic claims | A few hours; initial calculations supplied below | Existing packages may mispredict variance of new contrasts |
| 3 | Put unconditional mention, first-mention and process rates in one compact main-text summary | Moderate–high; makes outcome distinctions visible | Several hours using existing outputs | Avoid implying a causal funnel from conditional rates |
| 4 | Summarise robustness already completed rather than adding more variations | Moderate; makes the main result defensible without analytical sprawl | A few hours | Do not turn robustness selection into a search for favourable results |

### C. New computational experiments or annotations

| Rank | Change | Referee benefit | Effort/cost | Downside or risk |
|---|---|---|---|---|
| 1 | Recommendation coding on existing answers, **conditional on a usable rubric and human pilot** | Highest direct repair of the substantive outcome gap | 12,960 judge decisions for the proposed six-arm corpus; historical cost proxy about $5.75 | Shared judge bias; more labels do not create ground truth |
| 2 | Matched attribution × endorsement experiment | Highest new identification value | Five-arm core: 5,400 generated answers; historical proxy about $7.13 | Small attribution effects or interactions may remain unresolved |
| 3 | Matched-pool context-delivery/search experiment | High for a retrieval-mechanism paper | A separate design and new tool/model runs | Easily expands into a second paper; not necessary for the narrowed current claim |
| 4 | Re-measure access/JavaScript or add more consumer-interface sessions | Moderate for the audit, lower for Study 2 acceptance | New dated crawl or substantial manual collection | Still does not establish remediation effects or backend retrieval |

More API models, another temperature sweep, and more unblinded judge labels are low priorities.

### D. Human effort

| Rank | Task | Referee benefit | Effort | Downside or risk |
|---|---|---|---|---|
| 1 | Check a small blinded recommendation sample with answer-span evidence and an uncertainty option | High; tests whether the substantive rubric is usable | Approximately the available one hour | Precision and independence remain limited |
| 2 | Use author time to design examples, preserve blinding, and analyse disagreements without rewriting held-out labels | High; reduces avoidable annotation failures | Separate from the rater's hour | Author adjudication is not independent validation |
| 3 | Obtain a genuinely second rater later, if possible | High for stronger reliability claims | Additional unavailable human time | Cannot be replaced by calling a model a “second human” |
| 4 | Human assessment of faithful claim transmission | Useful but lower priority than recommendation here | A separate source-reading task | Trying to add it to the same hour will damage both tasks |

## 7. Claude's proposal 1: provenance follow-up

### Assessment

Adding `self_endorsement` and `quoted_endorsement` is directionally right, but three contrasts among those conditions and the old third-party treatment do not cleanly identify all of endorsement, attribution, repetition, placement and independent-document exposure. A quotation can change attribution, wording and salience simultaneously. Reusing old controls also leaves model/service drift mixed into the comparison.

**Do not run just two new arms and interpret differences from historical answers as pure provenance effects.** The existing responses are excellent for planning, but all primary contrasts need contemporaneous paired conditions.

### Recommended five-arm core

Fix the page carrying the added material to the target's own page. Use a standardised statement block with the same placement, target-name count, underlying product facts and approximately equal token length. Cross **stated source attribution** with **recommendation stance**:

| Arm | Stated source | Statement |
|---|---|---|
| B | None added | Original baseline page |
| S0 | Brand/first party | Neutral statement that the target is among the options considered for the query |
| S1 | Brand/first party | Matched statement explicitly recommending the target |
| Q0 | Named external evaluator | The same neutral content attributed to that evaluator |
| Q1 | Named external evaluator | The same recommendation attributed to that evaluator |

Use neutral source names and matched descriptors; do not make the external source sound more expert or prestigious in unrelated ways. Avoid new scores, customer counts or factual superiority claims. Hold the other pages fixed. Counterbalance source order across trials and use at least two fixed wording templates assigned across scenarios, with each trial's template shared by its arms. Check lengths and name counts mechanically before generation.

This design identifies the effect of an **external-attribution cue in supplied synthetic text**. It does not authenticate provenance or test whether an evaluator is genuinely independent.

Pre-specify three primary contrasts:

1. **S1 − S0:** effect of explicit recommendation under first-party attribution.
2. **Q1 − S1:** effect of external attribution with recommendation content held fixed.
3. **(Q1 − Q0) − (S1 − S0):** whether attribution changes the effect of recommendation language.

B provides a fresh anchor and helps describe the effect of the added statement block. Those anchor comparisons should be secondary, rather than an expanding family of unplanned headline tests.

**Optional seven-arm extension:** add matched neutral and recommending statements on the independent guide, T0 and T1. Then `(T1 − T0) − (Q1 − Q0)` addresses whether endorsement operates differently when carried by the guide rather than quoted on the brand page. It remains a document-location/source-context contrast, not pure institutional trust. Pre-specify it as secondary or enlarge the correction family; do not keep the three-test power calculation while adding a fourth primary test.

### Size, inference and power

Use the original **30 scenarios × 3 paired trials × 12 models**: 5,400 calls for five arms, or 7,560 for seven. Randomise condition execution order within blocks, run blocks within a short dated window, use fresh conversations, and preserve the scenario/trial alignment across models. Record exact model versions, failures, retries and settings. Resample scenarios jointly across models; weight the fixed models equally, with developer weighting as sensitivity. Use scenario-level sign flips and Holm correction for the declared three-contrast family.

There are **30 scenario clusters**, not 1,080 independent examples per arm. From saved answers, I calculated scenario-level standard errors of approximately:

- 1.58 points for exclusive guide endorsement minus guide mention;
- 1.93 points for endorsement minus citations;
- 2.37 points for endorsement minus baseline.

These are planning proxies, not estimates for the unobserved attribution manipulation. Using a conservative Bonferroni approximation to the three-test family, two-sided 5% familywise error and 80% power gives:

| Assumed SE of a new direct contrast | Approximate 80%-power detectable effect | Approximate power for 5 points | Approximate power for 8 points |
|---|---:|---:|---:|
| 2.0 points | 6.5 points | 54% | 95% |
| 2.5 points | 8.1 points | 35% | 79% |
| 3.0 points | 9.7 points | 23% | 61% |

These are normal-approximation calculations; a small-sample t-critical-value sensitivity raises the first two detectable effects to about 6.8 and 8.5 points. They are not simulated power guarantees for the sign-flip procedure. Interactions can be noisier: if two component contrasts each have SE 2–2.5 points and are uncorrelated, their difference has SE about 2.8–3.5 points. Their actual covariance must be estimated, not assumed away.

Under stable variance and square-root scaling, detecting 5 points at 80% power would require roughly **55–86 scenarios** for those first two SE assumptions, rather than 30. This is an extrapolation, not a sample-size certification. More distinct scenarios generally address scenario uncertainty better than merely adding repeated calls to the same 30.

**Decision rule:** treat a corrected positive direct contrast as evidence for the specified attribution cue. If the contrast is not significant, report its interval; do not conclude “provenance does not matter.” If a ±5-point equivalence claim is desired, pre-specify an equivalence procedure and its multiplicity handling; this small design may not resolve it. Keep interaction conclusions appropriately tentative.

### Costs and reporting

The saved main baseline/endorsement logs imply approximately **$1.43 per 1,080-answer arm**: about **$7.13 for five arms** or **$9.98 for seven**, before pilot calls, retries or price changes. These are historical logger-based proxies, not current provider quotes or bills. Longer prompts, reasoning behaviour and endpoint changes can invalidate them.

Suggested eventual wording:

> In a contemporaneous matched-content experiment, externally attributing the recommendation changed the probability of a target mention by X points [interval], relative to first-party attribution. The manipulation changed stated attribution, not verified source independence or truth.

## 8. Claude's proposal 2: recommendation coding of 6,480 answers

### Assessment

This is the most direct substantive upgrade because it reuses expensive generation and tests whether visibility gains are favourable. However, **two model judges are not two independent ground-truth raters**, and adjudicating all disagreements with a third model would not solve that problem.

For the six-condition set I checked—baseline, third-party endorsement, citations, statistics, filler and injection—there are 6,480 answers, averaging about **131 words**, of which 4,411 contain the exact target name. If the claim is to reinterpret the paper's keyword-stuffing result as well, include that condition explicitly: seven conditions would be **7,560 answers**. Do not generalise recommendation findings to unlabelled treatments or the separate 11-model replication cohort.

### Better protocol

Give each judge only the user query, target name and full answer. Hide generator identity, treatment, existing detector results and the other judge's labels. Treat any instructions quoted inside answers as data. Do not provide the source page for this task: that would encourage judges to assess the product instead of the answer's recommendation.

Use a compact codebook with separate fields:

- **Named:** target identified in the answer.
- **Recommended:** answer presents the target as an option the user should consider or choose, including an explicit conditional recommendation.
- **Preferred:** answer explicitly ranks or chooses it above alternatives; first appearance alone does not count.
- **Negative/warning:** answer rejects it, warns against it, or only identifies it in a warning about manipulation.
- **Uncertain:** insufficient context or genuinely ambiguous wording.

Allow recommendation and warning to coexist when the answer genuinely contains both. Require a short verbatim answer span for positive recommendation/preference and warning labels. Validate that the span exists; this catches malformed evidence, not semantic errors. “Accurate claim transmission” must remain a different task requiring source material.

Run a small balanced development pilot, fix the rubric, then freeze prompts, judge versions, parsing and analysis before full labelling. Keep human held-out items out of prompt development. Choose a primary judge by the documented pilot procedure, not by which produces larger treatment effects; report the second judge as sensitivity, with both label files preserved. Report family/self-evaluation sensitivities where the judge shares a developer with the generator.

### Analysis and decision rules

The primary new outcome should be the **unconditional probability of favourable recommendation over all valid answers**. Preserve the within-trial treatment–baseline pairing and scenario clustering. Do not condition the main analysis on being named: treatment affects membership of that set. Conditional conversion rates can be descriptive supplements.

For five treatments versus baseline, correct the five primary recommendation contrasts together. Preferred-option and warning outcomes should be declared secondary with an explicit multiplicity policy. Report uncertain labels and sensitivity bounds rather than silently coercing them to NO. Include per-judge estimates, confusion summaries against human judgments, disagreement rates by treatment and examples of consequential errors.

A pragmatic progression gate would be at least 90% agreement with the held-out human **binary recommendation** judgments in the probability sample, no recurring warning-as-recommendation error, and no unresolved systematic coding failure. This is a workflow threshold, not proof of validity; the sample is far too small to certify accuracy. If it fails, revise on development examples and obtain fresh checking, or keep the outcome exploratory. Never silently relabel the holdout until the threshold is reached.

A cross-judge sign reversal in a treatment effect is an important uncertainty to disclose, not a reason to select the more favourable judge. If mention gains remain but recommendation gains do not, that is a valuable result and should narrow the paper's practical conclusion.

### Size, precision and cost

The full proposal requires **12,960 judge decisions**. It creates no new independent generated answers and does not turn 30 scenarios into thousands of independent experimental units. Recommendation-specific power cannot be inferred from the mention effects: discordance and annotation errors determine it. Estimate scenario-level variance after the frozen pilot, using blinded outcome summaries where possible, and report achievable precision rather than promising 80% power.

Existing absorption-judge logs record about $0.38 and $0.48 for 960 decisions each. Scaling that historical rate gives approximately **$5.75 for two judges on 6,480 answers**, or **$6.71 on 7,560**. A 1,200-answer dual-judge stage would be approximately $1.07. Different prompts and output schemas require a fresh token-cost estimate.

At the user-supplied free-tier limit of approximately 500 requests/day, one judge making one request per answer would need at least **13 quota-days for 6,480 answers**; two such passes sharing that quota need about 26. Retries and other usage increase this. Batching can reduce requests but introduces order/format risks and does not eliminate token limits. Free tier is a scheduling option, not a free instantaneous substitute.

Suggested wording:

> In a post-hoc outcome analysis with a frozen coding protocol, two model judges estimated recommendation effects of X and Y. A small blinded single-rater check assessed rubric usability and observed agreement; it did not establish independent gold-standard accuracy.

## 9. Claude's proposal 3: a blind human check of 150 answers

### Assessment

The idea is necessary; the stated capacity is not sufficient for the ambitious version. At 131 words per answer, 150 answers already mean roughly **19,700 answer words**, or 328 words/minute for an hour before instructions, source reading or annotation. Faithful-transmission assessment adds further text and comparison work.

The repository's human-check code records earlier unusable annotation attempts. The new sheet also contains instructions effectively favouring NO under doubt and implying that baseline exposure determines the correct answer. Those are warning signs for the measurement task, not evidence of rater incompetence. A baseline answer can coincidentally express overlapping information; the annotator must judge the answer against a precise criterion, not infer the desired label from exposure.

**Do not call one non-expert's 150 rushed labels an independent gold standard, and do not try to validate mentions, recommendation, preference and absorption all in the same hour.** Prioritise literal identification and favourable recommendation. Keep the absorption claim descriptive for now.

### Feasible replacement

Budget the hour approximately as follows, stopping rather than rushing if the rate is slower:

- **10 minutes:** instructions and six practice examples, with feedback; exclude these from evaluation.
- **50 minutes:** target 60 unique evaluation answers plus six unobtrusive repeat presentations, approximately 45 seconds per presentation.
- Within the 60 unique answers, use **48 probability-sampled items** balanced across the six conditions and 12 models, plus **12 deliberately selected challenge items** covering warning-only mentions, rejected options, conditional recommendations and judge disagreement.

The 48-item probability panel can have eight items per condition and four per model through a balanced allocation. Use random selection within the declared cells and retain selection probabilities. The challenge set is diagnostic, not representative; report it separately. Repeat presentations measure limited **within-rater consistency**, not inter-rater reliability, and are not additional independent observations.

Hide condition and model labels, judge predictions and detector flags. Supply the query, target and answer; randomise order. Allow uncertainty. Ask for a brief evidence span when recommendation is marked positive. Do not require the rater to infer truth or read source passages in this particular hour.

If the author later reviews disputes, preserve the initial labels and describe author adjudication separately. Do not count that as a second independent rater. If this is the same person involved in earlier attempts, use fresh items and disclose their prior task familiarity rather than claiming complete independence.

### What this can establish

Report agreement and errors on the probability panel, challenge-set failures, completion time, uncertain cases and repeat consistency. Do not present accuracy with a tiny denominator as a stable model-wide property. Under a simplifying independent-binomial calculation, **zero errors in 48 items still permits an approximately 6.1% error rate at the one-sided 95% upper limit**; even 150 flawless items would only lower that figure to about 2.0%. Stratification, clustering and an imperfect human reference add further uncertainty.

The decision rule is operational: recurrent misunderstanding or warning-as-recommendation errors stop claims of validated recommendation measurement. Isolated disagreement requires transparent reporting and sensitivity analysis, not automatic discarding of the human label.

Suggested wording:

> One non-expert rater completed a blinded feasibility and agreement check on a small stratified sample, with additional diagnostic cases. This check assessed the annotation protocol and obvious failure modes; it did not measure inter-rater reliability or establish a gold standard.

## 10. Recommended execution order and budget discipline

**Do not run all three proposals at full scale immediately.** Use the following order:

1. **Locally, without APIs:** make the text corrections; freeze the answer manifest, coding rubric, sampling plan, statistical contrasts and machine-readable experiment specification. Existing-data checks, cost arithmetic, offline analysis code and annotation-sheet generation can all be prepared in this sandbox. This review itself did not implement those future study files.
2. **On the author's machine:** Claude runs a small judge-development pilot for rubric usability, schema, cost and timing. Freeze the judge configuration, then obtain labels for fresh held-out candidates without tuning on them; these can supply disagreement cases for the human check.
3. **Human stage, then scaled coding:** run the small recommendation feasibility check before committing to mass judge coding. Separate development items from held-out items. If the progression gate passes, Claude completes the remaining coding on the author's machine. No new answer generation is needed for this stage.
4. **On the author's machine:** run the five-arm attribution core with fresh controls and strict provider-specific spending caps. Add the two guide arms only if they address a retained claim and the measured budget permits them.
5. **Locally after transferring results:** analyse paired outcomes, uncertainty and judge sensitivity; update only conclusions supported by the new results; rebuild and rerun all claims/tests. Preserve old and new outcomes rather than replacing the original pre-specified endpoint silently.

The user-supplied approximate balances—AWS $13, Azure $43 and OpenAI $7.50—are **provider-specific estimates, not a fungible $63.50 budget or verified current balances**. At historical rates, the five-arm generation core plus both full Bedrock judge passes would total about **$12.88 before any contingency**, already too close to the stated AWS amount. The seven-arm version plus judging would be about $15.73. Do not launch both against a $13 AWS ceiling on that basis.

Reserve headroom for retries and pilot work, check current endpoint prices and available credit on the author's machine, and place judge work on another authorised provider only after verifying its price and cap. Otherwise use a staged judge sample or the five-arm rather than seven-arm generation design. An approximately 20% contingency is a planning allowance, not a guarantee that costs cannot exceed it. Preserve complete paired blocks when enforcing caps; never stop selectively according to observed effects.

**Bottom line:** the corrected paper is a defensible empirical foundation, not yet a strong general theory or practical validation of AEO. The best next revision should establish what the answers actually recommend, isolate one source-attribution effect under matched content, and remove the few remaining claims that exceed observability. That is a more credible route to IP&M than increasing model count or accumulating more automated agreement statistics.
