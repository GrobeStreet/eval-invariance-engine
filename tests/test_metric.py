"""Tests for the native Inspect metrics. Requires inspect_ai (dev extra)."""
from eval_invariance_engine.inspect_adapter import invariance_drift, invariance_flip_rate


def _sample_score(cond, correct, group="0"):
    from inspect_ai.scorer import Score, SampleScore

    return SampleScore(
        score=Score(
            value="C" if correct else "I",
            metadata={"invariance_condition": cond, "correct": correct},
        ),
        sample_id=f"{group}:{cond}",
        sample_metadata={"invariance_group": group, "invariance_condition": cond},
    )


def test_drift_metric():
    m = invariance_drift()
    scores = [
        _sample_score("shift0", True),
        _sample_score("shift0", True),
        _sample_score("shift1", False),
        _sample_score("shift1", False),
    ]
    assert m(scores) == 1.0  # shift0 accuracy 1.0, shift1 accuracy 0.0


def test_drift_metric_single_condition_is_zero():
    m = invariance_drift()
    assert m([_sample_score("shift0", True), _sample_score("shift0", False)]) == 0.0


def test_flip_rate_metric():
    m = invariance_flip_rate()
    scores = [
        _sample_score("shift0", True, group="A"),
        _sample_score("shift1", False, group="A"),   # group A flips
        _sample_score("shift0", True, group="B"),
        _sample_score("shift1", True, group="B"),     # group B stable
    ]
    assert m(scores) == 0.5
