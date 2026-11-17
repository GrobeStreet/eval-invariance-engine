"""An explicit plain-MCQ audit task, not a semantics-preserving Task wrapper.

Imports are lazy. All aggregation shares strict item/condition validation.
Only cyclic option rotations are generated; whitespace is a separate utility.
"""
from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional

from .perturbations import MCQItem, all_cyclic_variants
from .report import InvarianceReport, build_report
from .validation import point_metrics, results_from_rows

_GROUP_KEY = "invariance_group"
_COND_KEY = "invariance_condition"
_EXPECTED_KEY = "invariance_expected_conditions"


def _validate_letters(letters, n):
    if (not isinstance(letters, str) or not letters.isascii()
            or not letters.isalpha() or letters != letters.upper()
            or len(set(letters)) != len(letters) or len(letters) < n):
        raise ValueError("letters must be distinct uppercase ASCII letters covering all choices")
    if n < 2:
        raise ValueError("an MCQ audit needs at least two choices")


def cyclic_variant_samples(item: MCQItem, group_id: str, letters: str = "ABCD",
                           metadata=None) -> List[Any]:
    from inspect_ai.dataset import Sample
    _validate_letters(letters, len(item.options))
    if not isinstance(group_id, str) or not group_id.strip():
        raise ValueError("group_id must be a non-empty string")
    expected = [f"shift{i}" for i in range(len(item.options))]
    metadata = dict(metadata or {})
    if any(key.startswith("invariance_") for key in metadata):
        raise ValueError("source metadata may not use reserved invariance_ keys")
    samples = []
    for shift, variant in enumerate(all_cyclic_variants(item)):
        body = "\n".join(f"{letters[i]}. {option}" for i, option in enumerate(variant.options))
        samples.append(Sample(
            id=f"{group_id}:shift{shift}",
            input=f"{variant.question}\n{body}\n\nAnswer with the letter of the correct option only.",
            target=letters[variant.answer_index],
            metadata={**metadata, _GROUP_KEY: group_id, _COND_KEY: f"shift{shift}",
                      _EXPECTED_KEY: expected, "invariance_letters": letters[:len(item.options)]},
        ))
    return samples


def _target_to_index(target, choices, letters="ABCD"):
    # Multiple acceptable answers need a different scorer; do not pick the first.
    if isinstance(target, (list, tuple, bool)) or target is None:
        return None
    if type(target) is int:
        return target if 0 <= target < len(choices) else None
    if not isinstance(target, str):
        return None
    target = target.strip()
    if len(target) == 1 and target.upper() in letters[:len(choices)]:
        return letters.index(target.upper())
    matches = [i for i, choice in enumerate(choices) if target == choice]
    return matches[0] if len(matches) == 1 else None


def cyclic_mcq_task(samples, letters="ABCD", name="cyclic-mcq-audit"):
    """Build a NEW generate-only Task from plain question/choices/target samples.

    Source Task solvers, scorers, tools, sandbox, setup, model configuration,
    epochs and limits are not inherited. Configure this new task deliberately.
    Reject non-MCQ/chat/file-bearing samples and mixed choice counts.
    """
    from inspect_ai import Task
    from inspect_ai.dataset import MemoryDataset
    from inspect_ai.solver import generate
    expanded, seen, choice_count = [], set(), None
    for index, sample in enumerate(samples):
        choices = list(getattr(sample, "choices", None) or [])
        if not choices:
            raise ValueError("no multiple-choice samples: every sample needs choices and one target")
        if not isinstance(sample.input, str) or getattr(sample, "files", None) or getattr(sample, "setup", None):
            raise ValueError("only plain-text MCQ samples without files/setup are supported")
        _validate_letters(letters, len(choices))
        if choice_count is not None and len(choices) != choice_count:
            raise ValueError("all samples must have the same choice count for complete paired coverage")
        choice_count = len(choices)
        target = _target_to_index(sample.target, choices, letters)
        if target is None:
            raise ValueError(f"sample {index}: target must resolve to exactly one choice")
        group = str(sample.id) if sample.id is not None else str(index)
        if group in seen:
            raise ValueError(f"duplicate source sample id: {group!r}")
        seen.add(group)
        item = MCQItem(sample.input, choices, target)
        expanded.extend(cyclic_variant_samples(item, group, letters, sample.metadata))
    if not expanded:
        raise ValueError("no multiple-choice samples")
    return Task(dataset=MemoryDataset(expanded), solver=generate(),
                scorer=invariance_scorer(), name=name,
                metadata={"invariance_task_mode": "new generate-only plain-MCQ audit"})


def invariance_task(base_task: Any, letters: str = "ABCD", name: Optional[str] = None,
                    *, rebuild: bool = False) -> Any:
    """Compatibility entry point. Require explicit consent to rebuild the Task."""
    if rebuild is not True:
        raise ValueError("invariance_task does not preserve Task semantics; use cyclic_mcq_task(base_task.dataset) "
                         "or explicitly opt in with rebuild=True")
    return cyclic_mcq_task(base_task.dataset, letters,
                           name or (getattr(base_task, "name", None) or "task") + "-invariance")


def _rows_from_scores(scores):
    rows, expected = [], None
    for score in scores:
        sample_meta = getattr(score, "sample_metadata", None) or {}
        scored = getattr(score, "score", None)
        score_meta = getattr(scored, "metadata", None) or {}
        for key in (_GROUP_KEY, _COND_KEY, _EXPECTED_KEY):
            if key in sample_meta and key in score_meta and sample_meta[key] != score_meta[key]:
                raise ValueError(f"conflicting {key} metadata")
        metadata = {**sample_meta, **score_meta}
        correct = metadata.get("correct")
        if "correct" not in metadata:
            value = getattr(scored, "value", None)
            if value not in ("C", "I"):
                raise ValueError("correct metadata or an exact C/I score is required")
            correct = value == "C"
        declared = metadata.get(_EXPECTED_KEY)
        if declared is not None:
            if (not isinstance(declared, list) or len(declared) < 2
                    or any(not isinstance(c, str) or not c.strip() for c in declared)
                    or len(set(declared)) != len(declared)):
                raise ValueError("invalid expected condition metadata")
            if expected is not None and set(declared) != expected:
                raise ValueError("inconsistent expected conditions")
            expected = set(declared)
        rows.append({"item_id": metadata.get(_GROUP_KEY), "condition": metadata.get(_COND_KEY),
                     "correct": correct})
    results = results_from_rows(rows)
    if expected is not None and set(results) != expected:
        raise ValueError("missing expected conditions in Inspect scores")
    return results


def invariance_drift():
    from inspect_ai.scorer import metric
    @metric(name="invariance_drift", scores="unreduced")
    def _drift():
        def compute(scores: List[Any]) -> float:
            return point_metrics(_rows_from_scores(scores))[1]
        return compute
    return _drift()


def invariance_correctness_flip_rate():
    from inspect_ai.scorer import metric
    @metric(name="invariance_correctness_flip_rate", scores="unreduced")
    def _correctness_flip():
        def compute(scores: List[Any]) -> float:
            return point_metrics(_rows_from_scores(scores))[2]
        return compute
    return _correctness_flip()


def invariance_flip_rate():
    """Deprecated name; this metric counts correctness changes, not answer changes."""
    warnings.warn("use invariance_correctness_flip_rate; this does not measure answer flips",
                  DeprecationWarning, stacklevel=2)
    return invariance_correctness_flip_rate()


def invariance_scorer():
    from inspect_ai.scorer import Score, scorer, accuracy
    @scorer(metrics=[accuracy(), invariance_drift(), invariance_correctness_flip_rate()], name="invariance_scorer")
    def _factory():
        async def score(state, target):
            completion = state.output.completion.strip().upper()
            metadata = state.metadata or {}
            letters = metadata.get("invariance_letters", "ABCD")
            valid = len(completion) == 1 and completion in letters
            predicted = completion if valid else ""
            return Score(value="C" if valid and predicted == target.text.strip().upper() else "I",
                         answer=predicted,
                         metadata={key: metadata[key] for key in (_GROUP_KEY, _COND_KEY, _EXPECTED_KEY)
                                   if key in metadata} |
                                  {"correct": bool(valid and predicted == target.text.strip().upper()),
                                   "valid_answer": valid})
        return score
    return _factory()


def invariance_report_from_scores(scored: List[Dict[str, Any]], **kwargs) -> InvarianceReport:
    """Analyze explicit item_id/condition/correct rows, never positional grouping."""
    return build_report(results_from_rows(scored), **kwargs)
