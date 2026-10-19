# `apps.api.jarvis_api.routes.routines` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/api/jarvis_api/routes/routines.py`
_Authenticated, owner-scoped Routine lifecycle API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineCreateBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L23) |
| class | `RoutinePatchBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L50) |
| class | `InboxPolicyBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L71) |
| class | `EmptyBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L87) |
| function | `_principal` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L91) |
| function | `_service` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L110) |
| function | `_routine` | `(value)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L114) |
| function | `_run` | `(value)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L120) |
| function | `_not_found` | `(exc)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L130) |
| function | `list_routines` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L135) |
| function | `create_routine` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L140) |
| function | `get_inbox_defaults` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L147) |
| function | `set_inbox_defaults` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L152) |
| function | `get_routine` | `(routine_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L157) |
| function | `patch_routine` | `(routine_id, body)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L168) |
| function | `delete_routine` | `(routine_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L187) |
| function | `lifecycle_action` | `(routine_id, action)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L198) |
| function | `run_now` | `(routine_id, body=…)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L211) |
| function | `list_runs` | `(routine_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L227) |
| function | `get_run` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L235) |
| function | `get_run_events` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L246) |
| function | `cancel_run` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L254) |
| function | `get_redacted_diagnostic` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L262) |

