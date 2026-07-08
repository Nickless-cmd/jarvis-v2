# `core.coding_lane` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/coding_lane/auto_reviewer.py`
_Coding lane auto-reviewer — subscriber til coding_lane.commit_landed events._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_event_listeners` | `()` | Start background eventbus listener for coding_lane.commit_landed events. | [src](../../../core/coding_lane/auto_reviewer.py#L50) |
| function | `stop_event_listeners` | `()` | Stop the background listener thread. | [src](../../../core/coding_lane/auto_reviewer.py#L71) |
| function | `_listener_loop` | `(q)` | — | [src](../../../core/coding_lane/auto_reviewer.py#L77) |
| function | `_handle_commit_landed` | `(payload)` | Receive a commit-landed event, apply filters, dispatch to coding lane. | [src](../../../core/coding_lane/auto_reviewer.py#L94) |
| function | `_get_diff` | `(sha, project_root)` | Get the diff for a commit. Returns None on failure. | [src](../../../core/coding_lane/auto_reviewer.py#L158) |
| function | `_has_budget` | `()` | Check if coding lane has budget to spend on a review. | [src](../../../core/coding_lane/auto_reviewer.py#L181) |
| function | `_dispatch_review` | `(sha, message, prompt)` | Fire-and-forget dispatch to coding lane. Runs in a background thread. | [src](../../../core/coding_lane/auto_reviewer.py#L190) |
| function | `_do_review` | `(sha, message, prompt)` | Execute the review via coding lane and publish result. | [src](../../../core/coding_lane/auto_reviewer.py#L201) |
| function | `_publish_skipped` | `(sha, reason, detail=…)` | Publish that a review was skipped (filter match). | [src](../../../core/coding_lane/auto_reviewer.py#L241) |
| function | `_publish_review` | `(sha, message, *, status, severity=…, review_text=…, detail=…)` | Publish a review result event. | [src](../../../core/coding_lane/auto_reviewer.py#L254) |

