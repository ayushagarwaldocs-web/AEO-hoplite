# 3. Technical access: be fetchable, readable and indexable

Nothing else matters if an engine cannot reach your content. This is also where our own
measurement found the most avoidable losses (Experiment 1, below).

## 3.1 Know the three kinds of AI agent

Every major AI company now separates crawlers by purpose. Each robots.txt token is
independent: blocking one does not block the others.

| Operator | Training | Search index (answers) | Live fetch for a user |
|---|---|---|---|
| OpenAI | `GPTBot` | `OAI-SearchBot` | `ChatGPT-User` |
| Anthropic | `ClaudeBot` | `Claude-SearchBot` | `Claude-User` |
| Perplexity | (none) | `PerplexityBot` | `Perplexity-User` |
| Google | `Google-Extended` (token only) | `Googlebot` (feeds AI Overviews and AI Mode) | (none) |
| Apple | `Applebot-Extended` (token only) | `Applebot` | (none) |
| Meta | `Meta-ExternalAgent` | (none) | `Meta-ExternalFetcher` |
| Common Crawl | `CCBot` | (none) | (none) |

Sources: [OpenAI](https://developers.openai.com/api/docs/bots),
[Anthropic](https://support.claude.com/en/articles/8896518),
[Perplexity](https://docs.perplexity.ai/guides/bots),
[Google](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers).
The full registry, with docs links, lives in [`aeotools/bots.py`](../aeotools/bots.py).

What blocking does, in the operators' own words:

- OpenAI: "Sites that are opted out of OAI-SearchBot will not be shown in ChatGPT search
  answers" (they may still appear as navigational links). GPTBot only governs training.
- Anthropic: blocking Claude-User "prevents our system from retrieving your content in
  response to a user query"; blocking Claude-SearchBot "may reduce your site's visibility
  and accuracy in user search results."
- Google: Google-Extended "does not impact a site's inclusion in Google Search." AI Overviews
  and AI Mode use normal Search crawling and indexing, controlled by Googlebot and snippet
  controls.
- User-triggered fetchers may not honour robots.txt: Perplexity says Perplexity-User
  "generally ignores robots.txt rules"; OpenAI says robots.txt rules "may not apply" to
  ChatGPT-User.

## 3.2 Choose a robots.txt policy on purpose

Ready-to-edit files are in [`templates/`](../templates/):

| Goal | Template | Trade-off |
|---|---|---|
| Maximum AI visibility | [`robots-allow-all.txt`](../templates/robots-allow-all.txt) | Your content may be used for training |
| **Appear in AI answers, opt out of training** (most common for brands) | [`robots-answers-not-training.txt`](../templates/robots-answers-not-training.txt) | Future models learn about you only from third parties |
| Opt out of AI entirely | [`robots-block-ai.txt`](../templates/robots-block-ai.txt) | You disappear from AI answers that respect robots.txt |

Rules that trip people up:

- **The `*` group catches every unnamed bot.** A site with `User-agent: *` / `Disallow: /`
  plus an allowlist for Googlebot and Bingbot also blocks every AI search bot it forgot to
  name. In our sample, about one in five retrieval blocks came from such inherited rules rather
  than a named rule.
- **Deprecated tokens do nothing.** `anthropic-ai` and `Claude-Web` are retired; name
  `ClaudeBot`, `Claude-SearchBot` and `Claude-User`.
- **A 5xx or timeout on robots.txt means "disallow everything"** to compliant crawlers
  ([RFC 9309](https://www.rfc-editor.org/rfc/rfc9309)). Monitor it like an API.
- **Changes are not instant.** OpenAI and Perplexity both say about 24 hours.
- **Check every subdomain** you care about (docs., help., shop., blog.); each has its own
  robots.txt.

## 3.3 Check the layer that robots.txt cannot see: CDN and WAF

Bot management at the edge often blocks AI crawlers before robots.txt is consulted.

- Cloudflare blocked AI crawlers by default for new sites from 2025 and in 2026 introduced
  separate **Search / Agent / Training** categories; secondary reports describe new
  defaults (from 15 September 2026) that block Training and Agent bots on ad-supported pages.
  Mixed-use crawlers such as Googlebot are treated by the strictest applicable rule, so check
  your settings in AI Crawl Control.
- Allow verified crawlers by **user agent and published IP ranges**: OpenAI
  (`openai.com/searchbot.json`, `gptbot.json`, `chatgpt-user.json`), Anthropic
  (`claude.com/crawling/bots.json`), Perplexity (`perplexity.ai/perplexitybot.json`,
  `perplexity-user.json`).
- In our measurement, about one in five large organisational sites answered a plainly
  declared research crawler with a 403, 429 or challenge page, whatever user agent it
  sent. Verified AI crawlers may be allowlisted where we were not, so treat that as an
  upper bound. Still, check your own logs: are AI agents getting 200s?

Run the audit tool against your own site to see both layers at once:

```bash
python -m aeotools.audit www.example.com --render
```

## 3.4 Serve content as HTML

Most AI crawlers download raw HTML and do not run JavaScript. If your key copy, prices,
specs or FAQs are injected client-side, they are invisible to those crawlers.

- Use server-side rendering or static generation for content pages.
- Test: `curl -A "Mozilla/5.0 (compatible; GPTBot/1.4; +https://openai.com/gptbot)" https://example.com/page`
  and search the output for your key sentences. The audit tool's `--render` flag compares
  raw and rendered word counts.
- Keep important facts in text, not only in images, PDFs, carousels, tabs that load on
  click, or video without a transcript.

## 3.5 Get indexed where the answers come from

- **Google:** Search Console, XML sitemaps, internal links. Google states there are no extra
  requirements for AI Overviews and AI Mode beyond being indexed and snippet-eligible.
- **Bing:** Bing Webmaster Tools and [IndexNow](https://www.indexnow.org/). Bing grounds
  Copilot and is a major source for ChatGPT search. Its AI Performance report (preview since
  February 2026) shows how often Copilot and Bing's AI answers cite your pages.
- **Brave:** Brave Search runs its own index, reportedly used by several AI products.
  Check that you appear for your brand and category queries there.
- Keep `lastmod` in sitemaps accurate. Answer engines favour fresh pages for time-sensitive
  questions, and recrawl scheduling uses these hints.

## 3.6 Snippet and preview controls

- Google: `nosnippet`, `data-nosnippet`, `max-snippet` and `noindex` limit what Search,
  including AI features, can show. Use `data-nosnippet` surgically, for example on
  outdated disclaimers, rather than page-wide.
- Bing has documented `NOCACHE` and `NOARCHIVE` as controls over use in its chat answers.
  Check current guidance before relying on them.
- `noai` / `noimageai` meta tags are non-standard; no major engine documents honouring
  them for answers.

## 3.7 Emerging preference signals

- **IETF AI Preferences (AIPREF).** Working-group drafts define a vocabulary for usage
  preferences ([draft-ietf-aipref-vocab](https://datatracker.ietf.org/doc/html/draft-ietf-aipref-vocab-07))
  and a way to attach it via robots.txt and a `Content-Usage` HTTP header
  (draft-ietf-aipref-attach). Google says it intends to support the AIPREF signal in early
  2027. Not yet an RFC.
- **Cloudflare Content Signals** (`Content-Signal: search=yes, ai-train=no` in robots.txt),
  seen on 3.6% of reachable sites in our sample.
- **llms.txt** ([llmstxt.org](https://llmstxt.org/)): a Markdown guide to your site for LLMs.
  Adoption is real (23% of our sample, around half of SaaS, AI and fintech sites), but evidence
  that AI *search* uses it is weak. One 2026 analysis of server logs found most llms.txt files
  received no requests at all, and AI retrieval bots made about 1% of the requests that did
  arrive ([Ahrefs](https://ahrefs.com/blog/llmstxt-study/)). It is most useful for developer
  documentation that coding agents read. Cheap to add, low expected value for AEO.

## 3.8 What we measured (Experiment 1)

We audited 569 prominent organisational websites across 22 sectors in November 2026
(method and data: [`experiments/exp1_web_readiness`](../experiments/exp1_web_readiness/)).
Among the 550 with a reachable robots.txt:

| Finding | Share |
|---|---|
| Open to every AI crawler we track | 82.2% |
| Block at least one training crawler | 17.1% |
| Block at least one **answer** crawler (search index or live fetch) | 12.2% |
| Block every answer crawler | 3.1% |
| GPTBot blockers that still allow OAI-SearchBot (training opt-out done right) | 59.4% |
| Answer-crawler blocks inherited from the `*` group, not a named rule | 19.4% |
| Publish a valid llms.txt | 23.0% |
| Homepage requests refused or challenged at the edge (403/429/challenge), whatever the user agent | 18.6% of 532 |
| Rendered homepages with under half their text present without JavaScript | 11.2% of 269 |
| Homepages declaring an `Organization`-type JSON-LD entity | 54.1% of 412 |

Block rates by agent: PerplexityBot 10.4%, Claude-SearchBot 7.3%, ChatGPT-User 6.9%,
OAI-SearchBot 4.7%, compared with 11.6% for GPTBot and 13.3% for ClaudeBot. See the paper for
sector breakdowns, rendering results and limitations.

Next: [Content techniques →](04-content-techniques.md)
