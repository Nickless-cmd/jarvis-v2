from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def workspace_tmp(tmp_path, monkeypatch):
    import core.services.voice_anchor as va
    monkeypatch.setattr(va, "ensure_default_workspace", lambda: tmp_path)
    return tmp_path


def test_returns_empty_string_when_no_files(workspace_tmp):
    from core.services.voice_anchor import read_voice_anchor

    assert read_voice_anchor() == ""


def test_returns_static_only_when_no_recent(workspace_tmp):
    (workspace_tmp / "VOICE.md").write_text("tør, lavmælt, præcis", encoding="utf-8")
    from core.services.voice_anchor import read_voice_anchor

    out = read_voice_anchor()
    assert "tør, lavmælt, præcis" in out
    assert "VOICE.md" in out  # section header present


def test_concatenates_static_then_recent(workspace_tmp):
    (workspace_tmp / "VOICE.md").write_text("STATIC SEED", encoding="utf-8")
    (workspace_tmp / "VOICE_RECENT.md").write_text("RECENT EXEMPLARS", encoding="utf-8")
    from core.services.voice_anchor import read_voice_anchor

    out = read_voice_anchor()
    assert out.index("STATIC SEED") < out.index("RECENT EXEMPLARS")
