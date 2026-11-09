"""Ask models through Hoplite's coding-agent platform (exploratory; README, "Frontier models through a coding-agent
platform").

    python3 run_hoplite.py --models gpt-6-astra:low gemini-4-argon:low --stage 1
    python3 run_hoplite.py --models gpt-6.1-sol:low --stage 1        # the platform check

Each question is a new Hoplite thread started with `hoplite ask --json`. The prompt is the main design's system
prompt and user message after a fixed wrapper, because Hoplite has no direct model API and puts its own agent
instructions first. Answers are scored as in run_experiment.py and appended to data/responses_hoplite_<model>.jsonl,
so an interrupted run resumes; failed questions are retried on the next run.

Hoplite keeps a finished thread's sandbox for a while and refuses new threads while too many are kept
("retained_sandbox_limit_reached"). Such failures pause every worker for --pause seconds and the question is asked
again, up to --attempts times. If HOPLITE_API_KEY is in the repository's .env, each thread is archived through
Hoplite's public API (PATCH /api/threads/{id}) as soon as its answer has been received, which releases its sandbox at
once; the key is never printed.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from build_corpus import CONDITIONS, SYSTEM, build  # noqa: E402
from aeotools.metrics import brand_metrics, source_metrics  # noqa: E402

HOPLITE = os.environ.get("HOPLITE_BIN", str(Path.home() / ".local" / "bin" / "hoplite"))
WRAPPER = ("This is a one-off question, not a coding task. Do not run any commands, open any files or use any tools, "
           "and do not change the repository. Reply with your answer only, following the instructions below.\n\n"
           "Instructions: {system}\n\n{user}")
STAGE1 = ["baseline", "third_party", "citations", "statistics", "answer_first", "keyword_stuffing", "injection"]
SETUP = re.compile(r"setting up|workspace|sandbox|setup", re.I)  # Hoplite's own start-up step, not the model's
STOP_WORDS = re.compile(r"credit|allowance|spend[_ ]limit|usage[_ ]limit|payment|quota|billing", re.I)
API = "https://api.hoplite.sh"
_lock = threading.Lock()


def _archive_key() -> str | None:
    """HOPLITE_API_KEY from the gitignored .env (kept out of os.environ so the CLI keeps its own key)."""
    env = ROOT / ".env"
    if env.exists():
        for ln in env.read_text().splitlines():
            if ln.startswith("HOPLITE_API_KEY="):
                return ln.split("=", 1)[1].strip() or None
    return None


ARCHIVE_KEY = _archive_key()
_archive_warned = False


def archive(thread_id: str | None) -> bool | None:
    """Archive a finished thread so Hoplite releases its sandbox. None when there is no key or no thread."""
    global _archive_warned
    if not (ARCHIVE_KEY and thread_id):
        return None
    req = urllib.request.Request(f"{API}/api/threads/{thread_id}", method="PATCH",
                                 data=json.dumps({"archived": True}).encode(),
                                 headers={"Authorization": f"Bearer {ARCHIVE_KEY}", "Content-Type": "application/json",
                                          "User-Agent": "aeo-handbook-run-hoplite"})
    code = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return 200 <= r.status < 300
        except urllib.error.HTTPError as e:
            code = e.code
            if e.code in (400, 401, 403, 404):
                break
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(5)
    if not _archive_warned:
        _archive_warned = True
        print(f"  could not archive a thread (HTTP {code}); check HOPLITE_API_KEY in .env", flush=True)
    return False


def items_for(stage: int) -> list[dict]:
    """Stage 1: trial 0 of every scenario in seven conditions. Stage 2: the whole main design."""
    items = build(3)
    if stage == 1:
        items = [it for it in items if it["trial_id"].endswith("-0") and it["condition"] in STAGE1]
    trials = sorted({it["trial_id"] for it in items})
    random.Random("hoplite-order").shuffle(trials)
    rank = {t: i for i, t in enumerate(trials)}
    return sorted(items, key=lambda it: (rank[it["trial_id"]], CONDITIONS.index(it["condition"])))


def parse(stdout: str) -> tuple[dict, list[dict]]:
    """--json=stream prints one event per line, then the result object (the last line)."""
    events = []
    for line in stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    result = events[-1] if events and "exit_code" in events[-1] else {}
    return result, events[:-1] if result else events


def answer_text(events: list[dict]) -> tuple[str, int]:
    """Join the streamed text. The stream sometimes carries a stand-alone blank line in mid-sentence (between two
    pieces of one sentence) that the web app does not show; those pieces are dropped. Real paragraph breaks arrive
    inside a text piece."""
    parts = [e.get("text", "") for e in events if e.get("type") == "assistant_text"]
    out, dropped = [], 0
    for i, t in enumerate(parts):
        nxt = parts[i + 1] if i + 1 < len(parts) else ""
        prev = out[-1] if out else ""
        if (t.strip() == "" and "\n\n" in t and nxt[:1] and (nxt[:1] in " ,.;:)]" or nxt[:1].islower())
                and prev and not prev.endswith("\n")):
            dropped += 1
            continue
        out.append(t)
    return "".join(out).strip(), dropped


def ask(model_id: str, level: str, prompt: str, timeout: int) -> tuple[dict, list[dict], float, str]:
    cmd = [HOPLITE, "ask", "--model", model_id, "--reasoning", level, "--json=stream", "--", prompt]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        _, events = parse(out)
        thread = next((ev.get("threadId") or ev.get("thread_id") or ev.get("id") for ev in events
                       if ev.get("type") == "thread"), None)
        return {"threadId": thread} if thread else {}, events, time.time() - t0, f"timeout after {timeout} s"
    res, events = parse(r.stdout)
    err = ""
    if not res:
        err = f"exit {r.returncode}: {(r.stderr or r.stdout).strip()[-400:]}"
    elif res.get("error") or res.get("failure") or res.get("exit_code") not in (0, None):
        err = json.dumps({k: res.get(k) for k in ("error", "failure", "exit_code")})[:400]
    return res, events, time.time() - t0, err


def usage(events: list[dict]) -> dict:
    """The last usage report: the model that answered, tokens and cost (Hoplite's rates)."""
    u = next((e["usage"] for e in reversed(events) if e.get("type") == "usage" and e.get("usage", {}).get("runCount")), {})
    cost = (u.get("cost") or {}).get("amount")
    return {"model_reported": u.get("modelId"), "input_tokens": u.get("inputTokens"),
            "output_tokens": u.get("outputTokens"), "cost_usd": cost}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True, help="model_id:reasoning, e.g. gpt-6-astra:low")
    ap.add_argument("--stage", type=int, choices=[1, 2], default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--attempts", type=int, default=15, help="tries per question before it is recorded as failed")
    ap.add_argument("--pause", type=int, default=60, help="seconds every worker waits after a failed turn")
    ap.add_argument("--limit", type=int, default=None, help="ask at most this many questions per model (tests)")
    ap.add_argument("--conditions", nargs="+", default=None, help="only these conditions (e.g. the Grok check)")
    ap.add_argument("--max-cost", type=float, default=None, help="stop a model's run once it has cost this much (USD)")
    args = ap.parse_args()
    items = items_for(args.stage)
    if args.conditions:
        unknown = set(args.conditions) - {it["condition"] for it in items}
        if unknown:
            raise SystemExit(f"not in stage {args.stage}: {sorted(unknown)}")
        items = [it for it in items if it["condition"] in args.conditions]
    print(f"archiving finished threads: {'yes' if ARCHIVE_KEY else 'no (no HOPLITE_API_KEY in .env)'}", flush=True)

    for spec in args.models:
        model_id, _, level = spec.partition(":")
        level = level or "low"
        out = HERE / "data" / f"responses_hoplite_{model_id.split('/')[-1]}.jsonl"
        done = set()
        if out.exists():
            for line in out.open():
                r = json.loads(line)
                if not r.get("error"):
                    done.add((r["trial_id"], r["condition"]))
        todo = [it for it in items if (it["trial_id"], it["condition"]) not in done][: args.limit]
        print(f"{model_id} ({level}): {len(todo)} questions to ask, {len(done)} already answered", flush=True)
        state = {"stop": False, "billing_errors": 0, "timeouts": 0, "n": 0, "pause_until": 0.0, "cost": 0.0}

        def hold() -> None:
            """Wait while a recent failed turn has paused all workers."""
            while not state["stop"]:
                with _lock:
                    wait = state["pause_until"] - time.time()
                if wait <= 0:
                    return
                time.sleep(min(wait, 10))

        def run(it: dict) -> None:
            if state["stop"]:
                return
            prompt = WRAPPER.format(system=SYSTEM, user=it["user"])
            for attempt in range(1, args.attempts + 1):  # failed turns (mostly the sandbox limit) are retried
                hold()
                if state["stop"]:
                    return
                res, events, dt, err = ask(model_id, level, prompt, args.timeout)
                thread_id = res.get("threadId") or res.get("thread_id") or next(
                    (ev.get("threadId") for ev in events if ev.get("type") == "thread"), None)
                if not err or STOP_WORDS.search(err):
                    break
                if err.startswith("timeout"):
                    with _lock:
                        state["timeouts"] += 1
                        if state["timeouts"] >= 4 and not state["stop"]:
                            state["stop"] = True
                            print("  stopping: four turns in a row timed out (Hoplite may have paused runs, e.g. "
                                  "because the month's usage is spent)", flush=True)
                    if state["stop"]:
                        break
                if attempt == args.attempts:
                    break
                archive(thread_id)  # this failed attempt's thread is not needed; the last one is archived below
                with _lock:
                    state["pause_until"] = max(state["pause_until"], time.time() + args.pause)
            text, dropped = answer_text(events)
            if not text:
                text = (res.get("final_output") or res.get("output") or "").strip()
            u = usage(events)
            if not err and not text:
                err = "empty answer"
            if not err and u["model_reported"] and u["model_reported"] != model_id:
                err = f"answered by {u['model_reported']}, not {model_id}"
            calls = [{"name": c.get("name"), "status": c.get("status")} for c in (res.get("tool_calls") or [])]
            rec = {"model": f"hoplite:{model_id}:{level}",
                   **{k: it[k] for k in ("trial_id", "scenario", "vertical", "condition", "target", "target_index",
                                         "guide_index", "n_sources", "target_words")},
                   "text": text, "error": err or None, "thread": thread_id,
                   **u, "stray_breaks_dropped": dropped, "final_output_raw": res.get("final_output"),
                   "tool_calls": calls, "model_tool_calls": [c["name"] for c in calls if not SETUP.search(c["name"] or "")],
                   "steps": res.get("steps"), "latency_s": round(dt, 1), "route": "hoplite ask --json=stream (CLI 3.5.1)",
                   "stage": args.stage, "attempts": attempt, "finished_at": round(time.time(), 1)}
            if not err:
                rec.update(brand_metrics(text, it["brands"], it["target"]))
                rec.update(source_metrics(text, it["target_index"], it["n_sources"]))
                rec["guide_cited"] = source_metrics(text, it["guide_index"], it["n_sources"])["cited"]
            rec["archived"] = archive(thread_id)  # the answer is already in hand; archiving only frees the sandbox
            with _lock:
                with out.open("a") as fh:
                    fh.write(json.dumps(rec) + "\n")
                state["n"] += 1
                state["cost"] += rec.get("cost_usd") or 0.0
                if args.max_cost is not None and state["cost"] >= args.max_cost and not state["stop"]:
                    state["stop"] = True
                    print(f"  stopping: this run has cost ${state['cost']:.2f} (cap ${args.max_cost:.2f})", flush=True)
                if not err:
                    state["timeouts"] = 0
                if err and STOP_WORDS.search(err):
                    state["billing_errors"] += 1
                    if state["billing_errors"] >= 3:
                        state["stop"] = True
                        print("  stopping: Hoplite reports a credit or billing limit", flush=True)
                if err:
                    print(f"  error on {it['trial_id']}/{it['condition']}: {err[:160]}", flush=True)
                if state["n"] % 25 == 0:
                    print(f"  {state['n']}/{len(todo)} asked", flush=True)

        with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(run, todo))
        print(f"{model_id}: {state['n']} asked, ${state['cost']:.2f}", flush=True)
        if state["stop"]:
            return 2 if state["billing_errors"] else 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
