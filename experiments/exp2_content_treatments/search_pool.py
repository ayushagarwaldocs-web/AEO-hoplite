"""Page pool and search engine for the agentic search experiment (specified in README.md, "Agentic search").

Each scenario's pool holds the main design's five brands, seven more fictional brands made the same way (cached in
data/brands_extra.json) and the buyer's guide: 13 pages per scenario, 390 in one index. In an episode the target's
page, or for the third-party condition the guide, is the version for the episode's condition, exactly as in the main
design (build_corpus.build); every other page is unedited.

search() ranks pages by hybrid retrieval: Okapi BM25 (k1 = 1.2, b = 0.75; title and text, lower-cased, stop words
removed, Harman's S-stemmer) and cosine similarity of OpenAI text-embedding-3-small vectors (256 dimensions), fused
by reciprocal rank fusion (k = 60); ties go to the higher BM25 score, then the URL. Embeddings are cached in
data/agentic_embeddings.jsonl so every search can be replayed.

    python search_pool.py --build      # make the extra brands (DNS checks) and embed every page version
    python search_pool.py --demo "best project management tool for an agency"
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import random
import re
import sys
import threading
from collections import Counter
from pathlib import Path

import numpy as np
import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import build_corpus as bc  # noqa: E402
from scenarios import SCENARIOS  # noqa: E402
from aeotools.metrics import sentences  # noqa: E402

EXTRA_FILE = HERE / "data" / "brands_extra.json"
EMB_FILE = HERE / "data" / "agentic_embeddings.jsonl"
K_EXTRA = 7
TOP_N = 5
K1, B, RRF_K = 1.2, 0.75, 60
EMB_MODEL, EMB_DIMS = "text-embedding-3-small", 256
CONDITIONS = ["baseline", "third_party", "citations", "statistics", "answer_first", "keyword_stuffing", "injection"]

_STOP = set("""a about above after again all also am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have having he her
here hers him his how i if in into is it its itself just me more most my no nor not of off on once only or other
our ours out over own same she should so some such than that the their theirs them then there these they this
those through to too under until up very was we were what whats when where which while who whom why will with
would you your yours""".split())


# --- text processing ---------------------------------------------------------------------------------------

def s_stem(word: str) -> str:
    """Harman's S-stemmer (1991): removes plural endings only."""
    if len(word) > 3 and word.endswith("ies") and not word.endswith(("eies", "aies")):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("es") and not word.endswith(("aes", "ees", "oes")):
        return word[:-1]
    if len(word) > 2 and word.endswith("s") and not word.endswith(("us", "ss")):
        return word[:-1]
    return word


def terms(text: str) -> list[str]:
    return [s_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower().replace("'", "")) if w not in _STOP]


def norm_url(url: str) -> str:
    u = re.sub(r"^https?://", "", (url or "").strip().lower())
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/").split("#")[0]


# --- extra brands ------------------------------------------------------------------------------------------

def load_extra(make: bool = False) -> dict:
    """Seven more brands per scenario, generated like the main design's and DNS-checked; cached."""
    if EXTRA_FILE.exists():
        return json.loads(EXTRA_FILE.read_text())
    if not make:
        raise SystemExit("data/brands_extra.json is missing; run: python search_pool.py --build")
    cache = bc.load_brands()  # reserves every name already used
    bc._prepare_pool(2500)  # same name order as the main design's pool, extended
    extra = {}
    for sc in SCENARIOS:
        rng = random.Random(f"{sc['id']}:extra-brands")
        used = {frozenset(b["features"]) for b in cache[sc["id"]]["brands"]}
        brands = []
        for _ in range(K_EXTRA):
            core = bc._take("brand")
            fmt = bc._LOCAL_FMT.get(sc["category"], "{n}") if sc["kind"] == "local" else "{n}"
            name = fmt.format(n=core)
            domain = (core + (name.replace(core, "").replace(" ", "").lower() if sc["kind"] == "local" else "")
                      ).lower() + rng.choice(bc._TLDS)
            while True:
                feats = tuple(rng.sample(sc["features"], 3))
                if frozenset(feats) not in used:
                    used.add(frozenset(feats))
                    break
            brands.append({
                "core": core, "name": name, "domain": domain, "features": list(feats),
                "extra": rng.choice(sc["extras"]), "best_for": rng.choice(sc["best_for"]), "price": bc._price(sc, rng),
                "year": rng.randint(2008, 2021), "city": rng.choice(bc._CITIES), "hood": rng.choice(bc._HOODS),
                "closing": rng.choice(bc._CLOSINGS),
            })
        extra[sc["id"]] = brands
    EXTRA_FILE.write_text(json.dumps(extra, indent=1))
    return extra


# --- episodes ----------------------------------------------------------------------------------------------

def _page(sc: dict, b: dict, text: str) -> dict:
    return {"url": f"https://{b['domain']}/", "title": bc.title_for(sc, b), "text": text, "brand": b["core"],
            "scenario": sc["id"], "role": "brand"}


def episodes(trials: int = 3, conditions: list[str] | None = None, make: bool = False) -> tuple[list[dict], dict]:
    """(episodes, pool): one episode per trial and condition, and the unedited pool keyed by normalised URL.

    Targets and guide features use the same seeds as build_corpus.build, so trials match the main design."""
    cache, extra = bc.load_brands(), load_extra(make)
    pool: dict[str, dict] = {}
    eps: list[dict] = []
    for sc in SCENARIOS:
        brands = cache[sc["id"]]["brands"]
        guide_site = cache[sc["id"]]["guide_site"]
        srng = random.Random(f"{sc['id']}:setup")
        guide_features = srng.sample(sc["features"], 2)
        targets = srng.sample(range(bc.K), trials)
        for b in brands + extra[sc["id"]]:
            p = _page(sc, b, bc.main_paragraph(sc, b))
            pool[norm_url(p["url"])] = p
        title, url, body = bc.guide_doc(sc, guide_site, guide_features, None, "recommend", ())
        guide_url = norm_url(url)
        pool[guide_url] = {"url": url, "title": title, "text": body, "brand": None, "scenario": sc["id"], "role": "guide"}
        for t, target_i in enumerate(targets):
            target = brands[target_i]
            shortlist = [brands[(target_i + 1) % bc.K]["name"], brands[(target_i + 2) % bc.K]["name"]]
            shortlist.insert(t % 3, target["name"])
            for cond in conditions or CONDITIONS:
                override = {}
                if cond in bc.GUIDE_MODES:
                    gt, gu, gb = bc.guide_doc(sc, guide_site, guide_features, target, bc.GUIDE_MODES[cond],
                                              tuple(shortlist))
                    override[guide_url] = {**pool[guide_url], "title": gt, "text": gb}
                elif cond != "baseline":
                    p = _page(sc, target, bc.target_body(sc, target, cond))
                    override[norm_url(p["url"])] = p
                eps.append({
                    "trial_id": f"{sc['id']}-{t}", "scenario": sc["id"], "vertical": sc["vertical"], "condition": cond,
                    "query": sc["query"], "target": target["core"], "target_url": norm_url(f"https://{target['domain']}/"),
                    "guide_url": guide_url, "brands": [b["core"] for b in brands + extra[sc["id"]]],
                    "override": override,
                })
    return eps, pool


# --- embeddings --------------------------------------------------------------------------------------------

class Embedder:
    """OpenAI text-embedding-3-small at 256 dimensions, cached on disk by text hash (thread-safe)."""

    def __init__(self, path: Path = EMB_FILE):
        self.path, self.lock, self.vecs = path, threading.Lock(), {}
        if path.exists():
            for line in path.open():
                try:  # several runs append to the same cache; skip a line a concurrent write may have broken
                    r = json.loads(line)
                    v = np.frombuffer(base64.b64decode(r["v"]), dtype=np.float32)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
                if v.shape == (EMB_DIMS,):
                    self.vecs[r["h"]] = v

    @staticmethod
    def key(text: str) -> str:
        return hashlib.sha1(f"{EMB_MODEL}:{EMB_DIMS}:{text}".encode()).hexdigest()

    def _fetch(self, texts: list[str]) -> list[np.ndarray]:
        from aeotools.llm import _post_with_retry  # loads .env
        r = _post_with_retry("https://api.openai.com/v1/embeddings",
                             {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                              "Content-Type": "application/json"},
                             {"model": EMB_MODEL, "input": texts, "dimensions": EMB_DIMS})
        if isinstance(r, str):
            raise RuntimeError(f"embedding request failed: {r[:200]}")
        out = [np.asarray(d["embedding"], dtype=np.float32) for d in sorted(r.json()["data"], key=lambda d: d["index"])]
        return [v / (np.linalg.norm(v) or 1.0) for v in out]

    def get(self, texts: list[str]) -> list[np.ndarray]:
        keys = [self.key(t) for t in texts]
        with self.lock:
            missing = list(dict.fromkeys(t for t, k in zip(texts, keys) if k not in self.vecs))
        for i in range(0, len(missing), 256):
            batch = missing[i:i + 256]
            vecs = self._fetch(batch)
            with self.lock, self.path.open("a") as fh:
                for t, v in zip(batch, vecs):
                    k = self.key(t)
                    if k not in self.vecs:
                        self.vecs[k] = v
                        fh.write(json.dumps({"h": k, "v": base64.b64encode(v.astype(np.float32).tobytes()).decode()}) + "\n")
        with self.lock:
            return [self.vecs[k] for k in keys]


def doc_text(p: dict) -> str:
    return f"{p['title']}\n{p['text']}"


# --- search engine -----------------------------------------------------------------------------------------

class Engine:
    """Hybrid BM25 + dense retrieval over one episode's pool (the unedited pool plus the episode's overrides)."""

    def __init__(self, pool: dict, override: dict, embedder: Embedder):
        self.pages = {**pool, **override}
        self.urls = sorted(self.pages)
        self.emb = embedder
        toks = [terms(doc_text(self.pages[u])) for u in self.urls]
        self.tf = [Counter(t) for t in toks]
        self.len = np.array([len(t) for t in toks], dtype=float)
        self.avgdl = float(self.len.mean())
        df = Counter(w for t in toks for w in set(t))
        n = len(self.urls)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self.dvec = np.stack(embedder.get([doc_text(self.pages[u]) for u in self.urls]))

    def bm25(self, q: list[str]) -> np.ndarray:
        s = np.zeros(len(self.urls))
        for w in set(q):
            idf = self.idf.get(w)
            if idf is None:
                continue
            f = np.array([tf.get(w, 0) for tf in self.tf], dtype=float)
            s += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * self.len / self.avgdl))
        return s

    def rank(self, query: str) -> list[str]:
        """All URLs, best first."""
        bm = self.bm25(terms(query))
        qv = self.emb.get([query])[0]
        dense = self.dvec @ qv
        idx = range(len(self.urls))
        r_bm = {i: r for r, i in enumerate(sorted(idx, key=lambda i: (-bm[i], self.urls[i])), 1)}
        r_de = {i: r for r, i in enumerate(sorted(idx, key=lambda i: (-dense[i], self.urls[i])), 1)}
        fused = {i: 1 / (RRF_K + r_bm[i]) + 1 / (RRF_K + r_de[i]) for i in idx}
        return [self.urls[i] for i in sorted(idx, key=lambda i: (-fused[i], -bm[i], self.urls[i]))]

    def snippet(self, url: str, query: str) -> str:
        sents = sentences(self.pages[url]["text"])
        q = set(terms(query))
        scores = [len(q & set(terms(s))) for s in sents]
        best = max(range(len(sents)), key=lambda i: (scores[i], -i)) if sents else 0
        chosen = sents[best:best + 1]
        if chosen and len(chosen[0].split()) < 20 and best + 1 < len(sents):
            chosen.append(sents[best + 1])
        words = " ".join(chosen).split()
        return " ".join(words[:40]) + (" …" if len(words) > 40 else "")

    def search(self, query: str, n: int = TOP_N) -> tuple[str, list[str]]:
        urls = self.rank(query)[:n]
        lines = [f"[{i}] {self.pages[u]['title']}\n{self.pages[u]['url']}\n{self.snippet(u, query)}"
                 for i, u in enumerate(urls, 1)]
        return "\n\n".join(lines), urls

    def open(self, url: str) -> tuple[str, str | None]:
        key = norm_url(url)
        if key not in self.pages:  # a bare domain or another path on a pool site: each site has one page
            same = [u for u in self.urls if u.split("/")[0] == key.split("/")[0]]
            key = same[0] if len(same) == 1 else key
        p = self.pages.get(key)
        if p is None:
            return "Error: page not found. Use a URL from the search results.", None
        return f"{p['title']}\n{p['url']}\n\n{p['text']}", key


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--demo")
    args = ap.parse_args()
    eps, pool = episodes(make=args.build)
    print(f"{len(eps)} episodes per model, {len(pool)} unedited pages")
    if args.build:
        texts = [doc_text(p) for p in pool.values()]
        texts += [doc_text(p) for e in eps for p in e["override"].values()]
        texts = list(dict.fromkeys(texts))
        Embedder().get(texts)
        print(f"embedded {len(texts)} page versions")
    if args.demo:
        e = next(x for x in eps if x["condition"] == "baseline")
        eng = Engine(pool, e["override"], Embedder())
        text, urls = eng.search(args.demo)
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
