import json
import math
import pytest
from eval_invariance_engine.report import build_report
from eval_invariance_engine.validation import results_from_rows


def test_report_exact_numbers():
    r = build_report({"a": [True, True, True, True], "b": [True, True, False, False]})
    assert r.per_condition_accuracy == {"a": 1.0, "b": 0.5}
    assert r.max_drift == r.correctness_flip_rate == r.flip_rate == 0.5
    assert r.verdict == "drift_above_threshold"


def test_equal_accuracy_does_not_imply_stable_decisions():
    r = build_report({"a": [True, False], "b": [False, True]})
    assert r.max_drift == 0
    assert r.correctness_flip_rate == 1
    assert r.verdict == "drift_not_above_threshold"
    assert "not evidence of equivalence" in r.summary()
    assert "correctness_flip_rate=1.000" in r.summary()


def test_identical_observations():
    r = build_report({"a": [True, False], "b": [True, False]})
    assert r.max_drift == r.correctness_flip_rate == 0


@pytest.mark.parametrize("data", [
    {}, {"a": [True]}, {"a": [], "b": []},
    {"a": [True, False], "b": [True]},
    {"a": ["false"], "b": [True]}, {"a": [1], "b": [True]},
    {"a": [None], "b": [True]}, {"a": "false", "b": [True]},
    {"": [True], "b": [False]}, {1: [True], "b": [False]}, None,
])
def test_invalid_results_rejected(data):
    with pytest.raises(ValueError):
        build_report(data)


@pytest.mark.parametrize("threshold", [math.nan, math.inf, -1, 1.1, True, "0.03"])
def test_invalid_threshold_rejected(threshold):
    with pytest.raises(ValueError, match="threshold"):
        build_report({"a": [True], "b": [False]}, fragile_threshold=threshold)


@pytest.mark.parametrize("draws", [0, -1, 199, 200.0, True])
def test_invalid_bootstrap_rejected(draws):
    with pytest.raises(ValueError, match="n_boot"):
        build_report({"a": [True], "b": [False]}, n_boot=draws)


@pytest.mark.parametrize("seed", [None, True, 0.5, "0"])
def test_invalid_seed_rejected(seed):
    with pytest.raises(ValueError, match="seed"):
        build_report({"a": [True], "b": [False]}, seed=seed)


def test_paired_bootstrap_preserves_zero_drift_for_identical_item_vectors():
    data = {"a": [True, False, False, True], "b": [True, False, False, True]}
    r = build_report(data, seed=7)
    assert r.drift_ci95 == (0, 0)
    assert r.to_dict() == build_report(data, seed=7).to_dict()
    assert r.bootstrap_samples == 2000
    assert r.bootstrap_seed == 7
    assert json.loads(json.dumps(r.to_dict()))["n_items"] == 4


def test_explicit_item_identity_survives_shuffled_rows():
    rows = [
        {"item_id": "q1", "condition": "a", "correct": True},
        {"item_id": "q2", "condition": "a", "correct": False},
        {"item_id": "q2", "condition": "b", "correct": False},
        {"item_id": "q1", "condition": "b", "correct": True},
    ]
    assert build_report(rows).correctness_flip_rate == 0
    assert build_report(rows).to_dict() == build_report(rows[::-1]).to_dict()


@pytest.mark.parametrize("rows", [
    [],
    [{"condition": "a", "correct": True}],
    [{"item_id": 1, "condition": "a", "correct": True}],
    [{"item_id": "q", "condition": "a", "correct": "false"}],
    [{"item_id": "q", "condition": "a", "correct": True}] * 2,
    [{"item_id": "q", "condition": "a", "correct": True},
     {"item_id": "other", "condition": "b", "correct": True}],
    [None], "wrong",
])
def test_invalid_pairing_rejected(rows):
    with pytest.raises(ValueError):
        results_from_rows(rows)
