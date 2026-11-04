# 9. Beyond citations: agents, commerce, apps and ads

Answer engines are becoming places where people *act*: they buy, book and run tasks without
visiting your site. AEO therefore extends to being **usable by AI**, not only readable.

## 9.1 Product feeds

- **ChatGPT shopping** uses structured product data. OpenAI publishes a product feed
  specification for merchants ([developers.openai.com/commerce](https://developers.openai.com/commerce/guides/key-concepts));
  merchant reports emphasise complete, accurate and frequently refreshed data. Reports in 2026
  disagree on the status of ChatGPT's built-in checkout, so check OpenAI's current documentation.
- **Google** surfaces products in AI Mode and Gemini from Merchant Center. Google's
  [AI features guidance](https://developers.google.com/search/docs/appearance/ai-features)
  explicitly says to keep Merchant Center and Business Profile information current.
- Keep one accurate, frequently updated product catalogue (price, availability, variants,
  shipping, returns) and syndicate it everywhere.

## 9.2 Agentic commerce protocols

- **Agentic Commerce Protocol (ACP)**, from OpenAI and Stripe (2025), is an open standard
  that lets AI agents complete purchases with merchants.
- **Universal Commerce Protocol (UCP)**, announced by Google in January 2026 with partners
  including Shopify, connects catalogues, carts and checkout to Google surfaces such as AI
  Mode and Gemini.
- Commentators generally treat them as complementary. Most merchants adopt them through
  their commerce platform rather than building directly.

## 9.3 Apps and connectors inside assistants

- **ChatGPT apps** (Apps SDK) and **Claude connectors** are both built on the
  [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). They let an assistant
  query your live systems (inventory, bookings, account data, documentation) instead of
  guessing from the web.
- Good candidates: availability and pricing lookups, booking, order status, product
  configuration, documentation search.
- Treat an MCP server like a public API: authentication, rate limits, clear tool
  descriptions, and only the data you intend to expose.

## 9.4 Agent-friendly websites

Browser agents (ChatGPT's agent mode, Claude in Chrome and others) navigate your site the
way a person would, using the page structure:

- Use semantic, accessible HTML: real buttons and links, labelled form fields, a logical
  heading order. Good accessibility and agent-readiness are largely the same work.
- Show prices, availability and terms as text, not only in images or after interaction.
- Avoid challenge walls on the paths agents need (search, product, cart). Where bot
  protection is required, allow verified agents. Some operators sign agent requests
  (for example with the HTTP Message Signatures-based *Web Bot Auth* approach).

## 9.5 Ads in answer engines

Paid placement is a separate channel from AEO. It does not buy you a place in the organic
answer.

- **ChatGPT** began serving labelled "Sponsored" ads below answers in the US in February
  2026 (Free and Go tiers), opened a self-serve Ads Manager in May 2026, and added
  product-feed-based ads in June. OpenAI says ads do not influence answers. OpenAI's
  `OAI-AdsBot` reviews ad landing pages.
- **Google** shows ads in AI Overviews and AI Mode.
- **Anthropic** has said Claude will remain ad-free.

Next: [Anti-patterns and ethics →](10-anti-patterns-and-ethics.md)
