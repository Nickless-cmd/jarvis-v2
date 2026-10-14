from __future__ import annotations

from dataclasses import asdict

import pytest

from core.services.routine_types import AccessScope, RoutineCreate, RoutinePrincipal


@pytest.fixture(autouse=True)
def deterministic_user_keys(monkeypatch):
    import core.services.keyring_store as keyring_store

    monkeypatch.setattr(
        keyring_store,
        "get_user_key",
        lambda owner: (owner.encode("utf-8") + b"x" * 32)[:32],
    )


@pytest.fixture
def adapters(isolated_runtime):
    from core.runtime.db_core import connect
    from core.services.routine_service import RoutineService
    from core.services.routine_trigger_adapters import RoutineTriggerAdapters

    owner = RoutinePrincipal("canonical-owner", role="owner")
    service = RoutineService(owner)
    for source_kind in ("scheduled", "recurring"):
        routine = service.create_and_activate(RoutineCreate(
            name=f"{source_kind} routine",
            instruction=f"execute {source_kind}".encode(),
            capability_scope="chat",
            trigger_kind="schedule" if source_kind == "scheduled" else "interval",
        ))
        source_id = f"{source_kind}-1"
        with connect() as conn:
            conn.execute(
                "INSERT INTO routine_legacy_links "
                "(legacy_link_id,routine_id,run_id,source_kind,source_id,source_ref_enc,created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (f"link-{source_kind}", routine.id, None, source_kind, source_id,
                 b"opaque", "2026-10-12T00:00:00+00:00"),
            )
    return RoutineTriggerAdapters(system_owner_user_id="canonical-owner")


@pytest.mark.parametrize(
    "producer", ["scheduled", "recurring", "heartbeat", "dream", "council", "wakeup"]
)
def test_producers_enqueue_exactly_one_run_without_session(
    producer, adapters, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("legacy session delivery reached")

    monkeypatch.setattr("core.services.chat_sessions.append_chat_message", forbidden)
    monkeypatch.setattr(
        "core.services.notification_bridge.send_session_notification", forbidden
    )
    monkeypatch.setattr("core.services.session_inbox.enqueue", forbidden)

    created = adapters.fire(producer, source_id=f"{producer}-1")
    repeated = adapters.fire(producer, source_id=f"{producer}-1")

    assert created.count == 1
    assert repeated.count == 0
    assert "chat_session_id" not in asdict(created.run)
    assert created.run.idempotency_key == f"{producer}:{producer}-1"


def test_cutover_gate_never_runs_legacy_and_routine_paths_together(
    adapters, monkeypatch
):
    from core.services.routine_trigger_adapters import dispatch_recurring

    legacy_calls = []
    monkeypatch.setenv("JARVIS_ROUTINES_CUTOVER", "1")
    result = dispatch_recurring(
        "recurring-1", legacy=lambda: legacy_calls.append("legacy"), adapters=adapters
    )
    assert result.count == 1
    assert legacy_calls == []

    monkeypatch.setenv("JARVIS_ROUTINES_CUTOVER", "0")
    result = dispatch_recurring(
        "recurring-2", legacy=lambda: legacy_calls.append("legacy"), adapters=adapters
    )
    assert result is None
    assert legacy_calls == ["legacy"]


def test_system_producer_registry_is_closed(adapters):
    from core.services.routine_trigger_adapters import UnknownSystemProducer

    with pytest.raises(UnknownSystemProducer):
        adapters.fire("heartbeat-lookalike", source_id="fake-1")


def test_diagnostic_projector_remains_the_only_allowed_session_append(monkeypatch):
    from core.services.routine_diagnostics import project_failure, publish_failure

    calls = []
    monkeypatch.setattr(
        "core.identity.owner_resolver.resolve_owner_app_session", lambda: "owner-app"
    )
    monkeypatch.setattr(
        "core.identity.owner_resolver.session_is_external_channel", lambda _sid: False
    )
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "owner")
    monkeypatch.setattr(
        "core.services.chat_sessions.append_chat_message", lambda **kw: calls.append(kw)
    )
    monkeypatch.setattr(
        "core.services.inbox_state.registrer_kilde", lambda **_kw: {"status": "ok"}
    )
    publish_failure(project_failure(RuntimeError("private"), {}))
    assert len(calls) == 1
    assert calls[0]["session_id"] == "owner-app"
