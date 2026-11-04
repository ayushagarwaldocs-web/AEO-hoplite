# Other answer engines and assistants

Less documented, but worth covering in your robots.txt and measurement.

| Engine | Agents / tokens | Notes |
|---|---|---|
| **Meta AI** (WhatsApp, Instagram, Facebook, Messenger) | `Meta-ExternalAgent` (training and indexing), `Meta-ExternalFetcher` (user-initiated) | Meta documents both on its [web crawlers page](https://developers.facebook.com/docs/sharing/webmasters/web-crawlers). Blocking ExternalAgent may affect product indexing as well as training. |
| **Apple** (Siri, Spotlight, Apple Intelligence) | `Applebot` (search), `Applebot-Extended` (training-use token) | Blocking Applebot-Extended opts out of model training while keeping Siri/Spotlight search ([Apple](https://support.apple.com/en-us/119829)). |
| **DuckDuckGo** (DuckAssist / Duck.ai) | `DuckAssistBot` | Fetches pages for AI-assisted answers. |
| **Brave** (Brave Search AI answers) | Brave's own index | Brave Search's independent index is also reported to power other AI products' web search; check your visibility there. |
| **Mistral Le Chat** | `MistralAI-User` | User-triggered fetches. |
| **Grok (xAI)** | Not documented in detail | Leans heavily on X posts plus web search; public X presence matters. |
| **Common Crawl** | `CCBot` | Not an engine, but its open crawl feeds many training datasets. Blocking it removes you from many future models' training data. |
| **ByteDance** | `Bytespider` | Associated with training; researchers report inconsistent robots.txt compliance ([Liu et al., IMC 2025](https://www.sysnet.ucsd.edu/~voelker/pubs/robots-imc25.pdf)). |

## General advice

- Name the agents you care about explicitly. The `*` group is a blunt instrument that catches
  every new agent you haven't thought about.
- Re-check the agent list quarterly; operators add and retire tokens (Anthropic retired two).
  [`aeotools/bots.py`](../aeotools/bots.py) is the registry this repo uses.
- Verify claimed bots by IP range or reverse DNS where operators publish them; user-agent
  strings are trivially spoofed.
