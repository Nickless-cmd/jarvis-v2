# Codex Task: Tool Result Externalization

## Problem

Chat sessions become heavy for the browser. Every tool call result (file contents, db queries, bash output) is stored inline in `chat_messages` with `role='tool'`. A typical session accumulates 50-200KB+ of raw tool output in the DOM. Even with Claude 4.7's 1M context window, **browser weight is the real bottleneck** — DOM rendering, not token count.

## Current Architecture

- `core/services/chat_sessions.py` → `append_chat_message()` stores tool results as `role='tool'` messages with full content in the `chat_messages` table
- `core/services/visible_runs.py` → `_stream_visible_run()` processes tool calls, streams results via SSE, and persists them via `append_chat_message`
- `_build_visible_input()` in `core/services/visible_model.py` loads full chat history including tool messages and sends it all to the model
- `core/runtime/db.py` → `chat_messages` table: `message_id, session_id, role, content, created_at`
- Compaction exists (`/compact`, `context_compact_threshold_tokens: 40K`) but is reactive — only runs after the session is already heavy
- Tool results can be very large: `read_file` on source files, `db_query` returning hundreds of rows, `bash` with long output

## Solution: Tiered Tool Result Storage

### Core Idea

Store full tool results on disk as individual files. In the session history, store only a **reference** (summary + file path). The model gets a new tool `read_tool_result` to retrieve full output on demand.

### Implementation Plan

#### 1. Tool Result Store (`core/services/tool_result_store.py`)

Create a new service that:

- Saves tool results to `~/.jarvis-v2/tool_results/{result_id}.json` as individual files
- Each file contains: `{ "result_id": "...", "tool_name": "...", "arguments": {...}, "result": "...", "created_at": "...", "summary": "..." }`
- `save_tool_result(tool_name, arguments, result_content) -> str` — saves to disk, returns result_id
- `get_tool_result(result_id) -> dict | None` — reads from disk
- `summarize_result(content, max_length=500) -> str` — creates a short summary for inline reference
- `cleanup_old_results(max_age_days=7) -> int` — removes results older than N days

#### 2. Modify `append_chat_message()` in `core/services/chat_sessions.py`

When `role='tool'`:

- Call `tool_result_store.save_tool_result(...)` to persist the full content
- Generate a summary: first ~500 chars of the result, or a structured summary
- Store the **reference** in `chat_messages.content`: something like `[tool_result:result_id]\nSummary: <first 500 chars>\nUse read_tool_result to see full output.`
- The `content` column still has useful context but is bounded in size

#### 3. Modify `_build_visible_input()` in `core/services/visible_model.py`

When building the message list for the model:

- Detect `[tool_result:...]` patterns in tool messages
- For the **most recent** tool results (last 3-5), expand them inline so the model has immediate context
- For older tool results, keep only the reference/summary
- This keeps the prompt token count manageable while preserving recent tool context

#### 4. New Tool: `read_tool_result`

Add to `core/tools/workspace_capabilities.py` (or as a new capability file):

```python
{
    "name": "read_tool_result",
    "description": "Retrieve the full output of a previous tool call by result_id. Use this when you need to see the complete output that was summarized in the conversation.",
    "parameters": {
        "type": "object",
        "properties": {
            "result_id": {
                "type": "string",
                "description": "The result_id from a [tool_result:...] reference"
            }
        },
        "required": ["result_id"]
    }
}
```

The implementation reads from `tool_result_store.get_tool_result(result_id)` and returns the full content.

#### 5. Register in Simple Tools

Add `read_tool_result` to the simple tools registry in `core/tools/simple_tools.py` alongside the existing tools like `read_file`, `bash`, etc.

#### 6. Modify `_stream_visible_run()` in `core/services/visible_runs.py`

After executing native tool calls (`_execute_simple_tool_calls`), before persisting to DB:

- For each tool result, call `tool_result_store.save_tool_result(...)` 
- Pass the **reference** (not full content) to `append_chat_message(role='tool', content=reference_text)`

#### 7. Cleanup Script (`scripts/tool_result_cleanup.py`)

A standalone script that:

- Removes tool result files older than 7 days
- Can be run manually or via cron
- Reports how many files were cleaned up

#### 8. Tests (`tests/test_tool_result_externalization.py`)

- Test `tool_result_store.save_tool_result()` and `get_tool_result()` round-trip
- Test `summarize_result()` produces bounded-length summaries
- Test `append_chat_message()` with `role='tool'` stores reference, not full content
- Test `_build_visible_input()` expands recent references inline
- Test `read_tool_result` tool capability works end-to-end
- Test cleanup removes old files

## Key Files to Modify

- `core/services/chat_sessions.py` — modify `append_chat_message()` for tool role
- `core/services/visible_model.py` — modify `_build_visible_input()` to expand recent references
- `core/services/visible_runs.py` — modify tool result persistence flow
- `core/tools/simple_tools.py` — register `read_tool_result`
- `core/runtime/db.py` — possibly add index or migration for tool result references
- `core/runtime/config.py` — add `TOOL_RESULTS_DIR` config

## Key Files to Create

- `core/services/tool_result_store.py` — new service
- `scripts/tool_result_cleanup.py` — cleanup script
- `tests/test_tool_result_externalization.py` — tests

## Constraints

- **Backward compatible**: Old sessions with full inline tool results must still work. The `[tool_result:...]` pattern is only for new messages.
- **The model must still have context**: Recent tool results (last 3-5) should be expanded inline in `_build_visible_input()` so the model isn't blind.
- **Summary quality matters**: The inline summary should be useful enough that the model rarely needs to call `read_tool_result`. For short results (< 500 chars), just include the full thing.
- **Disk is cheap, tokens are expensive**: Store everything on disk, be selective about what goes into the prompt.
- **Thread safety**: `tool_result_store` will be called from async contexts — use file-based locking or atomic writes.

## Commit

When all changes are complete and tests pass, commit with message:

```
feat(chat): externalize tool results to disk, store references in session history

- Add tool_result_store service for saving/loading tool results to disk
- Modify append_chat_message to store references for tool role messages
- Expand recent tool results inline in _build_visible_input
- Add read_tool_result capability for retrieving full outputs
- Add cleanup script for old tool result files
- Full test coverage
```