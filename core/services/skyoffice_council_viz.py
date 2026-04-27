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
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Big meeting room — long conference table at y=640 / y=740 with chairs at
# x=320, 384, 448, 512 (north side) and x=256, 320, 384, 448, 512 (south
# side). Up to 8 council members sit at real chair positions instead of
# being arranged in an abstract circle. _MEETING_SEATS is the ordered
# fallback list of (x, y, anim_suffix) — first members get north seats
# (face down toward table), later members get south seats (face up).
_MEETING_SEATS: list[tuple[int, int, str]] = [
    # North side (sit facing down toward the table)
    (320, 640, "sit_down"),
    (384, 640, "sit_down"),
    (448, 640, "sit_down"),
    (512, 640, "sit_down"),
    # South side (sit facing up toward the table)
    (320, 736, "sit_up"),
    (384, 736, "sit_up"),
    (448, 736, "sit_up"),
    (512, 704, "sit_up"),
]

# Track which agent IDs we've placed so we can remove them on conclusion.
_active_council_agents: set[str] = set()
_lock = threading.Lock()
_subscribed = False


def is_in_meeting(agent_id: str) -> bool:
    """Public — used by skyoffice_residency to skip repositioning agents
    that the council viz has moved to the meeting table."""
    with _lock:
        return agent_id in _active_council_agents


def _agent_id_for_role(role: str) -> str:
    role = (role or "").strip().lower().replace(" ", "_") or "member"
    # Prefer matching an existing resident by role for visual continuity.
    try:
        from core.services.skyoffice_residency import list_residents
        for r in list_residents():
            if r.role == role:
                return r.agent_id
    except Exception:
        pass
    return f"agent:council:{role}"


def _seat_at(index: int) -> tuple[int, int, str]:
    """Pick a seat for the i'th council member. Wraps around the table if
    more than 8 members; the wraparound ones simply share seats."""
    return _MEETING_SEATS[index % len(_MEETING_SEATS)]


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
    from core.services.skyoffice_walk import walk_to, get_known_position
    from core.services.skyoffice_residency import (
        get_resident, _sprite_for_role,
    )
    with _lock:
        for idx, role in enumerate(members):
            x, y, sit_suffix = _seat_at(idx)
            agent_id = _agent_id_for_role(role)
            display_name = f"{role.title()}"
            resident = get_resident(agent_id)
            effective_role = resident.role if resident else "council"
            sprite = _sprite_for_role(effective_role)
            anim = f"{sprite}_{sit_suffix}"
            try:
                # First mark them in-meeting (state propagates via residency)
                # and set name/role; the walker handles position+anim over time.
                upsert_agent(
                    agent_id=agent_id, name=display_name,
                    role=effective_role, status="meeting",
                )
                # If we know where they are, walk them; else snap.
                if get_known_position(agent_id) is None:
                    upsert_agent(
                        agent_id=agent_id, x=x, y=y, anim=anim,
                    )
                else:
                    walk_to(
                        agent_id=agent_id,
                        target_x=x, target_y=y,
                        final_anim=anim, sprite=sprite,
                    )
                placed.append(agent_id)
                _active_council_agents.add(agent_id)
            except Exception as exc:
                logger.warning("skyoffice_council_viz: walk-to-meeting %s failed: %s", role, exc)
    if placed:
        logger.info(
            "skyoffice_council_viz: walking %d council agents to big meeting room (topic=%s)",
            len(placed), topic,
        )


def on_council_concluded(payload: dict[str, Any]) -> None:
    from core.services.skyoffice_bridge import remove_agent, upsert_agent
    from core.services.skyoffice_residency import (
        get_resident, _sit_anim_for_resident, _sprite_for_role, _last_applied,
    )
    from core.services.skyoffice_walk import walk_to, get_known_position

    with _lock:
        ids = list(_active_council_agents)
        _active_council_agents.clear()
    restored = removed = 0
    for aid in ids:
        resident = get_resident(aid)
        try:
            if resident is not None:
                anim = _sit_anim_for_resident(resident)
                sprite = _sprite_for_role(resident.role)
                # Update status now; walker will animate them home.
                upsert_agent(
                    agent_id=resident.agent_id, name=resident.name,
                    role=resident.role, status="idle",
                )
                if get_known_position(aid) is None:
                    upsert_agent(
                        agent_id=resident.agent_id,
                        x=resident.desk_x, y=resident.desk_y, anim=anim,
                    )
                else:
                    walk_to(
                        agent_id=resident.agent_id,
                        target_x=resident.desk_x, target_y=resident.desk_y,
                        final_anim=anim, sprite=sprite,
                    )
                _last_applied.pop(aid, None)
                restored += 1
            else:
                remove_agent(aid)
                removed += 1
        except Exception as exc:
            logger.warning("skyoffice_council_viz: cleanup %s failed: %s", aid, exc)
    if ids:
        logger.info(
            "skyoffice_council_viz: meeting ended — walking %d residents back, removed %d ad-hoc",
            restored, removed,
        )


def on_agent_recruited(payload: dict[str, Any]) -> None:
    """Mid-session agent arrival."""
    from core.services.skyoffice_bridge import upsert_agent

    role = str((payload or {}).get("role", "")).strip()
    if not role:
        return
    agent_id = _agent_id_for_role(role)
    with _lock:
        index = len(_active_council_agents)
    x, y, sit_suffix = _seat_at(index)
    try:
        from core.services.skyoffice_residency import get_resident, _sprite_for_role
        resident = get_resident(agent_id)
        effective_role = resident.role if resident else "council"
        sprite = _sprite_for_role(effective_role)
    except Exception:
        effective_role = "council"
        sprite = "lucy"
    anim = f"{sprite}_{sit_suffix}"
    try:
        res = upsert_agent(
            agent_id=agent_id, name=role.title(),
            role=effective_role, status="meeting", x=x, y=y, anim=anim,
        )
        if res.get("status") in {"ok", "skipped"}:
            with _lock:
                _active_council_agents.add(agent_id)
    except Exception as exc:
        logger.warning("skyoffice_council_viz: recruit %s failed: %s", role, exc)


_HANDLERS: dict[str, Any] = {
    "council.autonomous_triggered": on_council_triggered,
    "council.autonomous_concluded": on_council_concluded,
    "council.agent_recruited": on_agent_recruited,
}


def _poll_loop() -> None:
    """Daemon thread: pull events off the bus queue and dispatch to handlers."""
    try:
        from core.eventbus.bus import event_bus
    except Exception as exc:
        logger.warning("skyoffice_council_viz: eventbus import failed: %s", exc)
        return
    queue = event_bus.subscribe()
    logger.info("skyoffice_council_viz: subscribed to eventbus, polling for council.*")
    while True:
        item = queue.get()
        if item is None:
            return
        try:
            kind = str(item.get("kind") or "")
            handler = _HANDLERS.get(kind)
            if handler is None:
                continue
            payload = item.get("payload") or {}
            handler(payload)
        except Exception as exc:
            logger.warning("skyoffice_council_viz: handler error: %s", exc)


def _db_watermark_loop() -> None:
    """Backup: poll the events DB so council events published from OTHER
    processes (jarvis-api, ad-hoc scripts) also drive the visualization.
    Watermarks by event id so each event fires at most once."""
    import time as _time
    try:
        from core.eventbus.bus import event_bus
    except Exception:
        return
    last_id = 0
    # Seed at current max so we don't replay history on every restart.
    try:
        recent = event_bus.recent(limit=1) or []
        if recent:
            last_id = int(recent[0].get("id") or 0)
    except Exception:
        pass
    while True:
        try:
            recent = event_bus.recent(limit=50) or []
        except Exception:
            recent = []
        # recent is newest-first; iterate oldest-first to preserve order
        new_items = [r for r in reversed(recent) if int(r.get("id") or 0) > last_id]
        for item in new_items:
            try:
                kind = str(item.get("kind") or "")
                handler = _HANDLERS.get(kind)
                if handler:
                    handler(item.get("payload") or {})
            except Exception as exc:
                logger.debug("skyoffice_council_viz: db-poll handler err: %s", exc)
            last_id = max(last_id, int(item.get("id") or 0))
        _time.sleep(2.0)


def subscribe_council_visualization() -> None:
    """Idempotent — start a daemon thread that pulls council events from the bus
    and pushes them to SkyOffice as agent presence updates."""
    global _subscribed
    if _subscribed:
        return
    _subscribed = True
    threading.Thread(
        target=_poll_loop, name="skyoffice-council-viz", daemon=True,
    ).start()
    threading.Thread(
        target=_db_watermark_loop, name="skyoffice-council-db-poll", daemon=True,
    ).start()
