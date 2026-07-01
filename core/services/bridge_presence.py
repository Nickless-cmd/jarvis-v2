"""Cross-proces bro-tilstedeværelse via shared_cache (samme mønster som central_xproc).

Bro-registret er PER-PROCES (desk-WS registreres kun i api/8080; runtime/8011 har sit eget).
Når Bjørn skriver fra mobil kan runnen eksekvere i runtime-processen → den kan IKKE se om der
findes en levende desk-bro, og under HVILKET user_id. Resultat: 'bridge_not_connected' uden at
vide hvorfor.

Hver proces publicerer SIT eget registry-snapshot under bridge:presence:{proces}. Så kan enhver
proces læse HVILKE user_id'er der har en bro og HVOR — grundlaget for (a) ægte fejl-diagnose og
(b) deterministisk forward. Self-safe: alt fanges, tom ved cache-nedbrud.
"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_PREFIX = "bridge:presence:"
_TTL = 300.0
_ROLES = ("api", "runtime")


def publish(bridges: dict[str, dict]) -> None:
    """Publicér denne proces' bro-registry-snapshot (kaldes ved register/unregister/dispatch)."""
    try:
        from core.services import shared_cache
        from core.services.central_xproc import process_role
        role = process_role()
        shared_cache.set(
            _PREFIX + role,
            {"process": role, "ts": time.time(), "bridges": dict(bridges or {})},
            ttl_seconds=_TTL,
        )
    except Exception:  # pragma: no cover - cache nede → uændret adfærd
        pass


def all_presence() -> dict[str, dict]:
    """Bro-tilstedeværelse fra ALLE processer → {user_id: {process, client, capabilities, ...}}."""
    out: dict[str, dict] = {}
    try:
        from core.services import shared_cache
        for role in _ROLES:
            snap = shared_cache.get(_PREFIX + role)
            if not isinstance(snap, dict):
                continue
            for uid, info in (snap.get("bridges") or {}).items():
                merged: dict[str, Any] = {"process": snap.get("process", role)}
                if isinstance(info, dict):
                    merged.update(info)
                out[str(uid)] = merged
    except Exception:  # pragma: no cover
        pass
    return out


def process_for_user(user_id: str) -> str | None:
    """Hvilken proces holder en levende bro for user_id? None hvis ingen."""
    return (all_presence().get(str(user_id)) or {}).get("process")
