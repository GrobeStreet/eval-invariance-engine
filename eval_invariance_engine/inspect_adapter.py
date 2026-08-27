"""Drop-in integration with the Inspect AI eval harness (https://inspect.aisi.org.uk).

Two moving parts:
  1. `cyclic_variant_samples()` expands one MCQ Inspect `Sample` into its option-order
     variants, tagging each with an invariance group id + condition in metadata.
  2. `invariance_report_from_scores()` reads back the per-sample scores (post-eval) and
     produces an `InvarianceReport`, so you never depend on a bespoke metric internal.

Import is lazy: the framework-agnostic core works without `inspect_ai` installed.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .perturbations import MCQItem, all_cyclic_variants
from .report import InvarianceReport, build_report

_GROUP_KEY = "invariance_group"
_COND_KEY = "invariance_condition"


def cyclic_variant_samples(item: MCQItem, group_id: str, letters: str = "ABCD") -> List[Any]:
    """Return Inspect `Sample`s, one per cyclic option ordering, tagged for aggregation."""
    from inspect_ai.dataset import Sample  # lazy: only needed when integrating

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


def invariance_report_from_scores(scored: List[Dict[str, Any]], **kwargs) -> InvarianceReport:
    """Aggregate post-eval results into an InvarianceReport.

    `scored`: list of dicts each with keys `condition` (str) and `correct` (bool).
    """
    by_condition: Dict[str, List[bool]] = {}
    for row in scored:
        by_condition.setdefault(row["condition"], []).append(bool(row["correct"]))
    return build_report(by_condition, **kwargs)


def invariance_scorer():
    """A minimal Inspect `@scorer` that records the sample's invariance condition.

    Scores exact-match on the option letter and stamps the condition into the Score
    metadata, so `invariance_report_from_scores` can aggregate the eval log afterward.
    """
    from inspect_ai.scorer import Score, Target, accuracy, scorer, stderr
    from inspect_ai.solver import TaskState

    @scorer(metrics=[accuracy(), stderr()])
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
