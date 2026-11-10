from aeotools.html_signals import extract, looks_like_challenge, visible_text

PAGE = """<!doctype html><html lang="en"><head>
<title>Acme Widgets</title>
<meta name="description" content="Widgets for teams">
<meta name="robots" content="index, follow, noai">
<link rel="canonical" href="https://acme.example/">
<script type="application/ld+json">
{"@context": "https://schema.org", "@graph": [
  {"@type": "Organization", "name": "Acme", "sameAs": ["https://www.linkedin.com/company/acme",
   "https://www.wikidata.org/wiki/Q1"]},
  {"@type": "WebSite", "name": "Acme"}]}
</script>
<script>var hidden = "these words do not count";</script>
</head><body><h1>Acme Widgets</h1><p>Durable widgets for busy teams.</p>
<noscript>Please enable JavaScript to use the configurator.</noscript></body></html>"""


def test_extracts_core_signals():
    s = extract(PAGE)
    assert s.title == "Acme Widgets"
    assert s.meta_description and s.canonical
    assert s.h1_count == 1 and s.lang == "en"
    assert s.noai and not s.nosnippet
    assert s.jsonld_blocks == 1
    assert s.jsonld_types == ["Organization", "WebSite"]
    assert s.has_org_entity and s.same_as_links == 2
    assert s.noscript_warning
    assert s.words == 7  # "Acme Widgets Durable widgets for busy teams"


def test_detects_empty_spa_root():
    s = extract('<html><body><div id="root"></div><script src="app.js"></script></body></html>')
    assert s.spa_empty_root and s.words == 0


def test_invalid_jsonld_is_skipped():
    s = extract('<html><head><script type="application/ld+json">{oops</script></head><body>x</body></html>')
    assert s.jsonld_blocks == 0 and not s.has_org_entity


def test_challenge_detection():
    cf = "<html><head><title>Just a moment...</title></head><body>Checking your browser</body></html>"
    assert looks_like_challenge(403, cf)
    assert looks_like_challenge(200, cf)
    assert not looks_like_challenge(200, PAGE)


def test_visible_text_ignores_explicit_hidden_content():
    html = """<body><p>Visible</p><div hidden>Hidden attribute words</div>
    <span style=" DISPLAY : none !important; display:block">Hidden inline words</span>
    <section style="visibility: COLLAPSE">Collapsed words</section>
    <div style="opacity: 0">Transparent words</div>
    <div style="display:none; display:block">Visible override</div>
    <p style="content-visibility:hidden">Skipped content</p></body>"""
    text = visible_text(html)
    assert "Visible" in text and "Visible override" in text
    for hidden in ("Hidden attribute", "Hidden inline", "Collapsed", "Transparent", "Skipped"):
        assert hidden not in text


def test_extract_word_count_uses_explicitly_visible_text():
    s = extract('<body><p>Readable text</p><div hidden>Unseen words</div>'
                '<span style="display:none">Also unseen</span></body>')
    assert s.words == 2


def test_nested_hidden_content_is_removed_without_revisiting_destroyed_tags():
    html = ('<body><div hidden><span>Hidden child</span></div>'
            '<section style="display:none"><p><em>Also hidden</em></p></section>'
            '<p>Visible text</p></body>')
    assert visible_text(html) == "Visible text"
    assert extract(html).words == 2
