"""Jarvis MCP server — exposes memory, identity, state, and chat via Streamable HTTP."""
from __future__ import annotations

import json
import logging

from fastmcp import FastMCP

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.db import (
    get_protected_inner_voice,
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
    event_bus.publish("tool.mcp_invoked", {"tool": "jarvis_memory_read"})
    workspace = ensure_default_workspace()
    memory_path = workspace / "MEMORY.md"
    content = ""
    if memory_path.exists():
        content = memory_path.read_text(encoding="utf-8", errors="replace")
    event_bus.publish("tool.mcp_completed", {"tool": "jarvis_memory_read"})
    return content


@mcp.tool
def jarvis_memory_write(content: str) -> str:
    """Overwrite Jarvis' cross-session memory (MEMORY.md)."""
    event_bus.publish("tool.mcp_invoked", {"tool": "jarvis_memory_write"})
    workspace = ensure_default_workspace()
    memory_path = workspace / "MEMORY.md"
    memory_path.write_text(content, encoding="utf-8")
    event_bus.publish("tool.mcp_completed", {"tool": "jarvis_memory_write"})
    return f"MEMORY.md updated ({len(content)} chars)"


@mcp.tool
def jarvis_chat_sessions(limit: int = 20) -> str:
    """List Jarvis' chat sessions with metadata."""
    event_bus.publish("tool.mcp_invoked", {"tool": "jarvis_chat_sessions"})
    sessions = list_chat_sessions()[:limit]
    event_bus.publish("tool.mcp_completed", {"tool": "jarvis_chat_sessions"})
    return json.dumps(sessions, ensure_ascii=False, indent=2)


@mcp.tool
def jarvis_chat_history(session_id: str, limit: int = 50) -> str:
    """Get messages from a specific Jarvis chat session."""
    event_bus.publish("tool.mcp_invoked", {"tool": "jarvis_chat_history"})
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
    event_bus.publish("tool.mcp_completed", {"tool": "jarvis_chat_history"})
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool
def jarvis_identity() -> str:
    """Read Jarvis' identity files (SOUL.md, IDENTITY.md, USER.md)."""
    event_bus.publish("tool.mcp_invoked", {"tool": "jarvis_identity"})
    workspace = ensure_default_workspace()
    result = {}
    for filename in ("SOUL.md", "IDENTITY.md", "USER.md"):
        path = workspace / filename
        if path.exists():
            result[filename] = path.read_text(encoding="utf-8", errors="replace")
        else:
            result[filename] = ""
    event_bus.publish("tool.mcp_completed", {"tool": "jarvis_identity"})
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool
def jarvis_cognitive_state() -> str:
    """Get Jarvis' current cognitive state: inner voice, self-model, retained memory."""
    event_bus.publish("tool.mcp_invoked", {"tool": "jarvis_cognitive_state"})
    inner_voice = get_protected_inner_voice()
    self_model = get_private_self_model()
    retained = get_private_retained_memory_record()
    result = {
        "inner_voice": _safe_dict(inner_voice),
        "self_model": _safe_dict(self_model),
        "retained_memory": _safe_dict(retained),
    }
    event_bus.publish("tool.mcp_completed", {"tool": "jarvis_cognitive_state"})
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool
def jarvis_retained_memories(limit: int = 10) -> str:
    """Get Jarvis' cross-session retained memory records."""
    event_bus.publish("tool.mcp_invoked", {"tool": "jarvis_retained_memories"})
    records = recent_private_retained_memory_records(limit=limit)
    event_bus.publish("tool.mcp_completed", {"tool": "jarvis_retained_memories"})
    return json.dumps([_safe_dict(r) for r in records], ensure_ascii=False, indent=2)


@mcp.tool
def jarvis_events(limit: int = 30, kind: str = "") -> str:
    """Get recent Jarvis eventbus events, optionally filtered by kind prefix."""
    event_bus.publish("tool.mcp_invoked", {"tool": "jarvis_events"})
    events = event_bus.recent(limit=limit)
    if kind:
        events = [e for e in events if str(e.get("kind", "")).startswith(kind)]
    event_bus.publish("tool.mcp_completed", {"tool": "jarvis_events"})
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
    event_bus.publish(
        "tool.mcp_invoked", {"tool": "jarvis_chat", "message": message[:200]}
    )

    if not session_id:
        session_id = _get_or_create_mcp_session()

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

    event_bus.publish(
        "tool.mcp_completed",
        {
            "tool": "jarvis_chat",
            "tokens": result.input_tokens + result.output_tokens,
        },
    )
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
            parts.append(
                f"# {filename}\n\n"
                f"{path.read_text(encoding='utf-8', errors='replace')}"
            )
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

    from datetime import UTC, datetime

    title = f"MCP — {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"
    session = create_chat_session(title=title)
    _MCP_SESSION_ID = str(session.get("id") or session.get("session_id", ""))
    return _MCP_SESSION_ID


def _safe_dict(obj: dict | None) -> dict:
    """Convert a DB record to a JSON-safe dict."""
    if obj is None:
        return {}
    return {
        k: (
            str(v)
            if not isinstance(v, (str, int, float, bool, type(None)))
            else v
        )
        for k, v in obj.items()
    }


def create_mcp_app():
    """Create the ASGI app for mounting in FastAPI."""
    return mcp.http_app(path="/")
