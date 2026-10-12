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

