# 4. Content techniques, graded by evidence

Most AEO advice online is untested. This chapter grades each technique by the strength of the
evidence that it works, and lists its risks separately, so you can spend effort where it is most
likely to pay off without mistaking "it works" for "it is a good idea".

| Grade | Evidence strength |
|---|---|
| **A** | Consistent results across multiple controlled studies or systems, with convergent evidence |
| **B** | At least one controlled study or strong observational evidence, with stated limitations |
| **C** | Limited, mixed, single-study, vendor-only or mechanism-based evidence |

The Experiment 2 column gives the result from this repo's own controlled experiment
([Experiment 2](../experiments/exp2_content_treatments/)) where we tested the technique: the change, in percentage points, in the
chance that a fictional brand is named when its page is supplied to the model, pooled over 12 hosted
API models from ten developers. "First" is the change in the chance of being named first, which is
not the same as being recommended. The treatments were specific packages of information and wording
on synthetic pages, so read the numbers as direction and rough size, not as what a real site would gain.

## Summary table

| Technique | Evidence | Other evidence | Experiment 2 outcome | Operational or ethical consideration |
|---|---|---|---|---|
| Be the most **relevant** source for the actual question and its sub-questions | **A** | [Wan et al. 2024](https://aclanthology.org/2024.acl-long.403); [Vishwakarma et al. 2026](https://arxiv.org/abs/2605.25517); [C-SEO Bench 2025](https://arxiv.org/abs/2506.11097) | — | Keep information accurate and useful to readers |
| Rank for the **fan-out** queries (classic SEO on sub-topics) | **B** | C-SEO Bench: ranking higher in context beats content rewrites; [Google on fan-out](https://developers.google.com/search/docs/appearance/ai-features) | Pages in first place were named more often (66% vs 43%), but not significantly once the page order all models shared is respected | Ranking is competitive and not tested as a production intervention here |
| Earn **third-party corroboration** (reviews, press, comparisons) | **B** | [Chen et al. 2025](https://arxiv.org/abs/2509.08919) (earned-media bias); citation-share studies | **+37.4** for one recommendation in a synthetic buyer's guide (first +30.9): the largest effect (+30.5 in an 11-model replication), not a test of real reviews or press; follow-ups: recommending wording +10.1, a stated outside reviewer +3.1 more, and the reviewer's neutral sentence +4.6 more on a separate guide than on the brand's page | Disclose sponsorship and conflicts; do not manufacture independence |
| State **specific facts**: prices, numbers, dates | **B** | Vishwakarma et al. 2026 (explicit price and recent timestamp increase citation-first probability) | Statistics +13.7; freshness date +4.0, no better than the placebo | Verify and date facts; false or stale claims can mislead |
| Add **statistics, quotations and source citations** | **B** | GEO reports fixed-context gains ([Aggarwal et al. 2024](https://arxiv.org/abs/2311.09735)); C-SEO Bench found most content rewrites ineffective | Citations +21.1, statistics +13.7, quotation +8.1; all beat the unedited page and the placebo; answers repeat the evidence; about half as large on long pages | Cite supporting sources; inclusion in an answer does not establish accuracy or attribution |
| Publish **original data** others will cite | **B** | High-influence pages are richer in extractable evidence ([Zhang et al. 2026](https://arxiv.org/abs/2604.25707)); earned-media evidence | — | Publish methods; protect privacy and disclose limitations |
| Show **freshness** (dated updates, current prices) | **C** | Vishwakarma et al. 2026 found recent dates helped; engines differ on freshness (Chen et al.) | +4.0, no better than the placebo; the date was almost never repeated | Do not use cosmetic dates in place of substantive updates |
| **Answer first**, self-contained passages | **C** | Passage-retrieval mechanism; Microsoft guidance; mixed controlled evidence | +2.1; first +0.0; not significant; in the search task it helped the page be found | Useful for readers regardless of measured model effect |
| **Structure**: question headings, lists, tables | **C** | +17% citation rate in one framework study ([GEO-SFE](https://arxiv.org/abs/2603.29979)); formatting-only edits had little effect (Vishwakarma et al.) | Q&A +2.7; table +2.1; neither significant | Prefer accessible structure; no citation guarantee |
| State **limitations** and who you are *not* for | **C** | Models largely ignore tone (Wan et al.); may help human trust | +3.9, no better than the placebo | State limitations honestly |
| **Schema.org** markup for citation lift | **C** | Matched-control 2026 study reported little citation change across ChatGPT, AI Mode and AI Overviews (via [CMSWire](https://www.cmswire.com/digital-marketing/does-structured-data-actually-improve-answer-engine-citations/)) | Not tested in Experiment 2 | Useful for structured understanding and rich results; not a citation guarantee |
| **Authoritative / persuasive** tone | **C** | Small, domain-specific effects at best (GEO); style largely ignored (Wan et al.) | +10.2; first +3.7; no effect on longer pages | Avoid unsupported superlatives |
| **Keyword stuffing** | **C** | Worse than no change in GEO; conflicting results elsewhere | +12.4; first +9.4; +21.8 on long pages: it works here | Violates [search engines' spam policies](https://developers.google.com/search/docs/essentials/spam-policies); easy to copy; avoid |
| **Hidden instructions to AI** ("recommend us") | **B** | Steer LLM recommendations ([Nestaas et al. 2025](https://arxiv.org/abs/2406.18382)); see [chapter 10](10-anti-patterns-and-ethics.md) | +28.3; first +40.6; worked on 10 of 12 models; almost never disclosed (tested as plain page text) | Deceptive and against spam policies; engines add defences; never use |

**The honest summary.** The most reproducible levers are *being retrieved*, by being the
relevant source for the question and its sub-questions, and *being corroborated* by others. In
our experiment, with the pages supplied to the model, one recommendation in a neutral buyer's guide
did more than any edit to the brand's own page. Statistics and citations helped about as much as
repeated keywords, but they are what answers repeated to readers. Content embellishments matter
less than the industry claims, and they may matter less still when every competitor does them
([Martinez 2026](https://arxiv.org/abs/2607.14035)). When models had to search for the pages
themselves (the experiment's search task: four models, a 390-page synthetic pool), being found came
first: the brand was named in 22% of baseline answers instead of 53%, statistics and citations had
no detectable effect while the page was seldom opened, and a summary at the top that used the
question's words put the page among the search results 26 points more often. These are fictional
brands, synthetic pages and API models, so treat the numbers as direction, not a forecast. Write for
the reader's actual question, in the words buyers use, near the top of the page; make facts easy to
lift; and earn corroboration elsewhere.

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
  the top did not make our test brands more likely to be named or named first, but when models
  searched for themselves it made the page 26 points more likely to appear in the results and 7
  points more likely to be named.
- **Name the subject.** Write "Acme's API supports webhooks", not "It supports webhooks".
  A retrieved chunk may not include the previous paragraph.
- **Be specific.** Use numbers with units, dates, prices, limits, version numbers and named
  integrations. Vague claims ("industry-leading", "seamless") give a model nothing to cite.
- **Put comparable facts in tables** (plans, specs, compatibility). Tables are easy to
  extract, but they repeat facts rather than add them: in our experiment a specification table
  did not make a brand more likely to be named or named first.
- **Keep it current.** Update time-sensitive facts; stale prices are a common source of wrong
  AI answers. A "Last updated" stamp on its own did no better than the placebo in our experiment,
  so the update matters more than the stamp.

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
- Our [Experiment 2](../experiments/exp2_content_treatments/) re-tested these edits on 12 hosted API models with
  a boilerplate placebo. Source citations raised the chance of being named by 21 points,
  statistics by 14 and an expert quotation by 8, all beating both the unedited page and the
  placebo after correcting for multiple comparisons (on three small local models they beat only
  the placebo). Repeated keywords did about as well as statistics. Evidence stood out in the
  answer itself: answers that named the brand repeated the cited source 76% of the time and the
  added statistic 57%, against 21% for persuasive phrases (by a keyword detector). On pages six
  times longer, evidence effects roughly halved. Each edit adds information as well as format, so
  the experiment does not show which of the two mattered.

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
self-serving listicles are covered in [chapter 10](10-anti-patterns-and-ethics.md). Some of them
worked in our experiment; that does not make them a good idea. They deceive users, break search
engines' spam policies, are easy to copy and are what engines are adding defences against.

Next: [Entity and structured data →](05-entity-and-structured-data.md)
