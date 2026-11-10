"""Reanalyse released Study 1 summaries without requiring the private raw crawl.

    python analyze_revision.py

Writes results/revision_access.json from sites.csv and the retained rank-band
summaries. This is derived-data accounting, not a rerun of Study 1.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))


def _boolean(series: pd.Series) -> pd.Series:
    return series.fillna(False).astype(bool)


def _share(k: int, n: int) -> dict:
    return {"k": int(k), "n": int(n), "pct": round(100 * k / n, 1) if n else None}


def _prop(k: int, n: int) -> dict:
    from aeotools.tracker import wilson

    lo, hi = wilson(k, n) if n else (0.0, 0.0)
    return {**_share(k, n), "lo": round(100 * lo, 1), "hi": round(100 * hi, 1)}


def _load_components(sites_path: Path, barriers_path: Path) -> pd.DataFrame:
    sites = pd.read_csv(sites_path)
    needed = {"domain", "sector", "bot_wall", "raw_share", "rendered_words"}
    missing = needed - set(sites.columns)
    if missing:
        raise ValueError(f"{sites_path} lacks required derived columns: {sorted(missing)}")

    barrier_fields = {"index_named", "index_inherited", "robots_unreachable", "edge_refused"}
    missing_fields = barrier_fields - set(sites.columns)
    if missing_fields:
        barriers = pd.read_csv(barriers_path)
        fields = ["domain", *[name for name in missing_fields if name in barriers.columns]]
        # Older and regenerated tables both used "edge" without its semantics.
        # Subtract bot_wall to recover browser refusal in either schema; the two
        # measures are disjoint by definition (the bot wall still has usable HTML).
        if "edge_refused" in missing_fields and "edge_refused" not in barriers.columns:
            if "edge" not in barriers.columns:
                raise ValueError("derived barriers need edge_refused or the legacy edge field")
            bot_wall_by_domain = sites.set_index("domain")["bot_wall"]
            wall_in_barriers = _boolean(barriers["domain"].map(bot_wall_by_domain))
            barriers["edge_refused"] = _boolean(barriers["edge"]) & ~wall_in_barriers
            fields.append("edge_refused")
        fields = list(dict.fromkeys(fields))
        sites = sites.merge(barriers[fields], on="domain", how="left", validate="one_to_one")

    if "robots_unreachable" not in sites:
        if "robots_state" not in sites:
            raise ValueError("need robots_unreachable or robots_state in derived sites")
        sites["robots_unreachable"] = sites["robots_state"].eq("unreachable")
    for name in ("index_named", "index_inherited", "edge_refused"):
        if name not in sites:
            raise ValueError(f"could not recover {name} from released derived files")

    measured = sites["raw_share"].notna() & sites["rendered_words"].notna()
    js = (sites["raw_share"] < 0.5) & (sites["rendered_words"] >= 150)
    sites["js_measured"] = measured
    sites["js_dependent"] = js.where(measured, pd.NA)
    for name in ("index_named", "index_inherited", "robots_unreachable", "edge_refused", "bot_wall"):
        sites[name] = _boolean(sites[name])
    return sites


def _javascript(sites: pd.DataFrame) -> dict:
    overall = {"sites": len(sites), "measured": int(sites["js_measured"].sum()),
               "unmeasured": int((~sites["js_measured"]).sum()),
               "positive": int(sites["js_dependent"].fillna(False).astype(bool).sum())}
    overall["among_measured"] = _prop(overall["positive"], overall["measured"])
    overall["all_site_sensitivity"] = {
        "lower_if_all_unmeasured_are_negative": _share(overall["positive"], overall["sites"]),
        "upper_if_all_unmeasured_are_positive": _share(overall["positive"] + overall["unmeasured"], overall["sites"]),
        "interpretation": "classification sensitivity for unmeasured JS-dependence only; not bounds on actual access or exclusion",
    }
    by_sector = []
    for sector, group in sites.groupby("sector", sort=True):
        measured = group[group["js_measured"]]
        n, k = len(group), int(measured["js_dependent"].fillna(False).astype(bool).sum())
        by_sector.append({
            "sector": sector, "sites": n, "measured": len(measured),
            "unmeasured": n - len(measured), "positive": k,
            "among_measured": _prop(k, len(measured)),
            "all_site_sensitivity": {"lower": _share(k, n), "upper": _share(k + n - len(measured), n)},
        })
    overall["by_sector"] = by_sector
    return overall


def _rank_bands(draw_path: Path, results_path: Path) -> dict:
    draws = pd.read_csv(draw_path)
    summaries = pd.read_csv(results_path)
    if not {"rank", "band"} <= set(draws.columns):
        raise ValueError("rank sample must include rank and band")
    result: list[dict] = []
    for band, selected in draws.groupby("band", sort=False):
        sample_name = f"random {band}"
        rows = summaries[summaries["sample"] == sample_name]
        estimates = {}
        for _, row in rows.iterrows():
            metric = row["metric"]
            estimates[metric] = {key: (int(row[key]) if key in {"k", "n"} else float(row[key]))
                                 for key in ("k", "n", "pct", "lo", "hi")}
        retained = int(rows["n"].dropna().iloc[0]) if not rows.empty else None
        n_drawn = int(len(selected))
        ranks = pd.to_numeric(selected["rank"], errors="coerce").dropna()
        result.append({
            "band": str(band), "rank_min": int(ranks.min()), "rank_max": int(ranks.max()),
            "drawn": n_drawn, "retained": retained,
            "excluded": n_drawn - retained if retained is not None else None,
            "retained_pct": round(100 * retained / n_drawn, 1) if retained is not None and n_drawn else None,
            "estimates": estimates,
        })
    result.sort(key=lambda row: row["rank_min"])
    drawn_total = sum(row["drawn"] for row in result)
    retained_rows = [row["retained"] for row in result if row["retained"] is not None]
    retained_total = sum(retained_rows) if len(retained_rows) == len(result) else None
    return {
        "drawn": drawn_total, "retained": retained_total,
        "excluded": drawn_total - retained_total if retained_total is not None else None,
        "bands": result,
        "weighting": "equal numbers were drawn per rank band; no population-rank weighting is applied",
        "retention_note": "retained counts use the released website subset summaries; per-domain exclusion reasons are not present in these derived files",
        "estimate_note": "band estimates and Wilson intervals are conditional on the retained website subset",
    }



def _barrier_summary(sites: pd.DataFrame) -> dict:
    edge = sites["edge_refused"] | sites["bot_wall"]
    js = sites["js_dependent"]
    js_positive = js.fillna(False).astype(bool)
    b = pd.DataFrame({
        "index_named": sites["index_named"].astype(bool),
        "index_inherited": sites["index_inherited"].astype(bool),
        "robots_unreachable": sites["robots_unreachable"].astype(bool),
        "edge": edge.astype(bool),
        "js": js_positive,
    }, index=sites.index)
    keys = ["index_named", "index_inherited", "robots_unreachable", "edge", "js"]
    b["any"] = b[keys].any(axis=1)
    b["any_without_edge"] = b[[key for key in keys if key != "edge"]].any(axis=1)
    b["implicit"] = b[["index_inherited", "robots_unreachable", "edge", "js"]].any(axis=1)
    b["implicit_only"] = b["implicit"] & ~b["index_named"]
    b["implicit_without_edge"] = b[["index_inherited", "robots_unreachable", "js"]].any(axis=1)

    n = len(sites)
    summary = {name: _prop(int(b[name].sum()), n) for name in keys + [
        "any", "any_without_edge", "implicit", "implicit_only", "implicit_without_edge"]}
    summary["any_upper"] = _prop(int((b["any"] | js.isna()).sum()), n)
    summary["implicit_upper"] = _prop(int((b["implicit"] | js.isna()).sum()), n)
    summary["edge_refused"] = _prop(int(sites["edge_refused"].sum()), n)
    summary["bot_wall"] = _prop(int(sites["bot_wall"].sum()), n)
    overlap = sites["edge_refused"] & sites["bot_wall"]
    summary["browser_and_bot_refusal_overlap"] = _prop(int(overlap.sum()), n)
    attempted = ~_boolean(sites["homepage_skipped"]) if "homepage_skipped" in sites else pd.Series(False, index=sites.index)
    summary["edge_refused_attempted"] = _prop(
        int((sites["edge_refused"] & attempted).sum()), int(attempted.sum()))
    def combination(row: pd.Series) -> str:
        present = [key for key in keys if row[key]]
        if pd.isna(js.loc[row.name]):
            present.append("js_unmeasured")
        return " + ".join(present) or "none"
    summary["combinations"] = b.apply(combination, axis=1).value_counts().to_dict()
    summary["coverage"] = {
        "sites": n, "edge_attempted": int(attempted.sum()),
        "js_measured": int(sites["js_measured"].sum()),
        "js_unmeasured": int((~sites["js_measured"]).sum()),
    }
    summary["definitions"] = {
        "edge": "browser-client refusal OR bot-user-agent challenge",
        "js": "under half rendered text present in raw HTML; k is measured positives over the full site sample, unmeasured cases are not counted positive",
        "any": "at least one observed component; unmeasured JS is not counted positive",
        "any_upper": "sensitivity case treating every unmeasured JS observation as positive",
    }
    return summary


def analyze(sites_path: Path = RES / "sites.csv",
            barriers_path: Path = RES / "barriers_by_site.csv",
            draw_path: Path = HERE / "random_sample.csv",
            random_results_path: Path = RES / "random_vs_purposive.csv") -> dict:
    sites = _load_components(sites_path, barriers_path)
    n = len(sites)
    edge_union = sites["edge_refused"] | sites["bot_wall"]
    js_positive = sites["js_dependent"].fillna(False).astype(bool)
    known_non_js = (sites[["index_named", "index_inherited", "robots_unreachable"]].any(axis=1)
                    | edge_union)
    observed_positive = known_non_js | js_positive
    possible_positive = observed_positive | sites["js_dependent"].isna()
    unknown_without_other_positive = sites["js_dependent"].isna() & ~known_non_js

    attempted_n = (int((~_boolean(sites["homepage_skipped"])).sum())
                   if "homepage_skipped" in sites else None)
    if attempted_n is None:
        cached_edge = RES / "edge_breakdown.json"
        if cached_edge.exists():
            attempted_n = int(json.loads(cached_edge.read_text())["attempted"])
    homepage_ok_n = int(_boolean(sites["homepage_ok"]).sum()) if "homepage_ok" in sites else n
    components = {
        "index_named": _prop(int(sites["index_named"].sum()), n),
        "index_inherited": _prop(int(sites["index_inherited"].sum()), n),
        "robots_unreachable": _prop(int(sites["robots_unreachable"].sum()), n),
        "browser_edge_refused": {
            "k": int(sites["edge_refused"].sum()), "n_all_sites": n,
            "n_attempted": attempted_n,
            "pct_attempted": round(100 * int(sites["edge_refused"].sum()) / attempted_n, 1)
            if attempted_n else None,
        },
        "bot_user_agent_challenge": {
            "k": int(sites["bot_wall"].sum()), "n_all_sites": n, "n_homepage_ok": homepage_ok_n,
        },
        "edge_union": _prop(int(edge_union.sum()), n),
        "browser_and_bot_refusal_overlap": _prop(
            int((sites["edge_refused"] & sites["bot_wall"]).sum()), n),
        "js_dependence_when_measured": _prop(int(js_positive.sum()), int(sites["js_measured"].sum())),
    }
    js = _javascript(sites)
    return {
        "source": "released derived files only; no raw crawl was read or rerun",
        "sample_n": n,
        "potential_first_party_access_obstacles": {
            "definition": "at least one measured robots index policy obstacle, unreachable robots.txt, browser-client refusal/challenge, bot-user-agent challenge, or measured JS-dependence indicator",
            "components": components,
            "composite_observed_positive": _prop(int(observed_positive.sum()), n),
            "composite_if_all_unmeasured_js_are_positive": _share(int(possible_positive.sum()), n),
            "unmeasured_js_without_another_observed_obstacle": int(unknown_without_other_positive.sum()),
            "interpretation": "the composite is an indicator of potential obstacles, not an estimate of retrieval, exclusion from answers, or a true access bound",
        },
        "javascript_measurement": js,
        "barriers": _barrier_summary(sites),
        "rank_band_retention_and_estimates": _rank_bands(draw_path, random_results_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", type=Path, default=RES / "sites.csv")
    parser.add_argument("--barriers", type=Path, default=RES / "barriers_by_site.csv")
    parser.add_argument("--rank-draw", type=Path, default=HERE / "random_sample.csv")
    parser.add_argument("--rank-results", type=Path, default=RES / "random_vs_purposive.csv")
    parser.add_argument("--output", type=Path, default=RES / "revision_access.json")
    parser.add_argument("--no-figure", action="store_true", help="skip regenerating paper/figures/fig8_barriers")
    args = parser.parse_args(argv)
    report = analyze(args.sites, args.barriers, args.rank_draw, args.rank_results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    if not args.no_figure:
        import analyze_extensions as extensions
        from aeotools import plotstyle as ps

        ps.apply()
        extensions.fig_barriers(report["barriers"])
    print(json.dumps({"output": str(args.output), "sample_n": report["sample_n"],
                      "composite": report["potential_first_party_access_obstacles"]["composite_observed_positive"],
                      "js": report["javascript_measurement"]["among_measured"],
                      "rank_sample": report["rank_band_retention_and_estimates"]["drawn"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
