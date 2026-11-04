from aeotools.logs import ai_referrer, classify_agent, parse_line, summarise

LINES = [
    '20.1.2.3 - - [03/Nov/2026:10:00:00 +0000] "GET /pricing HTTP/1.1" 200 512 "-" '
    '"Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot"',
    '20.1.2.4 - - [03/Nov/2026:10:00:01 +0000] "GET /docs HTTP/1.1" 403 0 "-" '
    '"Mozilla/5.0 (compatible; Claude-SearchBot/1.0; +https://www.anthropic.com)"',
    '1.2.3.4 - - [03/Nov/2026:10:00:02 +0000] "GET /pricing?utm_source=chatgpt.com HTTP/1.1" 200 900 '
    '"https://chatgpt.com/" "Mozilla/5.0 (Macintosh) Safari/605.1"',
    'garbage line',
]


def test_parse_and_classify():
    hit = parse_line(LINES[0])
    assert hit.path == "/pricing" and hit.status == 200
    assert classify_agent(hit.ua) == "ChatGPT-User"
    assert classify_agent(parse_line(LINES[1]).ua) == "Claude-SearchBot"
    assert classify_agent("Mozilla/5.0 (Macintosh) Safari/605.1") is None


def test_referrers():
    assert ai_referrer("https://chatgpt.com/") == "ChatGPT"
    assert ai_referrer("https://www.perplexity.ai/search?q=x") == "Perplexity"
    assert ai_referrer("https://example.com/") is None


def test_summary_counts():
    s = summarise(LINES)
    assert s["parsed"] == 3 and s["skipped"] == 1
    assert s["agents"]["ChatGPT-User"]["2xx"] == 1
    assert s["agents"]["Claude-SearchBot"]["4xx"] == 1
    assert s["referrals"]["ChatGPT"] == 1
    assert s["landing"]["ChatGPT"]["/pricing"] == 1
