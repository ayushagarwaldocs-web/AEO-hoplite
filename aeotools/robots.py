"""A small RFC 9309 robots.txt evaluator that also explains its decisions.

Python's urllib.robotparser applies the first matching rule rather than the
longest one, and it cannot tell you whether a bot was named explicitly or only
caught by the "*" group. Both matter when auditing AI-crawler policies, so this
module implements the RFC directly:

- Groups are formed by consecutive user-agent lines; rules before any
  user-agent line are ignored.
- A crawler obeys every group naming its product token (case-insensitive,
  combined), otherwise every "*" group, otherwise nothing.
- The longest matching path pattern wins; on a tie, Allow wins.
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


@dataclass
class Rule:
    allow: bool
    pattern: str

    def __post_init__(self) -> None:
        anchored = self.pattern.endswith("$")
        body = self.pattern[:-1] if anchored else self.pattern
        regex = ".*".join(re.escape(part) for part in body.split("*"))
        self._re = re.compile(regex + ("$" if anchored else ""))

    def matches(self, path: str) -> bool:
        return self._re.match(path) is not None


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
        for rule in (r for g in groups for r in g.rules):
            if not rule.matches(path):
                continue
            if (best is None or len(rule.pattern) > len(best.pattern)
                    or (len(rule.pattern) == len(best.pattern) and rule.allow and not best.allow)):
                best = rule
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
