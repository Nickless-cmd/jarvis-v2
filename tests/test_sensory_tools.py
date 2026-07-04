"""Tests for core.tools.sensory_tools — sensory memory record/recall."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """Isolate sensory archive behind HOME-relative DB_PATH."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))

    import importlib
    for mod_name in [
        "core.runtime.config",
        "core.runtime.db_core",
        "core.runtime.db",
        "core.runtime.bootstrap",
        "core.services.memory_write_queue",
        "core.services.sensory_archive",
    ]:
        importlib.reload(__import__(mod_name, fromlist=[""]))


class TestExecRecordSensoryMemory:
    def test_record_sensory_memory_valid(self):
        from core.tools.sensory_tools import _exec_record_sensory_memory

        result = _exec_record_sensory_memory({
            "modality": "visual",
            "content": "en stille morgen med kaffe på bordet",
            "mood_tone": "roligt",
        })
        assert result["status"] == "ok"

    def test_record_sensory_memory_empty_content(self):
        from core.tools.sensory_tools import _exec_record_sensory_memory

        result = _exec_record_sensory_memory({
            "modality": "audio",
            "content": "   ",
        })
        assert result["status"] == "error"
        assert "error" in result

    def test_record_invalid_modality(self):
        from core.tools.sensory_tools import _exec_record_sensory_memory

        result = _exec_record_sensory_memory({
            "modality": "smell",
            "content": "duft af kaffe",
        })
        assert result["status"] == "error"

    def test_record_and_recall_roundtrip(self):
        from core.tools.sensory_tools import (
            _exec_record_sensory_memory,
            _exec_recall_sensory_memories,
        )
        from core.services.memory_write_queue import process_queue

        write = _exec_record_sensory_memory({
            "modality": "mixed",
            "content": "test runde: kaffe og tastatur",
            "mood_tone": "koncentreret",
        })
        assert write["status"] == "ok"

        # Flush async queue before recalling
        process_queue(batch_size=10)

        recall = _exec_recall_sensory_memories({"limit": 10})
        assert recall["status"] == "ok"
        assert recall["count"] >= 1

    def test_recall_empty(self):
        from core.tools.sensory_tools import _exec_recall_sensory_memories

        result = _exec_recall_sensory_memories({"limit": 10})
        assert result["status"] == "ok"
        assert isinstance(result["items"], list)

    def test_recall_filter_modality(self):
        from core.tools.sensory_tools import _exec_recall_sensory_memories

        result = _exec_recall_sensory_memories({"modality": "audio", "limit": 10})
        assert result["status"] == "ok"
        for item in result["items"]:
            assert item["modality"] == "audio"


class TestCentralWiring:
    """Coverage-gate: sanse-intaget observeres egress-frit til Centralen."""

    def test_source_wires_record_private(self):
        import inspect
        import core.tools.sensory_tools as mod
        src = inspect.getsource(mod)
        assert "record_private" in src
