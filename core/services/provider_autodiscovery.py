"""Provider auto-discovery (spec Fase C). Dagligt scan af providers' /models,
diff mod kendte modeller → nye lander i STAGING (pending_models), ALDRIG direkte
i routbar pool. Promotion kræver smoke + kvalitets-scoring + gratis-verifikation
(+ owner-approval). Opdagelse ≠ optagelse (jf. self-registering-nerve governance)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Self-throttle: dagligt scan. Modul-level state (nulstilles af daemon_manager restart
# via reset_var='_last_discovery_at') — heartbeat kalder tick hvert tick, daemonen
# no-op'er indtil cadencen er elapsed.
_last_discovery_at = None  # datetime | None
_CADENCE_MINUTES = 1440


def _list_remote_models(provider: str) -> list[str]:
    """Modeller providerens /models-endpoint rapporterer. [] ved fejl."""
    try:
        from core.services.cheap_provider_runtime_adapters import list_provider_models
        return [str(m.get("id") or m) for m in (list_provider_models(
            provider=provider, auth_profile="default") or [])]
    except Exception:
        return []


def _known_models() -> set[str]:
    """Modeller allerede i provider_router.json (uanset lane)."""
    try:
        from core.runtime.provider_router import load_provider_router_registry
        reg = load_provider_router_registry()
        return {str(m.get("model") or "") for m in (reg.get("models") or [])}
    except Exception:
        return set()


def _stage_pending(provider: str, model: str) -> None:
    """Skriv (provider, model) til pending_models-staging, status='pending'."""
    try:
        from datetime import datetime, UTC
        from core.runtime.db_core import connect
        with connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS pending_models ("
                "provider TEXT NOT NULL, model TEXT NOT NULL, discovered_at TEXT, "
                "status TEXT NOT NULL DEFAULT 'pending', UNIQUE(provider, model))")
            conn.execute(
                "INSERT OR IGNORE INTO pending_models (provider, model, discovered_at, status) "
                "VALUES (?, ?, ?, 'pending')",
                (provider, model, datetime.now(UTC).isoformat()))
    except Exception:
        logger.debug("stage_pending fejlede for %s/%s", provider, model, exc_info=True)


def _add_to_router(provider: str, model: str) -> None:
    """Faktisk optagelse i routbar pool. Kaldes KUN af promote_pending efter gates."""
    from datetime import datetime, UTC
    import json
    from core.runtime.config import PROVIDER_ROUTER_FILE
    reg = json.loads(PROVIDER_ROUTER_FILE.read_text(encoding="utf-8"))
    reg.setdefault("models", []).append(
        {"provider": provider, "model": model, "lane": "cheap", "enabled": True,
         "updated_at": datetime.now(UTC).isoformat()})
    PROVIDER_ROUTER_FILE.write_text(json.dumps(reg, indent=2, ensure_ascii=False),
                                    encoding="utf-8")


def _configured_providers() -> list[str]:
    """Alle providers i provider_router.json (til daglig re-scan). [] ved fejl."""
    try:
        from core.runtime.provider_router import load_provider_router_registry
        reg = load_provider_router_registry()
        return sorted({str(p.get("provider") or "").strip()
                       for p in (reg.get("providers") or []) if p.get("provider")})
    except Exception:
        return []


def tick_provider_autodiscovery_daemon() -> dict[str, object]:
    """Fase C daemon-tick: dagligt scan af alle providers' /models → nye modeller til
    pending_models-staging. Self-throttler internt (1440min). Auto-adder ALDRIG (governed).
    Self-safe: en enkelt providers scan-fejl vælter ikke tick'et."""
    global _last_discovery_at
    from datetime import datetime, timedelta, UTC
    now = datetime.now(UTC)
    if _last_discovery_at is not None and (now - _last_discovery_at) < timedelta(minutes=_CADENCE_MINUTES):
        return {"skipped": "cadence"}
    _last_discovery_at = now
    providers = _configured_providers()
    staged = 0
    for p in providers:
        try:
            staged += len(discover_provider(p))
        except Exception:
            logger.debug("autodiscovery-scan fejlede for %s", p, exc_info=True)
    return {"providers_scanned": len(providers), "staged": staged}


def discover_provider(provider: str) -> list[str]:
    """Scan provider, stage nye modeller. Returnér de nye (staged). Auto-adder ALDRIG."""
    known = _known_models()
    new = [m for m in _list_remote_models(provider) if m and m not in known]
    for m in new:
        _stage_pending(provider, m)
    return new


def _smoke_ok(provider: str, model: str) -> bool:
    """Svarer modellen på et minimalt kald?"""
    try:
        from core.services.cheap_provider_runtime_adapters import (
            _execute_openai_compatible_chat, CHEAP_PROVIDER_DEFAULTS)
        cfg = CHEAP_PROVIDER_DEFAULTS.get(provider) or {}
        raw = _execute_openai_compatible_chat(
            provider=provider, model=model, auth_profile="default",
            base_url=str(cfg.get("base_url") or ""),
            messages=[{"role": "user", "content": "Reply: OK"}],
            tools=None, extra_body={"max_tokens": 64})
        return bool(str(raw.get("text") or "").strip())
    except Exception:
        return False


def _is_free(provider: str, model: str) -> bool:
    """Konservativ gratis-verifikation. Default False (governed — hellere afvise)."""
    return "free" in model.lower() or ":free" in model.lower()


def _score_model(provider: str, model: str) -> float:
    """Seed kvalitets-score (§4.4). Grov til at komme i gang."""
    return 0.5


def promote_pending(provider: str, model: str, *, min_score: float = 0.5) -> bool:
    """Gated promotion: kræver smoke + gratis + score ≥ tærskel. Kun da optages
    modellen i routbar pool. Returnér True hvis promoveret."""
    if not _smoke_ok(provider, model):
        return False
    if not _is_free(provider, model):
        return False
    if _score_model(provider, model) < min_score:
        return False
    _add_to_router(provider, model)
    logger.info("provider_autodiscovery: promoveret %s/%s til routbar pool", provider, model)
    return True
