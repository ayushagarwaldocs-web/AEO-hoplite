import json

import pandas as pd

from experiments.exp1_web_readiness.analyze_revision import analyze


def test_derived_access_analysis_counts_bot_walls_and_missingness(tmp_path):
    sites = pd.DataFrame([
        {"domain": "a.test", "sector": "one", "bot_wall": False, "raw_share": 0.2,
         "rendered_words": 200, "homepage_ok": True, "homepage_skipped": False,
         "robots_state": "ok"},
        {"domain": "b.test", "sector": "one", "bot_wall": True, "raw_share": 0.9,
         "rendered_words": 200, "homepage_ok": True, "homepage_skipped": False,
         "robots_state": "ok"},
        {"domain": "c.test", "sector": "two", "bot_wall": False, "raw_share": None,
         "rendered_words": None, "homepage_ok": False, "homepage_skipped": False,
         "robots_state": "unreachable"},
        {"domain": "d.test", "sector": "two", "bot_wall": False, "raw_share": None,
         "rendered_words": None, "homepage_ok": False, "homepage_skipped": True,
         "robots_state": "ok"},
    ])
    sites_path = tmp_path / "sites.csv"
    sites.to_csv(sites_path, index=False)
    barriers = pd.DataFrame([
        {"domain": "a.test", "index_named": False, "index_inherited": False,
         "robots_unreachable": False, "edge": False},
        {"domain": "b.test", "index_named": False, "index_inherited": False,
         "robots_unreachable": False, "edge": False},
        {"domain": "c.test", "index_named": False, "index_inherited": False,
         "robots_unreachable": True, "edge": True},
        {"domain": "d.test", "index_named": True, "index_inherited": False,
         "robots_unreachable": False, "edge": False},
    ])
    barriers_path = tmp_path / "barriers.csv"
    barriers.to_csv(barriers_path, index=False)
    draws = pd.DataFrame({"rank": [1, 2, 2000, 3000], "band": ["1-1000", "1-1000", "1001-10000", "1001-10000"]})
    draws_path = tmp_path / "draws.csv"
    draws.to_csv(draws_path, index=False)
    summaries = pd.DataFrame([
        {"sample": "random 1-1000", "metric": "blocks GPTBot", "k": 1, "n": 1,
         "pct": 100.0, "lo": 20.7, "hi": 100.0},
        {"sample": "random 1001-10000", "metric": "blocks GPTBot", "k": 0, "n": 2,
         "pct": 0.0, "lo": 0.0, "hi": 65.8},
    ])
    results_path = tmp_path / "random.csv"
    summaries.to_csv(results_path, index=False)

    result = analyze(sites_path, barriers_path, draws_path, results_path)
    access = result["potential_first_party_access_obstacles"]
    assert access["components"]["edge_union"]["k"] == 2
    assert access["components"]["edge_union"]["n"] == 4
    assert access["components"]["browser_and_bot_refusal_overlap"]["k"] == 0
    assert access["composite_observed_positive"]["k"] == 4
    assert access["composite_if_all_unmeasured_js_are_positive"]["k"] == 4
    assert result["javascript_measurement"]["measured"] == 2
    assert result["javascript_measurement"]["unmeasured"] == 2
    assert result["rank_band_retention_and_estimates"]["drawn"] == 4
    assert result["rank_band_retention_and_estimates"]["bands"][0]["retained"] == 1


def test_study1_loader_preserves_unmeasured_javascript_status(tmp_path):
    import json

    from experiments.exp1_web_readiness import analyze as study1

    tokens = sorted(set(study1.TRAIN + study1.AI_SEARCH + study1.USER + study1.CLASSIC + study1.LEGACY))

    def record(domain, state, signaled, index_block=False):
        bots = {}
        for token in tokens:
            blocked = index_block and token == "OAI-SearchBot"
            bots[token] = {"root": not blocked, "named": blocked,
                           "matched_by": "explicit" if blocked else "none", "probe": not blocked}
        report = {
            "robots": {"state": state, "content_signals": [], "content_usage": []},
            "llms_txt": {"valid": False}, "wildcard_root_blocked": False, "bots": bots,
            "homepage_bot": {}, "homepage_browser": {"status": 200},
        }
        if signaled:
            report["signals"] = {"words": 100, "spa_empty_root": False,
                                 "noscript_warning": False, "jsonld_blocks": 0,
                                 "has_org_entity": False, "same_as_links": 0,
                                 "noai": False, "nosnippet": False}
        else:
            report["homepage_skipped"] = True
        return {"domain": domain, "sector": "sample", "report": report}

    sites_path = tmp_path / "sites.jsonl"
    sites_path.write_text("\n".join(json.dumps(r) for r in [
        record("measured.test", "ok", True, index_block=True),
        record("missing.test", "unreachable", False),
    ]) + "\n")
    renders_path = tmp_path / "renders.jsonl"
    renders_path.write_text(json.dumps({"domain": "measured.test", "ok": True,
                                        "raw_words": 100, "rendered_words": 300}) + "\n")

    loaded = study1.load(sites_path, renders_path).set_index("domain")
    assert bool(loaded.loc["measured.test", "index_named"])
    assert bool(loaded.loc["missing.test", "robots_unreachable"])
    assert bool(loaded.loc["measured.test", "js_measured"])
    assert bool(loaded.loc["measured.test", "js_dependent"])
    assert not bool(loaded.loc["missing.test", "js_measured"])
    assert pd.isna(loaded.loc["missing.test", "js_dependent"])



def test_revision_barrier_schema_and_union_replay_are_idempotent(tmp_path):
    sites = pd.DataFrame([
        {"domain": "browser.test", "sector": "one", "bot_wall": False, "raw_share": 0.8,
         "rendered_words": 200, "homepage_ok": False, "homepage_skipped": False, "robots_state": "ok"},
        {"domain": "bot.test", "sector": "one", "bot_wall": True, "raw_share": 0.9,
         "rendered_words": 200, "homepage_ok": True, "homepage_skipped": False, "robots_state": "ok"},
        {"domain": "unknown.test", "sector": "two", "bot_wall": False, "raw_share": None,
         "rendered_words": None, "homepage_ok": False, "homepage_skipped": True, "robots_state": "ok"},
        {"domain": "clear.test", "sector": "two", "bot_wall": False, "raw_share": 1.0,
         "rendered_words": 200, "homepage_ok": True, "homepage_skipped": False, "robots_state": "ok"},
    ])
    sites_path = tmp_path / "sites.csv"
    sites.to_csv(sites_path, index=False)
    base = pd.DataFrame([
        {"domain": "browser.test", "index_named": False, "index_inherited": False,
         "robots_unreachable": False},
        {"domain": "bot.test", "index_named": False, "index_inherited": False,
         "robots_unreachable": False},
        {"domain": "unknown.test", "index_named": False, "index_inherited": False,
         "robots_unreachable": False},
        {"domain": "clear.test", "index_named": False, "index_inherited": False,
         "robots_unreachable": False},
    ])
    draws = pd.DataFrame({"rank": [1], "band": ["1-1000"]})
    draws_path = tmp_path / "draws.csv"
    draws.to_csv(draws_path, index=False)
    rank_results = pd.DataFrame([
        {"sample": "random 1-1000", "metric": "blocks GPTBot", "k": 0, "n": 1,
         "pct": 0.0, "lo": 0.0, "hi": 79.3},
    ])
    rank_path = tmp_path / "rank.csv"
    rank_results.to_csv(rank_path, index=False)

    legacy = base.copy()
    legacy["edge"] = [True, True, False, False]
    legacy_path = tmp_path / "legacy_barriers.csv"
    legacy.to_csv(legacy_path, index=False)
    replayed = analyze(sites_path, legacy_path, draws_path, rank_path)

    assert replayed["potential_first_party_access_obstacles"]["components"]["browser_edge_refused"]["k"] == 1
    assert replayed["potential_first_party_access_obstacles"]["components"]["bot_user_agent_challenge"]["k"] == 1
    assert replayed["barriers"]["edge"]["k"] == 2
    assert replayed["barriers"]["any"]["k"] == 2
    assert replayed["barriers"]["js"]["k"] == 0
    assert replayed["barriers"]["js"]["n"] == 4
    assert replayed["barriers"]["js"]["pct"] == 0.0
    assert replayed["barriers"]["coverage"]["sites"] == 4
    assert replayed["barriers"]["coverage"]["js_unmeasured"] == 1

    current = base.copy()
    current["edge_refused"] = [True, False, False, False]
    current["bot_wall"] = [False, True, False, False]
    current["edge"] = [True, True, False, False]
    current_path = tmp_path / "current_barriers.csv"
    current.to_csv(current_path, index=False)
    explicit = analyze(sites_path, current_path, draws_path, rank_path)
    assert explicit["barriers"] == replayed["barriers"]
    assert explicit["potential_first_party_access_obstacles"]["composite_observed_positive"] == replayed[
        "potential_first_party_access_obstacles"]["composite_observed_positive"]
    expected = {"any", "any_without_edge", "implicit", "implicit_only", "implicit_without_edge",
                "index_named", "index_inherited", "robots_unreachable", "edge", "js"}
    assert expected <= set(explicit["barriers"])
    assert all({"k", "n", "pct", "lo", "hi"} <= set(explicit["barriers"][name])
               and explicit["barriers"][name]["n"] == 4 for name in expected)


def test_released_barrier_macros_use_full_sample_denominators():
    from experiments.exp1_web_readiness.analyze_revision import analyze

    result = analyze()
    barriers = result["barriers"]
    expected = {"any", "any_without_edge", "implicit", "implicit_only", "implicit_without_edge",
                "index_named", "index_inherited", "robots_unreachable", "edge", "js"}
    assert expected <= set(barriers)
    assert barriers["coverage"]["sites"] == 569
    assert all(barriers[name]["n"] == 569 for name in expected)
    assert barriers["any"]["k"] == 199
    assert barriers["edge"]["k"] == 101
    assert barriers["js"]["k"] == 30
    assert barriers["js"]["pct"] == 5.3


def test_extension_and_revision_barrier_summaries_match_full_sample():
    from experiments.exp1_web_readiness.analyze_extensions import barriers
    from experiments.exp1_web_readiness.analyze_revision import _barrier_summary

    sites = pd.DataFrame([
        {"domain": "a", "sector": "x", "index_named": False, "index_inherited": False,
         "robots_unreachable": False, "edge_refused": True, "bot_wall": False,
         "js_dependent": False, "js_measured": True, "homepage_skipped": False},
        {"domain": "b", "sector": "x", "index_named": True, "index_inherited": False,
         "robots_unreachable": False, "edge_refused": False, "bot_wall": True,
         "js_dependent": True, "js_measured": True, "homepage_skipped": False},
        {"domain": "c", "sector": "x", "index_named": False, "index_inherited": True,
         "robots_unreachable": False, "edge_refused": False, "bot_wall": False,
         "js_dependent": pd.NA, "js_measured": False, "homepage_skipped": True},
        {"domain": "d", "sector": "x", "index_named": False, "index_inherited": False,
         "robots_unreachable": True, "edge_refused": False, "bot_wall": False,
         "js_dependent": False, "js_measured": True, "homepage_skipped": False},
    ])
    extension, _ = barriers(sites)
    revision = _barrier_summary(sites)
    keys = ["any", "any_without_edge", "implicit", "implicit_only", "implicit_without_edge",
            "index_named", "index_inherited", "robots_unreachable", "edge", "js"]
    assert all(extension[key] == revision[key] for key in keys)
    assert all(extension[key]["n"] == 4 for key in keys)


def test_barrier_plot_labels_measured_js_and_full_sample_denominators():
    from experiments.exp1_web_readiness.analyze_extensions import barrier_plot_rows

    keys = ["index_named", "index_inherited", "robots_unreachable", "edge", "js"]
    summary = {key: {"k": 0, "n": 569, "pct": 0.0} for key in keys}
    summary["js"] = {"k": 30, "n": 569, "pct": 5.3}
    summary["any"] = {"k": 199, "n": 569, "pct": 35.0}
    summary["coverage"] = {"sites": 569, "js_measured": 269, "js_unmeasured": 300}
    rows = barrier_plot_rows(summary)
    js_label, js_pct, js_n = rows[4]
    all_label, all_pct, all_n = rows[-1]
    assert "n=269" in js_label and js_n == 269 and round(js_pct, 1) == 11.2
    assert "n=569" in all_label and all_n == 569 and all_pct == 35.0
    assert all("n=569" in rows[index][0] and rows[index][2] == 569 for index in range(4))
