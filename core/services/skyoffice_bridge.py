"""SkyOffice presence bridge — push Jarvis agent state to the virtual office.

SkyOffice (the virtual coworking app at ws://localhost:2567) exposes a small
HTTP bridge for external presence injection. This module is the Jarvis-side
client: when an agent activates, deactivates, or changes status, we POST
to the bridge so the agent's avatar appears, moves, or vanishes in the
virtual office.

Auth: shared token at runtime.json key 'skyoffice_bridge_token', mirrored
into the SkyOffice process via SKYOFFICE_BRIDGE_TOKEN env var.

Failure mode: if the bridge is unreachable (SkyOffice not running), all
calls return ``{"status": "skipped"}`` — Jarvis must continue without
presence. This keeps the virtual office strictly cosmetic.
"""
from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:2567"
_TIMEOUT = 2.0


def _bridge_token() -> str:
    try:
        from core.runtime.secrets import read_runtime_key
        return str(read_runtime_key("skyoffice_bridge_token") or "")
    except Exception:
        return ""


def _base_url() -> str:
    try:
        from core.runtime.secrets import read_runtime_key
        return str(read_runtime_key("skyoffice_base_url") or _DEFAULT_BASE_URL)
    except Exception:
        return _DEFAULT_BASE_URL


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    token = _bridge_token()
    if not token:
        return {"status": "skipped", "reason": "no bridge token configured"}
    url = f"{_base_url().rstrip('/')}{path}"
    try:
        r = requests.post(
            url, json=body,
            headers={"X-Bridge-Token": token, "Content-Type": "application/json"},
            timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:
        return {"status": "skipped", "reason": f"bridge unreachable: {exc}"}
    if r.status_code >= 400:
        return {"status": "error", "code": r.status_code, "body": r.text[:200]}
    try:
        return {"status": "ok", **r.json()}
    except Exception:
        return {"status": "ok"}


def upsert_agent(
    *,
    agent_id: str,
    name: str | None = None,
    role: str | None = None,
    status: str | None = None,
    x: int | None = None,
    y: int | None = None,
    anim: str | None = None,
    avatar_url: str | None = None,
) -> dict[str, Any]:
    """Create or update an agent's avatar in the virtual office.

    Always include agent_id (stable across calls — used as session key).
    Pass only the fields you want to update; omitted fields keep their
    previous value.
    """
    if not agent_id:
        return {"status": "error", "error": "agent_id required"}
    body: dict[str, Any] = {"agentId": agent_id}
    if name is not None:
        body["name"] = name
    if role is not None:
        body["role"] = role
    if status is not None:
        body["status"] = status
    if x is not None:
        body["x"] = x
    if y is not None:
        body["y"] = y
    if anim is not None:
        body["anim"] = anim
    if avatar_url is not None:
        body["avatarUrl"] = avatar_url
    return _post("/agents/upsert", body)


def remove_agent(agent_id: str) -> dict[str, Any]:
    if not agent_id:
        return {"status": "error", "error": "agent_id required"}
    return _post("/agents/remove", {"agentId": agent_id})


def list_agents() -> dict[str, Any]:
    token = _bridge_token()
    if not token:
        return {"status": "skipped", "agents": []}
    try:
        r = requests.get(
            f"{_base_url().rstrip('/')}/agents",
            headers={"X-Bridge-Token": token},
            timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:
        return {"status": "skipped", "reason": f"bridge unreachable: {exc}"}
    if r.status_code >= 400:
        return {"status": "error", "code": r.status_code}
    try:
        return {"status": "ok", **r.json()}
    except Exception:
        return {"status": "ok", "agents": []}


# ── Tools ──────────────────────────────────────────────────────────


def _exec_skyoffice_upsert_agent(args: dict[str, Any]) -> dict[str, Any]:
    return upsert_agent(
        agent_id=str(args.get("agent_id") or ""),
        name=args.get("name"),
        role=args.get("role"),
        status=args.get("status"),
        x=args.get("x"),
        y=args.get("y"),
        anim=args.get("anim"),
        avatar_url=args.get("avatar_url"),
    )


def _exec_skyoffice_remove_agent(args: dict[str, Any]) -> dict[str, Any]:
    return remove_agent(str(args.get("agent_id") or ""))


def _exec_skyoffice_list_agents(_args: dict[str, Any]) -> dict[str, Any]:
    return list_agents()


SKYOFFICE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "skyoffice_upsert_agent",
            "description": (
                "Create or update an agent's avatar in the SkyOffice virtual office. "
                "agent_id is the stable identifier (e.g. 'researcher-1'). Other fields "
                "are optional; only what you pass gets updated. status: idle|working|"
                "meeting|away. role: council|researcher|worker|observer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "status": {"type": "string"},
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "anim": {"type": "string"},
                    "avatar_url": {"type": "string"},
                },
                "required": ["agent_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skyoffice_remove_agent",
            "description": "Remove an agent's avatar from the SkyOffice virtual office.",
            "parameters": {
                "type": "object",
                "properties": {"agent_id": {"type": "string"}},
                "required": ["agent_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skyoffice_list_agents",
            "description": "List all agents currently visible in the SkyOffice virtual office.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
