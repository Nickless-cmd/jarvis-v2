"""Acceptance flows for Routine policy/presence routing."""
from __future__ import annotations

import pytest

from core.services.agentic_execution import AgenticTurn
from core.services.routine_types import RoutineCreate, RoutinePrincipal


@pytest.fixture(autouse=True)
def deterministic_user_keys(monkeypatch):
    import core.services.keyring_store as keyring_store

    monkeypatch.setattr(
        keyring_store,
        "get_user_key",
        lambda owner: (owner.encode("utf-8") + b"x" * 32)[:32],
    )


def _run(isolated_runtime, *, owner="bjorn", mode="adaptive", importance="normal"):
    from core.services.routine_service import RoutineService

    service = RoutineService(RoutinePrincipal(owner, role="member"))
    routine = service.create_and_activate(RoutineCreate(
        name="Rutine",
        instruction=b"Undersoeg og udfoer opgaven",
        capability_scope="chat",
        trigger_kind="schedule",
        execution_mode=mode,
        importance=importance,
        delivery_policy={"channel": "desk"},
    ))
    return service, routine, service.enqueue_run(
        routine.id, trigger_key="schedule:2026-10-26T08:00:00+00:00",
    )


def test_a_busy_jarvis_routes_adaptive_occurrence_to_background(
    isolated_runtime, monkeypatch,
):
    from core.services import routine_dispatch
    from core.services.routine_runner import RoutineRunner

    _service, _routine, run = _run(isolated_runtime)
    monkeypatch.setattr(
        routine_dispatch, "resolve_owner_session", lambda _owner: ("chat-bjorn", "valid"),
    )
    monkeypatch.setattr(
        routine_dispatch, "runtime_presence", lambda _sid: ("busy", "active-run"),
    )
    executed = []
    runner = RoutineRunner()
    monkeypatch.setattr(runner, "run_once", lambda run_id: executed.append(run_id) or "done")

    assert runner.run_next() == "done"
    assert executed == [run.run_id]


def test_b_idle_jarvis_executes_in_verified_session_once(
    isolated_runtime, monkeypatch,
):
    from core.runtime import db_routines
    from core.services import routine_dispatch
    from core.services.routine_runner import RoutineRunner

    service, routine, run = _run(isolated_runtime)
    monkeypatch.setattr(
        routine_dispatch, "resolve_owner_session", lambda _owner: ("chat-bjorn", "valid"),
    )
    monkeypatch.setattr(
        routine_dispatch, "runtime_presence", lambda _sid: ("idle", ""),
    )
    starts = []
    callback = {}

    def fake_start(message, **kwargs):
        starts.append((message, kwargs))
        callback["finish"] = kwargs["completion_callback"]
        return True

    monkeypatch.setattr(
        "core.services.visible_autonomous_run.start_autonomous_run", fake_start,
    )
    runner = RoutineRunner()
    monkeypatch.setattr(
        runner, "run_once", lambda _run_id: pytest.fail("unnecessary background run"),
    )

    outcome = runner.run_next()
    assert outcome.path == "session"
    assert len(starts) == 1
    assert starts[0][1]["session_id"] == "chat-bjorn"
    assert starts[0][1]["force_user_id"] == "bjorn"
    assert "ROUTINE WAKEUP" in starts[0][0]
    # The occurrence is already leased, so a second worker cannot execute it.
    assert runner.run_next() is None

    callback["finish"](
        outcome="completed", visible_run_id="visible-1",
        session_id="chat-bjorn", error="",
    )
    settled = db_routines.get_run(run.run_id, decrypt_for="bjorn")
    assert settled["status"] == "succeeded"
    assert b'"visible_run_id": "visible-1"' in settled["result"]
    assert service.list_runs(routine.id)[0].run_id == run.run_id


def test_c_offline_member_never_uses_another_users_session(
    isolated_runtime, monkeypatch,
):
    from core.runtime import db_routines
    from core.services import routine_dispatch
    from core.services.routine_runner import RoutineRunner

    _service, _routine, run = _run(isolated_runtime, owner="michelle")
    monkeypatch.setattr(
        routine_dispatch, "resolve_owner_session", lambda owner: ("", "offline"),
    )
    executed = []
    runner = RoutineRunner()

    def isolated(run_id):
        executed.append(db_routines.get_run(run_id)["owner_user_id"])
        return "isolated"

    monkeypatch.setattr(runner, "run_once", isolated)
    assert runner.run_next() == "isolated"
    assert executed == ["michelle"]
    assert db_routines.get_run(run.run_id)["status"] == "queued"


class _SuccessDriver:
    def complete(self, _request):
        return AgenticTurn(text="kritisk evidens")


def test_d_critical_background_result_is_durable_and_escalated(
    isolated_runtime, monkeypatch,
):
    from core.runtime import db_routines
    from core.services.routine_runner import RoutineRunner

    _service, _routine, run = _run(
        isolated_runtime, mode="background", importance="critical",
    )
    inbox = []
    monkeypatch.setattr(
        "core.services.inbox_state.registrer_kilde",
        lambda **kwargs: inbox.append(kwargs) or {"status": "ok"},
    )

    result = RoutineRunner(driver=_SuccessDriver()).run_next()
    stored = db_routines.get_run(run.run_id, decrypt_for="bjorn")
    assert result.status == "succeeded"
    assert stored["status"] == "succeeded"
    assert stored["result"] == b"kritisk evidens"
    assert inbox[-1]["bloker"] is True
    assert run.run_id in inbox[-1]["beskrivelse"]


def test_unknown_presence_or_owner_never_opens_execution(
    isolated_runtime, monkeypatch,
):
    from core.services import routine_dispatch
    from core.services.routine_runner import RoutineRunner

    _service, _routine, run = _run(isolated_runtime)
    runner = RoutineRunner()
    monkeypatch.setattr(
        runner, "run_once", lambda _run_id: pytest.fail("fail-closed route executed"),
    )
    monkeypatch.setattr(
        routine_dispatch, "resolve_owner_session", lambda _owner: ("", "unknown-owner"),
    )
    assert runner.run_next().reason == "unknown-owner"

    monkeypatch.setattr(
        routine_dispatch, "resolve_owner_session", lambda _owner: ("chat-bjorn", "valid"),
    )
    monkeypatch.setattr(
        routine_dispatch, "runtime_presence", lambda _sid: ("unknown", "sensor-failed"),
    )
    outcome = runner.run_next()
    assert outcome.run_id == run.run_id
    assert outcome.reason == "sensor-failed"


def test_schedule_occurrence_idempotency_is_shared_by_both_paths(isolated_runtime):
    service, routine, run = _run(isolated_runtime)
    replay = service.enqueue_run(
        routine.id, trigger_key="schedule:2026-10-26T08:00:00+00:00",
    )
    assert replay.run_id == run.run_id
    assert len(service.list_runs(routine.id)) == 1


def test_presence_er_sessions_lokal_ikke_global(monkeypatch):
    """En kørsel i ÉN session må ikke gøre en ANDEN sessions rutine «busy».

    Målt 29/10-2026: vagten spurgte ``levende_koersler()`` — som svarer sandt
    for enhver kørsel i processen. En almindelig samtale kl. 05:00 gjorde
    Michelles og Mikkels morgenbriefe «busy», og de lå i kø i seks dage mens
    deres fire ugentlige briefs så sunde ud i basen.
    """
    from core.services import in_flight_runs, wakeup_dispatcher
    from core.services import routine_dispatch

    monkeypatch.setattr(
        in_flight_runs, "levende_koersler",
        lambda: [{"run_id": "visible-x", "session_id": "chat-A"}],
    )
    monkeypatch.setattr(wakeup_dispatcher, "_active_turn_blocks", lambda _sid: "")

    assert routine_dispatch.runtime_presence("chat-A") == ("busy", "active-run")
    assert routine_dispatch.runtime_presence("chat-B") == ("idle", "")


def test_presence_unknown_naar_sensor_fejler(monkeypatch):
    """Kan presence ikke måles, er svaret «ved ikke» — aldrig «ledig»."""
    from core.services import in_flight_runs
    from core.services import routine_dispatch

    def _braek():
        raise RuntimeError("sensor nede")

    monkeypatch.setattr(in_flight_runs, "levende_koersler", _braek)
    assert routine_dispatch.runtime_presence("chat-A") == ("unknown", "presence-unavailable")
