import base64
import json

import numpy as np
import pandas as pd
import pytest

from experiments.exp2_content_treatments.analyze_agentic import equal_model_mean, fixed_query_effects
from experiments.exp2_content_treatments.search_pool import CacheOnlyEmbedder, Engine


class FakeEmbedder:
    def get(self, texts):
        vectors = []
        for text in texts:
            if text == "apple":
                vectors.append(np.array([0.0, 1.0]))
            elif "apple" in text:
                vectors.append(np.array([1.0, 0.0]))
            elif "pear" in text:
                vectors.append(np.array([0.0, 1.0]))
            else:
                vectors.append(np.array([-1.0, 0.0]))
        return vectors


def test_cache_only_embedder_returns_present_vectors_and_fails_on_misses(tmp_path):
    text = "cached only"
    vector = np.full(256, 0.25, dtype=np.float32)
    entry = {"h": CacheOnlyEmbedder.key(text),
             "v": base64.b64encode(vector.tobytes()).decode()}
    path = tmp_path / "embeddings.jsonl"
    path.write_text(json.dumps(entry) + "\n")

    class NoFetchEmbedder(CacheOnlyEmbedder):
        def _fetch(self, texts):
            raise AssertionError("cache-only access must not fetch embeddings")

    embedder = NoFetchEmbedder(path)
    np.testing.assert_array_equal(embedder.get([text])[0], vector)
    with pytest.raises(RuntimeError, match="cache is missing 1"):
        embedder.get(["not cached"])


def test_engine_exposes_bm25_dense_and_fused_rankings():
    pool = {
        "a.example/": {"title": "apple page", "text": "red apple", "url": "a.example/"},
        "b.example/": {"title": "pear page", "text": "green pear", "url": "b.example/"},
        "c.example/": {"title": "orange page", "text": "sweet orange", "url": "c.example/"},
    }
    engine = Engine(pool, {}, FakeEmbedder())

    rankings = engine.rankings("apple")

    assert set(rankings) == {"bm25_only", "embedding_only", "fused"}
    assert rankings["bm25_only"][0] == "a.example/"
    assert rankings["embedding_only"][0] == "b.example/"
    assert engine.rank("apple") == rankings["fused"]
    assert engine.rank("apple", "bm25_only") == rankings["bm25_only"]
    with pytest.raises(ValueError, match="Unknown ranking method"):
        engine.rank("apple", "unknown")


def test_equal_model_mean_does_not_weight_models_by_query_trial_count():
    rows = []
    counts = {"model_a": 90, "model_b": 70}
    for model, n in counts.items():
        for i in range(n):
            rows.append({"model": model, "value": float(model == "model_a"), "scenario": f"s{i % 12}"})
    data = pd.DataFrame(rows)

    assert equal_model_mean(data, "value") == pytest.approx(0.5)
    assert data["value"].mean() == pytest.approx(90 / 160)


def test_fixed_query_pooled_effect_averages_model_means_equally():
    rows = []
    for model, n in (("model_a", 90), ("model_b", 70)):
        for i in range(n):
            scenario = f"s{i % 12}"
            trial = f"{scenario}-{i}"
            rows.extend([
                {"model": model, "scenario": scenario, "trial_id": trial,
                 "condition": "baseline", "top5": 0.0},
                {"model": model, "scenario": scenario, "trial_id": trial,
                 "condition": "third_party", "top5": float(model == "model_a")},
            ])
    effects = fixed_query_effects(pd.DataFrame(rows), ["model_a", "model_b"])
    pooled = effects[(effects["model"] == "pooled") & (effects["condition"] == "third_party")].iloc[0]

    assert pooled["effect"] == pytest.approx(0.5)
    assert pooled["n_models"] == 2
    assert pooled["n_model_trials"] == 160
    assert pooled["n"] == 90
