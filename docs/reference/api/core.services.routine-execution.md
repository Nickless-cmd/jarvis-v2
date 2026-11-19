# `core.services.routine-execution` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/agentic_execution.py`
_A transport-neutral, fenced model/tool execution loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ToolCall` | `` | — | [src](../../../core/services/agentic_execution.py#L17) |
| class | `ToolResult` | `` | — | [src](../../../core/services/agentic_execution.py#L25) |
| class | `UsageRecord` | `` | — | [src](../../../core/services/agentic_execution.py#L38) |
| method | `UsageRecord.plus` | `(self, other)` | — | [src](../../../core/services/agentic_execution.py#L43) |
| class | `AgenticTurn` | `` | — | [src](../../../core/services/agentic_execution.py#L52) |
| class | `AgenticRequest` | `` | — | [src](../../../core/services/agentic_execution.py#L61) |
| class | `ExecutionResult` | `` | — | [src](../../../core/services/agentic_execution.py#L77) |
| class | `ModelDriver` | `` | — | [src](../../../core/services/agentic_execution.py#L87) |
| method | `ModelDriver.complete` | `(self, request)` | — | [src](../../../core/services/agentic_execution.py#L88) |
| class | `ExecutionSink` | `` | — | [src](../../../core/services/agentic_execution.py#L91) |
| method | `ExecutionSink.model_fragment` | `(self, text)` | — | [src](../../../core/services/agentic_execution.py#L92) |
| method | `ExecutionSink.tool_requested` | `(self, call)` | — | [src](../../../core/services/agentic_execution.py#L93) |
| method | `ExecutionSink.tool_result` | `(self, result)` | — | [src](../../../core/services/agentic_execution.py#L94) |
| method | `ExecutionSink.usage` | `(self, usage)` | — | [src](../../../core/services/agentic_execution.py#L95) |
| class | `CancellationProbe` | `` | — | [src](../../../core/services/agentic_execution.py#L98) |
| method | `CancellationProbe.check_before_effect` | `(self)` | — | [src](../../../core/services/agentic_execution.py#L99) |
| method | `CancellationProbe.check_between_rounds` | `(self)` | — | [src](../../../core/services/agentic_execution.py#L100) |
| class | `ExecutionContext` | `` | — | [src](../../../core/services/agentic_execution.py#L103) |
| function | `_normalisér_tool_calls` | `(raw)` | Provider-svarets ``tool_calls`` → ``ToolCall``. | [src](../../../core/services/agentic_execution.py#L113) |
| class | `_ProviderDriver` | `` | Production bridge to the existing provider router without UI state. | [src](../../../core/services/agentic_execution.py#L149) |
| method | `_ProviderDriver.complete` | `(self, request)` | — | [src](../../../core/services/agentic_execution.py#L152) |
| function | `_no_tool_executor` | `(call)` | — | [src](../../../core/services/agentic_execution.py#L249) |
| class | `VisibleExecutionAdapter` | `` | — | [src](../../../core/services/agentic_execution.py#L254) |
| class | `RoutineExecutionAdapter` | `` | — | [src](../../../core/services/agentic_execution.py#L263) |
| method | `RoutineExecutionAdapter.__init__` | `(self, context, *, instruction, driver=…, tool_executor=…, tools_payload=…, max_rounds=…)` | — | [src](../../../core/services/agentic_execution.py#L264) |
| function | `_emit_terminal` | `(sink, result)` | — | [src](../../../core/services/agentic_execution.py#L285) |
| function | `_approval` | `(sink, call)` | — | [src](../../../core/services/agentic_execution.py#L292) |
| function | `_samlet_tekst` | `(parts)` | Saml rundernes tekst til ét svar — med luft mellem runderne. | [src](../../../core/services/agentic_execution.py#L298) |
| function | `execute_agentic` | `(context, sink, cancellation)` | Run bounded model/tool rounds and emit exactly one terminal result. | [src](../../../core/services/agentic_execution.py#L311) |

## `core/services/routine_prompt.py`
_Build a bounded Routine prompt directly from its immutable execution context._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_routine_prompt` | `(context, *, instruction)` | Return the execution prompt without consulting conversation state. | [src](../../../core/services/routine_prompt.py#L9) |
| function | `build_session_routine_prompt` | `(context, *, instruction)` | Build a wakeup instruction; the visible lane supplies chat context. | [src](../../../core/services/routine_prompt.py#L55) |

## `core/services/routine_reconciler.py`
_Crash reconciliation and retention sweeps for Routine work._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineReconciler` | `` | — | [src](../../../core/services/routine_reconciler.py#L10) |
| method | `RoutineReconciler.__init__` | `(self, *, repository=…)` | — | [src](../../../core/services/routine_reconciler.py#L11) |
| method | `RoutineReconciler.reconcile_once` | `(self, now=…)` | — | [src](../../../core/services/routine_reconciler.py#L18) |
| method | `RoutineReconciler.sweep_retention` | `(self, now=…)` | — | [src](../../../core/services/routine_reconciler.py#L54) |

## `core/services/routine_runner.py`
_Fenced, session-neutral execution of one Routine run._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `publish_operational_failure` | `(*, routine_id, run_id, component)` | Best-effort fixed-schema projection; never expose execution content. | [src](../../../core/services/routine_runner.py#L30) |
| function | `_alert_owner` | `(text, run_id)` | Råb op til ejeren via samme kanaler som routine_diagnostics. | [src](../../../core/services/routine_runner.py#L50) |
| class | `StaleRoutineLease` | `` | The worker no longer owns the run generation. | [src](../../../core/services/routine_runner.py#L76) |
| class | `RunClaim` | `` | — | [src](../../../core/services/routine_runner.py#L81) |
| class | `RunState` | `` | — | [src](../../../core/services/routine_runner.py#L90) |
| function | `_claim` | `(row)` | — | [src](../../../core/services/routine_runner.py#L98) |
| function | `_state` | `(row)` | — | [src](../../../core/services/routine_runner.py#L108) |
| function | `_stale` | `(exc)` | — | [src](../../../core/services/routine_runner.py#L118) |
| function | `_standard_provider` | `()` | Modellen et rutine-run bruger når rutinen ikke selv peger på én. | [src](../../../core/services/routine_runner.py#L136) |
| function | `_standard_model` | `()` | Se :func:`_standard_provider` — samme måling, samme grund. | [src](../../../core/services/routine_runner.py#L160) |
| function | `_rutine_tools_payload` | `(context)` | Værktøjsskemaet denne rutine må byde modellen. Tom = værktøjs-fri. | [src](../../../core/services/routine_runner.py#L232) |
| function | `_rutine_max_rounds` | `(context)` | Læs et afgrænset rundebudget fra rutinens egen policy. | [src](../../../core/services/routine_runner.py#L262) |
| function | `_ejer_kontekst` | `(owner_user_id, *, run_id=…)` | Kør blokken som rutinens ejer: workspace, oprindelse og autonomi. | [src](../../../core/services/routine_runner.py#L276) |
| function | `build_tool_executor` | `(owner_user_id, *, run_id=…)` | Executor for ét rutine-run, scopet til rutinens ejer. | [src](../../../core/services/routine_runner.py#L319) |
| class | `RoutineRunRepository` | `` | — | [src](../../../core/services/routine_runner.py#L354) |
| method | `RoutineRunRepository.claim` | `(self, run_id, *, holder, now=…)` | — | [src](../../../core/services/routine_runner.py#L355) |
| method | `RoutineRunRepository.reclaim` | `(self, run_id, *, expected_generation, holder, now=…)` | — | [src](../../../core/services/routine_runner.py#L361) |
| method | `RoutineRunRepository.assert_current` | `(self, run_id, *, generation, holder=…)` | — | [src](../../../core/services/routine_runner.py#L373) |
| method | `RoutineRunRepository.renew` | `(self, run_id, *, generation, holder)` | — | [src](../../../core/services/routine_runner.py#L383) |
| method | `RoutineRunRepository.get_run` | `(self, run_id, *, decrypt_for=…)` | — | [src](../../../core/services/routine_runner.py#L391) |
| method | `RoutineRunRepository.next_queued_run` | `(self)` | — | [src](../../../core/services/routine_runner.py#L397) |
| method | `RoutineRunRepository.record_tool_dispatch_started` | `(self, run_id, *, generation, call, holder=…, now=…)` | — | [src](../../../core/services/routine_runner.py#L401) |
| method | `RoutineRunRepository.settle_tool_dispatch` | `(self, run_id, *, generation, call, succeeded, holder=…)` | — | [src](../../../core/services/routine_runner.py#L413) |
| method | `RoutineRunRepository.list_open_tool_effects` | `(self, run_id)` | — | [src](../../../core/services/routine_runner.py#L425) |
| method | `RoutineRunRepository.transition` | `(self, run_id, *, status, generation, result=…, diagnostic_code=…)` | — | [src](../../../core/services/routine_runner.py#L428) |
| method | `RoutineRunRepository.complete_success` | `(self, run_id, *, generation, result, delivery_channel)` | — | [src](../../../core/services/routine_runner.py#L440) |
| method | `RoutineRunRepository.get_failure_count` | `(self, routine_id)` | — | [src](../../../core/services/routine_runner.py#L452) |
| class | `_FencedRecorder` | `` | — | [src](../../../core/services/routine_runner.py#L456) |
| method | `_FencedRecorder.__init__` | `(self, recorder)` | — | [src](../../../core/services/routine_runner.py#L457) |
| method | `_FencedRecorder.append` | `(self, *args, **kwargs)` | — | [src](../../../core/services/routine_runner.py#L460) |
| method | `_FencedRecorder.list` | `(self, *args, **kwargs)` | — | [src](../../../core/services/routine_runner.py#L468) |
| class | `_RunSink` | `` | — | [src](../../../core/services/routine_runner.py#L472) |
| method | `_RunSink.__init__` | `(self, recorder, run_id, generation)` | — | [src](../../../core/services/routine_runner.py#L473) |
| method | `_RunSink._append` | `(self, kind, payload)` | — | [src](../../../core/services/routine_runner.py#L478) |
| method | `_RunSink.model_fragment` | `(self, text)` | — | [src](../../../core/services/routine_runner.py#L483) |
| method | `_RunSink.tool_requested` | `(self, call)` | — | [src](../../../core/services/routine_runner.py#L486) |
| method | `_RunSink.approval_requested` | `(self, call)` | — | [src](../../../core/services/routine_runner.py#L489) |
| method | `_RunSink.tool_result` | `(self, result)` | — | [src](../../../core/services/routine_runner.py#L492) |
| method | `_RunSink.usage` | `(self, usage)` | — | [src](../../../core/services/routine_runner.py#L500) |
| class | `_LeaseProbe` | `` | — | [src](../../../core/services/routine_runner.py#L508) |
| method | `_LeaseProbe.__init__` | `(self, repository, claim, holder)` | — | [src](../../../core/services/routine_runner.py#L509) |
| method | `_LeaseProbe._check` | `(self)` | — | [src](../../../core/services/routine_runner.py#L514) |
| method | `_LeaseProbe.check_before_effect` | `(self)` | — | [src](../../../core/services/routine_runner.py#L524) |
| method | `_LeaseProbe.check_between_rounds` | `(self)` | — | [src](../../../core/services/routine_runner.py#L527) |
| class | `_LeaseKeeper` | `` | Fornyer leasen MENS et værktøjskald kører. | [src](../../../core/services/routine_runner.py#L531) |
| method | `_LeaseKeeper.__init__` | `(self, repository, run_id, holder)` | — | [src](../../../core/services/routine_runner.py#L551) |
| method | `_LeaseKeeper._loop` | `(self)` | — | [src](../../../core/services/routine_runner.py#L559) |
| method | `_LeaseKeeper.__enter__` | `(self)` | — | [src](../../../core/services/routine_runner.py#L579) |
| method | `_LeaseKeeper.__exit__` | `(self, *exc_info)` | — | [src](../../../core/services/routine_runner.py#L591) |
| method | `_LeaseKeeper.set_generation` | `(self, generation)` | — | [src](../../../core/services/routine_runner.py#L596) |
| class | `RoutineRunner` | `` | — | [src](../../../core/services/routine_runner.py#L600) |
| method | `RoutineRunner.__init__` | `(self, *, driver=…, tool_executor=…, holder=…)` | — | [src](../../../core/services/routine_runner.py#L601) |
| method | `RoutineRunner.dispatch_tool` | `(self, run_id, *, generation, call, raw_executor=…)` | — | [src](../../../core/services/routine_runner.py#L612) |
| method | `RoutineRunner._context` | `(self, row, generation)` | — | [src](../../../core/services/routine_runner.py#L637) |
| method | `RoutineRunner.run_once` | `(self, run_id)` | — | [src](../../../core/services/routine_runner.py#L662) |
| method | `RoutineRunner.run_next` | `(self)` | — | [src](../../../core/services/routine_runner.py#L819) |
| method | `RoutineRunner._record_wait` | `(self, run_id, reason)` | Gør ventetiden synlig: en kø-kørsel uden events ser hængt ud. | [src](../../../core/services/routine_runner.py#L829) |
| method | `RoutineRunner._check_ollama_while_waiting` | `(self, run_id)` | — | [src](../../../core/services/routine_runner.py#L846) |
| method | `RoutineRunner.cancel` | `(self, run_id)` | — | [src](../../../core/services/routine_runner.py#L872) |
| method | `RoutineRunner.record_execution_success` | `(self, routine_id)` | — | [src](../../../core/services/routine_runner.py#L875) |
| method | `RoutineRunner.record_execution_failure` | `(self, routine_id, *, run_id, terminal_diagnostic_code=…)` | — | [src](../../../core/services/routine_runner.py#L878) |

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
| class | `UnmigratedRoutineSource` | `` | The cutover is enabled but this legacy source has no verified Routine. | [src](../../../core/services/routine_trigger_adapters.py#L21) |
| class | `UnknownSystemProducer` | `` | A producer not present in the explicit system-only registry was requested. | [src](../../../core/services/routine_trigger_adapters.py#L25) |
| class | `TriggerResult` | `` | — | [src](../../../core/services/routine_trigger_adapters.py#L30) |
| function | `_cutover_tokens` | `()` | Env-værdien som mængde: globale sandheds-ord ELLER ``kind:id``-par. | [src](../../../core/services/routine_trigger_adapters.py#L38) |
| function | `routine_cutover_enabled` | `()` | GLOBAL cutover — sand kun når env siger det uden at pege på enkeltkilder. | [src](../../../core/services/routine_trigger_adapters.py#L52) |
| function | `cutover_allows` | `(source_kind, source_id)` | Må netop DENNE kilde gå Routine-vejen? | [src](../../../core/services/routine_trigger_adapters.py#L61) |
| function | `_runner_principal` | `()` | — | [src](../../../core/services/routine_trigger_adapters.py#L76) |
| class | `RoutineTriggerAdapters` | `` | — | [src](../../../core/services/routine_trigger_adapters.py#L80) |
| method | `RoutineTriggerAdapters.__init__` | `(self, *, system_owner_user_id=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L81) |
| method | `RoutineTriggerAdapters._enqueue` | `(self, routine_id, *, trigger_key, execution_context=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L85) |
| method | `RoutineTriggerAdapters._linked` | `(self, source_kind, source_id)` | — | [src](../../../core/services/routine_trigger_adapters.py#L97) |
| method | `RoutineTriggerAdapters.enqueue_scheduled` | `(self, source_id)` | — | [src](../../../core/services/routine_trigger_adapters.py#L107) |
| method | `RoutineTriggerAdapters.enqueue_recurring` | `(self, source_id, *, occurrence_id=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L113) |
| method | `RoutineTriggerAdapters._owner` | `(self)` | — | [src](../../../core/services/routine_trigger_adapters.py#L121) |
| method | `RoutineTriggerAdapters._system_routine` | `(self, producer)` | — | [src](../../../core/services/routine_trigger_adapters.py#L132) |
| method | `RoutineTriggerAdapters.enqueue_system` | `(self, producer, source_id, *, trigger_inputs=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L156) |
| method | `RoutineTriggerAdapters.fire` | `(self, producer, *, source_id)` | — | [src](../../../core/services/routine_trigger_adapters.py#L166) |
| function | `enqueue_scheduled` | `(source_id)` | — | [src](../../../core/services/routine_trigger_adapters.py#L174) |
| function | `enqueue_recurring` | `(source_id, *, occurrence_id=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L178) |
| function | `enqueue_system` | `(producer, source_id, *, trigger_inputs=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L186) |
| function | `dispatch_recurring` | `(source_id, *, legacy, adapters=…, occurrence_id=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L195) |
| function | `dispatch_scheduled` | `(source_id, *, legacy, adapters=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L220) |
| function | `dispatch_system` | `(producer, source_id, *, trigger_inputs, legacy, adapters=…)` | — | [src](../../../core/services/routine_trigger_adapters.py#L230) |
| function | `dispatch_heartbeat_initiative` | `(*, focus, initiative_id, session_id=…)` | Extracted heartbeat execution boundary for the oversized runtime module. | [src](../../../core/services/routine_trigger_adapters.py#L245) |

