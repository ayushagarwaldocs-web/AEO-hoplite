# Review log: GPT-6 Astra, round 3 (10 November 2026)

A third, independent review of the version committed locally as `8743de4`. It ran in the same Astra thread as
round 2, so Astra knew its earlier verdict and the follow-up studies it had designed. It was asked to be especially
sceptical of those studies.

| File | What it is |
|---|---|
| [01-brief.md](01-brief.md) | What Astra was asked, exactly as sent |
| [02-review-report.md](02-review-report.md) | Astra's report, verbatim |
| [03-changes-after-review.md](03-changes-after-review.md) | What was done in response: the amended recommendation study, the text fixes and cuts, and the separate-site test with its results |

## Verdict in brief

- **Rating:** 6.5/10, up from 6; major revision; not yet ready to submit.
- **Odds as committed:** desk rejection 35–50%, eventual acceptance 15–30%.
- **Odds after the focused corrections and compression:** 25–40% and 25–40%.
- **Verified:**
  - the attribution analysis regenerates exactly from the committed data;
  - all 5,374 successful answers rescore with zero discrepancies;
  - 258 of 258 claim checks and 88 of 88 tests pass;
  - the main-study prompts are unchanged.
- **Two audit findings:**
  - The public record cannot order the 14:24 IST freeze against the first query at 14:24:35 IST, and the commit
    followed the run. The paper should say the protocol was fixed immediately before execution, rather than claim an
    independently verifiable pre-query freeze.
  - The recommendation study's frozen gate requires a valid judge label for every held-out item; 3 of the 60 are
    invalid. Claude confirmed this in `score_recommendation_human.py`. The gate therefore cannot pass whatever the
    human labels say.
- **Other points:**
  - narrow Section 5.4's conclusion and show the five arms' absolute rates;
  - six prose corrections;
  - cut the main text by 15–20%.
