from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services.agentic_execution import AgenticTurn, ToolCall
from core.services.routine_types import RoutineCreate, RoutinePrincipal


@pytest.fixture(autouse=True)
def deterministic_user_keys(monkeypatch):
    import core.services.keyring_store as keyring_store

    monkeypatch.setattr(
        keyring_store,
        "get_user_key",
        lambda owner: (owner.encode("utf-8") + b"x" * 32)[:32],
    )


class _OneToolDriver:
    def complete(self, request):
        if request.round_number == 1:
            return AgenticTurn(tool_calls=(ToolCall("call-1", "safe_tool", {}),))
        return AgenticTurn(text="done")


class _ApprovalDriver:
    def complete(self, _request):
        return AgenticTurn(tool_calls=(
            ToolCall("approval-1", "risky_tool", {}, requires_approval=True),
        ))


@pytest.fixture
def principal():
    return RoutinePrincipal("member-a", role="member")


@pytest.fixture
def service(isolated_runtime, principal):
    from core.services.routine_service import RoutineService

    return RoutineService(principal)


@pytest.fixture
def active_routine(service):
    return service.create_and_activate(RoutineCreate(
        name="Privat rutine",
        instruction=b"udfoer den private opgave",
        capability_scope="chat",
        trigger_kind="manual",
        failure_policy={"consecutive_failures": 3},
    ))


@pytest.fixture
def queued_run(service, active_routine):
    return service.enqueue_run(active_routine.id, trigger_key="manual:runner")


def test_stale_generation_cannot_dispatch_or_write(queued_run):
    from core.services.routine_runner import RoutineRunner, StaleRoutineLease

    runner = RoutineRunner(driver=_OneToolDriver(), tool_executor=lambda _call: "ok")
    claimed = runner.repository.claim(queued_run.run_id, holder=runner.holder)
    runner.repository.reclaim(
        queued_run.run_id,
        expected_generation=claimed.lease_generation,
        holder="replacement",
    )

    with pytest.raises(StaleRoutineLease):
        runner.dispatch_tool(
            queued_run.run_id,
            generation=claimed.lease_generation,
            call=ToolCall("late-call", "safe_tool", {}),
        )
    with pytest.raises(StaleRoutineLease):
        runner.recorder.append(
            queued_run.run_id,
            generation=claimed.lease_generation,
            kind="tool_result",
            payload={},
        )


def test_unknown_tool_outcome_is_failed_and_never_requeued(queued_run, monkeypatch):
    from core.services.routine_reconciler import RoutineReconciler
    from core.services.routine_runner import RoutineRunner

    now = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
    runner = RoutineRunner(driver=_OneToolDriver(), tool_executor=lambda _call: "ok")
    claimed = runner.repository.claim(
        queued_run.run_id,
        holder=runner.holder,
        now=now,
    )
    runner.repository.record_tool_dispatch_started(
        queued_run.run_id,
        generation=claimed.lease_generation,
        call=ToolCall("call-open", "private_tool", {"secret": "not persisted"}),
        now=now,
    )

    reconciler = RoutineReconciler(repository=runner.repository)
    published = []
    monkeypatch.setattr(
        "core.services.routine_runner.publish_operational_failure",
        lambda **kw: published.append(kw),
    )
    reconciler.reconcile_once(now=now + timedelta(seconds=91))

    run = runner.repository.get_run(queued_run.run_id)
    assert run.status == "failed"
    assert run.diagnostic_code == "tool_outcome_unknown"
    assert runner.repository.next_queued_run() is None
    assert runner.repository.get_failure_count(queued_run.routine_id) == 1
    assert published == [{
        "routine_id": queued_run.routine_id,
        "run_id": queued_run.run_id,
        "component": "tool",
    }]


def test_third_execution_failure_pauses_but_delivery_failure_does_not(
    service, active_routine
):
    from core.services.routine_delivery import RoutineDeliveryService
    from core.services.routine_runner import RoutineRunner

    runner = RoutineRunner()
    for number in range(1, 4):
        runner.record_execution_failure(active_routine.id, run_id=f"run-{number}")
    assert service.get(active_routine.id).status == "paused"

    service.resume(active_routine.id)
    RoutineDeliveryService().record_terminal_failure(run_id="delivery-only")
    assert service.get(active_routine.id).status == "active"


def test_success_resets_execution_failure_counter(service, active_routine):
    from core.services.routine_runner import RoutineRunner

    runner = RoutineRunner()
    runner.record_execution_failure(active_routine.id, run_id="run-1")
    runner.record_execution_success(active_routine.id)
    runner.record_execution_failure(active_routine.id, run_id="run-2")
    assert runner.repository.get_failure_count(active_routine.id) == 1
    assert service.get(active_routine.id).status == "active"


def test_run_once_records_exactly_one_terminal_event(queued_run):
    from core.services.routine_runner import RoutineRunner

    runner = RoutineRunner(driver=_OneToolDriver(), tool_executor=lambda _call: "ok")
    result = runner.run_once(queued_run.run_id)

    assert result.status == "succeeded"
    events = runner.recorder.list(queued_run.run_id, decrypt_for="member-a")
    assert sum(bool(event["terminal"]) for event in events) == 1
    assert runner.repository.list_open_tool_effects(queued_run.run_id) == []


def test_success_completion_does_not_use_non_atomic_delivery_insert(
    queued_run, monkeypatch,
):
    from core.services.routine_runner import RoutineRunner

    monkeypatch.setattr(
        "core.runtime.db_routines.create_delivery",
        lambda **_kw: (_ for _ in ()).throw(AssertionError("split completion")),
    )
    result = RoutineRunner(
        driver=_OneToolDriver(), tool_executor=lambda _call: "ok",
    ).run_once(queued_run.run_id)
    assert result.status == "succeeded"


def test_successful_run_creates_one_owner_scoped_delivery(queued_run):
    from core.runtime.db_core import connect
    from core.services.routine_runner import RoutineRunner

    runner = RoutineRunner(driver=_OneToolDriver(), tool_executor=lambda _call: "ok")
    runner.run_once(queued_run.run_id)
    with connect() as conn:
        rows = conn.execute(
            "SELECT owner_user_id,channel,status FROM routine_deliveries WHERE run_id=?",
            (queued_run.run_id,),
        ).fetchall()
    assert [tuple(row) for row in rows] == [("member-a", "desk", "pending")]


def test_approval_required_notifies_owner_without_counting_execution_failure(
    service, active_routine, monkeypatch,
):
    from core.services.routine_runner import RoutineRunner

    active_routine = service.update(
        active_routine.id, expected_version=active_routine.version,
        inbox_policy={"action_required": True},
    )
    run = service.enqueue_run(active_routine.id, trigger_key="manual:approval")
    writes = []
    monkeypatch.setattr(
        "core.services.inbox_state.registrer_kilde",
        lambda **kw: writes.append(kw) or {"status": "ok"},
    )
    runner = RoutineRunner(driver=_ApprovalDriver())
    result = runner.run_once(run.run_id)

    assert result.status == "waiting_approval"
    assert runner.repository.get_failure_count(active_routine.id) == 0
    assert [item["beskrivelse"] for item in writes] == [
        "Routinehændelse: action_required",
    ]
    assert "approval_requested" in {
        event["kind"] for event in runner.recorder.list(run.run_id, decrypt_for="member-a")
    }


def test_runtime_stop_joins_workers_without_claiming_more():
    from core.services.routine_runtime import RoutineRuntime

    class Runner:
        def __init__(self):
            self.claims = 0

        def run_next(self):
            self.claims += 1
            return None

    class Reconciler:
        def reconcile_once(self):
            return 0

        def sweep_retention(self):
            return {"archived": 0, "deleted": 0}

    class Delivery:
        def __init__(self):
            self.claims = 0

        def deliver_next(self):
            self.claims += 1
            return None

    runner = Runner()
    delivery = Delivery()
    runtime = RoutineRuntime(
        runner=runner, reconciler=Reconciler(), delivery=delivery,
        poll_seconds=0.01,
    )
    runtime.start()
    runtime.stop(timeout_seconds=2)
    claims_at_stop = runner.claims

    assert runtime.worker_is_alive() is False
    assert runtime.reconciler_is_alive() is False
    assert runtime.claim_count_after_stop() == 0
    assert runner.claims == claims_at_stop
    assert delivery.claims > 0
