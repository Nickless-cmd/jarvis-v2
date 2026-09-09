# `core.runtime.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/runtime/workspace_paths.py`
_Workspace path resolver — single source of truth for filesystem layout._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NoUserContextError` | `` | Raised when workspace_dir() is called without a resolvable user_id. | [src](../../../core/runtime/workspace_paths.py#L17) |
| function | `_jarvis_home` | `()` | JARVIS_HOME resolved at call time (so tests can override via env). | [src](../../../core/runtime/workspace_paths.py#L26) |
| function | `shared_dir` | `()` | Jarvis' own state. All users see the same instance. | [src](../../../core/runtime/workspace_paths.py#L31) |
| function | `workspace_dir` | `(user_id=…)` | Per-relation workspace. Defaults to current_user_id() from context. | [src](../../../core/runtime/workspace_paths.py#L40) |
| function | `workspace_dir_or_owner` | `()` | workspace_dir() with an owner fallback, then shared/ as last resort. | [src](../../../core/runtime/workspace_paths.py#L65) |
| function | `_user_id_to_workspace_name` | `(user_id)` | Resolve user_id → workspace folder name. | [src](../../../core/runtime/workspace_paths.py#L89) |

