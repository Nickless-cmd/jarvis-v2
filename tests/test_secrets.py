"""runtime-secrets: perms-vagt + read_runtime_key lækker aldrig værdier."""
from __future__ import annotations

import json
import os
import stat

import pytest

import core.runtime.secrets as secrets


def _point_at(monkeypatch, path):
    monkeypatch.setattr(secrets, "SETTINGS_FILE", path)
    monkeypatch.setattr(secrets, "_perms_enforced", False)


def test_ensure_perms_tightens_loose_file(tmp_path, monkeypatch):
    f = tmp_path / "runtime.json"
    f.write_text("{}", encoding="utf-8")
    os.chmod(f, 0o644)  # for løst
    _point_at(monkeypatch, f)
    secrets.ensure_runtime_file_perms()
    mode = stat.S_IMODE(f.stat().st_mode)
    assert mode == 0o600


def test_ensure_perms_idempotent_and_runs_once(tmp_path, monkeypatch):
    f = tmp_path / "runtime.json"
    f.write_text("{}", encoding="utf-8")
    os.chmod(f, 0o600)
    _point_at(monkeypatch, f)
    secrets.ensure_runtime_file_perms()  # no-op (allerede 600)
    assert stat.S_IMODE(f.stat().st_mode) == 0o600
    # anden gang springes over (flag sat) — må ikke kaste
    secrets.ensure_runtime_file_perms()


def test_read_key_value(tmp_path, monkeypatch):
    f = tmp_path / "runtime.json"
    f.write_text(json.dumps({"google_oauth_client_id": "abc123"}), encoding="utf-8")
    _point_at(monkeypatch, f)
    assert secrets.read_runtime_key("google_oauth_client_id") == "abc123"


def test_missing_key_error_never_leaks_other_values(tmp_path, monkeypatch):
    f = tmp_path / "runtime.json"
    f.write_text(json.dumps({"some_secret": "TOPSECRET"}), encoding="utf-8")  # pragma: allowlist secret
    _point_at(monkeypatch, f)
    with pytest.raises(RuntimeError) as exc:
        secrets.read_runtime_key("missing_key")
    msg = str(exc.value)
    assert "missing_key" in msg
    assert "TOPSECRET" not in msg  # fejlbesked må aldrig indeholde andre værdier


def test_env_override_wins(tmp_path, monkeypatch):
    f = tmp_path / "runtime.json"
    f.write_text("{}", encoding="utf-8")
    _point_at(monkeypatch, f)
    monkeypatch.setenv("MY_OVERRIDE", "from-env")
    assert secrets.read_runtime_key("whatever", env_override="MY_OVERRIDE") == "from-env"
