"""Kvote-regnskab pr. bruger/mode med daglig nulstilling (spec §21).

Gratis chat har kvote; betalt chat er ubegrænset; code mode har time-kvote;
cowork + agent-dispatch har dag-kvoter. Owner er ALTID ubegrænset (§21.11).

Tier afgøres af `users.json` (eksplicit `tier`-felt for special-tilfælde som
ordblinde/blinde, §21.8) ELLER udledt af rolle (owner→owner, member→plus, ukendt→free).

Forbrug persisteres i runtime_state-DB keyed by dato (CET) → automatisk nulstilling
kl. 00:00 CET (§21.6), cross-proces (api↔runtime). Ren regnskabs-service; Stripe-
opgør (§21.6) og enforcement-wiring er separate lag.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_CET = ZoneInfo("Europe/Copenhagen")
_DB_PREFIX = "quota:"
_WARN_FRACTION = 0.8

# kind → tier → daglig grænse. None = ubegrænset. (§21.2)
_LIMITS: dict[str, dict[str, int | None]] = {
    "chat":     {"free": 20, "plus": None, "pro": None, "owner": None},
    "code":     {"free": 0,  "plus": 180,  "pro": 300,  "owner": None},  # compute-minutter
    "cowork":   {"free": 0,  "plus": 10,   "pro": 50,   "owner": None},  # approvals
    "agent":    {"free": 0,  "plus": 2,    "pro": 5,    "owner": None},  # dispatches
}
_VALID_TIERS = ("free", "plus", "pro", "owner")


def _today() -> str:
    return datetime.now(_CET).date().isoformat()


def get_tier(user_id: str) -> str:
    """Brugerens tier. Eksplicit users.json-tier vinder (special-tilfælde §21.8);
    ellers udledt af rolle. Ubundet ("") = owner."""
    uid = str(user_id or "").strip()
    if not uid:
        return "owner"
    try:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(uid)
        if u is not None:
            explicit = str(getattr(u, "tier", "") or "").strip().lower()
            if explicit in _VALID_TIERS:
                return explicit
            if getattr(u, "role", "") == "owner":
                return "owner"
            if getattr(u, "role", "") == "member":
                return "plus"
    except Exception:
        pass
    return "free"


def _limit_for(kind: str, tier: str) -> int | None:
    return _LIMITS.get(kind, {}).get(tier, 0)


def _db_key(user_id: str, kind: str) -> str:
    return f"{_DB_PREFIX}{_today()}:{user_id}:{kind}"


def _get_used(user_id: str, kind: str) -> int:
    try:
        from core.runtime.db import get_runtime_state_value
        raw = get_runtime_state_value(_db_key(user_id, kind), "0")
        return int(raw or 0)
    except Exception:
        return 0


def check_quota(user_id: str, kind: str) -> dict:
    """Status uden at forbruge. {allowed, tier, used, limit (None=ubegrænset),
    remaining, warn}. Owner/ubegrænset → allowed altid."""
    tier = get_tier(user_id)
    limit = _limit_for(kind, tier)
    used = _get_used(user_id, kind)
    if limit is None:  # ubegrænset
        return {"allowed": True, "tier": tier, "used": used, "limit": None,
                "remaining": None, "warn": False}
    remaining = max(0, limit - used)
    return {
        "allowed": used < limit,
        "tier": tier, "used": used, "limit": limit, "remaining": remaining,
        "warn": limit > 0 and used >= int(limit * _WARN_FRACTION),
    }


def consume_quota(user_id: str, kind: str, amount: int = 1) -> dict:
    """Forbrug `amount` af kvoten hvis muligt. Returnerer status (som check_quota)
    + `consumed: bool`. Blokerer (consumed=False) hvis grænsen ville overskrides.
    Owner/ubegrænset → forbruger altid (men registrerer ikke, ubegrænset)."""
    status = check_quota(user_id, kind)
    if status["limit"] is None:
        return {**status, "consumed": True}
    if status["used"] + amount > status["limit"]:
        return {**status, "allowed": False, "consumed": False}
    new_used = status["used"] + amount
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(_db_key(user_id, kind), str(new_used))
    except Exception:
        pass
    return check_quota(user_id, kind) | {"consumed": True}
