"""Visibility metrics for generated answers.

Brand-level metrics (did the answer name the brand, and where):
  mentioned, rank (1 = first brand named), top_pick, mention_share

Source-level metrics (did the answer cite the brand's page, and how much):
  citation_share     share of [n] citation markers pointing at the source
  word_share         share of answer words in sentences citing the source
  pawc               position-adjusted word count, as defined in the GEO paper
                     (Aggarwal et al., KDD 2024): sentence word counts weighted
                     by exp(-position / number_of_sentences). A sentence that
                     cites k sources contributes 1/k of its words to each.
"""

from __future__ import annotations

import math
import re

_CITE_RE = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]")
_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9*\"'(\[])|\n+")
_WORD_RE = re.compile(r"\w+")


def sentences(answer: str) -> list[str]:
    parts = [p.strip() for p in _SENT_RE.split(answer)]
    return [p for p in parts if p and _WORD_RE.search(p)]


def citations_in(sentence: str) -> list[int]:
    found: list[int] = []
    for group in _CITE_RE.findall(sentence):
        for piece in re.split(r"\s*,\s*", group):
            if re.search(r"[–-]", piece):
                lo, hi = (int(x) for x in re.split(r"\s*[–-]\s*", piece))
                found.extend(range(lo, hi + 1) if 0 < hi - lo < 10 else [lo, hi])
            else:
                found.append(int(piece))
    return found


def brand_positions(answer: str, brands: list[str]) -> dict[str, int]:
    """Character offset of each brand's first mention (absent brands omitted)."""
    out = {}
    for b in brands:
        m = re.search(r"(?<!\w)" + re.escape(b) + r"(?!\w)", answer, flags=re.I)
        if m:
            out[b] = m.start()
    return out


def brand_metrics(answer: str, brands: list[str], target: str) -> dict:
    pos = brand_positions(answer, brands)
    order = sorted(pos, key=pos.get)
    counts = {b: len(re.findall(r"(?<!\w)" + re.escape(b) + r"(?!\w)", answer, flags=re.I)) for b in brands}
    total = sum(counts.values())
    rank = order.index(target) + 1 if target in pos else None
    return {
        "mentioned": target in pos,
        "rank": rank,
        "top_pick": rank == 1,
        "n_brands_mentioned": len(pos),
        "mention_share": counts[target] / total if total else 0.0,
    }


def source_metrics(answer: str, source_index: int, n_sources: int) -> dict:
    sents = sentences(answer)
    total_words = sum(len(_WORD_RE.findall(s)) for s in sents) or 1
    n = len(sents) or 1
    cites_all = 0
    cites_target = 0
    words = 0.0
    pawc = 0.0
    for i, s in enumerate(sents):
        cited = [c for c in dict.fromkeys(citations_in(s)) if 1 <= c <= n_sources]
        cites_all += len(cited)
        if source_index in cited:
            cites_target += 1
            share = len(_WORD_RE.findall(s)) / len(cited)
            words += share
            pawc += share * math.exp(-i / n)
    return {
        "cited": cites_target > 0,
        "citation_share": cites_target / cites_all if cites_all else 0.0,
        "word_share": words / total_words,
        "pawc": pawc / total_words,
        "n_citations": cites_all,
    }
