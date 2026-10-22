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
    from core.identity.workspace_context import user_context
    from core.services import scoped_recall_policy
    monkeypatch.setattr(scoped_recall_policy, "recall_enabled", lambda: True)
    with user_context(discord_id="test-user"):
        yield


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


class TestSourceParameter:
    """`source` stod i beskrivelsen, men ikke i schemaet — og handleren læste
    den aldrig. Målt 17/10-2026: nattens tre natrutine-poster fik 'ukendt'.

    To fejl, to tests: uden schema-parameteren kan kilden ikke SENDES, og uden
    foldningen i handleren kan den ikke MODTAGES. Den ene alene retter intet.
    """

    def test_schema_tilbyder_source(self):
        """Uden parameteren i schemaet afviser runtime et top-level source."""
        from core.tools.sensory_tools import SENSORY_TOOL_DEFINITIONS

        rec = next(
            d for d in SENSORY_TOOL_DEFINITIONS
            if d["function"]["name"] == "record_sensory_memory"
        )
        props = rec["function"]["parameters"]["properties"]
        assert "source" in props, (
            "beskrivelsen lover `source`, men schemaet tilbyder den ikke — "
            "så kan den aldrig sendes"
        )

    def test_top_level_source_naar_metadata(self):
        """Et top-level source skal foldes ind, dér hvor normaliseringen læser."""
        from core.tools.sensory_tools import _exec_record_sensory_memory
        from core.services.memory_write_queue import process_queue
        from core.services import sensory_archive

        write = _exec_record_sensory_memory({
            "modality": "atmosphere",
            "content": "natrutine-test: stille stue, gråt lys",
            "source": "natrutine",
        })
        assert write["status"] == "ok", write

        process_queue(batch_size=10)

        poster = sensory_archive.list_recent(limit=5)
        assert poster, "skrivningen nåede ikke arkivet"
        nyeste = poster[0]
        assert nyeste["metadata"].get("source") == "natrutine", (
            f"kilden tabtes: {nyeste['metadata']!r}"
        )
