"""Provider selvhelbredelse (spec Fase C). To sikre auto-handlinger:
(1) 3+ providers nede samtidig → eskalér til Bjørn (Discord). (2) model-drift
(404) → fjern modellen fra routbar pool automatisk + log til Central.

Removal er sikkert at auto-køre (de-eskalering); addition kræver stadig gate
(se provider_autodiscovery.promote_pending)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_ESCALATE_THRESHOLD = 3

# Self-throttle: 60min. Modul-level state (nulstilles af daemon_manager restart via
# reset_var='_last_heal_at'). Heartbeat kalder tick hvert tick; daemonen no-op'er
# indtil cadencen er elapsed.
_last_heal_at = None  # datetime | None
_CADENCE_MINUTES = 60


def _notify_bjorn(message: str) -> None:
    """Eskalér via eksisterende notifikations-sti (Discord/ntfy)."""
    try:
        from core.services.notification_router import notify_owner
        notify_owner(message, priority="high", source="provider_self_heal")
    except Exception:
        logger.warning("provider_self_heal eskalering (kunne ikke sende): %s", message)


def _remove_from_router(provider: str, model: str) -> None:
    """Fjern (provider, model) fra provider_router.json. Self-safe."""
    try:
        import json
        from core.runtime.config import PROVIDER_ROUTER_FILE
        reg = json.loads(PROVIDER_ROUTER_FILE.read_text(encoding="utf-8"))
        before = reg.get("models") or []
        reg["models"] = [m for m in before
                         if not (m.get("provider") == provider and m.get("model") == model)]
        PROVIDER_ROUTER_FILE.write_text(json.dumps(reg, indent=2, ensure_ascii=False),
                                        encoding="utf-8")
    except Exception:
        logger.debug("_remove_from_router fejlede %s/%s", provider, model, exc_info=True)


def _observe_central(payload: dict) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "provider_health", **payload})
    except Exception:
        pass


def check_and_heal(*, down_providers: list[str]) -> bool:
    """3+ providers nede samtidig → eskalér til Bjørn. Returnér True hvis eskaleret."""
    if len(down_providers) >= _ESCALATE_THRESHOLD:
        _notify_bjorn(
            f"⚠️ {len(down_providers)} providers nede samtidig: "
            f"{', '.join(down_providers)}. Cheap lane er presset.")
        _observe_central({"event": "multi_provider_down", "count": len(down_providers),
                          "providers": down_providers})
        return True
    return False


def _current_down_providers() -> list[str]:
    """Providers der lige nu er uopnåelige (proaktiv ping). Self-safe → []."""
    try:
        from core.services.provider_health_check import health_check_all_providers
        snap = health_check_all_providers()
        return [str(p) for p in (snap.get("unreachable") or [])]
    except Exception:
        return []


def tick_provider_self_heal_daemon() -> dict[str, object]:
    """Fase C daemon-tick: 60min self-heal. Samler nede providers og eskalerer til Bjørn
    hvis 3+ er nede samtidig. Self-throttler internt; self-safe (vælter aldrig heartbeaten).
    Model-drift (404) håndteres reaktivt via handle_model_drift, ikke på denne timer."""
    global _last_heal_at
    from datetime import datetime, timedelta, UTC
    now = datetime.now(UTC)
    if _last_heal_at is not None and (now - _last_heal_at) < timedelta(minutes=_CADENCE_MINUTES):
        return {"skipped": "cadence"}
    _last_heal_at = now
    down = _current_down_providers()
    escalated = check_and_heal(down_providers=down)
    return {"down_count": len(down), "escalated": escalated}


def handle_model_drift(*, provider: str, model: str, status_code: int) -> bool:
    """404 på en model = model-drift → fjern auto fra pool + log. Returnér True hvis fjernet."""
    if status_code == 404:
        _remove_from_router(provider, model)
        _observe_central({"event": "model_drift_removed", "provider": provider,
                          "model": model})
        logger.info("provider_self_heal: model-drift %s/%s (404) fjernet fra pool",
                    provider, model)
        return True
    return False
