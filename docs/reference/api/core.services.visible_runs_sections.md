# `core.services.visible_runs_sections` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/visible_runs_sections/__init__.py`
_visible_runs_sections — Boy Scout-udtrækninger fra visible_runs.py._

_(no top-level classes or functions)_

## `core/services/visible_runs_sections/client_tool_delegation.py`
_Klient-tool-delegering — udskilt enhed (Boy Scout: holder visible_runs.py lille)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `begin_client_tool` | `(call_id, *, tool_name, arguments, run_id, session_id)` | Registrér en delegeret klient-tool som pending, før loopet emitterer tool_use. | [src](../../../core/services/visible_runs_sections/client_tool_delegation.py#L36) |
| function | `await_client_tool_result` | `(call_id, *, timeout_s=…)` | Blokér (poll) til klienten leverer resultatet, eller deadline rammes. | [src](../../../core/services/visible_runs_sections/client_tool_delegation.py#L56) |

## `core/services/visible_runs_sections/detached_run.py`
_Detached (request-uafhængig) bruger-run → server-autoritativt via run_event_log._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_user_run_detached` | `(*, message, session_id, approval_mode=…, thinking_mode=…, force_user_id=…, tool_scope=…, provider_override=…, model_override=…, eff_model=…, eff_provider=…, lane=…, run_id=…, local_tool_exec=…)` | Start et server-autoritativt run. Returnerer run_id (klienten abonnerer | [src](../../../core/services/visible_runs_sections/detached_run.py#L13) |
| function | `start_or_attach_user_run` | `(*, message, session_id, nudge_enabled=…, **kw)` | Single-flight pr. session for server-autoritative runs. | [src](../../../core/services/visible_runs_sections/detached_run.py#L132) |

## `core/services/visible_runs_sections/run_control_state.py`
_Visible-run control state — udskilt fra visible_runs.py (Boy Scout)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_visible_run_control_key` | `(run_id)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L32) |
| function | `_visible_run_approval_key` | `(approval_id)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L36) |
| function | `_set_visible_run_control` | `(run_id, payload)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L40) |
| function | `_get_visible_run_control` | `(run_id)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L44) |
| function | `_set_active_visible_run` | `(payload)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L49) |
| function | `_get_active_visible_run_state` | `()` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L53) |
| function | `touch_active_visible_run` | `(run_id)` | Heartbeat: opdatér last_activity_at i den DELTE active-run state (DB), | [src](../../../core/services/visible_runs_sections/run_control_state.py#L58) |
| function | `_visible_run_cancelled` | `(run_id)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L73) |
| function | `_mark_visible_run_cancelled` | `(run_id, *, cancelled=…)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L77) |
| function | `append_visible_run_steer` | `(run_id, content)` | Append a mid-flight 'steer' message that the agentic loop will pick | [src](../../../core/services/visible_runs_sections/run_control_state.py#L86) |
| function | `consume_visible_run_steers` | `(run_id)` | Pop unread steers for this run. Marks them consumed in shared state | [src](../../../core/services/visible_runs_sections/run_control_state.py#L110) |
| function | `_set_visible_approval_state` | `(approval_id, payload)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L131) |
| function | `_get_visible_approval_state` | `(approval_id)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L135) |
| function | `_visible_run_client_tool_key` | `(call_id)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L143) |
| function | `_set_visible_client_tool_state` | `(call_id, payload)` | Sæt state for en delegeret klient-tool (cross-worker via DB). | [src](../../../core/services/visible_runs_sections/run_control_state.py#L147) |
| function | `_get_visible_client_tool_state` | `(call_id)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L152) |
| function | `resolve_visible_client_tool` | `(call_id, result_text)` | Klienten leverer resultatet af en delegeret tool. Flip pending → resolved | [src](../../../core/services/visible_runs_sections/run_control_state.py#L157) |

## `core/services/visible_runs_sections/stream_observers.py`
_Stream-observabilitets-nerver — Boy Scout-udtrækning fra visible_runs.py._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `observe_persist_failed` | `(run, exc)` | H5 (spec §2/§4.5): persistering af assistant-beskeden fejlede MENS svaret | [src](../../../core/services/visible_runs_sections/stream_observers.py#L18) |
| function | `observe_streamed_text_recovered` | `(run, *, chars, source)` | DAG-ÉT DIVERGENS-NERVE (2026-06-30, Bjørn: provider-agnostisk cutoff fra | [src](../../../core/services/visible_runs_sections/stream_observers.py#L41) |

