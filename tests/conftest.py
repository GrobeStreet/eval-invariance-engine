"""Keep optional Inspect runtime state inside pytest's temporary directory."""
import importlib.util
import pytest


@pytest.fixture(autouse=True)
def isolate_inspect_state(tmp_path, monkeypatch):
    if importlib.util.find_spec("inspect_ai"):
        from inspect_ai._util import appdirs
        monkeypatch.setattr(appdirs, "user_data_path", lambda *a, **k: tmp_path / "inspect-data")
        monkeypatch.setattr(appdirs, "user_cache_path", lambda *a, **k: tmp_path / "inspect-cache")
