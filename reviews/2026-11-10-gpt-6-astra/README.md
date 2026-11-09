# Review log: GPT-6 Astra, 10 November 2026

The author asked a second model to review the paper and its analysis code, first as a referee and a source of ideas,
then to make the changes it recommended. This folder keeps every brief, report and decision so the revision can be
traced later.

- **Reviewer:** GPT-6 Astra (OpenAI), run as agent threads on the Hoplite coding-agent platform. It read the public
  repository at commit `d2bfbf2` (the version on GitHub on 10 November 2026), had no API keys, called no language
  models and did not have the raw Study 1 crawl.
- **Coordinator:** Claude (Anthropic), which wrote the code and drafted the paper. It wrote the briefs, copied the
  reports here, and applies and checks the changes before anything is committed.
- The paper itself does not mention the platform. Its AI-use declaration names GPT-6 Astra as a reviewer and editor.

## Files

| File | What it is |
|---|---|
| [01-review-brief.md](01-review-brief.md) | What Astra was asked for the referee review |
| [02-review-report.md](02-review-report.md) | Astra's referee report, verbatim (verdict: major revision) |
| [03-audit-brief.md](03-audit-brief.md) | What Astra was asked for the code and statistics audit |
| [04-audit-report.md](04-audit-report.md) | Astra's audit report, verbatim (main finding: the pooled position test) |
| [05-change-request.md](05-change-request.md) | What Astra was then asked to change, with the author's decisions |

Still to come: Astra's own account of what it changed, and the checks run on the changes here, with the decision on
each point.

## The author's decisions (10 November 2026)

- Goal: "do what makes the paper most valuable, publishable in journal": make every change the existing data
  support, and list what would need new data.
- New title: *Crawler Access and Content Effects in Answer Engine Optimization: A Website Audit and Controlled
  Experiments*. Astra proposed *Crawler Access Policies and Brand Mentions in AI Answers: A Website Audit and Controlled
  Content Experiments*; the author kept "Answer Engine Optimization", the term readers search for.
- Remove the numerical access-versus-edit comparison (fixing access worth a median 2.2 times a content edit) and the
  cost ranking, as Astra advised. The case for access rests on the searchable-corpus experiment instead.

## How the runs went

- Two first attempts from the Hoplite command line failed before doing any work: the organisation the CLI was signed
  in to had no working sandbox. Each cost about $0.11.
- The review and the audit then ran in the author's new Hoplite workspace, at the web app's default reasoning level
  (Medium), for about 6 and 20 minutes. The change request went to the audit thread at reasoning level High.
