"""Clients for the answer-engine experiments and the visibility tracker.

A model is named "provider:model", for example:

    anthropic:claude-haiku-5-5      (official anthropic SDK)
    bedrock:anthropic.claude-opus-5-5   (Claude in Amazon Bedrock, anthropic[bedrock])
    bedrock:openai.gpt-oss-120b-1:0     (any other Bedrock model, Converse API via boto3)
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
import re
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
    "anthropic:claude-fable-5-1": (10.00, 50.00),
    # Run on the Gemini API free tier (no billing on the key's project, so no charge); paid-tier ceiling kept
    # so the guard stays meaningful if billing is ever enabled.
    "gemini:gemini-3.5-flash": (0.50, 3.00),
    # Standard price from 1 December 2026 as reported by third-party sources (introductory $2/$10 until 30 November),
    # so recorded costs are ceilings.
    "gemini:gemini-4-argon": (4.00, 20.00),
    # Run on the free tier (no charge); the 3.5 Flash ceiling is kept so the guard stays meaningful.
    "gemini:gemini-3.6-flash": (0.50, 3.00),
    "gemini:gemini-3.5-flash-lite": (0.50, 3.00),  # free tier as well; the same ceiling
    "openai:gpt-6.1-sol": (2.00, 10.00),
}
DEFAULT_PRICE = (5.00, 25.00)

# Amazon Bedrock ceilings, matched by substring of the model ID (first match wins).
# Third-party rows are the highest regional on-demand price on the Bedrock pricing
# page (November 2026). Claude rows are Anthropic's list price plus Bedrock's 10%
# regional-endpoint premium. Models not listed fall back to DEFAULT_PRICE.
BEDROCK_PRICES = [
    ("claude-fable", (11.00, 55.00)),
    ("claude-opus-5-5", (4.40, 22.00)),
    ("claude-opus", (5.50, 27.50)),
    ("claude-sonnet-5-5", (2.20, 11.00)),
    ("claude-sonnet", (3.30, 16.50)),
    ("claude-haiku-5-5", (0.11, 0.55)),
    ("claude-haiku", (1.10, 5.50)),
    # OpenAI on Bedrock: the US-endpoint price, 10% above the global one (= OpenAI's own price).
    ("gpt-6-astra", (11.00, 55.00)),
    ("gpt-6.1-sol", (2.20, 11.00)),
    ("gpt-6-sol", (2.20, 11.00)),
    ("gpt-6.1-terra", (1.10, 5.50)),
    ("gpt-6-luna", (0.11, 0.55)),
    ("gpt-5.6-sol", (4.40, 22.00)),
    ("gpt-5.6-terra", (2.20, 13.20)),
    ("gpt-5.6-luna", (0.22, 1.32)),
    ("gpt-5.5", (5.50, 33.00)),
    ("gpt-oss-120b", (0.28, 1.09)),
    ("gpt-oss-20b", (0.13, 0.55)),
    ("deepseek", (1.05, 3.03)),
    ("qwen3-235b", (0.40, 1.59)),
    ("qwen3-32b", (0.28, 1.09)),
    ("qwen3-next", (0.23, 1.86)),
    ("mistral-large", (0.62, 1.82)),
    ("gemma-3-27b", (0.36, 0.59)),
    ("nemotron-super", (0.18, 0.78)),
    ("kimi-k3", (3.30, 16.50)),
    ("kimi", (0.73, 3.60)),
    ("glm-5", (1.55, 4.96)),
    ("minimax", (0.47, 1.86)),
    # Not shown on the pricing page when checked: generous estimates so the guard errs high.
    ("llama4-maverick", (0.35, 1.40)),
    ("nova-2-lite", (0.40, 3.50)),
    ("nova-pro", (1.00, 4.00)),
]

# Microsoft Foundry (Azure) ceilings, matched by substring of the deployment name. MAI-Thinking-1's price is
# from its model card ($2/$8) and gpt-5-mini's is OpenAI's list price, both plus 10%; the others had no
# price on their cards when checked, so they are set high enough that the guard errs on the safe side.
AZURE_PRICES = [
    ("gpt-5-mini", (0.28, 2.20)),
    ("mai-thinking", (2.20, 8.80)),
    ("grok", (3.30, 16.50)),
    ("deepseek", (2.00, 8.00)),
    ("kimi", (3.30, 16.50)),
]


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
    notes: str = ""  # request settings a model refused and the call ran without

    def to_dict(self) -> dict:
        return asdict(self)


def available_providers() -> list[str]:
    found = []
    for name, var in (("anthropic", "ANTHROPIC_API_KEY"), ("openai", "OPENAI_API_KEY"),
                      ("gemini", "GEMINI_API_KEY"), ("openrouter", "OPENROUTER_API_KEY"),
                      ("local", "LOCAL_LLM_BASE_URL")):
        if os.environ.get(var):
            found.append(name)
    if any(os.environ.get(v) for v in ("AWS_BEARER_TOKEN_BEDROCK", "AWS_ACCESS_KEY_ID", "AWS_PROFILE")):
        found.append("bedrock")
    if os.environ.get("AZURE_FOUNDRY_API_KEY") and os.environ.get("AZURE_FOUNDRY_ENDPOINT"):
        found.append("azure")
    return found


def price(spec: str) -> tuple[float, float]:
    """USD per million tokens (input, output) used by the spending guard."""
    if spec in PRICES:
        return PRICES[spec]
    for prefix, table in (("bedrock:", BEDROCK_PRICES), ("azure:", AZURE_PRICES)):
        if spec.startswith(prefix):
            model = spec.partition(":")[2].lower()
            for key, value in table:
                if key in model:
                    return value
    return DEFAULT_PRICE


def estimate_cost(spec: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = price(spec)
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


# --- Amazon Bedrock ----------------------------------------------------------
# Credentials: a Bedrock API key in AWS_BEARER_TOKEN_BEDROCK, or the standard AWS
# chain (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, or AWS_PROFILE). Both clients
# read the same variables. Region from AWS_REGION, default us-east-1.

_bedrock_clients: dict[str, object] = {}
_THINK = re.compile(r"<think>.*?</think>", re.S)
_OPENAI_REASONING = re.compile(r"openai\.gpt-[56]")  # GPT-5.x and GPT-6.x, not gpt-oss
# Settings each model has refused, so later calls skip them instead of failing first.
_converse_fixes: dict[str, set[str]] = {}
_FIX_NOTES = {"system": "system prompt sent in the user turn", "temperature": "default temperature",
              "reasoning": "default reasoning effort"}


def _bedrock_region() -> str:
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def _drop_empty_bedrock_key() -> None:
    # The SDKs treat a blank AWS_BEARER_TOKEN_BEDROCK= line as a key and skip the access keys.
    if not os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)


def _bedrock_claude_client():
    """Claude in Amazon Bedrock: the Messages API, IDs like anthropic.claude-opus-5-5."""
    cache_key = "claude_no_retries" if os.environ.get("AEO_NO_RETRIES") == "1" else "claude"
    if cache_key not in _bedrock_clients:
        from anthropic import AnthropicBedrockMantle  # pip install "anthropic[bedrock]"

        _drop_empty_bedrock_key()
        region = _bedrock_region()
        # Pin the endpoint so a stray ANTHROPIC_BEDROCK_MANTLE_BASE_URL cannot redirect calls.
        _bedrock_clients[cache_key] = AnthropicBedrockMantle(
            aws_region=region, base_url=f"https://bedrock-mantle.{region}.api.aws/anthropic",
            max_retries=0 if os.environ.get("AEO_NO_RETRIES") == "1" else 5, timeout=180.0)
    return _bedrock_clients[cache_key]


def _bedrock_runtime_client():
    """Every other Bedrock model, through the Converse API."""
    cache_key = "runtime_no_retries" if os.environ.get("AEO_NO_RETRIES") == "1" else "runtime"
    if cache_key not in _bedrock_clients:
        import boto3  # pip install boto3
        from botocore.config import Config

        _drop_empty_bedrock_key()
        _bedrock_clients[cache_key] = boto3.client(
            "bedrock-runtime", region_name=_bedrock_region(),
            config=Config(retries={"total_max_attempts": 1} if os.environ.get("AEO_NO_RETRIES") == "1"
                          else {"max_attempts": 8, "mode": "adaptive"}, read_timeout=180))
    return _bedrock_clients[cache_key]


def _bedrock(model: str, system: str, user: str, max_tokens: int) -> LLMResult:
    spec = f"bedrock:{model}"
    started = time.time()
    if model.startswith("anthropic."):
        import anthropic

        # Same request as _claude: these models reject sampling parameters, so no temperature.
        try:
            resp = _bedrock_claude_client().messages.create(
                model=model, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": user}], output_config={"effort": "low"})
        except anthropic.APIStatusError as exc:
            return LLMResult(spec, error=f"HTTP {exc.status_code}: {exc.message}"[:300],
                             latency_s=time.time() - started)
        except anthropic.APIConnectionError as exc:
            return LLMResult(spec, error=f"connection: {exc}"[:300], latency_s=time.time() - started)
        text = "".join(b.text for b in resp.content if b.type == "text")
        pin, pout = resp.usage.input_tokens, resp.usage.output_tokens
        return LLMResult(spec, text=text, input_tokens=pin, output_tokens=pout,
                         cost_usd=estimate_cost(spec, pin, pout), stop_reason=resp.stop_reason or "",
                         latency_s=time.time() - started)

    from botocore.exceptions import BotoCoreError, ClientError

    fixes = _converse_fixes.setdefault(model, set())

    def request() -> dict:
        # Temperature 0 approximates the greedy decoding of the local runs (AEO_TEMPERATURE overrides it
        # for the sampling check). OpenAI's reasoning models get low effort, as Claude does; their hidden
        # reasoning is billed as output.
        r = {"modelId": model, "messages": [{"role": "user", "content": [{"text": user}]}],
             "inferenceConfig": {"maxTokens": max_tokens}}
        if "system" in fixes:
            r["messages"][0]["content"][0]["text"] = f"{system}\n\n{user}"
        else:
            r["system"] = [{"text": system}]
        if "temperature" not in fixes:
            r["inferenceConfig"]["temperature"] = float(os.environ.get("AEO_TEMPERATURE", "0"))
        if _OPENAI_REASONING.search(model) and "reasoning" not in fixes:
            r["additionalModelRequestFields"] = {"reasoning": {"effort": "low"}}
        return r

    resp = None
    for _ in range(4):
        req = request()
        try:
            resp = _bedrock_runtime_client().converse(**req)
            break
        except ClientError as exc:
            err = exc.response.get("Error", {})
            msg = f"{err.get('Code', 'ClientError')}: {err.get('Message', '')}"
            # A model that refuses a setting is retried without it, and the change is recorded.
            refused = next((k for k, present in (("system", "system" in req),
                                                  ("temperature", "temperature" in req["inferenceConfig"]),
                                                  ("reasoning", "additionalModelRequestFields" in req))
                            if present and k in msg.lower()), None)
            if exc.response.get("Error", {}).get("Code") != "ValidationException" or refused is None:
                return LLMResult(spec, error=msg[:300], latency_s=time.time() - started)
            fixes.add(refused)
        except BotoCoreError as exc:
            return LLMResult(spec, error=f"connection: {exc}"[:300], latency_s=time.time() - started)
    if resp is None:
        return LLMResult(spec, error="no response", latency_s=time.time() - started)
    blocks = ((resp.get("output") or {}).get("message") or {}).get("content") or []
    # Reasoning models return their reasoning as separate blocks or <think> spans; score only the answer.
    text = _THINK.sub("", "".join(b.get("text", "") for b in blocks)).strip()
    usage = resp.get("usage") or {}
    pin, pout = usage.get("inputTokens", 0), usage.get("outputTokens", 0)
    return LLMResult(spec, text=text, input_tokens=pin, output_tokens=pout,
                     cost_usd=estimate_cost(spec, pin, pout), stop_reason=resp.get("stopReason", ""),
                     latency_s=time.time() - started, notes="; ".join(_FIX_NOTES[f] for f in sorted(fixes)))


# --- REST providers ----------------------------------------------------------

def _post_with_retry(url: str, headers: dict, body: dict, attempts: int = 6) -> requests.Response | str:
    if os.environ.get("AEO_NO_RETRIES") == "1":
        attempts = 1
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
            if "insufficient_quota" in r.text:  # OpenAI: no credit on the account; retrying cannot help
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


_azure_fixes: dict[str, set] = {}
_AZURE_REASONING = re.compile(r"^(gpt-5|gpt-6|o\d)", re.I)


def _azure(model: str, system: str, user: str, max_tokens: int) -> LLMResult:
    """A Microsoft Foundry deployment through its OpenAI v1 chat-completions endpoint (model = deployment name)."""
    url = os.environ["AZURE_FOUNDRY_ENDPOINT"].rstrip("/") + "/chat/completions"
    headers = {"api-key": os.environ["AZURE_FOUNDRY_API_KEY"], "Content-Type": "application/json"}
    return _openai_v1(f"azure:{model}", url, headers, model, system, user, max_tokens)


def _openai_v1(spec: str, url: str, headers: dict, model: str, system: str, user: str,
               max_tokens: int) -> LLMResult:
    """OpenAI-style chat completions (Azure Foundry or the OpenAI API) with the same request everywhere.

    Temperature 0 (or AEO_TEMPERATURE) and, for OpenAI reasoning models, low reasoning effort, as on Bedrock;
    a parameter the endpoint rejects is dropped and recorded in notes. Requests stopped by a content filter are
    returned as errors starting with "content_filter" so they can be counted."""
    fixes = _azure_fixes.setdefault(spec, set())
    started = time.time()
    for _ in range(4):
        body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_completion_tokens" if "max_tokens" not in fixes else "max_tokens": max_tokens}
        if "temperature" not in fixes:
            body["temperature"] = float(os.environ.get("AEO_TEMPERATURE", "0"))
        if _AZURE_REASONING.search(model) and "reasoning" not in fixes:
            body["reasoning_effort"] = "low"
        r = _post_with_retry(url, headers, body)
        if not isinstance(r, str):
            break
        low = r.lower()
        if "content_filter" in low or "responsibleaipolicyviolation" in low or "content management policy" in low:
            return LLMResult(spec, error=f"content_filter: {r}"[:300], latency_s=time.time() - started)
        # Judge by what this request sent, not by the shared fixes set, which other threads may already have updated.
        refused = next((k for k, needle in (("temperature", "temperature"), ("reasoning", "reasoning_effort"),
                                            ("max_tokens", "max_completion_tokens"))
                        if needle in body and r.startswith("HTTP 400") and needle in low), None)
        if refused is None:
            return LLMResult(spec, error=r, latency_s=time.time() - started)
        fixes.add(refused)
    else:
        return LLMResult(spec, error="no response", latency_s=time.time() - started)
    data = r.json()
    choice = (data.get("choices") or [{}])[0]
    if choice.get("finish_reason") == "content_filter":
        return LLMResult(spec, error="content_filter: output filtered", latency_s=time.time() - started)
    text = _THINK.sub("", (choice.get("message") or {}).get("content") or "").strip()
    usage = data.get("usage") or {}
    pin, pout = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
    notes = {"temperature": "default temperature", "reasoning": "default reasoning effort",
             "max_tokens": "max_tokens instead of max_completion_tokens"}
    return LLMResult(spec, text=text, input_tokens=pin, output_tokens=pout, cost_usd=estimate_cost(spec, pin, pout),
                     stop_reason=choice.get("finish_reason") or "", latency_s=time.time() - started,
                     notes="; ".join(notes[f] for f in sorted(fixes)))


def _gemini(model: str, system: str, user: str, max_tokens: int, web_search: bool = False) -> LLMResult:
    spec = f"gemini:{model}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"}
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": max_tokens}}
    # Lowest reasoning setting, as for the other models. Temperature stays at Google's default: Google advises
    # against lowering it for Gemini 3, which can loop or degrade at low temperature.
    if re.match(r"gemini-[3-9]", model):
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": "low"}
    elif model.startswith("gemini-2.5-flash"):
        body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
    if web_search:
        body["tools"] = [{"google_search": {}}]
    started = time.time()
    r = _post_with_retry(url, headers, body)
    if isinstance(r, str) and r.startswith("HTTP 400") and "thinking" in r.lower():
        body["generationConfig"].pop("thinkingConfig", None)  # a model that refuses the setting runs without it
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
    if provider == "bedrock":
        return _bedrock(model, system, user, max_tokens)
    if provider == "azure":
        return _azure(model, system, user, max_tokens)
    if provider == "openai":
        return _openai_v1(spec, "https://api.openai.com/v1/chat/completions",
                          {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
                          model, system, user, max_tokens)
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
