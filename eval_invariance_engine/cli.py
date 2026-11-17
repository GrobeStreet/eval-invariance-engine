"""CLI for paired correctness diagnostics; invalid inputs exit with status 2."""
from __future__ import annotations

import argparse
import json
from typing import Dict, List, Optional

from .perturbations import MCQItem, all_cyclic_variants
from .report import build_report
from .validation import results_from_rows, validate_results


def _demo_results() -> Dict[str, List[bool]]:
    items = [
        MCQItem("2+2=?", ["4", "5", "6", "7"], 0),
        MCQItem("Capital of France?", ["Paris", "Rome", "Bonn", "Madrid"], 0),
        MCQItem("H2O is?", ["Water", "Gold", "Salt", "Iron"], 0),
        MCQItem("Largest planet?", ["Jupiter", "Mars", "Venus", "Mercury"], 0),
    ]
    results = {f"shift{s}": [] for s in range(4)}
    for item in items:
        for shift, variant in enumerate(all_cyclic_variants(item)):
            results[f"shift{shift}"].append(0 == variant.answer_index)
    return results


def _load_results(path: str, assume_aligned: bool = False) -> Dict[str, List[bool]]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        if not assume_aligned:
            raise ValueError("mapping input needs --assume-aligned; prefer rows with explicit item_id")
        return validate_results(data)
    return results_from_rows(data)


def _emit(results, threshold, seed, fail_on_drift, json_output=False, n_boot=2000) -> int:
    report = build_report(results, fragile_threshold=threshold, seed=seed, n_boot=n_boot)
    print(json.dumps(report.to_dict(), indent=2, allow_nan=False) if json_output else report.summary())
    return int(fail_on_drift and report.verdict == "drift_above_threshold")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="invariance-check", description="Paired correctness diagnostics.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    demo = sub.add_parser("demo", help="offline position-bias example")
    report = sub.add_parser("report", help="analyze item_id/condition/correct JSON rows")
    report.add_argument("path")
    report.add_argument("--assume-aligned", action="store_true", help="explicitly trust positional mapping alignment")
    for command in (demo, report):
        command.add_argument("--fail-on-drift", "--fail-on-fragile", dest="fail_on_drift",
                             action="store_true", help="exit 1 if observed accuracy drift exceeds threshold")
        command.add_argument("--threshold", type=float, default=0.03, help="accuracy drift tolerance, default 0.03")
        command.add_argument("--seed", type=int, default=0)
        command.add_argument("--bootstrap-samples", type=int, default=2000)
        command.add_argument("--json", action="store_true", help="emit report JSON")
    args = parser.parse_args(argv)
    try:
        results = _demo_results() if args.cmd == "demo" else _load_results(args.path, args.assume_aligned)
        return _emit(results, args.threshold, args.seed, args.fail_on_drift, args.json, args.bootstrap_samples)
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
