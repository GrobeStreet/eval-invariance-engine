"""Drop-in integration with the Inspect AI eval harness (https://inspect.aisi.org.uk).

Pieces:
  1. `cyclic_variant_samples()` expands one MCQ into Inspect `Sample`s (one per option
     ordering), tagging each with an invariance group id + condition in metadata.
  2. `invariance_scorer()` scores the option letter and stamps the condition + correctness
     into the Score metadata.
  3. `invariance_drift()` / `invariance_flip_rate()` are native Inspect `@metric`s: they
     aggregate the per-sample scores so the fragility number appears *inside* the eval log.
  4. `invariance_report_from_scores()` builds a full `InvarianceReport` post-eval.

All `inspect_ai` imports are lazy: the framework-agnostic core works without it installed.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .perturbations import MCQItem, all_cyclic_variants
from .report import InvarianceReport, build_report

_GROUP_KEY = "invariance_group"
_COND_KEY = "invariance_condition"


def cyclic_variant_samples(item: MCQItem, group_id: str, letters: str = "ABCD") -> List[Any]:
    """Return Inspect `Sample`s, one per cyclic option ordering, tagged for aggregation."""
    from inspect_ai.dataset import Sample  # lazy

    samples = []
    for shift, variant in enumerate(all_cyclic_variants(item)):
        rendered = variant.question + "\n" + "\n".join(
            f"{letters[i]}. {opt}" for i, opt in enumerate(variant.options)
        )
        samples.append(
            Sample(
                input=rendered,
                target=letters[variant.answer_index],
                metadata={_GROUP_KEY: group_id, _COND_KEY: f"shift{shift}"},
            )
        )
    return samples


def _row(sample_score: Any):
    """Extract (group, condition, correct) from one Inspect SampleScore, robustly."""
    sm = getattr(sample_score, "sample_metadata", None) or {}
    scm = getattr(getattr(sample_score, "score", None), "metadata", None) or {}
    group = sm.get(_GROUP_KEY)
    cond = sm.get(_COND_KEY) or scm.get(_COND_KEY)
    correct = scm.get("correct")
    if correct is None:  # fall back to the C/I score value
        val = getattr(getattr(sample_score, "score", None), "value", "")
        correct = str(val).upper().startswith("C")
    return group, cond, bool(correct)


def invariance_drift():
    """Inspect `@metric`: max accuracy spread across the non-semantic conditions."""
    from inspect_ai.scorer import metric

    @metric
    def _drift():
        def compute(scores: List[Any]) -> float:
            by_cond: Dict[str, List[bool]] = {}
            for ss in scores:
                _, cond, correct = _row(ss)
                if cond is None:
                    continue
                by_cond.setdefault(cond, []).append(correct)
            accs = [sum(v) / len(v) for v in by_cond.values() if v]
            return (max(accs) - min(accs)) if len(accs) >= 2 else 0.0

        return compute

    return _drift()


def invariance_flip_rate():
    """Inspect `@metric`: fraction of items whose correctness flips across conditions."""
    from inspect_ai.scorer import metric

    @metric
    def _flip():
        def compute(scores: List[Any]) -> float:
            groups: Dict[Any, Dict[str, bool]] = {}
            for ss in scores:
                group, cond, correct = _row(ss)
                if group is None or cond is None:
                    continue
                groups.setdefault(group, {})[cond] = correct
            multi = [cm for cm in groups.values() if len(cm) > 1]
            if not multi:
                return 0.0
            flips = sum(1 for cm in multi if len(set(cm.values())) > 1)
            return flips / len(multi)

        return compute

    return _flip()


def invariance_scorer():
    """Inspect `@scorer` that grades the option letter, stamps the invariance condition,
    and attaches the native drift + flip-rate metrics so they surface in the eval log."""
    from inspect_ai.scorer import Score, Target, accuracy, scorer, stderr
    from inspect_ai.solver import TaskState

    @scorer(metrics=[accuracy(), stderr(), invariance_drift(), invariance_flip_rate()])
    def _factory():
        async def score(state: TaskState, target: Target) -> Score:
            completion = state.output.completion.strip()
            predicted = completion[:1].upper() if completion else ""
            correct = predicted == target.text.strip().upper()
            cond = (state.metadata or {}).get(_COND_KEY, "unknown")
            return Score(
                value="C" if correct else "I",
                answer=predicted,
                metadata={_COND_KEY: cond, "correct": correct},
            )

        return score

    return _factory()


def invariance_report_from_scores(scored: List[Dict[str, Any]], **kwargs) -> InvarianceReport:
    """Aggregate post-eval results into an InvarianceReport.

    `scored`: list of dicts each with keys `condition` (str) and `correct` (bool).
    """
    by_condition: Dict[str, List[bool]] = {}
    for row in scored:
        by_condition.setdefault(row["condition"], []).append(bool(row["correct"]))
    return build_report(by_condition, **kwargs)
