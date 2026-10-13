# `apps.api.jarvis_api.routes.routines` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/api/jarvis_api/routes/routines.py`
_Authenticated, owner-scoped Routine lifecycle API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineCreateBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L23) |
| class | `RoutinePatchBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L43) |
| class | `InboxPolicyBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L64) |
| class | `EmptyBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L80) |
| function | `_principal` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L84) |
| function | `_service` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L93) |
| function | `_routine` | `(value)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L97) |
| function | `_run` | `(value)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L103) |
| function | `_not_found` | `(exc)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L113) |
| function | `list_routines` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L118) |
| function | `create_routine` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L123) |
| function | `get_inbox_defaults` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L130) |
| function | `set_inbox_defaults` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L135) |
| function | `get_routine` | `(routine_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L140) |
| function | `patch_routine` | `(routine_id, body)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L151) |
| function | `delete_routine` | `(routine_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L170) |
| function | `lifecycle_action` | `(routine_id, action)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L181) |
| function | `run_now` | `(routine_id, body=…)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L194) |
| function | `list_runs` | `(routine_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L210) |
| function | `get_run` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L218) |
| function | `get_run_events` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L229) |
| function | `cancel_run` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L237) |
| function | `get_redacted_diagnostic` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L245) |

