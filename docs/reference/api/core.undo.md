# `core.undo` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/undo/__init__.py`
_Bounded, message-scoped undo for file edits._

_(no top-level classes or functions)_

## `core/undo/message_edits.py`
_Undo file writes belonging to one saved assistant message._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_key` | `(session_id, call_id)` | — | [src](../../../core/undo/message_edits.py#L28) |
| function | `_index_key` | `(session_id)` | — | [src](../../../core/undo/message_edits.py#L33) |
| function | `_load` | `(key)` | — | [src](../../../core/undo/message_edits.py#L37) |
| function | `_save` | `(key, value)` | — | [src](../../../core/undo/message_edits.py#L42) |
| function | `_snapshot` | `(path)` | — | [src](../../../core/undo/message_edits.py#L47) |
| function | `_target` | `(name, arguments)` | — | [src](../../../core/undo/message_edits.py#L68) |
| function | `_remote_file_state` | `(path, user_id)` | — | [src](../../../core/undo/message_edits.py#L85) |
| function | `_remote_write` | `(path, user_id, content)` | — | [src](../../../core/undo/message_edits.py#L100) |
| function | `_remote_remove` | `(path, user_id, expected_sha, expected_mode)` | — | [src](../../../core/undo/message_edits.py#L111) |
| function | `_remote_snapshot` | `(path, user_id)` | — | [src](../../../core/undo/message_edits.py#L124) |
| function | `capture_before` | `(session_id, call_id, name, arguments)` | Take a bounded snapshot immediately before a supported file tool executes. | [src](../../../core/undo/message_edits.py#L141) |
| function | `capture_after` | `(token, result)` | — | [src](../../../core/undo/message_edits.py#L168) |
| function | `_message_blocks` | `(session_id, message_id)` | — | [src](../../../core/undo/message_edits.py#L187) |
| function | `_records` | `(session_id, message_id)` | — | [src](../../../core/undo/message_edits.py#L203) |
| function | `_decode` | `(snapshot)` | — | [src](../../../core/undo/message_edits.py#L224) |
| function | `_restore` | `(path, snapshot, remote_user_id, data, *, expected=…)` | — | [src](../../../core/undo/message_edits.py#L233) |
| function | `_matches` | `(current, expected)` | — | [src](../../../core/undo/message_edits.py#L258) |
| function | `undo_message` | `(session_id, message_id)` | Restore exact files only if all still equal this message's after-image. | [src](../../../core/undo/message_edits.py#L264) |

