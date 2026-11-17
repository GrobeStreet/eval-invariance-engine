import json
import pytest
from eval_invariance_engine.cli import main


def write_results(tmp_path, data):
    path = tmp_path / "results.json"
    path.write_text(json.dumps(data))
    return str(path)


def test_demo_and_legacy_gate_alias(capsys):
    assert main(["demo"]) == 0
    assert "DRIFT_ABOVE_THRESHOLD" in capsys.readouterr().out
    assert main(["demo", "--fail-on-drift"]) == 1
    assert main(["demo", "--fail-on-fragile"]) == 1


def test_mapping_requires_explicit_alignment(tmp_path, capsys):
    path = write_results(tmp_path, {"a": [True], "b": [False]})
    with pytest.raises(SystemExit) as e:
        main(["report", path])
    assert e.value.code == 2
    assert "--assume-aligned" in capsys.readouterr().err
    assert main(["report", path, "--assume-aligned", "--fail-on-drift"]) == 1


def test_row_order_and_json_report(tmp_path, capsys):
    path = write_results(tmp_path, [
        {"item_id": "q1", "condition": "a", "correct": True},
        {"item_id": "q2", "condition": "a", "correct": False},
        {"item_id": "q2", "condition": "b", "correct": False},
        {"item_id": "q1", "condition": "b", "correct": True},
    ])
    assert main(["report", path, "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["correctness_flip_rate"] == 0
    assert report["n_items"] == 2


@pytest.mark.parametrize("data", [
    {"a": ["false"], "b": [True]},
    {"a": [], "b": []},
    [{"condition": "a", "correct": True}],
])
def test_bad_data_exits_two(tmp_path, data):
    with pytest.raises(SystemExit) as error:
        main(["report", write_results(tmp_path, data), "--assume-aligned"])
    assert error.value.code == 2


def test_invalid_json_and_missing_file_are_actionable(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text("{")
    for filename in [str(path), str(tmp_path / "missing.json")]:
        with pytest.raises(SystemExit) as error:
            main(["report", filename])
        assert error.value.code == 2
    assert "Traceback" not in capsys.readouterr().err
