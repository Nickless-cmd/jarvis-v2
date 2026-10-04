from contextlib import nullcontext

import pytest

from core.services import side_tasks


def _lager(monkeypatch):
    state = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items))
    monkeypatch.setattr(side_tasks, "med_laas", lambda _key: nullcontext(), raising=False)
    return state


def test_queue_activation_and_completion_have_distinct_timestamps_and_links(monkeypatch):
    state = _lager(monkeypatch)
    tid = side_tasks.flag(title="Verificér første frame", prompt="Test startpositionen")["side_task_id"]
    assert state[0]["status"] == "pending"

    assert side_tasks.resolve(tid, decision="queued")["new_status"] == "queued"
    assert state[0]["queued_at"] and "resolved_at" not in state[0]
    assert side_tasks.resolve(
        tid, decision="activated", arbejds_session="chat-2", arbejds_run_id="run-3",
    )["new_status"] == "activated"
    assert state[0]["arbejds_session"] == "chat-2"
    assert state[0]["arbejds_run_id"] == "run-3"
    assert "resolved_at" not in state[0]

    side_tasks.resolve(tid, decision="completed", lukket_af="jarvis")
    assert state[0]["resolved_at"] and state[0]["status"] == "completed"
    assert side_tasks.list_open() == []
    assert side_tasks.list_alle()[0]["side_task_id"] == tid


def test_stable_finding_key_deduplicates_even_after_terminal_decision(monkeypatch):
    state = _lager(monkeypatch)
    first = side_tasks.flag(
        title="Test første frame", prompt="Test A", finding_key="coverage:RullendeTal:first-frame",
    )
    second = side_tasks.flag(
        title="Test første frame igen", prompt="Test B", finding_key="coverage:RullendeTal:first-frame",
    )
    assert second["side_task_id"] == first["side_task_id"]
    assert second["deduplicated"] is True
    assert len(state) == 1
    side_tasks.resolve(first["side_task_id"], decision="dismissed")
    third = side_tasks.flag(
        title="Test første frame igen", prompt="Test C", finding_key="coverage:RullendeTal:first-frame",
    )
    assert third["side_task_id"] == first["side_task_id"]
    assert len(state) == 1


def test_stale_work_returns_to_waiting_without_claiming_verified_completion(monkeypatch):
    state = _lager(monkeypatch)
    tid = side_tasks.flag(title="Lang opgave", prompt="Undersøg X")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-4")
    monkeypatch.setattr(side_tasks, "_sidst_aktiv", lambda _sid: "2020-01-01T00:00:00+00:00")
    result = side_tasks.fej_faerdige()
    assert result["lukket"] == 0
    assert state[0]["status"] == "pending"
    assert "resolved_at" not in state[0]


def test_long_active_run_is_not_returned_to_waiting(monkeypatch):
    state = _lager(monkeypatch)
    tid = side_tasks.flag(title="Langt run", prompt="Byg noget")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-9", arbejds_run_id="run-9")
    monkeypatch.setattr(side_tasks, "_sidst_aktiv", lambda _sid: "2020-01-01T00:00:00+00:00")
    monkeypatch.setattr(side_tasks, "_arbejds_run_aktiv", lambda _sid: True, raising=False)
    assert side_tasks.fej_faerdige().get("tilbage_til_venter", 0) == 0
    assert state[0]["status"] == "activated"


def test_tool_activation_binds_current_session_and_run(monkeypatch):
    state = _lager(monkeypatch)
    from core.services import session_context_resolve
    monkeypatch.setattr(session_context_resolve, "aktiv_session_id", lambda _d="": "chat-live")
    monkeypatch.setattr(session_context_resolve, "aktivt_run_id", lambda _d="": "run-live")
    tid = side_tasks.flag(title="A", prompt="B")["side_task_id"]
    assert side_tasks._exec_activate_side_task({"side_task_id": tid})["status"] == "ok"
    assert state[0]["arbejds_session"] == "chat-live"
    assert state[0]["arbejds_run_id"] == "run-live"


def test_failed_durable_write_never_reports_success(monkeypatch):
    _lager(monkeypatch)
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, _items: None)
    with pytest.raises(OSError, match="persist"):
        side_tasks.flag(title="A", prompt="B")
