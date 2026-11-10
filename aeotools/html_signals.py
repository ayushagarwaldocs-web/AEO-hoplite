"""Extract the signals an answer engine can read from a page's HTML.

Everything here works on HTML as delivered (no JavaScript), which is what most
AI crawlers see. Pass a rendered DOM instead to measure what a browser sees.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

from bs4 import BeautifulSoup

_HIDDEN_TAGS = ("script", "style", "noscript", "template", "svg", "iframe", "head")
_WORD_RE = re.compile(r"\w+", re.UNICODE)
_SPA_ROOT_RE = re.compile(
    r'<(div|main)[^>]+id=["\'](root|app|__next|___gatsby|svelte)["\'][^>]*>\s*</\1>', re.I)
_ENTITY_TYPES = {
    "organization", "corporation", "localbusiness", "newsmediaorganization",
    "educationalorganization", "governmentorganization", "ngo", "onlinestore",
    "store", "medicalorganization", "airline", "bank", "financialservice",
    "hotel", "restaurant", "collegeoruniversity", "website",
}


@dataclass
class PageSignals:
    words: int = 0
    title: str = ""
    meta_description: bool = False
    h1_count: int = 0
    lang: str = ""
    canonical: bool = False
    meta_robots: str = ""
    noai: bool = False
    nosnippet: bool = False
    jsonld_blocks: int = 0
    jsonld_types: list[str] = field(default_factory=list)
    has_org_entity: bool = False
    same_as_links: int = 0
    microdata: bool = False
    spa_empty_root: bool = False
    noscript_warning: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def visible_text(html: str) -> str:
    """Return text outside known non-visible elements and explicit hiding styles.

    This recognises HTML's ``hidden`` attribute and common inline CSS hiding
    declarations. It cannot infer visibility controlled by external stylesheets.
    """
    soup = BeautifulSoup(html, "lxml")
    _remove_nonvisible(soup)
    body = soup.body or soup
    return " ".join(body.get_text(" ").split())


def _inline_style_hides(style: str) -> bool:
    declarations: dict[str, tuple[bool, int, str]] = {}
    style = re.sub(r"/\*.*?\*/", "", style, flags=re.S)
    for order, declaration in enumerate(style.split(";")):
        if ":" not in declaration:
            continue
        name, value = declaration.split(":", 1)
        name, value = name.strip().lower(), value.strip().lower()
        important = bool(re.search(r"!\s*important\s*$", value))
        value = re.sub(r"!\s*important\s*$", "", value).strip()
        if not name:
            continue
        previous = declarations.get(name)
        if previous is None or (important, order) >= (previous[0], previous[1]):
            declarations[name] = (important, order, value)

    values = {name: item[2] for name, item in declarations.items()}
    if values.get("display") == "none":
        return True
    if values.get("visibility") in {"hidden", "collapse"}:
        return True
    if values.get("content-visibility") == "hidden":
        return True
    try:
        if float(values.get("opacity", "").rstrip("%")) == 0:
            return True
    except ValueError:
        pass
    return False


def _remove_nonvisible(soup: BeautifulSoup) -> None:
    for tag in soup(_HIDDEN_TAGS):
        tag.decompose()
    for tag in soup.find_all(True):
        if tag.decomposed:
            continue
        if tag.has_attr("hidden") or _inline_style_hides(tag.get("style", "")):
            tag.decompose()


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _walk_jsonld(node, types: list[str], same_as: list[str]) -> None:
    if isinstance(node, list):
        for item in node:
            _walk_jsonld(item, types, same_as)
        return
    if not isinstance(node, dict):
        return
    t = node.get("@type")
    for value in (t if isinstance(t, list) else [t]):
        if isinstance(value, str):
            types.append(value)
    links = node.get("sameAs")
    if isinstance(links, str):
        same_as.append(links)
    elif isinstance(links, list):
        same_as.extend(x for x in links if isinstance(x, str))
    for key, value in node.items():
        if key not in ("@type", "sameAs") and isinstance(value, (dict, list)):
            _walk_jsonld(value, types, same_as)


def extract(html: str) -> PageSignals:
    s = PageSignals()
    s.spa_empty_root = bool(_SPA_ROOT_RE.search(html))
    soup = BeautifulSoup(html, "lxml")

    if soup.title and soup.title.string:
        s.title = " ".join(soup.title.string.split())[:200]
    s.meta_description = bool(soup.find("meta", attrs={"name": re.compile("^description$", re.I)}))
    s.h1_count = len(soup.find_all("h1"))
    if soup.html and soup.html.get("lang"):
        s.lang = soup.html.get("lang")
    s.canonical = bool(soup.find("link", rel=lambda v: v and "canonical" in v))

    robots = [m.get("content", "") for m in soup.find_all("meta", attrs={"name": re.compile("^robots$", re.I)})]
    s.meta_robots = ", ".join(robots).lower()
    s.noai = "noai" in s.meta_robots
    s.nosnippet = "nosnippet" in s.meta_robots

    types: list[str] = []
    same_as: list[str] = []
    for block in soup.find_all("script", type=re.compile("ld\\+json", re.I)):
        raw = block.string or block.get_text() or ""
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        s.jsonld_blocks += 1
        _walk_jsonld(data, types, same_as)
    s.jsonld_types = sorted(set(types))
    s.has_org_entity = any(t.lower() in _ENTITY_TYPES - {"website"} for t in types)
    s.same_as_links = len(set(same_as))
    s.microdata = bool(soup.find(attrs={"itemtype": True}))

    for ns in soup.find_all("noscript"):
        if re.search(r"enable javascript|javascript (is )?(required|disabled)|turn on javascript",
                     ns.get_text(" "), re.I):
            s.noscript_warning = True
            break

    _remove_nonvisible(soup)
    body = soup.body or soup
    s.words = word_count(" ".join(body.get_text(" ").split()))
    return s


_CHALLENGE_MARKERS = (
    "just a moment...", "cf-chl", "challenge-platform", "attention required! | cloudflare",
    "px-captcha", "captcha-delivery", "datadome", "incapsula incident", "_incapsula_resource",
    "access denied</title>", "request unsuccessful. incapsula", "perimeterx", "verify you are human",
    "pardon our interruption", "are you a robot",
)


def looks_like_challenge(status: int, html: str) -> bool:
    """Heuristic: is this a bot wall rather than the real page?"""
    head = html[:20000].lower()
    if status in (401, 403, 429, 503) and (len(head) < 20000 or any(m in head for m in _CHALLENGE_MARKERS)):
        return True
    return any(m in head for m in _CHALLENGE_MARKERS) and word_count(visible_text(html[:200000])) < 150
