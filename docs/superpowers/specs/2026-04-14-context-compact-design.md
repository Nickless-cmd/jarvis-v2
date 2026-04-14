# Context Compact Implementation Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis a two-layer compaction system so long sessions and long tool-calling runs never overflow the context window — with Jarvis announcing when it happens.

**Architecture:** Session-level compact summarises old transcript messages and persists a `compact_marker` in the DB; run-level compact summarises accumulated tool-call/result pairs mid-loop. Both are triggered automatically by token-estimate thresholds, by Jarvis via a `compact_context` tool, and by the user via `/compact`.

**Tech Stack:** Python, FastAPI, SQLite (existing `chat_messages` table extended), heartbeat LLM (cheap model for summarisation), existing `visible_model.py` tool loop, existing `prompt_contract.py` transcript builder.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `core/context/__init__.py` | Create | Package marker |
| `core/context/token_estimate.py` | Create | Chars→token heuristic, message-list total |
| `core/context/session_compact.py` | Create | LLM-based session history summarisation + DB persistence |
| `core/context/run_compact.py` | Create | LLM-based tool-pair summarisation for running message list |
| `core/runtime/settings.py` | Modify | Three new compact threshold fields |
| `apps/api/jarvis_api/services/chat_sessions.py` | Modify | Store + retrieve `compact_marker` rows |
| `apps/api/jarvis_api/services/prompt_contract.py` | Modify | Auto-compact in transcript builder; `/compact` detection |
| `apps/api/jarvis_api/services/visible_model.py` | Modify | Auto-compact in tool loop; inject "announce compact" note |
| `core/tools/simple_tools.py` | Modify | `compact_context` tool definition + handler |
| `tests/test_context_compact.py` | Create | Unit tests for all new modules |

---

## Design Details

### Token estimation (`core/context/token_estimate.py`)

```python
_CHARS_PER_TOKEN = 3.5  # conservative for Danish/English mix

def estimate_tokens(text: str) -> int:
    return int(len(text) / _CHARS_PER_TOKEN)

def estimate_messages_tokens(messages: list[dict]) -> int:
    total = 0
    for m in messages:
        content = m.get("content") or ""
        if isinstance(content, list):
            content = " ".join(str(c) for c in content)
        total += estimate_tokens(str(content))
    return total
```

### Session compact (`core/context/session_compact.py`)

`compact_session_history(session_id, *, keep_recent, summarise_fn) -> CompactResult`

- Fetches all non-compact-marker messages for the session
- Splits: oldest `N - keep_recent` messages → to summarise; newest `keep_recent` → to keep
- Calls `summarise_fn(messages)` — an injected callable that hits the heartbeat model
- Stores result as `chat_messages` row with `content_type="compact_marker"`
- Returns `CompactResult(freed_tokens, summary_text, marker_id)`

`CompactResult` dataclass:
```python
@dataclass
class CompactResult:
    freed_tokens: int
    summary_text: str
    marker_id: str
```

### Run compact (`core/context/run_compact.py`)

`compact_run_messages(messages, *, keep_recent_pairs, summarise_fn) -> list[dict]`

- Identifies tool-call/result pairs in the message list (assistant messages with `tool_calls` + following `tool` role messages)
- Keeps the last `keep_recent_pairs` pairs untouched
- Calls `summarise_fn` on the older pairs
- Replaces them with a single synthetic `tool` message: `"[KOMPRIMERET KONTEKST: {summary}]"`
- Returns the modified message list

### RuntimeSettings additions

```python
context_compact_threshold_tokens: int = 40_000
context_run_compact_threshold_tokens: int = 60_000
context_keep_recent: int = 20          # messages (session level)
context_keep_recent_pairs: int = 4     # tool pairs (run level)
```

### DB: compact_marker

Stored in existing `chat_messages` table as a new `content_type` value `"compact_marker"`. No schema migration needed if `content_type` is already a free-text column. The `compact_marker` row has:
- `role = "system"`
- `content_type = "compact_marker"`
- `content = summary_text`

`chat_sessions.py` gets two new functions:
- `store_compact_marker(session_id, summary_text) -> str` — returns marker_id
- `get_compact_marker(session_id) -> str | None` — returns most recent summary, or None

### prompt_contract.py changes

In `_build_structured_transcript_messages()`:
1. After building the message list, call `estimate_messages_tokens(messages)`
2. If > `settings.context_compact_threshold_tokens`: run `compact_session_history()`
3. Inject compact_marker as first two messages if one exists:
   ```
   {"role": "user", "content": "[Komprimeret historik fra tidligere i samtalen:\n{summary}]"}
   {"role": "assistant", "content": "Forstået."}
   ```

`/compact` detection: before building the prompt, check if `user_message.strip().lower() == "/compact"`. If yes, run `compact_session_history()` regardless of token count, then set user_message to `"[/compact udført — historik komprimeret]"`.

### visible_model.py changes

In the tool-calling loop, after appending each tool result:
1. Call `estimate_messages_tokens(running_messages)`
2. If > `settings.context_run_compact_threshold_tokens`:
   - Call `compact_run_messages(running_messages, ...)`
   - Inject a system note into the next LLM call:
     ```
     {"role": "system", "content": "Dit arbejdende kontekstvindue er netop komprimeret. Nævn kort at du kompakterer (1 sætning) og fortsæt din opgave."}
     ```
   - Replace `running_messages` with the compacted list

### compact_context tool (simple_tools.py)

Tool definition:
```python
{
    "type": "function",
    "function": {
        "name": "compact_context",
        "description": (
            "Compact your working context to free up space. "
            "Summarises old session history and compresses accumulated tool results. "
            "Use when you notice you are approaching context limits or before starting a very long task."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}
```

Handler `_exec_compact_context(args, *, session_id)`:
- Runs session-level compact via `compact_session_history()`
- Does NOT touch the running message list (run-level compact is infra-triggered only)
- Returns `{"status": "ok", "freed_tokens": N, "summary": "..."}`

Note: `session_id` is passed into the tool handler via the existing tool execution context (same pattern as other session-aware tools).

### Observability

- `context.compacted` eventbus event: `{"layer": "session"|"run"|"both", "freed_tokens": N, "trigger": "auto"|"user"|"jarvis"}`
- `AttentionTrace` extended with `compact_applied: bool`, `compact_freed_tokens: int`
- Mission Control transcript view: `compact_marker` message type renders as `📦 Komprimeret historik` (UI change is optional, can come later)

### Summarisation LLM call

Both session and run compact use the same summarisation callable. The heartbeat model (cheap) is used. Prompt template:

```
System: Du er Jarvis's hukommelseskomprimerings-assistent. Komprimér præcist og bevar alle faktuelle detaljer, beslutninger, fejl og vigtige fund. Max {max_words} ord.
User: {messages_as_text}
```

Session compact: max 400 ord. Run compact: max 300 ord.

---

## Triggers Summary

| Trigger | Layer | How detected |
|---------|-------|-------------|
| `/compact` brugerkommando | Session | `user_message.strip().lower() == "/compact"` in prompt_contract |
| Auto session | Session | `estimate_messages_tokens > context_compact_threshold_tokens` |
| Auto run | Run | `estimate_messages_tokens > context_run_compact_threshold_tokens` in tool loop |
| `compact_context` tool | Both | Jarvis calls the tool explicitly |

---

## Out of Scope

- UI changes for `compact_marker` display (can follow as a separate task)
- Per-model context-limit lookup (use fixed thresholds from settings instead)
- Compacting the system prompt itself (attention budget already handles this)
