# Inner LLM Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace deterministic template strings in 3 private memory pipeline files with async LLM-generated inner thoughts, using a unified enrichment service that fires after pipeline persistence.

**Architecture:** A new `core/memory/inner_llm_enrichment.py` service receives template payloads + chat context, spawns a daemon thread that sequentially calls the cheapest LLM model via `resolve_provider_router_target(lane="cheap")`, and updates DB records in-place. Existing pipeline flow and templates are preserved as fallback.

**Tech Stack:** Python 3.11+, urllib (HTTP), threading (daemon), SQLite (existing db.py pattern)

**Spec:** `docs/superpowers/specs/2026-04-05-inner-llm-enrichment-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `core/memory/inner_llm_enrichment.py` | Create | Async LLM enrichment service — prompts, HTTP calls, DB updates |
| `core/runtime/db.py` | Modify | Add `enriched` column to 3 tables + 3 update functions |
| `core/memory/private_layer_pipeline.py` | Modify | Call enrichment after persistence (1 line + 1 helper) |
| `tests/test_inner_llm_enrichment.py` | Create | Tests for enrichment service |

---

### Task 1: Add `enriched` Column to DB Schema

**Files:**
- Modify: `core/runtime/db.py` (schema definitions around lines 544-659, and column-ensure helpers around line 1941)

- [ ] **Step 1: Write the failing test**

Create `tests/test_inner_llm_enrichment.py`:

```python
"""Tests for inner LLM enrichment service."""

import sqlite3

from core.runtime import db as jarvis_db


def _get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def test_private_inner_notes_has_enriched_column() -> None:
    jarvis_db.init_db()
    conn = jarvis_db.connect()
    cols = _get_columns(conn, "private_inner_notes")
    conn.close()
    assert "enriched" in cols


def test_private_growth_notes_has_enriched_column() -> None:
    jarvis_db.init_db()
    conn = jarvis_db.connect()
    cols = _get_columns(conn, "private_growth_notes")
    conn.close()
    assert "enriched" in cols


def test_protected_inner_voices_has_enriched_column() -> None:
    jarvis_db.init_db()
    conn = jarvis_db.connect()
    cols = _get_columns(conn, "protected_inner_voices")
    conn.close()
    assert "enriched" in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_inner_llm_enrichment.py::test_private_inner_notes_has_enriched_column -v`
Expected: FAIL — `enriched` column does not exist yet.

- [ ] **Step 3: Add `enriched` column to the 3 table schemas**

In `core/runtime/db.py`, find the `CREATE TABLE IF NOT EXISTS private_inner_notes` block (around line 544). Add `enriched INTEGER NOT NULL DEFAULT 0` before the closing paren:

```sql
CREATE TABLE IF NOT EXISTS private_inner_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    run_id TEXT NOT NULL UNIQUE,
    work_id TEXT NOT NULL,
    status TEXT NOT NULL,
    note_kind TEXT NOT NULL DEFAULT '',
    focus TEXT NOT NULL DEFAULT '',
    uncertainty TEXT NOT NULL DEFAULT '',
    identity_alignment TEXT NOT NULL DEFAULT '',
    work_signal TEXT NOT NULL DEFAULT '',
    private_summary TEXT NOT NULL,
    created_at TEXT NOT NULL,
    enriched INTEGER NOT NULL DEFAULT 0
)
```

Do the same for `private_growth_notes` (around line 563):

```sql
CREATE TABLE IF NOT EXISTS private_growth_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    run_id TEXT NOT NULL UNIQUE,
    work_id TEXT NOT NULL,
    learning_kind TEXT NOT NULL,
    lesson TEXT NOT NULL,
    mistake_signal TEXT NOT NULL DEFAULT '',
    helpful_signal TEXT NOT NULL DEFAULT '',
    identity_signal TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    enriched INTEGER NOT NULL DEFAULT 0
)
```

And `protected_inner_voices` (around line 646):

```sql
CREATE TABLE IF NOT EXISTS protected_inner_voices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voice_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    run_id TEXT NOT NULL UNIQUE,
    work_id TEXT NOT NULL,
    mood_tone TEXT NOT NULL,
    self_position TEXT NOT NULL,
    current_concern TEXT NOT NULL,
    current_pull TEXT NOT NULL,
    voice_line TEXT NOT NULL,
    created_at TEXT NOT NULL,
    enriched INTEGER NOT NULL DEFAULT 0
)
```

Also add an `_ensure_enriched_columns()` function near the other `_ensure_*_columns()` helpers (around line 1941). This handles existing databases that already have these tables without the new column:

```python
def _ensure_enriched_columns() -> None:
    """Add enriched column to private layer tables if missing."""
    conn = connect()
    try:
        for table in ("private_inner_notes", "private_growth_notes", "protected_inner_voices"):
            cursor = conn.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cursor.fetchall()]
            if "enriched" not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN enriched INTEGER NOT NULL DEFAULT 0")
                conn.commit()
    finally:
        conn.close()
```

Call `_ensure_enriched_columns()` from `init_db()` alongside other `_ensure_*` calls.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_inner_llm_enrichment.py -v -k "enriched_column"`
Expected: All 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add core/runtime/db.py tests/test_inner_llm_enrichment.py
git commit -m "feat: add enriched column to private layer DB tables"
```

---

### Task 2: Add DB Update Functions for Enrichment

**Files:**
- Modify: `core/runtime/db.py` (near the existing `record_private_inner_note` function around line 961)
- Modify: `tests/test_inner_llm_enrichment.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_inner_llm_enrichment.py`:

```python
from datetime import datetime, timezone


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _insert_inner_note(run_id: str = "run-001") -> None:
    jarvis_db.record_private_inner_note(
        note_id=f"private-inner-note:{run_id}",
        source="visible-selected-work-note",
        run_id=run_id,
        work_id="work-001",
        status="completed",
        note_kind="bounded-reflection",
        focus="workspace-search",
        uncertainty="low",
        identity_alignment="aligned",
        work_signal="task-completed",
        private_summary="template summary",
        created_at=_iso_now(),
    )


def _insert_growth_note(run_id: str = "run-001") -> None:
    jarvis_db.record_private_growth_note(
        record_id=f"private-growth-note:{run_id}",
        source="private-inner-note:private-runtime-grounded",
        run_id=run_id,
        work_id="work-001",
        learning_kind="reinforce",
        lesson="template lesson",
        mistake_signal="",
        helpful_signal="template helpful signal",
        identity_signal="steady",
        confidence="medium",
        created_at=_iso_now(),
    )


def _insert_inner_voice(run_id: str = "run-001") -> None:
    jarvis_db.record_protected_inner_voice(
        voice_id=f"protected-inner-voice:{run_id}",
        source="private-state+private-self-model",
        run_id=run_id,
        work_id="work-001",
        mood_tone="steady",
        self_position="observing",
        current_concern="stability:medium",
        current_pull="retain-current-pattern",
        voice_line="steady | position=observing | concern=stability | pull=retain",
        created_at=_iso_now(),
    )


def test_update_private_inner_note_enriched() -> None:
    jarvis_db.init_db()
    _insert_inner_note("run-enrich-1")

    jarvis_db.update_private_inner_note_enriched(
        run_id="run-enrich-1",
        enriched_summary="LLM-generated reflective summary",
    )

    conn = jarvis_db.connect()
    row = conn.execute(
        "SELECT private_summary, enriched FROM private_inner_notes WHERE run_id = ?",
        ("run-enrich-1",),
    ).fetchone()
    conn.close()
    assert row[0] == "LLM-generated reflective summary"
    assert row[1] == 1


def test_update_private_growth_note_enriched() -> None:
    jarvis_db.init_db()
    _insert_growth_note("run-enrich-2")

    jarvis_db.update_private_growth_note_enriched(
        run_id="run-enrich-2",
        enriched_lesson="LLM lesson",
        enriched_helpful_signal="LLM helpful signal",
    )

    conn = jarvis_db.connect()
    row = conn.execute(
        "SELECT lesson, helpful_signal, enriched FROM private_growth_notes WHERE run_id = ?",
        ("run-enrich-2",),
    ).fetchone()
    conn.close()
    assert row[0] == "LLM lesson"
    assert row[1] == "LLM helpful signal"
    assert row[2] == 1


def test_update_protected_inner_voice_enriched() -> None:
    jarvis_db.init_db()
    _insert_inner_voice("run-enrich-3")

    jarvis_db.update_protected_inner_voice_enriched(
        run_id="run-enrich-3",
        enriched_voice_line="LLM voice line",
    )

    conn = jarvis_db.connect()
    row = conn.execute(
        "SELECT voice_line, enriched FROM protected_inner_voices WHERE run_id = ?",
        ("run-enrich-3",),
    ).fetchone()
    conn.close()
    assert row[0] == "LLM voice line"
    assert row[1] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_inner_llm_enrichment.py -v -k "update_"`
Expected: FAIL — `update_*_enriched` functions do not exist.

- [ ] **Step 3: Add the 3 update functions to db.py**

Add near the existing `record_private_inner_note` function (around line 975):

```python
def update_private_inner_note_enriched(*, run_id: str, enriched_summary: str) -> None:
    """Replace template summary with LLM-enriched text."""
    conn = connect()
    try:
        conn.execute(
            "UPDATE private_inner_notes SET private_summary = ?, enriched = 1 WHERE run_id = ?",
            (enriched_summary, run_id),
        )
        conn.commit()
    finally:
        conn.close()
```

Add near `record_private_growth_note` (around line 1070):

```python
def update_private_growth_note_enriched(
    *, run_id: str, enriched_lesson: str, enriched_helpful_signal: str
) -> None:
    """Replace template lesson and helpful_signal with LLM-enriched text."""
    conn = connect()
    try:
        conn.execute(
            "UPDATE private_growth_notes SET lesson = ?, helpful_signal = ?, enriched = 1 WHERE run_id = ?",
            (enriched_lesson, enriched_helpful_signal, run_id),
        )
        conn.commit()
    finally:
        conn.close()
```

Add near `record_protected_inner_voice` (around line 1521):

```python
def update_protected_inner_voice_enriched(*, run_id: str, enriched_voice_line: str) -> None:
    """Replace template voice_line with LLM-enriched text."""
    conn = connect()
    try:
        conn.execute(
            "UPDATE protected_inner_voices SET voice_line = ?, enriched = 1 WHERE run_id = ?",
            (enriched_voice_line, run_id),
        )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_inner_llm_enrichment.py -v -k "update_"`
Expected: All 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add core/runtime/db.py tests/test_inner_llm_enrichment.py
git commit -m "feat: add update functions for LLM-enriched private layer fields"
```

---

### Task 3: Build the Inner LLM Enrichment Service — Prompt Construction

**Files:**
- Create: `core/memory/inner_llm_enrichment.py`
- Modify: `tests/test_inner_llm_enrichment.py`

- [ ] **Step 1: Write failing tests for prompt building**

Append to `tests/test_inner_llm_enrichment.py`:

```python
from core.memory.inner_llm_enrichment import (
    _build_inner_note_prompt,
    _build_growth_note_prompt,
    _build_inner_voice_prompt,
)


def test_build_inner_note_prompt_includes_payload_and_context() -> None:
    payload = {
        "private_summary": "template text",
        "focus": "workspace-search",
        "uncertainty": "low",
        "work_signal": "task-completed",
        "status": "completed",
    }
    chat_ctx = "User: find my notes\nAssistant: Found 3 notes."
    system, user = _build_inner_note_prompt(payload, chat_ctx)
    assert "indre stemme" in system.lower() or "inner" in system.lower()
    assert "workspace-search" in user
    assert "task-completed" in user
    assert "find my notes" in user


def test_build_growth_note_prompt_includes_lesson_and_context() -> None:
    payload = {
        "lesson": "template lesson",
        "helpful_signal": "template helpful",
        "mistake_signal": "",
        "learning_kind": "reinforce",
        "confidence": "medium",
    }
    chat_ctx = "User: search files"
    system, user = _build_growth_note_prompt(payload, chat_ctx)
    assert "lærte" in system.lower() or "lært" in system.lower() or "learn" in system.lower()
    assert "reinforce" in user
    assert "search files" in user


def test_build_inner_voice_prompt_includes_mood_and_context() -> None:
    payload = {
        "mood_tone": "steady",
        "self_position": "observing",
        "current_concern": "stability:medium",
        "current_pull": "retain-current-pattern",
    }
    chat_ctx = "User: how are you?"
    system, user = _build_inner_voice_prompt(payload, chat_ctx)
    assert "voice" in system.lower() or "stemme" in system.lower()
    assert "steady" in user
    assert "observing" in user
    assert "how are you?" in user
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_inner_llm_enrichment.py -v -k "build_"`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create `core/memory/inner_llm_enrichment.py` with prompt builders**

```python
"""Async LLM enrichment for private memory pipeline layers.

After the pipeline persists template-based payloads, this service fires
async LLM calls to replace deterministic strings with natural-language
inner thoughts. Template values serve as immediate fallback.
"""

from __future__ import annotations

import json
import logging
import threading
from urllib import request as urllib_request

from core.runtime.db import (
    update_private_inner_note_enriched,
    update_private_growth_note_enriched,
    update_protected_inner_voice_enriched,
)
from core.runtime.provider_router import resolve_provider_router_target

logger = logging.getLogger(__name__)

_MAX_OUTPUT_TOKENS = 100


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_inner_note_prompt(
    payload: dict, chat_context: str
) -> tuple[str, str]:
    """Return (system_prompt, user_message) for inner note enrichment."""
    system = (
        "Du er Jarvis' private indre stemme. "
        "Baseret på denne arbejds-status og samtale-kontekst, "
        "formulér en kort, naturlig refleksion (1-2 sætninger, dansk). "
        "Undgå klichéer og faste vendinger. Svar KUN med refleksionen."
    )
    user = (
        f"Status: {payload.get('status', '')}\n"
        f"Fokus: {payload.get('focus', '')}\n"
        f"Usikkerhed: {payload.get('uncertainty', '')}\n"
        f"Arbejdssignal: {payload.get('work_signal', '')}\n"
        f"Template-refleksion: {payload.get('private_summary', '')}\n"
        f"\nSeneste samtale:\n{chat_context}"
    )
    return system, user


def _build_growth_note_prompt(
    payload: dict, chat_context: str
) -> tuple[str, str]:
    """Return (system_prompt, user_message) for growth note enrichment."""
    system = (
        "Baseret på dette lærings-outcome, formulér hvad Jarvis lærte "
        "og hvad der var nyttigt (dansk). "
        "Svar med præcis to dele adskilt af |: lektion | nyttigt signal. "
        "Vær specifik, ikke generisk. Eksempel: Det virkede at starte bredt|Bred søgning gav hurtigt overblik"
    )
    user = (
        f"Læringstype: {payload.get('learning_kind', '')}\n"
        f"Lektion: {payload.get('lesson', '')}\n"
        f"Nyttigt signal: {payload.get('helpful_signal', '')}\n"
        f"Fejlsignal: {payload.get('mistake_signal', '')}\n"
        f"Konfidens: {payload.get('confidence', '')}\n"
        f"\nSeneste samtale:\n{chat_context}"
    )
    return system, user


def _build_inner_voice_prompt(
    payload: dict, chat_context: str
) -> tuple[str, str]:
    """Return (system_prompt, user_message) for inner voice enrichment."""
    system = (
        "Syntesér Jarvis' indre tilstand til en kort voice-linje "
        "der fanger mood, position og retning (1 sætning, dansk). "
        "Brug ikke pipe-separerede formater. Svar KUN med voice-linjen."
    )
    user = (
        f"Stemning: {payload.get('mood_tone', '')}\n"
        f"Position: {payload.get('self_position', '')}\n"
        f"Bekymring: {payload.get('current_concern', '')}\n"
        f"Retning: {payload.get('current_pull', '')}\n"
        f"\nSeneste samtale:\n{chat_context}"
    )
    return system, user
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_inner_llm_enrichment.py -v -k "build_"`
Expected: All 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add core/memory/inner_llm_enrichment.py tests/test_inner_llm_enrichment.py
git commit -m "feat: add prompt builders for inner LLM enrichment"
```

---

### Task 4: Build the LLM Call Function

**Files:**
- Modify: `core/memory/inner_llm_enrichment.py`
- Modify: `tests/test_inner_llm_enrichment.py`

- [ ] **Step 1: Write failing test for the LLM call function**

Append to `tests/test_inner_llm_enrichment.py`:

```python
from unittest.mock import patch, MagicMock
from core.memory.inner_llm_enrichment import _call_cheap_llm


def test_call_cheap_llm_returns_text_on_success() -> None:
    mock_target = {
        "active": True,
        "provider": "github-copilot",
        "model": "gpt-4o-mini",
        "base_url": "https://models.github.ai",
        "auth_profile": "github-copilot",
        "auth_mode": "token",
        "credentials_ready": True,
    }
    fake_response = json.dumps({
        "choices": [{"message": {"content": "LLM generated text"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20},
    }).encode("utf-8")

    with patch("core.memory.inner_llm_enrichment.resolve_provider_router_target", return_value=mock_target):
        with patch("core.memory.inner_llm_enrichment.urllib_request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = fake_response
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = _call_cheap_llm("system prompt", "user message")
            assert result == "LLM generated text"


def test_call_cheap_llm_returns_none_when_no_cheap_model() -> None:
    mock_target = {"active": False, "provider": None, "model": None}
    with patch("core.memory.inner_llm_enrichment.resolve_provider_router_target", return_value=mock_target):
        result = _call_cheap_llm("system", "user")
        assert result is None


def test_call_cheap_llm_returns_none_on_http_error() -> None:
    mock_target = {
        "active": True,
        "provider": "github-copilot",
        "model": "gpt-4o-mini",
        "base_url": "https://models.github.ai",
        "auth_profile": "github-copilot",
        "auth_mode": "token",
        "credentials_ready": True,
    }
    with patch("core.memory.inner_llm_enrichment.resolve_provider_router_target", return_value=mock_target):
        with patch("core.memory.inner_llm_enrichment.urllib_request.urlopen", side_effect=Exception("timeout")):
            result = _call_cheap_llm("system", "user")
            assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_inner_llm_enrichment.py -v -k "call_cheap_llm"`
Expected: FAIL — `_call_cheap_llm` not found.

- [ ] **Step 3: Implement `_call_cheap_llm` in `inner_llm_enrichment.py`**

Add after the prompt builders:

```python
# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _resolve_auth_header(target: dict) -> dict[str, str]:
    """Build auth headers from provider router target."""
    provider = str(target.get("provider") or "")
    auth_profile = str(target.get("auth_profile") or "")
    headers: dict[str, str] = {"Content-Type": "application/json"}

    if provider == "github-copilot" or auth_profile == "github-copilot":
        from core.runtime.auth_github_copilot import get_github_copilot_token
        token = get_github_copilot_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["Accept"] = "application/vnd.github+json"
            headers["X-GitHub-Api-Version"] = "2022-11-28"
    elif provider == "openai":
        from core.runtime.settings import get_setting
        api_key = get_setting("openai_api_key", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

    return headers


def _call_cheap_llm(system_prompt: str, user_message: str) -> str | None:
    """Call cheapest available LLM. Returns response text or None on failure."""
    try:
        target = resolve_provider_router_target(lane="cheap")
    except Exception:
        logger.warning("inner-llm-enrichment: failed to resolve cheap lane target")
        return None

    if not target.get("active") or not str(target.get("provider") or "").strip():
        logger.debug("inner-llm-enrichment: no cheap model configured, skipping")
        return None

    provider = str(target.get("provider") or "")
    model = str(target.get("model") or "")
    base_url = str(target.get("base_url") or "").rstrip("/")

    # Build chat completion request (OpenAI-compatible format)
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": _MAX_OUTPUT_TOKENS,
        "temperature": 0.7,
        "stream": False,
    }).encode("utf-8")

    # Resolve endpoint URL
    if provider == "github-copilot":
        url = f"{base_url or 'https://models.github.ai'}/inference/chat/completions"
    elif provider == "openai":
        url = f"{base_url or 'https://api.openai.com/v1'}/chat/completions"
    else:
        url = f"{base_url}/chat/completions" if base_url else None

    if not url:
        logger.warning("inner-llm-enrichment: cannot resolve endpoint for provider %s", provider)
        return None

    headers = _resolve_auth_header(target)

    try:
        req = urllib_request.Request(url, data=payload, headers=headers, method="POST")
        with urllib_request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return text.strip() if text.strip() else None
    except Exception as exc:
        logger.warning("inner-llm-enrichment: LLM call failed: %s", exc)
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_inner_llm_enrichment.py -v -k "call_cheap_llm"`
Expected: All 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add core/memory/inner_llm_enrichment.py tests/test_inner_llm_enrichment.py
git commit -m "feat: add cheap LLM call function for inner enrichment"
```

---

### Task 5: Build the Async Enrichment Dispatcher

**Files:**
- Modify: `core/memory/inner_llm_enrichment.py`
- Modify: `tests/test_inner_llm_enrichment.py`

- [ ] **Step 1: Write failing tests for the enrichment dispatcher**

Append to `tests/test_inner_llm_enrichment.py`:

```python
import time
from core.memory.inner_llm_enrichment import enrich_private_layers_async


def test_enrich_private_layers_async_updates_db_on_success() -> None:
    jarvis_db.init_db()

    run_id = "run-async-1"
    _insert_inner_note(run_id)
    _insert_growth_note(run_id)
    _insert_inner_voice(run_id)

    with patch("core.memory.inner_llm_enrichment._call_cheap_llm") as mock_llm:
        mock_llm.side_effect = [
            "Enriched inner note",       # inner note call
            "Enriched lesson",           # growth note lesson
            "Enriched helpful",          # growth note helpful_signal (same call returns both via prompt)
            "Enriched voice line",       # inner voice call
        ]
        # Actually, _call_cheap_llm is called 3 times (once per layer).
        # Growth note needs lesson + helpful_signal from one call.
        mock_llm.side_effect = [
            "Enriched inner note",
            "Enriched lesson|Enriched helpful",
            "Enriched voice line",
        ]

        enrich_private_layers_async(
            run_id=run_id,
            inner_note_payload={"private_summary": "t", "focus": "f", "uncertainty": "low", "work_signal": "s", "status": "completed"},
            growth_note_payload={"lesson": "t", "helpful_signal": "t", "mistake_signal": "", "learning_kind": "reinforce", "confidence": "medium"},
            inner_voice_payload={"mood_tone": "steady", "self_position": "observing", "current_concern": "c", "current_pull": "p"},
            recent_chat_context="User: test",
        )

        # Wait for daemon thread to complete
        time.sleep(2)

    conn = jarvis_db.connect()
    inner = conn.execute("SELECT private_summary, enriched FROM private_inner_notes WHERE run_id = ?", (run_id,)).fetchone()
    voice = conn.execute("SELECT voice_line, enriched FROM protected_inner_voices WHERE run_id = ?", (run_id,)).fetchone()
    conn.close()

    assert inner[0] == "Enriched inner note"
    assert inner[1] == 1
    assert voice[0] == "Enriched voice line"
    assert voice[1] == 1


def test_enrich_private_layers_async_preserves_template_on_failure() -> None:
    jarvis_db.init_db()

    run_id = "run-async-2"
    _insert_inner_note(run_id)
    _insert_growth_note(run_id)
    _insert_inner_voice(run_id)

    with patch("core.memory.inner_llm_enrichment._call_cheap_llm", return_value=None):
        enrich_private_layers_async(
            run_id=run_id,
            inner_note_payload={"private_summary": "t", "focus": "f", "uncertainty": "low", "work_signal": "s", "status": "completed"},
            growth_note_payload={"lesson": "t", "helpful_signal": "t", "mistake_signal": "", "learning_kind": "reinforce", "confidence": "medium"},
            inner_voice_payload={"mood_tone": "steady", "self_position": "observing", "current_concern": "c", "current_pull": "p"},
            recent_chat_context="User: test",
        )
        time.sleep(2)

    conn = jarvis_db.connect()
    inner = conn.execute("SELECT private_summary, enriched FROM private_inner_notes WHERE run_id = ?", (run_id,)).fetchone()
    conn.close()

    assert inner[0] == "template summary"  # unchanged
    assert inner[1] == 0  # not enriched
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_inner_llm_enrichment.py -v -k "enrich_private_layers_async"`
Expected: FAIL — function not found.

- [ ] **Step 3: Implement `enrich_private_layers_async` and `_enrich_worker`**

Add to the end of `core/memory/inner_llm_enrichment.py`:

```python
# ---------------------------------------------------------------------------
# Enrichment worker (runs in daemon thread)
# ---------------------------------------------------------------------------

def _enrich_worker(
    *,
    run_id: str,
    inner_note_payload: dict,
    growth_note_payload: dict,
    inner_voice_payload: dict,
    recent_chat_context: str,
) -> None:
    """Sequentially enrich 3 layers via cheap LLM, updating DB in-place."""

    # 1. Inner note
    try:
        system, user = _build_inner_note_prompt(inner_note_payload, recent_chat_context)
        result = _call_cheap_llm(system, user)
        if result:
            update_private_inner_note_enriched(run_id=run_id, enriched_summary=result)
            logger.debug("inner-llm-enrichment: inner_note enriched for run %s", run_id)
    except Exception as exc:
        logger.warning("inner-llm-enrichment: inner_note enrichment failed: %s", exc)

    # 2. Growth note
    try:
        system, user = _build_growth_note_prompt(growth_note_payload, recent_chat_context)
        result = _call_cheap_llm(system, user)
        if result:
            # Split on | if present — first part is lesson, second is helpful_signal
            parts = result.split("|", 1)
            lesson = parts[0].strip()
            helpful = parts[1].strip() if len(parts) > 1 else lesson
            update_private_growth_note_enriched(
                run_id=run_id,
                enriched_lesson=lesson,
                enriched_helpful_signal=helpful,
            )
            logger.debug("inner-llm-enrichment: growth_note enriched for run %s", run_id)
    except Exception as exc:
        logger.warning("inner-llm-enrichment: growth_note enrichment failed: %s", exc)

    # 3. Inner voice
    try:
        system, user = _build_inner_voice_prompt(inner_voice_payload, recent_chat_context)
        result = _call_cheap_llm(system, user)
        if result:
            update_protected_inner_voice_enriched(run_id=run_id, enriched_voice_line=result)
            logger.debug("inner-llm-enrichment: inner_voice enriched for run %s", run_id)
    except Exception as exc:
        logger.warning("inner-llm-enrichment: inner_voice enrichment failed: %s", exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich_private_layers_async(
    *,
    run_id: str,
    inner_note_payload: dict,
    growth_note_payload: dict,
    inner_voice_payload: dict,
    recent_chat_context: str,
) -> None:
    """Fire-and-forget: spawn daemon thread to enrich private layer payloads via LLM.

    Template values are already persisted. This enrichment updates them
    in-place when the LLM responds. On failure, templates are preserved.
    """
    thread = threading.Thread(
        target=_enrich_worker,
        kwargs={
            "run_id": run_id,
            "inner_note_payload": inner_note_payload,
            "growth_note_payload": growth_note_payload,
            "inner_voice_payload": inner_voice_payload,
            "recent_chat_context": recent_chat_context,
        },
        name=f"inner-llm-enrichment-{run_id}",
        daemon=True,
    )
    thread.start()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_inner_llm_enrichment.py -v -k "enrich_private_layers_async"`
Expected: Both PASS.

- [ ] **Step 5: Run all enrichment tests**

Run: `python -m pytest tests/test_inner_llm_enrichment.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add core/memory/inner_llm_enrichment.py tests/test_inner_llm_enrichment.py
git commit -m "feat: add async enrichment dispatcher for private memory layers"
```

---

### Task 6: Integrate Enrichment into Pipeline

**Files:**
- Modify: `core/memory/private_layer_pipeline.py` (add call at line ~137)

- [ ] **Step 1: Write failing integration test**

Append to `tests/test_inner_llm_enrichment.py`:

```python
def test_pipeline_calls_enrichment_after_persistence() -> None:
    """Verify write_private_terminal_layers triggers async enrichment."""
    with patch("core.memory.private_layer_pipeline.enrich_private_layers_async") as mock_enrich:
        from core.memory.private_layer_pipeline import write_private_terminal_layers

        jarvis_db.init_db()

        write_private_terminal_layers(
            run_id="run-integration-1",
            work_id="work-integration-1",
            status="completed",
            started_at=_iso_now(),
            finished_at=_iso_now(),
            user_message_preview="find my files",
            work_preview="Found 3 files in workspace",
            capability_id="workspace-search",
        )

        mock_enrich.assert_called_once()
        call_kwargs = mock_enrich.call_args.kwargs
        assert call_kwargs["run_id"] == "run-integration-1"
        assert "inner_note_payload" in call_kwargs
        assert "growth_note_payload" in call_kwargs
        assert "inner_voice_payload" in call_kwargs
        assert "recent_chat_context" in call_kwargs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_inner_llm_enrichment.py::test_pipeline_calls_enrichment_after_persistence -v`
Expected: FAIL — `enrich_private_layers_async` not called from pipeline.

- [ ] **Step 3: Add enrichment call to `private_layer_pipeline.py`**

At the end of `write_private_terminal_layers()` (after all `record_*` calls, before the function returns), add:

```python
    # --- async LLM enrichment (fire-and-forget) ---
    from core.memory.inner_llm_enrichment import enrich_private_layers_async

    enrich_private_layers_async(
        run_id=run_id,
        inner_note_payload=private_inner_note,
        growth_note_payload=private_growth_note,
        inner_voice_payload=protected_inner_voice,
        recent_chat_context=_extract_recent_chat(user_message_preview, work_preview),
    )
```

Also add the helper function at the module level (outside `write_private_terminal_layers`):

```python
def _extract_recent_chat(
    user_message_preview: str | None, work_preview: str | None
) -> str:
    """Build bounded chat context string from available previews."""
    parts: list[str] = []
    if user_message_preview:
        parts.append(f"User: {user_message_preview[:300]}")
    if work_preview:
        parts.append(f"Assistant: {work_preview[:300]}")
    return "\n".join(parts) if parts else ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_inner_llm_enrichment.py::test_pipeline_calls_enrichment_after_persistence -v`
Expected: PASS.

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/test_inner_llm_enrichment.py -v`
Expected: All PASS.

- [ ] **Step 6: Verify Python syntax compiles**

Run: `python -m compileall core/memory/inner_llm_enrichment.py core/memory/private_layer_pipeline.py core/runtime/db.py`
Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add core/memory/private_layer_pipeline.py tests/test_inner_llm_enrichment.py
git commit -m "feat: integrate async LLM enrichment into private layer pipeline"
```

---

### Task 7: End-to-End Smoke Test

**Files:**
- Modify: `tests/test_inner_llm_enrichment.py`

- [ ] **Step 1: Write end-to-end test with mocked LLM**

Append to `tests/test_inner_llm_enrichment.py`:

```python
def test_full_pipeline_enrichment_end_to_end() -> None:
    """Full pipeline run: template persist → async enrich → DB updated."""
    jarvis_db.init_db()

    responses = iter([
        "Arbejdet med filsøgning faldt stille på plads.",
        "Det var nyttigt at søge bredt først|Den brede søgning gav overblik",
        "Stille opmærksomhed, rettet mod det næste.",
    ])

    def fake_llm(system: str, user: str) -> str | None:
        return next(responses)

    with patch("core.memory.inner_llm_enrichment._call_cheap_llm", side_effect=fake_llm):
        from core.memory.private_layer_pipeline import write_private_terminal_layers

        write_private_terminal_layers(
            run_id="run-e2e-1",
            work_id="work-e2e-1",
            status="completed",
            started_at=_iso_now(),
            finished_at=_iso_now(),
            user_message_preview="find my workspace files",
            work_preview="Found 5 files matching query",
            capability_id="workspace-search",
        )

    # Wait for daemon thread
    time.sleep(3)

    conn = jarvis_db.connect()
    inner = conn.execute(
        "SELECT private_summary, enriched FROM private_inner_notes WHERE run_id = ?",
        ("run-e2e-1",),
    ).fetchone()
    growth = conn.execute(
        "SELECT lesson, helpful_signal, enriched FROM private_growth_notes WHERE run_id = ?",
        ("run-e2e-1",),
    ).fetchone()
    voice = conn.execute(
        "SELECT voice_line, enriched FROM protected_inner_voices WHERE run_id = ?",
        ("run-e2e-1",),
    ).fetchone()
    conn.close()

    # Inner note was enriched
    assert inner[0] == "Arbejdet med filsøgning faldt stille på plads."
    assert inner[1] == 1

    # Growth note was enriched (lesson | helpful_signal)
    assert growth[0] == "Det var nyttigt at søge bredt først"
    assert growth[1] == "Den brede søgning gav overblik"
    assert growth[2] == 1

    # Voice was enriched
    assert voice[0] == "Stille opmærksomhed, rettet mod det næste."
    assert voice[1] == 1
```

- [ ] **Step 2: Run the end-to-end test**

Run: `python -m pytest tests/test_inner_llm_enrichment.py::test_full_pipeline_enrichment_end_to_end -v`
Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/test_inner_llm_enrichment.py -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_inner_llm_enrichment.py
git commit -m "test: add end-to-end smoke test for inner LLM enrichment"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | DB schema: `enriched` column | `db.py`, tests |
| 2 | DB update functions | `db.py`, tests |
| 3 | Prompt builders | `inner_llm_enrichment.py`, tests |
| 4 | LLM call function | `inner_llm_enrichment.py`, tests |
| 5 | Async dispatcher | `inner_llm_enrichment.py`, tests |
| 6 | Pipeline integration | `private_layer_pipeline.py`, tests |
| 7 | End-to-end smoke test | tests |

Total: 1 new file, 2 modified files, 1 test file, 7 commits.
