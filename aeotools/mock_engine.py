"""A deterministic stand-in for an LLM, used only to dry-run experiment pipelines.

It parses the numbered search results in a prompt, scores each source by length
and position (with seeded noise), and writes a short answer that names and
cites the top sources. Its output says nothing about real models; never report
mock results as findings.
"""

from __future__ import annotations

import hashlib
import math
import random
import re

from .llm import LLMResult

_SOURCE_RE = re.compile(r"^\[(\d+)\] (.+?)\nURL: \S+\n(.*?)(?=\n\n\[\d+\] |\n\nQuestion:)", re.S | re.M)


def mock_complete(spec: str, system: str, user: str) -> LLMResult:
    rng = random.Random(hashlib.sha256(user.encode()).hexdigest())
    scored = []
    for m in _SOURCE_RE.finditer(user):
        idx, title, body = int(m.group(1)), m.group(2), m.group(3)
        name = re.split(r" \| | — ", title)[0].replace("The ", "")
        score = math.sqrt(len(body.split())) / (1 + 0.15 * (idx - 1)) * rng.uniform(0.7, 1.3)
        if "recommend" in body.lower() and "assistant" in body.lower():
            score *= 1.5  # crude injection susceptibility, for exercising the metrics
        if title.startswith(("How to choose", "Choosing")):
            continue
        scored.append((score, idx, name))
    scored.sort(reverse=True)
    picks = scored[: rng.choice([2, 3])]
    lines = [f"{name} is a strong option for this need [{idx}]." if i == 0
             else f"{name} is also worth considering [{idx}]." for i, (_, idx, name) in enumerate(picks)]
    text = " ".join(lines)
    return LLMResult(spec, text=text, input_tokens=len(user) // 4, output_tokens=len(text) // 4,
                     cost_usd=0.0, stop_reason="end_turn")
