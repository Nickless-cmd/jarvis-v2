"""Fenced, session-neutral execution of one Routine run."""
from __future__ import annotations

import hashlib
import logging
import uuid
from contextlib import contextmanager
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


# ── Værktøjsadgang for en rutine ─────────────────────────────────────────────
#
# Målt 25/10-2026: et rutine-run svarede «jeg har ikke adgang til et
# madopskrift-værktøj» med ``input_tokens=0``. Årsagen var ikke modellen men
# TRE led der alle manglede: ``RoutineRuntime`` byggede ``RoutineRunner()``
# uden executor, ``_ProviderDriver`` sendte ``requires_tools=False`` og læste
# aldrig ``tool_calls`` tilbage, og en rutine havde ingen oprindelse i
# værktøjspolitikken. De tre er rettet hver for sig; her bindes de sammen.
#
# Executoren er bundet til rutinens EJER, ikke til processen der kører den.
# Uden det ville Michelles rutine læse i Bjørns workspace — samme lækage som
# ``fire_session_id`` havde, blot i værktøjsvejen.


def _rutine_tools_payload(context: RoutineExecutionContext) -> list[dict]:
    """Værktøjsskemaet denne rutine må byde modellen. Tom = værktøjs-fri."""
    if str(getattr(context, "capability_scope", "") or "") == "system":
        # Systemrutiner (heartbeat/dream) er rammer, ikke opgaver: de skal ikke
        # kunne nå ud i verden. De beholder den værktøjs-fri adfærd.
        return []
    try:
        from core.tools.autonomous_tool_policy import allowed_tools_for_origin
        from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    except Exception:  # noqa: BLE001 — et manglende skema må ikke vælte kørslen
        _log.warning("rutine: kunne ikke indlæse værktøjsskemaet", exc_info=True)
        return []
    tilladte = allowed_tools_for_origin("routine")
    return [
        definition for definition in TOOL_DEFINITIONS
        if str((definition.get("function") or {}).get("name") or "") in tilladte
    ]


@contextmanager
def _ejer_kontekst(owner_user_id: str, *, run_id: str = ""):
    """Kør blokken som rutinens ejer: workspace, oprindelse og autonomi.

    Workspacet slås op på det KANONISKE id via ``get_user``. ``workspace_dir``
    kan ikke bruges her — den kræver et Discord-id og nægter ellers (målt
    25/10-2026), så et rutine-run ville fejle på kontekst frem for på arbejde.
    """
    from core.services import run_autonomy_context as autonomy
    from core.identity.workspace_context import reset_context, set_context

    workspace = ""
    try:
        from core.identity.user_db import get_user

        bruger = get_user(owner_user_id) or {}
        workspace = str(bruger.get("workspace") or "").strip()
    except Exception:  # noqa: BLE001 — kontekst er et gode, ikke en forudsætning
        _log.warning("rutine: kunne ikke slå workspace op for ejeren", exc_info=True)

    ws_token = None
    if workspace:
        ws_token = set_context(workspace_name=workspace, user_id=owner_user_id)
    aut_token = autonomy.set_autonomous(True)
    autonomy.set_run_identity(run_id or "routine", origin="routine")
    presence_token = autonomy.set_user_present(False)
    try:
        yield
    finally:
        try:
            autonomy.reset_user_present(presence_token)
        except Exception:  # noqa: BLE001
            pass
        try:
            autonomy.reset_autonomous(aut_token)
        except Exception:  # noqa: BLE001
            pass
        if ws_token is not None:
            try:
                reset_context(ws_token)
            except Exception:  # noqa: BLE001
                pass


def build_tool_executor(owner_user_id: str, *, run_id: str = "") -> Callable[[ToolCall], object]:
    """Executor for ét rutine-run, scopet til rutinens ejer.

    ``execute_tool_force`` bruges fordi et rutine-run er forhåndsgodkendt af
    sin ejer: der findes ingen dialog at parkere i. Politikken håndhæves
    stadig — ``is_allowed`` siger nej til alt uden for rutinens sæt, og et
    destruktivt kald rammer fortsat sin egen gate.
    """

    def _executér(call: ToolCall) -> object:
        from core.tools.simple_tools import execute_tool_force
        from core.tools.tool_result_format import format_tool_result_for_model

        with _ejer_kontekst(owner_user_id, run_id=run_id):
            from core.tools.autonomous_tool_policy import is_allowed

            if not is_allowed(call.name):
                return (
                    f"[Tool {call.name} error: ikke tilladt i en rutine-kørsel]"
                )
            try:
                raw = execute_tool_force(call.name, dict(call.arguments or {}))
            except Exception as exc:  # noqa: BLE001 — fejlen skal til MODELLEN
                return f"[Tool {call.name} error: {type(exc).__name__}: {exc}]"
        if not isinstance(raw, dict):
            raw = {"status": "ok", "text": str(raw)}
        if str(raw.get("status") or "") == "approval_needed":
            # En rutine har ingen at spørge. At parkere kørslen ville efterlade
            # den halvt udført uden nogen der kan frigive den.
            return f"[Tool {call.name} kræver godkendelse — ikke muligt i en rutine]"
        return format_tool_result_for_model(call.name, raw)

    return _executér


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

    def dispatch_tool(
        self, run_id: str, *, generation: int, call: ToolCall,
        raw_executor: Callable[[ToolCall], object] | None = None,
    ) -> object:
        self.repository.assert_current(run_id, generation=generation, holder=self.holder)
        self.repository.record_tool_dispatch_started(
            run_id, generation=generation, call=call, holder=self.holder,
        )
        succeeded = False
        try:
            executor = raw_executor or self.tool_executor
            if executor is None:
                raise RuntimeError(f"no executor configured for tool {call.name}")
            output = executor(call)
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
        tools_payload = _rutine_tools_payload(context)
        # Den RÅ executor (ejer-scopet) leveres ind til ``dispatch_tool``, som
        # stadig ejer lease-tjekket og værktøjs-events. Uden den omvej ville et
        # værktøjskald kunne køre efter at leasen var udløbet.
        raw_executor = self.tool_executor
        if raw_executor is None and tools_payload:
            raw_executor = build_tool_executor(claim.owner_user_id, run_id=run_id)
        adapter = RoutineExecutionAdapter(
            context,
            instruction=instruction,
            driver=self.driver,
            tool_executor=lambda call: self.dispatch_tool(
                run_id, generation=claim.lease_generation, call=call,
                raw_executor=raw_executor,
            ),
            tools_payload=tools_payload,
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
