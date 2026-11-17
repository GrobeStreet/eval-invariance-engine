"""Paired correctness diagnostics, not a certification of invariance.

The bootstrap interval describes empirical item-resampling variability. It is
not an equivalence test, and can be degenerate for small or uniform samples.
The verdict concerns observed aggregate accuracy drift only; inspect flip_rate
separately. Identical aggregate scores can hide different per-item outcomes.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


def results_from_rows(rows: List[Dict[str, Any]]) -> Dict[str, List[bool]]:
    """Align strict boolean outcomes by explicit item_id, never by row order.

    Every item must occur exactly once under every condition. item_id accepts
    nonempty strings or integers; integer 1 and string "1" remain distinct.
    """
    if not isinstance(rows, list) or not rows:
        raise ValueError("expected a nonempty list of item_id/condition/correct rows")
    grouped: Dict[str, Dict[Tuple[str, Any], bool]] = {}
    for position, row in enumerate(rows):
        if not isinstance(row, dict) or not {"item_id", "condition", "correct"} <= row.keys():
            raise ValueError(f"row {position}: requires item_id, condition, and correct")
        item = row["item_id"]
        if type(item) not in (int, str) or (isinstance(item, str) and not item.strip()):
            raise ValueError(f"row {position}: item_id must be an integer or nonempty string")
        condition, correct = row["condition"], row["correct"]
        if not isinstance(condition, str) or not condition.strip():
            raise ValueError(f"row {position}: condition must be a nonempty string")
        if type(correct) is not bool:
            raise ValueError(f"row {position}: correct must be a JSON boolean, not a string or number")
        key = (type(item).__name__, item)
        values = grouped.setdefault(condition, {})
        if key in values:
            raise ValueError(f"row {position}: duplicate item_id/condition pair")
        values[key] = correct
    conditions = sorted(grouped)
    keys = set(grouped[conditions[0]])
    if any(set(grouped[c]) != keys for c in conditions):
        raise ValueError("every condition must contain exactly the same item IDs")
    ordered = sorted(keys)
    return {c: [grouped[c][key] for key in ordered] for c in conditions}


@dataclass
class InvarianceReport:
    conditions: List[str]
    per_condition_accuracy: Dict[str, float]
    max_drift: float
    flip_rate: float
    drift_ci95: Tuple[float, float]
    n_items: int
    verdict: str

    def summary(self) -> str:
        accs = ", ".join(f"{c}={a:.3f}" for c, a in self.per_condition_accuracy.items())
        lo, hi = self.drift_ci95
        return (
            f"[{self.verdict.upper()}] n={self.n_items} | drift={self.max_drift:.3f} "
            f"(empirical bootstrap 95% interval {lo:.3f}-{hi:.3f}) | "
            f"flip_rate={self.flip_rate:.3f} | {accs} | "
            "drift-only diagnostic; not proof of equivalence"
        )


def _percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        raise ValueError("percentile requires at least one bootstrap replicate")
    return sorted_vals[min(int(p * len(sorted_vals)), len(sorted_vals) - 1)]


def build_report(
    results: Dict[str, List[bool]],
    fragile_threshold: float = 0.03,
    n_boot: int = 2000,
    seed: int = 0,
) -> InvarianceReport:
    """Score an explicitly position-aligned condition mapping.

    Low-level API: the caller is responsible for matching item identities.
    Prefer results_from_rows() for externally sourced results. 'below_threshold'
    describes a point estimate; it does not establish invariance or readiness.
    The bootstrap assumes independently sampled items, paired across conditions.
    """
    if not isinstance(results, dict) or len(results) < 2:
        raise ValueError("results must contain at least two conditions")
    if type(fragile_threshold) not in (int, float) or not math.isfinite(fragile_threshold) or not 0 <= fragile_threshold <= 1:
        raise ValueError("fragile_threshold must be finite and between 0 and 1")
    if type(n_boot) is not int or n_boot < 1:
        raise ValueError("n_boot must be a positive integer")
    for condition, values in results.items():
        if not isinstance(condition, str) or not condition.strip():
            raise ValueError("condition names must be nonempty strings")
        if not isinstance(values, (list, tuple)) or any(type(x) is not bool for x in values):
            raise ValueError("condition outcomes must be lists or tuples of booleans")
    conds = list(results)
    n = len(results[conds[0]])
    if n == 0:
        raise ValueError("results must contain at least one paired item")
    if any(len(results[c]) != n for c in conds):
        raise ValueError("all conditions must have the same number of items")

    acc = {c: sum(results[c]) / n for c in conds}
    max_drift = max(acc.values()) - min(acc.values())
    flips = sum(len({results[c][i] for c in conds}) > 1 for i in range(n))
    flip_rate = flips / n
    rng = random.Random(seed)
    drifts: List[float] = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        a = [sum(results[c][j] for j in idx) / n for c in conds]
        drifts.append(max(a) - min(a))
    drifts.sort()
    ci = (_percentile(drifts, 0.025), _percentile(drifts, 0.975))
    verdict = "fragile" if max_drift > fragile_threshold else "below_threshold"
    return InvarianceReport(conds, acc, max_drift, flip_rate, ci, n, verdict)
