"""Relation map — multi-tenant user theory of mind.

Lag 1 (teknisk krav): Gør user_theory_of_mind multi-tenant.

Bygger en relation_map der kan rumme flere user_theory_of_mind-instanser.
Primær bruger (default_user_id = "bjorn") bruger fortsat den DB-backed ToM
fra user_theory_of_mind.build_user_mental_model().
Sekundære brugere får JSON-backed lightweight profiler i runtime state.

Formål: Jarvis kan skelne og huske to eller flere personer separat.
Den sociale del (invitere en anden person) er et menneskeligt anliggende.
Den tekniske del er at arkitekturen er klar til det, når det sker.

Struktur i runtime state:
    {
      "users": {
        "bjorn": {
          "display_name": "Bjørn",
          "is_primary": true,
          "first_seen": "...",
          "last_seen": "...",
        },
        "<other_id>": {
          "display_name": "...",
          "is_primary": false,
          "first_seen": "...",
          "last_seen": "...",
          "tom_snapshot": {
            "traits": [...],
            "patterns": [...],
            "current_state": {...},
            "predictions": [...],
            "updated_at": "...",
          }
        }
      }
    }

Primær bruger bygges altid live fra DB; sekundære brugeres profiler
opdateres manuelt via update_secondary_user_tom().
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_STATE_KEY = "relation_map.state"
_DEFAULT_PRIMARY_ID = "bjorn"


# ---------------------------------------------------------------------------
# Public: relation map management
# ---------------------------------------------------------------------------


def get_relation_map() -> dict[str, object]:
    """Return full relation map. Auto-initializes primary user on first call."""
    state = _load_state()
    users = _users(state)
    if _DEFAULT_PRIMARY_ID not in users:
        ensure_primary_user()
        state = _load_state()
    return state


def ensure_primary_user(
    *,
    user_id: str = _DEFAULT_PRIMARY_ID,
    display_name: str = "Bjørn",
) -> None:
    """Ensure primary user entry exists in relation map."""
    state = _load_state()
    users = _users(state)
    if user_id not in users:
        users[user_id] = {
            "display_name": display_name,
            "is_primary": True,
            "first_seen": datetime.now(UTC).isoformat(),
            "last_seen": datetime.now(UTC).isoformat(),
        }
        _save_state({"users": users})


def register_secondary_user(
    *,
    user_id: str,
    display_name: str,
) -> dict[str, object]:
    """Register a new secondary user in the relation map."""
    state = _load_state()
    users = _users(state)
    now = datetime.now(UTC).isoformat()
    if user_id in users:
        users[user_id]["last_seen"] = now
        users[user_id]["display_name"] = display_name
    else:
        users[user_id] = {
            "display_name": display_name,
            "is_primary": False,
            "first_seen": now,
            "last_seen": now,
            "tom_snapshot": {},
        }
    _save_state({"users": users})
    try:
        event_bus.publish(
            "relation_map.user_registered",
            {"user_id": user_id, "display_name": display_name, "is_primary": False},
        )
    except Exception:
        pass
    return {"user_id": user_id, "display_name": display_name}


def update_secondary_user_tom(
    *,
    user_id: str,
    tom_snapshot: dict[str, object],
) -> bool:
    """Update theory-of-mind snapshot for a secondary user."""
    state = _load_state()
    users = _users(state)
    if user_id not in users:
        return False
    if users[user_id].get("is_primary"):
        # Primary user's ToM lives in DB — don't overwrite here
        return False
    users[user_id]["tom_snapshot"] = {
        **tom_snapshot,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    users[user_id]["last_seen"] = datetime.now(UTC).isoformat()
    _save_state({"users": users})
    return True


def get_user_theory_of_mind(user_id: str) -> dict[str, object]:
    """Return theory-of-mind for a user.

    For primary user: builds live from DB.
    For secondary users: returns stored snapshot (may be empty on first call).
    """
    state = _load_state()
    users = _users(state)

    user_entry = users.get(user_id) or {}
    is_primary = bool(user_entry.get("is_primary", False))

    if is_primary or user_id == _DEFAULT_PRIMARY_ID:
        # Live DB-backed ToM for primary user
        try:
            from core.services.user_theory_of_mind import build_user_mental_model
            return build_user_mental_model()
        except Exception:
            return {"traits": [], "patterns": [], "current_state": {}, "predictions": []}

    # Snapshot-based ToM for secondary users
    return dict(user_entry.get("tom_snapshot") or {})


def list_users() -> list[dict[str, object]]:
    """Return all users in the relation map. Auto-initializes primary user."""
    get_relation_map()  # triggers primary user auto-init
    state = _load_state()
    users = _users(state)
    return [
        {
            "user_id": uid,
            "display_name": str(u.get("display_name") or uid),
            "is_primary": bool(u.get("is_primary")),
            "first_seen": str(u.get("first_seen") or ""),
            "last_seen": str(u.get("last_seen") or ""),
            "has_tom": bool(u.get("tom_snapshot") or u.get("is_primary")),
        }
        for uid, u in users.items()
    ]


def build_relation_map_surface() -> dict[str, object]:
    """MC observability surface."""
    users = list_users()
    primary = next((u for u in users if u["is_primary"]), None)
    return {
        "user_count": len(users),
        "primary_user": primary,
        "secondary_users": [u for u in users if not u["is_primary"]],
        "summary": (
            f"{len(users)} bruger(e): {', '.join(u['display_name'] for u in users)}"
            if users else "Ingen brugere registreret endnu"
        ),
    }


def tick_relation_map_refresh(
    *, trigger: str = "heartbeat", last_visible_at: str = ""
) -> dict[str, object]:
    """Periodisk opdatering af relation map.

    Cadence: 720 min (12t).
    Kill-switch: layer_relation_map_enabled i runtime.json.
    - Primary user (bjorn): opdaterer last_seen til nu.
    - Secondary users: opdaterer tom_snapshot.updated_at hvis snapshot er
      mere end layer_relation_map_decay_days dage gammelt (default 14 dage).
    """
    from core.runtime.secrets import read_runtime_key

    try:
        enabled = read_runtime_key("layer_relation_map_enabled")
    except Exception:
        enabled = True
    if not enabled:
        return {"status": "disabled", "reason": "layer_relation_map_enabled=false"}

    try:
        decay_days = int(read_runtime_key("layer_relation_map_decay_days"))
    except Exception:
        decay_days = 14
    threshold = timedelta(hours=12)
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    state = _load_state()
    users = _users(state)

    # Auto-init primary if missing
    if _DEFAULT_PRIMARY_ID not in users:
        ensure_primary_user()
        state = _load_state()
        users = _users(state)

    refreshed = 0

    for user_id, user_entry in users.items():
        if user_entry.get("is_primary"):
            # Primary user: opdater last_seen
            user_entry["last_seen"] = now_iso
            refreshed += 1
        else:
            # Secondary: opdater tom_snapshot.updated_at hvis stale
            snapshot = user_entry.get("tom_snapshot") or {}
            updated_at_raw = str(snapshot.get("updated_at") or user_entry.get("first_seen") or "")
            stale = True
            if updated_at_raw:
                try:
                    updated_at = datetime.fromisoformat(updated_at_raw.replace("Z", "+00:00"))
                    if updated_at.tzinfo is None:
                        updated_at = updated_at.replace(tzinfo=UTC)
                    stale = (now - updated_at) >= threshold
                except (ValueError, TypeError):
                    stale = True

            if stale:
                if not isinstance(snapshot, dict):
                    snapshot = {}
                snapshot["updated_at"] = now_iso
                user_entry["tom_snapshot"] = snapshot
                refreshed += 1

    _save_state({"users": users})

    try:
        event_bus.publish(
            "relation_map.refresh_tick",
            {"trigger": trigger, "refreshed": refreshed, "user_count": len(users)},
        )
    except Exception:
        pass

    return {"status": "ok", "refreshed": refreshed, "trigger": trigger}


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _load_state() -> dict[str, object]:
    payload = get_runtime_state_value(_STATE_KEY, default={"users": {}})
    return payload if isinstance(payload, dict) else {"users": {}}


def _save_state(state: dict[str, object]) -> None:
    set_runtime_state_value(_STATE_KEY, state)


def _users(state: dict[str, object]) -> dict[str, dict]:
    raw = state.get("users")
    if not isinstance(raw, dict):
        return {}
    return raw  # type: ignore[return-value]
