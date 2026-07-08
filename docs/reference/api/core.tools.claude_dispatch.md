# `core.tools.claude_dispatch` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/tools/claude_dispatch/__init__.py`

_(no top-level classes or functions)_

## `core/tools/claude_dispatch/audit.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/tools/claude_dispatch/audit.py#L12) |
| function | `start_audit_row` | `(task_id, spec)` | — | [src](../../../core/tools/claude_dispatch/audit.py#L16) |
| function | `finalize_audit_row` | `(task_id, *, status, tokens_used, exit_code, diff_summary, error)` | — | [src](../../../core/tools/claude_dispatch/audit.py#L29) |
| function | `read_audit_row` | `(task_id)` | — | [src](../../../core/tools/claude_dispatch/audit.py#L47) |

## `core/tools/claude_dispatch/budget.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `BudgetExceeded` | `` | — | [src](../../../core/tools/claude_dispatch/budget.py#L11) |
| function | `_now` | `()` | — | [src](../../../core/tools/claude_dispatch/budget.py#L15) |
| function | `_hour_bucket` | `(dt)` | — | [src](../../../core/tools/claude_dispatch/budget.py#L19) |
| class | `BudgetTracker` | `` | — | [src](../../../core/tools/claude_dispatch/budget.py#L23) |
| method | `BudgetTracker.check_and_reserve` | `(self)` | — | [src](../../../core/tools/claude_dispatch/budget.py#L24) |
| method | `BudgetTracker.record_usage` | `(self, tokens)` | — | [src](../../../core/tools/claude_dispatch/budget.py#L50) |
| method | `BudgetTracker.current_dispatch_count` | `(self)` | — | [src](../../../core/tools/claude_dispatch/budget.py#L63) |

## `core/tools/claude_dispatch/host_oauth.py`
_Find a live host Claude Code OAuth token to inject into `claude -p` spawns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_process_start_time` | `(pid)` | Return process start time (seconds since boot) from /proc/<pid>/stat. | [src](../../../core/tools/claude_dispatch/host_oauth.py#L39) |
| function | `find_host_oauth_token` | `()` | Return a live host CLAUDE_CODE_OAUTH_TOKEN, or None if no host is running. | [src](../../../core/tools/claude_dispatch/host_oauth.py#L69) |

## `core/tools/claude_dispatch/jail.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `JailViolation` | `` | — | [src](../../../core/tools/claude_dispatch/jail.py#L12) |
| function | `assert_inside_jail` | `(path)` | — | [src](../../../core/tools/claude_dispatch/jail.py#L16) |
| function | `build_worktree_path` | `(task_id)` | — | [src](../../../core/tools/claude_dispatch/jail.py#L24) |

## `core/tools/claude_dispatch/runner.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_prompt` | `(spec)` | — | [src](../../../core/tools/claude_dispatch/runner.py#L23) |
| function | `_new_task_id` | `()` | — | [src](../../../core/tools/claude_dispatch/runner.py#L47) |
| function | `run_dispatch` | `(spec, eventbus)` | — | [src](../../../core/tools/claude_dispatch/runner.py#L51) |

## `core/tools/claude_dispatch/spec.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SpecValidationError` | `` | — | [src](../../../core/tools/claude_dispatch/spec.py#L17) |
| class | `TaskSpec` | `` | — | [src](../../../core/tools/claude_dispatch/spec.py#L22) |
| function | `parse_spec` | `(raw)` | — | [src](../../../core/tools/claude_dispatch/spec.py#L33) |

## `core/tools/claude_dispatch/stream.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ParsedEvent` | `` | — | [src](../../../core/tools/claude_dispatch/stream.py#L9) |
| function | `parse_stream_line` | `(line)` | — | [src](../../../core/tools/claude_dispatch/stream.py#L17) |

## `core/tools/claude_dispatch/tool.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_eventbus` | `()` | — | [src](../../../core/tools/claude_dispatch/tool.py#L16) |
| function | `_exec_dispatch_to_claude_code` | `(args)` | — | [src](../../../core/tools/claude_dispatch/tool.py#L23) |
| function | `_exec_dispatch_status` | `(args)` | — | [src](../../../core/tools/claude_dispatch/tool.py#L37) |
| function | `_exec_dispatch_cancel` | `(args)` | — | [src](../../../core/tools/claude_dispatch/tool.py#L47) |

## `core/tools/claude_dispatch/worktree.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_worktree` | `(task_id)` | — | [src](../../../core/tools/claude_dispatch/worktree.py#L9) |
| function | `cleanup_worktree` | `(task_id)` | — | [src](../../../core/tools/claude_dispatch/worktree.py#L24) |
| function | `worktree_diff` | `(task_id)` | — | [src](../../../core/tools/claude_dispatch/worktree.py#L41) |

