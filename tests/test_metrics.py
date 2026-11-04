import math

from aeotools.metrics import brand_metrics, citations_in, sentences, source_metrics

ANSWER = ("For a small agency, Velmora is the strongest pick because it includes client portals [2]. "
          "Quintrel is cheaper but lacks time tracking [4]. "
          "Both integrate with Slack [2][4].")


def test_sentence_split_and_citations():
    s = sentences(ANSWER)
    assert len(s) == 3
    assert citations_in("Both work [2][4].") == [2, 4]
    assert citations_in("See [1, 3] and [5-6].") == [1, 3, 5, 6]


def test_brand_metrics():
    m = brand_metrics(ANSWER, ["Velmora", "Quintrel", "Zarvik"], "Quintrel")
    assert m["mentioned"] and m["rank"] == 2 and not m["top_pick"]
    assert m["n_brands_mentioned"] == 2
    assert math.isclose(m["mention_share"], 0.5)
    absent = brand_metrics(ANSWER, ["Velmora", "Zarvik"], "Zarvik")
    assert not absent["mentioned"] and absent["rank"] is None


def test_source_metrics():
    m = source_metrics(ANSWER, 2, 6)
    assert m["cited"]
    assert math.isclose(m["citation_share"], 2 / 4)
    assert 0 < m["word_share"] < 1 and 0 < m["pawc"] <= m["word_share"]
    none = source_metrics(ANSWER, 5, 6)
    assert not none["cited"] and none["pawc"] == 0


def test_out_of_range_citations_are_ignored():
    m = source_metrics("Pick A [9].", 1, 6)
    assert m["n_citations"] == 0 and m["citation_share"] == 0


def test_wilson_interval():
    from aeotools.tracker import wilson
    lo, hi = wilson(5, 10)
    assert round(lo, 2) == 0.24 and round(hi, 2) == 0.76
    assert wilson(0, 0) == (0.0, 0.0)
