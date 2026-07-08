---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Anthropic-Compat Endpoint — Implementation Plan (Mode 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Desktop / Claude Code-compatible Anthropic Messages API endpoint (`POST /anthropic/v1/messages` + `GET /anthropic/v1/models`) that exposes Jarvis as a model — keeping Jarvis's identity (per-user workspace) while letting Claude Desktop's tools execute on the user's local machine.

**Architecture:** Stateless proxy in front of Ollama (visible-lane backend). API-key middleware resolves user → workspace ContextVar. Identity prefix from workspace files prepended to Claude Desktop's system parameter. Anthropic ↔ Ollama format translation. Streaming via `AnthropicSSEEmitter` state machine that emits the full Anthropic event sequence (`message_start` → `content_block_start` → `content_block_delta` → `content_block_stop` → `message_delta` → `message_stop`) including `tool_use` blocks with `input_json_delta` events.

**Tech Stack:** Python 3.11, FastAPI, Anthropic Messages API protocol, Ollama `/api/chat` (with tools), SSE streaming.

**Spec:** `docs/superpowers/specs/2026-05-06-anthropic-compat-design.md`

**Mode 2 only:** This plan does NOT add Jarvis's internal tools (`recall_memories`, `search_jarvis_brain`, etc.) to the toolset. That's Mode 3, deferred to a separate plan.

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `apps/api/jarvis_api/middleware/anthropic_auth.py` | API-key validation, user resolution, workspace ContextVar binding |
| `core/services/anthropic_identity.py` | Build identity prefix from workspace files (cached) |
| `core/services/anthropic_translator.py` | Request and response format conversion between Anthropic and Ollama |
| `core/services/anthropic_sse_emitter.py` | `AnthropicSSEEmitter` — streaming state machine |
| `apps/api/jarvis_api/routes/anthropic_compat.py` | `/anthropic/v1/messages` + `/anthropic/v1/models` |
| `state/anthropic_api_keys.json` | API-key → user mapping (gitignored, force-add for scaffold) |
| `tests/services/test_anthropic_identity.py` | |
| `tests/services/test_anthropic_translator.py` | |
| `tests/services/test_anthropic_sse_emitter.py` | |
| `tests/api/test_anthropic_messages.py` | Endpoint integration test |
| `tests/api/test_anthropic_auth.py` | Auth middleware test |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `anthropic_compat_enabled: bool = True`, `anthropic_compat_dev_mode_open: bool = False` |
| `apps/api/jarvis_api/app.py` | Register `anthropic_compat_router` and `anthropic_auth_middleware` |

---

## Task 1: Settings flags + state scaffold

**Files:**
- Modify: `core/runtime/settings.py`
- Create: `state/anthropic_api_keys.json`

- [ ] **Step 1: Add settings**

In `core/runtime/settings.py`, add inside `RuntimeSettings` (next to other tool_router settings):

```python
    # Anthropic-compat endpoint (added 2026-05-06)
    anthropic_compat_enabled: bool = True
    # When true, requests without x-api-key are accepted in dev (resolves to default workspace).
    # NEVER enable in production.
    anthropic_compat_dev_mode_open: bool = False
```

- [ ] **Step 2: Seed the API-key mapping file**

Create `state/anthropic_api_keys.json`:

```json
{
  "_doc": "Anthropic-compat API key registry. Keys map to user/workspace. Generate keys with `openssl rand -hex 24` prefixed with 'jvs-<user>-'.",
  "keys": {}
}
```

- [ ] **Step 3: Commit**

```bash
git add core/runtime/settings.py
git add -f state/anthropic_api_keys.json
git commit -m "feat(anthropic-compat): settings flags + API key registry scaffold"
```

---

## Task 2: anthropic_auth middleware

**Files:**
- Create: `apps/api/jarvis_api/middleware/anthropic_auth.py`
- Test: `tests/api/test_anthropic_auth.py`

- [ ] **Step 1: Write failing tests**

Create `tests/api/test_anthropic_auth.py`:

```python
"""Verify x-api-key resolution for Anthropic endpoint."""
import json
import pytest
from pathlib import Path

from apps.api.jarvis_api.middleware import anthropic_auth as ah


@pytest.fixture
def isolated_keys(tmp_path, monkeypatch):
    keys_path = tmp_path / "anthropic_api_keys.json"
    keys_path.write_text(json.dumps({
        "keys": {
            "jvs-bjorn-test-key": {"user": "bjorn", "workspace": "default"},
            "jvs-mikkel-test-key": {"user": "mikkel", "workspace": "mikkel"},
        }
    }))
    monkeypatch.setattr(ah, "_KEYS_PATH", keys_path)
    monkeypatch.setattr(ah, "_REPO_KEYS_PATH", keys_path)
    ah.invalidate_cache()
    return keys_path


def test_resolve_valid_key(isolated_keys):
    out = ah.resolve_api_key("jvs-bjorn-test-key")
    assert out == {"user": "bjorn", "workspace": "default"}


def test_resolve_invalid_key_returns_none(isolated_keys):
    assert ah.resolve_api_key("nonexistent") is None


def test_resolve_empty_key_returns_none(isolated_keys):
    assert ah.resolve_api_key("") is None
    assert ah.resolve_api_key(None) is None


def test_resolve_strips_whitespace(isolated_keys):
    out = ah.resolve_api_key("  jvs-bjorn-test-key  ")
    assert out is not None
    assert out["user"] == "bjorn"


def test_dev_mode_open_returns_default(monkeypatch, isolated_keys):
    out = ah.resolve_api_key("anything", dev_mode_open=True)
    assert out == {"user": "dev", "workspace": "default"}


def test_dev_mode_off_no_match(isolated_keys):
    assert ah.resolve_api_key("anything", dev_mode_open=False) is None
```

Run: `pytest tests/api/test_anthropic_auth.py -v`. Expected: FAIL (module missing).

- [ ] **Step 2: Implement middleware**

Create `apps/api/jarvis_api/middleware/anthropic_auth.py`:

```python
"""x-api-key resolution + workspace binding for Anthropic-compat endpoint."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_STATE_DIR = Path(os.getenv("JARVIS_STATE_DIR") or (Path.home() / ".jarvis-v2" / "state"))
_KEYS_PATH = _STATE_DIR / "anthropic_api_keys.json"

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_REPO_KEYS_PATH = _REPO_ROOT / "state" / "anthropic_api_keys.json"

_cache: dict[str, dict] = {}
_loaded = False


def _load() -> dict:
    global _loaded
    if _loaded:
        return _cache
    raw = {}
    for path in (_KEYS_PATH, _REPO_KEYS_PATH):
        if path.exists():
            try:
                raw = json.loads(path.read_text()).get("keys", {}) or {}
                break
            except Exception as exc:
                logger.warning("anthropic_auth: failed to read %s: %s", path, exc)
    _cache.clear()
    _cache.update(raw or {})
    _loaded = True
    return _cache


def invalidate_cache() -> None:
    global _loaded
    _cache.clear()
    _loaded = False


def resolve_api_key(api_key: Optional[str], *, dev_mode_open: bool = False) -> Optional[dict]:
    """Return {'user': str, 'workspace': str} or None for invalid keys."""
    if dev_mode_open:
        return {"user": "dev", "workspace": "default"}
    if not api_key:
        return None
    normalized = str(api_key).strip()
    if not normalized:
        return None
    keys = _load()
    return keys.get(normalized)


def short_key_for_log(api_key: Optional[str]) -> str:
    """Return first 4 chars + length suffix; never log full key."""
    if not api_key:
        return "<none>"
    n = str(api_key).strip()
    if len(n) <= 4:
        return f"<{len(n)}-char-key>"
    return f"{n[:4]}…<{len(n)}>"
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/api/test_anthropic_auth.py -v`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/middleware/anthropic_auth.py tests/api/test_anthropic_auth.py
git commit -m "feat(anthropic-compat): x-api-key resolution with cached registry"
```

---

## Task 3: anthropic_identity — build identity prefix

**Files:**
- Create: `core/services/anthropic_identity.py`
- Test: `tests/services/test_anthropic_identity.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_anthropic_identity.py`:

```python
import pytest
from pathlib import Path

from core.services import anthropic_identity as ai


def test_build_prefix_with_all_files(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "SOUL.md").write_text("I am Jarvis.")
    (ws / "IDENTITY.md").write_text("Identity facts.")
    (ws / "USER.md").write_text("Bjorn lives in Svendborg.")
    (ws / "STANDING_ORDERS.md").write_text("Be honest.")
    out = ai.build_identity_prefix(ws)
    assert "## SOUL.md" in out
    assert "I am Jarvis." in out
    assert "## IDENTITY.md" in out
    assert "## USER.md" in out
    assert "Bjorn lives in Svendborg." in out
    assert "## STANDING_ORDERS.md" in out


def test_build_prefix_with_missing_files(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "SOUL.md").write_text("Soul.")
    out = ai.build_identity_prefix(ws)
    assert "## SOUL.md" in out
    assert "## IDENTITY.md" not in out


def test_build_prefix_empty_workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    out = ai.build_identity_prefix(ws)
    assert out == ""


def test_build_prefix_caches_until_mtime_changes(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "SOUL.md").write_text("v1")
    a = ai.build_identity_prefix(ws)
    b = ai.build_identity_prefix(ws)
    assert a == b
    # Touch file with new content; mtime advances
    import time
    time.sleep(0.01)
    (ws / "SOUL.md").write_text("v2")
    c = ai.build_identity_prefix(ws)
    assert "v2" in c
```

Run: `pytest tests/services/test_anthropic_identity.py -v`. Expected: FAIL.

- [ ] **Step 2: Implement**

Create `core/services/anthropic_identity.py`:

```python
"""Build Jarvis identity prefix from a workspace directory.

Reads SOUL.md, IDENTITY.md, USER.md, STANDING_ORDERS.md (in that order)
and concatenates them into a single system-prompt prefix. Cached per
workspace; invalidated when any file's mtime advances.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_FILES_IN_ORDER = ("SOUL.md", "IDENTITY.md", "USER.md", "STANDING_ORDERS.md")

# cache: workspace_path_str -> (signature, content)
_cache: dict[str, tuple[str, str]] = {}


def _signature(workspace_dir: Path) -> str:
    parts = []
    for name in _FILES_IN_ORDER:
        p = workspace_dir / name
        if p.exists():
            try:
                parts.append(f"{name}:{p.stat().st_mtime_ns}")
            except OSError:
                pass
    return "|".join(parts)


def build_identity_prefix(workspace_dir: Path) -> str:
    """Return concatenated identity files for this workspace, or empty string.

    Format: each present file becomes a `## <FILENAME>\\n\\n<contents>`
    section, joined by blank lines.
    """
    key = str(workspace_dir.resolve())
    sig = _signature(workspace_dir)

    cached = _cache.get(key)
    if cached and cached[0] == sig:
        return cached[1]

    parts = []
    for name in _FILES_IN_ORDER:
        p = workspace_dir / name
        if not p.exists():
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("anthropic_identity: cannot read %s: %s", p, exc)
            continue
        parts.append(f"## {name}\n\n{content.strip()}")

    out = "\n\n".join(parts)
    _cache[key] = (sig, out)
    return out


def invalidate_cache() -> None:
    _cache.clear()
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_anthropic_identity.py -v`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/services/anthropic_identity.py tests/services/test_anthropic_identity.py
git commit -m "feat(anthropic-compat): identity prefix builder with mtime cache"
```

---

## Task 4: anthropic_translator — request side (Anthropic → Ollama)

**Files:**
- Create: `core/services/anthropic_translator.py`
- Test: `tests/services/test_anthropic_translator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_anthropic_translator.py`:

```python
import pytest

from core.services import anthropic_translator as at


def test_translate_simple_user_message():
    body = {
        "model": "jarvis",
        "messages": [{"role": "user", "content": "hej"}],
    }
    out = at.translate_request_to_ollama(
        anthropic_body=body,
        identity_prefix="## SOUL\nJeg er Jarvis.",
        backend_model="glm-5.1:cloud",
    )
    assert out["model"] == "glm-5.1:cloud"
    assert out["messages"][0] == {"role": "system", "content": "## SOUL\nJeg er Jarvis."}
    assert out["messages"][-1] == {"role": "user", "content": "hej"}


def test_translate_appends_system_to_identity_prefix():
    body = {
        "model": "jarvis",
        "system": "You are in Claude Code.",
        "messages": [{"role": "user", "content": "x"}],
    }
    out = at.translate_request_to_ollama(
        anthropic_body=body,
        identity_prefix="## SOUL\nJarvis.",
        backend_model="m",
    )
    sys_msg = out["messages"][0]["content"]
    assert "Jarvis." in sys_msg
    assert "You are in Claude Code." in sys_msg
    assert sys_msg.index("Jarvis.") < sys_msg.index("You are in Claude Code.")


def test_translate_assistant_with_tool_use():
    body = {
        "messages": [
            {"role": "user", "content": "list files"},
            {"role": "assistant", "content": [
                {"type": "text", "text": "Looking..."},
                {"type": "tool_use", "id": "toolu_1", "name": "Bash", "input": {"command": "ls"}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "toolu_1", "content": "file1\nfile2"},
            ]},
        ],
    }
    out = at.translate_request_to_ollama(
        anthropic_body=body, identity_prefix="", backend_model="m",
    )
    msgs = out["messages"]
    # Should have: assistant with tool_calls, then tool result
    assistant_msg = next(m for m in msgs if m["role"] == "assistant")
    assert assistant_msg["content"] == "Looking..."
    assert len(assistant_msg["tool_calls"]) == 1
    assert assistant_msg["tool_calls"][0]["function"]["name"] == "Bash"
    tool_msg = next(m for m in msgs if m["role"] == "tool")
    assert tool_msg["content"] == "file1\nfile2"
    assert tool_msg.get("tool_call_id") == "toolu_1"


def test_translate_tools_anthropic_to_ollama():
    body = {
        "messages": [{"role": "user", "content": "x"}],
        "tools": [
            {
                "name": "Read",
                "description": "Read a file",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        ],
    }
    out = at.translate_request_to_ollama(body, identity_prefix="", backend_model="m")
    assert "tools" in out
    tool = out["tools"][0]
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "Read"
    assert tool["function"]["description"] == "Read a file"
    assert tool["function"]["parameters"]["properties"]["path"]["type"] == "string"


def test_translate_string_content_unchanged():
    """User message with string content stays as string."""
    body = {"messages": [{"role": "user", "content": "plain text"}]}
    out = at.translate_request_to_ollama(body, identity_prefix="", backend_model="m")
    assert out["messages"][0]["content"] == "plain text"


def test_translate_stream_flag_passed():
    body = {"messages": [{"role": "user", "content": "x"}], "stream": True}
    out = at.translate_request_to_ollama(body, identity_prefix="", backend_model="m")
    assert out["stream"] is True
```

Run: `pytest tests/services/test_anthropic_translator.py -v`. Expected: FAIL.

- [ ] **Step 2: Implement request translator**

Create `core/services/anthropic_translator.py`:

```python
"""Translate between Anthropic Messages API format and Ollama /api/chat format.

Anthropic format uses content blocks (text, tool_use, tool_result), system
as a top-level field, and `tools` with `input_schema`. Ollama format uses
flat `messages` (with optional `tool_calls` on assistant messages and
separate `tool` role messages for results) and `tools` with `parameters`.
"""
from __future__ import annotations

from typing import Any


def translate_request_to_ollama(
    anthropic_body: dict[str, Any],
    *,
    identity_prefix: str,
    backend_model: str,
) -> dict[str, Any]:
    """Build an Ollama /api/chat payload from an Anthropic Messages request."""
    out: dict[str, Any] = {
        "model": backend_model,
        "messages": [],
        "stream": bool(anthropic_body.get("stream", False)),
    }

    # System message: identity prefix + Anthropic's system parameter
    user_system = str(anthropic_body.get("system") or "").strip()
    sys_parts = [s for s in (identity_prefix.strip(), user_system) if s]
    if sys_parts:
        out["messages"].append({
            "role": "system",
            "content": "\n\n".join(sys_parts),
        })

    # Translate each message
    for msg in anthropic_body.get("messages", []):
        out["messages"].extend(_translate_message(msg))

    # Translate tools (rename input_schema → parameters; wrap in function shape)
    if anthropic_body.get("tools"):
        out["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": str(t.get("name") or ""),
                    "description": str(t.get("description") or ""),
                    "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
                },
            }
            for t in anthropic_body["tools"]
            if t.get("name")
        ]

    # max_tokens → options.num_predict
    if anthropic_body.get("max_tokens"):
        out.setdefault("options", {})["num_predict"] = int(anthropic_body["max_tokens"])

    return out


def _translate_message(msg: dict[str, Any]) -> list[dict[str, Any]]:
    """Translate a single Anthropic message into 1-N Ollama messages.

    A user message with multiple tool_result blocks expands to multiple
    Ollama tool-role messages. An assistant message with text + tool_use
    becomes a single assistant message with text content + tool_calls list.
    """
    role = str(msg.get("role") or "user")
    content = msg.get("content")

    # String content → simple message
    if isinstance(content, str):
        return [{"role": role, "content": content}]

    if not isinstance(content, list):
        return [{"role": role, "content": str(content or "")}]

    if role == "user":
        # User can have text + tool_result blocks
        text_parts = []
        tool_results = []
        for block in content:
            btype = str(block.get("type") or "")
            if btype == "text":
                text_parts.append(str(block.get("text") or ""))
            elif btype == "tool_result":
                tool_results.append(block)
            # Other types (image) ignored in Mode 2

        out_msgs = []
        if text_parts:
            out_msgs.append({"role": "user", "content": "\n".join(text_parts)})
        for tr in tool_results:
            out_msgs.append({
                "role": "tool",
                "tool_call_id": str(tr.get("tool_use_id") or ""),
                "content": _stringify_tool_result_content(tr.get("content")),
            })
        return out_msgs

    if role == "assistant":
        text_parts = []
        tool_calls = []
        for block in content:
            btype = str(block.get("type") or "")
            if btype == "text":
                text_parts.append(str(block.get("text") or ""))
            elif btype == "tool_use":
                tool_calls.append({
                    "id": str(block.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(block.get("name") or ""),
                        "arguments": block.get("input") or {},
                    },
                })

        out: dict[str, Any] = {
            "role": "assistant",
            "content": "\n".join(text_parts),
        }
        if tool_calls:
            out["tool_calls"] = tool_calls
        return [out]

    # Unknown role → passthrough as plain text
    return [{"role": role, "content": str(content)}]


def _stringify_tool_result_content(content: Any) -> str:
    """Anthropic tool_result content can be string or list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content or "")
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_anthropic_translator.py -v`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/services/anthropic_translator.py tests/services/test_anthropic_translator.py
git commit -m "feat(anthropic-compat): translator request side (Anthropic → Ollama)"
```

---

## Task 5: anthropic_sse_emitter — streaming state machine

**Files:**
- Create: `core/services/anthropic_sse_emitter.py`
- Test: `tests/services/test_anthropic_sse_emitter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_anthropic_sse_emitter.py`:

```python
import json
import pytest

from core.services.anthropic_sse_emitter import AnthropicSSEEmitter


def _parse(events: list[str]) -> list[tuple[str, dict]]:
    """Parse a list of SSE chunks into (event_name, data) pairs."""
    out = []
    for chunk in events:
        lines = chunk.strip().split("\n")
        ev = ""
        data = {}
        for line in lines:
            if line.startswith("event: "):
                ev = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        out.append((ev, data))
    return out


def test_text_only_emits_correct_sequence():
    emitter = AnthropicSSEEmitter(message_id="msg_x", model="jarvis")
    events = []
    events.extend(emitter.begin_message())
    events.extend(emitter.text_delta("Hej"))
    events.extend(emitter.text_delta(" Bjørn"))
    events.extend(emitter.end_message(stop_reason="end_turn"))

    parsed = _parse(events)
    names = [p[0] for p in parsed]
    assert names == [
        "message_start",
        "content_block_start",
        "content_block_delta",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]
    # Verify text deltas
    assert parsed[2][1]["delta"] == {"type": "text_delta", "text": "Hej"}
    assert parsed[3][1]["delta"] == {"type": "text_delta", "text": " Bjørn"}
    # stop_reason in message_delta
    assert parsed[5][1]["delta"]["stop_reason"] == "end_turn"


def test_tool_use_emits_correct_sequence():
    emitter = AnthropicSSEEmitter(message_id="msg_x", model="jarvis")
    events = []
    events.extend(emitter.begin_message())
    events.extend(emitter.text_delta("Looking..."))
    # Transition from text → tool_use must close the text block first
    events.extend(emitter.tool_use_start(tool_call_id="toolu_1", name="Bash"))
    events.extend(emitter.tool_use_input_delta(partial_json='{"command":"ls"}'))
    events.extend(emitter.end_message(stop_reason="tool_use"))

    parsed = _parse(events)
    names = [p[0] for p in parsed]
    assert names == [
        "message_start",
        "content_block_start",  # text
        "content_block_delta",  # text_delta
        "content_block_stop",   # close text
        "content_block_start",  # tool_use
        "content_block_delta",  # input_json_delta
        "content_block_stop",   # close tool_use
        "message_delta",
        "message_stop",
    ]
    # tool_use block has correct shape
    assert parsed[4][1]["content_block"]["type"] == "tool_use"
    assert parsed[4][1]["content_block"]["name"] == "Bash"
    assert parsed[4][1]["content_block"]["id"] == "toolu_1"
    # input_json_delta
    assert parsed[5][1]["delta"] == {"type": "input_json_delta", "partial_json": '{"command":"ls"}'}


def test_no_text_before_tool_use_skips_text_block():
    """If there's only tool_use (no text), no text block is opened."""
    emitter = AnthropicSSEEmitter(message_id="m", model="jarvis")
    events = []
    events.extend(emitter.begin_message())
    events.extend(emitter.tool_use_start(tool_call_id="t1", name="Read"))
    events.extend(emitter.tool_use_input_delta('{"p":"/x"}'))
    events.extend(emitter.end_message(stop_reason="tool_use"))

    parsed = _parse(events)
    names = [p[0] for p in parsed]
    assert names == [
        "message_start",
        "content_block_start",  # tool_use (index 0)
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]


def test_index_increments_across_blocks():
    emitter = AnthropicSSEEmitter(message_id="m", model="jarvis")
    events = []
    events.extend(emitter.begin_message())
    events.extend(emitter.text_delta("a"))
    events.extend(emitter.tool_use_start("t1", "Bash"))
    events.extend(emitter.tool_use_input_delta("{}"))
    events.extend(emitter.tool_use_start("t2", "Read"))
    events.extend(emitter.tool_use_input_delta("{}"))
    events.extend(emitter.end_message(stop_reason="tool_use"))

    parsed = _parse(events)
    # Text block is index 0, first tool_use index 1, second tool_use index 2
    block_starts = [p for p in parsed if p[0] == "content_block_start"]
    indices = [bs[1]["index"] for bs in block_starts]
    assert indices == [0, 1, 2]


def test_ping_event_has_correct_shape():
    emitter = AnthropicSSEEmitter(message_id="m", model="jarvis")
    events = list(emitter.ping())
    parsed = _parse(events)
    assert parsed[0][0] == "ping"
    assert parsed[0][1] == {"type": "ping"}
```

Run: `pytest tests/services/test_anthropic_sse_emitter.py -v`. Expected: FAIL.

- [ ] **Step 2: Implement state machine**

Create `core/services/anthropic_sse_emitter.py`:

```python
"""Anthropic Messages API SSE state machine.

Emits a sequence of `event: <name>\\ndata: <json>\\n\\n` chunks matching
the Anthropic streaming protocol. Tracks current open content block so
text → tool_use transitions emit a `content_block_stop` first.
"""
from __future__ import annotations

import json
from typing import Iterator, Optional


class AnthropicSSEEmitter:
    """Stateful emitter for one streamed message.

    Usage:
        emitter = AnthropicSSEEmitter(message_id="msg_x", model="jarvis")
        yield from emitter.begin_message()
        yield from emitter.text_delta("Hej")
        yield from emitter.tool_use_start("toolu_1", "Bash")
        yield from emitter.tool_use_input_delta('{"cmd":"ls"}')
        yield from emitter.end_message(stop_reason="tool_use")
    """

    def __init__(self, *, message_id: str, model: str):
        self.message_id = message_id
        self.model = model
        self._next_index = 0
        self._open_block_type: Optional[str] = None  # "text" | "tool_use" | None
        self._open_block_index: Optional[int] = None
        self._message_started = False
        self._message_ended = False

    # ---- emission helpers ----

    @staticmethod
    def _format(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def begin_message(self) -> Iterator[str]:
        if self._message_started:
            return
        self._message_started = True
        yield self._format("message_start", {
            "type": "message_start",
            "message": {
                "id": self.message_id,
                "type": "message",
                "role": "assistant",
                "model": self.model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        })

    def _close_open_block(self) -> Iterator[str]:
        if self._open_block_type is None:
            return
        idx = self._open_block_index
        self._open_block_type = None
        self._open_block_index = None
        yield self._format("content_block_stop", {
            "type": "content_block_stop",
            "index": idx,
        })

    def _open_text_block(self) -> Iterator[str]:
        idx = self._next_index
        self._next_index += 1
        self._open_block_type = "text"
        self._open_block_index = idx
        yield self._format("content_block_start", {
            "type": "content_block_start",
            "index": idx,
            "content_block": {"type": "text", "text": ""},
        })

    def text_delta(self, text: str) -> Iterator[str]:
        if not text:
            return
        if self._open_block_type != "text":
            yield from self._close_open_block()
            yield from self._open_text_block()
        yield self._format("content_block_delta", {
            "type": "content_block_delta",
            "index": self._open_block_index,
            "delta": {"type": "text_delta", "text": text},
        })

    def tool_use_start(self, tool_call_id: str, name: str) -> Iterator[str]:
        yield from self._close_open_block()
        idx = self._next_index
        self._next_index += 1
        self._open_block_type = "tool_use"
        self._open_block_index = idx
        yield self._format("content_block_start", {
            "type": "content_block_start",
            "index": idx,
            "content_block": {
                "type": "tool_use",
                "id": tool_call_id,
                "name": name,
                "input": {},
            },
        })

    def tool_use_input_delta(self, partial_json: str) -> Iterator[str]:
        if self._open_block_type != "tool_use":
            return
        yield self._format("content_block_delta", {
            "type": "content_block_delta",
            "index": self._open_block_index,
            "delta": {"type": "input_json_delta", "partial_json": partial_json},
        })

    def end_message(self, *, stop_reason: str, output_tokens: int = 0) -> Iterator[str]:
        if self._message_ended:
            return
        yield from self._close_open_block()
        yield self._format("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": output_tokens},
        })
        yield self._format("message_stop", {"type": "message_stop"})
        self._message_ended = True

    def ping(self) -> Iterator[str]:
        yield self._format("ping", {"type": "ping"})

    def error(self, message: str) -> Iterator[str]:
        """Emit a graceful error: close any open block, emit error stop."""
        yield from self._close_open_block()
        yield self._format("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": "error", "stop_sequence": None},
            "usage": {"output_tokens": 0},
        })
        yield self._format("message_stop", {"type": "message_stop"})
        self._message_ended = True
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_anthropic_sse_emitter.py -v`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/services/anthropic_sse_emitter.py tests/services/test_anthropic_sse_emitter.py
git commit -m "feat(anthropic-compat): SSE state machine with text + tool_use blocks"
```

---

## Task 6: anthropic_translator — response side (Ollama → Anthropic)

**Files:**
- Modify: `core/services/anthropic_translator.py`
- Modify: `tests/services/test_anthropic_translator.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/services/test_anthropic_translator.py`:

```python
def test_drive_emitter_with_text_only_chunks():
    """Translator drives an emitter from Ollama-format streamed chunks."""
    from core.services.anthropic_sse_emitter import AnthropicSSEEmitter
    chunks = [
        {"message": {"role": "assistant", "content": "Hej"}, "done": False},
        {"message": {"role": "assistant", "content": " Bjørn"}, "done": False},
        {"message": {"role": "assistant", "content": ""}, "done": True, "done_reason": "stop"},
    ]
    emitter = AnthropicSSEEmitter(message_id="m", model="jarvis")
    events = list(at.drive_emitter_from_ollama_chunks(emitter, iter(chunks)))
    text = "".join(events)
    assert "text_delta" in text
    assert "Hej" in text
    assert " Bjørn" in text
    assert "stop_reason" in text
    assert "end_turn" in text


def test_drive_emitter_with_tool_calls_chunks():
    from core.services.anthropic_sse_emitter import AnthropicSSEEmitter
    chunks = [
        {"message": {"role": "assistant", "content": "Listing..."}, "done": False},
        {"message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "toolu_x",
                "function": {"name": "Bash", "arguments": {"command": "ls"}},
            }],
        }, "done": False},
        {"message": {"content": ""}, "done": True, "done_reason": "stop"},
    ]
    emitter = AnthropicSSEEmitter(message_id="m", model="jarvis")
    events = list(at.drive_emitter_from_ollama_chunks(emitter, iter(chunks)))
    text = "".join(events)
    assert "Listing..." in text
    assert "tool_use" in text
    assert "Bash" in text
    assert "input_json_delta" in text
    assert '"command"' in text
    assert "stop_reason" in text
    assert "tool_use" in text  # final stop_reason


def test_build_non_streaming_response_text_only():
    final = at.build_non_streaming_response(
        message_id="msg_x", model="jarvis",
        text="Hej Bjørn",
        tool_calls=[],
    )
    assert final["id"] == "msg_x"
    assert final["type"] == "message"
    assert final["role"] == "assistant"
    assert final["model"] == "jarvis"
    assert len(final["content"]) == 1
    assert final["content"][0] == {"type": "text", "text": "Hej Bjørn"}
    assert final["stop_reason"] == "end_turn"


def test_build_non_streaming_response_with_tool_use():
    final = at.build_non_streaming_response(
        message_id="msg_x", model="jarvis",
        text="Looking",
        tool_calls=[{
            "id": "toolu_1",
            "function": {"name": "Bash", "arguments": {"command": "ls"}},
        }],
    )
    assert len(final["content"]) == 2
    assert final["content"][0] == {"type": "text", "text": "Looking"}
    assert final["content"][1] == {
        "type": "tool_use",
        "id": "toolu_1",
        "name": "Bash",
        "input": {"command": "ls"},
    }
    assert final["stop_reason"] == "tool_use"
```

Run: `pytest tests/services/test_anthropic_translator.py -v`. Expected: FAIL on new tests.

- [ ] **Step 2: Append response-side functions to anthropic_translator.py**

Append to `core/services/anthropic_translator.py`:

```python
import json as _json_mod
from typing import Iterator, Iterable


def drive_emitter_from_ollama_chunks(emitter, chunks: Iterable[dict]) -> Iterator[str]:
    """Drive an AnthropicSSEEmitter from a stream of Ollama chat chunks.

    Each chunk has shape:
      {"message": {"role": "assistant", "content": "...", "tool_calls": [...]}, "done": bool, ...}

    Yields SSE-formatted strings. Calls begin_message once, then translates
    each delta into text_delta or tool_use_start + input_json_delta. Ends
    with end_message(stop_reason).
    """
    yield from emitter.begin_message()
    has_tool_call = False
    seen_tool_call_ids: set[str] = set()

    try:
        for chunk in chunks:
            msg = chunk.get("message") or {}
            content = str(msg.get("content") or "")
            if content:
                yield from emitter.text_delta(content)

            tool_calls = msg.get("tool_calls") or []
            for tc in tool_calls:
                tc_id = str(tc.get("id") or "")
                if not tc_id or tc_id in seen_tool_call_ids:
                    continue
                seen_tool_call_ids.add(tc_id)
                fn = tc.get("function") or {}
                name = str(fn.get("name") or "")
                args = fn.get("arguments")
                yield from emitter.tool_use_start(tool_call_id=tc_id, name=name)
                # Ollama gives tool args as a dict; emit as one input_json_delta
                if isinstance(args, dict):
                    yield from emitter.tool_use_input_delta(_json_mod.dumps(args, ensure_ascii=False))
                elif isinstance(args, str):
                    yield from emitter.tool_use_input_delta(args)
                has_tool_call = True

            if chunk.get("done"):
                break
    except Exception as exc:
        yield from emitter.error(str(exc))
        return

    stop_reason = "tool_use" if has_tool_call else "end_turn"
    yield from emitter.end_message(stop_reason=stop_reason)


def build_non_streaming_response(
    *,
    message_id: str,
    model: str,
    text: str,
    tool_calls: list[dict],
) -> dict:
    """Build the final Anthropic Messages response (non-streaming)."""
    content: list[dict] = []
    if text:
        content.append({"type": "text", "text": text})
    for tc in tool_calls:
        fn = tc.get("function") or {}
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args = _json_mod.loads(args)
            except Exception:
                args = {}
        content.append({
            "type": "tool_use",
            "id": str(tc.get("id") or ""),
            "name": str(fn.get("name") or ""),
            "input": args or {},
        })
    stop_reason = "tool_use" if tool_calls else "end_turn"
    return {
        "id": message_id,
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_anthropic_translator.py -v`. Expected: PASS (all).

- [ ] **Step 4: Commit**

```bash
git add core/services/anthropic_translator.py tests/services/test_anthropic_translator.py
git commit -m "feat(anthropic-compat): translator response side (Ollama chunks → Anthropic SSE)"
```

---

## Task 7: anthropic_compat endpoint (non-streaming first)

**Files:**
- Create: `apps/api/jarvis_api/routes/anthropic_compat.py`
- Test: `tests/api/test_anthropic_messages.py`

- [ ] **Step 1: Write failing tests for non-streaming path**

Create `tests/api/test_anthropic_messages.py`:

```python
import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def isolated_keys(tmp_path, monkeypatch):
    from apps.api.jarvis_api.middleware import anthropic_auth as ah
    keys_path = tmp_path / "keys.json"
    keys_path.write_text(json.dumps({
        "keys": {"jvs-test-key": {"user": "bjorn", "workspace": "default"}}
    }))
    monkeypatch.setattr(ah, "_KEYS_PATH", keys_path)
    monkeypatch.setattr(ah, "_REPO_KEYS_PATH", keys_path)
    ah.invalidate_cache()


@pytest.fixture
def app_with_router(isolated_keys, monkeypatch):
    # Mock backend Ollama call so test doesn't need a live server.
    def fake_ollama_chat_non_stream(payload):
        return {
            "message": {
                "role": "assistant",
                "content": "Hej Bjørn 🤍",
                "tool_calls": [],
            },
            "done": True,
            "done_reason": "stop",
        }
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.anthropic_compat._ollama_chat_non_stream",
        fake_ollama_chat_non_stream,
    )
    from apps.api.jarvis_api.routes.anthropic_compat import router
    app = FastAPI()
    app.include_router(router)
    return app


def test_models_endpoint(app_with_router):
    with TestClient(app_with_router) as c:
        r = c.get("/anthropic/v1/models")
        assert r.status_code == 200
        data = r.json()
        ids = [m["id"] for m in data["data"]]
        assert "jarvis" in ids


def test_messages_missing_api_key_returns_401(app_with_router):
    with TestClient(app_with_router) as c:
        r = c.post("/anthropic/v1/messages", json={
            "model": "jarvis",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "hej"}],
        })
        assert r.status_code == 401
        body = r.json()
        assert body["type"] == "error"
        assert body["error"]["type"] == "authentication_error"


def test_messages_invalid_api_key_returns_401(app_with_router):
    with TestClient(app_with_router) as c:
        r = c.post("/anthropic/v1/messages",
            headers={"x-api-key": "wrong-key"},
            json={"model": "jarvis", "max_tokens": 100, "messages": [{"role": "user", "content": "hej"}]},
        )
        assert r.status_code == 401


def test_messages_non_streaming_returns_anthropic_format(app_with_router):
    with TestClient(app_with_router) as c:
        r = c.post("/anthropic/v1/messages",
            headers={"x-api-key": "jvs-test-key"},
            json={
                "model": "jarvis",
                "max_tokens": 100,
                "messages": [{"role": "user", "content": "hej"}],
                "stream": False,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "message"
        assert body["role"] == "assistant"
        assert body["model"] == "jarvis"
        assert body["content"][0]["type"] == "text"
        assert "Hej Bjørn" in body["content"][0]["text"]
        assert body["stop_reason"] == "end_turn"
```

Run: `pytest tests/api/test_anthropic_messages.py -v`. Expected: FAIL.

- [ ] **Step 2: Implement endpoint (non-streaming + models list)**

Create `apps/api/jarvis_api/routes/anthropic_compat.py`:

```python
"""Anthropic Messages API compatible endpoint.

Exposes Jarvis as a model so Claude Desktop / Claude Code can connect
via ANTHROPIC_BASE_URL=http://<host>/anthropic. Routes per-user via
x-api-key. Mode 2: identity-injected, Claude Desktop's tools passed
through to the Ollama backend.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Iterator, Optional
from uuid import uuid4

import requests
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from apps.api.jarvis_api.middleware.anthropic_auth import (
    resolve_api_key,
    short_key_for_log,
)
from core.runtime.provider_router import resolve_provider_router_target
from core.runtime.settings import RuntimeSettings
from core.services.anthropic_identity import build_identity_prefix
from core.services.anthropic_sse_emitter import AnthropicSSEEmitter
from core.services.anthropic_translator import (
    build_non_streaming_response,
    drive_emitter_from_ollama_chunks,
    translate_request_to_ollama,
)

logger = logging.getLogger("uvicorn.error")
router = APIRouter()

_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_WORKSPACES_ROOT = Path(os.getenv("JARVIS_WORKSPACES_DIR")
                        or (Path.home() / ".jarvis-v2" / "workspaces"))


def _error_response(*, status: int, type_: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"type": "error", "error": {"type": type_, "message": message}},
    )


def _resolve_workspace_dir(workspace_name: str) -> Path:
    return _WORKSPACES_ROOT / workspace_name


def _resolve_backend_model(requested: Optional[str]) -> str:
    """Pick the Ollama model to use. 'jarvis' or empty → visible-lane default."""
    settings = RuntimeSettings()
    requested = (requested or "").strip()
    if not requested or requested.lower() == "jarvis":
        target = resolve_provider_router_target(lane="visible")
        return str(target.get("model") or "")
    # Allow explicit override (e.g. "claude-3-5-sonnet" → only works if user has it set up; for now passthrough)
    return requested


def _ollama_chat_non_stream(payload: dict) -> dict:
    """Call Ollama /api/chat with stream=False; return the single response dict."""
    body = dict(payload)
    body["stream"] = False
    r = requests.post(
        f"{_OLLAMA_BASE_URL}/api/chat",
        json=body,
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def _ollama_chat_stream(payload: dict) -> Iterator[dict]:
    """Call Ollama /api/chat with stream=True; yield chunks."""
    body = dict(payload)
    body["stream"] = True
    with requests.post(
        f"{_OLLAMA_BASE_URL}/api/chat",
        json=body,
        stream=True,
        timeout=120,
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception as exc:
                logger.warning("anthropic_compat: bad ollama chunk: %s", exc)


@router.get("/anthropic/v1/models")
async def list_models() -> JSONResponse:
    return JSONResponse(content={
        "data": [{
            "id": "jarvis",
            "type": "model",
            "display_name": "Jarvis",
            "created_at": "2026-05-06T00:00:00Z",
        }],
        "has_more": False,
        "first_id": "jarvis",
        "last_id": "jarvis",
    })


@router.post("/anthropic/v1/messages", response_model=None)
async def messages(request: Request) -> JSONResponse | StreamingResponse:
    settings = RuntimeSettings()
    if not settings.anthropic_compat_enabled:
        return _error_response(
            status=503, type_="api_error",
            message="Anthropic-compat endpoint is disabled.",
        )

    api_key = request.headers.get("x-api-key", "")
    user_info = resolve_api_key(
        api_key,
        dev_mode_open=settings.anthropic_compat_dev_mode_open,
    )
    if user_info is None:
        logger.info("anthropic_compat: invalid key=%s", short_key_for_log(api_key))
        return _error_response(
            status=401, type_="authentication_error",
            message="Invalid API key. See state/anthropic_api_keys.json.",
        )

    user = user_info.get("user", "")
    workspace = user_info.get("workspace", "default")
    workspace_dir = _resolve_workspace_dir(workspace)
    logger.info(
        "anthropic_compat: request user=%s workspace=%s key=%s",
        user, workspace, short_key_for_log(api_key),
    )

    try:
        body = await request.json()
    except Exception:
        return _error_response(
            status=400, type_="invalid_request_error",
            message="Body must be valid JSON.",
        )

    if not body.get("messages"):
        return _error_response(
            status=400, type_="invalid_request_error",
            message="`messages` is required and cannot be empty.",
        )

    backend_model = _resolve_backend_model(body.get("model"))
    if not backend_model:
        return _error_response(
            status=500, type_="api_error",
            message="No backend model configured.",
        )

    identity_prefix = build_identity_prefix(workspace_dir)
    ollama_payload = translate_request_to_ollama(
        anthropic_body=body,
        identity_prefix=identity_prefix,
        backend_model=backend_model,
    )

    message_id = f"msg_{uuid4().hex[:24]}"
    requested_model_label = (body.get("model") or "jarvis").strip() or "jarvis"

    if bool(body.get("stream", False)):
        return StreamingResponse(
            _stream_response(
                payload=ollama_payload,
                message_id=message_id,
                model=requested_model_label,
            ),
            media_type="text/event-stream",
        )

    # Non-streaming
    try:
        response = _ollama_chat_non_stream(ollama_payload)
    except Exception as exc:
        logger.exception("anthropic_compat: ollama call failed")
        return _error_response(
            status=502, type_="api_error",
            message=f"Backend call failed: {exc}",
        )

    msg = response.get("message") or {}
    text = str(msg.get("content") or "")
    tool_calls = msg.get("tool_calls") or []
    return JSONResponse(content=build_non_streaming_response(
        message_id=message_id,
        model=requested_model_label,
        text=text,
        tool_calls=tool_calls,
    ))


def _stream_response(*, payload: dict, message_id: str, model: str) -> Iterator[str]:
    """Drive the AnthropicSSEEmitter from Ollama stream chunks."""
    emitter = AnthropicSSEEmitter(message_id=message_id, model=model)
    try:
        chunks = _ollama_chat_stream(payload)
        yield from drive_emitter_from_ollama_chunks(emitter, chunks)
    except Exception as exc:
        logger.exception("anthropic_compat: stream failed")
        yield from emitter.error(str(exc))
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/api/test_anthropic_messages.py -v`. Expected: PASS for non-streaming + models tests.

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/routes/anthropic_compat.py tests/api/test_anthropic_messages.py
git commit -m "feat(anthropic-compat): /v1/messages non-streaming + /v1/models endpoints"
```

---

## Task 8: Streaming endpoint test + verification

**Files:**
- Modify: `tests/api/test_anthropic_messages.py`

- [ ] **Step 1: Add streaming integration test**

Append to `tests/api/test_anthropic_messages.py`:

```python
def test_messages_streaming_emits_anthropic_sse(monkeypatch, isolated_keys):
    """End-to-end: streaming endpoint emits the full Anthropic event sequence."""
    fake_chunks = [
        {"message": {"role": "assistant", "content": "Hej "}, "done": False},
        {"message": {"role": "assistant", "content": "Bjørn"}, "done": False},
        {"message": {"content": ""}, "done": True, "done_reason": "stop"},
    ]
    def fake_stream(payload):
        for c in fake_chunks:
            yield c
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.anthropic_compat._ollama_chat_stream",
        fake_stream,
    )

    from apps.api.jarvis_api.routes.anthropic_compat import router
    app = FastAPI()
    app.include_router(router)

    with TestClient(app) as c:
        r = c.post("/anthropic/v1/messages",
            headers={"x-api-key": "jvs-test-key"},
            json={
                "model": "jarvis",
                "max_tokens": 100,
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        )
        assert r.status_code == 200
        body = r.text
        # All required events present in correct order
        assert body.index("event: message_start") < body.index("event: content_block_start")
        assert body.index("event: content_block_start") < body.index("event: content_block_delta")
        assert body.index("event: content_block_delta") < body.index("event: content_block_stop")
        assert body.index("event: content_block_stop") < body.index("event: message_delta")
        assert body.index("event: message_delta") < body.index("event: message_stop")
        # Text content present in deltas
        assert "Hej " in body
        assert "Bjørn" in body
        # end_turn for text-only response
        assert "end_turn" in body
```

Run: `pytest tests/api/test_anthropic_messages.py -v`. Expected: PASS.

- [ ] **Step 2: Commit**

```bash
git add tests/api/test_anthropic_messages.py
git commit -m "test(anthropic-compat): streaming endpoint integration test"
```

---

## Task 9: Wire endpoint into app.py

**Files:**
- Modify: `apps/api/jarvis_api/app.py`

- [ ] **Step 1: Import + register router**

In `apps/api/jarvis_api/app.py`, near other route imports add:

```python
from apps.api.jarvis_api.routes.anthropic_compat import router as anthropic_compat_router
```

Near the other `app.include_router(...)` calls add:

```python
    app.include_router(anthropic_compat_router)
```

- [ ] **Step 2: Verify smoke test still passes**

Run: `conda run -n ai python scripts/smoke_test_startup.py`. Expected: exit 0.

- [ ] **Step 3: Run full anthropic test suite**

Run: `conda run -n ai pytest tests/services/test_anthropic_*.py tests/api/test_anthropic_*.py -v`. Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/app.py
git commit -m "feat(anthropic-compat): mount endpoint in main app"
```

---

## Task 10: Generate Bjørn's API key + manual Claude Code validation

**Files:**
- Modify: `state/anthropic_api_keys.json` (add Bjørn's key)

- [ ] **Step 1: Generate a key**

Run:

```bash
echo "jvs-bjorn-$(openssl rand -hex 12)"
```

Output something like: `jvs-bjorn-EXAMPLE-REPLACE-WITH-REAL-KEY`. Save it (you'll need it for Claude Code config).

- [ ] **Step 2: Add to registry**

Edit `state/anthropic_api_keys.json` and replace the empty `keys: {}` with:

```json
{
  "_doc": "Anthropic-compat API key registry.",
  "keys": {
    "jvs-bjorn-EXAMPLE-REPLACE-WITH-REAL-KEY": {"user": "bjorn", "workspace": "default"}
  }
}
```

(Substitute the actual key generated in step 1.)

- [ ] **Step 3: Restart services**

```bash
sudo systemctl restart jarvis-api
sleep 3
journalctl -u jarvis-api --since "20 seconds ago" --no-pager | grep -iE "anthropic|error" | tail -10
```

- [ ] **Step 4: Manual smoke via curl**

```bash
KEY="jvs-bjorn-EXAMPLE-REPLACE-WITH-REAL-KEY"  # actual key
curl -s http://localhost/anthropic/v1/models | python3 -m json.tool

curl -s -X POST http://localhost/anthropic/v1/messages \
  -H "x-api-key: $KEY" \
  -H "content-type: application/json" \
  -d '{
    "model": "jarvis",
    "max_tokens": 200,
    "messages": [{"role": "user", "content": "Sig hej til Bjørn på dansk"}]
  }' | python3 -m json.tool
```

Expected: 200 response with Anthropic-format message containing Danish greeting from Jarvis.

- [ ] **Step 5: Connect Claude Code**

In Claude Code settings (or via env):

```bash
export ANTHROPIC_BASE_URL=http://localhost/anthropic
export ANTHROPIC_AUTH_TOKEN="jvs-bjorn-EXAMPLE-REPLACE-WITH-REAL-KEY"
claude  # or claude-code
```

Test:
1. Ask Claude Code: "Read /etc/hostname"
2. Verify: Claude Code requests approval for `Read` tool, executes locally, sends result back
3. Verify: Jarvis responds with Danish, contextually aware (knows Bjørn from USER.md)

Manual validation criteria:
- Tool approval UI appears in Claude Code (means tool_use block was emitted)
- Tool result is fed back and Jarvis responds (multi-turn round-trip works)
- Response feels Jarvis-flavoured (Danish, warm tone)

- [ ] **Step 6: Generate Mikkel's key (when ready)**

Same as step 1 but `jvs-mikkel-...`. Add to registry under `{"user": "mikkel", "workspace": "mikkel"}`. Restart, share key with Mikkel.

- [ ] **Step 7: Commit registry changes**

```bash
git add -f state/anthropic_api_keys.json
git commit -m "feat(anthropic-compat): seed bjorn API key in registry"
```

(Or skip the commit if you'd rather keep keys out of git — they'll persist in `~/.jarvis-v2/state/`.)

---

## Self-Review

Spec coverage check:

- ✅ `POST /anthropic/v1/messages` — Tasks 7+8
- ✅ `GET /anthropic/v1/models` — Task 7
- ✅ x-api-key auth + user routing — Task 2
- ✅ Identity prefix from workspace files — Task 3
- ✅ Tool array passthrough (Anthropic→Ollama format) — Task 4
- ✅ tool_result handling on multi-turn — Task 4 (`_translate_message` user role)
- ✅ Anthropic SSE state machine — Task 5
- ✅ Backend response → Anthropic SSE translation — Task 6
- ✅ Settings flags (`anthropic_compat_enabled`, dev mode) — Task 1
- ✅ Anthropic error envelope — Task 7 (`_error_response`)
- ✅ Wire into app — Task 9
- ✅ Manual Claude Code validation — Task 10
- ✅ Multi-user isolation — Tasks 2 + 7 (workspace_dir resolution per user)

Placeholder scan: no TBD/TODO; all code blocks complete.

Type consistency:
- `AnthropicSSEEmitter` method names consistent across Tasks 5, 6, 7
- `translate_request_to_ollama` signature consistent across Tasks 4, 7
- `build_non_streaming_response` signature consistent across Tasks 6, 7
- `resolve_api_key` signature consistent across Tasks 2, 7

Notes:
- Mode 3 explicitly out of scope — no tasks for `recall_memories` etc. injection
- Token counting deferred (output_tokens=0 in usage, same as OpenAI-compat)
- Vision/image content blocks return passthrough but aren't tested; Mode 2 ignores them in `_translate_message`
- `_resolve_backend_model` defaults to visible lane; explicit Anthropic models via name passthrough (works only if user configures the appropriate provider — not part of this plan)
