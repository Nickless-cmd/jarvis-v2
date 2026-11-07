"""Surface for approval_feedback_subscriber (dark-edges batch 2). Se test_memory_and_approval_surfaces.py for reglerne."""
from __future__ import annotations

import queue

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


def test_approval_feedback_subscriber_surface(db):
    import core.services.approval_feedback_subscriber as fs
    _inactive(fs.build_approval_feedback_subscriber_surface(), "approval-feedback-subscriber", "findes ikke endnu")
    from core.runtime.db_schema import init_db
    init_db()  # tabellen oprettes af init_db, ikke af skriveren
    _inactive(fs.build_approval_feedback_subscriber_surface(), "approval-feedback-subscriber", "er tom")

    def run(*payloads):
        q: queue.Queue = queue.Queue()
        for i, p in enumerate(payloads):
            q.put({"kind": fs._SUPPORTED_KIND, "created_at": f"2026-11-07T10:00:0{i}+00:00", "payload": p})
        q.put(None)
        fs._SUBSCRIBER_STOP.clear()
        fs._subscriber_loop(subscriber=q)  # den rigtige forbruger-loekke

    run({"approval_state": "approved", "intent_key": "k1", "approval_source": "desk",
         "tool_name": "bash", "session_id": "s1"})
    s = _ok(fs.build_approval_feedback_subscriber_surface(), "approval-feedback-subscriber")
    assert s["active"] is True and s["signals"]["total"] == 1
    assert s["signals"]["by_state"] == {"approved": 1} and s["signals"]["by_source"] == {"desk": 1}
    assert s["signals"]["subscriber_alive"] is False
    run({"approval_state": "rejected", "intent_key": "k2", "approval_source": "desk",
         "tool_name": "bash", "session_id": "s2"},
        {"approval_state": "rejected", "intent_key": "k3", "approval_source": "mobil",
         "tool_name": "write_file", "session_id": "s2"})
    s = fs.build_approval_feedback_subscriber_surface()
    assert s["signals"]["total"] == 3 and s["signals"]["sessions"] == 2
    assert s["signals"]["by_state"] == {"rejected": 2, "approved": 1}
    assert s["signals"]["by_source"] == {"desk": 2, "mobil": 1}
    assert s["signals"]["top_tools"][0] == {"tool": "bash", "count": 2}


