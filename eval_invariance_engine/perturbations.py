"""Deterministic transformations intended to preserve the required answer.

Verify suitability per task: whitespace or option references may be semantic.
Sensitivity alone does not identify its causal mechanism.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class MCQItem:
    """A multiple-choice item with a known correct option index."""
    question: str
    options: List[str]
    answer_index: int

    def __post_init__(self) -> None:
        if not isinstance(self.question, str) or not self.question.strip():
            raise ValueError("question must be a non-empty string")
        if (not isinstance(self.options, (list, tuple)) or len(self.options) < 2
                or any(not isinstance(v, str) or not v.strip() for v in self.options)):
            raise ValueError("options must contain at least two non-empty strings")
        if type(self.answer_index) is not int:
            raise ValueError("answer_index must be an integer")
        if not (0 <= self.answer_index < len(self.options)):
            raise ValueError("answer_index out of range")

    @property
    def answer_text(self) -> str:
        return self.options[self.answer_index]


def cyclic_reorder(item: MCQItem, shift: int) -> MCQItem:
    """Rotate the option list right by `shift`, tracking where the answer lands.

    This is the option-order robustness perturbation: the set of answers is
    identical, only their A/B/C/D positions rotate. `answer_text` is invariant
    by construction (see tests).
    """
    n = len(item.options)
    s = shift % n
    if s == 0:
        return MCQItem(item.question, list(item.options), item.answer_index)
    new_options = item.options[-s:] + item.options[:-s]
    new_answer = (item.answer_index + s) % n
    return MCQItem(item.question, new_options, new_answer)


def all_cyclic_variants(item: MCQItem) -> List[MCQItem]:
    """Every cyclic option ordering (one per shift). Fixed, seed-free, exhaustive."""
    return [cyclic_reorder(item, s) for s in range(len(item.options))]


def whitespace_variant(text: str, style: str) -> str:
    """Whitespace restyling; callers must check whether spacing is semantic.

    styles: 'identity' (unchanged), 'collapse' (single-spaced),
    'pad' (double-spaced with trailing pad). Word content is always preserved.
    """
    words = text.split()
    if style == "identity":
        return text
    if style == "collapse":
        return " ".join(words)
    if style == "pad":
        return "  ".join(words) + "  "
    raise ValueError(f"unknown style: {style!r}")
