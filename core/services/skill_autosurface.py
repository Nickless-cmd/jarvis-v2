"""Owner-approved allowlist governing jarvis-code skill auto-surfacing (Fase 3).

Auto-surfacing (catalog injection into the system prompt + the client-driven
`skill_gate(autosurface=true)` call) widens the injection surface: the model
can `write_file` a `SKILL.md` and self-modify what gets suggested to it next
turn. This module is the choke point — *which* skills are eligible to be
auto-surfaced requires explicit owner approval, persisted outside the model's
reach. Ties into `project_self_registering_nerves` (durable, owner-gated
component registry: the model proposes, the owner approves, never auto-on).

Master kill-switch: `RuntimeSettings.skill_autosurface_enabled` (default
False). While off, `filter_to_approved` always returns `[]` — the whole
feature is inert even if skills are approved. Self-safe: all disk I/O is
wrapped so a corrupt/missing store never crashes the prompt-build or
skill_gate path — it just degrades to "nothing approved".
"""
from __future__ import annotations

import json
import logging
from typing import Any

from core.runtime.config import CONFIG_DIR

logger = logging.getLogger(__name__)

_STORE_PATH = CONFIG_DIR / "skill_autosurface.json"


def _read_store() -> dict[str, Any]:
    try:
        if not _STORE_PATH.exists():
            return {"approved": []}
        data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"approved": []}
        approved = data.get("approved")
        if not isinstance(approved, list):
            approved = []
        return {"approved": [str(n) for n in approved]}
    except Exception:
        logger.debug("skill_autosurface: store read fejlede, fail-safe empty", exc_info=True)
        return {"approved": []}


def _write_store(data: dict[str, Any]) -> None:
    try:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.debug("skill_autosurface: store write fejlede", exc_info=True)


def _emit_governance_event(kind: str, payload: dict[str, Any] | None = None) -> None:
    """Self-safe eventbus emission — observability must never break approval flow."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"skill.autosurface.{kind}", payload or {})
    except Exception:
        pass


def list_approved() -> list[str]:
    """Owner-approved skill names eligible for auto-surfacing. Empty on a fresh/corrupt store."""
    return list(_read_store().get("approved", []))


def approve_skill(name: str, *, role: str) -> bool:
    """Owner-only. Validates against installed skills (skill_engine.skill_exists).

    Raises PermissionError for any non-owner role. Returns False (no-op) for
    an unknown skill name. Returns True and persists on success.
    """
    if role != "owner":
        raise PermissionError("skill_autosurface.approve_skill requires role='owner'")

    from core.services import skill_engine
    if not skill_engine.skill_exists(name):
        return False

    store = _read_store()
    approved = store.get("approved", [])
    if name not in approved:
        approved.append(name)
        store["approved"] = approved
        _write_store(store)
        _emit_governance_event("approved", {"skill": name})
    return True


def revoke_skill(name: str, *, role: str) -> bool:
    """Owner-only. Removes `name` from the allowlist if present."""
    if role != "owner":
        raise PermissionError("skill_autosurface.revoke_skill requires role='owner'")

    store = _read_store()
    approved = store.get("approved", [])
    if name in approved:
        approved = [n for n in approved if n != name]
        store["approved"] = approved
        _write_store(store)
        _emit_governance_event("revoked", {"skill": name})
    return True


def filter_to_approved(names: list[str]) -> list[str]:
    """Narrow `names` to the owner-approved allowlist, gated by the master flag.

    Returns [] when the flag is off (feature inert), regardless of what's
    been approved — turning the flag on is a separate, explicit opt-in.
    """
    try:
        from core.runtime.settings import load_settings
        if not load_settings().skill_autosurface_enabled:
            return []
    except Exception:
        logger.debug("skill_autosurface: settings read fejlede, fail-safe empty", exc_info=True)
        return []

    approved = set(list_approved())
    return [n for n in names if n in approved]
