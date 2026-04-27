"""Activity-driven SkyOffice movement — daemons walk to Jarvis to report.

Watches the eventbus for events whose kind contains a known daemon name.
When matched, the corresponding resident leaves their desk, walks to a
spot near Jarvis's office, "reports" for ~4 seconds, then walks back.

Why throttle: many daemons fire every few seconds. We can't have them
shuttle to Jarvis on every event — they'd never sit at their desk.
Cooldown is 5 minutes per daemon by default.

Why substring match: the event kinds in this project don't follow a
single naming convention. Some are ``development_narrative.generated``,
others are ``runtime.<daemon>_completed``. A simple substring scan
catches both without needing to enumerate every kind.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


_REPORT_COOLDOWN = timedelta(minutes=5)
_REPORT_DWELL_S = 4.0  # how long they stand by Jarvis "reporting"

# Spot to walk to (just south of Jarvis's chair so they're visibly near him)
_REPORT_SPOT_X = 928
_REPORT_SPOT_Y = 256

_last_report: dict[str, datetime] = {}
_in_flight: set[str] = set()
_lock = threading.Lock()
_subscribed = False


def _resident_for_event_kind(kind: str) -> Any | None:
    """Return the Resident whose daemon name appears in the event kind, or None."""
    try:
        from core.services.skyoffice_residency import list_residents
        residents = list_residents()
    except Exception:
        return None
    lower_kind = (kind or "").lower()
    # Prefer longest-match to avoid 'meta_reflection' matching just 'reflection'
    candidates = sorted(
        [r for r in residents if r.kind_label == "daemon"],
        key=lambda r: -len(r.agent_id.split(":", 1)[-1]),
    )
    for r in candidates:
        bare = r.agent_id.split(":", 1)[-1]
        if bare in lower_kind:
            return r
    return None


def _can_report(agent_id: str) -> bool:
    with _lock:
        if agent_id in _in_flight:
            return False
        last = _last_report.get(agent_id)
        if last and (datetime.now(UTC) - last) < _REPORT_COOLDOWN:
            return False
        return True


def _trigger_report_walk(resident: Any) -> None:
    """Walk the daemon to Jarvis, wait, walk back."""
    from core.services.skyoffice_bridge import upsert_agent
    from core.services.skyoffice_walk import walk_to, get_known_position
    from core.services.skyoffice_residency import (
        _sit_anim_for_resident, _sprite_for_role, _last_applied,
    )
    from core.services.skyoffice_council_viz import is_in_meeting

    if is_in_meeting(resident.agent_id):
        return  # don't pull them out of a council meeting

    sprite = _sprite_for_role(resident.role)
    final_anim_at_jarvis = f"{sprite}_idle_up"   # facing Jarvis (he's north)
    final_anim_at_desk = _sit_anim_for_resident(resident)

    with _lock:
        if resident.agent_id in _in_flight:
            return
        _in_flight.add(resident.agent_id)
        _last_report[resident.agent_id] = datetime.now(UTC)

    def _on_arrive_at_jarvis() -> None:
        # Mark working briefly while reporting; then walk back.
        try:
            upsert_agent(agent_id=resident.agent_id, status="working")
        except Exception:
            pass

        def _go_home() -> None:
            try:
                if get_known_position(resident.agent_id) is None:
                    upsert_agent(
                        agent_id=resident.agent_id,
                        x=resident.desk_x, y=resident.desk_y,
                        anim=final_anim_at_desk,
                    )
                else:
                    walk_to(
                        agent_id=resident.agent_id,
                        target_x=resident.desk_x, target_y=resident.desk_y,
                        final_anim=final_anim_at_desk, sprite=sprite,
                        on_arrive=_on_settled_at_desk,
                    )
            except Exception as exc:
                logger.debug("activity: go_home %s failed: %s", resident.agent_id, exc)

        threading.Timer(_REPORT_DWELL_S, _go_home).start()

    def _on_settled_at_desk() -> None:
        with _lock:
            _in_flight.discard(resident.agent_id)
        try:
            upsert_agent(agent_id=resident.agent_id, status="idle")
            _last_applied.pop(resident.agent_id, None)  # let residency re-settle
        except Exception:
            pass

    if get_known_position(resident.agent_id) is None:
        # Can't walk — just snap-bounce in case bridge is fresh.
        with _lock:
            _in_flight.discard(resident.agent_id)
        return

    walk_to(
        agent_id=resident.agent_id,
        target_x=_REPORT_SPOT_X, target_y=_REPORT_SPOT_Y,
        final_anim=final_anim_at_jarvis, sprite=sprite,
        on_arrive=_on_arrive_at_jarvis,
    )
    logger.info(
        "skyoffice_activity: %s walking to report at Jarvis", resident.agent_id,
    )


# ── Eventbus poll loop (mirrors council_viz pattern) ────────────────────────


def _handle_event(item: dict[str, Any]) -> None:
    kind = str(item.get("kind") or "")
    if not kind:
        return
    resident = _resident_for_event_kind(kind)
    if resident is None:
        return
    if not _can_report(resident.agent_id):
        return
    _trigger_report_walk(resident)


def _poll_loop() -> None:
    try:
        from core.eventbus.bus import event_bus
    except Exception as exc:
        logger.warning("skyoffice_activity: eventbus import failed: %s", exc)
        return
    queue = event_bus.subscribe()
    logger.info("skyoffice_activity: subscribed to eventbus")
    while True:
        item = queue.get()
        if item is None:
            return
        try:
            _handle_event(item)
        except Exception as exc:
            logger.debug("skyoffice_activity: handler error: %s", exc)


def _db_watermark_loop() -> None:
    """Mirror the DB-poll fallback used by council_viz so events from other
    processes also drive activity walks."""
    try:
        from core.eventbus.bus import event_bus
    except Exception:
        return
    last_id = 0
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
        new_items = [r for r in reversed(recent) if int(r.get("id") or 0) > last_id]
        for item in new_items:
            try:
                _handle_event(item)
            except Exception:
                pass
            last_id = max(last_id, int(item.get("id") or 0))
        time.sleep(2.0)


def start_activity() -> None:
    global _subscribed
    if _subscribed:
        return
    _subscribed = True
    threading.Thread(target=_poll_loop, name="skyoffice-activity",
                     daemon=True).start()
    threading.Thread(target=_db_watermark_loop, name="skyoffice-activity-db",
                     daemon=True).start()
    logger.info("skyoffice_activity: started (cooldown=%dm, dwell=%.1fs)",
                int(_REPORT_COOLDOWN.total_seconds() // 60), _REPORT_DWELL_S)
