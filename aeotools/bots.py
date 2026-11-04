"""Registry of AI-related crawlers and robots.txt control tokens.

Each entry records who operates the agent, what it is used for, and where the
operator documents it. Categories:

- training:     collects content that may be used to train foundation models
- ai_search:    builds the index an AI assistant searches before answering
- user_fetch:   fetches a page live because a user asked the assistant something
- search:       classic search crawler whose index also feeds AI answers
- legacy:       deprecated token that still appears in many robots.txt files
- other:        anything else worth tracking (ads review, mixed use)

Sources were checked in November 2026; operators change these lists, so treat
the docs URLs as the authority.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bot:
    token: str
    operator: str
    category: str
    purpose: str
    honors_robots: str  # "yes", "no", "partial" or "unknown", per operator docs
    docs: str  # operator documentation; empty if none is published


BOTS: tuple[Bot, ...] = (
    # OpenAI
    Bot("GPTBot", "OpenAI", "training",
        "Crawls content that may be used to train OpenAI foundation models.",
        "yes", "https://developers.openai.com/api/docs/bots"),
    Bot("OAI-SearchBot", "OpenAI", "ai_search",
        "Indexes sites for ChatGPT search; opted-out sites are not shown in search answers.",
        "yes", "https://developers.openai.com/api/docs/bots"),
    Bot("ChatGPT-User", "OpenAI", "user_fetch",
        "Fetches pages for user-initiated actions in ChatGPT and GPTs.",
        "partial", "https://developers.openai.com/api/docs/bots"),
    Bot("OAI-AdsBot", "OpenAI", "other",
        "Reviews landing pages submitted as ChatGPT ads.",
        "unknown", "https://developers.openai.com/api/docs/bots"),
    # Anthropic
    Bot("ClaudeBot", "Anthropic", "training",
        "Collects web content that may contribute to model training.",
        "yes", "https://support.claude.com/en/articles/8896518"),
    Bot("Claude-SearchBot", "Anthropic", "ai_search",
        "Navigates the web to improve Claude's search result quality.",
        "yes", "https://support.claude.com/en/articles/8896518"),
    Bot("Claude-User", "Anthropic", "user_fetch",
        "Fetches pages when a user asks Claude a question.",
        "yes", "https://support.claude.com/en/articles/8896518"),
    # Perplexity
    Bot("PerplexityBot", "Perplexity", "ai_search",
        "Surfaces and links websites in Perplexity search results; not used for training.",
        "yes", "https://docs.perplexity.ai/docs/resources/perplexity-crawlers"),
    Bot("Perplexity-User", "Perplexity", "user_fetch",
        "Fetches pages for user questions; generally ignores robots.txt.",
        "no", "https://docs.perplexity.ai/docs/resources/perplexity-crawlers"),
    # Google
    Bot("Google-Extended", "Google", "training",
        "Control token (no separate crawler) for Gemini training and grounding; "
        "does not affect Google Search or AI Overviews.",
        "yes", "https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers"),
    Bot("Googlebot", "Google", "search",
        "Google Search crawler; also the source for AI Overviews and AI Mode.",
        "yes", "https://developers.google.com/search/docs/appearance/ai-features"),
    Bot("GoogleOther", "Google", "other",
        "Generic Google crawler for research and one-off fetches.",
        "yes", "https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers"),
    # Microsoft
    Bot("Bingbot", "Microsoft", "search",
        "Bing crawler; Bing's index grounds Copilot and is a major source for ChatGPT search.",
        "yes", "https://www.bing.com/webmasters/help/which-crawlers-does-bing-use-8c184ec0"),
    # Apple
    Bot("Applebot", "Apple", "search",
        "Crawler for Siri and Spotlight suggestions.",
        "yes", "https://support.apple.com/en-us/119829"),
    Bot("Applebot-Extended", "Apple", "training",
        "Control token governing use of Applebot-crawled data for Apple model training.",
        "yes", "https://support.apple.com/en-us/119829"),
    # Meta
    Bot("Meta-ExternalAgent", "Meta", "training",
        "Crawls content for AI training and product indexing.",
        "yes", "https://developers.facebook.com/docs/sharing/webmasters/web-crawlers"),
    Bot("Meta-ExternalFetcher", "Meta", "user_fetch",
        "Fetches pages for user-initiated actions in Meta AI products.",
        "partial", "https://developers.facebook.com/docs/sharing/webmasters/web-crawlers"),
    # Others
    Bot("CCBot", "Common Crawl", "training",
        "Open web crawl reused in many AI training datasets.",
        "yes", "https://commoncrawl.org/ccbot"),
    Bot("Bytespider", "ByteDance", "training",
        "ByteDance crawler associated with model training.",
        "unknown", ""),
    Bot("Amazonbot", "Amazon", "other",
        "Amazon crawler used for Alexa answers and other services.",
        "yes", "https://developer.amazon.com/docs/amazonbot/amazonbot.html"),
    Bot("DuckAssistBot", "DuckDuckGo", "ai_search",
        "Fetches pages to generate DuckDuckGo's AI-assisted answers.",
        "yes", "https://duckduckgo.com/duckduckgo-help-pages/results/duckassistbot"),
    Bot("MistralAI-User", "Mistral", "user_fetch",
        "Fetches pages for user requests in Le Chat.",
        "unknown", "https://docs.mistral.ai/robots"),
    # Legacy Anthropic tokens still common in robots.txt files
    Bot("anthropic-ai", "Anthropic", "legacy",
        "Deprecated Anthropic token.", "unknown", "https://support.claude.com/en/articles/8896518"),
    Bot("Claude-Web", "Anthropic", "legacy",
        "Deprecated Anthropic token.", "unknown", "https://support.claude.com/en/articles/8896518"),
)

BY_TOKEN = {b.token.lower(): b for b in BOTS}

# The tiers that matter most for answer-engine visibility, by operator.
TIERS = {
    "OpenAI": {"training": "GPTBot", "ai_search": "OAI-SearchBot", "user_fetch": "ChatGPT-User"},
    "Anthropic": {"training": "ClaudeBot", "ai_search": "Claude-SearchBot", "user_fetch": "Claude-User"},
    "Perplexity": {"ai_search": "PerplexityBot", "user_fetch": "Perplexity-User"},
}

# A user-agent substring per bot, for classifying access-log lines.
UA_PATTERNS = {b.token: b.token.lower() for b in BOTS if b.token not in {"Google-Extended", "Applebot-Extended"}}
# Bingbot announces itself as "bingbot"; Googlebot variants share the prefix.
UA_PATTERNS["Bingbot"] = "bingbot"


def bots_in(category: str) -> list[Bot]:
    return [b for b in BOTS if b.category == category]
