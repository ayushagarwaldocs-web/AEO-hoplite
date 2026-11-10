# Verification of GPT-6 Astra's changes (10 November 2026)

Done by Claude (Anthropic) on a separate local branch, `astra-revisions`, before anything was committed. Astra's
source changes are in [07-astra-changes.diff](07-astra-changes.diff); the edits made here afterwards are in
[09-claude-changes.diff](09-claude-changes.diff).

## How the patch was checked

- The patch was copied byte for byte from Astra's sandbox (its SHA-256 matched the one Astra reported) and applied
  cleanly to commit `d2bfbf2` plus this review log.
- The full pipeline (`analyze_all.sh`, including the PDF) was rerun here with network requests sent to a dead proxy:
  exit 0, all claim checks passing (157, up from 116 because Astra added checks). The test suite passed (68 tests).
- Study 1 was rerun here on the raw crawl, which is not in the repository and which Astra therefore could not use.
- No paid API was called. The search-task replay reads cached embeddings only and fails rather than calling the
  embedding API.

## Findings checked independently

| Finding | Check made here | Result |
|---|---|---|
| A1, pooled position test (H5) | New permutation code, written without reading Astra's: the slot labels are shuffled across trials, every model of a trial keeping the same slot; also within scenario | Main set, χ² 26.9: p = 0.402 and 0.411 (the original within-model test gave 0.0001). Replication, χ² 19.3: p = 0.591 and 0.589 (originally 0.0009). All 90 trials gave every model the same slot. **Confirmed**: H5 is not supported. |
| C2, barrier composite | Study 1 regenerated from the raw crawl | 199/569 = 35.0% [31.2, 39.0]. The two added sites are canva.com and rei.com (refused the bot user agent only). The rate without edge refusals is unchanged at 19.0%. **Confirmed.** |
| A4, robots.txt parser | Old and repaired parsers run on every robots.txt in the raw crawl (490 organisational, 539 Tranco), for the 16 AI agents and the wildcard, at the site root that Study 1 evaluates | **0 decisions differ.** The fix changes no reported number. |
| A3, hidden HTML | The raw crawl kept word counts, not HTML | Cannot be re-measured; the paper states the limitation. |
| A2, detector attribution | `judge_items.jsonl` compared before and after | 960 items, same ids and order; only the detector field differs, in 7 items. The model judges' labels are untouched. |
| Faster pipeline (about 100 s instead of 400 s) | Resampling settings compared | Not from fewer draws (10,000 permutations, 4,000 bootstrap samples, as before); the position test was vectorised. |
| Search-task predictions | Effect and contrast files | P2 and P3 hold (keyword stuffing raised how often the page was returned by 54.4 points and opened by 26.1, the summary raised returns by 26.4, citations and statistics did not); P4 holds (citation and statistics effects 24.2 and 20.6 points smaller with search, p < 0.001); P5 fails (+0.6). P1 holds in part. |
| MAI-Thinking-1 observation | Search-task data | It answered 183 of 630 questions (29%) without searching, and all 183 cited real sites it never retrieved (cnet.com 44, nytimes.com 35, pcmag.com, forbes.com, ...). |
| New references | Official BibTeX from the ACL Anthology and, for the SIGIR paper, the DOI record | All four exist, and authors, venue, pages and DOI match. |

## Kept from Astra

- **Analysis code:** the corrected position test (A1) and trial-clustered position intervals (B1); target attribution
  in the limitations detector (A2); the hidden-HTML and robots.txt parser fixes with regression tests (A3, A4); equal
  model weighting in the fixed-query replay (C1); the composite including bot-only refusals (C2); stronger claim
  checks (C3); new exploratory analyses (developer-weighted and leave-one-developer-out estimates, absolute
  probabilities, page-length diagnostics, a ranking replay, a sensitivity analysis without MAI-Thinking-1); 52 new
  tests.
- **Paper:** the dated deviation entries, with the original position results kept on record; the chain-rule form of
  the framework; definitions of answer engine, API model, answer agent, search crawler and fetcher; "potential
  first-party access obstacles"; the rank-band and JavaScript-coverage reporting for Study 1; "first-mentioned brand"
  in place of "top pick"; "source-embedded instruction" (it was plain page text, not hidden); the placebo described as
  not length-matched to every package; unconditional absorption rates beside the conditional ones; every correction the
  referee listed (blocking does not remove a site from answers, no lower bounds, no inferred intent, no claim that
  competitors' edits cancel, temperature results not called equivalence, no "resistance can be trained", 32 of 64
  sources called half rather than a majority, the llms.txt denominator); the usage weighting moved to the appendix;
  the four new references and the "Attribution and retrieval" paragraph; the new title chosen by the author.

## Changed or reversed here, and why

1. **Duplicate heading.** Study 1 had two `\section` commands in a row, an empty "Potential first-party access
   obstacles" followed by "Access barriers". One heading kept.
2. **Pre-specified hypotheses.** H1 and H3 had been reworded ("evidence packages", "keyword repetition"). Restored to
   the wording specified before the runs, with the caveat that the edits are packages stated beside them.
3. **Over-corrected narrative.** The abstract (12 numbers down to 3), the main-findings list (23 to 2), the discussion
   (12 to 0; 1,357 words to 597) and the conclusion had lost the quantified results and most of the interpretation,
   not only the overclaims. Rewritten from the pre-review text with every correction applied: the numbers are back
   (endorsement +37.4, citations +21.1, statistics +13.7, replication +30.5, search task 22% against 53%, the
   instruction in 10 of 12 models), the flagged phrasing stays out (no 2.2-times comparison or cost ranking, as the
   author decided; no inferred intent; no "because the page was seldom opened"; no "resistance can be trained";
   "longer synthetic pages"; the position effect reported as not supported), and the discussion's links to prior work
   (Chen et al., Aggarwal et al., Liu et al., the Guardian report, spam policies) are restored.
4. **Search-task verdicts.** Astra removed the verdicts on the pre-specified predictions P2 to P5. Restored, and the
   predictions are now stated in the paper; before, they were only in the experiment's README.
5. **Specifics restored.** Measurement dates (3 and 4 November 2026); the Tranco band boundaries and 250 draws per
   band; the Pew click-through figure; the content-delivery network's default blocking of AI crawlers; the comparison
   of the two samples (training against answer agents, the three publisher sectors, wildcard rules, llms.txt,
   Content-Signal, path-level rules), each statement checked against the current numbers; "an audit limited to
   AI-specific rules would not flag these sites"; specific external-validity limits, including that Google appears only
   through smaller models; the MAI-Thinking-1 observation; and "the largest effect on first mentions" for the
   instruction (checked: +40.6 against +30.9 for endorsement).
6. **Evidence table.** Astra replaced the graded table with a "boundaries" table without grades or citations of prior
   work. Rebuilt with separate columns for prior evidence, this paper's result, a grade that rates the strength of
   evidence only, and risks and limits, as the referee suggested. Keyword stuffing is now graded C (mixed evidence),
   with its spam risk listed separately.
7. **Consistent terms and figures.** "Keyword stuffing", the condition's name in the specification, tables and
   figures, instead of a partial switch to "keyword repetition"; "Boilerplate placebo" in figures and tables, to match
   the text; the position figure's caption, which described Wilson intervals although the code draws a
   trial-clustered bootstrap; the Study 1 obstacle figure, whose axis label was a cut-off disclaimer.
8. **Highlights, cover letter, README and handbook chapter 4.** Astra's versions were mostly caveats; every highlight
   was a limitation. Rewritten to state the findings within the corrected scope. Chapter 4 keeps Astra's new risk
   column, and the summary's effect in the search task is again described as causal within that task, where it was
   randomly assigned; only the comparison between tasks does not isolate retrieval.
9. **AI-use declaration.** The paper, the journal declarations and the submission builder now name GPT-6 Astra
   (OpenAI) as reviewer of the manuscript and code and as drafter of revisions.

## Not done: would need new data or people

- Human labels for whether an answer recommends the brand and transmits its claims accurately (the round-3 human
  check is still pending).
- Experiments that separate information, provenance and format, and a placebo matched in length to each package.
- Before-and-after measurements of fixing access, and a matched-pool search experiment that isolates retrieval.
- Re-measuring JavaScript dependence with the hidden-text fix, which needs a new crawl.

## Result

- Potential obstacles 35.0% (was 34.6%); H5 not supported (p = 0.411 and 0.593); every treatment effect unchanged.
- Claim checks 157 of 157; tests 68 of 68; the paper builds without errors.
- 45 pages (40 before the review): main text one page longer, appendices three (new robustness tables), references one.
- Hoplite usage: the audit-and-implementation thread came to about $31.65 of the workspace's included usage; the
  review thread's cost was not recorded; the two failed command-line attempts cost about $0.11 each.
