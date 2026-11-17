"""Descriptive paired correctness diagnostics, not an equivalence test."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

from .validation import point_metrics, results_from_rows, validate_results


@dataclass
class InvarianceReport:
    conditions: List[str]
    per_condition_accuracy: Dict[str, float]
    max_drift: float
    correctness_flip_rate: float
    drift_ci95: Tuple[float, float]
    n_items: int
    verdict: str
    drift_threshold: float
    bootstrap_samples: int
    bootstrap_seed: int
    interval_method: str = "paired-item percentile bootstrap; exploratory, not an equivalence test"

    @property
    def flip_rate(self) -> float:
        """Compatibility alias: correctness changes, NOT underlying-answer changes."""
        return self.correctness_flip_rate

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        accs = ", ".join(f"{c}={a:.3f}" for c, a in self.per_condition_accuracy.items())
        lo, hi = self.drift_ci95
        return (
            f"[{self.verdict.upper()}] n={self.n_items} | drift={self.max_drift:.3f} "
            f"(95% paired-item bootstrap {lo:.3f}-{hi:.3f}) | "
            f"correctness_flip_rate={self.correctness_flip_rate:.3f} | {accs} | "
            "descriptive threshold check, not evidence of equivalence"
        )


def _percentile(sorted_vals: List[float], p: float) -> float:
    position = (len(sorted_vals) - 1) * p
    lower, upper = math.floor(position), math.ceil(position)
    return sorted_vals[lower] + (sorted_vals[upper] - sorted_vals[lower]) * (position - lower)


def build_report(
    results: Dict[str, List[bool]],
    fragile_threshold: float = 0.03,
    n_boot: int = 2000,
    seed: int = 0,
) -> InvarianceReport:
    """Analyze item-aligned boolean arrays or item_id/condition/correct rows.

    Mapping callers assert positional alignment. fragile_threshold retains its
    old keyword for compatibility, but only gates observed accuracy drift.
    The item bootstrap assumes independent original items. Its percentile
    interval does not establish equivalence or guarantee nominal coverage,
    especially for a max-over-conditions statistic or very small samples.
    """
    results = results_from_rows(results) if isinstance(results, (list, tuple)) else validate_results(results)
    if (isinstance(fragile_threshold, bool)
            or not isinstance(fragile_threshold, (int, float))
            or not math.isfinite(fragile_threshold)
            or not 0 <= fragile_threshold <= 1):
        raise ValueError("drift threshold must be finite and between 0 and 1")
    if type(n_boot) is not int or n_boot < 200:
        raise ValueError("n_boot must be an integer of at least 200; use 2000 or more for reports")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    conds = list(results)
    n = len(results[conds[0]])
    acc, max_drift, flip_rate = point_metrics(results)
    rng = random.Random(seed)
    drifts = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        accuracies = [sum(results[c][j] for j in idx) / n for c in conds]
        drifts.append(max(accuracies) - min(accuracies))
    drifts.sort()
    ci = (_percentile(drifts, 0.025), _percentile(drifts, 0.975))
    verdict = "drift_above_threshold" if max_drift > fragile_threshold else "drift_not_above_threshold"
    return InvarianceReport(conds, acc, max_drift, flip_rate, ci, n, verdict,
                            float(fragile_threshold), n_boot, seed)
