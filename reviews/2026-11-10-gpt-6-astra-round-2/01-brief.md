# Brief for GPT-6 Astra: second review of the AEO paper

You are reviewing a research paper as an independent, critical referee and strategist. You have no memory of earlier
work on it, because this is a new workspace. Everything you need is below and in the files described.

## The paper and the goal

- Title: "Crawler Access and Content Effects in Answer Engine Optimization: A Website Audit and Controlled
  Experiments". Author: Ayush Agarwal, independent researcher, single author. Target: Information Processing &
  Management (Elsevier), with an arXiv preprint (cs.IR).
- The author says this paper is very important for their career. They want it as valuable and as publishable as
  honest reporting allows.
- The code, data and paper source are public at https://github.com/ayushagarwaldocs-web/AEO-hoplite. The public commit
  (d2bfbf2) is an older version, however. The current version exists only on the author's machine and has been
  uploaded to this sandbox (see Setup).

## History you should know

1. On 10 November 2026 a GPT-6 Astra agent in another workspace did three things with the 40-page version at d2bfbf2:
   - refereed it (verdict: major revision, with a substantial risk of rejection under its framing then);
   - audited the analysis code;
   - implemented a revision.
   Its review, audit, change log and diff are in `reviews/2026-11-10-gpt-6-astra/` (02 is the referee report, 04 the
   audit report, 06 the change log, 07 its diff).
2. Claude (Anthropic) wrote the code and drafted the paper with the author. It verified that revision independently
   (`08-verification.md`). The analysis fixes were confirmed and kept:
   - The pooled position test (H5) had broken the shared trial structure. Its p-value went from 0.0001 to 0.41, so H5
     is now not supported.
   - The access-obstacle composite became 199/569 = 35.0%.
   - The robots.txt parser fix changed no decision.
   - No treatment effect changed.
   Claude then restored the quantified findings and interpretation that the revision had stripped, and fixed errors it
   had introduced (`09-claude-changes.diff`).
3. The author chose the new title. They also removed the numerical access-versus-edit comparison ("fixing access is
   worth a median 2.2 times a content edit") and the cost ranking.
4. Later the same day, Claude made presentation fixes using existing data only (`10-follow-up-changes.md`):
   - research questions and contributions in the introduction;
   - the placebo's length reported: a median of 32 words added, against 8 to 44 for the single edits and 149 for the
     combined package, with a placebo effect of +1.8 points [−0.7, 4.3];
   - the appendix of sensitivity analyses rewritten;
   - consistent treatment names;
   - tables kept in their own sections.
5. Current state: 46 pages. `paper/check_claims.py` passes 162 of 162 checks, and 68 tests pass. Claude rates the paper
   at about 7 out of 10 for IP&M, with "major revision" as the most likely first decision. Claude helped write the paper
   and may be biased, which is why you are being asked.

## Still open from the first review (needs new data or people)

- **No human-coded outcome.**
  - "Named", the main pre-specified outcome, is detected automatically.
  - Nothing measures whether an answer recommends the brand.
  - The absorption measure rests on a keyword detector and two model judges.
- **Third-party endorsement mixes several things.** It is the headline effect: +37.4 points pooled over 12 models, more
  than any single on-page edit. But it combines provenance, an extra mention and an explicit recommendation. An
  exploratory follow-up separated recommendation strength from a bare mention, but not provenance.
- **Other gaps.**
  - The search-task comparison does not isolate retrieval.
  - There is no before-and-after measurement of access.
  - JavaScript dependence was measured on only 269 of 569 homepages.
- **Human labels.** An earlier round of human labels could not be used, because they followed the type of edit shown on
  the sheet rather than the answer text. A third round is prepared but not done.

## Resources and constraints

- **No model calls here.** This sandbox has no API keys, so you cannot call language models. Claude runs any new
  experiment on the author's machine. Keep to analysis, design and writing here.
- **Budgets left.** These are approximate, from Claude's ledger, and not verified:
  - AWS Bedrock, about $13. This covers the 12 main hosted models. The main run cost about $22 for 16,200 answers;
    Claude Sonnet 4.6 is the costliest, at about $0.008 per answer.
  - Azure, about $43 (GPT-5 mini, Grok 4.6, MAI-Thinking-1, DeepSeek V4 Pro, Kimi K3.1 Pro).
  - OpenAI, about $7.5.
  - Gemini free tier (Gemini 3.5 Flash-Lite, about 500 requests a day).
  The author has approved AWS spending.
- **Human time.** The author can probably find one non-expert rater for about an hour. There is no budget for
  crowdworkers.
- **Repository rules.** Do not commit, push, open pull requests, or touch any repository other than your local clone.
  This step is a report only: do not create or edit files outside /tmp.
- **No Hoplite.** Do not mention Hoplite in anything meant for the paper.

## Setup

1. Clone the public repository:
   `git clone https://github.com/ayushagarwaldocs-web/AEO-hoplite.git /tmp/aeo && cd /tmp/aeo && git checkout --detach d2bfbf2`
2. Rebuild the current files, which were uploaded in six parts to `/tmp/upload/`:
   - Run `cat /tmp/upload/part.* > /tmp/current.tgz && sha256sum /tmp/current.tgz`. It must print
     dcd2cd743a7bc5816541315ef76de4de900dde70b8d93a9a40bf8dc5f4746a1f.
   - Then run `tar xzf /tmp/current.tgz -C /tmp/aeo`.

   This overwrites the 128 files changed since d2bfbf2 and adds the new ones; `/tmp/upload/changed.txt` lists them, and
   nothing was deleted. The result is the author's current working tree, except files that are never published: API
   keys, run logs and the raw Study 1 crawl.
3. Read `paper/main.pdf`, the current 46-page version, as a referee would. Then read the review log, then whatever code
   and data you need. You may run Python analyses. `experiments/exp2_content_treatments/analyze_all.sh` rebuilds every
   number from the data without network access, in about 2 to 7 minutes; skip the PDF build if tectonic is missing.

## What I need from you

A. **Rating.**
   - An honest score out of 10 for IP&M, the likely first decision, and rough odds of desk rejection and of eventual
     acceptance.
   - How it compares with the version reviewed before (02-review-report.md).
   - Which other venues would fit better, if any.

B. **Referee report on the current version.**
   - Major and minor concerns, with page or section references, separating fatal problems from fixable ones.
   - Check that the main claims match the tables and the data.
   - Flag anything wrong, overstated or inconsistent, including errors that either revision introduced.

C. **Improvement strategy.** A ranked plan, weighing value for acceptance against effort, cost and risk, in four
   groups:
   1. text and structure only;
   2. analyses of existing data;
   3. new experiments within the budgets above;
   4. human tasks and submission tactics (preprint, expert readers, cover letter, venue).

   For each item, say what a referee would gain and what could go wrong.

D. **Critique of Claude's proposals, and better alternatives.** Improve or replace these designs. For each, give exact
   conditions, predictions, contrasts, sample sizes and power, costs, decision rules, and how the result would be
   reported. For reference, the main design has:
   - 30 scenarios × 3 trials = 90 trials per model;
   - effects paired within trial;
   - intervals from a cluster bootstrap over scenarios;
   - sign-flip tests with Holm correction.

   The proposals:
   1. **Provenance experiment** on the 12 main models.
      - In the existing third-party condition, the guide's endorsement sentence is "In our hands-on testing, {target}
        stood out for {feature 1} and {feature 2}, and it is the option we would shortlist first."
      - New condition `self_endorsement`: that identical sentence on the target's own page, with the guide neutral.
      - New condition `quoted_endorsement`: the sentence on the target's page as a quotation attributed to the guide's
        site, with the guide neutral.
      - Optionally, a re-run of the baseline to check for drift.
      - Contrasts: third-party vs self (where the words appear), quoted vs self (attribution), and third-party vs
        quoted.
      - Cost about $3 to $5.
   2. **Recommendation coding** of existing answers.
      - Two model judges from different developers label each answer. The target is either its single top
        recommendation, recommended among others, mentioned without being recommended (or negatively), or not named.
        The judges also name the top recommended brand.
      - Coverage: the baseline plus five key conditions, for the 12 main models (6,480 answers).
      - Agreement between the judges is reported, and the result is labelled exploratory.
      - Cost about $10 to $15.
   3. **Human check.** One rater, blind to condition, labels 150 answers with the same scheme, to validate the judges.

E. **What you could implement yourself next** in this sandbox: code for new conditions, analysis scripts, judge prompts
   and text revisions. Say in what order, and what Claude must do on the author's machine.

## Sandbox notes

- The six parts are already in `/tmp/upload/` and their combined SHA-256 has been checked.
- This sandbox has python3 and pdftotext but not pandas; install what you need with pip.
- The repository this workspace opened with (`hop`) is an empty placeholder. Do not modify it or push to it.

Write the full report in Markdown to `/tmp/astra_review_round2.md`, and give the same content as your final message.

- Be direct and specific, and do not soften judgments.
- Verify every number you quote against the files.
- If you cite literature, give full details and say whether you could verify them.
