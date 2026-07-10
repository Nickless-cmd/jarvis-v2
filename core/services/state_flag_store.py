"""State-flag store (leak-kandidat #1, 2026-07-10).

Letvægts nøgle→værdi-flag med TTL + cross-session persistens, pr. bruger. Modstykke
til Claude Codes `state.flag(key, value, ttl)` (KAIROS/CHICAGO-mønster). Jarvis havde
`schedule_task`+`remember_this`, men ikke en eksplicit flag-butik med get/list/clear.

Brug: "husk at spørge om X om 30 min", "denne output skal gemmes til review",
"afventer bruger-input" — sæt et flag, gå videre, læs det næste gang.

DB-backed (runtime_state_kv) → cross-proces (api↔runtime), overlever genstart.
Per-user JSON-dict; udløbne flag prunes ved læsning.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value


def _now() -> datetime:
    return datetime.now(UTC)


def _key(user_id: str) -> str:
    return f"state_flags:{user_id or 'default'}"


def _load(user_id: str) -> dict[str, dict[str, Any]]:
    raw = get_runtime_state_value(_key(user_id), "{}")
    try:
        data = json.loads(raw) if isinstance(raw, str) else (raw or {})
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _save(user_id: str, flags: dict[str, dict[str, Any]]) -> None:
    set_runtime_state_value(_key(user_id), json.dumps(flags, ensure_ascii=False, default=str))


def _prune(flags: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Fjern udløbne flag. Returnerer den rensede dict (muterer input)."""
    now_iso = _now().isoformat()
    dead = [k for k, v in flags.items()
            if v.get("expires_at") and str(v["expires_at"]) <= now_iso]
    for k in dead:
        flags.pop(k, None)
    return flags


def set_flag(key: str, value: Any, *, ttl_minutes: float | None = None,
             user_id: str = "default") -> dict[str, Any]:
    """Sæt/opdatér et flag. ttl_minutes=None/0 → intet udløb. Returnerer den lagrede
    post (til bekræftelse — strikst resultat-kontrakt)."""
    k = str(key or "").strip()
    if not k:
        raise ValueError("flag-nøgle må ikke være tom")
    flags = _prune(_load(user_id))
    expires_at = None
    if ttl_minutes and float(ttl_minutes) > 0:
        expires_at = (_now() + timedelta(minutes=float(ttl_minutes))).isoformat()
    rec = {"value": value, "expires_at": expires_at, "created_at": _now().isoformat()}
    flags[k] = rec
    _save(user_id, flags)
    return {"key": k, **rec}


def get_flag(key: str, *, user_id: str = "default") -> dict[str, Any] | None:
    """Læs et flag (prune udløbne først). None hvis ukendt/udløbet."""
    k = str(key or "").strip()
    if not k:
        return None
    flags = _prune(_load(user_id))
    _save(user_id, flags)  # persistér pruning
    rec = flags.get(k)
    return {"key": k, **rec} if rec else None


def clear_flag(key: str, *, user_id: str = "default") -> bool:
    """Fjern et flag. True hvis det fandtes."""
    k = str(key or "").strip()
    if not k:
        return False
    flags = _load(user_id)
    existed = k in flags
    if existed:
        flags.pop(k, None)
        _save(user_id, flags)
    return existed


def list_flags(*, user_id: str = "default") -> list[dict[str, Any]]:
    """Alle aktive (ikke-udløbne) flag."""
    flags = _prune(_load(user_id))
    _save(user_id, flags)
    return [{"key": k, **v} for k, v in flags.items()]
