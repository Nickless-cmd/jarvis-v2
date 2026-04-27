"""Agent relay — direct A→B messaging between sub-agents.

Existing pattern: agents send messages "agent->jarvis" only. Jarvis is
hub, no peer-to-peer. For multi-agent collaboration this is a bottleneck
— a researcher can't directly hand findings to a planner without
Jarvis as middleman.

This module adds a thin relay: one agent can send a message addressed
to another agent (by agent_id or by role-in-current-council). Receiver
gets it as a "agent->agent" direction message in their thread, picks
it up on next execution.

Stays advisory — does NOT auto-execute the receiver. The receiver must
be re-invoked via execute_agent_task or be in a council loop.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def relay_message(
    *,
    from_agent_id: str,
    to_agent_id: str,
    content: str,
    kind: str = "peer-message",
) -> dict[str, Any]:
    """Send a message from agent A to agent B."""
    if not from_agent_id or not to_agent_id or not content:
        return {"status": "error", "error": "from_agent_id, to_agent_id, content required"}
    try:
        from core.runtime.db import (
            create_agent_message,
            get_agent_registry_entry,
        )
    except Exception as exc:
        return {"status": "error", "error": f"db import failed: {exc}"}

    receiver = get_agent_registry_entry(to_agent_id)
    if receiver is None:
        return {"status": "error", "error": f"receiver agent not found: {to_agent_id}"}

    msg_id = f"agent-msg-{uuid4().hex}"
    thread_id = f"agent-thread-{to_agent_id}"
    create_agent_message(
        message_id=msg_id,
        thread_id=thread_id,
        agent_id=to_agent_id,
        direction="agent->agent",
        role="user",  # so receiver treats it as a prompt input
        kind=kind,
        content=f"[Message from {from_agent_id}]\n{content[:2000]}",
    )

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "agent.relay_message",
            {
                "from": from_agent_id,
                "to": to_agent_id,
                "kind": kind,
                "content_excerpt": content[:200],
            },
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "message_id": msg_id,
        "to_agent_id": to_agent_id,
        "to_role": str(receiver.get("role", "")),
        "delivered": True,
    }


def relay_to_role(
    *,
    from_agent_id: str,
    council_id: str,
    role: str,
    content: str,
    kind: str = "peer-message",
) -> dict[str, Any]:
    """Send to whoever in this council holds the given role."""
    try:
        from core.runtime.db import list_council_members
    except Exception as exc:
        return {"status": "error", "error": f"db import failed: {exc}"}
    members = list_council_members(council_id) or []
    target = next((m for m in members if str(m.get("role")) == role), None)
    if target is None:
        return {"status": "error", "error": f"no member with role={role} in council {council_id}"}
    return relay_message(
        from_agent_id=from_agent_id,
        to_agent_id=str(target.get("agent_id", "")),
        content=content,
        kind=kind,
    )


def _exec_relay_message(args: dict[str, Any]) -> dict[str, Any]:
    return relay_message(
        from_agent_id=str(args.get("from_agent_id") or ""),
        to_agent_id=str(args.get("to_agent_id") or ""),
        content=str(args.get("content") or ""),
        kind=str(args.get("kind") or "peer-message"),
    )


def _exec_relay_to_role(args: dict[str, Any]) -> dict[str, Any]:
    return relay_to_role(
        from_agent_id=str(args.get("from_agent_id") or ""),
        council_id=str(args.get("council_id") or ""),
        role=str(args.get("role") or ""),
        content=str(args.get("content") or ""),
        kind=str(args.get("kind") or "peer-message"),
    )


AGENT_RELAY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "agent_relay_message",
            "description": (
                "Send a peer-to-peer message between two sub-agents. "
                "Receiver picks it up on next execution. Does NOT auto-trigger "
                "the receiver — they must already be running or scheduled."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "from_agent_id": {"type": "string"},
                    "to_agent_id": {"type": "string"},
                    "content": {"type": "string"},
                    "kind": {"type": "string"},
                },
                "required": ["from_agent_id", "to_agent_id", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "agent_relay_to_role",
            "description": (
                "Send a message to whoever in a council currently holds a "
                "given role. Useful when you don't know the agent_id directly."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "from_agent_id": {"type": "string"},
                    "council_id": {"type": "string"},
                    "role": {"type": "string"},
                    "content": {"type": "string"},
                    "kind": {"type": "string"},
                },
                "required": ["from_agent_id", "council_id", "role", "content"],
            },
        },
    },
]
