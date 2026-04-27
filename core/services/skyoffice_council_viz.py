"""Council visualization — wire eventbus → SkyOffice presence.

When Jarvis fires a council session, the agents who participate should
appear as avatars sitting around the meeting-room table in the virtual
office. When the session concludes, they leave.

Wires three eventbus topics:
- council.autonomous_triggered → upsert one agent per member at table
- council.autonomous_concluded → remove all council agents
- council.agent_recruited → upsert the new arrival mid-session

Coordinates: the SkyOffice map is 1280x960px. The meeting room sits
central; we arrange members in a circle around (640, 480) at radius 80.

Agents IDs are namespaced ``agent:council:{role}`` so the same role
maps to the same avatar across sessions.

Failure mode: if the SkyOffice bridge is unreachable (token missing
or server down), every call returns 'skipped' and the subscriber
silently logs and moves on. The visual is purely cosmetic — Jarvis
never depends on it.
"""
from __future__ import annotations

import logging
import math
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Meeting room geometry (px). Map is 1280x960; the room is centered.
_MEETING_CENTER_X = 640
_MEETING_CENTER_Y = 480
_MEETING_RADIUS = 80

# Track which agent IDs we've placed so we can remove them on conclusion.
_active_council_agents: set[str] = set()
_lock = threading.Lock()
_subscribed = False


def _agent_id_for_role(role: str) -> str:
    role = (role or "").strip().lower().replace(" ", "_") or "member"
    return f"agent:council:{role}"


def _seat_position(index: int, total: int) -> tuple[int, int]:
    if total <= 0:
        return _MEETING_CENTER_X, _MEETING_CENTER_Y
    angle = (2 * math.pi * index) / max(total, 1)
    x = int(_MEETING_CENTER_X + _MEETING_RADIUS * math.cos(angle))
    y = int(_MEETING_CENTER_Y + _MEETING_RADIUS * math.sin(angle))
    return x, y


def _members_from_payload(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    members = payload.get("members") or payload.get("roles") or []
    if isinstance(members, list):
        return [str(m) for m in members if m]
    if isinstance(members, str):
        return [members]
    return []


def on_council_triggered(payload: dict[str, Any]) -> None:
    from core.services.skyoffice_bridge import upsert_agent

    members = _members_from_payload(payload)
    topic = str(payload.get("topic", "") or "")[:80]
    if not members:
        logger.debug("skyoffice_council_viz: no members in payload, skipping")
        return

    placed: list[str] = []
    with _lock:
        for idx, role in enumerate(members):
            x, y = _seat_position(idx, len(members))
            agent_id = _agent_id_for_role(role)
            display_name = f"{role.title()}"
            try:
                res = upsert_agent(
                    agent_id=agent_id,
                    name=display_name,
                    role="council",
                    status="meeting",
                    x=x, y=y,
                )
                if res.get("status") in {"ok", "skipped"}:
                    placed.append(agent_id)
                    _active_council_agents.add(agent_id)
            except Exception as exc:
                logger.warning("skyoffice_council_viz: upsert %s failed: %s", role, exc)
    if placed:
        logger.info(
            "skyoffice_council_viz: seated %d council agents (topic=%s)",
            len(placed), topic,
        )


def on_council_concluded(payload: dict[str, Any]) -> None:
    from core.services.skyoffice_bridge import remove_agent

    with _lock:
        ids = list(_active_council_agents)
        _active_council_agents.clear()
    for aid in ids:
        try:
            remove_agent(aid)
        except Exception as exc:
            logger.warning("skyoffice_council_viz: remove %s failed: %s", aid, exc)
    if ids:
        logger.info("skyoffice_council_viz: dismissed %d council agents", len(ids))


def on_agent_recruited(payload: dict[str, Any]) -> None:
    """Mid-session agent arrival."""
    from core.services.skyoffice_bridge import upsert_agent

    role = str((payload or {}).get("role", "")).strip()
    if not role:
        return
    agent_id = _agent_id_for_role(role)
    with _lock:
        index = len(_active_council_agents)
        total = max(index + 1, 6)  # rough — places new arrival on the perimeter
    x, y = _seat_position(index, total)
    try:
        res = upsert_agent(
            agent_id=agent_id, name=role.title(),
            role="council", status="meeting", x=x, y=y,
        )
        if res.get("status") in {"ok", "skipped"}:
            with _lock:
                _active_council_agents.add(agent_id)
    except Exception as exc:
        logger.warning("skyoffice_council_viz: recruit %s failed: %s", role, exc)


def subscribe_council_visualization() -> None:
    """Idempotent — subscribe to council eventbus topics for SkyOffice viz."""
    global _subscribed
    if _subscribed:
        return
    try:
        from core.eventbus.bus import event_bus
        event_bus.subscribe("council.autonomous_triggered", on_council_triggered)
        event_bus.subscribe("council.autonomous_concluded", on_council_concluded)
        event_bus.subscribe("council.agent_recruited", on_agent_recruited)
        _subscribed = True
        logger.info("skyoffice_council_viz: subscribed to 3 council topics")
    except Exception as exc:
        logger.warning("skyoffice_council_viz: subscribe failed: %s", exc)
