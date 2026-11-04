# Claude (Anthropic)

## Where answers come from

- **Training memory** for questions Claude answers without searching.
- **Web search**, which Claude uses when it decides fresh or external information is
  needed. Results come from Anthropic's `Claude-SearchBot` index and a third-party search
  provider (reported to be Brave Search). In the API, each web search result carries a URL,
  title and page age, and citations include the quoted text Claude relied on.
- **Live fetches** by `Claude-User` when a user asks Claude about a specific page.
- **Connectors (MCP)** that let Claude query a company's own systems directly, and **Claude
  in Chrome**, which browses sites as an agent.

## Crawlers and controls

| Token | Purpose | Effect of blocking (Anthropic's wording) |
|---|---|---|
| `ClaudeBot` | Training | Signals that future materials "should be excluded from our AI model training datasets" |
| `Claude-SearchBot` | Search quality and indexing | "may reduce your site's visibility and accuracy in user search results" |
| `Claude-User` | User-directed retrieval | "prevents our system from retrieving your content in response to a user query" |

Anthropic's bots honour robots.txt (including the non-standard `Crawl-delay`). The retired
tokens `anthropic-ai` and `Claude-Web` no longer have any effect. To verify traffic, compare
source IPs with `claude.com/crawling/bots.json`. Source: [Anthropic support](https://support.claude.com/en/articles/8896518).

## Optimisation priorities

1. **Allow `Claude-SearchBot` and `Claude-User`.** Name all three current tokens explicitly
   and remove the deprecated ones. In our measurement, some sites still listed only the old
   tokens.
2. **Be visible in the index Claude's search draws on.** Check your brand and category
   queries in Brave Search as well as Google and Bing.
3. **Make pages verifiable.** Claude's citations quote the specific text used, so precise,
   self-contained sentences with dates and figures are easier to cite accurately.
4. **Offer a connector** for live data (availability, pricing, documentation search) through
   an MCP server.
5. **Agent-ready pages** for Claude in Chrome: accessible HTML, prices and terms as text.

## Measurement

- Referrals from `claude.ai`.
- `Claude-User` hits in logs show pages being fetched for real user questions.
- The Claude API with the web search tool can reproduce search-grounded answers for sampling,
  though consumer-app behaviour can differ.

## Ads

None. Anthropic has said Claude will remain ad-free.
