"""Turn per-condition correctness into an invariance verdict.

Given the same items scored under several non-semantic conditions, we report:
  - per-condition accuracy,
  - max_drift: the spread between the best and worst condition,
  - flip_rate: the fraction of items whose correctness changed across conditions
    (the sharpest signal of non-semantic sensitivity),
  - a bootstrap 95% CI on the drift,
  - a verdict: 'fragile' if the drift exceeds a threshold, else 'invariant'.

Pure standard library. Deterministic given `seed`.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


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
            f"(95% CI {lo:.3f}-{hi:.3f}) | flip_rate={self.flip_rate:.3f} | {accs}"
        )


def _percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = min(int(p * len(sorted_vals)), len(sorted_vals) - 1)
    return sorted_vals[k]


def build_report(
    results: Dict[str, List[bool]],
    fragile_threshold: float = 0.03,
    n_boot: int = 2000,
    seed: int = 0,
) -> InvarianceReport:
    """results: condition-name -> per-item correctness (all lists item-aligned, equal length)."""
    if not results:
        raise ValueError("results must contain at least one condition")
    conds = list(results.keys())
    n = len(results[conds[0]])
    for c in conds:
        if len(results[c]) != n:
            raise ValueError("all conditions must have the same number of items")

    acc = {c: (sum(1 for x in results[c] if x) / n if n else 0.0) for c in conds}
    max_drift = (max(acc.values()) - min(acc.values())) if acc else 0.0

    flips = 0
    for i in range(n):
        if len({results[c][i] for c in conds}) > 1:
            flips += 1
    flip_rate = flips / n if n else 0.0

    rng = random.Random(seed)
    drifts: List[float] = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)] if n else []
        a = {c: (sum(1 for j in idx if results[c][j]) / n if n else 0.0) for c in conds}
        drifts.append((max(a.values()) - min(a.values())) if a else 0.0)
    drifts.sort()
    ci = (_percentile(drifts, 0.025), _percentile(drifts, 0.975))

    verdict = "fragile" if max_drift > fragile_threshold else "invariant"
    return InvarianceReport(conds, acc, max_drift, flip_rate, ci, n, verdict)
