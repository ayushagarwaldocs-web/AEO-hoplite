# Text corrections made from Astra's second report (10 November 2026)

Made by Claude on the uncommitted branch `astra-revisions`, while Astra built the follow-up code in its sandbox. Each
item was checked against the paper before it was changed. No numbers changed.

| Report item | Where | Before | After |
|---|---|---|---|
| 5.3, comparison class of "best edit" | `findings.tex`, `results_robust.tex`, `conclusion.tex` | Citations called "the best edit to the brand's own page" | "The strongest of the ten single page edits", noting that the combined package (+23.6) and the embedded instruction (+28.3) did more. Checked against `SINGLE_ON_PAGE` in `analyze_hypotheses.py`, which defines H2's comparison set. |
| 4.3, edge "upper bound" | `main.tex`, Study 1 method | The research-client refusal rate was "an upper-bound proxy for refusal of a verified agent" | It describes how sites treated our client and is neither an estimate nor a bound for verified agents, which a site may treat differently in either direction. |
| 5.4, intent of wildcard rules | `main.tex`, Study 1 results | Heading "Configuration errors" | "Wildcard rules and token problems", with "such a rule may be deliberate; the file does not show its owner's intent". |
| 5.5, power wording | `main.tex`, analysis | "a model-level null rules out only large effects" | Approximate, unadjusted detectable effects (checked in `analyze_power.py`: 2.80 standard errors), and a non-significant result read from its interval. |
| 5.1 and 4.5, interface snapshot | `findings.tex`, `discussion.tex`, `conclusion.tex`, `abstract.tex`, highlights | "The most used assistant showed no retrieval"; "no visible retrieval"; the snapshot in the abstract and highlights | "Two consumer assistants behaved differently in a snapshot", visible behaviour only, "in our 26 sessions". The snapshot is removed from the abstract and highlights. The abstract now says outcomes record whether answers name the brand, not whether they recommend it (248 words). |
| 5.2, training data | `discussion.tex` | Blocking a training crawler "keeps an organisation's own pages out of that operator's future training data" | It closes that operator's documented collection route, without guaranteeing absence from training data. |
| 4.2, "earned media" | `main.tex`, conditions table | Type "earned media" | "third party". Chen et al.'s earned-media finding is still cited as theirs. |
| 4.3, conclusion overreach | `conclusion.tex` | "access deserves equal attention"; keyword stuffing described as "saying plainly which questions a page answers" | "access and retrieval deserve attention too"; "repeating the question's words". |

After the changes, 162 of 162 claim checks pass, the paper builds at 46 pages, and the submission files were rebuilt.
