"""Aldrig-tør-bund for cheap lane (spec §5.5 Fund 4).

Begge routing-subsystemer (cheap_lane_balancer + cheap_provider_runtime_selection)
falder hertil i stedet for at ``raise`` når poolen er udmattet. ``attempt_floor``
prøver en konfigurerbar kæde af altid-sunde targets; hvis ALT fejler returneres et
typet degraderet resultat — ALDRIG en exception. Kalderen får altid noget den kan
håndtere, så en tom pool aldrig crasher inderliv/agenter/synlig Jarvis."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default-kæde: KEYLESS gratis-providere (pollinations → ovhcloud). Bjørn 16.jul:
# bunden må ALDRIG trække fra den betalte deepseek-API — heller ikke som nød-bund.
# Agent/cheap/inder-lanerne router allerede til gratis-poolen først (central_route);
# floor'en er kun sidste-udvej når HELE poolen er nede, og selv da skal den være GRATIS.
# pollinations valgt som primær (keyless → ingen profil-afhængighed, altid-reachable,
# live-verificeret PONG gennem floor-stien); ovhcloud som keyless backup. Hvis begge er
# nede → typet degraderet svar (aldrig exception, aldrig en overraskelses-regning).
# Overstyres af config-nøgle ``cheap_lane_floor_targets`` (liste af [provider, model]).
_DEFAULT_FLOOR: list[tuple[str, str]] = [("pollinations", "openai"), ("ovhcloud", "Qwen3.5-9B")]


def floor_targets() -> list[tuple[str, str]]:
    """Bund-kæden, config-overstyrbar. Self-safe → default ved fejl."""
    try:
        from core.runtime.settings import load_settings
        raw = getattr(load_settings(), "cheap_lane_floor_targets", None)
        if isinstance(raw, list) and raw:
            out = [(str(p), str(m)) for p, m in raw if p and m]
            if out:
                return out
    except Exception:
        logger.debug("floor_targets: config-læsning fejlede, bruger default", exc_info=True)
    return list(_DEFAULT_FLOOR)


def floor_result(*, lane: str, reason: str, provider: str = "floor",
                 model: str = "", text: str = "", status: str = "degraded",
                 extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Typet resultat der matcher pool-outputtets form. status='degraded' = tom bund."""
    body: dict[str, Any] = {
        "status": status, "lane": lane, "provider": provider, "model": model,
        "text": text, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
        "floor_reason": reason, "is_floor": True,
    }
    if extra:
        body.update(extra)
    return body


def _execute_floor_target(*, provider: str, model: str, message: str,
                          lane: str) -> dict[str, Any]:
    """Kør ét bund-target gennem den eksisterende adapter. Kan rejse — indkapsles
    af attempt_floor."""
    from core.services.cheap_provider_runtime_adapters import (
        _execute_openai_compatible_chat, CHEAP_PROVIDER_DEFAULTS)
    cfg = CHEAP_PROVIDER_DEFAULTS.get(provider) or {}
    raw = _execute_openai_compatible_chat(
        provider=provider, model=model, auth_profile="default",
        base_url=str(cfg.get("base_url") or ""),
        messages=[{"role": "user", "content": message}],
        tools=None, extra_body={"max_tokens": 512},
    )
    return {"status": "ok", "provider": provider, "model": model,
            "lane": lane, "text": str(raw.get("text") or ""),
            "input_tokens": int(raw.get("input_tokens") or 0),
            "output_tokens": int(raw.get("output_tokens") or 0),
            "cost_usd": float(raw.get("cost_usd") or 0.0), "is_floor": True}


def attempt_floor(*, message: str, lane: str, reason: str) -> dict[str, Any]:
    """Prøv bund-kæden i rækkefølge. Første ikke-tomme svar vinder. Hvis ALT
    fejler/tomt → degraderet resultat. Rejser ALDRIG."""
    for provider, model in floor_targets():
        try:
            r = _execute_floor_target(provider=provider, model=model,
                                      message=message, lane=lane)
            if str(r.get("text") or "").strip():
                logger.info("cheap_lane_floor: bund holdt via %s/%s (reason=%s)",
                            provider, model, reason)
                return r
        except Exception:
            logger.debug("cheap_lane_floor: bund-target %s/%s fejlede", provider, model,
                         exc_info=True)
    logger.warning("cheap_lane_floor: HELE bunden tør (reason=%s) → degraderet svar", reason)
    return floor_result(lane=lane, reason=reason)
