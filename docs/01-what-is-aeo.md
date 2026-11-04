# 1. What AEO is (and isn't)

**Answer Engine Optimization (AEO)** is the practice of making an organisation easy for AI
answer engines to find, understand, trust and cite: ChatGPT, Claude, Gemini, Perplexity,
Microsoft Copilot, Google's AI Overviews and AI Mode, and the assistants built on them.

You will see several names for overlapping ideas:

| Term | Where it comes from | Emphasis |
|---|---|---|
| **AEO** — Answer Engine Optimization | SEO industry, ~2017 (featured snippets, voice assistants), revived for LLM answers | Being *the answer* |
| **GEO** — Generative Engine Optimization | Aggarwal et al., *GEO*, KDD 2024 ([arXiv:2311.09735](https://arxiv.org/abs/2311.09735)) | Visibility inside generated responses |
| **LLMO / AI SEO / AI visibility** | Vendor and agency usage | Same goal, marketing labels |
| **C-SEO** — Conversational SEO | Puerto et al., *C-SEO Bench*, NeurIPS 2025 ([arXiv:2506.11097](https://arxiv.org/abs/2506.11097)) | Content edits aimed at conversational search |

This handbook uses **AEO** for the whole discipline and **GEO** when referring to the
research on content edits.

## Why it matters now

- ChatGPT reported roughly 900 million weekly users in early 2026; Google reports AI
  Overviews at around 2.5 billion monthly users and AI Mode above 1 billion (figures as
  announced; methods differ, so do not add them up).
- When Google shows an AI summary, people click a traditional result less often: 8% of
  visits versus 15% without one, and the links inside the summary get about 1% of clicks
  ([Pew Research, July 2025](https://www.pewresearch.org/short-reads/2025/07/22/google-users-are-less-likely-to-click-on-links-when-an-ai-summary-appears-in-the-results/)).
- AI referrals are still a small share of site traffic (estimates range from ~0.3% to ~1%),
  but buyers increasingly form their shortlist inside the answer, before any click.

The commercial consequence: **your brand can win or lose a decision without a visit ever
appearing in your analytics.**

## How AEO differs from SEO

| | SEO | AEO |
|---|---|---|
| Output | A ranked list of links | One synthesised answer with a few citations |
| Unit of competition | The page | The passage, the fact, the entity |
| Success | Rankings, clicks | Being mentioned, recommended, cited, and described accurately |
| Whose words count | Mostly yours (on-page) plus links | Mostly *other people's* (earned media, reviews, communities) |
| Stability | Fairly stable rankings | Probabilistic: the same prompt gives different answers |
| Measurement | Search Console, rank trackers | Prompt sampling, citation logs, a few first-party reports |

**Good SEO remains the foundation.** Answers grounded in live search sit on top of search
indexes (Google, Bing, Brave, engines' own crawlers). A page that is not crawled, indexed
and ranked for the sub-queries an assistant issues will not be retrieved, however well it
is written.

## The visibility vector

Being "visible in AI" is not one number. Following the multi-stage view argued in the 2026
GEO survey ([Martinez, arXiv:2607.14035](https://arxiv.org/abs/2607.14035)), track four stages:

1. **Discoverability** — can the engine crawl, index and retrieve you for the questions that
   matter? (Technical access, indexation, relevance.)
2. **Citation** — when retrieved, are you cited, and where in the answer?
3. **Absorption** — does your content actually shape the answer: its facts, wording, framing?
   ([Zhang et al., arXiv:2604.25707](https://arxiv.org/abs/2604.25707) show citation counts and
   influence diverge across engines.)
4. **Outcome** — do mentions turn into consideration, traffic, sign-ups or sales?

Most published "GEO tactics" act on stages 2–3 for content that is *already* in the
model's context. Most real-world losses happen at stage 1. This handbook covers all four.

## Two routes into an answer

| | Training memory (parametric) | Live retrieval (grounded) |
|---|---|---|
| What it is | What the model learned before its training cutoff | Pages the assistant searches and reads at answer time |
| How fast you can change it | Months: only when a new model ships | Days to weeks, once recrawled and reindexed |
| Main levers | Broad, consistent, long-lived presence in sources models learn from | Crawl access, indexation, ranking, extractable content, corroboration |
| Typical failure | Outdated or missing knowledge of your brand | Blocked crawler, JS-only page, not ranking for fan-out queries |

Both routes reward the same underlying asset: **clear, specific, consistent, corroborated
information about you, in many credible places.**

## What AEO cannot do

- **Guarantee placement.** No one controls generated answers; vendors promising "#1 in ChatGPT"
  are overselling.
- **Buy the organic answer.** Ads now exist in some engines, but they are labelled and
  separate from the answer (see [chapter 9](09-agents-commerce-and-apps.md)).
- **Escape competition.** When many competitors apply the same content tricks, the gains
  shrink toward zero ([C-SEO Bench](https://arxiv.org/abs/2506.11097);
  [Nestaas et al., ICLR 2025](https://arxiv.org/abs/2406.18382)). Durable advantage comes from
  being genuinely relevant and genuinely corroborated.

Next: [How answer engines work →](02-how-answer-engines-work.md)
