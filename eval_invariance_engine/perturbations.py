"""Deterministic, semantics-preserving perturbations.

The guarantee every perturbation here must uphold: it changes only *non-semantic*
surface form. The correct answer is still the same real-world answer; only its
label position or the surrounding whitespace changes. If a model's score moves
under these, the movement is the artifact — not the reasoning.
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
        if not self.options:
            raise ValueError("options must be non-empty")
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
    """Semantics-preserving whitespace restyling.

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
