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
| class | `ExecutionResult` | `` | — | [src](../../../core/services/agentic_execution.py#L72) |
| class | `ModelDriver` | `` | — | [src](../../../core/services/agentic_execution.py#L82) |
| method | `ModelDriver.complete` | `(self, request)` | — | [src](../../../core/services/agentic_execution.py#L83) |
| class | `ExecutionSink` | `` | — | [src](../../../core/services/agentic_execution.py#L86) |
| method | `ExecutionSink.model_fragment` | `(self, text)` | — | [src](../../../core/services/agentic_execution.py#L87) |
| method | `ExecutionSink.tool_requested` | `(self, call)` | — | [src](../../../core/services/agentic_execution.py#L88) |
| method | `ExecutionSink.tool_result` | `(self, result)` | — | [src](../../../core/services/agentic_execution.py#L89) |
| method | `ExecutionSink.usage` | `(self, usage)` | — | [src](../../../core/services/agentic_execution.py#L90) |
| class | `CancellationProbe` | `` | — | [src](../../../core/services/agentic_execution.py#L93) |
| method | `CancellationProbe.check_before_effect` | `(self)` | — | [src](../../../core/services/agentic_execution.py#L94) |
| method | `CancellationProbe.check_between_rounds` | `(self)` | — | [src](../../../core/services/agentic_execution.py#L95) |
| class | `ExecutionContext` | `` | — | [src](../../../core/services/agentic_execution.py#L98) |
| function | `_normalisér_tool_calls` | `(raw)` | Provider-svarets ``tool_calls`` → ``ToolCall``. | [src](../../../core/services/agentic_execution.py#L108) |
| class | `_ProviderDriver` | `` | Production bridge to the existing provider router without UI state. | [src](../../../core/services/agentic_execution.py#L144) |
| method | `_ProviderDriver.complete` | `(self, request)` | — | [src](../../../core/services/agentic_execution.py#L147) |
| function | `_no_tool_executor` | `(call)` | — | [src](../../../core/services/agentic_execution.py#L216) |
| class | `VisibleExecutionAdapter` | `` | — | [src](../../../core/services/agentic_execution.py#L221) |
| class | `RoutineExecutionAdapter` | `` | — | [src](../../../core/services/agentic_execution.py#L230) |
| method | `RoutineExecutionAdapter.__init__` | `(self, context, *, instruction, driver=…, tool_executor=…, tools_payload=…, max_rounds=…)` | — | [src](../../../core/services/agentic_execution.py#L231) |
| function | `_emit_terminal` | `(sink, result)` | — | [src](../../../core/services/agentic_execution.py#L252) |
| function | `_approval` | `(sink, call)` | — | [src](../../../core/services/agentic_execution.py#L259) |
| function | `execute_agentic` | `(context, sink, cancellation)` | Run bounded model/tool rounds and emit exactly one terminal result. | [src](../../../core/services/agentic_execution.py#L265) |

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
| method | `RoutineReconciler.sweep_retention` | `(self, now=…)` | — | [src](../../../core/services/routine_reconciler.py#L44) |

## `core/services/routine_runner.py`
_Fenced, session-neutral execution of one Routine run._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `publish_operational_failure` | `(*, routine_id, run_id, component)` | Best-effort fixed-schema projection; never expose execution content. | [src](../../../core/services/routine_runner.py#L29) |
| class | `StaleRoutineLease` | `` | The worker no longer owns the run generation. | [src](../../../core/services/routine_runner.py#L46) |
| class | `RunClaim` | `` | — | [src](../../../core/services/routine_runner.py#L51) |
| class | `RunState` | `` | — | [src](../../../core/services/routine_runner.py#L60) |
| function | `_claim` | `(row)` | — | [src](../../../core/services/routine_runner.py#L68) |
| function | `_state` | `(row)` | — | [src](../../../core/services/routine_runner.py#L78) |
| function | `_stale` | `(exc)` | — | [src](../../../core/services/routine_runner.py#L88) |
| function | `_standard_provider` | `()` | Modellen et rutine-run bruger når rutinen ikke selv peger på én. | [src](../../../core/services/routine_runner.py#L106) |
| function | `_standard_model` | `()` | Se :func:`_standard_provider` — samme måling, samme grund. | [src](../../../core/services/routine_runner.py#L130) |
| function | `_rutine_tools_payload` | `(context)` | Værktøjsskemaet denne rutine må byde modellen. Tom = værktøjs-fri. | [src](../../../core/services/routine_runner.py#L174) |
| function | `_ejer_kontekst` | `(owner_user_id, *, run_id=…)` | Kør blokken som rutinens ejer: workspace, oprindelse og autonomi. | [src](../../../core/services/routine_runner.py#L205) |
| function | `build_tool_executor` | `(owner_user_id, *, run_id=…)` | Executor for ét rutine-run, scopet til rutinens ejer. | [src](../../../core/services/routine_runner.py#L248) |
| class | `RoutineRunRepository` | `` | — | [src](../../../core/services/routine_runner.py#L283) |
| method | `RoutineRunRepository.claim` | `(self, run_id, *, holder, now=…)` | — | [src](../../../core/services/routine_runner.py#L284) |
| method | `RoutineRunRepository.reclaim` | `(self, run_id, *, expected_generation, holder, now=…)` | — | [src](../../../core/services/routine_runner.py#L290) |
| method | `RoutineRunRepository.assert_current` | `(self, run_id, *, generation, holder=…)` | — | [src](../../../core/services/routine_runner.py#L302) |
| method | `RoutineRunRepository.renew` | `(self, run_id, *, generation, holder)` | — | [src](../../../core/services/routine_runner.py#L312) |
| method | `RoutineRunRepository.get_run` | `(self, run_id, *, decrypt_for=…)` | — | [src](../../../core/services/routine_runner.py#L320) |
| method | `RoutineRunRepository.next_queued_run` | `(self)` | — | [src](../../../core/services/routine_runner.py#L326) |
| method | `RoutineRunRepository.record_tool_dispatch_started` | `(self, run_id, *, generation, call, holder=…, now=…)` | — | [src](../../../core/services/routine_runner.py#L330) |
| method | `RoutineRunRepository.settle_tool_dispatch` | `(self, run_id, *, generation, call, succeeded, holder=…)` | — | [src](../../../core/services/routine_runner.py#L342) |
| method | `RoutineRunRepository.list_open_tool_effects` | `(self, run_id)` | — | [src](../../../core/services/routine_runner.py#L354) |
| method | `RoutineRunRepository.transition` | `(self, run_id, *, status, generation, result=…, diagnostic_code=…)` | — | [src](../../../core/services/routine_runner.py#L357) |
| method | `RoutineRunRepository.complete_success` | `(self, run_id, *, generation, result, delivery_channel)` | — | [src](../../../core/services/routine_runner.py#L369) |
| method | `RoutineRunRepository.get_failure_count` | `(self, routine_id)` | — | [src](../../../core/services/routine_runner.py#L381) |
| class | `_FencedRecorder` | `` | — | [src](../../../core/services/routine_runner.py#L385) |
| method | `_FencedRecorder.__init__` | `(self, recorder)` | — | [src](../../../core/services/routine_runner.py#L386) |
| method | `_FencedRecorder.append` | `(self, *args, **kwargs)` | — | [src](../../../core/services/routine_runner.py#L389) |
| method | `_FencedRecorder.list` | `(self, *args, **kwargs)` | — | [src](../../../core/services/routine_runner.py#L397) |
| class | `_RunSink` | `` | — | [src](../../../core/services/routine_runner.py#L401) |
| method | `_RunSink.__init__` | `(self, recorder, run_id, generation)` | — | [src](../../../core/services/routine_runner.py#L402) |
| method | `_RunSink._append` | `(self, kind, payload)` | — | [src](../../../core/services/routine_runner.py#L407) |
| method | `_RunSink.model_fragment` | `(self, text)` | — | [src](../../../core/services/routine_runner.py#L412) |
| method | `_RunSink.tool_requested` | `(self, call)` | — | [src](../../../core/services/routine_runner.py#L415) |
| method | `_RunSink.approval_requested` | `(self, call)` | — | [src](../../../core/services/routine_runner.py#L418) |
| method | `_RunSink.tool_result` | `(self, result)` | — | [src](../../../core/services/routine_runner.py#L421) |
| method | `_RunSink.usage` | `(self, usage)` | — | [src](../../../core/services/routine_runner.py#L429) |
| class | `_LeaseProbe` | `` | — | [src](../../../core/services/routine_runner.py#L437) |
| method | `_LeaseProbe.__init__` | `(self, repository, claim, holder)` | — | [src](../../../core/services/routine_runner.py#L438) |
| method | `_LeaseProbe._check` | `(self)` | — | [src](../../../core/services/routine_runner.py#L443) |
| method | `_LeaseProbe.check_before_effect` | `(self)` | — | [src](../../../core/services/routine_runner.py#L453) |
| method | `_LeaseProbe.check_between_rounds` | `(self)` | — | [src](../../../core/services/routine_runner.py#L456) |
| class | `RoutineRunner` | `` | — | [src](../../../core/services/routine_runner.py#L460) |
| method | `RoutineRunner.__init__` | `(self, *, driver=…, tool_executor=…, holder=…)` | — | [src](../../../core/services/routine_runner.py#L461) |
| method | `RoutineRunner.dispatch_tool` | `(self, run_id, *, generation, call, raw_executor=…)` | — | [src](../../../core/services/routine_runner.py#L472) |
| method | `RoutineRunner._context` | `(self, row, generation)` | — | [src](../../../core/services/routine_runner.py#L494) |
| method | `RoutineRunner.run_once` | `(self, run_id)` | — | [src](../../../core/services/routine_runner.py#L519) |
| method | `RoutineRunner.run_next` | `(self)` | — | [src](../../../core/services/routine_runner.py#L589) |
| method | `RoutineRunner.cancel` | `(self, run_id)` | — | [src](../../../core/services/routine_runner.py#L593) |
| method | `RoutineRunner.record_execution_success` | `(self, routine_id)` | — | [src](../../../core/services/routine_runner.py#L596) |
| method | `RoutineRunner.record_execution_failure` | `(self, routine_id, *, run_id)` | — | [src](../../../core/services/routine_runner.py#L599) |

## `core/services/routine_runtime.py`
_Bounded worker and reconciler threads for Routines._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineRuntime` | `` | — | [src](../../../core/services/routine_runtime.py#L16) |
| method | `RoutineRuntime.__init__` | `(self, *, runner=…, reconciler=…, delivery=…, poll_seconds=…, reconcile_seconds=…, scheduler_seconds=…)` | — | [src](../../../core/services/routine_runtime.py#L17) |
| method | `RoutineRuntime._worker_loop` | `(self)` | — | [src](../../../core/services/routine_runtime.py#L39) |
| method | `RoutineRuntime._reconciler_loop` | `(self)` | — | [src](../../../core/services/routine_runtime.py#L67) |
| method | `RoutineRuntime.start` | `(self)` | — | [src](../../../core/services/routine_runtime.py#L79) |
| method | `RoutineRuntime.stop` | `(self, *, timeout_seconds=…)` | — | [src](../../../core/services/routine_runtime.py#L92) |
| method | `RoutineRuntime.worker_is_alive` | `(self)` | — | [src](../../../core/services/routine_runtime.py#L98) |
| method | `RoutineRuntime.reconciler_is_alive` | `(self)` | — | [src](../../../core/services/routine_runtime.py#L101) |
| method | `RoutineRuntime.claim_count_after_stop` | `(self)` | — | [src](../../../core/services/routine_runtime.py#L104) |
| function | `start_routine_runtime` | `()` | — | [src](../../../core/services/routine_runtime.py#L112) |
| function | `stop_routine_runtime` | `(*, timeout_seconds=…)` | — | [src](../../../core/services/routine_runtime.py#L121) |

## `core/services/routine_trigger_adapters.py`
_Single-path adapters from legacy producers to isolated Routine runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `UnmigratedRoutineSource` | `` | The cutover is enabled but this legacy source has no verified Routine. | [src](../../../core/services/routine_trigger_adapters.py#L18) |
| class | `UnknownSystemProducer` | `` | A producer not present in the explicit system-only registry was requested. | [src](../../../core/services/routine_trigger_adapters.py#L22) |
| class | `TriggerResult` | `` | — | [src](../../../core/services/routine_trigger_adapters.py#L27) |
| function | `_cutover_tokens` | `()` | Env-værdien som mængde: globale sandheds-ord ELLER ``kind:id``-par. | [src](../../../core/services/routine_trigger_adapters.py#L35) |
| function | `routine_cutover_enabled` | `()` | GLOBAL cutover — sand kun når env siger det uden at pege på enkeltkilder. | [src](../../../core/services/routine_trigger_adapters.py#L49) |
| function | `cutover_allows` | `(source_kind, source_id)` | Må netop DENNE kilde gå Routine-vejen? | [src](../../../core/services/routine_trigger_adapters.py#L58) |
| function | `_runner_principal` | `()` | — | [src](../../../core/services/routine_trigger_adapters.py#L73) |
| class | `RoutineTriggerAdapters` | `` | — | [src](../../../core/services/routine_trigger_adapters.py#L77) |
| method | `RoutineTriggerAdapters.__init__` | `(self, *, system_owner_user_id=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L78) |
| method | `RoutineTriggerAdapters._enqueue` | `(self, routine_id, *, trigger_key, execution_context=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L82) |
| method | `RoutineTriggerAdapters._linked` | `(self, source_kind, source_id)` | — | [src](../../../core/services/routine_trigger_adapters.py#L94) |
| method | `RoutineTriggerAdapters.enqueue_scheduled` | `(self, source_id)` | — | [src](../../../core/services/routine_trigger_adapters.py#L104) |
| method | `RoutineTriggerAdapters.enqueue_recurring` | `(self, source_id, *, occurrence_id=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L110) |
| method | `RoutineTriggerAdapters._owner` | `(self)` | — | [src](../../../core/services/routine_trigger_adapters.py#L118) |
| method | `RoutineTriggerAdapters._system_routine` | `(self, producer)` | — | [src](../../../core/services/routine_trigger_adapters.py#L129) |
| method | `RoutineTriggerAdapters.enqueue_system` | `(self, producer, source_id, *, trigger_inputs=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L153) |
| method | `RoutineTriggerAdapters.fire` | `(self, producer, *, source_id)` | — | [src](../../../core/services/routine_trigger_adapters.py#L163) |
| function | `enqueue_scheduled` | `(source_id)` | — | [src](../../../core/services/routine_trigger_adapters.py#L171) |
| function | `enqueue_recurring` | `(source_id, *, occurrence_id=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L175) |
| function | `enqueue_system` | `(producer, source_id, *, trigger_inputs=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L183) |
| function | `dispatch_recurring` | `(source_id, *, legacy, adapters=…, occurrence_id=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L192) |
| function | `dispatch_scheduled` | `(source_id, *, legacy, adapters=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L205) |
| function | `dispatch_system` | `(producer, source_id, *, trigger_inputs, legacy, adapters=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L215) |
| function | `dispatch_heartbeat_initiative` | `(*, focus, initiative_id, session_id=…)` | Extracted heartbeat execution boundary for the oversized runtime module. | [src](../../../core/services/routine_trigger_adapters.py#L230) |

