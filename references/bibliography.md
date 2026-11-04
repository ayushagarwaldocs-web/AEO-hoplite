# Annotated bibliography

Everything this handbook relies on, with what each source does and doesn't show. Checked in
November 2026. Vendor studies are useful signals but are not peer-reviewed and often sell
the solution they measure; weigh them accordingly.

## Peer-reviewed and preprint research

| Source | What it shows | Caveats |
|---|---|---|
| Aggarwal et al., **GEO: Generative Engine Optimization**, KDD 2024 ([arXiv:2311.09735](https://arxiv.org/abs/2311.09735)) | Introduces GEO, GEO-bench (~10K queries) and the position-adjusted word count metric. Quotations, statistics and citations raised visibility by up to ~40%; keyword stuffing hurt; lower-ranked sources gained most. | Fixed context of 5 sources; GPT-3.5 as the engine; effects on discoverability not measured |
| Puerto et al., **C-SEO Bench**, NeurIPS 2025 D&B ([arXiv:2506.11097](https://arxiv.org/abs/2506.11097)) | Most conversational-SEO methods are largely ineffective; ranking higher in the context matters more; gains fall as more actors adopt C-SEO | Benchmark settings; methods evolve |
| Chen et al., **GEO: How to Dominate AI Search**, 2025 ([arXiv:2509.08919](https://arxiv.org/abs/2509.08919)) | AI search favours earned media over brand-owned and social content, far more than Google; engines differ in freshness, language stability and phrasing sensitivity | Preprint; engine behaviour drifts |
| Vishwakarma et al., **What Gets Cited**, 2026 ([arXiv:2605.25517](https://arxiv.org/abs/2605.25517)) | 252,000 two-source contests across six LLMs: topical relevance and list position dominate; explicit price and recent timestamps help; formatting-only edits have little effect | Two-source setting; models not named in the abstract |
| Zhang et al., **From Citation Selection to Citation Absorption**, 2026 ([arXiv:2604.25707](https://arxiv.org/abs/2604.25707)) | 602 prompts across ChatGPT, Google AI Overviews/Gemini and Perplexity: citation breadth and influence diverge; high-influence pages are longer, more structured, aligned and evidence-rich | Observational |
| Yu et al., **Structural Feature Engineering for GEO**, 2026 ([arXiv:2603.29979](https://arxiv.org/abs/2603.29979)) | Structure-aware optimisation raised citation rate 17.3% across six engines | Framework paper; per-feature effects not in the abstract |
| Martinez, **Critical survey of GEO 2023–2026**, 2026 ([arXiv:2607.14035](https://arxiv.org/abs/2607.14035)) | 45 studies: relevance and context position are the most reproducible levers; generic heuristics transfer poorly; no technique shows stable cross-platform effects on discoverability | Survey |
| Wan, Wallace & Klein, **What Evidence Do Language Models Find Convincing?**, ACL 2024 ([anthology](https://aclanthology.org/2024.acl-long.403)) | Models weigh relevance heavily and largely ignore stylistic cues humans value (references, neutral tone) | Contested-question setting |
| Kumar & Lakkaraju, **Manipulating LLMs to Increase Product Visibility**, 2024 ([arXiv:2404.07981](https://arxiv.org/abs/2404.07981)) | Optimised "strategic text sequences" can push a product to the top of LLM recommendations | Adversarial research; disclaims misuse |
| Nestaas, Debenedetti & Tramèr, **Adversarial SEO for LLMs**, ICLR 2025 ([arXiv:2406.18382](https://arxiv.org/abs/2406.18382)) | Preference-manipulation attacks work on production LLM search (Bing, Perplexity); with several attackers, all lose | Attack research |
| Liu, Zhang & Liang, **Evaluating Verifiability in Generative Search Engines**, 2023 ([arXiv:2304.09848](https://arxiv.org/abs/2304.09848)) | Many generated statements are not fully supported by their citations | Earlier generation of engines |
| Liu et al., **Lost in the Middle**, TACL 2024 ([arXiv:2307.03172](https://arxiv.org/abs/2307.03172)) | Position effects in long contexts | Not AEO-specific |
| Longpre et al., **Consent in Crisis**, NeurIPS 2024 | Rapid rise in robots.txt restrictions on AI crawlers among sources of training corpora | Training-corpus domains, 2023–24 |
| Liu et al., **Somesite I Used To Crawl**, IMC 2025 ([PDF](https://www.sysnet.ucsd.edu/~voelker/pubs/robots-imc25.pdf)) | Adoption of AI-crawler rules, creator awareness, and crawler compliance; some crawlers ignore robots.txt | — |

## Operator documentation (primary sources)

- OpenAI, *Overview of OpenAI crawlers*: [developers.openai.com/api/docs/bots](https://developers.openai.com/api/docs/bots)
- Anthropic, *Does Anthropic crawl data from the web…*: [support.claude.com/en/articles/8896518](https://support.claude.com/en/articles/8896518)
- Perplexity, *Perplexity crawlers*: [docs.perplexity.ai/guides/bots](https://docs.perplexity.ai/guides/bots)
- Google, *AI features and your website*: [developers.google.com/search/docs/appearance/ai-features](https://developers.google.com/search/docs/appearance/ai-features)
- Google, *Common crawlers* (Google-Extended): [developers.google.com/search/docs/crawling-indexing/google-common-crawlers](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers)
- OpenAI, *Commerce key concepts* (product feeds, ACP): [developers.openai.com/commerce](https://developers.openai.com/commerce/guides/key-concepts)
- Model Context Protocol: [modelcontextprotocol.io](https://modelcontextprotocol.io/)

## Standards

- RFC 9309, *Robots Exclusion Protocol*: [rfc-editor.org/rfc/rfc9309](https://www.rfc-editor.org/rfc/rfc9309)
- IETF AIPREF drafts (vocabulary; attachment via robots.txt and `Content-Usage`): [datatracker](https://datatracker.ietf.org/doc/html/draft-ietf-aipref-vocab-07)
- llms.txt proposal: [llmstxt.org](https://llmstxt.org/)
- IndexNow: [indexnow.org](https://www.indexnow.org/)

## Industry studies (directional)

| Source | Finding |
|---|---|
| [Pew Research, July 2025](https://www.pewresearch.org/short-reads/2025/07/22/google-users-are-less-likely-to-click-on-links-when-an-ai-summary-appears-in-the-results/) | Clicks on traditional results: 8% of visits with an AI summary versus 15% without; summary links ~1% |
| [Vercel/MERJ, Dec 2024](https://vercel.com/blog/the-rise-of-the-ai-crawler) | Major AI crawlers fetched but did not execute JavaScript |
| [Peec AI, 2026](https://docs.peec.ai/research/most-cited-domains-in-ai-search) | Reddit, YouTube, LinkedIn and Wikipedia lead 30M cited sources |
| [Ahrefs, 2026](https://ahrefs.com/blog/llmstxt-study/) | Most llms.txt files received no requests; AI retrieval bots ~1% of requests |
| [BuzzStream, 2025](https://www.buzzstream.com/blog/publishers-block-ai-study/) | Top US/UK news sites: 79% block training bots, 71% block retrieval bots |
| [Tow Center/CJR, 2025](https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php) | AI search engines frequently mis-cite news sources |
| SparkToro/Gumshoe, Jan 2026 ([coverage](https://www.searchenginejournal.com/ai-recommendations-change-with-nearly-every-query-sparktoro/566242/)) | Brand recommendation lists almost never repeat; inclusion frequency is the stable metric |
| Bing Webmaster Tools AI Performance (preview, Feb 2026; [analysis](https://www.searchinfluence.com/blog/bing-ai-performance-report-copilot-citations/)) | First-party citation and grounding-query data for Copilot and Bing AI answers |
