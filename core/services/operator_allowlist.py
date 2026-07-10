"""Operator app-allowlist (leak-kandidat #5, CHICAGO-guard-mønster, 2026-07-10).

CHICAGO (Claude Codes desktop-computer-use) begrænser GUI-kontrol til en app-
ALLOWLIST + frontmost-gate + pr-session approval. Jarvis' operator-bro havde
pr-handling chat-godkendelse, men INGEN allowlist — han kunne bede om at styre
et hvilket som helst program. Dette tilføjer den manglende allowlist-guard.

OBSERVE-BY-DEFAULT (sikkert): uden enforce logges ikke-allowlistede app-kontrol-
forsøg til Centralen (så Bjørn SER hvilke apps Jarvis rører), men blokerer ikke —
så det bryder ikke hans tunge operator-flow. Owner flipper enforce for at håndhæve.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value

logger = logging.getLogger(__name__)

_LIST_KEY = "operator_app_allowlist"
_ENFORCE_KEY = "operator_app_allowlist_enforce"  # default False = observe-only


def _norm(app: str) -> str:
    return str(app or "").strip().lower()


def list_allowlist() -> list[str]:
    raw = get_runtime_state_value(_LIST_KEY, "[]")
    try:
        data = json.loads(raw) if isinstance(raw, str) else (raw or [])
        return [str(a) for a in data] if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def set_allowlist(apps: list[str]) -> list[str]:
    clean = sorted({_norm(a) for a in (apps or []) if _norm(a)})
    set_runtime_state_value(_LIST_KEY, json.dumps(clean, ensure_ascii=False))
    return clean


def add_to_allowlist(app: str) -> list[str]:
    cur = set(list_allowlist())
    n = _norm(app)
    if n:
        cur.add(n)
    return set_allowlist(sorted(cur))


def remove_from_allowlist(app: str) -> list[str]:
    cur = [a for a in list_allowlist() if a != _norm(app)]
    return set_allowlist(cur)


def is_enforced() -> bool:
    raw = get_runtime_state_value(_ENFORCE_KEY, False)
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return bool(raw)


def set_enforced(on: bool) -> bool:
    set_runtime_state_value(_ENFORCE_KEY, bool(on))
    return bool(on)


def _matches(app: str, allowlist: list[str]) -> bool:
    """En app matcher hvis dens navn/sti indeholder en allowlist-post (substring,
    så '/Applications/Safari.app' matcher 'safari')."""
    a = _norm(app)
    return any(entry and entry in a for entry in allowlist)


def check_app(app: str) -> dict[str, Any]:
    """Vurdér om Jarvis må GUI-styre `app`. OBSERVE-by-default:
    - matcher allowlist → allowed.
    - ellers + enforce OFF → allowed=True men observed=True (logget, ikke blokeret).
    - ellers + enforce ON → allowed=False (blokeret, ærlig grund)."""
    allowlist = list_allowlist()
    enforced = is_enforced()
    matched = _matches(app, allowlist)
    if matched:
        return {"allowed": True, "matched": True, "enforced": enforced, "app": app}
    # ikke på allowlist
    if not enforced:
        # observe-only: log at Jarvis rører en ikke-allowlistet app
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish("operator.app_not_allowlisted", {
                "app": str(app)[:200], "enforced": False, "action": "observed"})
        except Exception:
            pass
        return {"allowed": True, "matched": False, "enforced": False, "observed": True, "app": app}
    return {"allowed": False, "matched": False, "enforced": True, "app": app,
            "reason": (f"'{app}' er ikke på operator-app-allowlisten (enforce=ON). "
                       "Tilføj den via operator_allowlist.add_to_allowlist, ellers afvises GUI-kontrol.")}


def build_operator_allowlist_surface() -> dict[str, Any]:
    """Central-CLI: jc raw /central/operator-allowlist."""
    apps = list_allowlist()
    return {
        "active": True,
        "mode": "operator-app-allowlist",
        "enforced": is_enforced(),
        "summary": {"count": len(apps), "state": "enforce" if is_enforced() else "observe"},
        "items": apps,
    }
