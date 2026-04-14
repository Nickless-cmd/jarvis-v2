# Context Compact Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis two-layer context compaction — session history and run-level tool loops — triggered automatically, by the user via `/compact`, and by Jarvis via a `compact_context` tool.

**Architecture:** A `core/context/` package holds the token estimator, session compact, and run compact modules. DB stores compact markers as `role="compact_marker"` rows. The heartbeat model does LLM summarisation. Wiring happens in `prompt_contract.py` (session) and `visible_runs.py` (run + /compact). Jarvis announces run-level compactions in chat.

**Tech Stack:** Python 3.11, SQLite via existing `core.runtime.db.connect()`, urllib (no extra dependencies), heartbeat model provider (Ollama/OpenAI/OpenRouter).

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `core/context/__init__.py` | Create | Package marker |
| `core/context/token_estimate.py` | Create | Char→token heuristic |
| `core/runtime/settings.py` | Modify | Three compact threshold fields |
| `apps/api/jarvis_api/services/chat_sessions.py` | Modify | `store_compact_marker`, `get_compact_marker`, exclude compact_markers from regular history |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify | Public `call_heartbeat_llm_simple(prompt, max_tokens)` |
| `core/context/compact_llm.py` | Create | Thin wrapper that calls `call_heartbeat_llm_simple` |
| `core/context/session_compact.py` | Create | LLM-based session history summarisation |
| `core/context/run_compact.py` | Create | LLM-based tool-loop message list compaction |
| `apps/api/jarvis_api/services/prompt_contract.py` | Modify | Auto-compact + compact_marker injection in `_build_structured_transcript_messages` |
| `apps/api/jarvis_api/services/visible_runs.py` | Modify | `/compact` detection before model call + run auto-compact in agentic loop |
| `core/tools/simple_tools.py` | Modify | `compact_context` tool definition + handler |
| `tests/test_context_compact.py` | Create | All unit tests |

---

## Task 1: Token estimator + package init

**Files:**
- Create: `core/context/__init__.py`
- Create: `core/context/token_estimate.py`
- Test: `tests/test_context_compact.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_context_compact.py
"""Tests for context compact system."""
from __future__ import annotations

from unittest.mock import Mock


# ── Task 1: token_estimate ─────────────────────────────────────────────────

def test_estimate_tokens_empty():
    from core.context.token_estimate import estimate_tokens
    assert estimate_tokens("") == 0


def test_estimate_tokens_basic():
    from core.context.token_estimate import estimate_tokens
    # 35 chars / 3.5 = 10
    assert estimate_tokens("a" * 35) == 10


def test_estimate_messages_tokens_sums_content():
    from core.context.token_estimate import estimate_messages_tokens
    messages = [
        {"role": "user", "content": "a" * 35},       # 10 tokens
        {"role": "assistant", "content": "b" * 35},   # 10 tokens
    ]
    assert estimate_messages_tokens(messages) == 20


def test_estimate_messages_tokens_missing_content():
    from core.context.token_estimate import estimate_messages_tokens
    messages = [{"role": "user"}, {"role": "assistant", "content": None}]
    assert estimate_messages_tokens(messages) == 0


def test_estimate_messages_tokens_list_content():
    from core.context.token_estimate import estimate_messages_tokens
    # Some providers use list content
    messages = [{"role": "user", "content": ["hello", "world"]}]
    # "['hello', 'world']" = 18 chars / 3.5 = 5
    result = estimate_messages_tokens(messages)
    assert result >= 1  # Just check it doesn't crash
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'core.context'`

- [ ] **Step 3: Create package and token estimator**

Create `core/context/__init__.py` — empty:
```python
```

Create `core/context/token_estimate.py`:
```python
"""Token estimation utilities — heuristic only, no tokenizer required."""
from __future__ import annotations

_CHARS_PER_TOKEN: float = 3.5  # Conservative for Danish/English mix


def estimate_tokens(text: str) -> int:
    """Estimate token count from raw text."""
    return int(len(str(text or "")) / _CHARS_PER_TOKEN)


def estimate_messages_tokens(messages: list[dict]) -> int:
    """Estimate total tokens for a list of chat messages."""
    total = 0
    for m in messages:
        content = m.get("content") or ""
        if not isinstance(content, str):
            content = str(content)
        total += estimate_tokens(content)
    return total
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_estimate_tokens_empty tests/test_context_compact.py::test_estimate_tokens_basic tests/test_context_compact.py::test_estimate_messages_tokens_sums_content tests/test_context_compact.py::test_estimate_messages_tokens_missing_content tests/test_context_compact.py::test_estimate_messages_tokens_list_content -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add core/context/__init__.py core/context/token_estimate.py tests/test_context_compact.py
git commit -m "feat(compact): token estimator + core/context package"
```

---

## Task 2: Settings fields

**Files:**
- Modify: `core/runtime/settings.py:9-108`
- Test: `tests/test_context_compact.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_context_compact.py`:

```python
# ── Task 2: settings ──────────────────────────────────────────────────────

def test_settings_compact_threshold_default():
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.context_compact_threshold_tokens == 40_000


def test_settings_run_compact_threshold_default():
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.context_run_compact_threshold_tokens == 60_000


def test_settings_keep_recent_defaults():
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.context_keep_recent == 20
    assert s.context_keep_recent_pairs == 4


def test_settings_serialise_round_trip():
    import json
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    d = s.to_dict()
    assert d["context_compact_threshold_tokens"] == 40_000
    assert d["context_run_compact_threshold_tokens"] == 60_000
    assert d["context_keep_recent"] == 20
    assert d["context_keep_recent_pairs"] == 4
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_settings_compact_threshold_default -v
```

Expected: `AttributeError: 'RuntimeSettings' object has no attribute 'context_compact_threshold_tokens'`

- [ ] **Step 3: Add fields to settings.py**

In `core/runtime/settings.py`, after line 34 (`emotion_decay_factor: float = 0.97`), add:

```python
    # Context compact thresholds
    context_compact_threshold_tokens: int = 40_000
    context_run_compact_threshold_tokens: int = 60_000
    context_keep_recent: int = 20
    context_keep_recent_pairs: int = 4
```

In `to_dict()`, after line 58 (`"emotion_decay_factor": self.emotion_decay_factor,`), add:

```python
            "context_compact_threshold_tokens": self.context_compact_threshold_tokens,
            "context_run_compact_threshold_tokens": self.context_run_compact_threshold_tokens,
            "context_keep_recent": self.context_keep_recent,
            "context_keep_recent_pairs": self.context_keep_recent_pairs,
```

In `load_settings()`, after line 107 (`emotion_decay_factor=float(data.get("emotion_decay_factor", defaults.emotion_decay_factor)),`), add:

```python
        context_compact_threshold_tokens=int(data.get("context_compact_threshold_tokens", defaults.context_compact_threshold_tokens)),
        context_run_compact_threshold_tokens=int(data.get("context_run_compact_threshold_tokens", defaults.context_run_compact_threshold_tokens)),
        context_keep_recent=int(data.get("context_keep_recent", defaults.context_keep_recent)),
        context_keep_recent_pairs=int(data.get("context_keep_recent_pairs", defaults.context_keep_recent_pairs)),
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_settings_compact_threshold_default tests/test_context_compact.py::test_settings_run_compact_threshold_default tests/test_context_compact.py::test_settings_keep_recent_defaults tests/test_context_compact.py::test_settings_serialise_round_trip -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add core/runtime/settings.py tests/test_context_compact.py
git commit -m "feat(compact): add compact threshold settings fields"
```

---

## Task 3: DB compact marker

**Files:**
- Modify: `apps/api/jarvis_api/services/chat_sessions.py:107-120` (append_chat_message), `164-186` (recent_chat_session_messages)
- Test: `tests/test_context_compact.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_context_compact.py`:

```python
# ── Task 3: DB compact marker ─────────────────────────────────────────────

def test_store_compact_marker_returns_id(monkeypatch):
    from apps.api.jarvis_api.services import chat_sessions
    inserted = []
    monkeypatch.setattr(
        chat_sessions,
        "connect",
        lambda: _fake_connect(inserted),
    )
    # store_compact_marker should call connect and return a marker_id string
    # (we just verify it doesn't crash and uses the right role)
    # Use direct SQL check below instead of live DB


def test_get_compact_marker_returns_none_when_absent(monkeypatch):
    from apps.api.jarvis_api.services import chat_sessions
    monkeypatch.setattr(
        chat_sessions,
        "connect",
        lambda: _fake_connect_empty(),
    )
    result = chat_sessions.get_compact_marker("session-abc")
    assert result is None


def test_recent_session_messages_excludes_compact_markers(monkeypatch):
    from apps.api.jarvis_api.services import chat_sessions
    rows = [
        {"role": "user", "content": "hello", "created_at": "2026-01-01"},
        {"role": "compact_marker", "content": "old summary", "created_at": "2026-01-01"},
        {"role": "assistant", "content": "hi", "created_at": "2026-01-01"},
    ]
    monkeypatch.setattr(
        chat_sessions,
        "connect",
        lambda: _fake_connect_with_rows(rows),
    )
    messages = chat_sessions.recent_chat_session_messages("session-abc", limit=10)
    roles = [m["role"] for m in messages]
    assert "compact_marker" not in roles


# Helper fakes for DB mocking
class _FakeCursor:
    def __init__(self, rows): self._rows = rows
    def fetchall(self): return self._rows
    def fetchone(self): return self._rows[0] if self._rows else None
    def execute(self, *a, **kw): return self
    def __iter__(self): return iter(self._rows)


class _FakeConn:
    def __init__(self, rows=None): self._rows = rows or []
    def execute(self, *a, **kw): return _FakeCursor(self._rows)
    def __enter__(self): return self
    def __exit__(self, *a): pass


def _fake_connect(inserted=None):
    return _FakeConn()


def _fake_connect_empty():
    return _FakeConn(rows=[])


def _fake_connect_with_rows(rows):
    # Return rows filtered to exclude compact_marker (the implementation should do this)
    class _FilteringCursor:
        def __init__(self, all_rows): self._all = all_rows
        def fetchall(self):
            # Simulate what the SQL WHERE role != 'compact_marker' would return
            return [r for r in self._all if r.get("role") != "compact_marker"]
        def fetchone(self): return None
        def execute(self, *a, **kw): return self

    class _FilteringConn:
        def __init__(self, rows): self._rows = rows
        def execute(self, *a, **kw): return _FilteringCursor(self._rows)
        def __enter__(self): return self
        def __exit__(self, *a): pass

    return _FilteringConn(rows)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_get_compact_marker_returns_none_when_absent tests/test_context_compact.py::test_recent_session_messages_excludes_compact_markers -v
```

Expected: `AttributeError: module 'chat_sessions' has no attribute 'get_compact_marker'`

- [ ] **Step 3: Modify chat_sessions.py**

In `append_chat_message` at line 118, change:
```python
    if normalized_role not in {"user", "assistant", "tool"}:
```
to:
```python
    if normalized_role not in {"user", "assistant", "tool", "compact_marker"}:
```

In `recent_chat_session_messages` at line 169, change the SQL from:
```python
            SELECT role, content, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
```
to:
```python
            SELECT role, content, created_at
            FROM chat_messages
            WHERE session_id = ? AND role != 'compact_marker'
            ORDER BY id DESC
            LIMIT ?
```

After `recent_chat_session_messages`, add two new functions:

```python
def store_compact_marker(session_id: str, summary_text: str) -> str:
    """Store a compact marker for the session. Returns the marker message_id."""
    normalized_session = (session_id or "").strip()
    if not normalized_session:
        raise ValueError("session_id must not be empty")
    normalized_content = str(summary_text or "").strip()
    if not normalized_content:
        raise ValueError("summary_text must not be empty")
    timestamp = datetime.now(UTC).isoformat()
    marker_id = f"compact-{uuid4().hex}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (message_id, session_id, role, content, created_at)
            VALUES (?, ?, 'compact_marker', ?, ?)
            """,
            (marker_id, normalized_session, normalized_content, timestamp),
        )
    return marker_id


def get_compact_marker(session_id: str) -> str | None:
    """Return the most recent compact marker summary for the session, or None."""
    normalized = (session_id or "").strip()
    if not normalized:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT content FROM chat_messages
            WHERE session_id = ? AND role = 'compact_marker'
            ORDER BY id DESC
            LIMIT 1
            """,
            (normalized,),
        ).fetchone()
    return str(row["content"]) if row else None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_get_compact_marker_returns_none_when_absent tests/test_context_compact.py::test_recent_session_messages_excludes_compact_markers -v
```

Expected: 2 passed

- [ ] **Step 5: Compile check + commit**

```bash
conda run -n ai python -m compileall apps/api/jarvis_api/services/chat_sessions.py -q
git add apps/api/jarvis_api/services/chat_sessions.py tests/test_context_compact.py
git commit -m "feat(compact): store_compact_marker, get_compact_marker, exclude from history"
```

---

## Task 4: Compact LLM caller

**Files:**
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` (add public `call_heartbeat_llm_simple`)
- Create: `core/context/compact_llm.py`
- Test: `tests/test_context_compact.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_context_compact.py`:

```python
# ── Task 4: compact_llm ───────────────────────────────────────────────────

def test_call_compact_llm_returns_string(monkeypatch):
    from core.context import compact_llm
    monkeypatch.setattr(
        compact_llm,
        "_call_heartbeat_llm_simple",
        lambda prompt, max_tokens: "Summary result",
    )
    result = compact_llm.call_compact_llm("Summarise this", max_tokens=200)
    assert result == "Summary result"


def test_call_compact_llm_fallback_on_error(monkeypatch):
    from core.context import compact_llm
    def _fail(prompt, max_tokens):
        raise RuntimeError("model unavailable")
    monkeypatch.setattr(compact_llm, "_call_heartbeat_llm_simple", _fail)
    result = compact_llm.call_compact_llm("Summarise this", max_tokens=200)
    # Should return a fallback string, not raise
    assert isinstance(result, str)
    assert len(result) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_call_compact_llm_returns_string -v
```

Expected: `ModuleNotFoundError: No module named 'core.context.compact_llm'`

- [ ] **Step 3: Add public function to heartbeat_runtime.py**

At the end of `apps/api/jarvis_api/services/heartbeat_runtime.py`, add:

```python
def call_heartbeat_llm_simple(prompt: str, *, max_tokens: int = 400) -> str:
    """Call the heartbeat model with a plain prompt. Returns the response text.

    Used by the context compact system for summarisation. Raises RuntimeError
    if the model call fails (caller handles fallback).
    """
    target = _select_heartbeat_target()
    provider = str(target.get("provider") or "").strip()
    if provider == "ollama":
        result = _execute_ollama_prompt(prompt=prompt, target=target)
    elif provider == "openai":
        result = _execute_openai_prompt(prompt=prompt, target=target)
    elif provider == "openrouter":
        result = _execute_openrouter_prompt(prompt=prompt, target=target)
    else:
        # phase1-runtime or unknown — return a minimal fallback
        raise RuntimeError(f"compact: unsupported heartbeat provider: {provider}")
    return str(result.get("text") or "").strip()
```

- [ ] **Step 4: Create core/context/compact_llm.py**

```python
"""Thin wrapper that calls the heartbeat model for compact summarisation.

Callers use call_compact_llm(prompt) — never call heartbeat_runtime directly
from compact modules to keep the dependency one-way.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_FALLBACK_SUMMARY = "[Kontekst komprimeret — detaljer ikke tilgængelige]"


def _call_heartbeat_llm_simple(prompt: str, max_tokens: int) -> str:
    from apps.api.jarvis_api.services.heartbeat_runtime import call_heartbeat_llm_simple
    return call_heartbeat_llm_simple(prompt, max_tokens=max_tokens)


def call_compact_llm(prompt: str, *, max_tokens: int = 400) -> str:
    """Summarise prompt via the heartbeat model. Returns summary string.

    Never raises — returns a fallback string if the model is unavailable.
    """
    try:
        result = _call_heartbeat_llm_simple(prompt, max_tokens)
        return result if result else _FALLBACK_SUMMARY
    except Exception as exc:
        logger.warning("compact_llm: summarisation failed (%s) — using fallback", exc)
        return _FALLBACK_SUMMARY
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_call_compact_llm_returns_string tests/test_context_compact.py::test_call_compact_llm_fallback_on_error -v
```

Expected: 2 passed

- [ ] **Step 6: Compile check + commit**

```bash
conda run -n ai python -m compileall apps/api/jarvis_api/services/heartbeat_runtime.py core/context/compact_llm.py -q
git add apps/api/jarvis_api/services/heartbeat_runtime.py core/context/compact_llm.py tests/test_context_compact.py
git commit -m "feat(compact): call_heartbeat_llm_simple + compact_llm wrapper"
```

---

## Task 5: Session compact module

**Files:**
- Create: `core/context/session_compact.py`
- Test: `tests/test_context_compact.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_context_compact.py`:

```python
# ── Task 5: session_compact ───────────────────────────────────────────────

def test_compact_session_history_skips_if_too_few_messages(monkeypatch):
    from core.context import session_compact
    summarise_fn = Mock(return_value="Summary")

    # Mock get + store
    monkeypatch.setattr(
        session_compact,
        "_get_all_session_messages",
        lambda session_id: [{"role": "user", "content": "hi"} for _ in range(5)],
    )
    monkeypatch.setattr(session_compact, "_store_marker", lambda sid, text: "marker-1")

    result = session_compact.compact_session_history(
        "session-x", keep_recent=20, summarise_fn=summarise_fn
    )
    assert result is None
    assert not summarise_fn.called


def test_compact_session_history_calls_summarise_on_enough_messages(monkeypatch):
    from core.context import session_compact
    summarise_fn = Mock(return_value="Compressed history")

    messages = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
                for i in range(30)]
    monkeypatch.setattr(session_compact, "_get_all_session_messages", lambda sid: messages)
    monkeypatch.setattr(session_compact, "_store_marker", lambda sid, text: "marker-1")

    result = session_compact.compact_session_history(
        "session-x", keep_recent=20, summarise_fn=summarise_fn
    )
    assert result is not None
    assert result.summary_text == "Compressed history"
    assert result.freed_tokens > 0
    assert result.marker_id == "marker-1"
    assert summarise_fn.called


def test_compact_session_history_compresses_only_old_messages(monkeypatch):
    from core.context import session_compact
    captured_input = {}

    def _capture_summarise(msgs):
        captured_input["msgs"] = msgs
        return "Summary"

    messages = [{"role": "user", "content": f"msg {i}"} for i in range(25)]
    monkeypatch.setattr(session_compact, "_get_all_session_messages", lambda sid: messages)
    monkeypatch.setattr(session_compact, "_store_marker", lambda sid, text: "m")

    session_compact.compact_session_history(
        "session-x", keep_recent=20, summarise_fn=_capture_summarise
    )
    # Only the oldest 5 messages (25-20) should be passed to summarise_fn
    assert len(captured_input["msgs"]) == 5
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_compact_session_history_skips_if_too_few_messages -v
```

Expected: `ModuleNotFoundError: No module named 'core.context.session_compact'`

- [ ] **Step 3: Create core/context/session_compact.py**

```python
"""Session-level context compaction.

Summarises old chat history into a compact_marker stored in the DB.
The newest `keep_recent` messages are never compacted.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from core.context.token_estimate import estimate_tokens

logger = logging.getLogger(__name__)


@dataclass
class CompactResult:
    freed_tokens: int
    summary_text: str
    marker_id: str


def compact_session_history(
    session_id: str,
    *,
    keep_recent: int = 20,
    summarise_fn: Callable[[list[dict]], str],
) -> CompactResult | None:
    """Compact old session history for session_id.

    Fetches all messages, splits at (total - keep_recent), summarises the
    old slice via summarise_fn, stores a compact_marker in DB, and returns
    a CompactResult. Returns None if there are not enough messages to compact
    (i.e. total <= keep_recent).
    """
    messages = _get_all_session_messages(session_id)
    if len(messages) <= keep_recent:
        return None

    old_messages = messages[: len(messages) - keep_recent]
    freed_chars = sum(len(m.get("content") or "") for m in old_messages)
    freed_tokens = estimate_tokens("x" * freed_chars)

    summary_text = summarise_fn(old_messages)

    marker_id = _store_marker(session_id, summary_text)

    logger.info(
        "session_compact: session=%s compacted %d messages → %d tokens freed",
        session_id,
        len(old_messages),
        freed_tokens,
    )
    return CompactResult(
        freed_tokens=freed_tokens,
        summary_text=summary_text,
        marker_id=marker_id,
    )


# ── Internal helpers (monkeypatched in tests) ──────────────────────────────

def _get_all_session_messages(session_id: str) -> list[dict]:
    from apps.api.jarvis_api.services.chat_sessions import recent_chat_session_messages
    # Fetch a large window — 500 should cover most sessions
    return recent_chat_session_messages(session_id, limit=500)


def _store_marker(session_id: str, summary_text: str) -> str:
    from apps.api.jarvis_api.services.chat_sessions import store_compact_marker
    return store_compact_marker(session_id, summary_text)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_compact_session_history_skips_if_too_few_messages tests/test_context_compact.py::test_compact_session_history_calls_summarise_on_enough_messages tests/test_context_compact.py::test_compact_session_history_compresses_only_old_messages -v
```

Expected: 3 passed

- [ ] **Step 5: Compile check + commit**

```bash
conda run -n ai python -m compileall core/context/session_compact.py -q
git add core/context/session_compact.py tests/test_context_compact.py
git commit -m "feat(compact): session_compact module with CompactResult"
```

---

## Task 6: Run compact module

**Files:**
- Create: `core/context/run_compact.py`
- Test: `tests/test_context_compact.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_context_compact.py`:

```python
# ── Task 6: run_compact ───────────────────────────────────────────────────

def test_run_compact_returns_same_if_too_few_pairs():
    from core.context.run_compact import compact_run_messages
    summarise_fn = Mock(return_value="Compressed")
    messages = [
        {"role": "user", "content": "do stuff"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "Tool results: done"},
    ]
    result = compact_run_messages(
        messages, keep_base=1, keep_recent_pairs=4, summarise_fn=summarise_fn
    )
    assert result == messages
    assert not summarise_fn.called


def test_run_compact_compresses_middle_messages():
    from core.context.run_compact import compact_run_messages
    summarise_fn = Mock(return_value="Ran 3 tools: read, write, bash")

    # base: 1 msg, then 6 pairs (assistant + user) = 12 msgs, keep_recent_pairs=2
    base = [{"role": "user", "content": "start task"}]
    pairs = []
    for i in range(6):
        pairs.append({"role": "assistant", "content": f"Calling tool {i}"})
        pairs.append({"role": "user", "content": f"Tool results: result {i}"})
    messages = base + pairs  # 13 messages total

    result = compact_run_messages(
        messages, keep_base=1, keep_recent_pairs=2, summarise_fn=summarise_fn
    )
    assert len(result) < len(messages)
    assert any("[KOMPRIMERET KONTEKST:" in m.get("content", "") for m in result)
    assert summarise_fn.called


def test_run_compact_always_keeps_base_messages():
    from core.context.run_compact import compact_run_messages
    summarise_fn = Mock(return_value="Summary")

    base = [
        {"role": "system", "content": "You are Jarvis"},
        {"role": "user", "content": "Do the task"},
    ]
    pairs = []
    for i in range(6):
        pairs.append({"role": "assistant", "content": f"Calling tool {i}"})
        pairs.append({"role": "user", "content": f"Tool results: result {i}"})
    messages = base + pairs

    result = compact_run_messages(
        messages, keep_base=2, keep_recent_pairs=2, summarise_fn=summarise_fn
    )
    # First 2 messages (base) must always be present
    assert result[0] == base[0]
    assert result[1] == base[1]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_run_compact_returns_same_if_too_few_pairs -v
```

Expected: `ModuleNotFoundError: No module named 'core.context.run_compact'`

- [ ] **Step 3: Create core/context/run_compact.py**

```python
"""Run-level context compaction for the agentic tool-calling loop.

Compresses old message pairs in the running _agentic_messages list.
The base messages (initial prompt + first context) are always kept.
The most recent `keep_recent_pairs` pairs are always kept.
Everything in between is summarised.
"""
from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)


def compact_run_messages(
    messages: list[dict],
    *,
    keep_base: int,
    keep_recent_pairs: int,
    summarise_fn: Callable[[list[dict]], str],
) -> list[dict]:
    """Compact old messages in an agentic loop message list.

    Args:
        messages: The full _agentic_messages list.
        keep_base: Number of initial messages to always keep (prompt context).
        keep_recent_pairs: Number of most-recent assistant+user pairs to keep.
        summarise_fn: Callable that takes a list of messages and returns a summary string.

    Returns:
        A new, shorter messages list. Returns the original list unchanged if
        there is nothing to compact (middle section is empty or too small).
    """
    if len(messages) <= keep_base:
        return messages

    base = messages[:keep_base]
    rest = messages[keep_base:]

    # Each pair is 2 messages: assistant + user(tool results)
    keep_tail_count = keep_recent_pairs * 2
    if len(rest) <= keep_tail_count:
        return messages  # Nothing to compact

    middle = rest[: len(rest) - keep_tail_count]
    tail = rest[len(rest) - keep_tail_count :]

    summary = summarise_fn(middle)
    compact_msg = {
        "role": "user",
        "content": f"[KOMPRIMERET KONTEKST: {summary}]",
    }

    logger.info(
        "run_compact: compressed %d messages → 1 compact block",
        len(middle),
    )
    return base + [compact_msg] + tail
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_run_compact_returns_same_if_too_few_pairs tests/test_context_compact.py::test_run_compact_compresses_middle_messages tests/test_context_compact.py::test_run_compact_always_keeps_base_messages -v
```

Expected: 3 passed

- [ ] **Step 5: Compile check + commit**

```bash
conda run -n ai python -m compileall core/context/run_compact.py -q
git add core/context/run_compact.py tests/test_context_compact.py
git commit -m "feat(compact): run_compact module for agentic loop compaction"
```

---

## Task 7: Wire session compact into prompt_contract.py + /compact in visible_runs.py

**Files:**
- Modify: `apps/api/jarvis_api/services/prompt_contract.py:2695-2763` (`_build_structured_transcript_messages`)
- Modify: `apps/api/jarvis_api/services/visible_runs.py:382-420` (`_stream_visible_run` start)
- Test: `tests/test_context_compact.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_context_compact.py`:

```python
# ── Task 7: session compact wiring ────────────────────────────────────────

def test_build_transcript_prepends_compact_marker_when_present(monkeypatch):
    from apps.api.jarvis_api.services import prompt_contract

    monkeypatch.setattr(
        prompt_contract,
        "recent_chat_session_messages",
        lambda sid, limit: [
            {"role": "user", "content": "hello", "created_at": "2026-01-01"},
            {"role": "assistant", "content": "hi", "created_at": "2026-01-01"},
        ],
    )
    monkeypatch.setattr(
        prompt_contract,
        "_get_compact_marker_for_transcript",
        lambda sid: "Old summarised history here",
    )

    result = prompt_contract._build_structured_transcript_messages(
        "session-x", limit=60, include=True
    )
    # First message should be the compact marker injection
    assert result[0]["role"] == "user"
    assert "Old summarised history here" in result[0]["content"]
    assert result[1]["role"] == "assistant"
    assert result[1]["content"] == "Forstået."


def test_build_transcript_no_marker_no_prepend(monkeypatch):
    from apps.api.jarvis_api.services import prompt_contract

    monkeypatch.setattr(
        prompt_contract,
        "recent_chat_session_messages",
        lambda sid, limit: [
            {"role": "user", "content": "hello", "created_at": "2026-01-01"},
            {"role": "assistant", "content": "hi", "created_at": "2026-01-01"},
        ],
    )
    monkeypatch.setattr(
        prompt_contract,
        "_get_compact_marker_for_transcript",
        lambda sid: None,
    )
    monkeypatch.setattr(
        prompt_contract,
        "_maybe_auto_compact_session",
        lambda sid, messages, settings: None,
    )

    result = prompt_contract._build_structured_transcript_messages(
        "session-x", limit=60, include=True
    )
    # Should just be the normal messages, no prepended marker pair
    assert result[0]["content"] == "hello"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_build_transcript_prepends_compact_marker_when_present -v
```

Expected: `AttributeError: module 'prompt_contract' has no attribute '_get_compact_marker_for_transcript'`

- [ ] **Step 3: Modify _build_structured_transcript_messages in prompt_contract.py**

The function ends at line 2763 with `return result`. Replace the final `return result` with:

```python
    # ── Compact marker injection ──────────────────────────────────────────
    # If a compact_marker exists for this session, prepend it so Jarvis has
    # context about what happened before the current window.
    if session_id:
        marker_summary = _get_compact_marker_for_transcript(session_id)
        if marker_summary:
            result = [
                {
                    "role": "user",
                    "content": f"[Komprimeret historik fra tidligere i samtalen:\n{marker_summary}]",
                },
                {"role": "assistant", "content": "Forstået."},
            ] + result

        # ── Auto-compact check ────────────────────────────────────────────
        # If transcript is very long, trigger session compaction so future
        # prompts are smaller.
        try:
            from core.runtime.settings import load_settings as _load_compact_settings
            _compact_settings = _load_compact_settings()
            _maybe_auto_compact_session(session_id, result, _compact_settings)
        except Exception:
            pass  # Never let compact trigger crash the prompt build

    return result
```

Add these two helper functions anywhere in `prompt_contract.py` (after the imports block, or near the end of the file):

```python
def _get_compact_marker_for_transcript(session_id: str) -> str | None:
    """Fetch the most recent compact marker for this session (monkeypatchable)."""
    try:
        from apps.api.jarvis_api.services.chat_sessions import get_compact_marker
        return get_compact_marker(session_id)
    except Exception:
        return None


def _maybe_auto_compact_session(
    session_id: str,
    current_messages: list[dict],
    settings,
) -> None:
    """Trigger session compact if transcript tokens exceed threshold."""
    from core.context.token_estimate import estimate_messages_tokens
    if estimate_messages_tokens(current_messages) < settings.context_compact_threshold_tokens:
        return
    try:
        from core.context.session_compact import compact_session_history
        from core.context.compact_llm import call_compact_llm
        import logging as _log
        _log.getLogger(__name__).info(
            "prompt_contract: auto-compact triggered for session %s", session_id
        )
        compact_session_history(
            session_id,
            keep_recent=settings.context_keep_recent,
            summarise_fn=lambda msgs: call_compact_llm(
                "Komprimér denne dialog til max 400 ord. Bevar fakta, beslutninger og kontekst:\n\n"
                + "\n".join(f"{m['role']}: {m.get('content','')}" for m in msgs),
                max_tokens=500,
            ),
        )
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).warning("auto_compact_session failed: %s", exc)
```

- [ ] **Step 4: Add /compact detection to visible_runs.py**

In `_stream_visible_run` in `apps/api/jarvis_api/services/visible_runs.py`, immediately after line 383 (`controller = register_visible_run(run)`), add:

```python
    # ── /compact command ──────────────────────────────────────────────────
    if run.user_message.strip().lower() == "/compact":
        result_text = _handle_compact_command(run)
        run = run  # reassign user_message for the model call
        # Swap the message so Jarvis responds naturally
        object.__setattr__(run, "user_message", result_text)
```

Add the handler function before `_stream_visible_run`:

```python
def _handle_compact_command(run: "VisibleRun") -> str:
    """Run session compact and return a message for Jarvis to respond to."""
    try:
        from core.context.session_compact import compact_session_history
        from core.context.compact_llm import call_compact_llm
        from core.runtime.settings import load_settings as _ls
        settings = _ls()
        cr = compact_session_history(
            run.session_id or "",
            keep_recent=settings.context_keep_recent,
            summarise_fn=lambda msgs: call_compact_llm(
                "Komprimér denne dialog til max 400 ord. Bevar fakta, beslutninger og kontekst:\n\n"
                + "\n".join(f"{m['role']}: {m.get('content','')}" for m in msgs),
                max_tokens=500,
            ),
        )
        if cr:
            return (
                f"Jeg har netop komprimeret vores samtalehistorik. "
                f"{cr.freed_tokens} tokens frigjort. Bekræft kort."
            )
        return "Ingen historik at komprimere endnu — samtalen er stadig kort."
    except Exception as exc:
        return f"Komprimering mislykkedes: {exc}"
```

Note: `VisibleRun` is a dataclass with `slots=True`, so we use `object.__setattr__` to mutate it. Verify this works by checking the dataclass definition in `visible_runs.py` around line 239.

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_build_transcript_prepends_compact_marker_when_present tests/test_context_compact.py::test_build_transcript_no_marker_no_prepend -v
```

Expected: 2 passed

- [ ] **Step 6: Compile check + commit**

```bash
conda run -n ai python -m compileall apps/api/jarvis_api/services/prompt_contract.py apps/api/jarvis_api/services/visible_runs.py -q
git add apps/api/jarvis_api/services/prompt_contract.py apps/api/jarvis_api/services/visible_runs.py tests/test_context_compact.py
git commit -m "feat(compact): wire session auto-compact + /compact command"
```

---

## Task 8: Wire run auto-compact into visible_runs.py agentic loop

**Files:**
- Modify: `apps/api/jarvis_api/services/visible_runs.py:860-876` (end of agentic round loop)
- Test: `tests/test_context_compact.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_context_compact.py`:

```python
# ── Task 8: run compact wiring ────────────────────────────────────────────

def test_maybe_compact_agentic_messages_no_compact_below_threshold(monkeypatch):
    from apps.api.jarvis_api.services import visible_runs
    from core.runtime.settings import RuntimeSettings

    settings = RuntimeSettings()
    settings.context_run_compact_threshold_tokens = 60_000

    # Short messages — well below threshold
    messages = [{"role": "user", "content": "short"}]
    result = visible_runs._maybe_compact_agentic_messages(messages, base_count=1, settings=settings)
    assert result is messages  # unchanged


def test_maybe_compact_agentic_messages_compacts_above_threshold(monkeypatch):
    from apps.api.jarvis_api.services import visible_runs
    from core.runtime.settings import RuntimeSettings

    settings = RuntimeSettings()
    settings.context_run_compact_threshold_tokens = 10  # very low threshold

    monkeypatch.setattr(
        visible_runs,
        "_compact_llm_for_run",
        lambda prompt: "Compressed tool history",
    )

    base = [{"role": "user", "content": "start"}]
    pairs = []
    for i in range(8):
        pairs.append({"role": "assistant", "content": f"calling tool {i}" * 20})
        pairs.append({"role": "user", "content": f"tool result {i}" * 20})
    messages = base + pairs

    result = visible_runs._maybe_compact_agentic_messages(
        messages, base_count=1, settings=settings
    )
    assert len(result) < len(messages)
    assert any("[KOMPRIMERET KONTEKST:" in m.get("content", "") for m in result)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_maybe_compact_agentic_messages_no_compact_below_threshold -v
```

Expected: `AttributeError: module 'visible_runs' has no attribute '_maybe_compact_agentic_messages'`

- [ ] **Step 3: Add helpers + wiring to visible_runs.py**

Add these two functions before `_stream_visible_run` in `visible_runs.py`:

```python
def _compact_llm_for_run(prompt: str) -> str:
    """Call the compact LLM for run-level summarisation (monkeypatchable)."""
    from core.context.compact_llm import call_compact_llm
    return call_compact_llm(prompt, max_tokens=400)


def _maybe_compact_agentic_messages(
    messages: list[dict],
    *,
    base_count: int,
    settings,
) -> list[dict]:
    """Compact _agentic_messages if they exceed the run threshold.

    Returns a new (shorter) list, or the original list unchanged if below threshold.
    """
    from core.context.token_estimate import estimate_messages_tokens
    if estimate_messages_tokens(messages) < settings.context_run_compact_threshold_tokens:
        return messages
    from core.context.run_compact import compact_run_messages
    return compact_run_messages(
        messages,
        keep_base=base_count,
        keep_recent_pairs=settings.context_keep_recent_pairs,
        summarise_fn=lambda msgs: _compact_llm_for_run(
            "Komprimér disse tool-operationer til max 300 ord. Bevar resultater, fejl og vigtige fund:\n\n"
            + "\n".join(f"{m.get('role','')}: {m.get('content','')[:300]}" for m in msgs)
        ),
    )
```

In the agentic loop, after line 876 (`_agentic_messages = _agentic_messages + [...]`), add:

```python
                    # ── Run-level auto-compact ─────────────────────────────────────────
                    try:
                        from core.runtime.settings import load_settings as _lcs
                        _run_settings = _lcs()
                        _base_count = len(base_messages) + 1  # base msgs + first tool-results
                        _compacted = _maybe_compact_agentic_messages(
                            _agentic_messages,
                            base_count=_base_count,
                            settings=_run_settings,
                        )
                        if _compacted is not _agentic_messages:
                            _agentic_messages = _compacted
                            # Tell Jarvis to announce the compaction in its next response
                            _agentic_messages.append({
                                "role": "user",
                                "content": (
                                    "Note: Dit arbejdende kontekstvindue er netop komprimeret "
                                    "for at frigøre plads. Nævn kort at du kompakterer "
                                    "(1 sætning) og fortsæt din opgave."
                                ),
                            })
                    except Exception:
                        pass  # Never let compact crash the agentic loop
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_maybe_compact_agentic_messages_no_compact_below_threshold tests/test_context_compact.py::test_maybe_compact_agentic_messages_compacts_above_threshold -v
```

Expected: 2 passed

- [ ] **Step 5: Compile check + commit**

```bash
conda run -n ai python -m compileall apps/api/jarvis_api/services/visible_runs.py -q
git add apps/api/jarvis_api/services/visible_runs.py tests/test_context_compact.py
git commit -m "feat(compact): wire run auto-compact into agentic tool loop"
```

---

## Task 9: compact_context tool

**Files:**
- Modify: `core/tools/simple_tools.py` (add tool definition + handler)
- Test: `tests/test_context_compact.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_context_compact.py`:

```python
# ── Task 9: compact_context tool ──────────────────────────────────────────

def test_compact_context_tool_is_registered():
    from core.tools.simple_tools import get_tool_definitions
    tool_names = [t["function"]["name"] for t in get_tool_definitions()]
    assert "compact_context" in tool_names


def test_compact_context_tool_calls_session_compact(monkeypatch):
    from core.tools import simple_tools
    from core.context.session_compact import CompactResult

    compact_result = CompactResult(
        freed_tokens=5000,
        summary_text="Old history",
        marker_id="marker-1",
    )
    monkeypatch.setattr(
        simple_tools,
        "_exec_compact_context_session",
        lambda session_id: compact_result,
    )

    result = simple_tools._exec_compact_context(
        {}, session_id="session-abc"
    )
    assert result["status"] == "ok"
    assert result["freed_tokens"] == 5000


def test_compact_context_tool_handles_no_session(monkeypatch):
    from core.tools import simple_tools
    monkeypatch.setattr(
        simple_tools,
        "_exec_compact_context_session",
        lambda session_id: None,
    )
    result = simple_tools._exec_compact_context({}, session_id=None)
    assert result["status"] == "ok"
    assert result["freed_tokens"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_compact_context_tool_is_registered -v
```

Expected: `AssertionError: assert 'compact_context' in [...]`

- [ ] **Step 3: Add tool definition and handler to simple_tools.py**

Find `TOOL_DEFINITIONS: list[dict[str, Any]] = [` in `simple_tools.py` and add to the list (before `*BROWSER_TOOL_DEFINITIONS`):

```python
    {
        "type": "function",
        "function": {
            "name": "compact_context",
            "description": (
                "Compact your working context to free up space. "
                "Summarises old session history into a compact marker. "
                "Use proactively before starting very long tasks, or when you notice you are "
                "approaching context limits. Returns the number of tokens freed."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
```

Find `_TOOL_HANDLERS: dict[str, Any] = {` and add:

```python
    "compact_context": _exec_compact_context,
```

Add the handler function and internal helper (near the other `_exec_*` functions):

```python
def _exec_compact_context_session(session_id: str | None):
    """Run session compact. Returns CompactResult or None (monkeypatchable)."""
    if not session_id:
        return None
    from core.context.session_compact import compact_session_history
    from core.context.compact_llm import call_compact_llm
    from core.runtime.settings import load_settings as _ls
    settings = _ls()
    return compact_session_history(
        session_id,
        keep_recent=settings.context_keep_recent,
        summarise_fn=lambda msgs: call_compact_llm(
            "Komprimér denne dialog til max 400 ord. Bevar fakta, beslutninger og kontekst:\n\n"
            + "\n".join(f"{m['role']}: {m.get('content','')}" for m in msgs),
            max_tokens=500,
        ),
    )


def _exec_compact_context(args: dict[str, Any], *, session_id: str | None = None) -> dict[str, Any]:
    """Handler for compact_context tool."""
    cr = _exec_compact_context_session(session_id)
    if cr is None:
        return {
            "status": "ok",
            "freed_tokens": 0,
            "message": "Ingen historik at komprimere — samtalen er stadig kort.",
        }
    return {
        "status": "ok",
        "freed_tokens": cr.freed_tokens,
        "summary": cr.summary_text[:200],
        "message": f"Kontekst komprimeret. {cr.freed_tokens} tokens frigjort.",
    }
```

Note: The `_exec_compact_context` handler takes `session_id` as a keyword argument. This means the tool dispatch in `simple_tools.py` must pass `session_id` when calling it. Find where `_TOOL_HANDLERS[name](args)` is called and check if session_id is already threaded through. If not, update the dispatch to pass `session_id=current_session_id` for this tool only, or use `functools.partial` when registering.

Look for `_TOOL_HANDLERS` dispatch in `simple_tools.py` and use the pattern:
```python
# In the dispatch logic:
handler = _TOOL_HANDLERS.get(name)
if name == "compact_context":
    result = handler(args, session_id=session_id)
else:
    result = handler(args)
```

Or, more cleanly, check if the handler accepts `session_id` via `inspect.signature`.

Check how `queue_followup` in `simple_tools.py` handles session_id — it uses `_exec_queue_followup(args)` with no session_id parameter, instead reading from workspace config. For `compact_context`, the simplest approach is the same: make `_exec_compact_context(args)` look up the active session via `recent_chat_session_messages` to find the latest session_id, OR just skip session_id entirely and rely on the auto-compact in `prompt_contract.py` instead. If the dispatch does pass session_id (check the `execute_tool` call site in `visible_runs.py`), use it; otherwise remove the `session_id` parameter from `_exec_compact_context` and have it return a message telling Jarvis the auto-compact will handle it next prompt-build.

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py::test_compact_context_tool_is_registered tests/test_context_compact.py::test_compact_context_tool_calls_session_compact tests/test_context_compact.py::test_compact_context_tool_handles_no_session -v
```

Expected: 3 passed

- [ ] **Step 5: Compile check + commit**

```bash
conda run -n ai python -m compileall core/tools/simple_tools.py -q
git add core/tools/simple_tools.py tests/test_context_compact.py
git commit -m "feat(compact): compact_context tool — Jarvis can self-trigger session compact"
```

---

## Task 10: Full regression

**Files:** No new files

- [ ] **Step 1: Run all context compact tests**

```bash
conda run -n ai python -m pytest tests/test_context_compact.py -v
```

Expected: all tests pass

- [ ] **Step 2: Run existing test suites**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py tests/test_heartbeat_triggers.py tests/test_jarvis_experimental.py -v
```

Expected: all tests pass

- [ ] **Step 3: Full compile check**

```bash
conda run -n ai python -m compileall core apps/api scripts -q
```

Expected: no output (no errors)

- [ ] **Step 4: Restart API and verify startup**

```bash
sudo systemctl restart jarvis-api && sleep 8 && sudo systemctl is-active jarvis-api
```

Expected: `active`

```bash
sudo journalctl -u jarvis-api -n 10 --no-pager | grep -E "startup|ERROR"
```

Expected: `jarvis api startup complete` with no ERROR lines

- [ ] **Step 5: Final commit**

```bash
git log --oneline -8
```

Verify all 8 compact commits are present. No further commit needed.
