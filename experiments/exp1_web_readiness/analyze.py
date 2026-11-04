"""Analyse Experiment 1 and write tables and figures.

    python analyze.py

Outputs go to results/ (CSV + JSON) and ../../paper/figures/ (PNG + PDF).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from protego import Protego

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from aeotools import plotstyle as ps  # noqa: E402
from aeotools.robots import parse  # noqa: E402

RAW = HERE / "data" / "raw"
RES = HERE / "results"
FIG = ROOT / "paper" / "figures"

TRAIN = ["GPTBot", "ClaudeBot", "Google-Extended", "Applebot-Extended", "CCBot", "Meta-ExternalAgent", "Bytespider"]
AI_SEARCH = ["OAI-SearchBot", "Claude-SearchBot", "PerplexityBot", "DuckAssistBot"]
USER = ["ChatGPT-User", "Claude-User", "Perplexity-User", "Meta-ExternalFetcher", "MistralAI-User"]
CLASSIC = ["Googlebot", "Bingbot", "Applebot"]
CORE_TRAIN = ["GPTBot", "ClaudeBot", "Google-Extended", "CCBot"]
CORE_RETRIEVAL = ["OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot", "Claude-User", "PerplexityBot", "Perplexity-User"]
LEGACY = ["anthropic-ai", "Claude-Web"]
POLICY_ORDER = ["Open to AI crawlers", "Blocks training only", "Blocks some retrieval", "Blocks all retrieval"]
SECTOR_LABELS = {
    "ai_companies": "AI companies", "news_media": "News and media", "saas_b2b": "B2B SaaS",
    "devtools_cloud": "Developer and cloud", "ecommerce_retail": "E-commerce and retail",
    "consumer_brands": "Consumer brands", "consumer_tech": "Consumer tech", "banking": "Banking",
    "fintech_insurance": "Fintech and insurance", "healthcare": "Healthcare", "travel_hospitality": "Travel and hospitality",
    "education": "Education", "government_intl": "Government and IGOs", "food_restaurants": "Food and restaurants",
    "automotive": "Automotive", "telecom": "Telecom", "entertainment": "Entertainment and media apps",
    "social_reviews_ugc": "Social, reviews and UGC", "reference_science": "Reference and science",
    "professional_enterprise": "Professional and enterprise", "real_estate_home": "Real estate and home",
    "nonprofit": "Nonprofits",
}


def load(sites_path: Path = RAW / "sites.jsonl", renders_path: Path = RAW / "renders.jsonl") -> pd.DataFrame:
    sites = [json.loads(line) for line in sites_path.open()]
    renders = {}
    if renders_path.exists():
        for line in renders_path.open():
            r = json.loads(line)
            renders[r["domain"]] = r
    rows = []
    for s in sites:
        rep = s["report"]
        state = rep["robots"]["state"]
        reachable = state != "unreachable"
        row = {"domain": s["domain"], "sector": s["sector"], "rank": s.get("rank"), "band": s.get("band"),
               "robots_state": state, "reachable": reachable,
               "content_signal": bool(rep["robots"].get("content_signals")),
               "content_usage": bool(rep["robots"].get("content_usage")),
               "wildcard_root_blocked": rep.get("wildcard_root_blocked"),
               "llms_txt": bool(rep["llms_txt"]["valid"])}
        for token, d in rep["bots"].items():
            row[f"blocked:{token}"] = (d["root"] is False) if reachable else np.nan
            row[f"named:{token}"] = bool(d["named"]) if reachable else np.nan
            row[f"via:{token}"] = d["matched_by"]
            row[f"probe_blocked:{token}"] = (d["probe"] is False) if reachable else np.nan
        sig = rep.get("signals")
        hb, hw = rep.get("homepage_bot", {}), rep.get("homepage_browser", {})
        row["homepage_skipped"] = "homepage_skipped" in rep
        row["homepage_ok"] = sig is not None
        row["bot_wall"] = bool(hb.get("challenge")) and sig is not None
        row["scripted_blocked"] = (not row["homepage_skipped"]) and sig is None
        # Refused or challenged at the edge whichever user agent we sent (vs. a network-level failure)
        row["edge_refused"] = row["scripted_blocked"] and not hw.get("error") and (
            hw.get("status") in (401, 403, 429, 503) or bool(hw.get("challenge")))
        row["homepage_status"] = hw.get("status")
        if sig:
            row.update(raw_words=sig["words"], spa_empty_root=sig["spa_empty_root"],
                       noscript_warning=sig["noscript_warning"], has_jsonld=sig["jsonld_blocks"] > 0,
                       has_org_entity=sig["has_org_entity"], same_as_links=sig["same_as_links"],
                       noai_meta=sig["noai"], nosnippet_meta=sig["nosnippet"])
        r = renders.get(s["domain"])
        if r and r.get("ok") and r.get("rendered_words"):
            row["rendered_words"] = r["rendered_words"]
            row["raw_share"] = min(r["raw_words"] / r["rendered_words"], 1.0)
        rows.append(row)
    df = pd.DataFrame(rows)
    for col in ("raw_words", "rendered_words", "raw_share", "has_org_entity"):
        if col not in df:  # e.g. no homepage could be fetched, or no renders for this sample
            df[col] = np.nan

    reach = df["reachable"]
    b = lambda tokens: df[[f"blocked:{t}" for t in tokens]].astype(float)
    df.loc[reach, "any_train_block"] = b(CORE_TRAIN)[reach].max(axis=1).astype(bool)
    df.loc[reach, "any_retrieval_block"] = b(CORE_RETRIEVAL)[reach].max(axis=1).astype(bool)
    df.loc[reach, "all_retrieval_block"] = b(CORE_RETRIEVAL)[reach].min(axis=1).astype(bool)

    def policy(r):
        if not r["reachable"]:
            return None
        if r["all_retrieval_block"]:
            return POLICY_ORDER[3]
        if r["any_retrieval_block"]:
            return POLICY_ORDER[2]
        if r["any_train_block"]:
            return POLICY_ORDER[1]
        return POLICY_ORDER[0]
    df["policy"] = df.apply(policy, axis=1)

    def inherited(r):
        if not r["reachable"]:
            return np.nan
        return any(r[f"blocked:{t}"] and r[f"via:{t}"] == "wildcard" for t in CORE_RETRIEVAL)
    df["retrieval_block_inherited"] = df.apply(inherited, axis=1)
    named = lambda tokens: df[[f"named:{t}" for t in tokens]].astype(float).max(axis=1).astype(bool)
    df.loc[reach, "names_any_ai"] = named(TRAIN + AI_SEARCH + USER)[reach]
    df.loc[reach, "names_legacy"] = named(LEGACY)[reach]
    df.loc[reach, "names_current_anthropic"] = named(["ClaudeBot", "Claude-SearchBot", "Claude-User"])[reach]
    df["thin_raw"] = df["raw_words"] < 150
    df["js_dependent"] = (df["raw_share"] < 0.5) & (df["rendered_words"] >= 150)
    # Blocks the training crawler but leaves the same company's search crawler open
    df.loc[reach, "openai_split"] = (df["blocked:GPTBot"] == True) & (df["blocked:OAI-SearchBot"] == False)  # noqa: E712
    df.loc[reach, "anthropic_split"] = (df["blocked:ClaudeBot"] == True) & (df["blocked:Claude-SearchBot"] == False)  # noqa: E712
    return df


def pct(series) -> float:
    s = pd.Series(series).dropna().astype(float)
    return round(100 * s.mean(), 1) if len(s) else float("nan")


def protego_agreement() -> dict:
    agree = total = 0
    disagreements = []
    for line in (RAW / "robots_raw.jsonl").open():
        r = json.loads(line)
        if r["state"] != "ok":
            continue
        ours = parse(r["text"])
        theirs = Protego.parse(r["text"])
        for token in CORE_TRAIN + CORE_RETRIEVAL:
            a = ours.allowed(token, "/")
            b = theirs.can_fetch(f"https://{r['domain']}/", token)
            total += 1
            agree += a == b
            if a != b and len(disagreements) < 20:
                disagreements.append({"domain": r["domain"], "token": token, "ours": a, "protego": b})
    return {"comparisons": total, "agreement_pct": round(100 * agree / total, 2), "examples": disagreements}


def inexact_tokens() -> dict:
    """Sites naming a shortened form of an AI agent token (e.g. 'Perplexity' for 'PerplexityBot').

    RFC 9309 matches product tokens exactly, so whether such a group applies depends on each
    crawler's own parser; our block rates treat them as not applying (a conservative count).
    """
    tokens = [t.lower() for t in TRAIN + AI_SEARCH + USER]
    genuine = {t.lower() for t in TRAIN + AI_SEARCH + USER + CLASSIC + LEGACY}
    sites, examples = 0, {}
    for line in (RAW / "robots_raw.jsonl").open():
        r = json.loads(line)
        if r["state"] != "ok":
            continue
        named = {a for g in parse(r["text"]).groups for a in g.agents}
        loose = sorted({a for a in named if a not in genuine and a != "*" and len(a) >= 4
                        and any(t.startswith(a) for t in tokens)})
        if loose:
            sites += 1
            for a in loose:
                examples[a] = examples.get(a, 0) + 1
    return {"sites": sites, "variants": dict(sorted(examples.items(), key=lambda kv: -kv[1]))}


def summarize(df: pd.DataFrame) -> dict:
    reach = df[df["reachable"]]
    ok = df[df["homepage_ok"]]
    rendered = df[df["raw_share"].notna()]
    out = {
        "sites": len(df), "sectors": df["sector"].nunique(),
        "robots_states": df["robots_state"].value_counts().to_dict(),
        "reachable_robots": int(df["reachable"].sum()),
        "block_rate_pct": {t: pct(reach[f"blocked:{t}"]) for t in TRAIN + AI_SEARCH + USER + CLASSIC + LEGACY},
        "named_rate_pct": {t: pct(reach[f"named:{t}"]) for t in TRAIN + AI_SEARCH + USER + LEGACY},
        "policy_pct": {p: pct(reach["policy"] == p) for p in POLICY_ORDER},
        "any_train_block_pct": pct(reach["any_train_block"]),
        "any_retrieval_block_pct": pct(reach["any_retrieval_block"]),
        "all_retrieval_block_pct": pct(reach["all_retrieval_block"]),
        "retrieval_block_inherited_pct_of_retrieval_blockers": pct(
            reach.loc[reach["any_retrieval_block"] == True, "retrieval_block_inherited"]),  # noqa: E712
        "wildcard_root_blocked_pct": pct(reach["wildcard_root_blocked"]),
        "openai_split_pct_of_gptbot_blockers": pct(reach.loc[reach["blocked:GPTBot"] == True, "openai_split"]),  # noqa: E712
        "anthropic_split_pct_of_claudebot_blockers": pct(
            reach.loc[reach["blocked:ClaudeBot"] == True, "anthropic_split"]),  # noqa: E712
        "names_any_ai_pct": pct(reach["names_any_ai"]),
        "legacy_without_current_anthropic_pct": pct(
            reach.loc[reach["names_legacy"] == True, "names_current_anthropic"] == False),  # noqa: E712
        "legacy_named_sites": int((reach["names_legacy"] == True).sum()),  # noqa: E712
        "content_signal_pct": pct(reach["content_signal"]), "content_usage_pct": pct(reach["content_usage"]),
        "llms_txt_pct": pct(df["llms_txt"]),
        "homepage": {"ok": int(df["homepage_ok"].sum()), "skipped_by_robots": int(df["homepage_skipped"].sum()),
                     "no_usable_html": int(df["scripted_blocked"].sum())},
        "bot_wall_pct_of_ok": pct(ok["bot_wall"]),
        "thin_raw_pct_of_ok": pct(ok["thin_raw"]), "spa_empty_root_pct_of_ok": pct(ok["spa_empty_root"]),
        "median_raw_words": float(ok["raw_words"].median()),
        "rendered_sites": len(rendered),
        "median_raw_share": round(float(rendered["raw_share"].median()), 3) if len(rendered) else None,
        "js_dependent_pct_of_rendered": pct(rendered["js_dependent"]) if len(rendered) else None,
        "jsonld_pct_of_ok": pct(ok["has_jsonld"]), "org_entity_pct_of_ok": pct(ok["has_org_entity"]),
        "median_same_as_links_with_org": float(ok.loc[ok["has_org_entity"] == True, "same_as_links"].median()),  # noqa: E712
        "noai_meta_pct_of_ok": pct(ok["noai_meta"]),
    }
    return out


def by_sector(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sector, g in df.groupby("sector"):
        reach = g[g["reachable"]]
        ok = g[g["homepage_ok"]]
        rend = g[g["raw_share"].notna()]
        rows.append({
            "sector": SECTOR_LABELS.get(sector, sector), "sites": len(g),
            "GPTBot": pct(reach["blocked:GPTBot"]), "OAI-SearchBot": pct(reach["blocked:OAI-SearchBot"]),
            "ChatGPT-User": pct(reach["blocked:ChatGPT-User"]),
            "ClaudeBot": pct(reach["blocked:ClaudeBot"]), "Claude-SearchBot": pct(reach["blocked:Claude-SearchBot"]),
            "Claude-User": pct(reach["blocked:Claude-User"]),
            "PerplexityBot": pct(reach["blocked:PerplexityBot"]), "Google-Extended": pct(reach["blocked:Google-Extended"]),
            "CCBot": pct(reach["blocked:CCBot"]),
            "any_retrieval_block": pct(reach["any_retrieval_block"]),
            "llms_txt": pct(g["llms_txt"]), "org_entity": pct(ok["has_org_entity"]) if len(ok) else np.nan,
            "thin_raw": pct(ok["thin_raw"]) if len(ok) else np.nan,
            "js_dependent": pct(rend["js_dependent"]) if len(rend) else np.nan,
        })
    return pd.DataFrame(rows).sort_values("any_retrieval_block", ascending=False)


# --- figures -----------------------------------------------------------------

def fig_block_rates(summary: dict) -> None:
    groups = [("Training", TRAIN, ps.SERIES[0]), ("AI search index", AI_SEARCH, ps.SERIES[1]),
              ("Live fetch for a user", USER, ps.SERIES[2])]
    labels, values, colors, ys = [], [], [], []
    y = 0
    gap_positions = []
    for name, tokens, color in groups:
        for t in sorted(tokens, key=lambda t: -summary["block_rate_pct"][t]):
            labels.append(t)
            values.append(summary["block_rate_pct"][t])
            colors.append(color)
            ys.append(y)
            y += 1
        gap_positions.append((name, ys[-len(tokens)], ys[-1], color))
        y += 0.8
    fig, ax = ps.plt.subplots(figsize=(6.4, 4.6))
    ax.set_xlim(0, max(values) * 1.18)
    ax.set_ylim(y - 0.6, -0.8)
    for yy, v, c in zip(ys, values, colors):
        ps.hbar(ax, yy, 0, v, c)
        ax.text(v + max(values) * 0.012, yy, f"{v:.0f}%", va="center", ha="left", fontsize=8, color=ps.INK2)
    ax.set_yticks(ys, labels)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_xlabel("Share of sites whose robots.txt blocks the agent at the site root (%)")
    handles = [ps.plt.Line2D([0], [0], color=c, lw=6, solid_capstyle="butt") for _, _, c in groups]
    ax.legend(handles, [g[0] for g in groups], loc="lower right")
    ps.save(fig, FIG / "fig1_block_rates")


def fig_sector_heatmap(sec: pd.DataFrame) -> None:
    cols = ["GPTBot", "ClaudeBot", "Google-Extended", "CCBot", "OAI-SearchBot", "Claude-SearchBot",
            "PerplexityBot", "ChatGPT-User", "Claude-User"]
    data = sec[cols].to_numpy(dtype=float)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", ps.SEQ_BLUE)
    fig, ax = ps.plt.subplots(figsize=(7.2, 6.6))
    ax.pcolormesh(data, cmap=cmap, vmin=0, vmax=100, edgecolors=ps.SURFACE, linewidth=2)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            ax.text(j + 0.5, i + 0.5, f"{v:.0f}", ha="center", va="center", fontsize=7.5,
                    color="#ffffff" if v >= 55 else ps.INK)
    ax.set_xticks(np.arange(len(cols)) + 0.5, cols, rotation=40, ha="right")
    ax.set_yticks(np.arange(len(sec)) + 0.5, [f"{s} ({n})" for s, n in zip(sec["sector"], sec["sites"])])
    ax.invert_yaxis()
    ax.tick_params(length=0)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.axvline(4, color=ps.INK2, lw=1)
    ax.text(2, -0.6, "Training", ha="center", fontsize=8, color=ps.INK2)
    ax.text(6.5, -0.6, "Answer agents", ha="center", fontsize=8, color=ps.INK2)
    ps.save(fig, FIG / "fig2_sector_heatmap")


def fig_policy_types(df: pd.DataFrame) -> None:
    reach = df[df["reachable"]]
    tab = (pd.crosstab(reach["sector"], reach["policy"], normalize="index") * 100).reindex(columns=POLICY_ORDER).fillna(0)
    tab = tab.sort_values(POLICY_ORDER[0])
    colors = ["#d9d7d0", ps.SERIES[0], ps.SERIES[1], ps.SERIES[7]]  # neutral grey = no block
    fig, ax = ps.plt.subplots(figsize=(7.2, 6.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(len(tab) - 0.4, -0.6)
    for i, (sector, row) in enumerate(tab.iterrows()):
        left = 0.0
        for k, p in enumerate(POLICY_ORDER):
            w = row[p]
            if w > 0:
                ps.hbar(ax, i, left, w, colors[k], round_end=False)
                if w >= 9:
                    ax.text(left + w / 2, i, f"{w:.0f}", ha="center", va="center", fontsize=7,
                            color=ps.INK if k == 0 else "#ffffff")
                left += w
        ax.plot([left, left], [i - 0.3, i + 0.3], color=ps.SURFACE, lw=0)
    # 2px surface gaps between segments
    for i, (sector, row) in enumerate(tab.iterrows()):
        cum = np.cumsum(row.to_numpy())[:-1]
        for c in cum:
            if 0 < c < 100:
                ax.plot([c, c], [i - 0.33, i + 0.33], color=ps.SURFACE, lw=2, solid_capstyle="butt")
    ax.set_yticks(range(len(tab)), [SECTOR_LABELS.get(s, s) for s in tab.index])
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Share of sites in sector (%)")
    handles = [ps.plt.Line2D([0], [0], color=c, lw=6, solid_capstyle="butt") for c in colors]
    ax.legend(handles, POLICY_ORDER, loc="upper center", bbox_to_anchor=(0.45, -0.08), ncol=4, fontsize=7.5)
    ps.save(fig, FIG / "fig3_policy_types")


def fig_raw_share(df: pd.DataFrame) -> None:
    rend = df["raw_share"].dropna()
    if rend.empty:
        return
    fig, ax = ps.plt.subplots(figsize=(6.0, 3.0))
    bins = np.linspace(0, 1, 21)
    counts, edges = np.histogram(rend, bins=bins)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, counts.max() * 1.15)
    for c, l, r in zip(counts, edges[:-1], edges[1:]):
        if c:
            ax.bar(l + 0.0015, c, width=(r - l) - 0.003, align="edge", color=ps.SERIES[0], linewidth=0)
    ax.axvline(0.5, color=ps.INK2, lw=1)
    share = 100 * df.loc[df["raw_share"].notna(), "js_dependent"].mean()
    ax.text(0.49, counts.max() * 1.05, f"{share:.0f}% of homepages: under half the\nrendered text exists without JavaScript",
            ha="right", va="top", fontsize=8, color=ps.INK2)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_xlabel("Words in raw HTML ÷ words after JavaScript rendering")
    ax.set_ylabel("Homepages")
    ps.save(fig, FIG / "fig4_raw_share")


def main() -> int:
    ps.apply()
    RES.mkdir(parents=True, exist_ok=True)
    df = load()
    summary = summarize(df)
    summary["protego_crosscheck"] = protego_agreement()
    summary["inexact_tokens"] = inexact_tokens()
    sec = by_sector(df)
    (RES / "summary.json").write_text(json.dumps(summary, indent=2))
    sec.to_csv(RES / "by_sector.csv", index=False)
    keep = ["domain", "sector", "robots_state", "policy", "any_train_block", "any_retrieval_block",
            "retrieval_block_inherited", "llms_txt", "content_signal", "homepage_ok", "bot_wall",
            "raw_words", "rendered_words", "raw_share", "has_org_entity", "same_as_links"] + \
           [f"blocked:{t}" for t in CORE_TRAIN + CORE_RETRIEVAL]
    df[keep].to_csv(RES / "sites.csv", index=False)
    pd.DataFrame({"agent": list(summary["block_rate_pct"]), "block_rate_pct": list(summary["block_rate_pct"].values())}) \
        .to_csv(RES / "block_rates.csv", index=False)
    fig_block_rates(summary)
    fig_sector_heatmap(sec)
    fig_policy_types(df)
    fig_raw_share(df)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("protego_crosscheck",)}, indent=1))
    print("protego agreement:", summary["protego_crosscheck"]["agreement_pct"], "% of",
          summary["protego_crosscheck"]["comparisons"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
