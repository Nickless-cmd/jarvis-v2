# `core.services.decision_triggers` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/decision_triggers/__init__.py`
_Decision triggers — importing this package registers all triggers._

_(no top-level classes or functions)_

## `core/services/decision_triggers/backend_unresolved.py`
_Trigger: fire when 3 consecutive Jarvis-backend tool calls happen_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_jarvis_backend_call` | `(tool_call)` | — | [src](../../../core/services/decision_triggers/backend_unresolved.py#L44) |
| function | `backend_unresolved_3_calls` | `(ctx)` | — | [src](../../../core/services/decision_triggers/backend_unresolved.py#L67) |

## `core/services/decision_triggers/loop_nudge.py`
_Trigger: fire when Jarvis has had 8 consecutive tool-only rounds._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `loop_nudge_5_rounds` | `(ctx)` | — | [src](../../../core/services/decision_triggers/loop_nudge.py#L27) |

