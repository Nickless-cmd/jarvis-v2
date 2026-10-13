"""Fenced, session-neutral execution of one Routine run."""
from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from core.runtime import db_routines
from core.services.agentic_execution import (
    ExecutionResult,
    ModelDriver,
    RoutineExecutionAdapter,
    ToolCall,
    ToolResult,
    UsageRecord,
    execute_agentic,
)
from core.services.routine_run_recorder import RoutineRunRecorder
from core.services.routine_types import AccessScope, RoutineExecutionContext


_log = logging.getLogger(__name__)


def publish_operational_failure(
    *, routine_id: str, run_id: str, component: str,
) -> None:
    """Best-effort fixed-schema projection; never expose execution content."""
    try:
        from core.services.routine_diagnostics import project_failure, publish_failure

        projection = project_failure(RuntimeError("routine execution failed"), {
            "routine_id": routine_id,
            "run_id": run_id,
            "trusted_component": component,
        })
        publish_failure(projection)
    except Exception:
        _log.warning("routine failure projection could not be published", exc_info=True)


class StaleRoutineLease(RuntimeError):
    """The worker no longer owns the run generation."""


@dataclass(frozen=True)
class RunClaim:
    run_id: str
    routine_id: str
    owner_user_id: str
    lease_generation: int
    lease_expires_at: str


@dataclass(frozen=True)
class RunState:
    run_id: str
    routine_id: str
    status: str
    diagnostic_code: str
    lease_generation: int


def _claim(row: dict) -> RunClaim:
    return RunClaim(
        run_id=str(row["run_id"]),
        routine_id=str(row["routine_id"]),
        owner_user_id=str(row["owner_user_id"]),
        lease_generation=int(row["lease_generation"]),
        lease_expires_at=str(row["lease_expires_at"]),
    )


def _state(row: dict) -> RunState:
    return RunState(
        run_id=str(row["run_id"]),
        routine_id=str(row["routine_id"]),
        status=str(row["status"]),
        diagnostic_code=str(row.get("diagnostic_code") or ""),
        lease_generation=int(row["lease_generation"]),
    )


def _stale(exc: ValueError) -> StaleRoutineLease:
    return StaleRoutineLease("routine lease is no longer current")


class RoutineRunRepository:
    def claim(
        self, run_id: str, *, holder: str, now: datetime | None = None,
    ) -> RunClaim | None:
        row = db_routines.claim_run(run_id, holder=holder, now=now, lease_seconds=90)
        return None if row is None else _claim(row)

    def reclaim(
        self, run_id: str, *, expected_generation: int, holder: str,
        now: datetime | None = None,
    ) -> RunClaim:
        try:
            return _claim(db_routines.reclaim_run(
                run_id, expected_generation=expected_generation, holder=holder,
                now=now, lease_seconds=90,
            ))
        except ValueError as exc:
            raise _stale(exc) from exc

    def assert_current(
        self, run_id: str, *, generation: int, holder: str | None = None,
    ) -> dict:
        try:
            return db_routines.assert_current_run_lease(
                run_id, expected_generation=generation, holder=holder,
            )
        except ValueError as exc:
            raise _stale(exc) from exc

    def renew(self, run_id: str, *, generation: int, holder: str) -> RunClaim:
        try:
            return _claim(db_routines.renew_run_lease(
                run_id, holder=holder, expected_generation=generation, lease_seconds=90,
            ))
        except ValueError as exc:
            raise _stale(exc) from exc

    def get_run(self, run_id: str, *, decrypt_for: str | None = None) -> RunState | dict:
        row = db_routines.get_run(run_id, decrypt_for=decrypt_for)
        if row is None:
            raise KeyError(run_id)
        return row if decrypt_for is not None else _state(row)

    def next_queued_run(self) -> RunState | None:
        row = db_routines.next_queued_run()
        return None if row is None else _state(row)

    def record_tool_dispatch_started(
        self, run_id: str, *, generation: int, call: ToolCall,
        holder: str | None = None, now: datetime | None = None,
    ) -> dict:
        try:
            return db_routines.record_tool_effect_started(
                run_id=run_id, call_id=call.call_id, tool_name=call.name,
                expected_generation=generation, holder=holder, now=now,
            )
        except ValueError as exc:
            raise _stale(exc) from exc

    def settle_tool_dispatch(
        self, run_id: str, *, generation: int, call: ToolCall, succeeded: bool,
        holder: str | None = None,
    ) -> dict:
        try:
            return db_routines.settle_tool_effect(
                run_id=run_id, call_id=call.call_id,
                expected_generation=generation, succeeded=succeeded, holder=holder,
            )
        except ValueError as exc:
            raise _stale(exc) from exc

    def list_open_tool_effects(self, run_id: str) -> list[dict]:
        return db_routines.list_open_tool_effects(run_id)

    def transition(
        self, run_id: str, *, status: str, generation: int,
        result: bytes | None = None, diagnostic_code: str = "",
    ) -> RunState:
        try:
            return _state(db_routines.transition_run(
                run_id, to_status=status, expected_generation=generation,
                result=result, diagnostic_code=diagnostic_code,
            ))
        except ValueError as exc:
            raise _stale(exc) from exc

    def complete_success(
        self, run_id: str, *, generation: int, result: bytes,
        delivery_channel: str | None,
    ) -> RunState:
        try:
            return _state(db_routines.complete_run_success(
                run_id, expected_generation=generation, result=result,
                delivery_channel=delivery_channel,
            ))
        except ValueError as exc:
            raise _stale(exc) from exc

    def get_failure_count(self, routine_id: str) -> int:
        return db_routines.get_execution_failure_count(routine_id)


class _FencedRecorder:
    def __init__(self, recorder: RoutineRunRecorder):
        self._recorder = recorder

    def append(self, *args, **kwargs):
        try:
            return self._recorder.append(*args, **kwargs)
        except ValueError as exc:
            if "stale routine lease" in str(exc):
                raise _stale(exc) from exc
            raise

    def list(self, *args, **kwargs):
        return self._recorder.list(*args, **kwargs)


class _RunSink:
    def __init__(self, recorder: _FencedRecorder, run_id: str, generation: int):
        self.recorder = recorder
        self.run_id = run_id
        self.generation = generation

    def _append(self, kind: str, payload: dict) -> None:
        self.recorder.append(
            self.run_id, kind=kind, payload=payload, generation=self.generation,
        )

    def model_fragment(self, text: str) -> None:
        self._append("model_fragment", {"text": text})

    def tool_requested(self, call: ToolCall) -> None:
        self._append("tool_requested", {"call_id": call.call_id, "name": call.name})

    def approval_requested(self, call: ToolCall) -> None:
        self._append("approval_requested", {"call_id": call.call_id, "name": call.name})

    def tool_result(self, result: ToolResult) -> None:
        self._append("tool_result", {
            "call_id": result.call_id,
            "name": result.name,
            "succeeded": result.succeeded,
            "output": str(result.output),
        })

    def usage(self, usage: UsageRecord) -> None:
        self._append("usage", {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd": usage.cost_usd,
        })


class _LeaseProbe:
    def __init__(self, repository: RoutineRunRepository, claim: RunClaim, holder: str):
        self.repository = repository
        self.claim = claim
        self.holder = holder

    def _check(self) -> None:
        row = self.repository.assert_current(
            self.claim.run_id, generation=self.claim.lease_generation, holder=self.holder,
        )
        expires = datetime.fromisoformat(str(row["lease_expires_at"]))
        if (expires - datetime.now(UTC)).total_seconds() <= 30:
            self.claim = self.repository.renew(
                self.claim.run_id, generation=self.claim.lease_generation, holder=self.holder,
            )

    def check_before_effect(self) -> None:
        self._check()

    def check_between_rounds(self) -> None:
        self._check()


class RoutineRunner:
    def __init__(
        self, *, driver: ModelDriver | None = None,
        tool_executor: Callable[[ToolCall], object] | None = None,
        holder: str | None = None,
    ):
        self.driver = driver
        self.tool_executor = tool_executor
        self.holder = holder or f"routine-worker-{uuid.uuid4().hex}"
        self.repository = RoutineRunRepository()
        self.recorder = _FencedRecorder(RoutineRunRecorder())

    def dispatch_tool(self, run_id: str, *, generation: int, call: ToolCall) -> object:
        self.repository.assert_current(run_id, generation=generation, holder=self.holder)
        self.repository.record_tool_dispatch_started(
            run_id, generation=generation, call=call, holder=self.holder,
        )
        succeeded = False
        try:
            if self.tool_executor is None:
                raise RuntimeError(f"no executor configured for tool {call.name}")
            output = self.tool_executor(call)
            succeeded = True
            return output
        finally:
            self.repository.settle_tool_dispatch(
                run_id, generation=generation, call=call, succeeded=succeeded,
                holder=self.holder,
            )

    def _context(self, row: dict, generation: int) -> RoutineExecutionContext:
        definition = dict(row["definition_snapshot"])
        execution = dict(row.get("execution_context") or {})
        workspace = dict(definition.get("workspace") or {})
        instruction = bytes(definition["instruction"])
        return RoutineExecutionContext(
            run_id=str(row["run_id"]),
            routine_id=str(row["routine_id"]),
            routine_version=int(row["routine_version"]),
            owner_user_id=str(row["owner_user_id"]),
            access_scope=AccessScope(str(row["access_scope"])),
            instruction_ref=f"routine:{row['routine_id']}:v{row['routine_version']}",
            instruction_hash=hashlib.sha256(instruction).hexdigest(),
            trigger_inputs=execution,
            workspace_name=str(workspace.get("name") or ""),
            workspace_kind=str(workspace.get("kind") or ""),
            workspace_root=str(workspace.get("root") or ""),
            capability_scope=str(definition["capability_scope"]),
            permission_policy=dict(definition.get("permission_policy") or {}),
            approval_policy=dict(execution.get("approval_policy") or {}),
            provider=str(execution.get("provider") or ""),
            model=str(execution.get("model") or ""),
            lease_generation=generation,
        )

    def run_once(self, run_id: str) -> ExecutionResult:
        claim = self.repository.claim(run_id, holder=self.holder)
        if claim is None:
            raise StaleRoutineLease("routine run is not claimable")
        row = self.repository.get_run(run_id, decrypt_for=claim.owner_user_id)
        context = self._context(row, claim.lease_generation)
        instruction = bytes(row["definition_snapshot"]["instruction"])
        adapter = RoutineExecutionAdapter(
            context,
            instruction=instruction,
            driver=self.driver,
            tool_executor=lambda call: self.dispatch_tool(
                run_id, generation=claim.lease_generation, call=call,
            ),
        )
        result = execute_agentic(
            adapter,
            _RunSink(self.recorder, run_id, claim.lease_generation),
            _LeaseProbe(self.repository, claim, self.holder),
        )
        if result.status == "succeeded":
            delivery_policy = dict(row["definition_snapshot"].get("delivery_policy") or {})
            channel = str(delivery_policy.get("channel") or "desk").strip().lower()
            self.repository.complete_success(
                run_id, generation=claim.lease_generation,
                result=result.text.encode("utf-8"), delivery_channel=channel,
            )
            self.record_execution_success(claim.routine_id)
        elif result.status == "waiting_approval":
            self.repository.transition(
                run_id, status="failed", generation=claim.lease_generation,
                result=result.text.encode("utf-8"), diagnostic_code="action_required",
            )
            from core.services.routine_inbox import project_event_to_inbox

            project_event_to_inbox({
                "owner_user_id": claim.owner_user_id,
                "routine_id": claim.routine_id,
                "event_id": f"{run_id}:action-required",
                "event_type": "action_required",
            })
        else:
            code = result.error_code or result.status
            self.repository.transition(
                run_id, status="failed", generation=claim.lease_generation,
                result=result.text.encode("utf-8"), diagnostic_code=code,
            )
            from core.services.routine_inbox import project_event_to_inbox

            project_event_to_inbox({
                "owner_user_id": claim.owner_user_id,
                "routine_id": claim.routine_id,
                "event_id": f"{run_id}:failed",
                "event_type": "failed",
            })
            publish_operational_failure(
                routine_id=claim.routine_id, run_id=run_id, component="runner",
            )
            self.record_execution_failure(claim.routine_id, run_id=run_id)
        return result

    def run_next(self) -> ExecutionResult | None:
        run = self.repository.next_queued_run()
        return None if run is None else self.run_once(run.run_id)

    def cancel(self, run_id: str) -> RunState:
        return _state(db_routines.cancel_run(run_id))

    def record_execution_success(self, routine_id: str) -> None:
        db_routines.update_execution_failure_count(routine_id, success=True)

    def record_execution_failure(self, routine_id: str, *, run_id: str) -> int:
        count = db_routines.update_execution_failure_count(routine_id, success=False)
        routine = db_routines.get_routine(routine_id)
        if routine is None:
            raise KeyError(routine_id)
        private = db_routines.get_routine(
            routine_id, decrypt_for=str(routine["owner_user_id"]),
        )
        threshold = int(dict(private.get("failure_policy") or {}).get(
            "consecutive_failures", 3,
        ))
        if count >= max(1, threshold) and routine["status"] == "active":
            db_routines.transition_routine(routine_id, to_status="paused")
            from core.services.routine_inbox import project_event_to_inbox

            project_event_to_inbox({
                "owner_user_id": routine["owner_user_id"],
                "routine_id": routine_id,
                "event_id": f"{run_id}:failure-threshold",
                "event_type": "auto_paused",
            })
        return count
