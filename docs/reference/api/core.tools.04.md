# `core.tools.04` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/tools/workspace_capability_decl.py`
_Capability body declaration-parsere + workspace-sti-resolution._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_declared_read_file_path` | `(body)` | — | [src](../../../core/tools/workspace_capability_decl.py#L18) |
| function | `_declared_search_file_spec` | `(body)` | — | [src](../../../core/tools/workspace_capability_decl.py#L22) |
| function | `_declared_external_file_spec` | `(body)` | — | [src](../../../core/tools/workspace_capability_decl.py#L36) |
| function | `_declared_exec_spec` | `(body)` | — | [src](../../../core/tools/workspace_capability_decl.py#L53) |
| function | `_declared_write_target_path` | `(body)` | — | [src](../../../core/tools/workspace_capability_decl.py#L70) |
| function | `_declared_body_value` | `(body, key, *, validate=…)` | — | [src](../../../core/tools/workspace_capability_decl.py#L74) |
| function | `_is_valid_workspace_relative_path` | `(value)` | — | [src](../../../core/tools/workspace_capability_decl.py#L91) |
| function | `_resolve_workspace_relative_path` | `(workspace_dir, value)` | — | [src](../../../core/tools/workspace_capability_decl.py#L102) |
| function | `_resolve_external_path` | `(workspace_dir, value)` | — | [src](../../../core/tools/workspace_capability_decl.py#L114) |
| function | `_is_within_workspace_root` | `(workspace_dir, candidate)` | — | [src](../../../core/tools/workspace_capability_decl.py#L126) |
| function | `_expand_declared_path` | `(value, *, workspace_dir)` | — | [src](../../../core/tools/workspace_capability_decl.py#L135) |

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

