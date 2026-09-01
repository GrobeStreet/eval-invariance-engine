"""Tests for the invariance_task() one-call wrapper. Requires inspect_ai (Python >=3.10)."""
import pytest

pytest.importorskip("inspect_ai")

from inspect_ai import Task
from inspect_ai.dataset import MemoryDataset, Sample

from eval_invariance_engine.inspect_adapter import invariance_task


def _base_task():
    return Task(
        dataset=MemoryDataset([
            Sample(input="2+2=?", choices=["4", "5", "6", "7"], target="A"),
            Sample(input="Capital of France?", choices=["Paris", "Rome", "Bonn", "Madrid"], target="A"),
        ])
    )


def test_expands_each_mcq_into_cyclic_variants():
    t = invariance_task(_base_task())
    samples = list(t.dataset)
    assert len(samples) == 8  # 2 items x 4 orderings
    assert all("invariance_group" in (s.metadata or {}) for s in samples)
    assert all("invariance_condition" in (s.metadata or {}) for s in samples)
    groups = {}
    for s in samples:
        groups.setdefault(s.metadata["invariance_group"], set()).add(s.metadata["invariance_condition"])
    assert len(groups) == 2
    assert all(len(conds) == 4 for conds in groups.values())


def test_correct_answer_preserved_across_orderings():
    t = invariance_task(_base_task())
    expected = {"0": "4", "1": "Paris"}  # group id = source index; target index 0
    for s in list(t.dataset):
        letter = s.target
        line = next(l for l in s.input.splitlines() if l.strip().startswith(letter + "."))
        option = line.split(".", 1)[1].strip()
        assert option == expected[s.metadata["invariance_group"]]


def test_task_has_scorer():
    t = invariance_task(_base_task())
    assert t.scorer is not None


def test_non_mcq_samples_raise_clear_error():
    task = Task(dataset=MemoryDataset([Sample(input="free text, no choices", target="whatever")]))
    with pytest.raises(ValueError, match="no multiple-choice samples"):
        invariance_task(task)
