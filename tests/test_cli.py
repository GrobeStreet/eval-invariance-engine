import json

from eval_invariance_engine.cli import main


def test_demo_runs(capsys):
    rc = main(["demo"])
    out = capsys.readouterr().out
    assert "FRAGILE" in out
    assert rc == 0


def test_demo_fail_on_fragile_exits_nonzero():
    assert main(["demo", "--fail-on-fragile"]) == 1


def test_report_from_mapping(tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"a": [True, True, True, True], "b": [True, True, False, False]}))
    rc = main(["report", str(p), "--assume-aligned"])
    out = capsys.readouterr().out
    assert "drift=0.500" in out
    assert rc == 0


def test_report_fail_on_fragile(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"a": [True, True, True, True], "b": [True, True, False, False]}))
    assert main(["report", str(p), "--assume-aligned", "--fail-on-fragile"]) == 1


def test_report_below_threshold_from_list(tmp_path, capsys):
    p = tmp_path / "r.json"
    rows = [
        {"item_id": "q0", "condition": "a", "correct": True},
        {"item_id": "q0", "condition": "b", "correct": True},
    ]
    p.write_text(json.dumps(rows))
    rc = main(["report", str(p)])
    assert "BELOW_THRESHOLD" in capsys.readouterr().out
    assert rc == 0
