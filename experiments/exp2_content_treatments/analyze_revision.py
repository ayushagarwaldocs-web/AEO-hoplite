"""Exploratory developer-weight and absolute-probability diagnostics for Study 2.

Estimates describe selected API models and synthetic scenarios, not a population
of models or production answer engines.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze as main_analysis  # noqa: E402
from build_corpus import CONDITIONS  # noqa: E402

BASELINE = "baseline"
TREATMENTS = [c for c in CONDITIONS if c != BASELINE]
BOOTSTRAP_SEED = 20261110

_BEDROCK_DEVELOPERS = (
    ("anthropic", "Anthropic"), ("openai", "OpenAI"), ("deepseek", "DeepSeek"),
    ("qwen", "Alibaba"), ("amazon", "Amazon"), ("google", "Google"),
    ("minimax", "MiniMax"), ("mistral", "Mistral AI"), ("nvidia", "NVIDIA"),
    ("meta", "Meta"), ("moonshotai", "Moonshot AI"), ("zai", "Zhipu AI"),
)
_AZURE_DEVELOPERS = {
    "deepseek-v4-pro": "DeepSeek",
    "kimi-k3.1-pro": "Moonshot AI",
    "mai-thinking-1": "Microsoft",
    "gpt-5-mini": "OpenAI",
    "grok-4.6": "xAI",
}


def developer_for_model(model: str) -> str:
    """Map the API model identifier to its developer, not its serving API."""
    if model.startswith("bedrock:"):
        model_id = model.split(":", 1)[1].casefold()
        for marker, developer in _BEDROCK_DEVELOPERS:
            if marker in model_id:
                return developer
    elif model.startswith("azure:"):
        model_id = model.split(":", 1)[1].casefold()
        if model_id in _AZURE_DEVELOPERS:
            return _AZURE_DEVELOPERS[model_id]
    elif model.startswith("anthropic:"):
        return "Anthropic"
    elif model.startswith("openai:"):
        return "OpenAI"
    elif model.startswith("gemini:"):
        return "Google"
    raise ValueError(f"No explicit model-developer mapping for {model!r}")


def successful_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep observed successful answers; failures are not no-mentions."""
    out = df.copy()
    if "error" in out:
        out = out[out["error"].isna()].copy()
    return out


def paired_rows(df: pd.DataFrame, condition: str) -> pd.DataFrame:
    """Successful same-model, same-scenario, same-trial baseline/treatment pairs."""
    if condition == BASELINE:
        raise ValueError("condition must be a treatment, not baseline")
    data = successful_rows(df)
    data = data[data["condition"].isin([BASELINE, condition])].copy()
    keys = ["model", "scenario", "trial_id"]
    if data.duplicated(keys + ["condition"], keep=False).any():
        raise ValueError("duplicate successful model/scenario/trial/condition rows")
    wide = data.pivot(index=keys, columns="condition", values="mentioned")
    if BASELINE not in wide or condition not in wide:
        return pd.DataFrame(columns=keys + ["developer", "baseline_mentioned", "treated_mentioned", "diff"])
    wide = wide[[BASELINE, condition]].dropna().rename(
        columns={BASELINE: "baseline_mentioned", condition: "treated_mentioned"}
    ).reset_index()
    wide["baseline_mentioned"] = wide["baseline_mentioned"].astype(float)
    wide["treated_mentioned"] = wide["treated_mentioned"].astype(float)
    wide["diff"] = wide["treated_mentioned"] - wide["baseline_mentioned"]
    wide["developer"] = wide["model"].map(developer_for_model)
    return wide


def aggregate_trials(
    pairs: pd.DataFrame, weighting: str, excluded_developer: str | None = None
) -> pd.DataFrame:
    """Return one estimate: average successful trial means per model, then weight models/developers."""
    data = pairs
    if excluded_developer is not None:
        data = data[data["developer"] != excluded_developer]
    columns = ["baseline_mentioned", "treated_mentioned", "diff"]
    if data.empty:
        return pd.DataFrame(columns=columns)
    model_means = data.groupby(["model", "developer"], as_index=False)[columns].mean()
    if weighting == "equal_model":
        estimate = model_means[columns].mean()
    elif weighting == "equal_developer":
        developer_means = model_means.groupby("developer")[columns].mean()
        estimate = developer_means.mean()
    else:
        raise ValueError(f"unknown weighting: {weighting}")
    return pd.DataFrame([estimate.to_dict()])


def _cluster_interval(
    pairs: pd.DataFrame, weighting: str, bootstrap_samples: int,
    excluded_developer: str | None = None,
) -> tuple[float, float]:
    """Scenario-cluster bootstrap for the hierarchical successful-pair estimand."""
    data = pairs
    if excluded_developer is not None:
        data = data[data["developer"] != excluded_developer]
    if data.empty or bootstrap_samples < 1:
        return float("nan"), float("nan")

    scenarios = sorted(data["scenario"].unique())
    models = sorted(data["model"].unique())
    grouped = data.groupby(["scenario", "model"], sort=True)
    counts = grouped.size().unstack("model").reindex(index=scenarios, columns=models, fill_value=0).to_numpy(dtype=float)
    sums = grouped["diff"].sum().unstack("model").reindex(index=scenarios, columns=models, fill_value=0).to_numpy(dtype=float)

    n_scenarios = len(scenarios)
    sampled = main_analysis.RNG.integers(0, n_scenarios, size=(bootstrap_samples, n_scenarios))
    multiplicities = np.zeros((bootstrap_samples, n_scenarios), dtype=np.int16)
    np.add.at(multiplicities, (np.arange(bootstrap_samples)[:, None], sampled), 1)
    model_counts = multiplicities @ counts
    model_sums = multiplicities @ sums
    with np.errstate(divide="ignore", invalid="ignore"):
        model_effects = model_sums / model_counts
    model_effects[model_counts == 0] = np.nan

    if weighting in {"equal_model", "model"}:
        estimates = np.nanmean(model_effects, axis=1)
    elif weighting in {"equal_developer", "developer", "leave_one_developer_out"}:
        model_developer = data[["model", "developer"]].drop_duplicates().set_index("model")["developer"]
        developers = sorted(model_developer.unique())
        developer_effects = np.column_stack([
            np.nanmean(model_effects[:, [i for i, model in enumerate(models) if model_developer[model] == dev]], axis=1)
            for dev in developers
        ])
        estimates = np.nanmean(developer_effects, axis=1)
    else:
        raise ValueError(f"unknown weighting: {weighting}")
    estimates = estimates[np.isfinite(estimates)]
    if not len(estimates):
        return float("nan"), float("nan")
    return float(np.percentile(estimates, 2.5)), float(np.percentile(estimates, 97.5))


def _estimate(
    pairs: pd.DataFrame, estimate: pd.DataFrame, weighting: str, condition: str,
    dataset: str, bootstrap_samples: int, *, group: str = "",
    excluded_developer: str = "", interval_pairs: pd.DataFrame | None = None,
) -> dict[str, Any]:
    if estimate.empty:
        base = treated = effect = low = high = float("nan")
    else:
        base = float(estimate.iloc[0]["baseline_mentioned"])
        treated = float(estimate.iloc[0]["treated_mentioned"])
        effect = float(estimate.iloc[0]["diff"])
        low, high = _cluster_interval(
            interval_pairs if interval_pairs is not None else pairs, weighting, bootstrap_samples,
            excluded_developer=excluded_developer or None,
        )
    return {
        "dataset": dataset, "condition": condition, "weighting": weighting,
        "group": group, "excluded_developer": excluded_developer,
        "n_paired": int(len(pairs)),
        "n_trials": int(pairs[["scenario", "trial_id"]].drop_duplicates().shape[0]) if not pairs.empty else 0,
        "n_scenarios": int(pairs["scenario"].nunique()) if not pairs.empty else 0,
        "n_models": int(pairs["model"].nunique()) if not pairs.empty else 0,
        "n_developers": int(pairs["developer"].nunique()) if not pairs.empty else 0,
        "baseline_probability": base, "treated_probability": treated,
        "effect": effect, "ceiling_headroom": 1.0 - base if np.isfinite(base) else float("nan"),
        "ci_low": low, "ci_high": high,
    }

def target_length_summaries(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """Summarise deduplicated successful target-page stimuli and paired length changes."""
    data = successful_rows(df)
    stimuli = data[["scenario", "trial_id", "condition", "target_words"]].drop_duplicates()
    if stimuli.duplicated(["scenario", "trial_id", "condition"], keep=False).any():
        raise ValueError("target_words differs across model records for the same page stimulus")
    stimuli["target_words"] = pd.to_numeric(stimuli["target_words"], errors="raise")
    baseline = stimuli[stimuli.condition == BASELINE][
        ["scenario", "trial_id", "target_words"]
    ].rename(columns={"target_words": "baseline_words"})
    rows = []
    conditions = [BASELINE] + [c for c in TREATMENTS if c in set(stimuli.condition)]
    for condition in conditions:
        current = stimuli[stimuli.condition == condition].copy()
        paired = current.merge(baseline, on=["scenario", "trial_id"], how="inner", validate="one_to_one")
        words = current["target_words"]
        delta = paired["target_words"] - paired["baseline_words"]
        rows.append({
            "dataset": dataset, "condition": condition, "n_pages": int(len(current)),
            "n_paired_pages": int(len(paired)),
            "mean_words": float(words.mean()) if len(words) else float("nan"),
            "median_words": float(words.median()) if len(words) else float("nan"),
            "sd_words": float(words.std(ddof=1)) if len(words) > 1 else 0.0,
            "q1_words": float(words.quantile(.25)) if len(words) else float("nan"),
            "q3_words": float(words.quantile(.75)) if len(words) else float("nan"),
            "min_words": int(words.min()) if len(words) else None,
            "max_words": int(words.max()) if len(words) else None,
            "mean_delta_vs_baseline": float(delta.mean()) if len(delta) else float("nan"),
            "median_delta_vs_baseline": float(delta.median()) if len(delta) else float("nan"),
            "q1_delta_vs_baseline": float(delta.quantile(.25)) if len(delta) else float("nan"),
            "q3_delta_vs_baseline": float(delta.quantile(.75)) if len(delta) else float("nan"),
        })
    return pd.DataFrame(rows)


def _json_number(value: Any) -> int | float | None:
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer, int)):
        return int(value)
    return float(value)


def _ranking_summary(weighted: pd.DataFrame, lodo: pd.DataFrame) -> dict[str, Any]:
    model = weighted[weighted.weighting == "equal_model"].set_index("condition").effect
    developer = weighted[weighted.weighting == "equal_developer"].set_index("condition").effect
    model_order = model.sort_values(ascending=False, kind="stable").index.tolist()
    developer_order = developer.sort_values(ascending=False, kind="stable").index.tolist()
    rho = model.rank().corr(developer.rank(), method="pearson")
    stability = {}
    for condition, rows in lodo.groupby("condition"):
        ranks = rows["rank"].astype(int)
        stability[condition] = {
            "rank_min": int(ranks.min()), "rank_max": int(ranks.max()),
            "rank_mean": float(ranks.mean()), "top_rank_count": int((ranks == 1).sum()),
        }
    top_model, top_dev = model_order[:3], developer_order[:3]
    return {
        "equal_model_order": model_order, "equal_developer_order": developer_order,
        "spearman_rank_correlation": float(rho) if pd.notna(rho) else None,
        "top_three_equal_model": top_model, "top_three_equal_developer": top_dev,
        "top_three_overlap": [c for c in top_model if c in top_dev],
        "leave_one_developer_out_rank_stability": stability,
    }


def analyze_dataset(
    df: pd.DataFrame, dataset: str, source: str, bootstrap_samples: int = 4000
) -> dict[str, Any]:
    data = successful_rows(df)
    models = sorted(data.model.unique())
    developer_map = {model: developer_for_model(model) for model in models}
    trial_count = int(data[["scenario", "trial_id"]].drop_duplicates().shape[0])
    weighted_rows, developer_rows, model_rows, lodo_rows = [], [], [], []
    missing_pair_details = {}
    baseline_keys = data[data.condition == BASELINE][["model", "scenario", "trial_id"]].drop_duplicates()

    for condition in [c for c in TREATMENTS if c in set(data.condition)]:
        pairs = paired_rows(data, condition)
        expected_pairs = len(models) * trial_count
        matched_keys = pairs[["model", "scenario", "trial_id"]].drop_duplicates()
        missing = baseline_keys.merge(
            matched_keys, on=["model", "scenario", "trial_id"], how="left", indicator=True
        ).query('_merge == "left_only"')
        if not missing.empty:
            missing_pair_details[condition] = [
                {"model": row.model, "scenario": row.scenario, "trial_id": row.trial_id,
                 "status": "no successful paired treatment response"}
                for row in missing.itertuples(index=False)
            ]
        for weighting in ("equal_model", "equal_developer"):
            estimate = aggregate_trials(pairs, weighting)
            row = _estimate(pairs, estimate, weighting, condition, dataset, bootstrap_samples)
            row["n_expected_pairs"] = expected_pairs
            row["n_missing_pairs"] = expected_pairs - len(pairs)
            weighted_rows.append(row)
        for developer in sorted(pairs.developer.unique()):
            subset = pairs[pairs.developer == developer]
            estimate = aggregate_trials(subset, "equal_developer")
            row = _estimate(subset, estimate, "developer", condition, dataset, 0, group=developer)
            row["n_expected_pairs"] = subset["model"].nunique() * trial_count
            row["n_missing_pairs"] = row["n_expected_pairs"] - len(subset)
            developer_rows.append(row)
        for model in sorted(pairs.model.unique()):
            subset = pairs[pairs.model == model]
            estimate = aggregate_trials(subset, "equal_model")
            row = _estimate(subset, estimate, "model", condition, dataset, 0, group=model)
            row["n_expected_pairs"] = trial_count
            row["n_missing_pairs"] = trial_count - len(subset)
            model_rows.append(row)

        full = next(r for r in weighted_rows if r["condition"] == condition and r["weighting"] == "equal_developer")
        for excluded in sorted(pairs.developer.unique()):
            remaining = pairs[pairs.developer != excluded]
            estimate = aggregate_trials(pairs, "equal_developer", excluded_developer=excluded)
            row = _estimate(
                remaining, estimate, "leave_one_developer_out", condition, dataset,
                bootstrap_samples, excluded_developer=excluded, interval_pairs=pairs,
            )
            row["delta_vs_full"] = row["effect"] - full["effect"]
            row["n_expected_pairs"] = remaining["model"].nunique() * trial_count
            row["n_missing_pairs"] = row["n_expected_pairs"] - len(remaining)
            lodo_rows.append(row)

    weighted, developers = pd.DataFrame(weighted_rows), pd.DataFrame(developer_rows)
    models_df, lodo = pd.DataFrame(model_rows), pd.DataFrame(lodo_rows)
    if not lodo.empty:
        lodo["rank"] = lodo.groupby("excluded_developer").effect.rank(
            ascending=False, method="min"
        ).astype(int)
    lengths = target_length_summaries(data, dataset)

    by_condition = {}
    fields = (
        "n_paired", "n_expected_pairs", "n_missing_pairs", "n_trials", "n_scenarios",
        "n_models", "n_developers", "baseline_probability", "treated_probability",
        "effect", "ceiling_headroom", "ci_low", "ci_high",
    )
    for condition, rows in weighted.groupby("condition", sort=False):
        by_condition[condition] = {
            row["weighting"]: {field: _json_number(row[field]) for field in fields}
            for _, row in rows.iterrows()
        }
    summary = {
        "source": source, "n_input_rows": int(len(df)),
        "n_successful_rows": int(len(data)), "n_models": len(models),
        "n_developers": len(set(developer_map.values())),
        "n_scenarios": int(data.scenario.nunique()), "n_trials": trial_count,
        "developer_map": developer_map,
        "scope": "Selected API models and synthetic scenarios; not a model-population or production-engine estimate.",
        "pairing": "Only successful same-model, same-scenario, same-trial baseline/treatment pairs are analysed; failed and unmatched rows are not imputed.",
        "missing_pair_details": missing_pair_details,
        "estimand": {
            "equal_model": "For each selected model, mean baseline, treated, and paired-difference outcomes across that model's successful paired trials; then equal-weight the model means.",
            "equal_developer": "For each selected model, mean outcomes across its successful paired trials; average model means equally within each developer; then average developer means equally.",
            "uncertainty": "Scenario-cluster bootstrap of the corresponding hierarchical estimator; resampled estimates use available selected models/developers in each replicate.",
            "missingness": "n_expected_pairs and n_missing_pairs are reported by condition; estimates use successful paired trials only.",
        },
        "weighted_effects": by_condition,
        "ranking": _ranking_summary(weighted, lodo),
        "leave_one_developer_out": {
            "n_exclusions_per_condition": int(lodo["excluded_developer"].nunique()) if not lodo.empty else 0,
            "minimum_effect": float(lodo.effect.min()) if not lodo.empty else None,
            "maximum_effect": float(lodo.effect.max()) if not lodo.empty else None,
        },
    }
    return {
        "summary": summary,
        "developer_effects": pd.concat([weighted, developers], ignore_index=True),
        "model_effects": models_df,
        "leave_one_developer_out": lodo,
        "target_lengths": lengths,
    }


def focus_table(summaries: dict[str, Any], lodo: pd.DataFrame) -> pd.DataFrame:
    """Compact descriptive table for the four focal content-package treatments."""
    labels = {
        "third_party": "Third-party endorsement",
        "citations": "Source citations",
        "statistics": "Statistics",
        "keyword_stuffing": "Keyword stuffing",
    }
    rows = []
    for dataset, summary in summaries.items():
        for condition, label in labels.items():
            estimates = summary["weighted_effects"].get(condition)
            if not estimates:
                continue
            model = estimates["equal_model"]
            developer = estimates["equal_developer"]
            deleted = lodo[(lodo.dataset == dataset) & (lodo.condition == condition)]
            rows.append({
                "dataset": dataset, "treatment": condition, "label": label,
                "n_paired": developer["n_paired"], "n_missing_pairs": developer["n_missing_pairs"],
                "equal_model_baseline_probability": model["baseline_probability"],
                "equal_model_treated_probability": model["treated_probability"],
                "equal_model_effect": model["effect"],
                "equal_developer_baseline_probability": developer["baseline_probability"],
                "equal_developer_treated_probability": developer["treated_probability"],
                "equal_developer_effect": developer["effect"],
                "equal_developer_ci_low": developer["ci_low"],
                "equal_developer_ci_high": developer["ci_high"],
                "equal_developer_ceiling_headroom": developer["ceiling_headroom"],
                "leave_one_developer_out_min": float(deleted.effect.min()) if not deleted.empty else float("nan"),
                "leave_one_developer_out_max": float(deleted.effect.max()) if not deleted.empty else float("nan"),
                "n_developer_exclusions": int(deleted.excluded_developer.nunique()),
            })
    return pd.DataFrame(rows)

def run(
    bedrock_path: Path, replication_path: Path, output_dir: Path, bootstrap_samples: int = 4000
):
    main_analysis.RNG = np.random.default_rng(BOOTSTRAP_SEED)
    summaries, dev_tables, model_tables, lodo_tables, length_tables = {}, [], [], [], []
    for name, path in (("bedrock", bedrock_path), ("replication", replication_path)):
        try:
            source = path.resolve().relative_to(HERE).as_posix()
        except ValueError:
            source = str(path)
        result = analyze_dataset(pd.read_json(path, lines=True), name, source, bootstrap_samples)
        summaries[name] = result["summary"]
        dev_tables.append(result["developer_effects"])
        model_tables.append(result["model_effects"])
        lodo_tables.append(result["leave_one_developer_out"])
        length_tables.append(result["target_lengths"])
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "analysis": "Exploratory existing-data absolute mention, weighting, developer deletion, and target-page length diagnostics.",
        "bootstrap": {
            "method": "Scenario-cluster bootstrap of the hierarchical successful-pair estimands; selected units absent from a bootstrap resample are omitted in that replicate.",
            "replicates": int(bootstrap_samples), "seed": BOOTSTRAP_SEED,
            "interval": "Percentile 95% interval; descriptive for the sampled scenarios and selected models.",
        },
        "datasets": summaries,
    }
    (output_dir / "revision_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    pd.concat(dev_tables, ignore_index=True).to_csv(output_dir / "revision_developer_effects.csv", index=False)
    pd.concat(model_tables, ignore_index=True).to_csv(output_dir / "revision_model_effects.csv", index=False)
    pd.concat(lodo_tables, ignore_index=True).to_csv(output_dir / "revision_leave_one_developer_out.csv", index=False)
    pd.concat(length_tables, ignore_index=True).to_csv(output_dir / "revision_target_lengths.csv", index=False)
    lodo = pd.concat(lodo_tables, ignore_index=True)
    focus_table(summaries, lodo).to_csv(output_dir / "revision_focus_table.csv", index=False)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bedrock", type=Path, default=HERE / "data" / "responses_bedrock.jsonl")
    parser.add_argument("--replication", type=Path, default=HERE / "data" / "responses_flagship.jsonl")
    parser.add_argument("--output-dir", type=Path, default=HERE / "results")
    parser.add_argument("--bootstrap-samples", type=int, default=4000)
    args = parser.parse_args()
    if args.bootstrap_samples < 1:
        parser.error("--bootstrap-samples must be positive")
    result = run(args.bedrock, args.replication, args.output_dir, args.bootstrap_samples)
    for name, detail in result["datasets"].items():
        print(f"{name}: {detail['n_successful_rows']} successful rows, "
              f"{detail['n_models']} selected models, {detail['n_developers']} developers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
