# Glossary

**AEO (Answer Engine Optimization)** — Making an organisation easy for AI answer engines to
find, understand, trust and cite.

**AI Overviews / AI Mode** — Google Search's AI-generated summary at the top of results, and
its conversational search mode. Both draw on Google's search index.

**AIPREF** — IETF working group defining a vocabulary for AI usage preferences and ways to
attach it to content (robots.txt, the `Content-Usage` HTTP header). Drafts as of 2026.

**Answer engine** — Any system that responds to a question with a generated answer rather
than a list of links: ChatGPT, Claude, Gemini, Perplexity, Copilot, AI Overviews.

**Citation share** — Your share of the citation markers in an answer or across a sample.

**Content-Signal** — Cloudflare's robots.txt extension for expressing preferences such as
`search=yes, ai-train=no`.

**Earned media** — Coverage of you on sources you don't own or pay for: reviews, news,
independent comparisons, community discussion.

**Entity** — A distinct thing (organisation, product, person, place) that engines and
knowledge graphs track.

**Fan-out (query fan-out)** — An engine rewriting one prompt into several sub-queries before
retrieving sources.

**GEO (Generative Engine Optimization)** — The research framing of AEO introduced by
Aggarwal et al. (KDD 2024), focused on content edits that change visibility in generated
answers.

**Grounding** — Supplying a model with retrieved documents at answer time so its answer is
based on, and can cite, those documents.

**Grounding queries** — The background search queries an AI system issues to find sources;
reported by Bing Webmaster Tools' AI Performance report.

**llms.txt** — A proposed Markdown file at `/llms.txt` that summarises a site for LLMs and
links to key pages.

**MCP (Model Context Protocol)** — An open protocol that lets assistants call external tools
and data sources; the basis of ChatGPT apps and Claude connectors.

**Parametric knowledge (training memory)** — What a model learned during training, used when
it answers without searching.

**PAWC (Position-Adjusted Word Count)** — The GEO paper's visibility metric: words in
sentences citing a source, weighted by how early they appear.

**Prompt set** — A fixed, tagged list of prompts used to measure AI visibility over time.

**Retrieval / RAG** — Fetching documents relevant to a question and giving them to the model
(retrieval-augmented generation).

**Share of voice** — Your brand's mentions as a share of all tracked brands' mentions.

**Training crawler** — A crawler collecting data for model training (GPTBot, ClaudeBot,
CCBot), as distinct from search-index bots and user-triggered fetchers.

**User-triggered fetcher** — An agent that fetches a page because a user asked the assistant
something (ChatGPT-User, Claude-User, Perplexity-User).
