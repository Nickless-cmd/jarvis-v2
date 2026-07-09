# `core.services.visible_runs_sections` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/visible_runs_sections/__init__.py`
_visible_runs_sections — Boy Scout-udtrækninger fra visible_runs.py._

_(no top-level classes or functions)_

## `core/services/visible_runs_sections/detached_run.py`
_Detached (request-uafhængig) bruger-run → server-autoritativt via run_event_log._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_user_run_detached` | `(*, message, session_id, approval_mode=…, thinking_mode=…, force_user_id=…, tool_scope=…, provider_override=…, model_override=…, eff_model=…, eff_provider=…, lane=…, run_id=…)` | Start et server-autoritativt run. Returnerer run_id (klienten abonnerer | [src](../../../core/services/visible_runs_sections/detached_run.py#L13) |
| function | `start_or_attach_user_run` | `(*, message, session_id, nudge_enabled=…, **kw)` | Single-flight pr. session for server-autoritative runs. | [src](../../../core/services/visible_runs_sections/detached_run.py#L130) |

## `core/services/visible_runs_sections/run_control_state.py`
_Visible-run control state — udskilt fra visible_runs.py (Boy Scout)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_visible_run_control_key` | `(run_id)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L27) |
| function | `_visible_run_approval_key` | `(approval_id)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L31) |
| function | `_set_visible_run_control` | `(run_id, payload)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L35) |
| function | `_get_visible_run_control` | `(run_id)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L39) |
| function | `_set_active_visible_run` | `(payload)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L44) |
| function | `_get_active_visible_run_state` | `()` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L48) |
| function | `touch_active_visible_run` | `(run_id)` | Heartbeat: opdatér last_activity_at i den DELTE active-run state (DB), | [src](../../../core/services/visible_runs_sections/run_control_state.py#L53) |
| function | `_visible_run_cancelled` | `(run_id)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L68) |
| function | `_mark_visible_run_cancelled` | `(run_id, *, cancelled=…)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L72) |
| function | `append_visible_run_steer` | `(run_id, content)` | Append a mid-flight 'steer' message that the agentic loop will pick | [src](../../../core/services/visible_runs_sections/run_control_state.py#L81) |
| function | `consume_visible_run_steers` | `(run_id)` | Pop unread steers for this run. Marks them consumed in shared state | [src](../../../core/services/visible_runs_sections/run_control_state.py#L105) |
| function | `_set_visible_approval_state` | `(approval_id, payload)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L126) |
| function | `_get_visible_approval_state` | `(approval_id)` | — | [src](../../../core/services/visible_runs_sections/run_control_state.py#L130) |

## `core/services/visible_runs_sections/stream_observers.py`
_Stream-observabilitets-nerver — Boy Scout-udtrækning fra visible_runs.py._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `observe_persist_failed` | `(run, exc)` | H5 (spec §2/§4.5): persistering af assistant-beskeden fejlede MENS svaret | [src](../../../core/services/visible_runs_sections/stream_observers.py#L18) |
| function | `observe_streamed_text_recovered` | `(run, *, chars, source)` | DAG-ÉT DIVERGENS-NERVE (2026-06-30, Bjørn: provider-agnostisk cutoff fra | [src](../../../core/services/visible_runs_sections/stream_observers.py#L41) |

