from eval_invariance_engine.report import build_report
import pytest


def test_fragile_case_exact_numbers():
    results = {
        "shift0": [True, True, True, True],
        "shift1": [True, True, False, False],
    }
    r = build_report(results, seed=0)
    assert r.per_condition_accuracy["shift0"] == 1.0
    assert r.per_condition_accuracy["shift1"] == 0.5
    assert r.max_drift == 0.5
    assert r.flip_rate == 0.5   # items 2 and 3 change correctness
    assert r.verdict == "fragile"


def test_invariant_case():
    results = {
        "a": [True, False, True, False],
        "b": [True, False, True, False],
    }
    r = build_report(results, seed=0)
    assert r.max_drift == 0.0
    assert r.flip_rate == 0.0
    assert r.verdict == "invariant"


def test_unequal_lengths_raise():
    with pytest.raises(ValueError):
        build_report({"a": [True, False], "b": [True]})


def test_bootstrap_is_deterministic():
    results = {"a": [True, True, False, True], "b": [False, True, False, True]}
    r1 = build_report(results, seed=7)
    r2 = build_report(results, seed=7)
    assert r1.drift_ci95 == r2.drift_ci95
    lo, hi = r1.drift_ci95
    assert lo <= hi
