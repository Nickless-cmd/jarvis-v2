"""Tests for core.services.memory_write_queue — async write queue."""
from __future__ import annotations

import pytest


@pytest.fixture
def fresh_queue(monkeypatch, tmp_path):
    """Isolate queue DB via HOME-based DB_PATH, then reset module state."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))

    # Force reload of ALL config/DB modules so Path.home() is re-evaluated.
    # Order matters: config → db_core → db → bootstrap → memory_write_queue
    import importlib
    for mod_name in [
        "core.runtime.config",
        "core.runtime.db_core",
        "core.runtime.db",
        "core.runtime.bootstrap",
        "core.services.memory_write_queue",
    ]:
        importlib.reload(__import__(mod_name, fromlist=[""]))

    from core.services import memory_write_queue as mwq
    return mwq


class TestEnqueueWrite:
    def test_enqueue_sensory(self, fresh_queue):
        mwq = fresh_queue
        qid = mwq.enqueue_write("sensory", {
            "modality": "visual", "content": "test", "mood_tone": "neutral",
        })
        assert qid != ""
        assert qid.startswith("mwq-")
        counts = mwq.queue_size()
        assert counts["pending"] >= 1

    def test_enqueue_brain(self, fresh_queue):
        mwq = fresh_queue
        qid = mwq.enqueue_write("brain", {
            "kind": "indsigt", "title": "test", "content": "brain entry",
            "visibility": "personal", "domain": "self",
        })
        assert qid != ""

    def test_enqueue_memory_sidecar(self, fresh_queue):
        mwq = fresh_queue
        qid = mwq.enqueue_write("memory_sidecar", {
            "heading": "test", "action": "updated", "content": "sidecar",
        })
        assert qid != ""

    def test_enqueue_invalid_type(self, fresh_queue):
        mwq = fresh_queue
        qid = mwq.enqueue_write("invalid_type", {"content": "nope"})
        assert qid == ""

    def test_queue_initial_state_empty(self, fresh_queue):
        mwq = fresh_queue
        counts = mwq.queue_size()
        assert counts["total"] == 0, f"expected empty queue, got {counts}"


class TestProcessQueue:
    def test_process_pending(self, fresh_queue):
        mwq = fresh_queue
        qid = mwq.enqueue_write("sensory", {
            "modality": "atmosphere", "content": "en stille stue", "mood_tone": "roligt",
        })
        assert qid != ""

        result = mwq.process_queue(batch_size=10)
        assert result["processed"] >= 1
        assert result["succeeded"] >= 1

        counts = mwq.queue_size()
        assert counts["pending"] == 0, f"expected 0 pending, got {counts}"

    def test_process_empty_no_error(self, fresh_queue):
        mwq = fresh_queue
        result = mwq.process_queue(batch_size=10)
        assert result["processed"] == 0
        assert result["failed"] == 0

    def test_multiple_writes_then_process(self, fresh_queue):
        mwq = fresh_queue
        for i in range(5):
            qid = mwq.enqueue_write("sensory", {
                "modality": "mixed", "content": f"batch item {i}", "mood_tone": "neutral",
            })
            assert qid != ""
        counts = mwq.queue_size()
        assert counts["pending"] == 5, f"expected 5 pending, got {counts}"

        result = mwq.process_queue(batch_size=10)
        assert result["processed"] == 5, f"expected 5 processed, got {result}"
        assert result["succeeded"] == 5


class TestDaemonTick:
    def test_tick_signature(self, fresh_queue):
        mwq = fresh_queue
        result = mwq.tick_memory_write_queue_daemon()
        assert isinstance(result, dict)

    def test_tick_processes_items(self, fresh_queue):
        mwq = fresh_queue
        mwq.enqueue_write("sensory", {
            "modality": "visual", "content": "tick test", "mood_tone": "neutral",
        })
        result = mwq.tick_memory_write_queue_daemon()
        assert result.get("processed", 0) >= 1 or result.get("succeeded", 0) >= 1
