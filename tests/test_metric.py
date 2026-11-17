import pytest
pytest.importorskip("inspect_ai")
from inspect_ai.scorer import Score, SampleScore
from eval_invariance_engine.inspect_adapter import (
    invariance_drift, invariance_correctness_flip_rate, invariance_report_from_scores,
)


def score(cond, correct, group="q1", **extra):
    return SampleScore(score=Score(value="C" if correct else "I",
                                   metadata={"correct": correct, **extra}),
                       sample_id=f"{group}:{cond}",
                       sample_metadata={"invariance_group": group, "invariance_condition": cond})


def test_metrics_match_id_paired_report_despite_shuffled_scores():
    scores = [score("a", True, "q1"), score("a", False, "q2"),
              score("b", False, "q2"), score("b", True, "q1")]
    assert invariance_drift()(scores) == 0
    assert invariance_correctness_flip_rate()(scores) == 0
    scores[-1] = score("b", False, "q1")
    assert invariance_drift()(scores) == 0.5
    assert invariance_correctness_flip_rate()(scores) == 0.5


@pytest.mark.parametrize("scores", [
    [], [score("a", True)],
    [score("a", True), score("a", True), score("b", False)],
    [score("a", True, "q1"), score("b", False, "q2")],
    [score("a", "false"), score("b", True)],
    [score("a", True, invariance_expected_conditions=["a", "b", "c"]), score("b", False)],
])
def test_native_metrics_reject_incomplete_or_ambiguous_data(scores):
    for metric in [invariance_drift(), invariance_correctness_flip_rate()]:
        with pytest.raises(ValueError):
            metric(scores)


def test_post_eval_rows_require_identity_and_preserve_alignment():
    with pytest.raises(ValueError, match="item_id"):
        invariance_report_from_scores([{"condition": "a", "correct": True}])
    rows = [{"item_id": "q", "condition": "a", "correct": True},
            {"item_id": "q", "condition": "b", "correct": False}]
    assert invariance_report_from_scores(rows).correctness_flip_rate == 1
