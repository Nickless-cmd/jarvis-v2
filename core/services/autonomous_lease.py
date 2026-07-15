"""visible↔autonomous mutual-exclusion lease (marker-default).

An autonomous, event-driven nudge must NEVER interrupt Bjørn mid-conversation
or race the visible lane on shared self-model/central state. The design
decision is "marker-first, opt-in wake only when idle":

- The visible lane holds a short TTL lease while a turn is in flight.
- An autonomous dispatch that fires while the visible lease is held does NOT
  proceed; it instead writes a durable MARKER (a bounded pending list) and
  defers. When the visible turn ends the deferred nudges can be reconsidered.
- Only when the visible lane is idle does an autonomous dispatch proceed.

Durable via ``core.runtime.db_core.get/set_runtime_state_value`` so a lease and
its markers survive restarts. Self-safe: every DB touch is wrapped and failures
fail-open (idle / empty) so this guard can never wedge the runtime.
"""

from __future__ import annotations

import time
from typing import Any

from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value

# runtime_state keys
_LEASE_KEY = "autonomous_lease.visible"
_MARKERS_KEY = "autonomous_lease.pending_markers"

# Bounded marker list so a long visible session can't grow it unboundedly.
MAX_MARKERS = 50

# Default visible-lease lifetime. Auto-expires so a crashed turn never locks
# the autonomous lane out forever.
DEFAULT_TTL_S = 120.0


def _now(now_ts: float | None) -> float:
    return time.time() if now_ts is None else float(now_ts)


def acquire_visible(ttl_s: float = DEFAULT_TTL_S, now_ts: float | None = None) -> None:
    """Visible lane claims the lease for ``ttl_s`` seconds (fail-open)."""
    try:
        expires_at = _now(now_ts) + max(0.0, float(ttl_s))
        set_runtime_state_value(_LEASE_KEY, {"expires_at": expires_at})
    except Exception:
        # Fail-open: if we can't record the lease, the autonomous lane simply
        # sees "idle" and proceeds — never wedges the visible turn.
        pass


def release_visible() -> None:
    """Visible lane releases the lease (fail-open)."""
    try:
        set_runtime_state_value(_LEASE_KEY, {"expires_at": 0.0})
    except Exception:
        pass


def visible_active(now_ts: float | None = None) -> bool:
    """True if a visible lease is currently held and not expired (fail-open)."""
    try:
        raw = get_runtime_state_value(_LEASE_KEY, None)
    except Exception:
        return False
    if not isinstance(raw, dict):
        return False
    try:
        expires_at = float(raw.get("expires_at", 0.0))
    except (TypeError, ValueError):
        return False
    return expires_at > _now(now_ts)


def _read_markers() -> list[dict[str, Any]]:
    try:
        raw = get_runtime_state_value(_MARKERS_KEY, None)
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    return [m for m in raw if isinstance(m, dict)]


def _write_markers(markers: list[dict[str, Any]]) -> None:
    try:
        set_runtime_state_value(_MARKERS_KEY, markers)
    except Exception:
        pass


def pending_markers() -> list[dict[str, Any]]:
    """Read (without draining) the deferred autonomous markers."""
    return _read_markers()


def consume_markers() -> list[dict[str, Any]]:
    """Read AND drain the deferred markers (a second call returns empty)."""
    markers = _read_markers()
    if markers:
        _write_markers([])
    return markers


def try_autonomous_dispatch(
    payload: dict[str, Any],
    now_ts: float | None = None,
    *,
    scope: str | None = None,
    session_id: str | None = None,
    control_plane: bool = False,
) -> dict[str, Any]:
    """Gate an autonomous dispatch against the visible lane.

    If the visible lane is active → defer: append ``payload`` to the bounded
    pending-markers list and return ``{"action": "deferred", ...}``. If idle →
    return ``{"action": "proceed"}`` and the caller dispatches.

    Projection tags (Bilag 2, "one self, many projections"). All optional and
    additive — omit them and the marker is exactly as before (a GLOBAL
    self-signal nudge visible to everyone):

    * ``scope`` — the ``user_id`` this nudge was derived from. A user-scoped
      nudge surfaces ONLY in that user's context (see :func:`nudge_allowed_for`).
    * ``session_id`` — narrows a user-scoped nudge to a single conversation.
    * ``control_plane`` — marks a control-plane nudge (Central, council,
      telemetry, gate-toggles): OWNER-only, never surfaced to members.
    """
    marker = dict(payload) if isinstance(payload, dict) else {"payload": payload}
    marker.setdefault("marked_at", _now(now_ts))
    if scope is not None:
        marker["scope"] = str(scope)
    if session_id is not None:
        marker["session_id"] = str(session_id)
    if control_plane:
        marker["control_plane"] = True

    if visible_active(now_ts=now_ts):
        markers = _read_markers()
        markers.append(marker)
        # Bounded: drop oldest so the list can't grow unbounded.
        if len(markers) > MAX_MARKERS:
            markers = markers[-MAX_MARKERS:]
        _write_markers(markers)
        return {"action": "deferred", "reason": "visible-active"}
    return {"action": "proceed"}


def _resolve_role(user_id: str | None, role: str | None) -> str | None:
    """Resolve the member role, preferring an explicit ``role``.

    Reuses the existing user registry (``find_user_by_discord_id``) rather than
    inventing a second source of truth. Self-safe: on any lookup error the role
    stays unknown (None) so the gate fails toward LESS exposure, never more.
    """
    if role is not None:
        return str(role).strip().lower() or None
    uid = str(user_id or "").strip()
    if not uid:
        return None
    try:
        from core.identity.users import find_user_by_discord_id

        user = find_user_by_discord_id(uid)
    except Exception:
        return None
    return user.role if user is not None else None


def nudge_allowed_for(
    marker: dict[str, Any],
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    role: str | None = None,
) -> bool:
    """Role- AND session-gate: may this nudge surface for this user/session?

    Rules (default-open for the shared self, closed for the private layers):

    1. **Control-plane** nudge → OWNER only. Members meet the being, not the
       machine room under it.
    2. **Global** nudge (no ``scope``) → visible to everyone. These are the
       shared self-signals (body, mood, continuity) — the same Jarvis for all.
    3. **User-scoped** nudge → only the matching ``user_id``; and if the marker
       also carries a ``session_id``, only that session. A relation's nudge
       never leaks into another relation's room.

    Self-safe: a malformed marker fails toward suppression (False), never toward
    leaking a private nudge.
    """
    if not isinstance(marker, dict):
        return False

    resolved_role = _resolve_role(user_id, role)

    if marker.get("control_plane"):
        return resolved_role == "owner"

    m_scope = marker.get("scope")
    if m_scope is None:
        return True  # global self-signal nudge → the full being, for everyone

    if str(m_scope) != str(user_id or ""):
        return False

    m_session = marker.get("session_id")
    if m_session is not None and session_id is not None:
        return str(m_session) == str(session_id)
    return True


def markers_for(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    role: str | None = None,
    drain: bool = False,
) -> list[dict[str, Any]]:
    """Return the deferred markers this user/session/role is allowed to see.

    Role- and session-gated projection of the pending markers. With
    ``drain=True`` the returned (allowed) markers are removed from the durable
    list while everyone else's markers are left untouched — so consuming your
    own nudges never drops another relation's pending nudge.
    """
    all_markers = _read_markers()
    allowed = [
        m
        for m in all_markers
        if nudge_allowed_for(m, user_id=user_id, session_id=session_id, role=role)
    ]
    if drain and allowed:
        remaining = [m for m in all_markers if m not in allowed]
        _write_markers(remaining)
    return allowed
