"""Strict correctness inputs shared by reports, CLI and Inspect."""
from collections.abc import Mapping, Sequence


class IncompleteCoverageError(ValueError):
    """Valid cells do not yet cover a complete paired comparison."""


def validate_results(results):
    """Validate explicitly item-aligned arrays; never coerce truthiness."""
    if not isinstance(results, Mapping) or len(results) < 2:
        raise IncompleteCoverageError("results must contain at least two conditions")
    copied = {}
    n = None
    for condition, values in results.items():
        if not isinstance(condition, str) or not condition.strip():
            raise ValueError("condition must be a non-empty string")
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            raise ValueError(f"{condition}: correctness must be a sequence of booleans")
        if not values:
            raise ValueError("each condition must contain at least one item")
        if any(type(value) is not bool for value in values):
            raise ValueError(f"{condition}: correct must be a boolean, not a string or number")
        if n is not None and len(values) != n:
            raise ValueError("all conditions must have the same number of items")
        n = len(values)
        copied[condition] = list(values)
    return copied


def results_from_rows(rows):
    """Pair item_id/condition/correct rows; reject duplicates and missing cells."""
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("rows must be a non-empty list")
    by_condition = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"row {index}: expected an object")
        for field in ("item_id", "condition"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"row {index}: {field} must be a non-empty string")
        if type(row.get("correct")) is not bool:
            raise ValueError(f"row {index}: correct must be a boolean")
        condition, item = row["condition"], row["item_id"]
        cells = by_condition.setdefault(condition, {})
        if item in cells:
            raise ValueError(f"duplicate item_id/condition pair: {item!r}, {condition!r}")
        cells[item] = row["correct"]
    conditions = sorted(by_condition)
    items = sorted(by_condition[conditions[0]])
    for condition in conditions:
        if set(by_condition[condition]) != set(items):
            raise IncompleteCoverageError("every item_id must appear exactly once in every condition (missing coverage)")
    return validate_results({c: [by_condition[c][item] for item in items] for c in conditions})


def point_metrics(results):
    """Return per-condition accuracy, accuracy spread and correctness flip rate."""
    results = validate_results(results)
    n = len(next(iter(results.values())))
    accuracy = {c: sum(v) / n for c, v in results.items()}
    flips = sum(len(set(outcomes)) > 1 for outcomes in zip(*results.values()))
    return accuracy, max(accuracy.values()) - min(accuracy.values()), flips / n
