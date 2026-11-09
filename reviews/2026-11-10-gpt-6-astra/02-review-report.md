# GPT-6 Astra's referee review (10 November 2026)

- Reviewer: GPT-6 Astra (OpenAI), reasoning level Medium, run as an agent thread on the Hoplite platform
  (thread `thr_2470761b4745439d9adfd3024763ed4b`; it worked for about 6 minutes and made 34 tool calls).
- Reviewed: `paper/main.pdf` at commit `d2bfbf2` (40 pages), with read access to the public repository.
- Brief: [01-review-brief.md](01-review-brief.md).
- Copied verbatim from the thread's final message. The text was taken from the rendered page and converted back to
  Markdown, so emphasis and lists may differ slightly from the original; the words are unchanged.
- These are suggestions. What was done with each one is recorded in [README.md](README.md).

---

# Referee report

*Reviewed the 40-page PDF at commit `d2bfbf2`, with targeted checks of the supporting code and data. Page numbers below refer to the PDF. No repository files were changed, and no language-model APIs were called.*

## 1. Verdict

**Major revision**, with a substantial risk of rejection if submitted with the present framing.

Three issues would drive that recommendation:

1. **The headline “discoverability gap” is not directly measured.** The website audit measures potential obstacles to particular access routes, not exclusion from answers. The paper’s own Perplexity audit demonstrates the distinction.
2. **The experiments identify effects of compound interventions in synthetic environments, not general returns to AEO techniques.** Evidence, endorsement, length, repetition, placement and retrieval exposure are not fully separated.
3. **Some inference and outcome labels are stronger than their implementations warrant.** The position test breaks the shared-trial dependence structure; “top pick” means first mention; and several nonsignificant results become claims of no effect.

The cheapest viable revision is a narrower measurement-and-benchmark paper, not an attempt to establish that fixing access generally outperforms content optimisation.

## 2. Major concerns

### 2.1 Potential barriers are treated as demonstrated exclusion

**Where:** §§3–4, pp. 4–8; §6, pp. 18–19; conclusion, pp. 21–22.

**Problem:** Study 1 does not estimate how often (A_e=0). A research-client refusal does not establish refusal of a verified crawler; losing half the rendered words does not establish loss of relevant information; and disallowing one crawler does not exclude partner indexes, cached material or user-triggered fetches. The composite also combines barriers affecting different engines.

Equation (1) should use conditional probabilities along a defined route, rather than assume stage independence. More importantly, the audit’s composite indicator is not an empirical estimate of that equation’s access probability.

**Why it matters:** The comparison on p. 18—restoring access versus content editing, including the median **2.2-times** advantage—transports synthetic selection rates to unrelated real websites without measuring retrieval probability, actual blockage or the effect of remediation.

**Cheapest fix:** Rename the audit outcome “potential first-party access obstacles”; distinguish crawler policy, observed research-client accessibility and text availability. Use a conditional-probability decomposition and remove the numerical remediation comparison and unsupported cost ranking.

**Requirements:** Existing data and text suffice for the narrower claim. Retaining causal claims about remediation requires new before/after access and visibility measurements.

### 2.2 Sampling and missingness do not support “the wider web”

**Where:** §4.1, pp. 4–5; §4.2, pp. 6–8; §7, p. 21.

**Problem:** The organisational sample is purposive. The Tranco sample selects equal numbers from four dramatically unequal rank bands, then retains 703/1,000 domains using criteria that include reachable robots.txt. Thus the aggregate is neither a simple random sample of popular websites nor representative of the wider web. Excluding unreachable robots.txt is especially consequential when unreachability is itself a headline barrier. Rendering succeeds for only 269 organisational homepages.

The code treats missing JavaScript-dependence observations as false when constructing the composite.

**Why it matters:** Wilson intervals do not account for selection bias or informative missingness. The 34.6% and 19.0% figures have mixed measurement uncertainty; neither is a straightforward population prevalence estimate.

**Cheapest fix:** Define the target population; report rank-band estimates, retention and exclusion reasons; explain any weighting; distinguish measured absence from unmeasured status; provide missingness sensitivity bounds. Describe purposive-sample intervals as conditional summaries, not population guarantees.

**Requirements:** Existing retained records and sampling logs; additional crawling only if unresolved cases must be classified.

### 2.3 “Evidence,” provenance and length are bundled

**Where:** Study 2 methods, pp. 8–10; results, pp. 11–16; Appendix D, pp. 28–30.

**Problem:** The citations treatment adds a favourable score, named evaluators, URLs and a guide listing. Statistics add favourable product information. The quotation supplies an explicit recommendation. These are not isolated tests of citation formatting, quantification or expert attribution.

The single boilerplate placebo is only approximately length-matched: the response metadata show different page lengths across conditions. It cannot establish that length is controlled for every intervention.

Third-party endorsement also combines another occurrence of the brand, another source and an explicit recommendation. Appendix H separates some endorsement strength from exposure, but not third-party provenance from equivalent first-party wording.

**Why it matters:** A model may rationally favour the newly better-described product without preferring “evidence” as a presentation technique. Synthetic, unverified claims being repeated are not evidence that models reward truth or checkability.

**Cheapest fix:** Describe these as effects of specific information packages. Promote Appendix H’s contrasts into the main argument, disclose treatment-length distributions and replace “controls for length” with a qualified statement.

**Requirements:** Existing data/text for narrower conclusions. Isolating provenance, factual improvement and formatting requires new matched-content experiments and model runs.

### 2.4 The agentic comparison does not isolate retrieval or establish mediation

**Where:** §5.3, pp. 17–18; Appendix J, p. 35; Table 15, p. 39.

**Problem:** The comparison changes six supplied pages into a searchable corpus containing twelve candidate brands per scenario, snippets, tool-use decisions and a call budget. The **53% versus 22%** baseline difference therefore combines retrieval with competition and presentation changes.

“Lost their effect because the page was seldom opened” is a causal mediation claim. Opening is a post-treatment, relevance-dependent choice, and snippets can also convey information. The reported 96% mention rate among opened pages cannot establish the effect of opening.

**Why it matters:** Retrieval bottlenecks are plausible, but the experiment does not uniquely identify them as the explanation for attenuation.

**Cheapest fix:** Call this a comparison between two task regimes. Report search compliance, snippet exposure and page opening separately. Use the existing query replay to compare BM25-only, embedding-only and fused rankings, and show a sensitivity analysis excluding the frequently non-searching model.

**Requirements:** Existing logs and cached embeddings support these analyses without model calls. Isolating retrieval requires a matched-pool experiment; identifying mediation requires additional design assumptions or interventions.

### 2.5 Position inference ignores shared experimental assignments

**Where:** Analysis description, p. 10; Table 6, p. 13; position results, p. 14; Figure 10, p. 32.

**Problem:** All models receive the same trial-level target positions. However, `position_test()` permutes positions independently within each model, breaking the dependence induced by shared scenarios and target assignments. Figure 10 explicitly treats answers as independent. The scenario-clustered treatment analysis does not have this particular problem.

Separately, H3 is labelled “Supported” for small models because positive effects are nonsignificant. The code implements exactly that rule, not an equivalence test.

**Why it matters:** The evidence supporting H5 may be overstated, and failure to reject is not evidence supporting a null prediction. The pooled/stratified discrepancy alone does not resolve either issue.

**Cheapest fix:** Reanalyse position using trial-aligned assignments across models and scenario-aware inference; replace independent-answer intervals. Mark small-model H3 inconclusive unless equivalence is demonstrated. State that pooled intervals generalise over sampled scenarios conditional on the selected models.

**Requirements:** Existing responses only.

### 2.6 Visibility, recommendation and absorption are conflated

**Where:** Outcomes, p. 9; absorption, p. 14; call-out rescoring, p. 15; Table 13, p. 38.

**Problem:** “Top pick” is the first brand named, not an annotated recommendation. Removing injection warnings fixes one failure mode but not introductory comparisons, rejected options or unordered lists.

Absorption conditions on mentioning the target, an outcome affected by treatment. Comparisons therefore concern different selected answer sets. Detectors also differ substantially: recognising a unique number or source name is easier than recognising paraphrased persuasive language. Two model judges are not a gold standard; Table 13 reports substantial baseline false positives for some judgments.

**Why it matters:** Visibility gains need not mean favourable recommendations, and differential copying need not establish superior informational value.

**Cheapest fix:** Rename the automated measure “first-mentioned brand.” Add blinded human annotation of an existing response subset for recommendation polarity, explicit preferred option and accurate claim transmission. Report unconditional absorption alongside conditional rates; stop presenting imperfect detector rates as strict lower bounds.

**Requirements:** Existing responses plus new human annotations; no model runs.

### 2.7 Product-level conclusions exceed the audit’s observability

**Where:** Abstract, p. 1; replication framing, pp. 10–11; live audit, pp. 16–17; discussion, p. 19.

**Problem:** API models from an assistant’s developer are not necessarily that assistant’s deployed models or orchestration. Usage weighting cannot repair that mismatch. The single-account, single-location audit records visible behaviour, not backend retrieval telemetry. No displayed search or citations does not conclusively establish generation solely from parametric memory.

**Why it matters:** Statements about “the most used assistant” extrapolate beyond both the sample and what the interface reveals.

**Cheapest fix:** Say “no visible text-search activity or source citations in these 26 sessions”; describe the replication as additional API models, not assistant replication. Remove product-market weighting from the principal evidence.

**Requirements:** Text changes suffice. Broader product claims need repeated audits across accounts, settings and locations; backend mechanism claims require stronger observability.

## 3. Overclaims and inconsistencies

- **“Blocking an operator’s search-index crawler removes the site from that operator’s answers”** (§2, p. 3) contradicts the Perplexity observations and explanation on pp. 16–17. Replace “removes” with a statement about a particular crawling route.
- **“The rates are lower bounds”** (§4.2, p. 7) conflicts with the admission that edge refusals are an upper-bound proxy (p. 5; Figure 3, p. 8). Missing coverage and false-positive barriers operate in opposite directions; the composite has no demonstrated one-sided bound.
- **“A side effect rather than a decision”** (§6, p. 18) infers operator intent from wildcard rules and technical behaviour. An implicit rule can be deliberate. Use “not expressed through an agent-specific rule.”
- **“If every competitor made the same edit the gains would cancel”** (p. 14), strengthened to an edit helping **“only while competitors have not made it”** (p. 20), is not established by single-target interventions. Multi-party optimisation could change answer length, selection or ranking.
- **“Sampling at temperature 1 left every conclusion in place”** (p. 16) is stronger than no corrected interaction reaching significance. Table 12 reports a citation-effect change of −6.9 points with an unadjusted interval excluding zero. Say no change survived the specified correction, not that robustness or equivalence was established.
- **“Resistance can be trained”** (§6, p. 20) asserts a training mechanism from cross-model behaviour. No training intervention was tested.
- **“More than any edit … in all 12 hosted models”** (conclusion, p. 21) is too strong: Table 9 shows third-party endorsement and the combined edit tied at +20.0 for Qwen3 Next 80B. Specify the pooled comparison and whether bundles/adversarial edits are excluded.
- **Gemini majority:** p. 16 says 32 of 64 sources were vendors’, then says third-party majority holds “only narrowly.” Half is not a majority.
- **Unlabelled denominator changes:** llms.txt prevalence is **23.6%** in Table 2 (p. 8), but **23.0%** in Table 16 (p. 40). These appear to use reachable-file versus all-site denominators; disclose them. Likewise, **+11.7** keyword points on p. 2 versus **+12.4** in Table 5 is a model-cohort change, not necessarily an error, but the introduction should identify the long-page cohort.
- **“Hidden instruction”** implies concealment not implemented in the supplied-text experiment. Appendix D presents an ordinary instruction sentence. The experiment tests a source-embedded instruction, not whether extraction preserves hidden HTML.

## 4. Ideas to strengthen the paper

Ranked by acceptance value relative to effort:

1. **Very high value, low effort — narrow the contribution.**
   Suggested statement:
   > We measure potential obstacles to first-party crawler access and test how synthetic page interventions affect brand mentions under supplied-context and searchable-corpus conditions. Treatment rankings depend on the information environment; these experiments do not estimate production-engine returns.
2. **Very high value, moderate effort — repair inference and outcome validity.**
   Prioritise shared-trial position inference, honest null-result labels and a human-coded recommendation subset over adding models.
3. **High value, low–moderate effort — make retrieval the organising comparison.**
   Present a compact matrix of intervention → search exposure → opening → mention → favourable recommendation. Show unconditional outcomes and clearly label conditional associations.
4. **High value, moderate effort — explain heterogeneity using existing responses.**
   Report absolute baseline/treated probabilities and ceiling headroom; repeat pooled estimates leaving out each developer and with equal developer weights. Sonnet 5.5’s 94.4% baseline makes raw percentage-point comparisons especially misleading.
5. **High value, moderate effort — strengthen the access measurement report.**
   Add a sample-flow diagram, per-engine barrier profiles, missingness bounds and rank-band results. Preserve the distinction between policy and demonstrated access failure throughout.
6. **Medium value, low effort — cut competing narratives.**
   Move detailed model procurement, usage weighting and practitioner recommendations to supplementary material. Shorten repeated findings across introduction, discussion and conclusion. Remove the numerical access-versus-edit payoff comparison.
7. **Medium value, low effort — replace the evidence grades.**
   Appendix K mixes efficacy, normative desirability and documented requirements. Keyword stuffing receives D despite positive experimental effects. Use separate columns for evidence strength, observed effect and operational/ethical risk.

**Suggested title:**

**“Crawler Access Policies and Brand Mentions in AI Answers: A Website Audit and Controlled Content Experiments”**

**Abstract changes:** Lead with the two estimands; qualify 34.6% as potential obstacles in a purposive sample; identify API experiments as synthetic; retain the retrieval-dependent reversal; remove the ChatGPT snapshot from the headline unless explicitly labelled as exploratory interface observations.

## 5. Missing related work a referee would expect

These works exist and are absent from the bibliography:

- **Gao, Yen, Yu and Chen (2023), [“Enabling Large Language Models to Generate Text with Citations”](https://aclanthology.org/2023.emnlp-main.398/), EMNLP.** ALCE separates answer correctness and citation quality. It is directly relevant to distinguishing a citation being present from a claim being supported.
- **Rashkin et al. (2023), [“Measuring Attribution in Natural Language Generation Models”](https://aclanthology.org/2023.cl-4.2/), Computational Linguistics.** The AIS framework supplies a principled human-annotation basis for claim attribution. It would sharpen the paper’s absorption construct.
- **Xu et al. (2024), [“Knowledge Conflicts for LLMs: A Survey”](https://aclanthology.org/2024.emnlp-main.486/), EMNLP.** Relevant to the distinction between contextual and parametric knowledge, and to what fictional entities remove—and fail to model—about real brands.
- **Cormack, Clarke and Büttcher (2009), [“Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods”](https://doi.org/10.1145/1571941.1572114), SIGIR.** This is a methodological citation missing from Appendix J’s central retrieval specification.

The largest literature problem is not citation count: the paper needs clearer positioning within retrieval evaluation and attribution measurement, rather than primarily practitioner optimisation.

## 6. Minor points

- Define “answer agent,” “search crawler,” “fetcher,” “answer engine” and “API model” once and use them consistently. They are not interchangeable experimental units.
- Replace “realistic pages” with “longer synthetic pages.” Adding generic boilerplate does not validate realism.
- DNS non-resolution does not prove that a brand name is absent from training data (p. 8); describe it as a collision-reduction precaution.
- Appendix D’s example is interrupted by unrelated tables and figures across pp. 26–29. Keep the prompt and treatment examples together.
- Give per-sector denominators for JavaScript dependence in Table 8; percentages based on small rendered subsets are otherwise difficult to interpret.
- Explain why some unadjusted confidence intervals exclude zero while Holm-adjusted tests are nonsignificant.
- Replace “evidence edits had no effect” with “did not show a positive effect” where appropriate, especially for agentic statistics, whose estimate is negative.
- Provide a dated pre-specification/deviation index linked to exact repository revisions. Explicitly retain the distinction between pre-specified and publicly preregistered.
