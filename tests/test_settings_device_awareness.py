import json

import core.runtime.settings as settings_mod
from core.runtime.settings import RuntimeSettings, load_settings


def test_device_awareness_defaults_true():
    assert RuntimeSettings().device_awareness_enabled is True


def test_device_awareness_parsed_from_file(tmp_path, monkeypatch):
    f = tmp_path / "runtime.json"
    f.write_text(json.dumps({"device_awareness_enabled": False}), encoding="utf-8")
    monkeypatch.setattr(settings_mod, "SETTINGS_FILE", f)
    assert load_settings().device_awareness_enabled is False


def test_device_awareness_roundtrips_in_to_dict():
    s = RuntimeSettings()
    assert s.to_dict()["device_awareness_enabled"] is True
