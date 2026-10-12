# `core.services.routine-execution` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/agentic_execution.py`
_A transport-neutral, fenced model/tool execution loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ToolCall` | `` | — | [src](../../../core/services/agentic_execution.py#L17) |
| class | `ToolResult` | `` | — | [src](../../../core/services/agentic_execution.py#L25) |
| class | `UsageRecord` | `` | — | [src](../../../core/services/agentic_execution.py#L33) |
| method | `UsageRecord.plus` | `(self, other)` | — | [src](../../../core/services/agentic_execution.py#L38) |
| class | `AgenticTurn` | `` | — | [src](../../../core/services/agentic_execution.py#L47) |
| class | `AgenticRequest` | `` | — | [src](../../../core/services/agentic_execution.py#L56) |
| class | `ExecutionResult` | `` | — | [src](../../../core/services/agentic_execution.py#L65) |
| class | `ModelDriver` | `` | — | [src](../../../core/services/agentic_execution.py#L75) |
| method | `ModelDriver.complete` | `(self, request)` | — | [src](../../../core/services/agentic_execution.py#L76) |
| class | `ExecutionSink` | `` | — | [src](../../../core/services/agentic_execution.py#L79) |
| method | `ExecutionSink.model_fragment` | `(self, text)` | — | [src](../../../core/services/agentic_execution.py#L80) |
| method | `ExecutionSink.tool_requested` | `(self, call)` | — | [src](../../../core/services/agentic_execution.py#L81) |
| method | `ExecutionSink.tool_result` | `(self, result)` | — | [src](../../../core/services/agentic_execution.py#L82) |
| method | `ExecutionSink.usage` | `(self, usage)` | — | [src](../../../core/services/agentic_execution.py#L83) |
| class | `CancellationProbe` | `` | — | [src](../../../core/services/agentic_execution.py#L86) |
| method | `CancellationProbe.check_before_effect` | `(self)` | — | [src](../../../core/services/agentic_execution.py#L87) |
| method | `CancellationProbe.check_between_rounds` | `(self)` | — | [src](../../../core/services/agentic_execution.py#L88) |
| class | `ExecutionContext` | `` | — | [src](../../../core/services/agentic_execution.py#L91) |
| class | `_ProviderDriver` | `` | Production bridge to the existing provider router without UI state. | [src](../../../core/services/agentic_execution.py#L100) |
| method | `_ProviderDriver.complete` | `(self, request)` | — | [src](../../../core/services/agentic_execution.py#L103) |
| function | `_no_tool_executor` | `(call)` | — | [src](../../../core/services/agentic_execution.py#L137) |
| class | `VisibleExecutionAdapter` | `` | — | [src](../../../core/services/agentic_execution.py#L142) |
| class | `RoutineExecutionAdapter` | `` | — | [src](../../../core/services/agentic_execution.py#L151) |
| method | `RoutineExecutionAdapter.__init__` | `(self, context, *, instruction, driver=…, tool_executor=…, max_rounds=…)` | — | [src](../../../core/services/agentic_execution.py#L152) |
| function | `_emit_terminal` | `(sink, result)` | — | [src](../../../core/services/agentic_execution.py#L170) |
| function | `_approval` | `(sink, call)` | — | [src](../../../core/services/agentic_execution.py#L177) |
| function | `execute_agentic` | `(context, sink, cancellation)` | Run bounded model/tool rounds and emit exactly one terminal result. | [src](../../../core/services/agentic_execution.py#L183) |

## `core/services/routine_prompt.py`
_Build a bounded Routine prompt directly from its immutable execution context._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_routine_prompt` | `(context, *, instruction)` | Return the execution prompt without consulting conversation state. | [src](../../../core/services/routine_prompt.py#L9) |

## `core/services/routine_reconciler.py`
_Crash reconciliation and retention sweeps for Routine work._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineReconciler` | `` | — | [src](../../../core/services/routine_reconciler.py#L10) |
| method | `RoutineReconciler.__init__` | `(self, *, repository=…)` | — | [src](../../../core/services/routine_reconciler.py#L11) |
| method | `RoutineReconciler.reconcile_once` | `(self, now=…)` | — | [src](../../../core/services/routine_reconciler.py#L18) |
| method | `RoutineReconciler.sweep_retention` | `(self, now=…)` | — | [src](../../../core/services/routine_reconciler.py#L22) |

## `core/services/routine_runner.py`
_Fenced, session-neutral execution of one Routine run._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `StaleRoutineLease` | `` | The worker no longer owns the run generation. | [src](../../../core/services/routine_runner.py#L24) |
| class | `RunClaim` | `` | — | [src](../../../core/services/routine_runner.py#L29) |
| class | `RunState` | `` | — | [src](../../../core/services/routine_runner.py#L38) |
| function | `_claim` | `(row)` | — | [src](../../../core/services/routine_runner.py#L46) |
| function | `_state` | `(row)` | — | [src](../../../core/services/routine_runner.py#L56) |
| function | `_stale` | `(exc)` | — | [src](../../../core/services/routine_runner.py#L66) |
| class | `RoutineRunRepository` | `` | — | [src](../../../core/services/routine_runner.py#L70) |
| method | `RoutineRunRepository.claim` | `(self, run_id, *, holder, now=…)` | — | [src](../../../core/services/routine_runner.py#L71) |
| method | `RoutineRunRepository.reclaim` | `(self, run_id, *, expected_generation, holder, now=…)` | — | [src](../../../core/services/routine_runner.py#L77) |
| method | `RoutineRunRepository.assert_current` | `(self, run_id, *, generation, holder=…)` | — | [src](../../../core/services/routine_runner.py#L89) |
| method | `RoutineRunRepository.renew` | `(self, run_id, *, generation, holder)` | — | [src](../../../core/services/routine_runner.py#L99) |
| method | `RoutineRunRepository.get_run` | `(self, run_id, *, decrypt_for=…)` | — | [src](../../../core/services/routine_runner.py#L107) |
| method | `RoutineRunRepository.next_queued_run` | `(self)` | — | [src](../../../core/services/routine_runner.py#L113) |
| method | `RoutineRunRepository.record_tool_dispatch_started` | `(self, run_id, *, generation, call, holder=…, now=…)` | — | [src](../../../core/services/routine_runner.py#L117) |
| method | `RoutineRunRepository.settle_tool_dispatch` | `(self, run_id, *, generation, call, succeeded, holder=…)` | — | [src](../../../core/services/routine_runner.py#L129) |
| method | `RoutineRunRepository.list_open_tool_effects` | `(self, run_id)` | — | [src](../../../core/services/routine_runner.py#L141) |
| method | `RoutineRunRepository.transition` | `(self, run_id, *, status, generation, result=…, diagnostic_code=…)` | — | [src](../../../core/services/routine_runner.py#L144) |
| method | `RoutineRunRepository.get_failure_count` | `(self, routine_id)` | — | [src](../../../core/services/routine_runner.py#L156) |
| class | `_FencedRecorder` | `` | — | [src](../../../core/services/routine_runner.py#L160) |
| method | `_FencedRecorder.__init__` | `(self, recorder)` | — | [src](../../../core/services/routine_runner.py#L161) |
| method | `_FencedRecorder.append` | `(self, *args, **kwargs)` | — | [src](../../../core/services/routine_runner.py#L164) |
| method | `_FencedRecorder.list` | `(self, *args, **kwargs)` | — | [src](../../../core/services/routine_runner.py#L172) |
| class | `_RunSink` | `` | — | [src](../../../core/services/routine_runner.py#L176) |
| method | `_RunSink.__init__` | `(self, recorder, run_id, generation)` | — | [src](../../../core/services/routine_runner.py#L177) |
| method | `_RunSink._append` | `(self, kind, payload)` | — | [src](../../../core/services/routine_runner.py#L182) |
| method | `_RunSink.model_fragment` | `(self, text)` | — | [src](../../../core/services/routine_runner.py#L187) |
| method | `_RunSink.tool_requested` | `(self, call)` | — | [src](../../../core/services/routine_runner.py#L190) |
| method | `_RunSink.tool_result` | `(self, result)` | — | [src](../../../core/services/routine_runner.py#L193) |
| method | `_RunSink.usage` | `(self, usage)` | — | [src](../../../core/services/routine_runner.py#L201) |
| class | `_LeaseProbe` | `` | — | [src](../../../core/services/routine_runner.py#L209) |
| method | `_LeaseProbe.__init__` | `(self, repository, claim, holder)` | — | [src](../../../core/services/routine_runner.py#L210) |
| method | `_LeaseProbe._check` | `(self)` | — | [src](../../../core/services/routine_runner.py#L215) |
| method | `_LeaseProbe.check_before_effect` | `(self)` | — | [src](../../../core/services/routine_runner.py#L225) |
| method | `_LeaseProbe.check_between_rounds` | `(self)` | — | [src](../../../core/services/routine_runner.py#L228) |
| class | `RoutineRunner` | `` | — | [src](../../../core/services/routine_runner.py#L232) |
| method | `RoutineRunner.__init__` | `(self, *, driver=…, tool_executor=…, holder=…)` | — | [src](../../../core/services/routine_runner.py#L233) |
| method | `RoutineRunner.dispatch_tool` | `(self, run_id, *, generation, call)` | — | [src](../../../core/services/routine_runner.py#L244) |
| method | `RoutineRunner._context` | `(self, row, generation)` | — | [src](../../../core/services/routine_runner.py#L262) |
| method | `RoutineRunner.run_once` | `(self, run_id)` | — | [src](../../../core/services/routine_runner.py#L287) |
| method | `RoutineRunner.run_next` | `(self)` | — | [src](../../../core/services/routine_runner.py#L322) |
| method | `RoutineRunner.cancel` | `(self, run_id)` | — | [src](../../../core/services/routine_runner.py#L326) |
| method | `RoutineRunner.record_execution_success` | `(self, routine_id)` | — | [src](../../../core/services/routine_runner.py#L329) |
| method | `RoutineRunner.record_execution_failure` | `(self, routine_id, *, run_id)` | — | [src](../../../core/services/routine_runner.py#L332) |

## `core/services/routine_runtime.py`
_Bounded worker and reconciler threads for Routines._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineRuntime` | `` | — | [src](../../../core/services/routine_runtime.py#L15) |
| method | `RoutineRuntime.__init__` | `(self, *, runner=…, reconciler=…, poll_seconds=…, reconcile_seconds=…)` | — | [src](../../../core/services/routine_runtime.py#L16) |
| method | `RoutineRuntime._worker_loop` | `(self)` | — | [src](../../../core/services/routine_runtime.py#L29) |
| method | `RoutineRuntime._reconciler_loop` | `(self)` | — | [src](../../../core/services/routine_runtime.py#L37) |
| method | `RoutineRuntime.start` | `(self)` | — | [src](../../../core/services/routine_runtime.py#L49) |
| method | `RoutineRuntime.stop` | `(self, *, timeout_seconds=…)` | — | [src](../../../core/services/routine_runtime.py#L62) |
| method | `RoutineRuntime.worker_is_alive` | `(self)` | — | [src](../../../core/services/routine_runtime.py#L68) |
| method | `RoutineRuntime.reconciler_is_alive` | `(self)` | — | [src](../../../core/services/routine_runtime.py#L71) |
| method | `RoutineRuntime.claim_count_after_stop` | `(self)` | — | [src](../../../core/services/routine_runtime.py#L74) |
| function | `start_routine_runtime` | `()` | — | [src](../../../core/services/routine_runtime.py#L82) |
| function | `stop_routine_runtime` | `(*, timeout_seconds=…)` | — | [src](../../../core/services/routine_runtime.py#L91) |

