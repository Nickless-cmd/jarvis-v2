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

    assert side_tasks.resolve(
        tid, decision="running", arbejds_session="chat-2", arbejds_run_id="run-3",
    )["new_status"] == "running"
    assert state[0]["running_at"]
    assert state[0]["last_progress_at"]

    side_tasks.resolve(tid, decision="completed", lukket_af="jarvis",
                       bevis="Startpositionen er daekket af en test")
    assert state[0]["resolved_at"] and state[0]["status"] == "completed"
    assert side_tasks.list_open() == []
    assert side_tasks.list_alle()[0]["side_task_id"] == tid


@pytest.mark.parametrize("decision", ["paused", "blocked", "failed"])
def test_non_terminal_stop_requires_reason_and_remains_visible(monkeypatch, decision):
    state = _lager(monkeypatch)
    tid = side_tasks.flag(title="Lang opgave", prompt="Undersøg X")["side_task_id"]
    side_tasks.resolve(tid, decision="running", arbejds_session="chat-4", arbejds_run_id="run-4")

    assert side_tasks.resolve(tid, decision=decision)["status"] == "error"
    result = side_tasks.resolve(tid, decision=decision, reason="Venter på en ekstern afhængighed")

    assert result["new_status"] == decision
    assert state[0]["status"] == decision
    assert state[0]["state_reason"] == "Venter på en ekstern afhængighed"
    assert state[0][f"{decision}_at"]
    assert side_tasks.list_open()[0]["side_task_id"] == tid
    assert state[0]["transition_history"][-1]["to"] == decision


def test_running_task_can_return_to_queue_and_resume(monkeypatch):
    state = _lager(monkeypatch)
    tid = side_tasks.flag(title="Pausebar", prompt="Gør arbejdet")["side_task_id"]
    side_tasks.resolve(tid, decision="running", arbejds_session="chat-4")

    assert side_tasks.resolve(tid, decision="queued", reason="Fortsættes senere")["status"] == "ok"
    assert state[0]["status"] == "queued"
    assert side_tasks.resolve(tid, decision="running", arbejds_session="chat-5")["status"] == "ok"
    assert state[0]["status"] == "running"


def test_run_reconciliation_never_leaves_ambiguous_running_state(monkeypatch):
    state = _lager(monkeypatch)
    tid = side_tasks.flag(title="Autonom", prompt="Undersøg X")["side_task_id"]
    side_tasks.resolve(tid, decision="running", arbejds_session="chat-4", arbejds_run_id="run-4")

    assert side_tasks.reconcile_run(
        tid, outcome="failed", run_id="run-4", error="provider timeout",
    ) is True
    assert state[0]["status"] == "failed"
    assert "provider timeout" in state[0]["state_reason"]


def test_run_reconciliation_does_not_override_explicit_pause(monkeypatch):
    state = _lager(monkeypatch)
    tid = side_tasks.flag(title="Autonom", prompt="Undersøg X")["side_task_id"]
    side_tasks.resolve(tid, decision="running", arbejds_run_id="run-4")
    side_tasks.resolve(tid, decision="paused", reason="Bjørn satte den på pause")

    assert side_tasks.reconcile_run(tid, outcome="completed", run_id="run-4") is True
    assert state[0]["status"] == "paused"
    assert state[0]["state_reason"] == "Bjørn satte den på pause"


def test_run_progress_updates_current_step(monkeypatch):
    state = _lager(monkeypatch)
    tid = side_tasks.flag(title="Progress", prompt="Undersøg X")["side_task_id"]
    side_tasks.resolve(tid, decision="running", arbejds_run_id="run-4")

    assert side_tasks.record_run_progress("run-4", current_step="pytest") is True
    assert state[0]["current_step"] == "pytest"
    assert state[0]["last_progress_at"]


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
    side_tasks.resolve(first["side_task_id"], decision="dismissed",
                       reason="daekket af en anden opgave")
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
