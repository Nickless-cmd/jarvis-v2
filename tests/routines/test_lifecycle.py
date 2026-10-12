from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services.routine_types import RoutineCreate, RoutinePatch, RoutinePrincipal


def valid_create(**changes):
    values = {
        "name": "Morgenrutine",
        "instruction": b"Lav en privat opsummering",
        "capability_scope": "chat",
        "trigger_kind": "manual",
        "trigger_config": {},
        "permission_policy": {},
        "delivery_policy": {"channel": "desk"},
        "inbox_policy": {"failed": True},
        "retention_policy": {"archive_stopped_days": 30},
        "failure_policy": {"consecutive_failures": 3},
    }
    values.update(changes)
    return RoutineCreate(**values)


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
def jarvis_principal():
    return RoutinePrincipal("jarvis", role="system", actor_kind="jarvis")


@pytest.fixture
def service(isolated_runtime, member_principal):
    from core.services.routine_service import RoutineService

    return RoutineService(principal=member_principal)


@pytest.fixture
def active_routine(service):
    return service.create_and_activate(valid_create())


@pytest.fixture
def stopped_routine(service, active_routine):
    return service.stop(active_routine.routine_id)


def test_edit_during_run_keeps_old_snapshot(service, active_routine):
    run = service.enqueue_run(active_routine.routine_id, trigger_key="manual:1")
    updated = service.update(
        active_routine.routine_id,
        expected_version=1,
        patch=RoutinePatch(instruction=b"ny"),
    )
    old_run = service.get_run(run.run_id, decrypt=True)
    assert old_run.routine_version == 1
    assert old_run.definition_snapshot["instruction"] == b"Lav en privat opsummering"
    assert updated.version == 2


def test_editing_stopped_does_not_reactivate(service, stopped_routine):
    updated = service.update(
        stopped_routine.routine_id,
        expected_version=1,
        patch=RoutinePatch(name="nyt"),
    )
    assert updated.status == "stopped"
    assert updated.version == 2


def test_pause_and_resume_do_not_change_definition_version(service, active_routine):
    paused = service.pause(active_routine.routine_id)
    resumed = service.resume(active_routine.routine_id)
    assert paused.version == resumed.version == active_routine.version == 1


def test_stale_edit_is_rejected(service, active_routine):
    from core.services.routine_service import StaleRoutineVersion

    service.update(
        active_routine.routine_id,
        expected_version=1,
        patch=RoutinePatch(name="version two"),
    )
    with pytest.raises(StaleRoutineVersion):
        service.update(
            active_routine.routine_id,
            expected_version=1,
            patch=RoutinePatch(name="lost update"),
        )


def test_stop_revokes_claim_and_cancels_queued(service, active_routine):
    from core.runtime.db_routines import claim_run

    running = service.enqueue_run(active_routine.routine_id, trigger_key="manual:running")
    queued = service.enqueue_run(active_routine.routine_id, trigger_key="manual:queued")
    assert claim_run(running.run_id, holder="worker") is not None
    stopped = service.stop(active_routine.routine_id)
    assert stopped.status == "stopped"
    running_after = service.get_run(running.run_id)
    queued_after = service.get_run(queued.run_id)
    assert running_after.status == "cancelling"
    assert running_after.lease_holder is None
    assert running_after.lease_generation == 2
    assert queued_after.status == "cancelled"


def test_stop_is_idempotent(service, active_routine):
    first = service.stop(active_routine.routine_id)
    second = service.stop(active_routine.routine_id)
    assert second.status == first.status == "stopped"
    assert second.version == first.version


def test_jarvis_proposal_starts_as_draft(
    service, jarvis_principal, member_principal
):
    from core.services.routine_authorization import RoutineForbidden

    routine = service.create_proposal(
        jarvis_principal,
        for_owner=member_principal,
        command=valid_create(),
    )
    assert routine.status == "draft"
    with pytest.raises(RoutineForbidden):
        service.enqueue_run(jarvis_principal, routine.routine_id, trigger_key="system:1")


def test_jarvis_restart_requires_per_routine_opt_in(
    service, stopped_routine, jarvis_principal
):
    from core.services.routine_authorization import RoutineForbidden

    with pytest.raises(RoutineForbidden):
        service.restart(jarvis_principal, stopped_routine.routine_id)


def test_jarvis_may_restart_only_when_definition_opts_in(
    service, member_principal, jarvis_principal
):
    routine = service.create_and_activate(
        member_principal,
        valid_create(jarvis_restart_allowed=True),
    )
    service.stop(member_principal, routine.routine_id)
    restarted = service.restart(jarvis_principal, routine.routine_id)
    assert restarted.status == "active"
    assert restarted.instruction == b""
    assert restarted.name == ""


def test_stopped_routine_archives_after_30_days_but_is_not_deleted(
    service, stopped_routine
):
    from core.runtime.db_core import connect

    now = datetime(2026, 10, 12, tzinfo=UTC)
    with connect() as conn:
        conn.execute(
            "UPDATE routines SET stopped_at=? WHERE routine_id=?",
            ((now - timedelta(days=31)).isoformat(), stopped_routine.routine_id),
        )
    report = service.archive_stopped_before(now=now)
    assert report == {"archived": 1, "deleted": 0}
    assert service.get(stopped_routine.routine_id).status == "archived"


def test_auto_delete_requires_explicit_policy(service):
    from core.runtime.db_core import connect

    routine = service.create_and_activate(
        valid_create(retention_policy={"archive_stopped_days": 30, "auto_delete_days": 60})
    )
    service.stop(routine.routine_id)
    now = datetime(2026, 10, 12, tzinfo=UTC)
    with connect() as conn:
        conn.execute(
            "UPDATE routines SET stopped_at=? WHERE routine_id=?",
            ((now - timedelta(days=61)).isoformat(), routine.routine_id),
        )
    report = service.archive_stopped_before(now=now)
    assert report == {"archived": 0, "deleted": 1}
    assert service.get(routine.routine_id) is None


def test_delete_erases_private_rows_and_leaves_content_free_tombstone(
    service, active_routine
):
    from core.runtime.db_core import connect
    from core.runtime.db_routines import append_run_event, create_delivery

    run = service.enqueue_run(active_routine.routine_id, trigger_key="manual:delete")
    append_run_event(run_id=run.run_id, kind="output", payload={"private": "secret"})
    create_delivery(run_id=run.run_id, channel="desk", payload=b"secret")
    assert service.delete(active_routine.routine_id) is True
    with connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM routines WHERE routine_id=?", (active_routine.routine_id,)
        ).fetchone()[0] == 0
        tombstone = conn.execute(
            "SELECT * FROM routine_tombstones WHERE routine_id=?",
            (active_routine.routine_id,),
        ).fetchone()
    assert tombstone is not None
    assert set(tombstone.keys()) == {
        "routine_id", "owner_user_id_hash", "deleted_at", "reason_code"
    }


def test_recorder_keeps_one_terminal_event(service, active_routine):
    from core.services.routine_run_recorder import RoutineRunRecorder

    run = service.enqueue_run(active_routine.routine_id, trigger_key="manual:recorder")
    recorder = RoutineRunRecorder()
    first = recorder.append(run.run_id, kind="succeeded", payload={}, terminal=True)
    second = recorder.append(run.run_id, kind="failed", payload={}, terminal=True)
    assert first["event_id"] == second["event_id"]
