"""A small RFC 9309 robots.txt evaluator that also explains its decisions.

Python's urllib.robotparser applies the first matching rule rather than the
longest one, and it cannot tell you whether a bot was named explicitly or only
caught by the "*" group. Both matter when auditing AI-crawler policies, so this
module implements the RFC directly:

- Groups are formed by consecutive user-agent lines; rules before any
  user-agent line are ignored.
- A crawler obeys every group naming its product token (case-insensitive,
  combined), otherwise every "*" group, otherwise nothing.
- The matching rule whose match has the most URI octets wins; on a tie, Allow wins.
- "*" matches any sequence and a trailing "$" anchors the end of the path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_KEYS = {
    "user-agent": "user-agent", "useragent": "user-agent", "user agent": "user-agent",
    "allow": "allow", "disallow": "disallow", "dissallow": "disallow", "disalow": "disallow",
    "sitemap": "sitemap", "content-signal": "content-signal", "content-usage": "content-usage",
    "crawl-delay": "crawl-delay",
}
_TOKEN_RE = re.compile(r"[A-Za-z_-]+")
_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_RESERVED = frozenset(":/?#[]@!$&'()*+,;=")
_PERCENT_RE = re.compile(r"%([0-9a-fA-F]{2})")


def _normalize_path(value: str) -> str:
    """Normalize URI path octets for robots.txt comparison."""
    out: list[str] = []
    i = 0
    while i < len(value):
        char = value[i]
        if char == "%":
            match = _PERCENT_RE.match(value, i)
            if match:
                octet = int(match.group(1), 16)
                decoded = chr(octet)
                out.append(decoded if decoded in _UNRESERVED else f"%{octet:02X}")
                i += 3
                continue
            out.append("%25")
        elif ord(char) > 0x7F:
            out.extend(f"%{octet:02X}" for octet in char.encode("utf-8"))
        elif char in _RESERVED and char != "/":
            out.append(f"%{ord(char):02X}")
        else:
            out.append(char)
        i += 1
    return "".join(out)


def _octet_length(value: str) -> int:
    """Count URI octets in normalized text; each percent escape encodes one octet."""
    return len(_PERCENT_RE.sub("x", value))


@dataclass
class Rule:
    allow: bool
    pattern: str

    def __post_init__(self) -> None:
        anchored = self.pattern.endswith("$")
        body = self.pattern[:-1] if anchored else self.pattern
        regex = ".*".join(re.escape(_normalize_path(part)) for part in body.split("*"))
        self._re = re.compile(regex + ("$" if anchored else ""), re.DOTALL)

    def matches(self, path: str) -> bool:
        return self.match_length(path) is not None

    def match_length(self, path: str) -> int | None:
        match = self._re.match(_normalize_path(path))
        return _octet_length(match.group(0)) if match else None


@dataclass
class Group:
    agents: list[str] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)


@dataclass
class Decision:
    allowed: bool
    matched_by: str          # "explicit", "wildcard" or "none"
    rule: str | None         # the deciding rule, e.g. "Disallow: /"


@dataclass
class RobotsTxt:
    groups: list[Group]
    sitemaps: list[str]
    content_signals: list[str]
    content_usage: list[str]

    def _groups_for(self, token: str) -> tuple[list[Group], str]:
        token = token.lower()
        named = [g for g in self.groups if token in g.agents]
        if named:
            return named, "explicit"
        wildcard = [g for g in self.groups if "*" in g.agents]
        if wildcard:
            return wildcard, "wildcard"
        return [], "none"

    def names(self, token: str) -> bool:
        """True if some group names this token explicitly."""
        return any(token.lower() in g.agents for g in self.groups)

    def decide(self, token: str, path: str = "/") -> Decision:
        groups, how = self._groups_for(token)
        best: Rule | None = None
        best_length = -1
        for rule in (r for g in groups for r in g.rules):
            match_length = rule.match_length(path)
            if match_length is None:
                continue
            if (best is None or match_length > best_length
                    or (match_length == best_length and rule.allow and not best.allow)):
                best = rule
                best_length = match_length
        if best is None:
            return Decision(True, how, None)
        label = f"{'Allow' if best.allow else 'Disallow'}: {best.pattern}"
        return Decision(best.allow, how, label)

    def allowed(self, token: str, path: str = "/") -> bool:
        return self.decide(token, path).allowed


def _agent_token(value: str) -> str:
    value = value.strip()
    if value.startswith("*"):
        return "*"
    match = _TOKEN_RE.match(value)
    return match.group(0).lower() if match else value.lower()


def parse(text: str) -> RobotsTxt:
    groups: list[Group] = []
    current: Group | None = None
    in_agent_run = False
    sitemaps: list[str] = []
    signals: list[str] = []
    usage: list[str] = []

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = _KEYS.get(key.strip().lower())
        value = value.strip()
        if key is None:
            continue
        if key == "user-agent":
            if current is None or not in_agent_run:
                current = Group()
                groups.append(current)
            current.agents.append(_agent_token(value))
            in_agent_run = True
            continue
        if key == "sitemap":
            sitemaps.append(value)
            continue
        if key == "content-signal":
            signals.append(value)
            continue
        if key == "content-usage":
            usage.append(value)
            continue
        in_agent_run = False
        if current is None or key == "crawl-delay":
            continue
        if value:  # an empty Allow/Disallow matches nothing
            current.rules.append(Rule(allow=(key == "allow"), pattern=value))

    return RobotsTxt(groups, sitemaps, signals, usage)


def looks_like_html(text: str) -> bool:
    head = text.lstrip()[:512].lower()
    return head.startswith("<!doctype html") or head.startswith("<html") or "<head" in head
