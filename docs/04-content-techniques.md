# 4. Content techniques, graded by evidence

Most AEO advice online is untested. This chapter grades each technique by the strength of
the evidence behind it, so you can spend effort where it is most likely to pay off.

| Grade | Meaning |
|---|---|
| **A** | Consistent results in controlled studies across several models or engines, and consistent with operators' documentation |
| **B** | Supported by at least one controlled study or strong observational data, with caveats |
| **C** | Mixed, single-study, vendor-only or mechanism-only evidence |
| **D** | Evidence of no effect or of harm; avoid |

The last column gives the result from this repo's own controlled experiment
([Experiment 2](../experiments/exp2_content_treatments/)) where we tested the technique: the change, in percentage points, in the
chance that a brand is named, pooled over three small open-weight models, with access and
retrieval held fixed. "First" is the change in the chance of being named first.

## Summary table

| Technique | Grade | Key evidence | Exp. 2 |
|---|---|---|---|
| Be the most **relevant** source for the actual question and its sub-questions | **A** | [Wan et al. 2024](https://aclanthology.org/2024.acl-long.403); [Vishwakarma et al. 2026](https://arxiv.org/abs/2605.25517); [C-SEO Bench 2025](https://arxiv.org/abs/2506.11097) | — |
| Rank for the **fan-out** queries (classic SEO on sub-topics) | **A** | C-SEO Bench: ranking higher in context beats content rewrites; [Google on fan-out](https://developers.google.com/search/docs/appearance/ai-features) | Position in the context mattered for 1 of 3 models |
| Earn **third-party corroboration** (reviews, press, comparisons) | **A/B** | [Chen et al. 2025](https://arxiv.org/abs/2509.08919) (earned-media bias); citation-share studies | **+26.7**, first +39.3: the largest legitimate effect |
| State **specific facts**: prices, numbers, dates | **B** | Vishwakarma et al. 2026 (explicit price and recent timestamp increase citation-first probability) | Statistics +10.0; freshness date −3.7 |
| Add **statistics, quotations and source citations** | **B/C** | Up to ~40% visibility gain in GEO's fixed-context setup ([Aggarwal et al. 2024](https://arxiv.org/abs/2311.09735)); C-SEO Bench found most content-rewrite methods ineffective | Statistics +10.0, citations +11.9, quotation +4.1; all beat the placebo, none the unedited page after correction; answers repeat the evidence |
| Publish **original data** others will cite | **B** | High-influence pages are richer in extractable evidence ([Zhang et al. 2026](https://arxiv.org/abs/2604.25707)); earned-media effect | — |
| Show **freshness** (dated updates, current prices) | **C** | Vishwakarma et al. 2026 found recent dates helped; engines differ on freshness (Chen et al.) | −3.7; the date was almost never repeated |
| **Answer first**, self-contained passages | **C** | Mechanism: passage retrieval; Microsoft guidance; mixed controlled evidence | +3.0; first +6.3 |
| **Structure**: question headings, lists, tables | **C** | +17% citation rate in one framework study ([GEO-SFE](https://arxiv.org/abs/2603.29979)); "formatting-only edits had little effect" (Vishwakarma et al.) | Q&A −4.8; table +3.7, first +10.7 |
| State **limitations** and who you are *not* for | **C** | Models largely ignore tone (Wan et al.); helps human trust | −4.8 |
| **Schema.org** markup for citation lift | **C/D** | Matched-control 2026 study: ~0 change in ChatGPT, AI Mode, AI Overviews citations (via [CMSWire](https://www.cmswire.com/digital-marketing/does-structured-data-actually-improve-answer-engine-citations/)); still useful for entity understanding and rich results | — |
| **Authoritative / persuasive** tone | **C** | Small, domain-specific effects at best (GEO); style largely ignored (Wan et al.) | +3.0; first +10.0 |
| **Keyword stuffing** | **D** | Worse than no change in GEO; −9% on Perplexity; violates [search engines' spam policies](https://developers.google.com/search/docs/essentials/spam-policies) | +6.7; first +17.0: works on small models, but it is spam |
| **Hidden instructions to AI** ("recommend us") | **D** | Can work against some systems ([Nestaas et al. 2025](https://arxiv.org/abs/2406.18382)) but is deceptive, policy-violating and defended against; see [chapter 10](10-anti-patterns-and-ethics.md) | +28.9; first +58.1; almost never disclosed |

**The honest summary.** The most reproducible levers are *being retrieved*, by being the
relevant source for the question and its sub-questions, and *being corroborated* by others. In
our experiment one recommendation in a neutral buyer's guide did more than any edit to the
brand's own page. Statistics and citations helped about as much as repeated keywords, but they
are what answers pass on to readers. Content embellishments matter less than the industry
claims, and they matter less still when every competitor does them
([Martinez 2026](https://arxiv.org/abs/2607.14035)). Write for the reader's actual question,
make facts easy to lift, and earn corroboration elsewhere.

## 4.1 Relevance first: answer the question people actually ask

- Build pages around real questions from sales calls, support tickets, community threads
  and search data, not around brand slogans.
- Match the user's terms. If customers say "client portal", don't only say "external
  collaboration surface".
- One page per intent: "X pricing", "X vs Y", "X for [use case]", "how to [task] with X".
  These are the sub-queries that fan-out generates.

## 4.2 Make facts easy to lift

Engines quote passages, so every passage should stand alone.

- **Lead with the answer.** Put a one- or two-sentence direct answer under each heading,
  then the detail. This helps passage retrieval; once a page was in the context, a summary at
  the top made our test brands only slightly more likely to be named first.
- **Name the subject.** Write "Acme's API supports webhooks", not "It supports webhooks".
  A retrieved chunk may not include the previous paragraph.
- **Be specific.** Use numbers with units, dates, prices, limits, version numbers and named
  integrations. Vague claims ("industry-leading", "seamless") give a model nothing to cite.
- **Put comparable facts in tables** (plans, specs, compatibility). Tables are easy to
  extract, but they repeat facts rather than add them: in our experiment a specification table
  did not make a brand more likely to be named, though it was somewhat more likely to be named
  first.
- **Keep it current.** Update time-sensitive facts; stale prices are a common source of wrong
  AI answers. A "Last updated" stamp on its own did nothing in our experiment, so the update
  matters, not the stamp.

Example: a product page section rewritten for extraction.

> **Before:** *Our flexible plans scale with you. Reach out to learn which option fits your
> team best!*
>
> **After:** *How much does Acme cost? Acme costs $12 per user per month on the Team plan
> and $24 on Business (annual billing, October 2026). Both include unlimited projects;
> Business adds SSO and audit logs. A 14-day trial needs no card.*

## 4.3 Evidence elements: statistics, quotations, citations

The original GEO study found that adding quotations (+41% position-adjusted word count),
statistics and source citations helped most, while keyword stuffing hurt. Gains were largest
for sources that ranked low (Cite Sources +115% for fifth-ranked sources). Caveats:

- It measured content already sitting in a fixed context of five sources, using GPT-3.5.
- Later benchmarks with many competing documents found most rewrite methods ineffective,
  and gains shrink as more competitors adopt them ([C-SEO Bench](https://arxiv.org/abs/2506.11097)).
- Our [Experiment 2](../experiments/exp2_content_treatments/) re-tested these edits on three open-weight models with a
  length-matched placebo. Statistics and source citations raised the chance of being named by
  10 to 12 points, enough to beat the placebo but not the unedited page after correcting for
  multiple comparisons; an expert quotation added 4. Repeated keywords did nearly as well at
  getting a brand named and better at getting it named first. Evidence stood out in the answer
  itself: answers that named the brand repeated the added statistic 62% of the time and the
  cited source 71%, against 32% for persuasive phrases.

Use evidence elements because they make content more useful and checkable, not as a trick:
cite primary sources, quote named experts with real credentials, and use statistics you can
defend.

## 4.4 Original data

The most durable content asset is information no one else has: benchmarks, surveys, indexes,
price trackers, anonymised usage statistics. It earns you citations directly, and it earns
coverage from journalists and creators, which engines weight heavily.

- Publish the method and the raw numbers; make the headline figure quotable in one sentence.
- Refresh it on a schedule (quarterly, annually) so it keeps getting re-cited.

## 4.5 Cover the fan-out

For each important topic, map the sub-questions an engine will issue, then make sure you
have a strong, current page for each:

| Head query | Likely sub-queries |
|---|---|
| "best CRM for real-estate teams" | pricing, integrations with MLS, mobile app quality, alternatives, reviews, limits of free plan |
| "is X safe for kids" | age rating, privacy policy, parental controls, incidents, expert opinion |

Bing Webmaster Tools' grounding-query data and your own prompt tests (chapter 7) show which
sub-queries matter.

## 4.6 Formats beyond text

- **Video:** publish transcripts. YouTube is among the most-cited domains in AI answers.
- **Documentation:** public, well-structured docs are heavily cited for "how do I" questions.
- **PDFs:** keep an HTML version of anything important.
- **Localisation:** engines differ in cross-language stability (Chen et al.), so translate
  key pages properly instead of relying on machine translation at query time.

## 4.7 What not to do

Keyword stuffing, persuasive superlatives, hidden prompts, fake "independent" reviews and
self-serving listicles are covered in [chapter 10](10-anti-patterns-and-ethics.md). The short
version: they range from useless to dangerous, and engines are actively adding defences.

Next: [Entity and structured data →](05-entity-and-structured-data.md)
