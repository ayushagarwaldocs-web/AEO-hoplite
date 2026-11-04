"""Audit a website's readiness for AI answer engines.

Checks what an AI crawler would experience: robots.txt policy for every known
AI agent, llms.txt, how the homepage responds to a declared bot versus a
browser, how much text exists without JavaScript, and entity markup.

    python -m aeotools.audit example.com
    python -m aeotools.audit example.com --render --json report.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

import requests

from . import robots as robotslib
from .bots import BOTS, TIERS
from .html_signals import extract, looks_like_challenge, visible_text, word_count

RESEARCH_TOKEN = "AEOHandbookResearch"
BOT_UA = f"Mozilla/5.0 (compatible; {RESEARCH_TOKEN}/1.0; AI-readiness audit)"
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              f"(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36 {RESEARCH_TOKEN}/1.0")
PROBE_PATH = "/aeo-probe/article.html"   # an arbitrary content path
MAX_BYTES = 3_000_000

CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
)


def origin_of(target: str) -> str:
    if "://" not in target:
        target = "https://" + target
    p = urlparse(target)
    return f"{p.scheme}://{p.netloc}"


def fetch(url: str, ua: str, timeout: float = 20.0) -> dict:
    """GET a URL, following up to 5 redirects. Never raises."""
    out = {"url": url, "status": None, "final_url": None, "content_type": "", "text": "",
           "bytes": 0, "error": None, "headers": {}}
    try:
        with requests.Session() as s:
            s.max_redirects = 5
            r = s.get(url, headers={"User-Agent": ua, "Accept": "text/html,text/plain,*/*;q=0.8",
                                    "Accept-Language": "en-US,en;q=0.8"},
                      timeout=timeout, stream=True)
            body = r.raw.read(MAX_BYTES, decode_content=True)
            ctype = r.headers.get("Content-Type", "")
            out.update(status=r.status_code, final_url=r.url, content_type=ctype,
                       headers={k.lower(): v for k, v in r.headers.items()},
                       bytes=len(body))
            # requests assumes ISO-8859-1 for text/* without a charset; most pages are UTF-8.
            charset = r.encoding if "charset" in ctype.lower() else "utf-8"
            out["text"] = body.decode(charset or "utf-8", errors="replace")
    except requests.RequestException as exc:
        out["error"] = type(exc).__name__
    except Exception as exc:  # decoding, ssl edge cases
        out["error"] = type(exc).__name__
    return out


def find_chrome() -> str | None:
    for c in CHROME_CANDIDATES:
        path = c if os.path.isabs(c) else shutil.which(c)
        if path and os.path.exists(path):
            return path
    return None


def render(url: str, chrome: str, ua: str = BROWSER_UA, timeout: int = 45) -> str | None:
    """Return the DOM after JavaScript runs, using headless Chrome."""
    with tempfile.TemporaryDirectory(prefix="aeo-chrome-") as profile:
        cmd = [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
               "--no-default-browser-check", "--mute-audio", "--hide-scrollbars",
               f"--user-data-dir={profile}", f"--user-agent={ua}",
               "--virtual-time-budget=10000", "--timeout=25000", "--dump-dom", url]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
        html = proc.stdout.decode("utf-8", errors="replace")
        return html if html.strip() else None


def robots_report(origin: str, ua: str = BOT_UA,
                  keep_text: bool = False) -> tuple[dict, robotslib.RobotsTxt | None]:
    res = fetch(origin + "/robots.txt", ua)
    rep = {"status": res["status"], "error": res["error"], "bytes": res["bytes"],
           "final_url": res["final_url"]}
    if keep_text:
        rep["text"] = res["text"][:500_000]
    status = res["status"]
    if res["error"] or status is None or status >= 500:
        rep["state"] = "unreachable"          # RFC 9309: treat as full disallow
        return rep, None
    if status >= 400:
        rep["state"] = "absent"               # RFC 9309: crawlers may fetch anything
        return rep, robotslib.parse("")
    text = res["text"]
    if robotslib.looks_like_html(text):
        rep["state"] = "html"                 # soft-404; no valid rules
        return rep, robotslib.parse("")
    rep["state"] = "ok"
    parsed = robotslib.parse(text)
    rep["groups"] = len(parsed.groups)
    rep["sitemaps"] = len(parsed.sitemaps)
    rep["content_signals"] = parsed.content_signals
    rep["content_usage"] = parsed.content_usage
    return rep, parsed


def bot_decisions(parsed: robotslib.RobotsTxt | None) -> dict:
    out = {}
    for b in BOTS:
        if parsed is None:
            out[b.token] = {"root": None, "probe": None, "named": None, "matched_by": None, "rule": None}
            continue
        root = parsed.decide(b.token, "/")
        probe = parsed.decide(b.token, PROBE_PATH)
        out[b.token] = {"root": root.allowed, "probe": probe.allowed, "named": parsed.names(b.token),
                        "matched_by": root.matched_by, "rule": root.rule}
    return out


def llms_report(origin: str, ua: str = BOT_UA) -> dict:
    res = fetch(origin + "/llms.txt", ua)
    text = res["text"].lstrip("﻿ \n\r\t")
    valid = (res["status"] == 200 and not robotslib.looks_like_html(text)
             and text.startswith("# "))
    return {"status": res["status"], "valid": valid, "bytes": res["bytes"] if valid else 0}


def audit(target: str, do_render: bool = False, chrome: str | None = None,
          respect_robots: bool = True, keep_robots_text: bool = False) -> dict:
    origin = origin_of(target)
    report: dict = {"target": target, "origin": origin}

    rob, parsed = robots_report(origin, keep_text=keep_robots_text)
    report["robots"] = rob
    report["bots"] = bot_decisions(parsed)
    if parsed is None:
        report["wildcard_root_blocked"] = None
    else:
        has_wildcard = any("*" in g.agents for g in parsed.groups)
        report["wildcard_root_blocked"] = has_wildcard and not parsed.allowed("*", "/")
    report["llms_txt"] = llms_report(origin)

    if respect_robots and parsed is not None and not parsed.allowed(RESEARCH_TOKEN, "/"):
        report["homepage_skipped"] = "robots.txt disallows our research agent"
        return report
    if respect_robots and parsed is None:
        report["homepage_skipped"] = "robots.txt unreachable"
        return report

    as_bot = fetch(origin + "/", BOT_UA)
    as_browser = fetch(origin + "/", BROWSER_UA)
    report["homepage_bot"] = {
        "status": as_bot["status"], "error": as_bot["error"], "bytes": as_bot["bytes"],
        "challenge": looks_like_challenge(as_bot["status"] or 0, as_bot["text"]) if as_bot["status"] else None,
    }
    ok_browser = as_browser["status"] == 200 and not looks_like_challenge(200, as_browser["text"])
    report["homepage_browser"] = {
        "status": as_browser["status"], "error": as_browser["error"], "bytes": as_browser["bytes"],
        "final_url": as_browser["final_url"],
        "challenge": looks_like_challenge(as_browser["status"] or 0, as_browser["text"]) if as_browser["status"] else None,
        "x_robots_tag": as_browser["headers"].get("x-robots-tag", ""),
    }
    if ok_browser:
        report["signals"] = extract(as_browser["text"]).to_dict()

    if do_render and ok_browser:
        chrome = chrome or find_chrome()
        if chrome:
            dom = render(as_browser["final_url"] or origin + "/", chrome)
            if dom:
                rendered_words = word_count(visible_text(dom))
                raw_words = report["signals"]["words"]
                report["rendered"] = {
                    "words": rendered_words,
                    "raw_share": round(min(raw_words / rendered_words, 1.0), 3) if rendered_words else None,
                }
    return report


# --- human-readable output -------------------------------------------------

def advice(rep: dict) -> list[str]:
    tips: list[str] = []
    bots = rep.get("bots", {})
    for operator, tiers in TIERS.items():
        for tier, token in tiers.items():
            d = bots.get(token, {})
            if d.get("root") is False and tier != "training":
                tips.append(f"{token} ({operator} {tier.replace('_', ' ')}) is blocked: "
                            f"you can be dropped from {operator}'s AI answers.")
    if rep.get("robots", {}).get("state") == "unreachable":
        tips.append("robots.txt is unreachable (5xx/timeout); compliant crawlers treat that as 'disallow all'.")
    if rep.get("wildcard_root_blocked"):
        tips.append("Your '*' group disallows '/', so any AI agent you have not named is blocked.")
    hb = rep.get("homepage_bot", {})
    hw = rep.get("homepage_browser", {})
    if hb.get("challenge") and hw.get("status") == 200:
        tips.append("A declared bot gets a challenge or error page while a browser gets content: "
                    "check WAF/CDN bot settings (e.g. Cloudflare AI Crawl Control).")
    sig = rep.get("signals") or {}
    if sig and sig.get("words", 0) < 150:
        tips.append(f"Only {sig.get('words')} words are visible without JavaScript; "
                    "most AI crawlers do not run JavaScript. Server-render key content.")
    rend = rep.get("rendered") or {}
    if rend.get("raw_share") is not None and rend["raw_share"] < 0.5:
        tips.append(f"Only {rend['raw_share']:.0%} of the rendered text exists in the raw HTML.")
    if sig and not sig.get("has_org_entity"):
        tips.append("No Organization-type JSON-LD found: add one with sameAs links to your official profiles.")
    if sig and sig.get("noai"):
        tips.append("A 'noai' robots meta tag is present (a training opt-out signal, not a standard directive).")
    if not rep.get("llms_txt", {}).get("valid"):
        tips.append("No valid /llms.txt (optional; low evidence of use by AI search, useful for docs and agents).")
    return tips


def print_report(rep: dict) -> None:
    print(f"\nAI-readiness audit: {rep['origin']}")
    rob = rep["robots"]
    print(f"robots.txt: {rob.get('state')} (HTTP {rob.get('status')})"
          + (f", content signals: {rob['content_signals']}" if rob.get("content_signals") else ""))
    print("\nAgent                 Operator      Category     Root  Named")
    for b in BOTS:
        d = rep["bots"][b.token]
        root = {True: "allow", False: "BLOCK", None: "?"}[d["root"]]
        print(f"{b.token:<21} {b.operator:<13} {b.category:<12} {root:<5} {'yes' if d['named'] else ''}")
    if "homepage_skipped" in rep:
        print(f"\nHomepage: skipped ({rep['homepage_skipped']})")
    else:
        hb, hw = rep["homepage_bot"], rep["homepage_browser"]
        print(f"\nHomepage as declared bot: HTTP {hb['status']}{' (challenge)' if hb['challenge'] else ''}")
        print(f"Homepage as browser:      HTTP {hw['status']}{' (challenge)' if hw['challenge'] else ''}")
        sig = rep.get("signals")
        if sig:
            print(f"Words without JavaScript: {sig['words']}"
                  + (f"  (rendered: {rep['rendered']['words']})" if rep.get("rendered") else ""))
            print(f"JSON-LD types: {', '.join(sig['jsonld_types']) or 'none'}; sameAs links: {sig['same_as_links']}")
    print(f"llms.txt: {'present' if rep['llms_txt']['valid'] else 'absent'}")
    tips = advice(rep)
    if tips:
        print("\nRecommendations:")
        for t in tips:
            print(f"  - {t}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="domain or URL, e.g. example.com")
    ap.add_argument("--render", action="store_true", help="also render with headless Chrome")
    ap.add_argument("--ignore-robots", action="store_true",
                    help="fetch the homepage even if robots.txt disallows this tool (your own site only)")
    ap.add_argument("--json", metavar="PATH", help="write the full report as JSON")
    args = ap.parse_args(argv)

    rep = audit(args.target, do_render=args.render, respect_robots=not args.ignore_robots)
    print_report(rep)
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(rep, fh, indent=2)
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
