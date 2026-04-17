from __future__ import annotations

import json


def test_load_save_preserves_unknown_keys(
    isolated_runtime,
    tmp_path,
    monkeypatch,
) -> None:
    """Round-trip through load -> save must preserve arbitrary top-level keys."""
    runtime_settings = isolated_runtime.settings

    settings_file = tmp_path / "runtime.json"
    settings_file.write_text(
        json.dumps(
            {
                "port": 80,
                "visible_model_name": "old-model",
                "tavily_api_key": "tvly-xxx",
                "home_assistant_url": "http://ha.local:8123",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime_settings, "SETTINGS_FILE", settings_file)

    runtime_settings.update_visible_execution_settings(
        visible_model_name="new-model",
    )

    saved = json.loads(settings_file.read_text(encoding="utf-8"))
    assert saved["visible_model_name"] == "new-model"
    assert saved["tavily_api_key"] == "tvly-xxx"
    assert saved["home_assistant_url"] == "http://ha.local:8123"
    assert saved["port"] == 80
