"""Offline utilities for the dated follow-up; never called by the main analysis."""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SCHEMA_VERSION = 1
SEED = 20261110


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_jsonl(path):
    path = Path(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, allow_nan=False) + "\n" for r in rows))


def append_jsonl(path, row):
    with Path(path).open("a") as f:
        f.write(json.dumps(row, allow_nan=False) + "\n")
        f.flush()
        import os
        os.fsync(f.fileno())


@contextlib.contextmanager
def exclusive(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another runner owns this output") from exc
        yield


@contextlib.contextmanager
def execution_settings():
    values = {k: os.environ.get(k) for k in ('AEO_TEMPERATURE', 'AEO_NO_RETRIES')}
    os.environ.update(AEO_TEMPERATURE='0', AEO_NO_RETRIES='1')
    try:
        yield
    finally:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def request_ceiling(spec, system, user, max_tokens):
    from aeotools.llm import estimate_cost
    if type(max_tokens) is not int or max_tokens <= 0:
        raise ValueError("Output token limit must be positive")
    # Byte-count input allowance is deliberately more conservative than chars/4 planning.
    return estimate_cost(spec, len((system + user).encode()) + 256, max_tokens)


class BudgetLog:
    """Reserve before calls; refuse ambiguous interrupted calls on resume."""
    def __init__(self, output, fingerprint, total_cap, model_caps=None):
        self.output = Path(output)
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.journal = self.output.with_suffix(self.output.suffix + ".requests.jsonl")
        self.rows = read_jsonl(self.output)
        self.requests = read_jsonl(self.journal)
        self.fingerprint = fingerprint
        self.total_cap, self.model_caps = total_cap, model_caps or {}
        if not math.isfinite(total_cap) or total_cap <= 0:
            raise ValueError("Spending cap must be positive and finite")
        if any(not math.isfinite(v) or v <= 0 for v in self.model_caps.values()):
            raise ValueError("Per-model caps must be positive and finite")
        if any(r.get("fingerprint") != fingerprint for r in self.rows + self.requests):
            raise ValueError("Resume fingerprint differs: use a new output for a new protocol/settings")
        completed = {r["request_id"] for r in self.rows}
        if len(completed) != len(self.rows) or completed != {r['request_id'] for r in self.requests}:
            raise ValueError("Unsettled request or inconsistent journal; reconcile before resuming")
        if any(r["request_id"] not in completed for r in self.requests):
            raise ValueError("Unsettled request: reconcile provider usage and journal before resuming; no automatic retry")
        self.by_model = {}
        for row in self.rows:
            charge = float(row["budget_charge_usd"])
            self.by_model[row["model"]] = self.by_model.get(row["model"], 0) + charge

    @property
    def spent(self):
        return sum(self.by_model.values())

    def permits(self, spec, reservation):
        return (self.spent + reservation <= self.total_cap + 1e-12 and
                self.by_model.get(spec, 0) + reservation <= self.model_caps.get(spec, self.total_cap) + 1e-12)

    def start(self, spec, item_id, reservation):
        if not self.permits(spec, reservation):
            raise ValueError("Insufficient budget reservation")
        row = {"request_id": digest([self.fingerprint, spec, item_id, len(self.requests)]),
               "fingerprint": self.fingerprint, "model": spec, "item_id": item_id,
               "reserved_usd": reservation, "started_at": timestamp()}
        append_jsonl(self.journal, row)
        self.requests.append(row)
        return row

    def finish(self, request, row):
        cost = float(row.get("cost_usd", 0))
        if not math.isfinite(cost) or cost < 0:
            raise ValueError("Invalid reported cost; reconcile the unsettled request")
        missing_usage = not row.get("input_tokens") or not row.get("output_tokens")
        charge = max(cost, request["reserved_usd"]) if missing_usage else cost
        record = {**request, **row, "completed_at": timestamp(), "budget_charge_usd": charge,
                  "usage_unresolved": missing_usage}
        append_jsonl(self.output, record)
        self.rows.append(record)
        spec = request["model"]
        self.by_model[spec] = self.by_model.get(spec, 0) + charge
        if charge > request["reserved_usd"] + 1e-12:
            raise ValueError("Reported charge exceeded reservation; stop and review provider/settings")
        return record


def holm(values):
    order = np.argsort(values)
    adjusted = np.empty(len(values))
    bound = 0.
    for rank, idx in enumerate(order):
        bound = max(bound, min(1., values[idx] * (len(values) - rank)))
        adjusted[idx] = bound
    return adjusted.tolist()


def effect(rows, *, n_boot=4000, n_perm=10000, seed=SEED, developers=None):
    """Equal-model estimates; common scenario resampling/signs preserve model dependence."""
    if rows.empty:
        return {"effect": None, "ci_low": None, "ci_high": None, "p": None,
                "n_pairs": 0, "n_models": 0, "n_scenarios": 0}
    if rows.duplicated(["model", "scenario", "trial_id"]).any():
        raise ValueError("Duplicate paired trials")
    agg = rows.groupby(["scenario", "model"]).delta.agg(["sum", "count"])
    sums = agg["sum"].unstack(fill_value=0)
    counts = agg["count"].unstack(fill_value=0).reindex_like(sums)
    a, b = sums.to_numpy(), counts.to_numpy()
    weights = np.ones(a.shape[1]) / a.shape[1]
    if developers:
        groups = [developers[m] for m in sums.columns]
        weights = np.array([1 / (len(set(groups)) * groups.count(g)) for g in groups])
    observed = float((a.sum(0) / b.sum(0)) @ weights)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(a), (n_boot, len(a)))
    denom = b[indices].sum(1)
    valid = (denom > 0).all(1)
    boot = (a[indices].sum(1)[valid] / denom[valid]) @ weights
    signs = rng.choice([-1., 1.], (n_perm, len(a)))
    null = ((signs @ a) / b.sum(0)) @ weights
    lo, hi = np.quantile(boot, [.025, .975])
    return {"effect": observed, "ci_low": float(lo), "ci_high": float(hi),
            "p": float((1 + (abs(null) >= abs(observed) - 1e-12).sum()) / (n_perm + 1)),
            "n_pairs": len(rows), "n_models": a.shape[1], "n_scenarios": len(a),
            "bootstrap_valid": int(valid.sum()), "bootstrap_requested": n_boot}


def agreement(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    table = [[0, 0], [0, 0]]
    for x, y in pairs:
        table[int(x)][int(y)] += 1
    n = len(pairs)
    if not n:
        return {"n": 0, "confusion": table, "agreement": None, "kappa": None}
    observed = (table[0][0] + table[1][1]) / n
    pa = sum(x for x, _ in pairs) / n
    pb = sum(y for _, y in pairs) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return {"n": n, "confusion": table, "agreement": observed,
            "kappa": (observed - expected) / (1 - expected) if expected < 1 else None}


def require_private(*paths):
    root = Path(__file__).resolve().parent / 'data' / 'private'
    for path in paths:
        if not Path(path).resolve().is_relative_to(root.resolve()):
            raise ValueError(f'Private follow-up material must remain under {root}')
