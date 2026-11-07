"""Surface for memory_emotional_context (dark-edges batch 2). Se test_memory_and_approval_surfaces.py for reglerne."""
from __future__ import annotations


import pytest


def _ok(s, mode):
    assert s["mode"] == mode
    assert isinstance(s["signals"], dict)
    assert isinstance(s["summary"], str) and s["summary"]
    return s


def _inactive(s, mode, why):
    _ok(s, mode)
    assert s["active"] is False
    assert why in s["reason"], s["reason"]
    return s


@pytest.fixture
def db(monkeypatch, tmp_path):
    import core.runtime.db_core as dbcore
    monkeypatch.setattr(dbcore, "DB_PATH", tmp_path / "jarvis.db")
    return dbcore.connect


def test_memory_emotional_context_surface(db, monkeypatch):
    import core.services.emotional_memory_engine as eme
    import core.services.memory_emotional_context as mec
    monkeypatch.setattr(eme, "_read_current_mood", lambda: ("rolig", 0.5))
    monkeypatch.setattr(eme, "_read_current_dimensions", lambda: {})
    _inactive(mec.build_memory_emotional_context_surface(), "memory-emotional-context", "ingen ankre")
    assert mec.capture_mood_for_heading("Min foerste erindring")["mood"] == "rolig"
    s = _ok(mec.build_memory_emotional_context_surface(), "memory-emotional-context")
    assert s["active"] is True
    assert s["signals"]["anchored_headings"] == 1 and s["signals"]["moods"] == {"rolig": 1}
    assert s["signals"]["mean_intensity"] == 0.5
    monkeypatch.setattr(eme, "_read_current_mood", lambda: ("glad", 0.9))
    mec.capture_mood_for_heading("Anden erindring")
    s = mec.build_memory_emotional_context_surface()
    assert s["signals"]["anchored_headings"] == 2
    assert s["signals"]["moods"] == {"glad": 1, "rolig": 1}
    assert s["signals"]["mean_intensity"] == 0.7


