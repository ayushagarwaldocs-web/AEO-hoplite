# ChatGPT (OpenAI)

## Where answers come from

- **Training memory** for questions that don't trigger search.
- **ChatGPT search**: OpenAI's own index built by `OAI-SearchBot`, plus third-party search
  providers (Bing has been the main partner) and content from licensing partners.
- **Live fetches** by `ChatGPT-User` when a user's request needs a specific page, including
  GPT Actions and agent tasks.

## Crawlers and controls

| Token | Purpose | Notes |
|---|---|---|
| `GPTBot` | Training | Disallowing it "indicates a site's content should not be used in training" |
| `OAI-SearchBot` | Search index | Opted-out sites "will not be shown in ChatGPT search answers" (may still appear as navigational links) |
| `ChatGPT-User` | User-initiated fetches | "robots.txt rules may not apply"; not used to decide search eligibility |
| `OAI-AdsBot` | Ad landing-page review | Data not used for training |

IP ranges: `openai.com/gptbot.json`, `openai.com/searchbot.json`, `openai.com/chatgpt-user.json`.
robots.txt changes take about 24 hours for search. Source: [OpenAI crawler docs](https://developers.openai.com/api/docs/bots).

## Optimisation priorities

1. **Allow `OAI-SearchBot` and `ChatGPT-User`**, at the edge as well as in robots.txt. Block
   `GPTBot` separately if you want a training opt-out.
2. **Be strong in Bing:** Bing Webmaster Tools, IndexNow, and clean indexation of sub-topic pages.
3. **Write for absorption.** ChatGPT cites fewer sources than Perplexity or Google, but each
   cited page shapes more of the answer, so complete, well-structured pages with definitions,
   numbers and comparisons win ([Zhang et al. 2026](https://arxiv.org/abs/2604.25707)).
4. **Earn the sources ChatGPT favours:** Wikipedia/Wikidata accuracy, authoritative
   publications, LinkedIn (cited in a large share of ChatGPT search answers in 2026 studies),
   and reviews.
5. **Commerce:** submit a product feed following OpenAI's spec; consider the Agentic Commerce
   Protocol through your commerce platform.
6. **Apps:** a ChatGPT app (Apps SDK, built on MCP) puts live data and actions inside ChatGPT.

## Measurement

- Referrals arrive from `chatgpt.com`, with `utm_source=chatgpt.com` on cited links.
- `ChatGPT-User` hits in server logs signal real-time demand for specific pages.
- OpenAI offers no publisher citation dashboard as of November 2026; use prompt sampling.

## Ads

Labelled "Sponsored" ads below answers since February 2026 (US, Free and Go tiers),
self-serve since May 2026, with product-feed ads from June. OpenAI states ads don't influence
answers.
