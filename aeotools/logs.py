"""Summarise AI-agent traffic and AI referrals from web server access logs.

Reads Apache/Nginx "combined" format (also gzipped). For each known AI agent it
reports hits, status classes and top paths; for human visits it reports
referrals from AI assistants. With --verify it downloads the operators'
published IP ranges and flags hits whose IP does not match the claimed agent.

    python -m aeotools.logs /var/log/nginx/access.log
    python -m aeotools.logs access.log.gz --verify --top 15
"""

from __future__ import annotations

import argparse
import gzip
import ipaddress
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass

from .bots import BOTS, UA_PATTERNS

_LINE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+)[^"]*" '
    r'(?P<status>\d{3}) \S+ "(?P<referer>[^"]*)" "(?P<ua>[^"]*)"')

AI_REFERRERS = {
    "chatgpt.com": "ChatGPT", "chat.openai.com": "ChatGPT", "perplexity.ai": "Perplexity",
    "claude.ai": "Claude", "gemini.google.com": "Gemini", "copilot.microsoft.com": "Copilot",
    "edgeservices.bing.com": "Copilot", "chat.mistral.ai": "Mistral", "meta.ai": "Meta AI",
    "grok.com": "Grok", "duck.ai": "DuckDuckGo AI",
}

IP_RANGES = {
    "GPTBot": ["https://openai.com/gptbot.json"],
    "OAI-SearchBot": ["https://openai.com/searchbot.json"],
    "ChatGPT-User": ["https://openai.com/chatgpt-user.json"],
    "ClaudeBot": ["https://claude.com/crawling/bots.json"],
    "Claude-SearchBot": ["https://claude.com/crawling/bots.json"],
    "Claude-User": ["https://claude.com/crawling/bots.json"],
    "PerplexityBot": ["https://www.perplexity.ai/perplexitybot.json"],
    "Perplexity-User": ["https://www.perplexity.ai/perplexity-user.json"],
}
_CIDR = re.compile(r"[0-9a-fA-F:.]+/\d{1,3}")


@dataclass
class Hit:
    ip: str
    path: str
    status: int
    referer: str
    ua: str


def parse_line(line: str) -> Hit | None:
    m = _LINE.match(line)
    if not m:
        return None
    return Hit(m["ip"], m["path"], int(m["status"]), m["referer"], m["ua"])


def classify_agent(ua: str) -> str | None:
    low = ua.lower()
    # Longest pattern first so "claude-searchbot" wins over shorter overlaps.
    for token, pattern in sorted(UA_PATTERNS.items(), key=lambda kv: -len(kv[1])):
        if pattern in low:
            return token
    return None


def ai_referrer(referer: str) -> str | None:
    m = re.match(r"https?://([^/]+)", referer)
    if not m:
        return None
    host = m.group(1).lower()
    for domain, name in AI_REFERRERS.items():
        if host == domain or host.endswith("." + domain):
            return name
    return None


def load_ranges(tokens: set[str]) -> dict[str, list]:
    import requests
    cache: dict[str, list] = {}
    out: dict[str, list] = {}
    for token in tokens:
        nets = []
        for url in IP_RANGES.get(token, []):
            if url not in cache:
                try:
                    text = requests.get(url, timeout=20).text
                    cache[url] = [ipaddress.ip_network(c, strict=False) for c in _CIDR.findall(text)]
                except Exception:
                    cache[url] = []
            nets.extend(cache[url])
        if nets:
            out[token] = nets
    return out


def summarise(lines, verify: bool = False) -> dict:
    agents: dict[str, Counter] = defaultdict(Counter)
    paths: dict[str, Counter] = defaultdict(Counter)
    ips: dict[str, set] = defaultdict(set)
    referrals: Counter = Counter()
    landing: dict[str, Counter] = defaultdict(Counter)
    parsed = skipped = 0
    for line in lines:
        hit = parse_line(line)
        if hit is None:
            skipped += 1
            continue
        parsed += 1
        token = classify_agent(hit.ua)
        if token:
            agents[token]["hits"] += 1
            agents[token][f"{hit.status // 100}xx"] += 1
            paths[token][hit.path] += 1
            ips[token].add(hit.ip)
            continue
        source = ai_referrer(hit.referer)
        if source and hit.status < 400:
            referrals[source] += 1
            landing[source][hit.path.split("?")[0]] += 1

    unverified: dict[str, int] = {}
    if verify:
        ranges = load_ranges(set(agents) & set(IP_RANGES))
        for token, nets in ranges.items():
            bad = 0
            for ip in ips[token]:
                try:
                    addr = ipaddress.ip_address(ip)
                except ValueError:
                    bad += 1
                    continue
                if not any(addr in n for n in nets if n.version == addr.version):
                    bad += 1
            unverified[token] = bad
    return {"parsed": parsed, "skipped": skipped, "agents": agents, "paths": paths,
            "ip_counts": {t: len(s) for t, s in ips.items()}, "referrals": referrals,
            "landing": landing, "unverified_ips": unverified}


def _open(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", errors="replace")
    return open(path, errors="replace")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--top", type=int, default=5, help="top paths per agent")
    ap.add_argument("--verify", action="store_true", help="check IPs against operators' published ranges")
    args = ap.parse_args(argv)

    def lines():
        for p in args.logs:
            with _open(p) as fh:
                yield from fh

    s = summarise(lines(), verify=args.verify)
    print(f"Parsed {s['parsed']:,} lines ({s['skipped']:,} unparsed)\n")
    category = {b.token: b.category for b in BOTS}
    print(f"{'Agent':<22}{'Category':<12}{'Hits':>8}{'2xx':>7}{'3xx':>7}{'4xx':>7}{'5xx':>7}{'IPs':>6}")
    for token, c in sorted(s["agents"].items(), key=lambda kv: -kv[1]["hits"]):
        print(f"{token:<22}{category.get(token, ''):<12}{c['hits']:>8}{c['2xx']:>7}{c['3xx']:>7}"
              f"{c['4xx']:>7}{c['5xx']:>7}{s['ip_counts'][token]:>6}")
    if s["unverified_ips"]:
        print("\nIPs outside the operator's published ranges (possible spoofing):")
        for token, n in s["unverified_ips"].items():
            print(f"  {token}: {n} of {s['ip_counts'][token]}")
    for token, c in s["paths"].items():
        print(f"\nTop paths for {token}:")
        for path, n in c.most_common(args.top):
            print(f"  {n:>6}  {path}")
    if s["referrals"]:
        print("\nVisits referred by AI assistants:")
        for source, n in s["referrals"].most_common():
            top = ", ".join(p for p, _ in s["landing"][source].most_common(3))
            print(f"  {source:<14}{n:>7}   top landing pages: {top}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
