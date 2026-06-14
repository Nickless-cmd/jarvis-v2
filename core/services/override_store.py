"""Owner-override-session-store — DB-backed, cross-proces.

Spec §6, §14.2. Når Bjørn verificerer sig via TOTP i en fremmed session, gemmes
override-state her. **DB-backed (runtime_state_kv), IKKE in-memory** — jarvis-api
og jarvis-runtime er separate processer (13. juni-lektien: in-memory dicts spænder
ikke processer; bridge-routing/wakeup-bugs kom præcis derfra).

Bagdørs-invariant (§6.0): en AKTIV override = fuld owner-KONTROL (alle tools).
Niveauet (`help`/`debug`) styrer kun DATA-dybde mod en fremmed brugers ting; det
nedgraderer ALDRIG tool-kontrollen. `private` kan aldrig aktiveres (hardblock).

Per-session nøgle (`owner_override:<session_id>`) → undgår read-modify-write-race
på en delt dict mellem processer.

- `grant(session_id, level)` — start override; initial-vindue 90s (§6.3).
- `touch(session_id)` — aktivitet fornyer til 5 min (§9); revivér ikke udløbet.
- `is_active` / `level` — læs (lazy expiry).
- `revoke(session_id)` — sæt udløbet (ingen delete-API i runtime_state).
"""
from __future__ import annotations

import time

from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_INITIAL_WINDOW = 90.0    # sek — første override-vindue (§6.3)
_ACTIVITY_WINDOW = 300.0  # sek — fornyes ved aktivitet (§9, 5 min)
_GRANTABLE_LEVELS = ("help", "debug")  # 'private' er hardblock — aldrig grantbar


def _key(session_id: str) -> str:
    return f"owner_override:{str(session_id or '').strip()}"


def _now(now: float | None) -> float:
    return time.time() if now is None else float(now)


def grant(session_id: str, *, level: str = "help", now: float | None = None) -> dict:
    """Aktivér owner-override for en session. Returnér record.

    `level` clamps til {help, debug}; alt andet (inkl. 'private') → 'help'
    (private kan aldrig aktiveres, §6.4). Initial-vindue 90s.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return {}
    lvl = level if level in _GRANTABLE_LEVELS else "help"
    ts = _now(now)
    record = {
        "level": lvl,
        "granted_at": ts,
        "expires_at": ts + _INITIAL_WINDOW,
    }
    set_runtime_state_value(_key(sid), record)
    return record


def _read(session_id: str) -> dict | None:
    raw = get_runtime_state_value(_key(session_id), None)
    return raw if isinstance(raw, dict) else None


def is_active(session_id: str, *, now: float | None = None) -> bool:
    """True hvis sessionen har en aktiv (ikke-udløbet) override."""
    rec = _read(session_id)
    if not rec:
        return False
    return _now(now) < float(rec.get("expires_at") or 0)


def level(session_id: str, *, now: float | None = None) -> str | None:
    """Override-niveau hvis aktiv, ellers None."""
    rec = _read(session_id)
    if not rec or _now(now) >= float(rec.get("expires_at") or 0):
        return None
    return str(rec.get("level") or "help")


def touch(session_id: str, *, now: float | None = None) -> bool:
    """Forny en AKTIV override til +5 min ved aktivitet. False hvis udløbet/fraværende.

    Reviverer aldrig en udløbet override (§9 — override aktivt 5 min efter
    første verifikation, fornyes ved aktivitet, men ikke genoplivning).
    """
    rec = _read(session_id)
    if not rec:
        return False
    ts = _now(now)
    if ts >= float(rec.get("expires_at") or 0):
        return False
    rec["expires_at"] = ts + _ACTIVITY_WINDOW
    set_runtime_state_value(_key(session_id), rec)
    return True


def revoke(session_id: str) -> None:
    """Deaktivér override (sæt udløbet — runtime_state har ingen delete)."""
    rec = _read(session_id) or {"level": "help", "granted_at": 0.0}
    rec["expires_at"] = 0.0
    set_runtime_state_value(_key(session_id), rec)
