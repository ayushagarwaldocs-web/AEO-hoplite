# Perplexity

## Where answers come from

Perplexity is search-first: almost every answer is grounded in retrieved pages, from its own
index built by `PerplexityBot`, with live fetches by `Perplexity-User`. Answers typically
cite more sources than ChatGPT ([Zhang et al. 2026](https://arxiv.org/abs/2604.25707)).

## Crawlers and controls

| Token | Purpose | Notes |
|---|---|---|
| `PerplexityBot` | Search index | "not used to crawl content for AI foundation models" |
| `Perplexity-User` | User-initiated fetches | "generally ignores robots.txt rules" because a user requested the fetch |

IP ranges: `perplexity.ai/perplexitybot.json` and `perplexity.ai/perplexity-user.json`.
Changes can take up to 24 hours. Cloudflare's Bot Fight Mode may still challenge these bots
even with WAF allow rules. Source: [Perplexity bot docs](https://docs.perplexity.ai/guides/bots).

In 2025 Cloudflare publicly accused Perplexity of crawling sites that had blocked it;
Perplexity disputed the claims. Partly as a result, PerplexityBot is the most-blocked
answer crawler in our sample (10.4% of sites, against 4.7% for OAI-SearchBot).

## Optimisation priorities

1. **Allow `PerplexityBot`** (robots.txt and WAF, using the published IP ranges) if you want
   to be cited.
2. **Community presence:** Reddit is among the most-cited sources in Perplexity answers in
   2026 studies. Participate genuinely (chapter 6).
3. **Freshness:** Perplexity is often used for current information, so keep dated facts current.
4. **Breadth of corroboration:** because answers cite many sources, being mentioned across
   several of them (reviews, comparisons, news) compounds.

## Measurement

Referrals from `perplexity.ai`; `PerplexityBot` and `Perplexity-User` hits in logs. The Sonar
API can approximate grounded answers for sampling.
