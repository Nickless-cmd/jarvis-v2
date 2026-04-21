# Session Search + Channel Awareness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis a `search_sessions` tool to search older sessions across channels (keyword + semantic), and inject explicit channel-awareness into the system prompt so he knows which channel he's currently on and how to behave there.

**Architecture:** New `core/tools/session_search.py` implements the tool (SQL LIKE for keyword, Ollama embeddings for semantic), registered with two lines in `simple_tools.py`. Channel-awareness is a new `_channel_context_section()` in `prompt_contract.py`, using `parse_channel_from_session_title()` in `chat_sessions.py` and workspace files at `workspace/channels/*.md`.

**Tech Stack:** Python 3.11, SQLite (`core.runtime.db.connect`), Ollama (nomic-embed-text via HTTP), pytest + monkeypatch

---

### Task 1: `parse_channel_from_session_title()` helper

**Files:**
- Modify: `core/services/chat_sessions.py` (append at end of file)
- Create: `tests/services/test_parse_channel.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_parse_channel.py`:

```python
"""Tests for parse_channel_from_session_title."""
from core.services.chat_sessions import parse_channel_from_session_title


def test_discord_dm():
    channel, detail = parse_channel_from_session_title("Discord DM")
    assert channel == "discord"
    assert detail == "DM"


def test_discord_public_channel():
    channel, detail = parse_channel_from_session_title("Discord #123456789")
    assert channel == "discord"
    assert detail == "#123456789"


def test_telegram_dm():
    channel, detail = parse_channel_from_session_title("Telegram DM")
    assert channel == "telegram"
    assert detail == "DM"


def test_webchat_new_chat():
    channel, detail = parse_channel_from_session_title("New chat")
    assert channel == "webchat"
    assert detail is None


def test_webchat_none_input():
    channel, detail = parse_channel_from_session_title(None)
    assert channel == "webchat"
    assert detail is None


def test_unknown_title():
    channel, detail = parse_channel_from_session_title("Something weird")
    assert channel == "unknown"
    assert detail is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/services/test_parse_channel.py -v
```
Expected: FAIL with `ImportError: cannot import name 'parse_channel_from_session_title'`

- [ ] **Step 3: Implement the function**

Append to the end of `core/services/chat_sessions.py`:

```python
def parse_channel_from_session_title(title: str | None) -> tuple[str, str | None]:
    """Parse channel type and detail from a session title.

    Returns (channel_type, channel_detail) where channel_type is one of:
    'discord', 'telegram', 'webchat', 'unknown'.

    Examples:
        "Discord DM"         -> ("discord", "DM")
        "Discord #123456789" -> ("discord", "#123456789")
        "Telegram DM"        -> ("telegram", "DM")
        "New chat"           -> ("webchat", None)
        None                 -> ("webchat", None)
        "Something weird"    -> ("unknown", None)
    """
    if not title or title.strip() in ("New chat", ""):
        return ("webchat", None)
    t = title.strip()
    if t == "Discord DM":
        return ("discord", "DM")
    if t.startswith("Discord #"):
        return ("discord", t[len("Discord "):])
    if t.startswith("Discord"):
        return ("discord", None)
    if t == "Telegram DM":
        return ("telegram", "DM")
    if t.startswith("Telegram"):
        return ("telegram", None)
    return ("unknown", None)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/services/test_parse_channel.py -v
```
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add core/services/chat_sessions.py tests/services/test_parse_channel.py
git commit -m "feat: add parse_channel_from_session_title helper"
```

---

### Task 2: Workspace channel description files

**Files:**
- Create: `workspace/channels/discord.md`
- Create: `workspace/channels/telegram.md`
- Create: `workspace/channels/webchat.md`

- [ ] **Step 1: Create `workspace/channels/discord.md`**

```markdown
Discord bruges til uformelle samtaler, hurtige spørgsmål og teknisk hjælp.
Svar gerne kortere og mere direkte end i webchat.
Brug en afslappet tone — undgå lange punktlister med mindre de er nødvendige.
```

- [ ] **Step 2: Create `workspace/channels/telegram.md`**

```markdown
Telegram bruges primært til notifikationer og korte beskeder.
Svar kort og præcist — Telegram er til hurtig kommunikation.
Undgå lange svar med mindre brugeren specifikt beder om det.
```

- [ ] **Step 3: Create `workspace/channels/webchat.md`**

```markdown
Webchat er til dybdegående samtaler og teknisk arbejde.
Du kan bruge længere svar og detaljerede forklaringer her.
```

- [ ] **Step 4: Commit**

```bash
git add workspace/channels/
git commit -m "feat: add workspace channel description files"
```

---

### Task 3: `_channel_context_section()` in prompt_contract.py

**Files:**
- Modify: `core/services/prompt_contract.py` (add functions near `_workspace_file_section`, around line 1140)
- Create: `tests/services/test_channel_context_section.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_channel_context_section.py`:

```python
"""Tests for _channel_context_section in prompt_contract."""
from pathlib import Path
from unittest.mock import patch


def test_discord_dm_with_workspace_file(tmp_path):
    channels_dir = tmp_path / "channels"
    channels_dir.mkdir()
    (channels_dir / "discord.md").write_text("Discord er uformelt.")

    with patch("core.services.prompt_contract._channel_workspace_path", return_value=channels_dir):
        with patch("core.services.chat_sessions.get_chat_session", return_value={"title": "Discord DM", "session_id": "s1"}):
            from core.services.prompt_contract import _channel_context_section
            result = _channel_context_section("s1")

    assert result is not None
    assert "Discord DM" in result
    assert "Discord er uformelt." in result


def test_discord_dm_without_workspace_file(tmp_path):
    channels_dir = tmp_path / "channels"
    channels_dir.mkdir()
    # No discord.md

    with patch("core.services.prompt_contract._channel_workspace_path", return_value=channels_dir):
        with patch("core.services.chat_sessions.get_chat_session", return_value={"title": "Discord DM", "session_id": "s1"}):
            from core.services.prompt_contract import _channel_context_section
            result = _channel_context_section("s1")

    assert result is not None
    assert "Discord DM" in result


def test_none_session_id_returns_none():
    from core.services.prompt_contract import _channel_context_section
    assert _channel_context_section(None) is None


def test_webchat_without_workspace_file_returns_none(tmp_path):
    channels_dir = tmp_path / "channels"
    channels_dir.mkdir()
    # No webchat.md

    with patch("core.services.prompt_contract._channel_workspace_path", return_value=channels_dir):
        with patch("core.services.chat_sessions.get_chat_session", return_value={"title": "New chat", "session_id": "s2"}):
            from core.services.prompt_contract import _channel_context_section
            result = _channel_context_section("s2")

    assert result is None


def test_unknown_channel_returns_none(tmp_path):
    channels_dir = tmp_path / "channels"
    channels_dir.mkdir()

    with patch("core.services.prompt_contract._channel_workspace_path", return_value=channels_dir):
        with patch("core.services.chat_sessions.get_chat_session", return_value={"title": "Something weird", "session_id": "s3"}):
            from core.services.prompt_contract import _channel_context_section
            result = _channel_context_section("s3")

    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/services/test_channel_context_section.py -v
```
Expected: FAIL with `ImportError: cannot import name '_channel_context_section'`

- [ ] **Step 3: Add functions to prompt_contract.py**

Find `_workspace_file_section` (around line 1117) and add these two functions directly after it:

```python
def _channel_workspace_path() -> "Path":
    from pathlib import Path
    return Path(__file__).resolve().parent.parent.parent / "workspace" / "channels"


def _channel_context_section(session_id: str | None) -> str | None:
    """Returns current channel context for the prompt, or None.

    Injects channel name + optional workspace description for Discord/Telegram.
    Webchat is the implicit default — only injected if webchat.md exists.
    Unknown channel titles are silently skipped.
    """
    if not session_id:
        return None
    from core.services.chat_sessions import get_chat_session, parse_channel_from_session_title
    session = get_chat_session(session_id)
    if not session:
        return None
    title = str(session.get("title") or "").strip()
    channel_type, channel_detail = parse_channel_from_session_title(title)
    if channel_type == "unknown":
        return None
    channel_file = _channel_workspace_path() / f"{channel_type}.md"
    if channel_type == "webchat" and not channel_file.exists():
        return None
    if channel_detail:
        label = f"{channel_type.capitalize()} {channel_detail}"
    else:
        label = channel_type.capitalize()
    lines = ["## Current channel", f"Du kommunikerer via {label}."]
    if channel_file.exists():
        desc = channel_file.read_text(encoding="utf-8", errors="replace").strip()
        if desc:
            lines.append(desc)
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/services/test_channel_context_section.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add core/services/prompt_contract.py tests/services/test_channel_context_section.py
git commit -m "feat: add _channel_context_section to prompt_contract"
```

---

### Task 4: Wire channel section into prompt assembly

**Files:**
- Modify: `core/services/prompt_contract.py` (find `build_visible_chat_prompt_assembly`, around line 274)

The channel section should be injected early — after the identity/soul sections, before memory recall. Find the call to `_visible_memory_recall_bundle_section` (around line 414) and add the channel section just before it.

- [ ] **Step 1: Find the injection point**

```bash
conda activate ai && grep -n "_visible_memory_recall_bundle_section\|recall_bundle\|## Current" core/services/prompt_contract.py | head -20
```

Note the line numbers for `recall_bundle =` and the surrounding `parts.append(...)` calls.

- [ ] **Step 2: Add injection in `build_visible_chat_prompt_assembly`**

Find the block where `recall_bundle` is built (around line 414-421) and add before it:

```python
    channel_section = _channel_context_section(session_id)
    if channel_section:
        parts.append(channel_section)
        derived_inputs.append("channel context")
```

The `parts` list and `derived_inputs` list are already used in this function — this follows the exact same pattern as other conditional sections.

- [ ] **Step 3: Run existing test suite to verify no regressions**

```bash
conda activate ai && pytest tests/ -v --timeout=30 -x 2>&1 | tail -30
```
Expected: all previously passing tests still pass.

- [ ] **Step 4: Commit**

```bash
git add core/services/prompt_contract.py
git commit -m "feat: inject channel context into visible prompt assembly"
```

---

### Task 5: `session_search.py` — keyword search

**Files:**
- Create: `core/tools/session_search.py`
- Create: `tests/tools/test_session_search.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/test_session_search.py`:

```python
"""Tests for session_search tool."""
import pytest
from unittest.mock import patch, MagicMock


def _make_row(role, content, created_at, session_id, title):
    row = MagicMock()
    row.__getitem__ = lambda self, k: {
        "role": role, "content": content, "created_at": created_at,
        "session_id": session_id, "session_title": title,
    }[k]
    return row


def test_keyword_search_returns_results(monkeypatch):
    from core.tools.session_search import exec_search_sessions

    fake_rows = [
        _make_row("user", "hej discord", "2026-04-19T10:00:00", "s1", "Discord DM"),
        _make_row("assistant", "hej tilbage", "2026-04-19T10:01:00", "s1", "Discord DM"),
    ]

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.fetchall.return_value = fake_rows

    with patch("core.tools.session_search.connect", return_value=mock_conn):
        result = exec_search_sessions({"query": "hej", "mode": "keyword"})

    assert result["status"] == "ok"
    assert result["count"] == 2
    assert result["results"][0]["channel"] == "discord"
    assert result["results"][0]["session_title"] == "Discord DM"


def test_channel_filter_discord_only(monkeypatch):
    from core.tools.session_search import exec_search_sessions

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.fetchall.return_value = []

    with patch("core.tools.session_search.connect", return_value=mock_conn):
        result = exec_search_sessions({"query": "test", "mode": "keyword", "channel": "discord"})

    # Verify the SQL contained the Discord filter
    call_args = mock_conn.execute.call_args
    assert "Discord" in call_args[0][0]
    assert result["count"] == 0


def test_empty_query_returns_error():
    from core.tools.session_search import exec_search_sessions
    result = exec_search_sessions({"query": ""})
    assert result["status"] == "error"
    assert "query" in result["error"]


def test_no_results_returns_ok():
    from core.tools.session_search import exec_search_sessions

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.fetchall.return_value = []

    with patch("core.tools.session_search.connect", return_value=mock_conn):
        result = exec_search_sessions({"query": "xyzzy", "mode": "keyword"})

    assert result["status"] == "ok"
    assert result["count"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/tools/test_session_search.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'core.tools.session_search'`

- [ ] **Step 3: Create `core/tools/session_search.py` with keyword search**

```python
"""search_sessions tool — cross-channel session search with keyword and semantic modes."""
from __future__ import annotations

from typing import Any

from core.runtime.db import connect
from core.services.chat_sessions import parse_channel_from_session_title

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_sessions",
        "description": (
            "Search across all past chat sessions from all channels (Discord, Telegram, webchat). "
            "Supports keyword matching and semantic similarity search. "
            "Use to recall what was discussed on a specific channel, or to find conversations about a topic."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for — a topic, phrase, or concept.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["keyword", "semantic", "both"],
                    "description": "Search mode. 'keyword' = exact phrase match, 'semantic' = meaning-based, 'both' = combined (default).",
                },
                "channel": {
                    "type": "string",
                    "enum": ["discord", "telegram", "webchat", "all"],
                    "description": "Filter by channel. Default: 'all'.",
                },
                "since": {
                    "type": "string",
                    "description": "Only return results after this ISO date, e.g. '2026-04-01'.",
                },
                "until": {
                    "type": "string",
                    "description": "Only return results before this ISO date, e.g. '2026-04-20'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 10, max 30).",
                },
            },
            "required": ["query"],
        },
    },
}


# --- Channel filter helpers ---

_CHANNEL_TITLE_PATTERNS: dict[str, str] = {
    "discord": "Discord%",
    "telegram": "Telegram%",
    "webchat": "New chat",
}


def _channel_title_filter(channel: str) -> tuple[str, list[Any]]:
    """Returns (SQL WHERE clause fragment, params) for channel filter."""
    if channel == "all" or channel not in _CHANNEL_TITLE_PATTERNS:
        return ("", [])
    pattern = _CHANNEL_TITLE_PATTERNS[channel]
    if channel == "webchat":
        return ("AND (s.title = ? OR s.title IS NULL)", [pattern])
    return ("AND s.title LIKE ?", [pattern])


# --- Keyword search ---

def _keyword_search(
    query: str,
    *,
    channel: str,
    since: str | None,
    until: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    channel_clause, channel_params = _channel_title_filter(channel)
    date_clauses = []
    date_params: list[str] = []
    if since:
        date_clauses.append("AND m.created_at >= ?")
        date_params.append(since)
    if until:
        date_clauses.append("AND m.created_at <= ?")
        date_params.append(until)

    sql = f"""
        SELECT m.message_id, m.role, m.content, m.created_at, m.session_id,
               s.title AS session_title
        FROM chat_messages m
        LEFT JOIN chat_sessions s ON s.session_id = m.session_id
        WHERE m.content LIKE ?
          AND m.role IN ('user', 'assistant')
          {channel_clause}
          {' '.join(date_clauses)}
        ORDER BY m.id DESC
        LIMIT ?
    """
    params = [f"%{query}%"] + channel_params + date_params + [limit]

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [_row_to_result(row, match_type="keyword") for row in rows]


def _row_to_result(row: Any, *, match_type: str) -> dict[str, Any]:
    content = str(row["content"] or "")
    title = str(row["session_title"] or row["session_id"] or "")
    channel_type, channel_detail = parse_channel_from_session_title(title)
    return {
        "message_id": row["message_id"],
        "session_id": row["session_id"],
        "session_title": title,
        "channel": channel_type,
        "channel_detail": channel_detail,
        "role": row["role"],
        "content": content[:2000] + ("…" if len(content) > 2000 else ""),
        "created_at": str(row["created_at"] or "")[:19],
        "match_type": match_type,
    }


# --- Semantic search ---

def _embed_query(text: str) -> list[float] | None:
    """Embed text via Ollama. Returns None if unavailable."""
    try:
        import json
        import urllib.request

        payload = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/embeddings",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())["embedding"]
    except Exception:
        return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _semantic_search(
    query: str,
    *,
    channel: str,
    since: str | None,
    until: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Embed query, fetch candidate messages, rank by cosine similarity."""
    query_embedding = _embed_query(query)
    if query_embedding is None:
        return []

    channel_clause, channel_params = _channel_title_filter(channel)
    date_clauses = []
    date_params: list[str] = []
    if since:
        date_clauses.append("AND m.created_at >= ?")
        date_params.append(since)
    if until:
        date_clauses.append("AND m.created_at <= ?")
        date_params.append(until)

    # Fetch a candidate pool (300 recent messages) to rank semantically
    sql = f"""
        SELECT m.message_id, m.role, m.content, m.created_at, m.session_id,
               s.title AS session_title
        FROM chat_messages m
        LEFT JOIN chat_sessions s ON s.session_id = m.session_id
        WHERE m.role IN ('user', 'assistant')
          {channel_clause}
          {' '.join(date_clauses)}
        ORDER BY m.id DESC
        LIMIT 300
    """
    params = channel_params + date_params

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    if not rows:
        return []

    # Embed candidates and rank
    scored: list[tuple[float, Any]] = []
    for row in rows:
        content = str(row["content"] or "")[:800]
        row_embedding = _embed_query(content)
        if row_embedding is None:
            continue
        score = _cosine_similarity(query_embedding, row_embedding)
        scored.append((score, row))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [_row_to_result(row, match_type="semantic") for _, row in scored[:limit]]


# --- Combined search ---

def _merge_results(
    keyword_results: list[dict],
    semantic_results: list[dict],
    limit: int,
) -> list[dict]:
    """Merge and deduplicate, semantic hits ranked first."""
    seen: set[str] = set()
    merged: list[dict] = []
    for r in semantic_results:
        mid = r["message_id"]
        if mid not in seen:
            seen.add(mid)
            merged.append({**r, "match_type": "semantic"})
    for r in keyword_results:
        mid = r["message_id"]
        if mid not in seen:
            seen.add(mid)
            merged.append({**r, "match_type": "keyword"})
        else:
            # Upgrade match_type for items found by both
            for m in merged:
                if m["message_id"] == mid:
                    m["match_type"] = "both"
    return merged[:limit]


# --- Tool entry point ---

def exec_search_sessions(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}

    mode = str(args.get("mode") or "both")
    channel = str(args.get("channel") or "all")
    since = args.get("since") or None
    until = args.get("until") or None
    limit = min(int(args.get("limit") or 10), 30)

    try:
        keyword_results: list[dict] = []
        semantic_results: list[dict] = []
        fallback_note = ""

        if mode in ("keyword", "both"):
            keyword_results = _keyword_search(
                query, channel=channel, since=since, until=until, limit=limit
            )

        if mode in ("semantic", "both"):
            semantic_results = _semantic_search(
                query, channel=channel, since=since, until=until, limit=limit
            )
            if not semantic_results and mode == "semantic":
                fallback_note = " (Ollama unavailable, no semantic results)"
            elif not semantic_results and mode == "both":
                fallback_note = " (semantic unavailable, keyword only)"

        if mode == "both":
            results = _merge_results(keyword_results, semantic_results, limit)
        elif mode == "semantic":
            results = semantic_results or keyword_results  # fallback to keyword
        else:
            results = keyword_results

        if not results:
            return {
                "status": "ok",
                "count": 0,
                "text": f"No sessions found matching '{query}'{fallback_note}",
                "results": [],
            }

        lines = [f"Found {len(results)} result(s) for '{query}'{fallback_note}:\n"]
        for r in results:
            ts = r["created_at"][:16]
            ch = r["channel_detail"] or r["channel"]
            lines.append(f"[{ts}] {r['role'].upper()} via {ch} ({r['match_type']}):\n{r['content']}\n")

        return {
            "status": "ok",
            "count": len(results),
            "results": results,
            "text": "\n".join(lines),
        }

    except Exception as exc:
        return {"status": "error", "error": str(exc)}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/tools/test_session_search.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add core/tools/session_search.py tests/tools/test_session_search.py
git commit -m "feat: add search_sessions tool with keyword and semantic search"
```

---

### Task 6: Register `search_sessions` tool in simple_tools.py

**Files:**
- Modify: `core/tools/simple_tools.py` (two additions only)

- [ ] **Step 1: Find the TOOL_DEFINITIONS list and execution map**

```bash
grep -n "search_chat_history\|TOOL_DEFINITIONS\|TOOL_EXECUTION_MAP" core/tools/simple_tools.py | head -20
```

Note the exact variable names and the line where `search_chat_history` appears in the execution map.

- [ ] **Step 2: Add tool definition import at top of simple_tools.py**

Find the existing imports at the top of `core/tools/simple_tools.py` and add:

```python
from core.tools.session_search import TOOL_DEFINITION as _SESSION_SEARCH_TOOL_DEF
from core.tools.session_search import exec_search_sessions as _exec_search_sessions
```

- [ ] **Step 3: Add to TOOL_DEFINITIONS list**

Find where `search_chat_history` tool dict is defined in `TOOL_DEFINITIONS` (around line 848). Add the new tool after it:

```python
    _SESSION_SEARCH_TOOL_DEF,
```

- [ ] **Step 4: Add to execution map**

Find the execution map entry for `search_chat_history` (around line 4300). Add after it:

```python
    "search_sessions": _exec_search_sessions,
```

- [ ] **Step 5: Verify import works**

```bash
conda activate ai && python -c "from core.tools.simple_tools import TOOL_DEFINITIONS; names = [t['function']['name'] for t in TOOL_DEFINITIONS]; print('search_sessions' in names)"
```
Expected: `True`

- [ ] **Step 6: Run full test suite**

```bash
conda activate ai && pytest tests/ -v --timeout=30 -x 2>&1 | tail -30
```
Expected: all previously passing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add core/tools/simple_tools.py
git commit -m "feat: register search_sessions tool"
```

---

### Task 7: Manual smoke test

- [ ] **Step 1: Restart jarvis-runtime**

```bash
sudo systemctl restart jarvis-runtime && sleep 3 && sudo journalctl -u jarvis-runtime -n 30
```
Expected: service starts successfully, no import errors.

- [ ] **Step 2: Verify channel section appears in logs for Discord message**

Send a test message via Discord DM and check runtime logs:

```bash
sudo journalctl -u jarvis-runtime -f | grep -i "channel\|current channel"
```
Expected: channel context section included in prompt (no error).

- [ ] **Step 3: Ask Jarvis directly**

In Discord DM, send: "Hvilken kanal er vi på lige nu?"

Expected: Jarvis svarer eksplicit at han er på Discord DM — ikke webchat.

- [ ] **Step 4: Test search_sessions tool**

In any chat, ask: "Brug search_sessions til at finde samtaler om Telegram gateway"

Expected: Jarvis kalder `search_sessions` med query="Telegram gateway" og returnerer resultater fra ældre sessioner.
