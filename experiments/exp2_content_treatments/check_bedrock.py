"""Check Amazon Bedrock access and project costs before a paid run.

    python check_bedrock.py                  # credentials found, and the text models this account lists
    python check_bedrock.py --models bedrock:anthropic.claude-opus-5-5 bedrock:openai.gpt-oss-120b-1:0
    python check_bedrock.py --all            # one prompt to every listed model and to Claude

With --models or --all, each model answers one real prompt from the corpus (a
baseline page) and the full run is projected from its token counts and the
spending-guard prices in aeotools/llm.py. One prompt costs under a cent on most
models and about three cents on Claude Opus 5.5. Results go to
data/bedrock_check.json, never to the responses file, and credentials are never
printed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from build_corpus import SYSTEM, build  # noqa: E402
from aeotools import llm  # noqa: E402  (loads the repo's .env)
from aeotools.metrics import brand_metrics  # noqa: E402

CLAUDE = ["anthropic.claude-opus-5-5", "anthropic.claude-sonnet-5-5", "anthropic.claude-haiku-5-5"]


def credentials() -> str:
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        return "a Bedrock API key (AWS_BEARER_TOKEN_BEDROCK)"
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return "AWS access keys (AWS_ACCESS_KEY_ID)"
    if os.environ.get("AWS_PROFILE"):
        return f"the AWS profile {os.environ['AWS_PROFILE']!r}"
    return ""


def list_models() -> list[str]:
    """Print the text models this account can call and return one spec per model."""
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    client = boto3.client("bedrock", region_name=llm._bedrock_region())
    try:
        models = client.list_foundation_models(byOutputModality="TEXT")["modelSummaries"]
        profiles = [p for page in client.get_paginator("list_inference_profiles").paginate(typeEquals="SYSTEM_DEFINED")
                    for p in page["inferenceProfileSummaries"]]
    except (ClientError, BotoCoreError) as exc:
        print(f"These credentials cannot list models ({exc}).\nPick IDs from the model catalog and test them with --models.")
        return []
    # A model is called by its own ID when it supports on-demand use, otherwise through an
    # inference profile; prefer the global profile, then the US one.
    by_model = {}
    for p in profiles:
        for m in p.get("models", []):
            by_model.setdefault(m["modelArn"].rsplit("/", 1)[-1], []).append(p["inferenceProfileId"])
    rank = lambda i: (not i.startswith("global."), not i.startswith("us."), i)  # noqa: E731
    rows = {}
    for m in models:
        if m.get("modelLifecycle", {}).get("status") == "LEGACY":
            continue
        ids = [m["modelId"]] if "ON_DEMAND" in m.get("inferenceTypesSupported", []) else by_model.get(m["modelId"], [])
        if ids:
            rows[f"bedrock:{sorted(ids, key=rank)[0]}"] = (m["providerName"], m["modelName"])
    print(f"{len(rows)} text models callable in {llm._bedrock_region()}:")
    for spec, (provider, name) in sorted(rows.items(), key=lambda kv: kv[1]):
        guard = "" if llm.price(spec) != llm.DEFAULT_PRICE else "  (no price on file: guard assumes $5/$25)"
        print(f"  {provider:<14} {spec:<62} {name}{guard}")
    print("Claude in Bedrock uses its own endpoint: " + " ".join(f"bedrock:{c}" for c in CLAUDE) + "\n")
    return list(rows)


def smoke(specs: list[str]) -> None:
    items = build(3)
    item = next(it for it in items if it["condition"] == "baseline")
    n = len(items)
    print(f"One baseline prompt per model; projections are for the full run of {n:,} prompts.\n")
    total, results = 0.0, []
    for spec in specs:
        res = llm.complete(spec, SYSTEM, item["user"], max_tokens=4000)
        row = {"model": spec, "ok": not res.error, "error": res.error, "input_tokens": res.input_tokens,
               "output_tokens": res.output_tokens, "stop_reason": res.stop_reason, "words": len(res.text.split()),
               "latency_s": round(res.latency_s, 1), "price_on_file": llm.price(spec) != llm.DEFAULT_PRICE,
               "notes": res.notes}
        results.append(row)
        if res.error:
            print(f"  FAIL  {spec}\n        {res.error}")
            continue
        named = brand_metrics(res.text, item["brands"], item["target"])["mentioned"]
        pin, pout = llm.price(spec)
        row["projected_usd"] = round(n * (res.input_tokens * pin + res.output_tokens * pout) / 1e6, 2)
        total += row["projected_usd"]
        note = "" if row["price_on_file"] else "  (no price on file: assumes $5/$25 per M)"
        print(f"  ok    {spec}\n        {res.input_tokens} in / {res.output_tokens} out tokens, {res.latency_s:.1f}s, "
              f"{row['words']} words, target named: {bool(named)}, stop: {res.stop_reason}\n"
              f"        full run about ${row['projected_usd']:.2f}{note}"
              + (f"\n        ran with: {res.notes}" if res.notes else ""))
    (HERE / "data" / "bedrock_check.json").write_text(json.dumps(results, indent=1))
    print(f"\nProjected total for the models that answered: ${total:.2f}. "
          f"Output length varies, so set --max-spend about 25% above this. Saved to data/bedrock_check.json.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=[], help="bedrock:<model or inference-profile id> ...")
    ap.add_argument("--all", action="store_true", help="test every listed model and the Claude models")
    args = ap.parse_args()
    found = credentials()
    if not found:
        print("No AWS credentials found. Add AWS_BEARER_TOKEN_BEDROCK (or AWS_ACCESS_KEY_ID and "
              "AWS_SECRET_ACCESS_KEY) and AWS_REGION to the .env file at the repo root.")
        return 1
    print(f"Using {found}, region {llm._bedrock_region()}.\n")
    if args.all:
        listed = list_models()
        # Older Claude versions also appear in the listing (through Converse); only the Claude endpoint IDs are tested.
        smoke([f"bedrock:{c}" for c in CLAUDE] + [s for s in listed if "anthropic." not in s])
    elif args.models:
        smoke(args.models)
    else:
        list_models()
    return 0


if __name__ == "__main__":
    sys.exit(main())
