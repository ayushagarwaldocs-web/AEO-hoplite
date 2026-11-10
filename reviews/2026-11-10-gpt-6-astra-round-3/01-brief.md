# Brief for GPT-6 Astra: third review, of the committed version

Thank you for the second review and the build. Please now review the paper again, as a strict, independent IP&M
referee. You helped design the new studies, so be especially sceptical of them, and do not defend your own choices.
This step is a report only: do not edit, commit or push anything, and do not touch the `hop` repository.

## What to review

- `/tmp/aeo-v3`, branch `review-v3`, at commit `8743de4`. These are the author's exact local commits on top of the
  public `d2bfbf2` (bundle SHA-256 8168b726...d5a6, verified):
  - `9f808f6`: the round-1 revision;
  - `8743de4`: everything since your second review.
- `paper/main.pdf` is the current 47-page version.
- Your earlier working copy, `/tmp/aeo` (branch `round2`), is still in this sandbox, for comparison with what you built.

## What happened since your second review (6/10)

1. **Text corrections from your report** (see `reviews/2026-11-10-gpt-6-astra-round-2/04-text-corrections.md`):
   - the comparison class of the best edit;
   - edge refusals no longer called a bound;
   - wildcard intent;
   - power wording;
   - the interface snapshot removed from the abstract and highlights;
   - the scope of training-crawler blocks.
2. **Claude reviewed your build and changed it before any paid query**, recording each change, with times, in
   `experiments/exp2_content_treatments/README.md` and `reviews/.../round-2/07-verification.md`:
   - the attribution sentences now name the scenario's stated need instead of "the question";
   - the evaluator is "Neralin" instead of NeralinAA to NeralinBD;
   - only `data/private/` is ignored by git;
   - per-model caps are based on the larger of the live and historical cost, with a $10 total cap instead of $9;
   - a `--part` mode runs one process per model;
   - the judge output limit is 1,024 tokens instead of 256;
   - evidence spans are compared without regard to Markdown, quotes or case;
   - MAI-Thinking-1 was dropped after its pilot;
   - the rater workbook uses plain language.
3. **The attribution follow-up ran** (`reviews/.../round-2/08-attribution-results.md`, paper Section 5.4 and Table 6):
   - 5,385 of 5,400 calls were made. Nemotron 3 Super is excluded under the 87-trial rule, after 10 failed calls that
     were not retried.
   - Results on 11 models: S1 − S0 = +10.1 [6.7, 13.8]; Q1 − S1 = +3.1 [1.4, 4.9]; the interaction +2.0 [−0.6, 4.6],
     not significant.
   - The fresh baseline gave 49.1% against the original 49.7%.
   - The abstract, findings, discussion, threats, deviations, README and cover letter were updated.
4. **Recommendation coding is built and piloted, but not run at scale.**
   - The GPT-5 mini pilot passed (82 of 84 valid), and GPT-5 mini has labelled the 60 held-out human items.
   - The one-hour human check has not been done yet, so the full coding has not started.
   - The paper says nothing about recommendation results yet.
5. 258 of 258 claim checks and 87 tests pass. The author's coordinator, Claude, rates the paper about 6.5 out of 10 on
   your scale.

## What I need from you

A. **Rating.** A fresh score out of 10 for IP&M, the likely first decision, and rough odds of desk rejection and of
   eventual acceptance. Say what changed since your 6/10, and why.

B. **Verification.**
   - Rerun `experiments/exp2_content_treatments/analyze_attribution.py` and `analyze_attribution_extra.py` from the
     committed data (install pandas if needed).
   - Check every number and claim in Section 5.4, Table 6, the abstract and the findings list against the outputs.
   - Run `python3 paper/check_claims.py` and `python3 -m pytest -q`.

   Report anything that does not match.

C. **Audit of Claude's pre-run changes.** For each change in point 2:
   - Is it defensible?
   - Was it made and recorded before the queries? Compare the freeze record's time, 14:24 IST, with the first row's
     timestamp in `data/responses_bedrock_attribution.jsonl`.
   - Is it disclosed adequately in the paper (the deviations list in Appendix E)?
   - Does any of it weaken the claim that the follow-up was "specified on 10 November 2026 before any of its queries"?
   - Do the changes to the evidence-span checker or to the judge settings threaten the recommendation protocol's
     integrity?

D. **Referee report on the current version.**
   - What still blocks acceptance, separating fatal from fixable.
   - Whether Section 5.4's interpretation is supported: "On supplied pages, then, what a recommendation says mattered
     more than who was said to make it." Consider the ceiling, the +30.5-point neutral-sentence effect and the design's
     scope.
   - Any overclaims or inconsistencies introduced since your last review.

E. **Before submission.** A short, ranked plan:
   1. Is the recommendation coding still necessary, and what should the paper say if the human check fails?
   2. What to cut or move to supplementary material to reach a focused main text, naming sections.
   3. Anything else that would materially change the odds.

Write the full report in Markdown to `/tmp/astra_review_round3.md`, and give the same content as your final message.
Be direct and specific, verify every number you quote, and do not soften judgments.
