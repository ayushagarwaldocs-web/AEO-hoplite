"""Live audit of production assistants (README, robustness item 6).

Reads data/audit/perplexity.jsonl, data/audit/gemini.jsonl and data/audit/chatgpt.jsonl and reports:
  1. the share of cited sources that belong to a vendor in the question's category (a company that makes or
     sells what the question asks about, including retailers and the vendor's own blog or docs) versus
     third parties (publishers, review sites, other companies, forums, app stores);
  2. for Perplexity, whether each cited URL is allowed for PerplexityBot by its site's robots.txt (Study 1 code).

Vendor labels are by hand, per question, from the domain or source name; they are listed below so that a reader
can check or change them. Usage:  python3 analyze_audit.py [--robots]
"""
import json
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))

AUDIT = ROOT / "data" / "audit"
RESULTS = ROOT / "results"

# Perplexity: domains that sell in the question's category (per scenario).
PPLX_VENDORS = {
    "pm_agency": {"asana.com", "ones.com", "larksuite.com", "juntrax.com"},
    "crm_realestate": {"learn.realscout.com", "freshworks.com", "blog.hubspot.com"},
    "email_ecom": {"sequenzy.com", "brevo.com", "sender.net", "blog.hubspot.com"},
    "accounting_freelance": {"flowlancerr.com"},
    "password_smb": {"kaspersky.com", "blog.lastpass.com"},
    "helpdesk_saas": {"helpscout.com", "tidio.com", "helpdesk.com", "freshworks.com", "helply.com"},
    "hosting_django": {"fly.io", "render.com"},
    "monitoring_mobile": {"sentry.io", "docs.sentry.io", "firebase.google.com", "shakebug.com"},
    "vacuum_pets": {"tapo.com"},
    "grinder_espresso": {"clivecoffee.com", "coffeebros.com"},
    "shoes_flatfeet": {"in.puma.com", "asics.com"},
    "tent_backpacking": {"rei.com"},
    "bootcamp_career": {"tripleten.com", "scrimba.com", "coddy.tech"},
    "language_spanish": {"busuu.com", "praktika.ai", "lingualive.ai", "spanish.kwiziq.com", "ihmadrid.com"},
    "tutoring_math": {"fusionacademy.com", "preply.com", "cuemath.com"},
    "budget_couples": {"stash.com", "pocketguard.com"},
    "dogfood_picky": {"petsmart.com"},
    "wp_hosting": {"hostinger.com", "pantheon.io"},
    "ebike_commute": {"upway.co", "aventon.com", "rei.com"},
}

# Gemini shows source names, not URLs.
GEMINI_VENDORS = {
    "Ravetree", "Stackby", "Sell.Do", "Freshworks", "Drip", "Insider One", "Minutemailer", "WorksBuddy AI",
    "Airwallex", "viaSocket", "The LastPass Blog", "Bitwarden", "Macha AI", "Robylon", "Tidio", "Alloy Software",
    "Fly.io", "Appliku", "Aiven", "Shakebug", "Narwal Canada", "Espresso Machines", "Coffee Bros.", "LEVEL8",
    "Boot.dev", "Fluently", "ACE Academy", "getfinny.app", "HomeLedger", "Kwik Pets", "Cozymeal", "Aipas Bike",
}


def host(u: str) -> str:
    return (urllib.parse.urlparse(u).hostname or "").removeprefix("www.")


def load(name):
    p = AUDIT / f"{name}.jsonl"
    return [json.loads(l) for l in open(p)] if p.exists() else []


def perplexity_rows():
    rows = []
    for r in load("perplexity"):
        seen = []
        for u in r["urls"]:
            u2 = u.split("#")[0]
            if u2 not in seen:
                seen.append(u2)
        for u in seen:
            h = host(u)
            rows.append({"scenario": r["scenario"], "url": u, "domain": h,
                         "vendor": h in PPLX_VENDORS.get(r["scenario"], set()),
                         "incognito": r.get("incognito")})
    return rows


def robots_check(rows):
    from aeotools import audit as aud
    cache = {}
    for row in rows:
        p = urllib.parse.urlparse(row["url"])
        origin = f"{p.scheme}://{p.hostname}"
        if origin not in cache:
            rep, parsed = aud.robots_report(origin)
            cache[origin] = (rep["state"], parsed)
        state, parsed = cache[origin]
        path = p.path or "/"
        row["robots_state"] = state
        if parsed is None:
            row["pplx_allowed"], row["pplx_named"], row["google_ext_allowed"] = None, None, None
            row["pplx_user_allowed"] = None
        else:
            row["pplx_allowed"] = parsed.allowed("PerplexityBot", path)
            row["pplx_user_allowed"] = parsed.allowed("Perplexity-User", path)
            row["pplx_named"] = parsed.names("PerplexityBot")
            row["google_ext_allowed"] = parsed.allowed("Google-Extended", path)
    return rows


def main():
    RESULTS.mkdir(exist_ok=True)
    rows = perplexity_rows()
    if "--robots" in sys.argv:
        rows = robots_check(rows)
    with open(RESULTS / "audit_perplexity_citations.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    n = len(rows)
    nq = len({r["scenario"] for r in rows})
    vend = sum(r["vendor"] for r in rows)
    per_q = Counter(r["scenario"] for r in rows if r["vendor"])
    q_majority = sum(1 for s in {r["scenario"] for r in rows}
                     if per_q[s] * 2 > sum(1 for r in rows if r["scenario"] == s))
    domains = Counter(r["domain"] for r in rows)
    out = {"perplexity": {"questions": nq, "citations": n, "vendor": vend,
                          "vendor_pct": round(100 * vend / n, 1),
                          "questions_with_vendor": len(per_q), "questions_vendor_majority": q_majority,
                          "distinct_domains": len(domains),
                          "incognito_questions": len({r["scenario"] for r in rows if r["incognito"] is True}),
                          "top_domains": domains.most_common(8)}}
    if "--robots" in sys.argv:
        known = [r for r in rows if r["pplx_allowed"] is not None]
        out["perplexity"]["robots"] = {
            "checked": len(rows), "unreachable": sum(r["robots_state"] == "unreachable" for r in rows),
            "pplx_blocked": sum(r["pplx_allowed"] is False for r in known),
            "pplx_blocked_domains": sorted({r["domain"] for r in known if r["pplx_allowed"] is False}),
            "pplx_named": sum(bool(r["pplx_named"]) for r in known),
            "pplx_blocked_named": sum(r["pplx_allowed"] is False and bool(r["pplx_named"]) for r in known),
            "pplx_blocked_user": sum(r["pplx_allowed"] is False and r["pplx_user_allowed"] is False for r in known),
            "pplx_blocked_questions": len({r["scenario"] for r in known if r["pplx_allowed"] is False}),
            "google_ext_blocked": sum(r["google_ext_allowed"] is False for r in known)}

    g = load("gemini")
    gs = [(r["scenario"], s) for r in g for s in r.get("sources", [])]
    gv = sum(s in GEMINI_VENDORS for _, s in gs)
    out["gemini"] = {"questions": len(g), "sources": len(gs), "vendor": gv,
                     "vendor_pct": round(100 * gv / len(gs), 1) if gs else None,
                     "questions_without_sources": sum(1 for r in g if not r.get("sources"))}
    c = load("chatgpt")
    if c:
        out["chatgpt"] = {
            "questions": len(c),
            "with_cited_sources": sum(1 for r in c if r.get("urls")),
            "cited_sources": sum(len(r.get("urls", [])) for r in c),
            "searched": sum(1 for r in c if r.get("searched") is True),
            "images_only": sum(1 for r in c if r.get("searched") == "images only"),
            "with_product_links": sum(1 for r in c if r.get("product_links")),
            "product_links": sum(len(r.get("product_links", [])) for r in c),
            "with_top_pick": sum(1 for r in c if r.get("top_pick")),
            "asked_back": sum(1 for r in c if "asked" in r.get("answer_head", "").lower()),
            "unpersonalized_temporary": sum(1 for r in c if r.get("temporary") and r.get("unpersonalized"))}
    (RESULTS / "audit_summary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
