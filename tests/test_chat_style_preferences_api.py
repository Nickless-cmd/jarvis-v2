"""The existing /api/preferences surface also owns conversational style."""
from __future__ import annotations

from apps.api.jarvis_api.routes import jarvisx_sessions as routes


def _store(monkeypatch, tmp_path):
    values: dict[str, object] = {}
    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.identity.workspace_context.current_workspace_name", lambda: "michelle")
    monkeypatch.setattr(
        "core.runtime.db_core.get_runtime_state_value",
        lambda key, default=None: values.get(key, default),
    )
    monkeypatch.setattr(
        "core.runtime.db_core.set_runtime_state_value",
        lambda key, value: values.__setitem__(key, value),
    )
    return values


def test_preferences_get_includes_default_chat_style(monkeypatch, tmp_path) -> None:
    _store(monkeypatch, tmp_path)
    result = routes.preferences_get()
    assert result["output_style"] == "balanced"
    assert result["chat_style"]["tone"] == "adaptive"
    assert result["chat_style"]["profanity"] == "adaptive"


def test_preferences_patch_merges_chat_style_per_workspace(monkeypatch, tmp_path) -> None:
    values = _store(monkeypatch, tmp_path)
    result = routes.preferences_set(routes.PreferencesUpdate(
        chat_style={"tone": "playful", "profanity": "comfortable"},
    ))
    assert result["preferences"]["chat_style"]["tone"] == "playful"
    assert values["chat_style:michelle"] == {
        "tone": "playful", "emoji": "adaptive", "profanity": "comfortable",
        "visuals": "adaptive", "questions": "adaptive",
    }
