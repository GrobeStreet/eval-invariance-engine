"""`invariance-check` — a small CLI over the invariance engine.

Usage:
  invariance-check demo                     run the built-in fragility demo
  invariance-check report results.json      score a results file, print the report
  invariance-check report results.json --fail-on-fragile   exit 1 if fragile (CI gate)

`results.json` is either a mapping {condition: [true, false, ...]} or a list of
{"condition": "...", "correct": true} rows.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List, Optional

from .perturbations import MCQItem, all_cyclic_variants
from .report import build_report


def _demo_results() -> Dict[str, List[bool]]:
    """A memorized position-bias model (always picks option A) over cyclic reorderings."""
    items = [
        MCQItem("2+2=?", ["4", "5", "6", "7"], 0),
        MCQItem("Capital of France?", ["Paris", "Rome", "Bonn", "Madrid"], 0),
        MCQItem("H2O is?", ["Water", "Gold", "Salt", "Iron"], 0),
        MCQItem("Largest planet?", ["Jupiter", "Mars", "Venus", "Mercury"], 0),
    ]
    results: Dict[str, List[bool]] = {f"shift{s}": [] for s in range(4)}
    for item in items:
        for shift, variant in enumerate(all_cyclic_variants(item)):
            results[f"shift{shift}"].append(0 == variant.answer_index)
    return results


def _load_results(path: str) -> Dict[str, List[bool]]:
    with open(path) as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        return {k: [bool(x) for x in v] for k, v in data.items()}
    by_cond: Dict[str, List[bool]] = {}
    for row in data:
        by_cond.setdefault(row["condition"], []).append(bool(row["correct"]))
    return by_cond


def _emit(results, threshold, seed, fail_on_fragile) -> int:
    report = build_report(results, fragile_threshold=threshold, seed=seed)
    print(report.summary())
    return 1 if (fail_on_fragile and report.verdict == "fragile") else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="invariance-check",
        description="Measure whether an eval score survives non-semantic perturbation.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("demo", help="run the built-in fragility demo")
    d.add_argument("--fail-on-fragile", action="store_true")

    r = sub.add_parser("report", help="score a results JSON file")
    r.add_argument("path")
    r.add_argument("--threshold", type=float, default=0.03, help="fragile if drift exceeds this")
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--fail-on-fragile", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "demo":
        return _emit(_demo_results(), 0.03, 0, args.fail_on_fragile)
    return _emit(_load_results(args.path), args.threshold, args.seed, args.fail_on_fragile)


if __name__ == "__main__":
    sys.exit(main())
