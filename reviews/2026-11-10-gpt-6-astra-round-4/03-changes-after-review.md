# Changes after Astra's fourth review (10 November 2026)

Made by Claude on the working tree after the author asked for Astra's finishing pass. No new data were collected, and
no estimate changed.

## Wording in the paper

- **Third contrast.**
  - Section 5.4 now labels the arms B, Q0, Q1, T0 and T1, and states the three contrasts as equations.
  - It says the third contrast equals (T1 − Q1) − (T0 − Q0). Recommending wording added 11.2 points on the brand page
    and 7.4 on the guide, so the contrast is −3.8.
  - The ceiling is called a plausible reading, not an identified mechanism.
- **Citations.** "Citations moved from the brand's page to the guide" is replaced in the paper, the top-level README and
  the round-3 log. The new wording says that citations of the brand's page fell and, descriptively, citations of the
  guide rose. Section 5.4 adds that both pages were cited in 77.8% of T1 answers and 54.7% of Q1 answers. These
  both-pages rates were added after this review and are labelled descriptive in `analyze_site_extra.py` and the
  experiment README.
- **Appendix E.** The freeze is described as author-recorded and not independently timestamped.

## Records

- **Experiment README, separate-site section.**
  - The second-account execution paragraph is labelled the original plan.
  - The freeze record is labelled author-recorded, and notes that it was committed after the run (`82fe67e`, 19:13
    IST).
  - The run record separates the last recorded answer (18:31:51 IST) from the last process exit (18:31:57 IST).
- **Claim check.** The timing check is relabelled. It says the first recorded request is later than the
  author-recorded freeze time, and that this does not verify when the freeze happened.
- **Round-3 log.** The "15% shorter" figure now states that it was counted before the separate-site text was added.
  It also gives Astra's own count of 8.2% from version 3 to version 4.

## Public-facing claims

- **Top-level README, item 2.** "Engines lean on reviews, press, communities and reference sites more than on your
  own pages" is now attributed to the AI-search literature (Chen et al. 2025). The experiment is described as what it
  tested: synthetic pages supplied to API models, with no test of real reviews or press.
- **Top-level README, item 4.** "In our experiment they did nothing" is replaced. Q&A rewrites and freshness stamps
  did not change mentions significantly, and freshness dates did no better than the placebo. This is the same
  correction Astra asked for in the paper in round 3.
- **Handbook evidence table.** The corroboration row says the +37.4 is for one recommendation in a synthetic buyer's
  guide, not a test of real reviews or press.

## Code

- **Rank correlation.** `make_numbers.py` rounds effects to 10 decimals before computing Spearman's rho. Exactly tied
  effects then stay tied across pandas versions, which explains the 0.94 versus 0.95 that Astra saw for `SmRhoPawc`.
  The committed values are unchanged: `SmRhoPawc` 0.95, `RhoPawc` 0.85, `FlRhoPawc` 0.89.
- **Recommendation study, before any human label or full coding.**
  - `recommendation_data.py` re-parses every stored attempt with the frozen parser instead of trusting its stored
    validity flag.
  - The analysis audit reports re-asks by model and condition.
  - `recommendation_protocol.py`, whose hash is frozen, is unchanged.
  - A new test covers both additions.
  - The existing held-out labels pass the stricter check: 60 of 60 valid, with one re-ask, on an injection-condition
    item.
  - The experiment README records this as a dated audit addition.

## Not changed

- No further paid experiment, as Astra advised.
- The recommendation study still waits for the human labels. Its gate and thresholds are unchanged.
- The cover letter keeps its arXiv placeholder until there is a preprint number.

## State

432 of 432 claim checks pass, 96 tests pass and 1 is skipped (it needs `boto3`), and the paper builds at 47 pages with
references starting on page 24. The submission files are rebuilt.
