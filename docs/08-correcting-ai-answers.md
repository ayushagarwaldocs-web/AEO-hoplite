# 8. Correcting what AI gets wrong about you

Wrong prices, discontinued products, an old CEO, a resolved incident presented as current, a
competitor's feature attributed to you: these are the most urgent AEO problems because they
cost sales and trust directly.

## 8.1 Audit

Run a brand-accuracy prompt set every month and after any major change:

- "What is [brand]?", "How much does [product] cost?", "Who runs [brand]?",
  "Is [brand] safe / legit / good?", "What are the downsides of [product]?",
  "[brand] vs [competitor]"
- Ask each engine with search on and, where possible, off (training memory only)
- Record every factual claim and mark it correct, outdated, wrong or unverifiable

## 8.2 Diagnose: retrieval or memory?

| Symptom | Likely route | Where to fix |
|---|---|---|
| Wrong answer **with a citation** | Retrieval | The cited page (yours or a third party's) |
| Wrong answer, **no citation**, search off | Training memory | Long-run web consensus; next model generation |
| Wrong only in one engine | That engine's index | Its crawler access, its sources (see [engines/](../engines/README.md)) |
| Right on your site, wrong elsewhere | Third-party drift | Profiles, directories, old press |

## 8.3 Fix at the source

1. **Your own pages first.** Make the correct fact explicit, dated and easy to quote; remove
   or redirect outdated pages; update structured data and `dateModified`.
2. **Third-party sources.** Update profiles you control (directories, review platforms, app
   stores, Crunchbase, LinkedIn); politely request corrections from publishers with evidence;
   on Wikipedia, use the talk page and disclose your affiliation.
3. **Publish a clear statement** for recurring confusion: "Acme discontinued Widget Classic
   in March 2026; Widget 2 replaces it" or "Acme is not affiliated with Acme Corp (UK)".
   Statements like these are easy to retrieve and cite.
4. **Request recrawl and reindexing:** IndexNow for Bing, URL Inspection in Google Search
   Console, and sitemap `lastmod`.
5. **Use in-product feedback** (thumbs-down with an explanation) for egregious errors. It is
   low-leverage on its own but documents the problem.

## 8.4 Expect different timelines

- **Retrieval-grounded answers:** typically days to a few weeks after recrawl.
- **Training memory:** only when models are retrained or updated, often months. Until then,
  make sure search-triggering prompts (prices, "latest", "current") retrieve your corrected
  pages.

## 8.5 Serious harms

For defamatory, dangerous or legally significant errors, keep dated evidence (prompts,
answers, screenshots) and use the provider's official reporting or legal channels. Do not
try to "fix" an answer by planting hidden instructions or fake corroboration; it backfires
(chapter 10).

Next: [Agents, commerce and apps →](09-agents-commerce-and-apps.md)
