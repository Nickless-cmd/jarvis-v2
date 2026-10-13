from __future__ import annotations

import json

import pytest

from core.services.agentic_execution import AgenticTurn
from core.services.routine_types import AccessScope, RoutineCreate, RoutinePrincipal


@pytest.fixture(autouse=True)
def deterministic_user_keys(monkeypatch):
    import core.services.keyring_store as keyring_store

    monkeypatch.setattr(
        keyring_store,
        "get_user_key",
        lambda owner: (owner.encode("utf-8") + b"x" * 32)[:32],
    )


class _SuccessDriver:
    def complete(self, _request):
        return AgenticTurn(text="privat resultat")


class _FailureDriver:
    def complete(self, _request):
        raise RuntimeError("never-visible")


def _command(**changes):
    values = {
        "name": "Privat rutine",
        "instruction": b"privat instruktion",
        "capability_scope": "chat",
        "trigger_kind": "manual",
        "delivery_policy": {"channel": "desk"},
    }
    values.update(changes)
    return RoutineCreate(**values)


def _delivery(run_id):
    from core.runtime.db_core import connect

    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM routine_deliveries WHERE run_id=?", (run_id,),
        ).fetchone()
    return None if row is None else dict(row)


def test_user_routine_isolated_run_has_timeline_and_private_delivery(
    isolated_runtime, monkeypatch,
):
    from core.services.routine_runner import RoutineRunner
    from core.services.routine_service import RoutineService

    def forbidden(*_args, **_kwargs):
        raise AssertionError("routine execution reached a session surface")

    monkeypatch.setattr("core.services.chat_sessions.append_chat_message", forbidden)
    monkeypatch.setattr("core.services.session_inbox.enqueue", forbidden, raising=False)
    member = RoutinePrincipal("member-1", role="member")
    service = RoutineService(member)
    routine = service.create_and_activate(_command())
    run = service.enqueue_run(routine.id, trigger_key="manual:e2e")

    result = RoutineRunner(driver=_SuccessDriver()).run_once(run.run_id)

    assert result.status == "succeeded"
    events = service.list_run_events(run.run_id)
    assert [event["kind"] for event in events][-1] == "succeeded"
    delivery = _delivery(run.run_id)
    assert delivery is not None
    assert delivery["owner_user_id"] == "member-1"
    assert delivery["channel"] == "desk"


def test_system_owner_routine_and_delivery_are_owner_only(isolated_runtime):
    from core.services.routine_authorization import RoutineForbidden
    from core.services.routine_runner import RoutineRunner
    from core.services.routine_service import RoutineService

    owner = RoutinePrincipal("house-owner", role="owner")
    owner_service = RoutineService(owner)
    routine = owner_service.create_and_activate(_command(access_scope=AccessScope.SYSTEM_OWNER))
    run = owner_service.enqueue_run(routine.id, trigger_key="manual:system-e2e")
    RoutineRunner(driver=_SuccessDriver()).run_once(run.run_id)

    assert _delivery(run.run_id)["owner_user_id"] == "house-owner"
    with pytest.raises(RoutineForbidden):
        RoutineService(RoutinePrincipal("member-2", role="member")).get(routine.id)


def test_cross_user_failure_exposes_only_redacted_projection(isolated_runtime):
    from core.services.routine_authorization import RoutineForbidden
    from core.services.routine_runner import RoutineRunner
    from core.services.routine_service import RoutineService

    member_service = RoutineService(RoutinePrincipal("member-1", role="member"))
    routine = member_service.create_and_activate(_command())
    run = member_service.enqueue_run(routine.id, trigger_key="manual:failure-e2e")
    result = RoutineRunner(driver=_FailureDriver()).run_once(run.run_id)
    owner_service = RoutineService(RoutinePrincipal("house-owner", role="owner"))

    assert result.status == "failed"
    diagnostic = owner_service.get_redacted_diagnostic(run.run_id)
    assert "never-visible" not in json.dumps(diagnostic)
    with pytest.raises(RoutineForbidden):
        owner_service.get(routine.id)


def test_failed_run_uses_its_owners_selected_inbox(isolated_runtime, monkeypatch):
    from core.services.routine_runner import RoutineRunner
    from core.services.routine_service import RoutineService

    writes = []
    monkeypatch.setattr(
        "core.services.inbox_state.registrer_kilde",
        lambda **kw: writes.append(kw) or {"status": "ok"},
    )
    service = RoutineService(RoutinePrincipal("member-1", role="member"))
    routine = service.create_and_activate(_command(inbox_policy={"failed": True}))
    writes.clear()
    run = service.enqueue_run(routine.id, trigger_key="manual:inbox-failure")
    published = []
    monkeypatch.setattr(
        "core.services.routine_runner.publish_operational_failure",
        lambda **kw: published.append(kw),
    )
    RoutineRunner(driver=_FailureDriver()).run_once(run.run_id)

    assert len(writes) == 1
    assert writes[0]["bruger_id"] == "member-1"
    assert writes[0]["beskrivelse"] == "Routinehændelse: failed"
    assert published == [{
        "routine_id": routine.id, "run_id": run.run_id, "component": "runner",
    }]
