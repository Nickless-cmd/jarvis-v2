"""Bro-broker — owner-styret skift mellem aktive bro-forbindelser (spec §6.6).

Under en gyldig TOTP-override kan Bjørn sige "forbind til Mikkels bro" / "mors bro".
Broerne (Discord-gateways, Telegram-listeners, jarvis-desk operator-broer) er
registreret i jarvisx_bridge.bridge_registry, keyed by user_id.

switch() verificerer ALTID override_store.is_active for requester-sessionen FØR
et skift signaleres — ingen override → intet skift (bagdørs-invariant §6.0: kun
TOTP-verificeret owner kan krydse til en fremmed bro). Skiftet signaleres via
eventbus; selve routing-ændringen håndteres af lytteren (Fase 4-wiring).
"""
from __future__ import annotations

_SWITCHABLE_LEVELS = ("help", "debug")


def _active_user_ids() -> list[str]:
    """user_id'er med en aktiv bro (process-local registry)."""
    try:
        from core.services.jarvisx_bridge import bridge_registry
        return bridge_registry.list_user_ids()
    except Exception:
        return []


def list_active_bros() -> list[str]:
    """Alle brugere med en aktiv bro lige nu."""
    return _active_user_ids()


def switch(target_user: str, *, requester_session: str, now: float | None = None) -> dict:
    """Skift requester-sessionen til target-brugerens bro — kræver gyldig override.

    Returnerer {ok, ...}. Afvises hvis: ingen aktiv override, utilstrækkeligt
    niveau (kun help/debug kan skifte; private er hardblock), eller target-broen
    ikke er forbundet.
    """
    from core.services import override_store

    target = str(target_user or "").strip()
    if not override_store.is_active(requester_session, now=now):
        return {"ok": False, "reason": "no_active_override"}
    lvl = override_store.level(requester_session, now=now)
    if lvl not in _SWITCHABLE_LEVELS:
        return {"ok": False, "reason": "insufficient_level", "level": lvl}
    if target not in _active_user_ids():
        return {"ok": False, "reason": "bro_not_found", "available": _active_user_ids()}

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("bro_broker.switch_requested", {
            "target_user": target,
            "requester_session": requester_session,
            "level": lvl,
        })
    except Exception:
        pass
    return {"ok": True, "target_user": target, "level": lvl}
