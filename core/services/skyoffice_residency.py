"""SkyOffice residency — Jarvis + his daemons live in the office full-time.

The office should never feel empty. Jarvis has a command station at the
top-right; daemons sit at desks in the workspace rows. Status reflects
what each one is doing right now (idle / working / meeting). Council
sessions don't replace residents — they relocate them to the table and
back when concluded.

Two cooperating mechanisms:

1. **Residency tick** (this module, every 30s): upserts every resident
   at their home desk with current status. If SkyOffice is reachable
   the office stays populated; if it's down all calls no-op.

2. **Council viz** (skyoffice_council_viz, eventbus-driven): on
   council.autonomous_triggered moves participants to the meeting
   circle (if they're residents) or spawns them temporarily (if they
   aren't). On conclude, residents return to their desks.

The two modules cooperate via the shared registry in this file.
"""
from __future__ import annotations

import logging
import random
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# Map: 1280x960 pixels (40x30 tiles × 32px). Meeting room is the central
# rectangle around (640, 480). Workspace rows on the left, command
# station upper-right, daemon row middle-left.

class Resident:
    __slots__ = ("agent_id", "name", "role", "desk_x", "desk_y", "kind_label")

    def __init__(
        self,
        *,
        agent_id: str,
        name: str,
        role: str,
        desk_x: int,
        desk_y: int,
        kind_label: str = "daemon",
    ) -> None:
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.desk_x = desk_x
        self.desk_y = desk_y
        self.kind_label = kind_label  # 'self' | 'daemon' | 'agent'


# Permanent residents. Coordinates correspond to ACTUAL chair positions
# read from client/public/assets/map/map.json — agents sit on real
# furniture, not floating in the void. The default Player spawn is
# (705, 500), so anything in that ballpark is interior.
#
# Layout:
#   Jarvis at the solo manager's chair (960, 192)
#   Two council chairs around the central 2x2 table at y≈305 (used during
#   council viz, not as residents' homes)
#   Seven daemons across the workstation row at y=416 (x=224..576)
#   Eighth daemon at the right-bench station (1184, 480)

_RESIDENTS: list[Resident] = [
    # Jarvis at the solo manager chair upper-middle
    Resident(
        agent_id="agent:jarvis", name="Jarvis", role="self",
        desk_x=960, desk_y=192, kind_label="self",
    ),
    # Right-side workstation rows — chairs facing computers at y=576 and y=736
    # Top workstation row
    Resident(agent_id="daemon:thought_stream", name="Thought Stream",
             role="researcher", desk_x=992, desk_y=576),
    Resident(agent_id="daemon:meta_reflection", name="Meta Reflection",
             role="researcher", desk_x=1088, desk_y=576),
    Resident(agent_id="daemon:reflection_cycle", name="Reflection Cycle",
             role="researcher", desk_x=1184, desk_y=576),
    # Middle pair (chairs at y=480)
    Resident(agent_id="daemon:user_model", name="User Model",
             role="researcher", desk_x=1088, desk_y=480),
    Resident(agent_id="daemon:code_aesthetic", name="Code Aesthetic",
             role="worker", desk_x=1184, desk_y=480),
    # Bottom workstation row at y=736
    Resident(agent_id="daemon:development_narrative", name="Dev Narrative",
             role="worker", desk_x=992, desk_y=736),
    Resident(agent_id="daemon:current_pull", name="Current Pull",
             role="worker", desk_x=1088, desk_y=736),
    Resident(agent_id="daemon:goal_signal_synthesizer", name="Goal Synthesizer",
             role="worker", desk_x=1184, desk_y=736),
]


def list_residents() -> list[Resident]:
    return list(_RESIDENTS)


def get_resident(agent_id: str) -> Resident | None:
    for r in _RESIDENTS:
        if r.agent_id == agent_id:
            return r
    return None


# ── Status inference ────────────────────────────────────────────────────────

def _recent_daemon_activity_window() -> dict[str, datetime]:
    """Return {daemon_name: last_seen_ts} for the last 5 minutes.

    Sources: looks at `daemon_log` state-store entries if present; falls
    back to event-bus 'daemon.*' kinds. Returns empty dict on any failure.
    """
    out: dict[str, datetime] = {}
    cutoff = datetime.now(UTC) - timedelta(minutes=5)
    try:
        from core.eventbus.bus import event_bus
        recent = event_bus.recent(limit=200) or []
    except Exception:
        return out
    for ev in recent:
        kind = str(ev.get("kind") or "")
        if not kind.startswith("daemon."):
            continue
        try:
            ts = datetime.fromisoformat(str(ev.get("created_at") or ""))
        except ValueError:
            continue
        if ts < cutoff:
            continue
        payload = ev.get("payload") or {}
        name = str(payload.get("daemon_name") or payload.get("name") or "")
        if not name:
            continue
        prev = out.get(name)
        if prev is None or ts > prev:
            out[name] = ts
    return out


def _resident_status(resident: Resident, activity: dict[str, datetime]) -> str:
    if resident.kind_label == "self":
        # Jarvis: 'thinking' if there's been any visible-run lately, else 'idle'
        try:
            from core.eventbus.bus import event_bus
            recent = event_bus.recent(limit=30) or []
            cutoff = datetime.now(UTC) - timedelta(minutes=2)
            for ev in recent:
                kind = str(ev.get("kind") or "")
                if kind.startswith("runtime.visible_run") or kind.startswith("channel.chat"):
                    try:
                        ts = datetime.fromisoformat(str(ev.get("created_at") or ""))
                        if ts > cutoff:
                            return "working"
                    except ValueError:
                        continue
        except Exception:
            pass
        return "idle"
    # daemon: 'working' if it produced an event in the last 5 minutes
    bare_name = resident.agent_id.split(":", 1)[-1]
    if bare_name in activity:
        return "working"
    return "idle"


# ── Residency tick ──────────────────────────────────────────────────────────


_residency_started = False
_TICK_INTERVAL_SECONDS = 30.0


def _residency_tick() -> None:
    """One pass: upsert every resident at their desk with current status."""
    from core.services.skyoffice_bridge import upsert_agent
    activity = _recent_daemon_activity_window()
    placed = 0
    skipped = 0
    for r in _RESIDENTS:
        # If this resident is currently in the meeting (council viz moved them)
        # we leave their position alone — only refresh status.
        from core.services.skyoffice_council_viz import is_in_meeting
        in_meeting = is_in_meeting(r.agent_id)
        status = "meeting" if in_meeting else _resident_status(r, activity)
        try:
            kwargs: dict[str, Any] = dict(
                agent_id=r.agent_id, name=r.name, role=r.role, status=status,
            )
            if not in_meeting:
                # Idle residents wander a little around their desk so the
                # office feels alive. Working residents stay put — focused.
                if status == "idle":
                    kwargs["x"] = r.desk_x + random.randint(-40, 40)
                    kwargs["y"] = r.desk_y + random.randint(-30, 30)
                    # Pick a facing direction roughly aligned with the move.
                    kwargs["anim"] = random.choice([
                        "adam_idle_left", "adam_idle_right",
                        "adam_idle_up", "adam_idle_down",
                    ])
                else:
                    kwargs["x"] = r.desk_x
                    kwargs["y"] = r.desk_y
            res = upsert_agent(**kwargs)
            if res.get("status") == "ok":
                placed += 1
            else:
                skipped += 1
        except Exception as exc:
            logger.debug("residency tick: upsert %s failed: %s", r.agent_id, exc)
    if placed:
        logger.debug("skyoffice_residency: placed=%d skipped=%d", placed, skipped)


def _residency_loop() -> None:
    while True:
        try:
            _residency_tick()
        except Exception as exc:
            logger.warning("residency loop iteration failed: %s", exc)
        time.sleep(_TICK_INTERVAL_SECONDS)


def start_residency() -> None:
    """Idempotent — start the residency tick thread."""
    global _residency_started
    if _residency_started:
        return
    _residency_started = True
    threading.Thread(
        target=_residency_loop, name="skyoffice-residency", daemon=True,
    ).start()
    logger.info("skyoffice_residency: started (tick every %ds)",
                int(_TICK_INTERVAL_SECONDS))
