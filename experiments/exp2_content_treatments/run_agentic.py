"""Run the agentic search experiment (specified in README.md, "Agentic search").

The model gets the user's question and two tools, search and open_page, over the page pool of search_pool.py. It
may make up to eight tool calls; then the tools are withheld and it must answer. Azure deployments use Chat
Completions; OpenAI models use the Responses API (GPT-6.1 Sol rejects function tools with reasoning in Chat
Completions).

    python run_agentic.py --model azure:gpt-5-mini --pilot            # two episodes -> data/agentic_pilot.jsonl
    python run_agentic.py --model azure:gpt-5-mini --cap 8 --workers 8

Each episode is scored when it ends and appended to data/agentic_<model>.jsonl, so an interrupted run resumes
without repeating finished episodes. Trials run in a fixed random order with all conditions of a trial together.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import random
import re
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from search_pool import CONDITIONS, Embedder, Engine, episodes  # noqa: E402
from aeotools.llm import _THINK, _post_with_retry, estimate_cost  # noqa: E402  (also loads .env)
from aeotools.metrics import brand_metrics  # noqa: E402

MAX_CALLS = 8
MAX_ROUNDS = 14
SYSTEM = ("You are an AI search assistant with two tools: search, which searches the web and returns the top five "
          "results with short snippets, and open_page, which returns the text of a web page. Search before you "
          "answer, and answer the user's question using only the pages you found, not your prior knowledge of "
          "products. Cite the pages you rely on by putting their URL in square brackets, such as "
          "[https://example.com/], at the end of the relevant sentence. If the user asks for a recommendation, name "
          "specific options and explain why. Keep the answer under 250 words.")
# Before the pilot the prompt said "using the pages you found"; see README.md, "Agentic search", after the pilot.
LIMIT_MSG = "Tool limit reached. Answer the question now using only the pages you found."
_MARKUP = re.compile(r"<[｜|]DSML[｜|].*", re.S)  # tool-call markup some models write as text when tools are withheld
_FN = [
    {"name": "search", "description": "Search the web. Returns the top five results, each with a title, URL and snippet.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "The search query."}},
                    "required": ["query"]}},
    {"name": "open_page", "description": "Open a web page and return its full text.",
     "parameters": {"type": "object", "properties": {"url": {"type": "string",
                                                             "description": "The page URL, as shown in the results."}},
                    "required": ["url"]}},
]
TOOLS_CC = [{"type": "function", "function": f} for f in _FN]
TOOLS_RESP = [{"type": "function", **f} for f in _FN]
_REASONING = re.compile(r"^(gpt-5|gpt-6|o\d)", re.I)
_lock = threading.Lock()
_fixes: dict[str, set] = {}


class Episode:
    """Tool execution and bookkeeping for one episode."""

    def __init__(self, engine: Engine):
        self.engine, self.steps, self.calls = engine, [], 0

    def run_tool(self, name: str, raw_args: str | dict) -> str:
        if self.calls >= MAX_CALLS:
            return LIMIT_MSG
        try:
            args = raw_args if isinstance(raw_args, dict) else json.loads(raw_args or "{}")
        except json.JSONDecodeError:
            args = {}
        self.calls += 1
        if name == "search":
            q = str(args.get("query", ""))[:300]
            text, urls = self.engine.search(q)
            self.steps.append({"tool": "search", "query": q, "results": urls})
            return text
        if name == "open_page":
            url = str(args.get("url", ""))[:300]
            text, key = self.engine.open(url)
            self.steps.append({"tool": "open_page", "url": url, "page": key})
            return text
        self.steps.append({"tool": name, "error": "unknown tool"})
        return f"Error: unknown tool {name}."


def _endpoint(spec: str) -> tuple[str, dict, str]:
    provider, _, model = spec.partition(":")
    if provider == "azure":
        return (os.environ["AZURE_FOUNDRY_ENDPOINT"].rstrip("/") + "/chat/completions",
                {"api-key": os.environ["AZURE_FOUNDRY_API_KEY"], "Content-Type": "application/json"}, model)
    if provider == "openai":
        return ("https://api.openai.com/v1/responses",
                {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"}, model)
    raise ValueError(f"unsupported provider for the agentic run: {spec}")


def _post(spec: str, url: str, headers: dict, make_body) -> tuple[dict | None, str | None]:
    """POST with the main runs' handling of refused settings (dropped and recorded in _fixes[spec])."""
    fixes = _fixes.setdefault(spec, set())
    for _ in range(4):
        body = make_body(fixes)
        r = _post_with_retry(url, headers, body)
        if not isinstance(r, str):
            return r.json(), None
        low = r.lower()
        if "content_filter" in low or "responsibleaipolicyviolation" in low or "content management policy" in low:
            return None, f"content_filter: {r}"[:300]
        # Judge by what this request sent, not by the shared set, which another thread may have updated already.
        refused = next((k for k, needle, sent in (("temperature", "temperature", "temperature"),
                                                  ("reasoning", "reasoning", "reasoning_effort"),
                                                  ("reasoning", "reasoning", "reasoning"),
                                                  ("max_tokens", "max_completion_tokens", "max_completion_tokens"))
                        if r.startswith("HTTP 400") and needle in low and sent in body), None)
        if refused is None:
            return None, r[:300]
        fixes.add(refused)
    return None, "no response"


def chat_episode(spec: str, ep: dict, tools: Episode, max_tokens: int) -> dict:
    url, headers, model = _endpoint(spec)
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": ep["query"]}]
    usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    forced = False
    for _ in range(MAX_ROUNDS):
        force = tools.calls >= MAX_CALLS
        if force and not forced:
            msgs.append({"role": "user", "content": LIMIT_MSG})
        forced = forced or force

        def body(fixes, force=force):
            b = {"model": model, "messages": msgs, "tools": TOOLS_CC, "tool_choice": "none" if force else "auto",
                 ("max_tokens" if "max_tokens" in fixes else "max_completion_tokens"): max_tokens}
            if "temperature" not in fixes:
                b["temperature"] = 0.0
            if _REASONING.search(model) and "reasoning" not in fixes:
                b["reasoning_effort"] = "low"
            return b

        data, err = _post(spec, url, headers, body)
        if err:
            return {"error": err, "forced": forced, **usage}
        u = data.get("usage") or {}
        usage["input_tokens"] += u.get("prompt_tokens", 0)
        usage["output_tokens"] += u.get("completion_tokens", 0)
        usage["cached_tokens"] += (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0
        choice = (data.get("choices") or [{}])[0]
        if choice.get("finish_reason") == "content_filter":
            return {"error": "content_filter: output filtered", "forced": forced, **usage}
        msg = choice.get("message") or {}
        calls = msg.get("tool_calls") or []
        if calls and not force:
            msgs.append({"role": "assistant", "content": msg.get("content"), "tool_calls": calls})
            for c in calls:
                fn = c.get("function") or {}
                msgs.append({"role": "tool", "tool_call_id": c["id"],
                             "content": tools.run_tool(fn.get("name", ""), fn.get("arguments", "{}"))})
            continue
        text = _MARKUP.sub("", _THINK.sub("", msg.get("content") or "")).strip()
        if not text:
            return {"error": "empty answer", "forced": forced, **usage}
        return {"text": text, "forced": forced, "stop_reason": choice.get("finish_reason") or "", **usage}
    return {"error": "too many rounds", "forced": forced, **usage}


def responses_episode(spec: str, ep: dict, tools: Episode, max_tokens: int) -> dict:
    url, headers, model = _endpoint(spec)
    items: list = [{"role": "user", "content": ep["query"]}]
    prev = None
    usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    forced = False
    for _ in range(MAX_ROUNDS):
        force = tools.calls >= MAX_CALLS
        if force and not forced:
            items = items + [{"role": "user", "content": LIMIT_MSG}]
        forced = forced or force

        def body(fixes, force=force, items=items, prev=prev):
            b = {"model": model, "instructions": SYSTEM, "input": items, "tools": TOOLS_RESP,
                 "tool_choice": "none" if force else "auto", "max_output_tokens": max_tokens}
            if prev:
                b["previous_response_id"] = prev
            if _REASONING.search(model) and "reasoning" not in fixes:
                b["reasoning"] = {"effort": "low"}
            return b

        data, err = _post(spec, url, headers, body)
        if err:
            return {"error": err, "forced": forced, **usage}
        prev = data.get("id")
        u = data.get("usage") or {}
        usage["input_tokens"] += u.get("input_tokens", 0)
        usage["output_tokens"] += u.get("output_tokens", 0)
        usage["cached_tokens"] += (u.get("input_tokens_details") or {}).get("cached_tokens", 0) or 0
        out = data.get("output") or []
        calls = [o for o in out if o.get("type") == "function_call"]
        if calls and not force:
            items = [{"type": "function_call_output", "call_id": c["call_id"],
                      "output": tools.run_tool(c.get("name", ""), c.get("arguments", "{}"))} for c in calls]
            continue
        text = "".join(c.get("text", "") for o in out if o.get("type") == "message"
                       for c in o.get("content") or [] if c.get("type") == "output_text").strip()
        if not text:
            return {"error": f"empty answer ({data.get('status')})", "forced": forced, **usage}
        return {"text": text, "forced": forced, "stop_reason": data.get("status") or "", **usage}
    return {"error": "too many rounds", "forced": forced, **usage}


def score(ep: dict, res: dict, steps: list[dict]) -> dict:
    text = res.get("text", "")
    out = brand_metrics(text, ep["brands"], ep["target"])
    searches = [s for s in steps if s["tool"] == "search"]
    opens = [s for s in steps if s["tool"] == "open_page"]
    t, g = ep["target_url"], ep["guide_url"]
    first = searches[0]["results"] if searches else []
    out.update({
        "cited": t.split("/")[0] in text.lower(),
        "guide_cited": g.split("/")[0] in text.lower(),
        "surfaced": any(t in s["results"] for s in searches),
        "opened": any(s.get("page") == t for s in opens),
        "first_rank": first.index(t) + 1 if t in first else 0,
        "guide_surfaced": any(g in s["results"] for s in searches),
        "guide_opened": any(s.get("page") == g for s in opens),
        "n_search": len(searches), "n_open": len(opens), "no_search": not searches,
        "no_brand": out["n_brands_mentioned"] == 0,
    })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--cap", type=float, required=False, default=None, help="estimated spend cap for this model ($)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=None, help="run at most this many new episodes")
    args = ap.parse_args()
    spec = args.model
    safe = re.sub(r"[^A-Za-z0-9.-]+", "-", spec.replace(":", "_")).lower()
    out = Path(args.out) if args.out else HERE / "data" / ("agentic_pilot.jsonl" if args.pilot else f"agentic_{safe}.jsonl")

    eps, pool = episodes()
    if args.pilot:
        eps = [e for e in eps if e["trial_id"] == "pm_agency-0" and e["condition"] in ("baseline", "third_party")]
    else:
        trials = sorted({e["trial_id"] for e in eps})
        random.Random(20261106).shuffle(trials)
        order = {t: i for i, t in enumerate(trials)}
        eps.sort(key=lambda e: (order[e["trial_id"]], random.Random(f"{e['trial_id']}:{e['condition']}").random()))

    done, spent = set(), 0.0
    if out.exists():
        for line in out.open():
            r = json.loads(line)
            if r["model"] != spec:
                continue
            spent += r.get("cost_usd", 0.0)
            if not r.get("error"):
                done.add((r["trial_id"], r["condition"]))
    todo = [e for e in eps if (e["trial_id"], e["condition"]) not in done]
    if args.limit:
        todo = todo[:args.limit]
    state = {"spent": spent, "stopped": False}
    embedder = Embedder()
    print(f"{spec}: {len(todo)} episodes to run (spent so far ${spent:.2f}, cap {args.cap})", flush=True)
    runner = responses_episode if spec.startswith("openai:") else chat_episode

    def run(ep: dict) -> None:
        if state["stopped"]:
            return
        engine = Engine(pool, ep["override"], embedder)
        tools = Episode(engine)
        started = time.time()
        try:
            res = runner(spec, ep, tools, args.max_tokens)
        except Exception as exc:  # a harness failure is recorded, never silently dropped
            res = {"error": f"harness: {type(exc).__name__}: {exc}"[:300]}
        cost = estimate_cost(spec, res.get("input_tokens", 0), res.get("output_tokens", 0))
        rec = {"model": spec, **{k: ep[k] for k in ("trial_id", "scenario", "vertical", "condition", "target",
                                                       "target_url", "guide_url", "query")},
               "text": res.get("text", ""), "steps": tools.steps, "n_calls": tools.calls,
               "forced": res.get("forced", False), "input_tokens": res.get("input_tokens", 0),
               "output_tokens": res.get("output_tokens", 0), "cached_tokens": res.get("cached_tokens", 0),
               "cost_usd": cost, "latency_s": round(time.time() - started, 2), "stop_reason": res.get("stop_reason", ""),
               "error": res.get("error"), "notes": "; ".join(sorted(_fixes.get(spec, set())))}
        if not rec["error"]:
            rec.update(score(ep, res, tools.steps))
        with _lock:
            state["spent"] += cost
            if args.cap is not None and state["spent"] >= args.cap:
                state["stopped"] = True
            with out.open("a") as fh:
                fh.write(json.dumps(rec) + "\n")

    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool_ex:
        futures = [pool_ex.submit(run, e) for e in todo]
        for i, f in enumerate(cf.as_completed(futures), 1):
            f.result()
            if i % 50 == 0:
                print(f"  {i}/{len(todo)}  spent ${state['spent']:.2f}", flush=True)
    if state["stopped"]:
        print(f"Cap reached (${state['spent']:.2f} >= ${args.cap:.2f}); stopped.", flush=True)
        return 1
    print(f"Done. Estimated spend for {spec}: ${state['spent']:.2f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
