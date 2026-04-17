from __future__ import annotations

import importlib
import json


def test_mail_config_reads_from_runtime_json(
    isolated_runtime,
    tmp_path,
    monkeypatch,
) -> None:
    runtime_secrets = importlib.import_module("core.runtime.secrets")

    settings_file = tmp_path / "runtime.json"
    settings_file.write_text(
        json.dumps(
            {
                "mail_smtp_host": "test.example.com",
                "mail_smtp_port": 587,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime_secrets, "SETTINGS_FILE", settings_file)

    assert runtime_secrets.read_runtime_key("mail_smtp_host") == "test.example.com"
    assert runtime_secrets.read_runtime_key("mail_smtp_port", as_int=True) == 587


def test_mail_config_missing_key_raises(
    isolated_runtime,
    tmp_path,
    monkeypatch,
) -> None:
    runtime_secrets = importlib.import_module("core.runtime.secrets")

    settings_file = tmp_path / "runtime.json"
    settings_file.write_text(
        json.dumps({"mail_user": "jarvis@example.com"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime_secrets, "SETTINGS_FILE", settings_file)

    try:
        runtime_secrets.read_runtime_key("mail_password")
        assert False, "Expected RuntimeError for missing mail_password"
    except RuntimeError as exc:
        assert "mail_password" in str(exc)


def test_env_override_wins(
    isolated_runtime,
    tmp_path,
    monkeypatch,
) -> None:
    runtime_secrets = importlib.import_module("core.runtime.secrets")

    settings_file = tmp_path / "runtime.json"
    settings_file.write_text(
        json.dumps({"mail_user": "filevalue@example.com"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime_secrets, "SETTINGS_FILE", settings_file)
    monkeypatch.setenv("JARVIS_MAIL_USER", "envvalue@example.com")

    assert (
        runtime_secrets.read_runtime_key(
            "mail_user",
            env_override="JARVIS_MAIL_USER",
        )
        == "envvalue@example.com"
    )
