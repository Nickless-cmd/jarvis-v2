# `core.tools.04` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/tools/worktree_tools.py`
_Git worktree primitive — let Jarvis experiment in isolation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_project_root` | `()` | — | [src](../../../core/tools/worktree_tools.py#L35) |
| function | `_is_git_repo` | `(path)` | — | [src](../../../core/tools/worktree_tools.py#L43) |
| function | `_git` | `(cwd, argv)` | — | [src](../../../core/tools/worktree_tools.py#L47) |
| function | `_safe_branch_name` | `(name)` | — | [src](../../../core/tools/worktree_tools.py#L57) |
| function | `_exec_worktree_create` | `(args)` | — | [src](../../../core/tools/worktree_tools.py#L63) |
| function | `_exec_worktree_list` | `(_args)` | — | [src](../../../core/tools/worktree_tools.py#L110) |
| function | `_exec_worktree_merge` | `(args)` | — | [src](../../../core/tools/worktree_tools.py#L146) |
| function | `_exec_worktree_discard` | `(args)` | — | [src](../../../core/tools/worktree_tools.py#L192) |

## `core/tools/world_model_tools.py`
_World Model tools — predict_outcome + resolve_prediction._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_predict_outcome` | `(args)` | Record a falsifiable prediction. | [src](../../../core/tools/world_model_tools.py#L25) |
| function | `_exec_resolve_prediction` | `(args)` | Resolve an open prediction with a later observation. | [src](../../../core/tools/world_model_tools.py#L85) |

