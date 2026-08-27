from eval_invariance_engine.perturbations import (
    MCQItem,
    cyclic_reorder,
    all_cyclic_variants,
    whitespace_variant,
)
import pytest


def test_cyclic_reorder_tracks_answer():
    item = MCQItem("q", ["A", "B", "C", "D"], 0)
    r = cyclic_reorder(item, 1)
    assert r.options == ["D", "A", "B", "C"]
    assert r.answer_index == 1
    # the correct real answer text is preserved
    assert r.answer_text == item.answer_text == "A"


def test_cyclic_reorder_shift_zero_identity():
    item = MCQItem("q", ["A", "B", "C", "D"], 2)
    r = cyclic_reorder(item, 0)
    assert r.options == item.options and r.answer_index == item.answer_index


def test_all_variants_preserve_answer_text():
    item = MCQItem("q", ["w", "x", "y", "z"], 3)
    variants = all_cyclic_variants(item)
    assert len(variants) == 4
    for v in variants:
        assert v.answer_text == "z"
    # every ordering is distinct
    assert len({tuple(v.options) for v in variants}) == 4


def test_whitespace_variants_preserve_content():
    text = "the quick brown fox"
    for style in ("identity", "collapse", "pad"):
        out = whitespace_variant(text, style)
        assert out.split() == text.split()


def test_bad_answer_index_rejected():
    with pytest.raises(ValueError):
        MCQItem("q", ["A", "B"], 5)
