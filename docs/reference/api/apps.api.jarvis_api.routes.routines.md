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
| function | `_run` | `(value)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L128) |
| function | `_not_found` | `(exc)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L138) |
| function | `list_routines` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L143) |
| function | `create_routine` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L148) |
| function | `get_inbox_defaults` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L155) |
| function | `set_inbox_defaults` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L160) |
| function | `active_runs` | `()` | Rutine-kørsler der er i gang lige nu. | [src](../../../apps/api/jarvis_api/routes/routines.py#L165) |
| function | `origin_sessions` | `(routine_id)` | Hvor en system-rutines arbejde FAKTISK ligger. | [src](../../../apps/api/jarvis_api/routes/routines.py#L184) |
| function | `chat_session` | `(routine_id)` | Rutinens samtale — hvor man SER hvad den gjorde, og kan svare den. | [src](../../../apps/api/jarvis_api/routes/routines.py#L210) |
| function | `get_routine` | `(routine_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L265) |
| function | `patch_routine` | `(routine_id, body)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L276) |
| function | `delete_routine` | `(routine_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L295) |
| function | `lifecycle_action` | `(routine_id, action)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L306) |
| function | `run_now` | `(routine_id, body=…)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L319) |
| function | `list_runs` | `(routine_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L335) |
| function | `get_run` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L343) |
| function | `get_run_events` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L354) |
| function | `cancel_run` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L362) |
| function | `get_redacted_diagnostic` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L370) |

