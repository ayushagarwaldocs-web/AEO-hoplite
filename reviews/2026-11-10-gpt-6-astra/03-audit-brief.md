# Brief for the code and statistics audit (sent 10 November 2026)

Sent verbatim as the first message of a second GPT-6 Astra thread (reasoning level Medium).

---

This is a code and statistics audit for a research paper. It is report-only: do not edit, commit or push anything (including the repository this workspace opened with), do not open pull requests, and do not call any language-model APIs. Run code only in a temporary directory.

Clone the public repository https://github.com/ayushagarwaldocs-web/AEO-hoplite into a temporary directory (branch main, commit d2bfbf2). The compiled paper is paper/main.pdf (extract its text with pdftotext or pypdf); compare what the paper says was done with what the code does.

Priority 1, Study 2 (experiments/exp2_content_treatments) and the paper build:
- analyze.py: effects, cluster_boot, sign_flip_p and holm, and how answers are filtered (error rows, duplicates, which conditions and models enter each estimate).
- analyze_robustness.py (the replication set, usage weighting by visit shares, minimum detectable effects), analyze_agentic.py, analyze_absorption.py, analyze_callouts.py and analyze_absorption_judge.py.
- The aeotools code that scores answers (brand mentioned, top pick, citations).
- paper/make_numbers.py and paper/check_claims.py: do the macros feed the text correctly, and does each claim check really test the sentence it is named after?
Then reproduce: install requirements.txt, run experiments/exp2_content_treatments/analyze_all.sh --no-pdf, and check whether paper/numbers.tex and the results files come out identical to the committed ones.

Priority 2, if time allows, Study 1: the robots.txt and access-barrier classification code (experiments/exp1_web_readiness and aeotools). Look for parsing mistakes such as user-agent group matching, Allow/Disallow precedence and wildcard handling. The raw crawl is not in the repository, so review the logic and test it on small examples you write.

Report in Markdown. For each finding give file:line, what is wrong, a concrete input or scenario that produces a wrong number, the likely effect on the paper's reported results (direction and rough size), and your confidence. Group findings as (a) bugs, (b) statistical choices a referee could question, with the alternative, and (c) mismatches between the paper's description and the code. Say plainly where you found nothing serious. Keep it under 2,500 words, and end with the full report as your final message.
