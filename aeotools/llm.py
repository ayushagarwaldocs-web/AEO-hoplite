"""Clients for the answer-engine experiments and the visibility tracker.

A model is named "provider:model", for example:

    anthropic:claude-haiku-5-5      (official anthropic SDK)
    openai:gpt-5-mini               (REST, Chat Completions)
    gemini:gemini-2.5-flash         (REST, generateContent)
    openrouter:meta-llama/llama-4-maverick
    local:qwen3:8b                  (any OpenAI-compatible server at LOCAL_LLM_BASE_URL)

Keys come from the environment or a .env file at the repo root. Every call
returns an LLMResult with text, token usage and an estimated cost, and never
raises for API errors, so long experiment runs survive transient failures.

Claude refusal fallbacks are deliberately not enabled: in a measurement study a
fallback would silently swap the model being measured. Refusals are recorded.
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:  # python-dotenv is optional
    pass

# USD per million tokens (input, output). Used for the spending guard only;
# check provider pricing pages before large runs. Unknown models fall back to
# DEFAULT_PRICE, which is deliberately pessimistic.
PRICES = {
    "anthropic:claude-haiku-5-5": (0.10, 0.50),
    "anthropic:claude-sonnet-5-5": (2.00, 10.00),
    "anthropic:claude-opus-5-5": (4.00, 20.00),
}
DEFAULT_PRICE = (5.00, 25.00)


@dataclass
class LLMResult:
    spec: str
    text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    stop_reason: str = ""
    latency_s: float = 0.0
    error: str | None = None
    cited_urls: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def available_providers() -> list[str]:
    found = []
    for name, var in (("anthropic", "ANTHROPIC_API_KEY"), ("openai", "OPENAI_API_KEY"),
                      ("gemini", "GEMINI_API_KEY"), ("openrouter", "OPENROUTER_API_KEY"),
                      ("local", "LOCAL_LLM_BASE_URL")):
        if os.environ.get(var):
            found.append(name)
    return found


def estimate_cost(spec: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = PRICES.get(spec, DEFAULT_PRICE)
    return (input_tokens * pin + output_tokens * pout) / 1_000_000


# --- Claude ------------------------------------------------------------------

_anthropic_client = None


def _claude(model: str, system: str, user: str, max_tokens: int, web_search: bool = False) -> LLMResult:
    global _anthropic_client
    import anthropic  # pip install anthropic

    if _anthropic_client is None:
        # Pin the public endpoint: some shells export ANTHROPIC_BASE_URL for other tools.
        _anthropic_client = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            base_url=os.environ.get("AEO_ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
            max_retries=5, timeout=180.0)
    spec = f"anthropic:{model}"
    kwargs = {}
    if web_search:
        # Dynamic-filtering web search needs Sonnet/Opus 4.6+; other models use the basic variant.
        tool_type = "web_search_20250305" if "haiku" in model else "web_search_20260209"
        kwargs["tools"] = [{"type": tool_type, "name": "web_search", "max_uses": 3}]
    messages = [{"role": "user", "content": user}]
    started = time.time()
    text, urls, pin, pout, stop = "", [], 0, 0, ""
    try:
        for _ in range(4):  # resume server-tool turns that pause
            resp = _anthropic_client.messages.create(
                model=model, max_tokens=max_tokens, system=system, messages=messages,
                output_config={"effort": "low"}, **kwargs)
            pin += resp.usage.input_tokens
            pout += resp.usage.output_tokens
            stop = resp.stop_reason or ""
            for block in resp.content:
                if block.type == "text":
                    text += block.text
                    for c in getattr(block, "citations", None) or []:
                        if getattr(c, "url", None):
                            urls.append(c.url)
            if stop != "pause_turn":
                break
            messages = messages + [{"role": "assistant", "content": resp.content}]
    except anthropic.APIStatusError as exc:
        return LLMResult(spec, error=f"HTTP {exc.status_code}: {exc.message}"[:300],
                         latency_s=time.time() - started)
    except anthropic.APIConnectionError as exc:
        return LLMResult(spec, error=f"connection: {exc}"[:300], latency_s=time.time() - started)
    return LLMResult(spec, text=text, input_tokens=pin, output_tokens=pout,
                     cost_usd=estimate_cost(spec, pin, pout), stop_reason=stop,
                     latency_s=time.time() - started, cited_urls=list(dict.fromkeys(urls)))


# --- REST providers ----------------------------------------------------------

def _post_with_retry(url: str, headers: dict, body: dict, attempts: int = 6) -> requests.Response | str:
    delay = 2.0
    for attempt in range(attempts):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=180)
        except requests.RequestException as exc:
            err = f"connection: {type(exc).__name__}"
        else:
            if r.status_code < 400:
                return r
            err = f"HTTP {r.status_code}: {r.text[:200]}"
            if r.status_code not in (408, 409, 429) and r.status_code < 500:
                return err
        if attempt < attempts - 1:
            time.sleep(delay + random.uniform(0, 1))
            delay = min(delay * 2, 60)
    return err


def _chat_completions(spec: str, url: str, headers: dict, model: str, system: str, user: str,
                      max_tokens: int, token_field: str = "max_tokens", extra: dict | None = None) -> LLMResult:
    body = {"model": model, token_field: max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    body.update(extra or {})
    started = time.time()
    r = _post_with_retry(url, headers, body)
    if isinstance(r, str):
        return LLMResult(spec, error=r, latency_s=time.time() - started)
    data = r.json()
    choice = (data.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    usage = data.get("usage") or {}
    pin, pout = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
    cost = usage.get("cost") if isinstance(usage.get("cost"), (int, float)) else estimate_cost(spec, pin, pout)
    return LLMResult(spec, text=text, input_tokens=pin, output_tokens=pout, cost_usd=float(cost),
                     stop_reason=choice.get("finish_reason") or "", latency_s=time.time() - started)


def _gemini(model: str, system: str, user: str, max_tokens: int, web_search: bool = False) -> LLMResult:
    spec = f"gemini:{model}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"}
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": max_tokens}}
    if web_search:
        body["tools"] = [{"google_search": {}}]
    started = time.time()
    r = _post_with_retry(url, headers, body)
    if isinstance(r, str):
        return LLMResult(spec, error=r, latency_s=time.time() - started)
    data = r.json()
    cand = (data.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    meta = data.get("usageMetadata") or {}
    pin = meta.get("promptTokenCount", 0)
    pout = meta.get("candidatesTokenCount", 0) + meta.get("thoughtsTokenCount", 0)
    chunks = (cand.get("groundingMetadata") or {}).get("groundingChunks") or []
    urls = [c["web"].get("title") or c["web"].get("uri") for c in chunks if c.get("web")]
    return LLMResult(spec, text=text, input_tokens=pin, output_tokens=pout,
                     cost_usd=estimate_cost(spec, pin, pout),
                     stop_reason=cand.get("finishReason", ""), latency_s=time.time() - started,
                     cited_urls=[u for u in urls if u])


def complete(spec: str, system: str, user: str, max_tokens: int = 4000, web_search: bool = False) -> LLMResult:
    """Call a model. web_search grounds the answer in live search (Anthropic and Gemini only)."""
    provider, _, model = spec.partition(":")
    if web_search and provider not in ("anthropic", "gemini"):
        raise ValueError(f"web_search is only implemented for anthropic: and gemini: models, not {spec}")
    if provider == "anthropic":
        return _claude(model, system, user, max_tokens, web_search)
    if provider == "openai":
        return _chat_completions(spec, "https://api.openai.com/v1/chat/completions",
                                 {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                                 model, system, user, max_tokens, token_field="max_completion_tokens")
    if provider == "gemini":
        return _gemini(model, system, user, max_tokens, web_search)
    if provider == "openrouter":
        return _chat_completions(spec, "https://openrouter.ai/api/v1/chat/completions",
                                 {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
                                 model, system, user, max_tokens, extra={"usage": {"include": True}})
    if provider == "local":
        base = os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        return _chat_completions(spec, f"{base}/chat/completions", {}, model, system, user, max_tokens)
    if provider == "mock":
        from .mock_engine import mock_complete
        return mock_complete(spec, system, user)
    raise ValueError(f"unknown provider in {spec!r}")
