from __future__ import annotations

import inspect
import json
from dataclasses import asdict

import pytest

from core.services.routine_types import RoutineCreate, RoutinePrincipal


@pytest.fixture(autouse=True)
def deterministic_user_keys(monkeypatch):
    import core.services.keyring_store as keyring_store

    monkeypatch.setattr(
        keyring_store,
        "get_user_key",
        lambda owner: (owner.encode("utf-8") + b"x" * 32)[:32],
    )


@pytest.fixture
def member_principal():
    return RoutinePrincipal("member-a", role="member")


@pytest.fixture
def command():
    return RoutineCreate(
        name="Privat rutine",
        instruction=b"hemmelig instruktion",
        capability_scope="chat",
        trigger_kind="manual",
        delivery_policy={"channel": "desk"},
        inbox_policy={},
    )


@pytest.fixture
def successful_run(isolated_runtime, member_principal, command):
    from core.runtime.db_routines import create_delivery, transition_run
    from core.services.routine_service import RoutineService

    service = RoutineService(member_principal)
    routine = service.create_and_activate(command)
    run = service.enqueue_run(routine.routine_id, trigger_key="manual:delivery")
    transition_run(run.run_id, to_status="succeeded", result=b"privat resultat")
    create_delivery(run_id=run.run_id, channel="desk", payload=b"privat resultat")
    return run


@pytest.fixture
def delivery_service(isolated_runtime):
    from core.services.routine_delivery import RoutineDeliveryService

    return RoutineDeliveryService()


def test_failure_projection_cannot_leak_private_fields():
    from core.services.routine_diagnostics import project_failure

    raw = RuntimeError(
        "Michelle /home/m/private.txt token=sekret instruction=ring til lægen"
    )
    projection = project_failure(
        raw,
        {
            "routine_id": "Michelle-private-routine",
            "run_id": "/home/m/run",
            "routine_name": "Privat",
            "tool_args": {"x": "hemmelig"},
            "component": "Privat",
            "error_code": "sekret",
        },
    )
    encoded = json.dumps(asdict(projection), ensure_ascii=False)
    for forbidden in (
        "Michelle", "/home/m", "sekret", "ring til", "hemmelig", "Privat"
    ):
        assert forbidden not in encoded


def test_only_diagnostic_projector_may_write_shared_session(monkeypatch):
    from core.services.routine_diagnostics import (
        project_failure,
        publish_failure,
        render_projection,
    )

    calls = []
    inbox = []
    monkeypatch.setattr(
        "core.identity.owner_resolver.resolve_owner_app_session", lambda: "owner-app"
    )
    monkeypatch.setattr(
        "core.identity.owner_resolver.session_is_external_channel", lambda _sid: False
    )
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "owner-user")
    monkeypatch.setattr(
        "core.services.chat_sessions.append_chat_message", lambda **kw: calls.append(kw)
    )
    monkeypatch.setattr(
        "core.services.inbox_state.registrer_kilde", lambda **kw: inbox.append(kw) or {"status": "ok"}
    )
    projection = project_failure(RuntimeError("private"), {})
    outcome = publish_failure(projection)
    assert outcome == {"session": "delivered", "inbox": "ok"}
    assert len(calls) == 1
    assert calls[0]["session_id"] == "owner-app"
    assert calls[0]["content"] == render_projection(projection)
    assert inbox[0]["kildetype"] == "routine_event"


def test_diagnostic_projector_rejects_external_or_missing_session(monkeypatch):
    from core.services.routine_diagnostics import project_failure, publish_failure

    calls = []
    monkeypatch.setattr(
        "core.identity.owner_resolver.resolve_owner_app_session", lambda: "discord-session"
    )
    monkeypatch.setattr(
        "core.identity.owner_resolver.session_is_external_channel", lambda _sid: True
    )
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "owner-user")
    monkeypatch.setattr(
        "core.services.chat_sessions.append_chat_message", lambda **kw: calls.append(kw)
    )
    monkeypatch.setattr(
        "core.services.inbox_state.registrer_kilde", lambda **_kw: {"status": "ok"}
    )
    outcome = publish_failure(project_failure(RuntimeError("private"), {}))
    assert outcome["session"] == "blocked"
    assert calls == []


def test_delivery_retry_does_not_create_second_run(delivery_service, successful_run):
    first = delivery_service.claim_for_run(successful_run.run_id, holder="worker-1")
    delivery_service.settle(
        first.delivery_id,
        holder="worker-1",
        outcome="retry",
        next_attempt_at="2000-01-01T00:00:00+00:00",
    )
    assert delivery_service.repository.count_runs(successful_run.routine_id) == 1
    again = delivery_service.claim_for_run(successful_run.run_id, holder="worker-2")
    assert again.retry_count == 1
    assert again.lease_generation == 2


def test_wrong_delivery_holder_cannot_settle(delivery_service, successful_run):
    from core.services.routine_delivery import StaleDeliveryLease

    claim = delivery_service.claim_for_run(successful_run.run_id, holder="worker-1")
    with pytest.raises(StaleDeliveryLease):
        delivery_service.settle(
            claim.delivery_id,
            holder="worker-2",
            outcome="delivered",
        )


def test_terminal_delivery_failure_uses_routine_inbox_policy(
    isolated_runtime, member_principal, monkeypatch,
):
    from core.services.routine_delivery import RoutineDeliveryService
    from core.services.routine_service import RoutineService

    writes = []
    monkeypatch.setattr(
        "core.services.inbox_state.registrer_kilde",
        lambda **kw: writes.append(kw) or {"status": "ok"},
    )
    service = RoutineService(member_principal)
    routine = service.create_and_activate(RoutineCreate(
        name="Levering", instruction=b"privat", capability_scope="chat",
        trigger_kind="manual", inbox_policy={"delivery_failed": True},
    ))
    writes.clear()
    run = service.enqueue_run(routine.id, trigger_key="manual:delivery-fail")
    from core.runtime.db_routines import create_delivery, transition_run
    transition_run(run.run_id, to_status="succeeded", result=b"resultat")
    create_delivery(run_id=run.run_id, channel="desk", payload=b"resultat")
    delivery = RoutineDeliveryService()
    claim = delivery.claim_for_run(run.run_id, holder="delivery-worker")
    delivery.settle(claim.delivery_id, holder="delivery-worker", outcome="failed")

    assert [item["beskrivelse"] for item in writes] == [
        "Routinehændelse: delivery_failed",
    ]


def test_inbox_defaults_are_copied_then_overridable(
    isolated_runtime, member_principal, command
):
    from core.services.routine_inbox import RoutineInboxService
    from core.services.routine_service import RoutineService

    inbox_service = RoutineInboxService()
    inbox_service.set_user_defaults(member_principal, {"edited": False, "failed": True})
    routine = RoutineService(member_principal).create_and_activate(command)
    inbox_service.set_override(member_principal, routine.id, {"edited": True})
    effective = inbox_service.effective_policy(member_principal, routine.id)
    assert effective["edited"] is True
    assert effective["failed"] is True
    assert effective["created"] is True


def test_inbox_projection_obeys_user_policy(
    isolated_runtime, member_principal, command, monkeypatch
):
    from core.services.routine_inbox import RoutineInboxService
    from core.services.routine_service import RoutineService

    inbox_service = RoutineInboxService()
    inbox_service.set_user_defaults(member_principal, {"edited": False, "failed": True})
    routine = RoutineService(member_principal).create_and_activate(command)
    writes = []
    monkeypatch.setattr(
        "core.services.inbox_state.registrer_kilde", lambda **kw: writes.append(kw) or {"status": "ok"}
    )
    assert inbox_service.project_event_to_inbox({
        "event_id": "event-edit",
        "event_type": "edited",
        "owner_user_id": member_principal.user_id,
        "routine_id": routine.id,
    })["status"] == "suppressed"
    assert inbox_service.project_event_to_inbox({
        "event_id": "event-fail",
        "event_type": "failed",
        "owner_user_id": member_principal.user_id,
        "routine_id": routine.id,
    })["status"] == "ok"
    assert len(writes) == 1


def test_lifecycle_operations_project_only_user_selected_events(
    isolated_runtime, member_principal, monkeypatch,
):
    from core.services.routine_service import RoutineService

    writes = []
    monkeypatch.setattr(
        "core.services.inbox_state.registrer_kilde",
        lambda **kw: writes.append(kw) or {"status": "ok"},
    )
    command = RoutineCreate(
        name="Inbox-rutine", instruction=b"privat", capability_scope="chat",
        trigger_kind="manual",
        inbox_policy={
            "created": True, "edited": True, "paused": True,
            "stopped": True, "archived": True, "deleted": True,
        },
    )
    service = RoutineService(member_principal)
    routine = service.create_and_activate(command)
    routine = service.update(routine.id, expected_version=1, name="Nyt navn")
    service.pause(routine.id)
    service.resume(routine.id)
    service.stop(routine.id)
    service.restart(routine.id)
    service.stop(routine.id)
    service.archive(routine.id)
    service.restore(routine.id)
    assert service.delete(routine.id) is True

    event_types = [item["beskrivelse"].split(": ", 1)[1] for item in writes]
    assert event_types == [
        "created", "edited", "paused", "resumed", "stopped", "restarted",
        "stopped", "archived", "restored", "deleted",
    ]


def test_editing_inbox_policy_changes_the_effective_projection(
    isolated_runtime, member_principal, command, monkeypatch,
):
    from core.services.routine_inbox import RoutineInboxService
    from core.services.routine_service import RoutineService

    writes = []
    monkeypatch.setattr(
        "core.services.inbox_state.registrer_kilde",
        lambda **kw: writes.append(kw) or {"status": "ok"},
    )
    service = RoutineService(member_principal)
    routine = service.create_and_activate(command)
    writes.clear()
    service.update(
        routine.id, expected_version=1,
        inbox_policy={"created": False, "edited": True},
    )
    assert RoutineInboxService().effective_policy(member_principal, routine.id) == {
        "created": False, "edited": True,
    }
    assert [item["beskrivelse"] for item in writes] == ["Routinehændelse: edited"]


def test_only_diagnostics_module_imports_chat_append():
    import core.services.routine_delivery as delivery
    import core.services.routine_diagnostics as diagnostics
    import core.services.routine_inbox as inbox

    assert "append_chat_message" in inspect.getsource(diagnostics)
    assert "append_chat_message" not in inspect.getsource(delivery)
    assert "append_chat_message" not in inspect.getsource(inbox)
    assert "session_inbox" not in inspect.getsource(delivery)
    assert "notification_bridge" not in inspect.getsource(delivery)
