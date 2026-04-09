# Jarvis MCP Server + OpenAI-Compatible Proxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose Jarvis as an MCP server (Streamable HTTP) and OpenAI-compatible proxy so Claude Code and other editors can access Jarvis' memory, identity, cognitive state, and chat capabilities.

**Architecture:** FastMCP server mounted at `/mcp` in existing FastAPI app with 9 tools (8 passive + 1 active) and 3 resources. Separate OpenAI-compatible router at `/v1/chat/completions` wrapping requests with Jarvis identity/memory. Both share DB, eventbus, config.

**Tech Stack:** Python 3.11+, FastAPI, FastMCP, existing Jarvis core modules (chat_sessions, visible_model, visible_runs, eventbus, identity, memory)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `apps/api/jarvis_api/mcp_server.py` | **NEW** — FastMCP server: 9 tools, 3 resources, eventbus integration |
| `apps/api/jarvis_api/routes/openai_compat.py` | **NEW** — `/v1/chat/completions` endpoint with model routing, streaming, session management |
| `apps/api/jarvis_api/app.py` | **MODIFY** — Mount MCP server + OpenAI compat router |

---

### Task 1: Install FastMCP dependency

**Files:**
- Modify: Project dependency configuration

- [ ] **Step 1: Install fastmcp in the conda ai environment**

```bash
conda activate ai && pip install fastmcp
```

- [ ] **Step 2: Verify import works**

```bash
conda activate ai && python -c "from fastmcp import FastMCP; print('fastmcp OK')"
```

Expected: `fastmcp OK`

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "chore: add fastmcp dependency"
```

---

### Task 2: MCP Server — Passive Tools (memory, sessions, identity)

**Files:**
- Create: `apps/api/jarvis_api/mcp_server.py`
- Test: `tests/test_mcp_server.py`

- [ ] **Step 1: Write failing tests for passive MCP tools**

Create `tests/test_mcp_server.py`:

```python
"""Tests for Jarvis MCP server tools."""
from __future__ import annotations

import importlib


def _get_mcp_server():
    mod = importlib.import_module("apps.api.jarvis_api.mcp_server")
    return importlib.reload(mod)


def test_mcp_server_module_imports():
    """MCP server module imports without error."""
    mod = _get_mcp_server()
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "create_mcp_app")


def test_jarvis_memory_read_tool_exists():
    mod = _get_mcp_server()
    tool_names = [t.name for t in mod.mcp._tool_manager.list_tools()]
    assert "jarvis_memory_read" in tool_names


def test_jarvis_memory_write_tool_exists():
    mod = _get_mcp_server()
    tool_names = [t.name for t in mod.mcp._tool_manager.list_tools()]
    assert "jarvis_memory_write" in tool_names


def test_jarvis_chat_sessions_tool_exists():
    mod = _get_mcp_server()
    tool_names = [t.name for t in mod.mcp._tool_manager.list_tools()]
    assert "jarvis_chat_sessions" in tool_names


def test_jarvis_chat_history_tool_exists():
    mod = _get_mcp_server()
    tool_names = [t.name for t in mod.mcp._tool_manager.list_tools()]
    assert "jarvis_chat_history" in tool_names


def test_jarvis_identity_tool_exists():
    mod = _get_mcp_server()
    tool_names = [t.name for t in mod.mcp._tool_manager.list_tools()]
    assert "jarvis_identity" in tool_names


def test_jarvis_cognitive_state_tool_exists():
    mod = _get_mcp_server()
    tool_names = [t.name for t in mod.mcp._tool_manager.list_tools()]
    assert "jarvis_cognitive_state" in tool_names


def test_jarvis_retained_memories_tool_exists():
    mod = _get_mcp_server()
    tool_names = [t.name for t in mod.mcp._tool_manager.list_tools()]
    assert "jarvis_retained_memories" in tool_names


def test_jarvis_events_tool_exists():
    mod = _get_mcp_server()
    tool_names = [t.name for t in mod.mcp._tool_manager.list_tools()]
    assert "jarvis_events" in tool_names


def test_jarvis_chat_tool_exists():
    mod = _get_mcp_server()
    tool_names = [t.name for t in mod.mcp._tool_manager.list_tools()]
    assert "jarvis_chat" in tool_names


def test_all_nine_tools_registered():
    mod = _get_mcp_server()
    tool_names = [t.name for t in mod.mcp._tool_manager.list_tools()]
    expected = {
        "jarvis_memory_read",
        "jarvis_memory_write",
        "jarvis_chat_sessions",
        "jarvis_chat_history",
        "jarvis_identity",
        "jarvis_cognitive_state",
        "jarvis_retained_memories",
        "jarvis_events",
        "jarvis_chat",
    }
    assert expected.issubset(set(tool_names)), f"Missing: {expected - set(tool_names)}"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && python -m pytest tests/test_mcp_server.py -v
```

Expected: ModuleNotFoundError or AttributeError — module doesn't exist yet.

- [ ] **Step 3: Implement the MCP server with passive tools**

Create `apps/api/jarvis_api/mcp_server.py`:

```python
"""Jarvis MCP server — exposes memory, identity, state, and chat via Streamable HTTP."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastmcp import FastMCP

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.db import (
    get_protected_inner_voice,
    list_recent_protected_inner_voices,
    get_private_self_model,
    get_private_retained_memory_record,
    recent_private_retained_memory_records,
)
from apps.api.jarvis_api.services.chat_sessions import (
    list_chat_sessions,
    get_chat_session,
    create_chat_session,
)

logger = logging.getLogger("uvicorn.error")

mcp = FastMCP("Jarvis V2")


# ---------------------------------------------------------------------------
# Passive tools — Read/write memory and state
# ---------------------------------------------------------------------------

@mcp.tool
def jarvis_memory_read() -> str:
    """Read Jarvis' cross-session memory (MEMORY.md)."""
    event_bus.publish("mcp.tool_invoked", {"tool": "jarvis_memory_read"})
    workspace = ensure_default_workspace()
    memory_path = workspace / "MEMORY.md"
    if not memory_path.exists():
        return ""
    content = memory_path.read_text(encoding="utf-8", errors="replace")
    event_bus.publish("mcp.tool_completed", {"tool": "jarvis_memory_read"})
    return content


@mcp.tool
def jarvis_memory_write(content: str) -> str:
    """Overwrite Jarvis' cross-session memory (MEMORY.md)."""
    event_bus.publish("mcp.tool_invoked", {"tool": "jarvis_memory_write"})
    workspace = ensure_default_workspace()
    memory_path = workspace / "MEMORY.md"
    memory_path.write_text(content, encoding="utf-8")
    event_bus.publish("mcp.tool_completed", {"tool": "jarvis_memory_write"})
    return f"MEMORY.md updated ({len(content)} chars)"


@mcp.tool
def jarvis_chat_sessions(limit: int = 20) -> str:
    """List Jarvis' chat sessions with metadata."""
    event_bus.publish("mcp.tool_invoked", {"tool": "jarvis_chat_sessions"})
    sessions = list_chat_sessions()[:limit]
    event_bus.publish("mcp.tool_completed", {"tool": "jarvis_chat_sessions"})
    return json.dumps(sessions, ensure_ascii=False, indent=2)


@mcp.tool
def jarvis_chat_history(session_id: str, limit: int = 50) -> str:
    """Get messages from a specific Jarvis chat session."""
    event_bus.publish("mcp.tool_invoked", {"tool": "jarvis_chat_history"})
    session = get_chat_session(session_id)
    if session is None:
        return json.dumps({"error": f"Session {session_id} not found"})
    messages = session.get("messages", [])
    if limit:
        messages = messages[-limit:]
    result = {
        "session_id": session.get("id"),
        "title": session.get("title"),
        "messages": messages,
    }
    event_bus.publish("mcp.tool_completed", {"tool": "jarvis_chat_history"})
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool
def jarvis_identity() -> str:
    """Read Jarvis' identity files (SOUL.md, IDENTITY.md, USER.md)."""
    event_bus.publish("mcp.tool_invoked", {"tool": "jarvis_identity"})
    workspace = ensure_default_workspace()
    result = {}
    for filename in ("SOUL.md", "IDENTITY.md", "USER.md"):
        path = workspace / filename
        if path.exists():
            result[filename] = path.read_text(encoding="utf-8", errors="replace")
        else:
            result[filename] = ""
    event_bus.publish("mcp.tool_completed", {"tool": "jarvis_identity"})
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool
def jarvis_cognitive_state() -> str:
    """Get Jarvis' current cognitive state: inner voice, self-model, retained memory."""
    event_bus.publish("mcp.tool_invoked", {"tool": "jarvis_cognitive_state"})
    inner_voice = get_protected_inner_voice()
    self_model = get_private_self_model()
    retained = get_private_retained_memory_record()
    result = {
        "inner_voice": _safe_dict(inner_voice),
        "self_model": _safe_dict(self_model),
        "retained_memory": _safe_dict(retained),
    }
    event_bus.publish("mcp.tool_completed", {"tool": "jarvis_cognitive_state"})
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool
def jarvis_retained_memories(limit: int = 10) -> str:
    """Get Jarvis' cross-session retained memory records."""
    event_bus.publish("mcp.tool_invoked", {"tool": "jarvis_retained_memories"})
    records = recent_private_retained_memory_records(limit=limit)
    event_bus.publish("mcp.tool_completed", {"tool": "jarvis_retained_memories"})
    return json.dumps([_safe_dict(r) for r in records], ensure_ascii=False, indent=2)


@mcp.tool
def jarvis_events(limit: int = 30, kind: str = "") -> str:
    """Get recent Jarvis eventbus events, optionally filtered by kind prefix."""
    event_bus.publish("mcp.tool_invoked", {"tool": "jarvis_events"})
    events = event_bus.recent(limit=limit)
    if kind:
        events = [e for e in events if str(e.get("kind", "")).startswith(kind)]
    event_bus.publish("mcp.tool_completed", {"tool": "jarvis_events"})
    return json.dumps(events, ensure_ascii=False, default=str, indent=2)


# ---------------------------------------------------------------------------
# Active tool — Chat through visible lane
# ---------------------------------------------------------------------------

@mcp.tool
def jarvis_chat(message: str, session_id: str = "") -> str:
    """Send a message to Jarvis through his visible run pipeline.

    He reflects, updates state, builds memory. Returns his response.
    If no session_id, uses or creates a default MCP session.
    """
    event_bus.publish("mcp.tool_invoked", {"tool": "jarvis_chat", "message": message[:200]})

    if not session_id:
        session_id = _get_or_create_mcp_session()

    # Run visible model synchronously (non-streaming) to get response
    from apps.api.jarvis_api.services.visible_model import execute_visible_model
    from core.runtime.provider_router import resolve_provider_router_target

    target = resolve_provider_router_target(lane="visible")
    provider = str(target.get("provider", ""))
    model = str(target.get("model", ""))

    result = execute_visible_model(
        message=message,
        provider=provider,
        model=model,
        session_id=session_id,
    )

    event_bus.publish("mcp.tool_completed", {
        "tool": "jarvis_chat",
        "tokens": result.input_tokens + result.output_tokens,
    })
    return result.text


# ---------------------------------------------------------------------------
# MCP Resources
# ---------------------------------------------------------------------------

@mcp.resource("jarvis://memory")
def resource_memory() -> str:
    """Jarvis' cross-session memory."""
    workspace = ensure_default_workspace()
    path = workspace / "MEMORY.md"
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


@mcp.resource("jarvis://identity")
def resource_identity() -> str:
    """Jarvis' combined identity files."""
    workspace = ensure_default_workspace()
    parts = []
    for filename in ("SOUL.md", "IDENTITY.md", "USER.md"):
        path = workspace / filename
        if path.exists():
            parts.append(f"# {filename}\n\n{path.read_text(encoding='utf-8', errors='replace')}")
    return "\n\n---\n\n".join(parts)


@mcp.resource("jarvis://chat/{session_id}")
def resource_chat_session(session_id: str) -> str:
    """A specific Jarvis chat session with all messages."""
    session = get_chat_session(session_id)
    if session is None:
        return json.dumps({"error": f"Session {session_id} not found"})
    return json.dumps(session, ensure_ascii=False, default=str, indent=2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MCP_SESSION_ID: str | None = None


def _get_or_create_mcp_session() -> str:
    """Return or create a persistent MCP chat session."""
    global _MCP_SESSION_ID
    if _MCP_SESSION_ID:
        session = get_chat_session(_MCP_SESSION_ID)
        if session is not None:
            return _MCP_SESSION_ID

    from datetime import datetime, UTC
    title = f"MCP — {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"
    session = create_chat_session(title=title)
    _MCP_SESSION_ID = str(session.get("id") or session.get("session_id", ""))
    return _MCP_SESSION_ID


def _safe_dict(obj: dict | None) -> dict:
    """Convert a DB record to a JSON-safe dict."""
    if obj is None:
        return {}
    return {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
            for k, v in obj.items()}


def create_mcp_app():
    """Create the ASGI app for mounting in FastAPI."""
    return mcp.http_app(path="/")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && python -m pytest tests/test_mcp_server.py -v
```

Expected: All 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/mcp_server.py tests/test_mcp_server.py
git commit -m "feat: add Jarvis MCP server with 9 tools and 3 resources"
```

---

### Task 3: OpenAI-Compatible Proxy — `/v1/chat/completions`

**Files:**
- Create: `apps/api/jarvis_api/routes/openai_compat.py`
- Test: `tests/test_openai_compat.py`

- [ ] **Step 1: Write failing tests for the proxy endpoint**

Create `tests/test_openai_compat.py`:

```python
"""Tests for OpenAI-compatible proxy endpoint."""
from __future__ import annotations

import importlib


def _get_module():
    mod = importlib.import_module("apps.api.jarvis_api.routes.openai_compat")
    return importlib.reload(mod)


def test_module_imports():
    mod = _get_module()
    assert hasattr(mod, "router")


def test_resolve_model_provider_ollama_cloud():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("minimax-m2.7:cloud")
    assert provider == "ollama"
    assert model == "minimax-m2.7:cloud"


def test_resolve_model_provider_glm():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("glm-5.1:cloud")
    assert provider == "ollama"
    assert model == "glm-5.1:cloud"


def test_resolve_model_provider_qwen():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("qwen3.5:397b-cloud")
    assert provider == "ollama"
    assert model == "qwen3.5:397b-cloud"


def test_resolve_model_provider_gemma():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("gemma4:32b-cloud")
    assert provider == "ollama"
    assert model == "gemma4:32b-cloud"


def test_resolve_model_provider_openai():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("gpt-4o")
    assert provider == "openai"
    assert model == "gpt-4o"


def test_resolve_model_provider_copilot():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("copilot/gpt-4o")
    assert provider == "github-copilot"
    assert model == "gpt-4o"


def test_resolve_model_provider_jarvis_default():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("jarvis")
    # Should return visible lane defaults — provider/model depend on config
    assert isinstance(provider, str)
    assert isinstance(model, str)


def test_resolve_model_provider_empty_default():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("")
    assert isinstance(provider, str)
    assert isinstance(model, str)


def test_build_openai_response_format():
    mod = _get_module()
    resp = mod._build_completion_response(
        run_id="test-123",
        model="minimax-m2.7:cloud",
        content="Hello",
        input_tokens=10,
        output_tokens=5,
    )
    assert resp["object"] == "chat.completion"
    assert resp["model"] == "minimax-m2.7:cloud"
    assert resp["choices"][0]["message"]["content"] == "Hello"
    assert resp["choices"][0]["finish_reason"] == "stop"
    assert resp["usage"]["prompt_tokens"] == 10
    assert resp["usage"]["completion_tokens"] == 5
    assert resp["usage"]["total_tokens"] == 15


def test_build_streaming_chunk_format():
    mod = _get_module()
    chunk = mod._build_stream_chunk(
        run_id="test-123",
        model="minimax-m2.7:cloud",
        delta_content="Hej",
    )
    assert chunk["object"] == "chat.completion.chunk"
    assert chunk["choices"][0]["delta"]["content"] == "Hej"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && python -m pytest tests/test_openai_compat.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement the OpenAI-compatible proxy**

Create `apps/api/jarvis_api/routes/openai_compat.py`:

```python
"""OpenAI-compatible proxy: /v1/chat/completions wrapping Jarvis visible lane."""
from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from typing import Iterator
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from apps.api.jarvis_api.services.chat_sessions import (
    create_chat_session,
    get_chat_session,
    append_chat_message,
)
from apps.api.jarvis_api.services.visible_model import (
    stream_visible_model,
    execute_visible_model,
    VisibleModelDelta,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
)
from core.eventbus.bus import event_bus
from core.runtime.provider_router import resolve_provider_router_target

logger = logging.getLogger("uvicorn.error")
router = APIRouter()


@router.post("/v1/chat/completions")
async def chat_completions(request: Request) -> JSONResponse | StreamingResponse:
    """OpenAI-compatible chat completion endpoint wrapping Jarvis' visible lane."""
    body = await request.json()
    model_param = str(body.get("model", "")).strip()
    messages = body.get("messages", [])
    stream = bool(body.get("stream", False))

    # Extract user message (last user role message)
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = str(msg.get("content", ""))
            break

    if not user_message:
        return JSONResponse(
            status_code=400,
            content={"error": {"message": "No user message found in messages array", "type": "invalid_request_error"}},
        )

    # Resolve provider and model
    provider, model = _resolve_model_provider(model_param)

    # Session handling
    session_id = request.headers.get("X-Jarvis-Session", "").strip()
    if not session_id:
        session_id = _get_or_create_proxy_session()

    # Persist user message
    append_chat_message(session_id=session_id, role="user", content=user_message)

    event_bus.publish("proxy.request_received", {
        "provider": provider,
        "model": model,
        "stream": stream,
        "session_id": session_id,
    })

    run_id = f"jarvis-proxy-{uuid4().hex[:12]}"

    if stream:
        return StreamingResponse(
            _stream_response(
                run_id=run_id,
                message=user_message,
                provider=provider,
                model=model,
                session_id=session_id,
            ),
            media_type="text/event-stream",
        )

    # Non-streaming
    result = execute_visible_model(
        message=user_message,
        provider=provider,
        model=model,
        session_id=session_id,
    )
    append_chat_message(session_id=session_id, role="assistant", content=result.text)
    return JSONResponse(content=_build_completion_response(
        run_id=run_id,
        model=model,
        content=result.text,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    ))


def _stream_response(
    *,
    run_id: str,
    message: str,
    provider: str,
    model: str,
    session_id: str,
) -> Iterator[str]:
    """Yield OpenAI-format SSE chunks from Jarvis' visible model stream."""
    full_text = ""
    for event in stream_visible_model(
        message=message,
        provider=provider,
        model=model,
        session_id=session_id,
    ):
        if isinstance(event, VisibleModelDelta):
            full_text += event.delta
            chunk = _build_stream_chunk(
                run_id=run_id,
                model=model,
                delta_content=event.delta,
            )
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        elif isinstance(event, VisibleModelStreamDone):
            # Persist assistant response
            if full_text.strip():
                append_chat_message(session_id=session_id, role="assistant", content=full_text)
            yield "data: [DONE]\n\n"
            return

    # Fallback if stream ends without done event
    if full_text.strip():
        append_chat_message(session_id=session_id, role="assistant", content=full_text)
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Model routing
# ---------------------------------------------------------------------------

def _resolve_model_provider(model_param: str) -> tuple[str, str]:
    """Map a model parameter to (provider, model) tuple.

    Rules:
    - "jarvis" or empty → visible lane default
    - Contains ":cloud" or known Ollama tag → ollama
    - Starts with "gpt-" or "o1-" or "o3-" → openai
    - Starts with "copilot/" → github-copilot (strip prefix)
    - Otherwise → visible lane default provider with given model
    """
    model = model_param.strip()

    if not model or model == "jarvis":
        target = resolve_provider_router_target(lane="visible")
        return str(target.get("provider", "")), str(target.get("model", ""))

    if model.startswith("copilot/"):
        return "github-copilot", model.removeprefix("copilot/")

    if model.startswith(("gpt-", "o1-", "o3-")):
        return "openai", model

    if ":cloud" in model or ":" in model:
        return "ollama", model

    # Unknown model — use default provider
    target = resolve_provider_router_target(lane="visible")
    return str(target.get("provider", "")), model


# ---------------------------------------------------------------------------
# Response formatting
# ---------------------------------------------------------------------------

def _build_completion_response(
    *,
    run_id: str,
    model: str,
    content: str,
    input_tokens: int,
    output_tokens: int,
) -> dict:
    """Build a standard OpenAI chat.completion response."""
    return {
        "id": run_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    }


def _build_stream_chunk(
    *,
    run_id: str,
    model: str,
    delta_content: str,
) -> dict:
    """Build a standard OpenAI chat.completion.chunk for streaming."""
    return {
        "id": run_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": delta_content},
                "finish_reason": None,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

_PROXY_SESSION_ID: str | None = None


def _get_or_create_proxy_session() -> str:
    """Return or create a persistent proxy chat session."""
    global _PROXY_SESSION_ID
    if _PROXY_SESSION_ID:
        session = get_chat_session(_PROXY_SESSION_ID)
        if session is not None:
            return _PROXY_SESSION_ID

    title = f"Claude Code — {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"
    session = create_chat_session(title=title)
    _PROXY_SESSION_ID = str(session.get("id") or session.get("session_id", ""))
    return _PROXY_SESSION_ID
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && python -m pytest tests/test_openai_compat.py -v
```

Expected: All 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/openai_compat.py tests/test_openai_compat.py
git commit -m "feat: add OpenAI-compatible proxy at /v1/chat/completions"
```

---

### Task 4: Mount MCP Server + Proxy Router in FastAPI App

**Files:**
- Modify: `apps/api/jarvis_api/app.py`
- Test: `tests/test_app_mounts.py`

- [ ] **Step 1: Write failing test for app mounts**

Create `tests/test_app_mounts.py`:

```python
"""Tests for app mounts — MCP server and OpenAI compat router."""
from __future__ import annotations

import importlib


def test_app_has_openai_compat_route():
    """The /v1/chat/completions route must be registered."""
    mod = importlib.import_module("apps.api.jarvis_api.app")
    mod = importlib.reload(mod)
    routes = [r.path for r in mod.app.routes if hasattr(r, "path")]
    assert "/v1/chat/completions" in routes


def test_app_has_mcp_mount():
    """The /mcp mount must exist."""
    mod = importlib.import_module("apps.api.jarvis_api.app")
    mod = importlib.reload(mod)
    mount_paths = [r.path for r in mod.app.routes if hasattr(r, "path")]
    assert "/mcp" in mount_paths
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && python -m pytest tests/test_app_mounts.py -v
```

Expected: FAIL — routes not yet mounted.

- [ ] **Step 3: Mount MCP server and proxy router in app.py**

Modify `apps/api/jarvis_api/app.py` — add these imports at the top (after existing imports):

```python
from apps.api.jarvis_api.routes.openai_compat import router as openai_compat_router
from apps.api.jarvis_api.mcp_server import create_mcp_app
```

Then inside `create_app()`, after the existing `app.include_router(...)` lines, add:

```python
    # OpenAI-compatible proxy
    app.include_router(openai_compat_router)

    # MCP server (Streamable HTTP)
    mcp_app = create_mcp_app()
    app.mount("/mcp", mcp_app)
```

The lifespan from FastMCP needs to be integrated. If FastMCP requires its lifespan, update the FastAPI creation:

```python
    mcp_app = create_mcp_app()
    app = FastAPI(title="Jarvis V2 API", lifespan=mcp_app.lifespan)
```

Move the `mcp_app = create_mcp_app()` line BEFORE `app = FastAPI(...)` to pass the lifespan.

Full modified `create_app()`:

```python
def create_app() -> FastAPI:
    ensure_runtime_dirs()
    init_db()
    ensure_default_workspace()

    mcp_app = create_mcp_app()
    app = FastAPI(title="Jarvis V2 API", lifespan=mcp_app.lifespan)

    app.include_router(chat_router)
    app.include_router(health_router)
    app.include_router(mc_router)
    app.include_router(live_router)
    app.include_router(system_health_router, prefix="/mc")
    app.include_router(openai_compat_router)
    app.mount("/mcp", mcp_app)

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("jarvis api startup begin")
        start_runtime_hook_runtime()
        start_heartbeat_scheduler()
        event_bus.publish("runtime.started", {"component": "api"})
        logger.info("jarvis api startup complete")

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("jarvis api shutdown begin")
        stop_heartbeat_scheduler()
        stop_runtime_hook_runtime()
        logger.info("jarvis api shutdown complete")

    return app
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && python -m pytest tests/test_app_mounts.py -v
```

Expected: Both tests PASS.

- [ ] **Step 5: Run full syntax check**

```bash
conda activate ai && python -m compileall apps/api
```

Expected: No syntax errors.

- [ ] **Step 6: Run existing tests to check for regressions**

```bash
conda activate ai && python -m pytest tests/ -x --timeout=30 2>&1 | tail -20
```

Expected: Existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add apps/api/jarvis_api/app.py tests/test_app_mounts.py
git commit -m "feat: mount MCP server at /mcp and OpenAI proxy at /v1"
```

---

### Task 5: Integration Smoke Test

**Files:**
- No new files — manual verification

- [ ] **Step 1: Start the API server**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && uvicorn apps.api.jarvis_api.app:app --host 127.0.0.1 --port 8010 &
sleep 3
```

- [ ] **Step 2: Test MCP endpoint responds**

```bash
curl -s http://127.0.0.1:8010/mcp/ | head -20
```

Expected: Some response from FastMCP (likely the MCP endpoint listing or protocol response).

- [ ] **Step 3: Test OpenAI proxy non-streaming**

```bash
curl -s http://127.0.0.1:8010/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"jarvis","messages":[{"role":"user","content":"Hej Jarvis, hvem er du?"}]}' \
  | python -m json.tool
```

Expected: OpenAI-format response with `choices[0].message.content` containing Jarvis' response with his identity.

- [ ] **Step 4: Test OpenAI proxy streaming**

```bash
curl -s -N http://127.0.0.1:8010/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"jarvis","messages":[{"role":"user","content":"Hvad er 2+2?"}],"stream":true}' \
  | head -10
```

Expected: SSE chunks in OpenAI format ending with `data: [DONE]`.

- [ ] **Step 5: Verify session was created**

```bash
curl -s http://127.0.0.1:8010/chat/sessions | python -m json.tool | head -20
```

Expected: A session titled "Claude Code — ..." appears in the list.

- [ ] **Step 6: Stop the test server**

```bash
kill %1 2>/dev/null
```

- [ ] **Step 7: Commit any fixes**

If any adjustments were needed during smoke testing, commit them:

```bash
git add -A && git commit -m "fix: adjustments from integration smoke test"
```
