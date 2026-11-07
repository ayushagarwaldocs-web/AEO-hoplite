"""Minimum detectable effects (exploratory; added 6 November 2026 to help read the null results).

For every treatment-versus-baseline contrast on mentions, the standard error is approximated from the 95% cluster-
bootstrap interval of analyze.py (width / 3.92). The minimum detectable effect with 80% power at a two-sided 5% level
is then 2.80 standard errors; at the strictest Holm threshold over the 14 treatments (0.05 / 14) it is 3.75 standard
errors (z = 2.91 + 0.84). Reported pooled over models and per model, for the main analysis and the replication.

    python3 analyze_power.py        # writes results/mde.csv and results/mde_summary.json
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
Z80, Z80_HOLM = 2.80, 3.75


def main() -> None:
    rows, summary = [], {}
    for tag in ("bedrock", "flagship"):
        f = RES / f"effects_{tag}.csv"
        if not f.exists():
            continue
        e = pd.read_csv(f)
        m = e[(e["outcome"] == "mentioned") & (e["reference"] == "baseline")].copy()
        m["se"] = (m["ci_high"] - m["ci_low"]) / 3.92
        m["mde80"], m["mde80_holm"] = Z80 * m["se"], Z80_HOLM * m["se"]
        m["set"] = tag
        rows.append(m[["set", "model", "condition", "effect", "ci_low", "ci_high", "p_holm", "se", "mde80", "mde80_holm"]])
        pooled, per = m[m["model"] == "pooled"], m[m["model"] != "pooled"]
        summary[tag] = {
            "pooled_mde80_median": round(100 * pooled["mde80"].median(), 1),
            "pooled_mde80_min": round(100 * pooled["mde80"].min(), 1),
            "pooled_mde80_max": round(100 * pooled["mde80"].max(), 1),
            "pooled_mde80_holm_median": round(100 * pooled["mde80_holm"].median(), 1),
            "per_model_mde80_median": round(100 * per["mde80"].median(), 1),
            "per_model_mde80_q25": round(100 * per["mde80"].quantile(0.25), 1),
            "per_model_mde80_q75": round(100 * per["mde80"].quantile(0.75), 1),
            "per_model_mde80_holm_median": round(100 * per["mde80_holm"].median(), 1),
        }
    pd.concat(rows).to_csv(RES / "mde.csv", index=False)
    (RES / "mde_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
