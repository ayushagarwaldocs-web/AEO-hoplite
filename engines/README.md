# Engine-by-engine guides

The fundamentals in [`docs/`](../docs/) apply everywhere. These guides cover what differs per
engine: where its answers come from, which crawlers and controls matter, what it tends to
cite, and how to measure it. Facts were checked against operator documentation in November
2026; anything second-hand is marked as reported.

| | [ChatGPT](chatgpt.md) | [Claude](claude-anthropic.md) | [Google AI](google.md) | [Perplexity](perplexity.md) | [Copilot](copilot.md) |
|---|---|---|---|---|---|
| **Grounding index** | OAI-SearchBot + third-party search (Bing has been the main partner) | Claude-SearchBot + a search provider (reportedly Brave) | Google Search index | Own index (PerplexityBot) | Bing |
| **Answer crawlers to allow** | `OAI-SearchBot`, `ChatGPT-User` | `Claude-SearchBot`, `Claude-User` | `Googlebot` | `PerplexityBot`, `Perplexity-User` | `Bingbot` |
| **Training control** | `GPTBot` | `ClaudeBot` | `Google-Extended` (Gemini; not Search) | n/a (PerplexityBot is not used for training) | n/a (no separate token) |
| **Respects robots.txt for live fetches** | "may not apply" | Yes (Anthropic: bots honour robots.txt) | n/a | Generally no | n/a |
| **Citation style** | Fewer sources, more influence each | Inline citations with quoted snippets | Many links; fan-out across subtopics | Many sources per answer | Footnoted sources |
| **First-party visibility data** | Referrals (`utm_source=chatgpt.com`) | Referrals from claude.ai | Search Console (inside "Web") | Referrals | **Bing Webmaster Tools AI Performance** |
| **Commerce** | Product feeds; ACP | Connectors (MCP) | Merchant Center; UCP | Shopping features | Bing Shopping / Merchant Center |
| **Apps / tools** | ChatGPT apps (MCP) | Connectors (MCP), Claude in Chrome | Gemini extensions | Comet browser | Copilot agents |
| **Ads** | Yes, since Feb 2026 (labelled, below answers) | No (Anthropic says ad-free) | Yes, in AI Overviews and AI Mode | Previously tested sponsored follow-ups | Yes |

Other engines (Meta AI, Grok, Apple, DuckDuckGo, Brave, Mistral and more): [others.md](others.md).

## What changes across engines, per the research

- **Source overlap is low.** Optimising for one engine does not guarantee visibility in
  another; measure each separately.
- **Breadth versus depth.** Perplexity and Google cite more sources per answer; ChatGPT cites
  fewer but each cited page shapes more of the answer ([Zhang et al. 2026](https://arxiv.org/abs/2604.25707)).
- **Different favourite sources.** Reddit is especially prominent in Perplexity and Google's
  AI features, Wikipedia in ChatGPT, YouTube in AI Overviews
  ([Peec AI 2026](https://docs.peec.ai/research/most-cited-domains-in-ai-search)).
- **Different sensitivities.** Engines differ in freshness preference, cross-language
  stability and sensitivity to how a prompt is phrased ([Chen et al. 2025](https://arxiv.org/abs/2509.08919)).
- **Underlying models differ** in how they weigh evidence inside the same sources. Our
  Experiment 2 compares models directly on identical source sets (see the paper).
