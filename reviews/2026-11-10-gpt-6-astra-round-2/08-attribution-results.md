# Attribution follow-up: run and results (10 November 2026)

- **Specification.** Frozen at 14:24 IST, before any query; see the experiment README.
- **Run.** 14:24 to 15:25 IST, 12 Bedrock models in parallel, one process per model.
- **Calls.** 5,385 of the 5,400 planned calls were made. 11 failed with server errors or timeouts and were not retried,
  as the protocol requires: 10 for Nemotron 3 Super and 1 for Claude Sonnet 4.6. Nemotron then hit its spending cap,
  because failed calls are charged at their full reservation, and was left with 81 complete trials.
- **Panel.** The pre-specified rule needs 87 complete trials, so Nemotron is excluded and 11 models are analysed.
  Claude has 89 complete trials and every other model has 90.
- **Cost.** $7.42 at the repository's ceiling prices, about $5.90 at Bedrock's billed prices. The cap was $10.

## Results

Primary outcome: mentions, pooled over 11 models with equal weight, with Holm correction over the three contrasts.

| Contrast | Mentions | Named first (secondary) |
|---|---|---|
| Recommending vs neutral wording, brand as source | +10.1 [6.7, 13.8], p < 0.001 | +23.3 [17.9, 29.4], p < 0.001 |
| Outside reviewer vs brand, recommending wording | +3.1 [1.4, 4.9], p = 0.003 | +4.9 [2.9, 6.8], p < 0.001 |
| Difference between the two sources' wording effects | +2.0 [−0.6, 4.6], p = 0.150 | +3.2 [1.2, 5.4], p = 0.008 |

Equal developer weighting gives the same verdicts for mentions.

**Descriptive (not pre-specified):**
- Recommending wording raised mentions in all 11 models. The outside source raised them in 9 and lowered them in none.
- With the brand recommending itself, 10 of the 11 models already named it in at least 85% of answers, which leaves
  little room for the source to add more.
- The neutral sentence alone raised mentions by +30.5 points over the fresh baseline.
- The fresh baseline reproduced the original one. Over 989 paired trials, the target was named in 49.1% of answers
  against 49.7% four to six days earlier, and the two answers agreed in 87.5% of trials.

## In the paper

- New Section 5.4 with Table 6, built from generated macros and checked by 9 new claim checks plus the macro checks
  (258 of 258 pass).
- Updated: the abstract (247 words), the findings list, the discussion of endorsement, the threats to validity, a
  dated entry in the deviations list, the introduction's study overview, the README and the cover letter.
- Interpretation kept within the design: on supplied pages, the wording of a recommendation mattered more than its
  stated source. This is a stated attribution in synthetic text, not verified independence, and it was not tested on
  a separate site.
