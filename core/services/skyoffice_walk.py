"""SkyOffice walk module — smooth movement instead of teleporting.

When a resident moves between positions (desk ↔ meeting room ↔ another
agent's desk) the bridge previously did one upsert with new x/y, which
Phaser snaps to instantly. This module replaces that snap with a real
walk: the agent's x/y is tweened toward the target every ~150ms with
the right run animation, then settles into the requested final anim.

Architecture: a single daemon walker thread serves all active walks.
Each walk: snapshot start position, compute step vector, push the
agent toward target until distance < step. New walks for the same
agent supersede pending ones (you can interrupt a walk-back-to-desk
by sending the agent to a meeting).

Tracking current position is necessary because the bridge is one-way
(we only push). The walker keeps its own `_last_known_position` map
seeded by walk endpoints — residency seeds it for new residents.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


_STEP_INTERVAL_S = 0.15        # ~6 fps server-side updates
_STEP_PIXELS = 24              # px per step (smooth at 6 fps → 160 px/s)


@dataclass
class _Walk:
    agent_id: str
    target_x: int
    target_y: int
    final_anim: str
    sprite: str  # "adam"|"ash"|"lucy"|"nancy"
    on_arrive: Any = None  # optional callable() invoked when walk completes
    cur_x: int = 0
    cur_y: int = 0
    started: float = field(default_factory=time.time)


_walks: dict[str, _Walk] = {}
_positions: dict[str, tuple[int, int]] = {}
_lock = threading.Lock()
_walker_started = False


def set_known_position(agent_id: str, x: int, y: int) -> None:
    """Seed the walker's belief of where an agent currently is.
    Call this when you place an agent without a walk (e.g., first spawn)."""
    with _lock:
        _positions[agent_id] = (int(x), int(y))


def get_known_position(agent_id: str) -> tuple[int, int] | None:
    with _lock:
        return _positions.get(agent_id)


def walk_to(
    *,
    agent_id: str,
    target_x: int,
    target_y: int,
    final_anim: str,
    sprite: str,
    on_arrive: Any = None,
) -> None:
    """Schedule a smooth walk for this agent. If there's already a walk in
    flight, replace it (the new target wins). If we don't know the current
    position, snap directly to the target (no walk possible)."""
    with _lock:
        cur = _positions.get(agent_id)
        if cur is None:
            # Snap. Caller should set_known_position first; do best-effort.
            _positions[agent_id] = (int(target_x), int(target_y))
            _do_snap = True
        else:
            cx, cy = cur
            _walks[agent_id] = _Walk(
                agent_id=agent_id,
                target_x=int(target_x), target_y=int(target_y),
                final_anim=str(final_anim or ""),
                sprite=str(sprite or "adam"),
                on_arrive=on_arrive,
                cur_x=cx, cur_y=cy,
            )
            _do_snap = False
    if _do_snap:
        _snap_to(agent_id, target_x, target_y, final_anim)


def _snap_to(agent_id: str, x: int, y: int, anim: str) -> None:
    from core.services.skyoffice_bridge import upsert_agent
    try:
        upsert_agent(agent_id=agent_id, x=int(x), y=int(y), anim=anim)
    except Exception as exc:
        logger.debug("walk snap %s failed: %s", agent_id, exc)


def _direction_anim(sprite: str, dx: int, dy: int) -> str:
    """Pick the run animation for the dominant axis of motion."""
    if abs(dx) > abs(dy):
        return f"{sprite}_run_{'right' if dx > 0 else 'left'}"
    return f"{sprite}_run_{'down' if dy > 0 else 'up'}"


def _step_one_walk(walk: _Walk) -> bool:
    """Advance one walk by a step. Returns True if walk is complete."""
    from core.services.skyoffice_bridge import upsert_agent

    dx = walk.target_x - walk.cur_x
    dy = walk.target_y - walk.cur_y
    distance = (dx * dx + dy * dy) ** 0.5
    if distance <= _STEP_PIXELS:
        # Final step — snap to target and apply final anim
        try:
            upsert_agent(
                agent_id=walk.agent_id,
                x=int(walk.target_x), y=int(walk.target_y),
                anim=walk.final_anim,
            )
        except Exception as exc:
            logger.debug("walk arrive %s failed: %s", walk.agent_id, exc)
        with _lock:
            _positions[walk.agent_id] = (int(walk.target_x), int(walk.target_y))
        if callable(walk.on_arrive):
            try:
                walk.on_arrive()
            except Exception as exc:
                logger.debug("walk on_arrive %s failed: %s", walk.agent_id, exc)
        return True

    # Mid-walk step
    step_dx = int(round((dx / distance) * _STEP_PIXELS))
    step_dy = int(round((dy / distance) * _STEP_PIXELS))
    new_x = walk.cur_x + step_dx
    new_y = walk.cur_y + step_dy
    anim = _direction_anim(walk.sprite, step_dx, step_dy)
    try:
        upsert_agent(
            agent_id=walk.agent_id,
            x=new_x, y=new_y, anim=anim,
        )
    except Exception as exc:
        logger.debug("walk step %s failed: %s", walk.agent_id, exc)
    walk.cur_x = new_x
    walk.cur_y = new_y
    with _lock:
        _positions[walk.agent_id] = (new_x, new_y)
    return False


def _walker_loop() -> None:
    while True:
        try:
            with _lock:
                snapshot = list(_walks.items())
            done: list[str] = []
            for agent_id, walk in snapshot:
                if _step_one_walk(walk):
                    done.append(agent_id)
            if done:
                with _lock:
                    for aid in done:
                        _walks.pop(aid, None)
        except Exception as exc:
            logger.warning("walker loop iter failed: %s", exc)
        time.sleep(_STEP_INTERVAL_S)


def start_walker() -> None:
    global _walker_started
    if _walker_started:
        return
    _walker_started = True
    threading.Thread(
        target=_walker_loop, name="skyoffice-walker", daemon=True,
    ).start()
    logger.info("skyoffice_walk: walker thread started")
