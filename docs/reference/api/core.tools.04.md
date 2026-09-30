# `core.tools.04` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/tools/workspace_capabilities_verdict.py`
_Approval-verdicts + proposal/execution-content for mutating/sudo exec._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_approved_mutating_exec_verdict` | `(classification)` | — | [src](../../../core/tools/workspace_capabilities_verdict.py#L31) |
| function | `_approved_sudo_exec_verdict` | `(classification, *, workspace_dir)` | — | [src](../../../core/tools/workspace_capabilities_verdict.py#L76) |
| function | `_mutating_exec_proposal_content` | `(*, command_text, command_source, classification)` | — | [src](../../../core/tools/workspace_capabilities_verdict.py#L164) |
| function | `_mutating_exec_execution_content` | `(*, command_text, command_source, classification, exit_code, output_text)` | — | [src](../../../core/tools/workspace_capabilities_verdict.py#L215) |
| function | `_sudo_exec_execution_content` | `(*, command_text, command_source, classification, exit_code, output_text)` | — | [src](../../../core/tools/workspace_capabilities_verdict.py#L249) |
| function | `_resolve_target_path_for_sudo_exec` | `(workspace_dir, target)` | — | [src](../../../core/tools/workspace_capabilities_verdict.py#L284) |

## `core/tools/workspace_capabilities_wsio.py`
_Encryption-aware workspace-fil I/O-helpers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ws_read_text` | `(path)` | Læs workspace-fil encryption-aware (member .enc transparent). None hvis | [src](../../../core/tools/workspace_capabilities_wsio.py#L14) |
| function | `_ws_write_text` | `(path, content)` | Skriv workspace-fil encryption-aware (member → .enc når ENCRYPT_ON_WRITE on; | [src](../../../core/tools/workspace_capabilities_wsio.py#L22) |
| function | `_ws_path_exists` | `(path)` | Eksistens encryption-aware: plaintext eller member .enc. | [src](../../../core/tools/workspace_capabilities_wsio.py#L29) |

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

