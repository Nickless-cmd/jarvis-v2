# `apps.api.jarvis_api.routes.routines` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/api/jarvis_api/routes/routines.py`
_Authenticated, owner-scoped Routine lifecycle API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineCreateBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L23) |
| class | `RoutinePatchBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L43) |
| class | `InboxPolicyBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L64) |
| class | `EmptyBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L77) |
| function | `_principal` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L81) |
| function | `_service` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L90) |
| function | `_routine` | `(value)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L94) |
| function | `_run` | `(value)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L100) |
| function | `_not_found` | `(exc)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L110) |
| function | `list_routines` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L115) |
| function | `create_routine` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L120) |
| function | `get_inbox_defaults` | `()` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L127) |
| function | `set_inbox_defaults` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L132) |
| function | `get_routine` | `(routine_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L137) |
| function | `patch_routine` | `(routine_id, body)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L148) |
| function | `delete_routine` | `(routine_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L167) |
| function | `lifecycle_action` | `(routine_id, action)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L178) |
| function | `run_now` | `(routine_id, body=…)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L191) |
| function | `list_runs` | `(routine_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L207) |
| function | `get_run` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L215) |
| function | `get_run_events` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L226) |
| function | `cancel_run` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L234) |
| function | `get_redacted_diagnostic` | `(run_id)` | — | [src](../../../apps/api/jarvis_api/routes/routines.py#L242) |

