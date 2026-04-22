"""User Registry — per-user workspace mapping for multi-user Jarvis.

Én Jarvis, flere brugere. Hver bruger har sin egen workspace (MEMORY.md +
USER.md + relations-historie). SOUL.md, IDENTITY.md, STANDING_ORDERS.md
og Jarvis' indre liv er fælles.

Storage: `~/.jarvis-v2/config/users.json`. Roles:
  - "owner" — fuld adgang, admin-rettigheder, kan tilføje brugere
  - "member" — samme tools i DM, begrænset admin

Design-principper:
- Users.json er single source of truth for kendt-bruger-liste
- Unknown discord_id → ignorér (handling ligger i discord_gateway)
- Workspace navnet mappes direkte til `WORKSPACES_DIR / <name>/`
- Discord_id er PRIMARY key (unique)
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path

from core.runtime.config import CONFIG_DIR

logger = logging.getLogger(__name__)

# Kept for backwards compat + tests — but the authoritative path is
# computed lazily by _users_file() so tests can monkeypatch CONFIG_DIR
# or HOME safely.
USERS_FILE = CONFIG_DIR / "users.json"
_VALID_ROLES = {"owner", "member"}
_LOCK = threading.Lock()


def _users_file() -> Path:
    """Resolve users.json path at call time so tests can isolate via HOME."""
    # Re-import to pick up any patched CONFIG_DIR
    from core.runtime.config import CONFIG_DIR as _CONFIG_DIR
    return Path(_CONFIG_DIR) / "users.json"


@dataclass(frozen=True)
class User:
    discord_id: str
    name: str
    role: str  # "owner" | "member"
    workspace: str
    created_at: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_file() -> None:
    if _users_file().exists():
        return
    _users_file().parent.mkdir(parents=True, exist_ok=True)
    _users_file().write_text(
        json.dumps({"users": []}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_users() -> list[User]:
    """Load all registered users from users.json. Empty list if file missing."""
    with _LOCK:
        _ensure_file()
        try:
            data = json.loads(_users_file().read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("users.py: failed to load users.json: %s", exc)
            return []
    raw_users = data.get("users") if isinstance(data, dict) else None
    if not isinstance(raw_users, list):
        return []
    users: list[User] = []
    for item in raw_users:
        if not isinstance(item, dict):
            continue
        did = str(item.get("discord_id") or "").strip()
        name = str(item.get("name") or "").strip()
        role = str(item.get("role") or "member").strip().lower()
        ws = str(item.get("workspace") or "").strip()
        if not did or not name or not ws:
            continue
        if role not in _VALID_ROLES:
            role = "member"
        users.append(User(
            discord_id=did,
            name=name,
            role=role,
            workspace=ws,
            created_at=str(item.get("created_at") or _now_iso()),
        ))
    return users


def _save_users(users: list[User]) -> None:
    with _LOCK:
        _ensure_file()
        payload = {"users": [u.as_dict() for u in users]}
        _users_file().write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False),
            encoding="utf-8",
        )


def find_user_by_discord_id(discord_id: str) -> User | None:
    """Lookup by discord_id. Returns None if unknown."""
    did = str(discord_id or "").strip()
    if not did:
        return None
    for user in load_users():
        if user.discord_id == did:
            return user
    return None


def find_user_by_name(name: str) -> User | None:
    target = str(name or "").strip().lower()
    if not target:
        return None
    for user in load_users():
        if user.name.lower() == target:
            return user
    return None


def find_user_by_workspace(workspace: str) -> User | None:
    target = str(workspace or "").strip()
    if not target:
        return None
    for user in load_users():
        if user.workspace == target:
            return user
    return None


def add_user(
    *,
    discord_id: str,
    name: str,
    role: str = "member",
    workspace: str = "",
) -> User | None:
    """Add a new user. Returns the User or None on validation failure.

    - discord_id must be unique
    - workspace defaults to name.lower() if empty
    - role defaults to 'member'; use 'owner' explicitly for the owner
    """
    did = str(discord_id or "").strip()
    nm = str(name or "").strip()
    if not did or not nm:
        return None
    role_c = str(role or "member").strip().lower()
    if role_c not in _VALID_ROLES:
        role_c = "member"
    ws = str(workspace or "").strip() or nm.lower().replace(" ", "_")

    existing = load_users()
    for u in existing:
        if u.discord_id == did:
            logger.warning("add_user: discord_id %s already exists (%s)", did, u.name)
            return None
        if u.workspace == ws:
            logger.warning("add_user: workspace %r already used by %s", ws, u.name)
            return None

    user = User(
        discord_id=did, name=nm, role=role_c, workspace=ws,
        created_at=_now_iso(),
    )
    existing.append(user)
    _save_users(existing)
    logger.info("add_user: registered %s (discord_id=%s, workspace=%s, role=%s)",
                nm, did, ws, role_c)
    return user


def remove_user(*, discord_id: str) -> bool:
    """Remove user from registry. Does NOT delete workspace files (manual decision)."""
    did = str(discord_id or "").strip()
    if not did:
        return False
    existing = load_users()
    kept = [u for u in existing if u.discord_id != did]
    if len(kept) == len(existing):
        return False
    _save_users(kept)
    logger.info("remove_user: removed discord_id=%s", did)
    return True


def get_owner() -> User | None:
    """Return the single owner user (there should be exactly one)."""
    for user in load_users():
        if user.role == "owner":
            return user
    return None


def is_known_discord_id(discord_id: str) -> bool:
    return find_user_by_discord_id(discord_id) is not None


def list_member_workspaces() -> list[str]:
    """Return all registered workspace names (for UI / admin)."""
    return [u.workspace for u in load_users()]
