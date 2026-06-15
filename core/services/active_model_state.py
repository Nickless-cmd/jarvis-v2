"""Aktiv per-run visible-model (provider+model) pr. bruger.

Problemet: composeren kan override provider/model pr. besked (provider_choice).
Den override havner i system-prompten ("You are running as model: X via provider:
Y") MEN ikke i `read_model_config`-tool'et, som læser den GLOBALE provider_router-
default. Resultat: tool'et modsiger prompten → Jarvis konfabulerer "config-drift".

Denne lille DB-backede store husker den SENESTE aktive (provider, model) pr.
bruger, sat ved run-start, så read_model_config kan vise den aktive override ved
siden af den globale default. Cross-proces (api↔runtime) via runtime_state_kv.
"""
from __future__ import annotations

from datetime import datetime, timezone

from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_KEY = "active_visible_targets"


def _norm_uid(user_id: str | None) -> str:
    return str(user_id).strip() if (user_id and str(user_id).strip()) else "owner"


def set_active_visible_target(user_id: str | None, provider: str, model: str) -> None:
    """Husk den aktive (provider, model) for en bruger ved run-start."""
    data = get_runtime_state_value(_KEY, {})
    if not isinstance(data, dict):
        data = {}
    data[_norm_uid(user_id)] = {
        "provider": str(provider or ""),
        "model": str(model or ""),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    set_runtime_state_value(_KEY, data)


def get_active_visible_target(user_id: str | None) -> dict | None:
    """Den seneste aktive (provider, model) for en bruger, eller None."""
    data = get_runtime_state_value(_KEY, {})
    if not isinstance(data, dict):
        return None
    rec = data.get(_norm_uid(user_id))
    return rec if isinstance(rec, dict) and rec.get("provider") else None
