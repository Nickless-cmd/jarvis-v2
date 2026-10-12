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


def test_unknown_tool_outcome_is_failed_and_never_requeued(queued_run):
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
    reconciler.reconcile_once(now=now + timedelta(seconds=91))

    run = runner.repository.get_run(queued_run.run_id)
    assert run.status == "failed"
    assert run.diagnostic_code == "tool_outcome_unknown"
    assert runner.repository.next_queued_run() is None


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

    runner = Runner()
    runtime = RoutineRuntime(runner=runner, reconciler=Reconciler(), poll_seconds=0.01)
    runtime.start()
    runtime.stop(timeout_seconds=2)
    claims_at_stop = runner.claims

    assert runtime.worker_is_alive() is False
    assert runtime.reconciler_is_alive() is False
    assert runtime.claim_count_after_stop() == 0
    assert runner.claims == claims_at_stop
