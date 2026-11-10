# Changes after Astra's third review (10 November 2026)

Made by Claude on the uncommitted working tree, after the author chose to redo the recommendation study rather than
drop it, and asked for Astra's other recommendations too.

## Recommendation study: amendment 1

Full record: "Amendment 1" in `experiments/exp2_content_treatments/README.md`.

- **Written and frozen at 16:42 IST, before any label under it.**
  - The 60 version-1 held-out items, whose invalid judge outputs had made the gate unattainable, are retired from the
    human check. They stay in the census coding.
  - A fresh, disjoint set of 48 probability items, 12 challenge items and 6 repeats was drawn with a new seed.
  - Invalid judge outputs get uniform re-asks: up to three calls per item, at every stage, and the first valid one
    counts.
  - The gate counts a judge label still invalid after re-asks as a disagreement; there is no separate completeness
    rule.
  - The pair minimum is 80, because only 87–88 pairs per model and contrast exist after the pilot and practice
    exclusions.
  - The checker's source code is hashed into the protocol.
- **Checks.**
  - Version 1 rebuilds with identical hashes after the refactor.
  - Four new tests cover the fresh draw, the re-asks (including rejection of a re-ask after a valid output), the stop
    after three calls, and the amended gate.
- **Results.**
  - GPT-5 mini development pilot under the amendment: 83 of 84 valid after re-asks ($0.057).
  - Fresh held-out stage: 60 of 60 valid ($0.042).
  - The new rater workbook replaced the unused version-1 copy in the author's Downloads folder.
- **Second judge.** The decision to run the declared Qwen 3 32B fallback was recorded at 16:55 IST, after the author
  offered more AWS credit and before any human label existed. Its pilot was 0 of 84 valid: every output was wrapped in a
  Markdown code block, which the frozen checker rejects. Under the rule written beforehand it is not used, and the
  checker was not amended to admit it.

## Astra's text recommendations

- **Section 5.4.**
  - The freeze is described as fixed immediately before execution, with the first query at 14:24:35 IST and the public
    record committed after the run.
  - Five arm rates added (49.1, 79.7, 89.8, 80.8 and 92.9%).
  - The 989 complete blocks are stated, and one answer that reached the token limit is disclosed.
  - The baseline is "close to the original", not "reproduced".
  - The conclusion is narrowed to the measured contrast, and the exclusivity of "the option" is noted.
- **Prose corrections.**
  - Freshness dates "did not outperform the placebo", rather than "did nothing".
  - The conclusion no longer guesses where ChatGPT's answers came from.
  - The "earned coverage" claims are removed.
  - The reproducibility claim is made precise.
  - The discussion's checklist is replaced by a short, scoped implications paragraph.
- **Citation outcome.** Astra noted that the outside source's effect on citation of the brand's page has a
  Holm-adjusted p of about .104. The specification listed citation as a secondary outcome, but Section 5.4 had not
  reported it. Table 6 now reports all three outcomes, one row per contrast, and the text says that this contrast did not
  survive Holm correction. A claim check tests the sentence.
- **Review logs.** The round-2 verification log said its changes were made "before any paid query". A dated
  correction note there now says which changes followed paid judge pilots. Briefs stay verbatim, as sent.
- **Experiment README.**
  - Superseded plans are labelled historical: the $9 caps, the 256-token judge limit, the 87-pair minimum, the
    no-retry rule and the pre-pilot budgets.
  - A note on the attribution freeze line says that "follow-up query" there means an attribution query, and that the
    judge pilots ran from 13:53:46 to 14:26:43 IST. It also says the minute-level record cannot be ordered against the
    first query at 14:24:35 IST.
- **Appendix E.** The attribution entry is now a compact timeline: draft, the four pre-run changes (including $9 to
  $10), the freeze and first-query times, the post-run commit and the descriptive extras.
- **Compression.** The main text went from about 10,200 to 8,660 words (15% shorter):
  - the findings list went from eight bullets to three;
  - the discussion was cut to about 1,000 words;
  - the conclusion was shortened;
  - the Study 2 method keeps model sourcing, quota history, long-page text rules and judge names only in the
    appendices, to which they were moved word for word;
  - Section 5.2's interface detail moved to a new appendix paragraph;
  - the framework is retitled "A decomposition of AI visibility" and described as organising the studies, not as an
    estimated model;
  - the sample-comparison paragraph points to Table 17 instead of repeating it.

## Separate-site follow-up: run

- **Design.** The specification is in the experiment README. It has five arms in one run: B, the outside reviewer's
  sentence on the brand page (Q0, Q1), and the identical sentence on the buyer's guide (T0, T1). The primary contrasts
  are T1 − Q1, T0 − Q0 and their difference, with a Holm family over the three.
- **Code.**
  - `site_*` arms in `attribution.py` and `build_corpus.py`, with a mechanical check;
  - a generalised runner;
  - `analyze_site.py`, `run_site_parts.sh` and `combine_attribution_parts.py --study site`;
  - four tests.
- **Unchanged.** The main prompts still match the recorded hash, and the attribution prompts match the committed
  version.
- **Account.** The author's second AWS account refused every smoke-check call: its organisation policy denies Bedrock
  API keys, and nothing was spent there. At the author's direction the run used the first account, the one used for the
  earlier runs.
- **Freeze and run.**
  - The freeze was recorded at 17:31:11 IST, with code and plan hashes. The first query started at 17:31:16 IST, and the
    last model finished at 18:31:57 IST.
  - All 5,400 calls succeeded: no errors, no capped model and no truncated answer.
  - Cost: $7.30 at ceiling prices.
  - Every row carries the frozen items' fingerprint.
  - Nothing is committed yet, so the public record will again follow the run, and the paper says so.
- **Results** (12 models, 1,080 complete blocks, Holm over three).
  - The neutral sentence named the target 4.6 points more often on the guide than on the brand page ([1.9, 7.4],
    p .013).
  - For the recommending sentence, near the ceiling in both places (92.9% and 93.7%), the difference was not resolved:
    +0.8 [−0.8, 2.7].
  - The third contrast, the first minus the second, was −3.8 [−6.7, −1.1] (p .031), but not significant with developers
    weighted equally (p .070).
  - Secondary: on the guide, the recommending sentence cut citations of the target's page by 7.7 points, as answers
    cited the guide instead.
  - The arms repeated from the attribution follow-up came out within one point of it.
- **Where it is reported.**
  - The paper: the end of Section 5.4 and Table 7, a sentence each in the findings, discussion and conclusion, the
    limitations paragraph, and an Appendix E entry.
  - The repository: the experiment README run record, the top-level README and the handbook's evidence table.
  - The cover letter: its "wording mattered more than source" phrase is narrowed as Astra asked.
  - The abstract is unchanged, to stay within 250 words.
- **Claim checks.** 13 new claim checks cover these statements, plus the macro checks.
- **Also added.** An AI-use statement that names Astra's drafting of the attribution design and code.

## State

423 of 423 claim checks pass, 95 tests pass and 1 is skipped (it needs `boto3`), and the paper builds at 47 pages with
references starting on page 24. All of this was committed locally after the separate-site run, on branch
`astra-revisions`; nothing is pushed.
