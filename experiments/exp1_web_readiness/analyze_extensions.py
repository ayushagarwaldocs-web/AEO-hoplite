"""Experiment 1 extensions: inference, discoverability barriers, a random sample of
popular sites, and a 2023-2026 history from archived robots.txt files.

    python analyze_extensions.py

Uses the phase-A data plus, when present, data/raw/random_*.jsonl (run_random_sample.py)
and data/raw/history_*.jsonl (run_history.py). Writes results/extended.json, CSV tables
and paper figures.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.dates as mdates
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from experiments.exp1_web_readiness import analyze as A1  # noqa: E402
from aeotools import plotstyle as ps  # noqa: E402
from aeotools.bots import BOTS  # noqa: E402
from aeotools.robots import looks_like_html, parse  # noqa: E402
from aeotools.tracker import wilson  # noqa: E402

RAW, RES, FIG = A1.RAW, A1.RES, A1.FIG
INDEX = ["OAI-SearchBot", "Claude-SearchBot", "PerplexityBot"]  # AI search-index crawlers
TOKENS = [b.token for b in BOTS]
LIVE_DATE = "2026-11-03"
rng = np.random.default_rng(20261104)


def prop(series) -> dict:
    s = pd.Series(series).dropna().astype(bool)
    k, n = int(s.sum()), len(s)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "pct": round(100 * k / n, 1) if n else None,
            "lo": round(100 * lo, 1), "hi": round(100 * hi, 1)}


def paired_test(x: pd.Series, y: pd.Series) -> dict:
    """Exact McNemar test for two binary outcomes measured on the same sites."""
    from statsmodels.stats.contingency_tables import mcnemar

    x, y = x.astype(bool), y.astype(bool)
    table = [[int((x & y).sum()), int((x & ~y).sum())], [int((~x & y).sum()), int((~x & ~y).sum())]]
    return {"only_first": table[0][1], "only_second": table[1][0], "p": float(mcnemar(table, exact=True).pvalue)}


def chi2_permutation(groups: pd.Series, outcome: pd.Series, n_perm: int = 10_000) -> dict:
    """Chi-square test of independence with a permutation p-value (many cells are small)."""
    g = pd.Categorical(groups).codes
    y = outcome.astype(int).to_numpy()
    k = g.max() + 1

    def stat(yy):
        tab = np.zeros((k, 2))
        np.add.at(tab, (g, yy), 1)
        exp = tab.sum(1, keepdims=True) * tab.sum(0, keepdims=True) / tab.sum()
        return float(((tab - exp) ** 2 / exp).sum())

    obs = stat(y)
    perm = np.array([stat(rng.permutation(y)) for _ in range(n_perm)])
    return {"chi2": round(obs, 1), "df": int(k - 1), "p_perm": float((1 + (perm >= obs).sum()) / (n_perm + 1)),
            "cramers_v": round(float(np.sqrt(obs / len(y))), 2)}


# --- 1. inference for the snapshot ---------------------------------------------

def inference(df: pd.DataFrame) -> dict:
    reach = df[df["reachable"]]
    out = {"block": {t: prop(reach[f"blocked:{t}"]) for t in A1.CORE_TRAIN + A1.CORE_RETRIEVAL},
           "policy": {p: prop(reach["policy"] == p) for p in A1.POLICY_ORDER},
           "any_train_block": prop(reach["any_train_block"]),
           "any_retrieval_block": prop(reach["any_retrieval_block"]),
           "llms_txt": prop(df["llms_txt"]),
           "edge": prop(df.loc[~df["homepage_skipped"], "edge_refused"]),
           "js_dependent": prop(df.loc[df["js_measured"], "js_dependent"])}
    out["paired"] = {f"{a} vs {b}": paired_test(reach[f"blocked:{a}"], reach[f"blocked:{b}"])
                     for a, b in [("GPTBot", "OAI-SearchBot"), ("ClaudeBot", "Claude-SearchBot"),
                                  ("GPTBot", "ChatGPT-User")]}
    out["paired"]["any training vs any answer"] = paired_test(reach["any_train_block"], reach["any_retrieval_block"])
    out["sector_test"] = chi2_permutation(reach["sector"], reach["any_retrieval_block"])
    # Path-level rules: an answer agent allowed at the root but blocked at a typical article path
    probe = reach[[f"probe_blocked:{t}" for t in A1.CORE_RETRIEVAL]].astype(bool).any(axis=1)
    out["answer_blocked_at_article_path"] = prop(probe)
    out["answer_blocked_at_path_only"] = prop(probe & ~reach["any_retrieval_block"].astype(bool))
    return out


# --- 2. discoverability barriers -------------------------------------------------

BARRIERS = {
    "index_named": "Names an AI search crawler and blocks it",
    "index_inherited": "Blocks an AI search crawler via the wildcard group",
    "robots_unreachable": "robots.txt unreachable (5xx or network error)",
    "edge": "Edge refusal of our research client (browser or bot)",
    "js": "JavaScript-dependent homepage (raw text < half of rendered)",
}


def barriers(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    b = pd.DataFrame({"domain": df["domain"], "sector": df["sector"]})
    b["index_named"] = df["index_named"].fillna(False).astype(bool)
    b["index_inherited"] = df["index_inherited"].fillna(False).astype(bool)
    b["robots_unreachable"] = df["robots_unreachable"].astype(bool)
    b["edge_refused"] = df["edge_refused"].fillna(False).astype(bool)
    b["bot_wall"] = df["bot_wall"].fillna(False).astype(bool)
    b["edge"] = b["edge_refused"] | b["bot_wall"]
    b["js"] = df["js_dependent"]
    keys = list(BARRIERS)
    non_js = [k for k in keys if k != "js"]
    non_js_positive = b[non_js].any(axis=1)
    js_positive = b["js"].fillna(False).astype(bool)
    b["any"] = non_js_positive | js_positive
    b["any_upper"] = b["any"] | b["js"].isna()
    no_edge = [k for k in keys if k not in {"edge", "js"}]
    b["any_without_edge"] = b[no_edge].any(axis=1) | js_positive
    implicit_components = ["index_inherited", "robots_unreachable", "edge"]
    b["implicit"] = b[implicit_components].any(axis=1) | js_positive
    b["implicit_upper"] = b["implicit"] | b["js"].isna()
    b["implicit_only"] = b["implicit"] & ~b["index_named"]
    b["implicit_without_edge"] = b[["index_inherited", "robots_unreachable"]].any(axis=1) | js_positive
    def combo(row):
        present = [k for k in keys if pd.notna(row[k]) and bool(row[k])]
        if pd.isna(row["js"]):
            present.append("js_unmeasured")
        return " + ".join(present) or "none"
    combos = b.apply(combo, axis=1).value_counts().to_dict()
    out = {k: prop(b[k].fillna(False)) for k in keys + ["any", "any_upper", "any_without_edge", "implicit",
                                                        "implicit_upper", "implicit_only", "implicit_without_edge"]}
    out["edge_refused"] = prop(b["edge_refused"])
    out["bot_wall"] = prop(b["bot_wall"])
    out["browser_and_bot_refusal_overlap"] = prop(b["edge_refused"] & b["bot_wall"])
    attempted = ~df["homepage_skipped"].astype(bool)
    out["edge_refused_attempted"] = prop(df.loc[attempted, "edge_refused"])
    out["combinations"] = combos
    out["coverage"] = {"sites": len(df), "edge_attempted": int(attempted.sum()),
                       "js_measured": int(df["js_measured"].sum()),
                       "js_unmeasured": int((~df["js_measured"]).sum())}
    return out, b


def barrier_plot_rows(res: dict) -> list[tuple[str, float, int]]:
    rows = []
    for key, label in BARRIERS.items():
        metric = res[key]
        denominator = int(res["coverage"]["js_measured"]) if key == "js" else int(metric["n"])
        pct = 100 * metric["k"] / denominator if denominator else 0.0
        rows.append((f"{label} (n={denominator})", pct, denominator))
    overall = res["any"]
    rows.append((f"At least one potential obstacle (n={overall['n']})", overall["pct"], int(overall["n"])))
    return rows


def fig_barriers(res: dict) -> None:
    rows = barrier_plot_rows(res)
    vals = [row[1] for row in rows]
    labels = [row[0] for row in rows]
    colors = [ps.SERIES[0]] + [ps.SERIES[1]] * 4 + [ps.INK2]
    fig, ax = ps.plt.subplots(figsize=(6.4, 2.9))
    ax.set_xlim(0, max(vals) * 1.22)
    ys = list(range(len(rows) - 1)) + [len(rows) - 0.5]
    ax.set_ylim(ys[-1] + 0.7, -0.7)
    for y, v, c in zip(ys, vals, colors):
        ps.hbar(ax, y, 0, v, c)
        ax.text(v + max(vals) * 0.012, y, f"{v:.1f}%", va="center", ha="left", fontsize=8, color=ps.INK2)
    ax.set_yticks(ys, labels)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_xlabel("Share of sites (%)")
    handles = [ps.plt.Line2D([0], [0], color=c, lw=6, solid_capstyle="butt") for c in ps.SERIES[:2]]
    ax.legend(handles, ["Explicit crawler policy", "Observed access-route indicator"], loc="upper right")
    ps.save(fig, FIG / "fig8_barriers")


# --- 3. random sample of popular sites -------------------------------------------

def random_sample(purposive: pd.DataFrame) -> dict | None:
    path = RAW / "random_sites.jsonl"
    if not path.exists():
        return None
    r = A1.load(path, RAW / "random_renders.jsonl")
    status = pd.to_numeric(r["homepage_status"], errors="coerce")
    # A website: robots.txt reachable and the homepage answered (or we were asked not to fetch it)
    r["website"] = r["reachable"] & (r["homepage_ok"] | r["edge_refused"] | r["homepage_skipped"]
                                     | status.between(200, 399))
    w = r[r["website"]].copy()
    p = purposive[purposive["reachable"]]

    def metrics(d: pd.DataFrame) -> dict:
        m = {t: prop(d[f"blocked:{t}"]) for t in A1.CORE_TRAIN + A1.CORE_RETRIEVAL}
        m.update({"any_train_block": prop(d["any_train_block"]), "any_retrieval_block": prop(d["any_retrieval_block"]),
                  "inherited_of_blockers": prop(d.loc[d["any_retrieval_block"] == True, "retrieval_block_inherited"]),  # noqa: E712
                  "names_any_ai": prop(d["names_any_ai"]), "llms_txt": prop(d["llms_txt"]),
                  "content_signal": prop(d["content_signal"]),
                  "edge": prop(d.loc[~d["homepage_skipped"], "edge_refused"]),
                  "org_entity": prop(d.loc[d["homepage_ok"], "has_org_entity"]) if d["homepage_ok"].any() else None})
        m["policy"] = {k: prop(d["policy"] == k) for k in A1.POLICY_ORDER}
        return m

    content_heavy = ["news_media", "social_reviews_ugc", "reference_science"]
    out = {"drawn": len(r), "websites": len(w), "random": metrics(w), "purposive": metrics(p),
           "purposive_without_content_sectors": metrics(p[~p["sector"].isin(content_heavy)]),
           "by_band": {band: metrics(g) for band, g in w.groupby("band")}}
    out["bands_n"] = w["band"].value_counts().to_dict()
    rows = []
    for name, d in [("purposive", p), ("random", w)] + [(f"random {b}", g) for b, g in w.groupby("band")]:
        for t in A1.CORE_TRAIN + A1.CORE_RETRIEVAL:
            rows.append({"sample": name, "metric": f"blocks {t}", **prop(d[f"blocked:{t}"])})
        for col in ["any_train_block", "any_retrieval_block", "llms_txt", "names_any_ai"]:
            rows.append({"sample": name, "metric": col, **prop(d[col])})
    pd.DataFrame(rows).to_csv(RES / "random_vs_purposive.csv", index=False)
    fig_random(out)
    return out


def fig_random(res: dict) -> None:
    items = [(f"blocks {t}", t) for t in ["GPTBot", "ClaudeBot", "CCBot", "Google-Extended", "OAI-SearchBot",
                                           "Claude-SearchBot", "PerplexityBot", "ChatGPT-User"]]
    items += [("blocks any answer agent", "any_retrieval_block"), ("publishes llms.txt", "llms_txt")]
    fig, ax = ps.plt.subplots(figsize=(6.4, 3.8))
    for i, (label, key) in enumerate(items):
        for j, (sample, color, dy) in enumerate([("purposive", ps.SERIES[0], -0.14), ("random", ps.SERIES[1], 0.14)]):
            m = res[sample][key]
            ax.plot([m["lo"], m["hi"]], [i + dy, i + dy], color=color, lw=1.6, solid_capstyle="round")
            ax.plot(m["pct"], i + dy, "o", ms=6, color=color, mec=ps.SURFACE, mew=1.2)
    ax.set_yticks(range(len(items)), [lab for lab, _ in items])
    ax.set_ylim(len(items) - 0.4, -0.6)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_xlim(0, None)
    ax.set_xlabel("Share of sites with a reachable robots.txt (%), with 95% Wilson intervals")
    handles = [ps.plt.Line2D([0], [0], color=c, marker="o", lw=1.6) for c in ps.SERIES[:2]]
    ax.legend(handles, [f"Organisational sample (n={res['purposive']['GPTBot']['n']})",
                        f"Random popular sites (n={res['random']['GPTBot']['n']})"], loc="upper right")
    ps.save(fig, FIG / "fig9_random_sample")


# --- 4. history 2023-2026 --------------------------------------------------------

def history(live: pd.DataFrame) -> dict | None:
    cap_path, txt_path = RAW / "history_captures.jsonl", RAW / "history_robots.jsonl"
    if not cap_path.exists():
        return None
    texts = {}
    for line in txt_path.open():
        t = json.loads(line)
        if t["text"] is not None:
            texts[(t["domain"], t["digest"])] = t["text"]
    rows = []
    for line in cap_path.open():
        c = json.loads(line)
        for date, p in c["picks"].items():
            text = texts.get((c["domain"], p[1])) if p else ("" if date in c["absent"] else None)
            if text is not None and looks_like_html(text):
                text = ""  # an HTML page served as robots.txt: no rules
            row = {"domain": c["domain"], "date": date, "observed": text is not None,
                   "gap_days": None}
            if p:
                row["gap_days"] = (pd.Timestamp(p[0][:8]) - pd.Timestamp(date)).days
            if text is not None:
                parsed = parse(text)
                for t in TOKENS:
                    row[f"blocked:{t}"] = not parsed.allowed(t, "/")
                    row[f"named:{t}"] = parsed.names(t)
            rows.append(row)
    h = pd.DataFrame(rows)
    lv = live[live["reachable"]][["domain"] + [f"blocked:{t}" for t in TOKENS] + [f"named:{t}" for t in TOKENS]].copy()
    lv["date"], lv["observed"] = LIVE_DATE, True
    h = pd.concat([h, lv], ignore_index=True)
    for col in [f"blocked:{t}" for t in TOKENS] + [f"named:{t}" for t in TOKENS]:
        h[col] = h[col].astype("boolean")
    b = lambda d, toks: d[[f"blocked:{t}" for t in toks]].fillna(False).any(axis=1)  # noqa: E731
    nm = lambda d, toks: d[[f"named:{t}" for t in toks]].fillna(False).any(axis=1)  # noqa: E731
    h["any_train_block"] = b(h, A1.CORE_TRAIN)
    h["any_retrieval_block"] = b(h, A1.CORE_RETRIEVAL)
    h["any_index_block"] = b(h, INDEX)
    h["names_any_ai"] = nm(h, A1.TRAIN + A1.AI_SEARCH + A1.USER)
    h["names_legacy"] = nm(h, A1.LEGACY)
    h["openai_split"] = h["blocked:GPTBot"].fillna(False) & ~h["blocked:OAI-SearchBot"].fillna(False)

    obs = h[h["observed"]]
    dates = sorted(obs["date"].unique())
    panel = set.intersection(*[set(obs.loc[obs["date"] == d, "domain"]) for d in dates])
    bal = obs[obs["domain"].isin(panel)]
    series_cols = ([f"blocked:{t}" for t in A1.CORE_TRAIN + A1.CORE_RETRIEVAL]
                   + [f"named:{t}" for t in A1.CORE_RETRIEVAL + A1.LEGACY]
                   + ["any_train_block", "any_retrieval_block", "any_index_block", "names_any_ai", "names_legacy"])
    ts = bal.groupby("date")[series_cols].mean().mul(100).round(1)
    ts["n"] = bal.groupby("date").size()
    ts.to_csv(RES / "history_balanced_panel.csv")
    ts_all = obs.groupby("date")[series_cols].mean().mul(100).round(1)
    ts_all["n"] = obs.groupby("date").size()
    ts_all.to_csv(RES / "history_all_observed.csv")

    # Persistence: of sites blocking GPTBot at the first post-GPTBot wave, how many still do?
    first = bal[bal["date"] == "2024-01-01"].set_index("domain")
    last = bal[bal["date"] == LIVE_DATE].set_index("domain")
    blockers = first.index[first["blocked:GPTBot"].fillna(False)]
    still = last.loc[blockers, "blocked:GPTBot"].fillna(False).mean() if len(blockers) else np.nan
    # Answer-agent rules among GPTBot blockers: when did they name OpenAI's search crawler?
    gpt_live = last.index[last["blocked:GPTBot"].fillna(False)]
    named_search = bal[bal["domain"].isin(gpt_live)].groupby("date")["named:OAI-SearchBot"].mean().mul(100).round(1)

    # Archive fidelity: archived copy within 45 days before the live crawl vs. the live result
    val = h[(h["date"] == "2026-11-01") & h["observed"] & h["gap_days"].between(-45, 0)].set_index("domain")
    common = val.index.intersection(lv["domain"])
    agree = []
    lvi = lv.set_index("domain")
    for t in A1.CORE_TRAIN + A1.CORE_RETRIEVAL:
        agree += list(val.loc[common, f"blocked:{t}"].astype(bool) == lvi.loc[common, f"blocked:{t}"].astype(bool))
    out = {"domains_queried": int(h.loc[h["date"] != LIVE_DATE, "domain"].nunique()),
           "observed_by_date": obs.groupby("date").size().to_dict(),
           "balanced_panel": len(panel), "dates": dates,
           "series": ts.reset_index().to_dict(orient="records"),
           "gptbot_2024_blockers": int(len(blockers)),
           "gptbot_2024_blockers_still_blocking_pct": round(100 * float(still), 1) if len(blockers) else None,
           "oai_searchbot_named_among_live_gptbot_blockers": named_search.to_dict(),
           "fidelity": {"sites": int(len(common)), "decisions": len(agree),
                        "agreement_pct": round(100 * float(np.mean(agree)), 1) if agree else None}}
    fig_history(ts)
    return out


def fig_history(ts: pd.DataFrame) -> None:
    dates = pd.to_datetime(ts.index)
    fig, axes = ps.plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    panels = [("Training crawlers", ["GPTBot", "CCBot", "ClaudeBot", "Google-Extended"]),
              ("AI search and user agents", ["OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot", "PerplexityBot"])]
    top = max(ts[[f"blocked:{t}" for _, toks in panels for t in toks]].max()) * 1.15
    for ax, (title, toks) in zip(axes, panels):
        for i, t in enumerate(toks):
            y = ts[f"blocked:{t}"]
            ax.plot(dates, y, color=ps.SERIES[i], lw=2, marker="o", ms=3.5, mec=ps.SURFACE, mew=0.8)
            ax.text(dates[-1] + pd.Timedelta(days=25), y.iloc[-1], t, va="center", fontsize=7.5, color=ps.INK2)
        ax.set_title(title, loc="left")
        ax.set_ylim(0, top)
        ax.yaxis.grid(True)
        ax.set_axisbelow(True)
        ax.set_xlim(dates[0] - pd.Timedelta(days=40), dates[-1] + pd.Timedelta(days=330))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[0].set_ylabel(f"Sites blocking the agent (%), n={int(ts['n'].iloc[0])}")
    ps.save(fig, FIG / "fig10_history")


def main() -> int:
    ps.apply()
    df = A1.load()
    out = {"inference": inference(df)}
    out["barriers"], b = barriers(df)
    b.to_csv(RES / "barriers_by_site.csv", index=False)
    fig_barriers(out["barriers"])
    rs = random_sample(df)
    if rs:
        out["random_sample"] = rs
    hist = history(df)
    if hist:
        out["history"] = hist
    (RES / "extended.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "history"}, indent=1, default=float)[:6000])
    if hist:
        print(json.dumps({k: v for k, v in hist.items() if k != "series"}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
