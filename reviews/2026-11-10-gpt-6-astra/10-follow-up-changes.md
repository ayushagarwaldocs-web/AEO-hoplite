# Follow-up changes after verification (10 November 2026)

Made by Claude (Anthropic) on the same uncommitted branch, `astra-revisions`, after the author asked how to
improve the paper further. They use existing data only: no model was called and no number changed. The verified
state before these edits was saved as patches outside the repository first.

| Change | Why |
|---|---|
| The introduction now states three research questions (access, selection, search), says which study answers each, and lists three contributions. | The referee's first suggestion was a narrower, clearly stated contribution; the two studies were linked only implicitly. |
| The placebo's length is reported: it added a median of 32 words to the target's page, within the 8 to 44 words of the single edits; only the combined package (149) was much longer. Its effect was +1.8 points [−0.7, 4.3]. | The conditions table called the placebo "length-matched" while two other passages said it was not matched. The data show it is close to the single edits but not to the combined package, so all three passages now say that. The numbers are generated macros with a new claim check. |
| The appendix section "Exploratory existing-data revision summaries" is now "Sensitivity analyses", rewritten as ordinary paper text, with labelled tables cited from the main text. | Its title and wording read like a response to reviewers. |
| Its three tables use the paper's treatment names ("Third-party endorsement", "Source citations", "Keyword stuffing" instead of "Endorsement", "Citation package", "Repeated keywords"), "Replication" instead of "Additional API", proper minus signs and no "−0.0". | Consistent terms across tables. |
| The appendix "Agentic search" is now "Searchable-corpus task", as in Section 5.3, and the deviation entry names MAI-Thinking-1 instead of "the noncompliant model". | The referee asked for each term to be defined once and used consistently. |
| Floats now stay within their own sections, the appendix starts on a new page, and the short Study 1 appendices open with a sentence. | Eight appendix tables had drifted to the last pages, away from their sections (the referee noted tables interrupting Appendix D). |

Checks after the changes: 162 of 162 claim checks pass (four new: three generated length macros and the placebo-length
check), 68 tests pass, and the paper builds without LaTeX warnings at 46 pages, one more than before (the research questions lengthen
the main text by about half a page, and the appendix now starts on a new page). The arXiv and journal files were
rebuilt.
