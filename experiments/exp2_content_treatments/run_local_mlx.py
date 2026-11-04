"""Run Experiment 2 with local open-weight models on Apple Silicon (MLX).

    ../../.venv-local/bin/python run_local_mlx.py --model mlx-community/Llama-3.2-3B-Instruct-4bit

Uses the same corpus, system prompt and scoring as run_experiment.py and appends
to the same responses file, so analyze.py treats local and API models alike.
Decoding is greedy, so every response is reproducible on the same weights and
mlx-lm version. Prompts are processed one trial (15 conditions) at a time with
small batches, chunked prefill and a capped buffer cache to fit in 8 GB of unified memory.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from build_corpus import SYSTEM, build  # noqa: E402
from aeotools.metrics import brand_metrics, source_metrics  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="Hugging Face repo of an MLX model")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None, help="only the first N trials (for testing)")
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--completion-batch", type=int, default=4)
    ap.add_argument("--prefill-batch", type=int, default=1)
    ap.add_argument("--prefill-step", type=int, default=512, help="tokens per prefill chunk (lower = less memory)")
    ap.add_argument("--cache-limit-gb", type=float, default=0.5, help="cap on MLX's buffer cache")
    ap.add_argument("--no-prefix-cache", action="store_true",
                    help="prefill every prompt in full instead of sharing the trial's common prefix")
    ap.add_argument("--out", default=str(HERE / "data" / "responses.jsonl"))
    args = ap.parse_args()

    import mlx.core as mx
    from mlx_lm import batch_generate, load
    from mlx_lm.models.cache import make_prompt_cache

    mx.set_cache_limit(int(args.cache_limit_gb * 1e9))  # keep the footprint small on 8 GB machines

    spec = "mlx:" + args.model.split("/")[-1]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in out.open():
            r = json.loads(line)
            if r["model"] == spec and not r.get("error"):
                done.add((r["trial_id"], r["condition"]))

    trials: dict[str, list[dict]] = defaultdict(list)
    for it in build(args.trials):
        if (it["trial_id"], it["condition"]) not in done:
            trials[it["trial_id"]].append(it)
    trial_ids = list(trials)[: args.limit] if args.limit else list(trials)
    total = sum(len(trials[t]) for t in trial_ids)
    print(f"{spec}: {total} prompts in {len(trial_ids)} trials", flush=True)
    if not total:
        return 0

    model, tokenizer = load(args.model)
    started = time.time()
    finished = 0
    for t in trial_ids:
        items = trials[t]
        prompts = [tokenizer.apply_chat_template(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": it["user"]}],
            add_generation_prompt=True) for it in items]
        t0 = time.time()
        inputs, caches = prompts, None
        if not args.no_prefix_cache:
            # All conditions of a trial share their token prefix up to the edited page:
            # prefill it once and let each prompt continue from that cache.
            n = min(len(p) for p in prompts) - 1
            k = next((i for i in range(n) if len({p[i] for p in prompts}) > 1), n)
            if k > 0:
                cache = make_prompt_cache(model)
                prefix = mx.array(prompts[0][:k])
                for start in range(0, k, args.prefill_step):
                    model(prefix[None, start:start + args.prefill_step], cache=cache)
                    mx.eval([c.state for c in cache])
                inputs, caches = [p[k:] for p in prompts], [cache] * len(prompts)
        resp = batch_generate(model, tokenizer, inputs, prompt_caches=caches, max_tokens=args.max_tokens,
                              return_token_ids=True, completion_batch_size=args.completion_batch,
                              prefill_batch_size=args.prefill_batch, prefill_step_size=args.prefill_step)
        elapsed = time.time() - t0
        with out.open("a") as fh:
            for it, prompt, text, ids in zip(items, prompts, resp.texts, resp.token_ids):
                rec = {"model": spec, **{k: it[k] for k in (
                    "trial_id", "scenario", "vertical", "condition", "target", "target_index",
                    "guide_index", "n_sources", "target_words")},
                    "text": text, "input_tokens": len(prompt), "output_tokens": len(ids), "cost_usd": 0.0,
                    "stop_reason": "length" if len(ids) >= args.max_tokens else "stop",
                    "latency_s": round(elapsed / len(items), 2), "error": None, "cited_urls": []}
                rec.update(brand_metrics(text, it["brands"], it["target"]))
                rec.update(source_metrics(text, it["target_index"], it["n_sources"]))
                rec["guide_cited"] = source_metrics(text, it["guide_index"], it["n_sources"])["cited"]
                fh.write(json.dumps(rec) + "\n")
        finished += len(items)
        rate = finished / (time.time() - started)
        eta = (total - finished) / rate / 60 if rate else 0
        print(f"  {finished}/{total}  {elapsed:.0f}s for this trial  "
              f"peak mem {mx.get_peak_memory() / 1e9:.1f} GB  ETA {eta:.0f} min", flush=True)
        mx.clear_cache()
    print(f"Done in {(time.time() - started) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
