from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest


@pytest.fixture()
def workspace_tmp(tmp_path, monkeypatch):
    import core.services.voice_curator as vc
    monkeypatch.setattr(vc, "ensure_default_workspace", lambda: tmp_path)
    return tmp_path


def test_writes_voice_recent_file(workspace_tmp, monkeypatch):
    from core.services import voice_curator

    monkeypatch.setattr(
        voice_curator, "_fetch_chat_exemplars", lambda *, limit: [
            {"source": "chat", "date": "2026-05-08", "text": "Jeg tror ikke det er færdigt endnu."},
            {"source": "chat", "date": "2026-05-07", "text": "Det stak mig lidt i siden at høre."},
        ]
    )
    monkeypatch.setattr(voice_curator, "_fetch_chronicle_exemplars", lambda *, limit: [])
    monkeypatch.setattr(voice_curator, "_fetch_journal_exemplars", lambda *, limit: [])

    changed = voice_curator.refresh_voice_recent()
    assert changed is True
    out = (workspace_tmp / "VOICE_RECENT.md").read_text(encoding="utf-8")
    assert "Jeg tror ikke det er færdigt endnu." in out
    assert "{source: chat" in out


def test_idempotent_no_rewrite_when_unchanged(workspace_tmp, monkeypatch):
    from core.services import voice_curator

    fake = [{"source": "chat", "date": "2026-05-08", "text": "samme tekst med nok ord til at passere min-grænsen overhovedet"}]
    monkeypatch.setattr(voice_curator, "_fetch_chat_exemplars", lambda *, limit: fake)
    monkeypatch.setattr(voice_curator, "_fetch_chronicle_exemplars", lambda *, limit: [])
    monkeypatch.setattr(voice_curator, "_fetch_journal_exemplars", lambda *, limit: [])

    assert voice_curator.refresh_voice_recent() is True
    assert voice_curator.refresh_voice_recent() is False  # unchanged second time


def test_diversity_caps_per_source(workspace_tmp, monkeypatch):
    from core.services import voice_curator

    many_chat = [
        {"source": "chat", "date": "2026-05-08", "text": f"chat exemplar nummer {i} med nok ord til at passere min-grænsen overhovedet"}
        for i in range(10)
    ]
    monkeypatch.setattr(voice_curator, "_fetch_chat_exemplars", lambda *, limit: many_chat)
    monkeypatch.setattr(voice_curator, "_fetch_chronicle_exemplars", lambda *, limit: [
        {"source": "chronicle", "date": "2026-05-05", "text": "chronicle exemplar med nok ord til passere"}
    ])
    monkeypatch.setattr(voice_curator, "_fetch_journal_exemplars", lambda *, limit: [
        {"source": "journal", "date": "2026-05-01", "text": "journal exemplar med nok ord til at passere"}
    ])

    voice_curator.refresh_voice_recent()
    out = (workspace_tmp / "VOICE_RECENT.md").read_text(encoding="utf-8")
    # Diversity rule: max 2 from any single source
    assert out.count("{source: chat") <= 2


def test_excludes_inner_voice(monkeypatch, workspace_tmp):
    """inner_voice is private thought — explicitly never included."""
    from core.services import voice_curator

    # The module must not expose a function that pulls inner_voice.
    assert not hasattr(voice_curator, "_fetch_inner_voice_exemplars")
