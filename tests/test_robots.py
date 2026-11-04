from aeotools.robots import looks_like_html, parse


def test_empty_file_allows_everything():
    r = parse("")
    assert r.allowed("GPTBot", "/")
    assert r.decide("GPTBot").matched_by == "none"


def test_explicit_group_beats_wildcard():
    r = parse("User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /\n")
    assert not r.allowed("GPTBot", "/")
    assert r.decide("GPTBot").matched_by == "explicit"
    assert r.allowed("OAI-SearchBot", "/")
    assert r.decide("OAI-SearchBot").matched_by == "wildcard"


def test_wildcard_block_catches_unnamed_ai_agents():
    r = parse("User-agent: Googlebot\nAllow: /\n\nUser-agent: *\nDisallow: /\n")
    assert r.allowed("Googlebot", "/")
    assert not r.allowed("Claude-SearchBot", "/")
    assert not r.names("Claude-SearchBot")


def test_longest_match_wins():
    r = parse("User-agent: *\nDisallow: /\nAllow: /blog\n")
    assert not r.allowed("x", "/")
    assert r.allowed("x", "/blog/post")


def test_allow_wins_a_tie():
    r = parse("User-agent: *\nDisallow: /page\nAllow: /page\n")
    assert r.allowed("x", "/page")


def test_wildcards_and_end_anchor():
    r = parse("User-agent: *\nDisallow: /*.pdf$\nDisallow: /private*/\n")
    assert not r.allowed("x", "/files/a.pdf")
    assert r.allowed("x", "/files/a.pdf?download=1")
    assert not r.allowed("x", "/private-area/doc")


def test_groups_for_same_agent_are_combined():
    r = parse("User-agent: GPTBot\nDisallow: /a\n\nUser-agent: GPTBot\nDisallow: /b\n")
    assert not r.allowed("GPTBot", "/a")
    assert not r.allowed("GPTBot", "/b")
    assert r.allowed("GPTBot", "/c")


def test_multiple_agents_share_a_group():
    r = parse("User-agent: GPTBot\nUser-agent: ClaudeBot\nDisallow: /\n")
    assert not r.allowed("GPTBot")
    assert not r.allowed("ClaudeBot")
    assert r.allowed("Claude-User")


def test_version_suffix_and_case_are_ignored():
    r = parse("user-agent: gptbot/1.2\nDISALLOW: /\n")
    assert not r.allowed("GPTBot", "/")


def test_token_match_is_exact_not_prefix():
    r = parse("User-agent: Claude\nDisallow: /\n")
    assert r.allowed("Claude-User", "/")


def test_rules_before_any_user_agent_are_ignored():
    r = parse("Disallow: /\nUser-agent: *\nAllow: /\n")
    assert r.allowed("x", "/")


def test_empty_disallow_means_allow():
    r = parse("User-agent: *\nDisallow:\n")
    assert r.allowed("x", "/anything")


def test_sitemap_and_content_signals_do_not_break_groups():
    text = ("User-agent: *\nContent-Signal: search=yes, ai-train=no\nAllow: /\n"
            "Sitemap: https://example.com/sitemap.xml\n\nUser-agent: CCBot\nDisallow: /\n")
    r = parse(text)
    assert r.content_signals == ["search=yes, ai-train=no"]
    assert r.sitemaps == ["https://example.com/sitemap.xml"]
    assert r.allowed("GPTBot")
    assert not r.allowed("CCBot")


def test_comments_are_stripped():
    r = parse("User-agent: * # everyone\nDisallow: /tmp # scratch\n")
    assert not r.allowed("x", "/tmp/file")


def test_html_soft_404_detection():
    assert looks_like_html("<!DOCTYPE html><html><head></head></html>")
    assert not looks_like_html("User-agent: *\nDisallow:\n")
