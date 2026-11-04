"""The robots.txt templates must do exactly what their names promise."""

from pathlib import Path

from aeotools.robots import parse

T = Path(__file__).resolve().parents[1] / "templates"
TRAINING = ["GPTBot", "ClaudeBot", "Google-Extended", "Applebot-Extended", "CCBot"]
ANSWERS = ["OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot", "Claude-User", "PerplexityBot", "Perplexity-User"]


def load(name):
    return parse((T / name).read_text())


def test_answers_not_training():
    r = load("robots-answers-not-training.txt")
    assert all(not r.allowed(b) for b in TRAINING)
    assert all(r.allowed(b, "/pricing") for b in ANSWERS)
    assert r.allowed("Googlebot") and r.allowed("Bingbot")


def test_allow_all():
    r = load("robots-allow-all.txt")
    assert all(r.allowed(b, "/blog/post") for b in TRAINING + ANSWERS)
    assert not r.allowed("GPTBot", "/admin/users")


def test_block_ai_keeps_search_engines():
    r = load("robots-block-ai.txt")
    assert all(not r.allowed(b) for b in TRAINING + ANSWERS)
    assert r.allowed("Googlebot") and r.allowed("Bingbot")
