# Brief for the referee review (sent 10 November 2026)

Sent verbatim as the first message of a new GPT-6 Astra thread (reasoning level Medium, the web app's default).

---

You are reviewing an unpublished research paper as an expert referee and as a collaborator who suggests improvements. This is a review task: do not edit, commit or push anything (including the repository this workspace opened with), do not open pull requests, and do not call any language-model APIs.

Get the paper: clone the public repository https://github.com/ayushagarwaldocs-web/AEO-hoplite into a temporary directory (branch main, commit d2bfbf2) and read the compiled paper, paper/main.pdf (40 pages), by extracting its text with pdftotext or pypdf. The LaTeX sources in paper/ take every number from macros in paper/numbers.tex, so use the PDF for the numbers. The rest of the repository holds the code and data behind the paper; consult it when you need to check a method or a table, but the review is of the paper.

The paper is "The Discoverability Gap: Access Barriers and Content Effects in Answer Engine Optimization" by a single independent researcher. It will be posted on arXiv (cs.IR) and submitted to Information Processing & Management (Elsevier).

Write a report in Markdown with these sections:
1. Verdict: what an IP&M referee would likely recommend (accept, minor revision, major revision or reject), and the two or three reasons that would drive that recommendation.
2. Major concerns: problems with design, validity, statistics, interpretation or framing that a referee would raise. For each, give where it is (section and page), the problem, why it matters, and the cheapest fix. Say whether the fix needs new data or model runs, or can be made with the existing data and text.
3. Overclaims and inconsistencies: sentences whose wording goes beyond the reported evidence, and numbers or statements that disagree between the abstract, sections, figures and tables. Quote briefly and give pages.
4. Ideas to strengthen the paper: further analyses possible with the existing data, a sharper statement of the contribution, what to cut, merge or move to the appendix, and a better title or abstract if you have one. Rank the ideas by value for acceptance relative to effort.
5. Related work a referee would expect that is missing: name the work and say why it matters. Mark anything you are not sure exists as uncertain; never invent a citation.
6. Minor points: clarity, terminology, figures, tables and typos.

Be specific and candid, and leave out praise. Keep the report under 3,000 words. Where you are unsure, say so. End with the full report as your final message.
