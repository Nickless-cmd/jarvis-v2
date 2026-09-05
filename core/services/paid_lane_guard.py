"""Vagt: kun Bjørns egen lane må ramme den betalte DeepSeek-API (2026-09-05).

Bjørns regel fra 16. juli står i `settings.py`: den betalte deepseek.com-API er
KUN til visible lane; baggrund kører på ollama. Men lane-opslaget sker ikke i
settings — det sker i `~/.jarvis-v2/config/provider_router.json`. Dér pegede
`inner_enrichment` stadig på `https://api.deepseek.com/v1`, og
`daemon_llm.quality_daemon_llm_call` resolver netop den lane. Resultat: 281
betalte kald på syv dage til internt arbejde. Reglen var brudt i omkring syv
uger uden at nogen opdagede det, fordi de to steder sagde hver sit.

Denne vagt lukker hullet ved at spørge det sted der faktisk bestemmer —
`resolve_provider_router_target` — og råbe op når en lane uden for
`_ALLOWED_PAID_LANES` peger på en betalt vært. Den RETTER intet: et lane-valg er
en driftsbeslutning, ikke noget en vagt skal tage. Den gør bruddet synligt i
Centralen og i loggen, så det ikke kan ligge uset i syv uger igen.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Lanes der MÅ koste penge: Bjørns egne ture.
_ALLOWED_PAID_LANES = frozenset({"visible", "primary"})
# Værter vi betaler for pr. token. Ollama-cloud og de gratis lanes er ikke her.
_PAID_HOSTS = frozenset({"api.deepseek.com"})
# Lanes vi overhovedet spørger til (jf. provider_router._normalize_lane).
_LANES = ("visible", "cheap", "coding", "premium", "local", "inner_enrichment")


def _host(url: str) -> str:
    try:
        return (urlparse(str(url or "")).hostname or "").lower()
    except Exception:
        return ""


def is_paid(base_url: str) -> bool:
    return _host(base_url) in _PAID_HOSTS


def audit_paid_lanes() -> list[dict[str, Any]]:
    """Hvilke lanes peger på en betalt vært uden at måtte?

    Returnerer én post pr. brud. Tom liste = reglen holder. Self-safe: en lane
    der ikke kan resolves springes over frem for at vælte kaldet.
    """
    from core.runtime.provider_router import resolve_provider_router_target

    leaks: list[dict[str, Any]] = []
    for lane in _LANES:
        if lane in _ALLOWED_PAID_LANES:
            continue
        try:
            target = resolve_provider_router_target(lane=lane) or {}
        except Exception as exc:
            logger.debug("paid_lane_guard: kunne ikke resolve %s: %s", lane, exc)
            continue
        base_url = str(target.get("base_url") or "")
        if is_paid(base_url):
            leaks.append({
                "lane": lane,
                "provider": str(target.get("provider") or ""),
                "model": str(target.get("model") or ""),
                "host": _host(base_url),
            })
    return leaks


def check_paid_lanes() -> dict[str, Any]:
    """Kør vagten: log + Central-nerve ved brud. Retter aldrig noget selv."""
    try:
        leaks = audit_paid_lanes()
    except Exception as exc:
        logger.debug("paid_lane_guard: audit fejlede: %s", exc)
        return {"checked": False, "leaks": []}
    if leaks:
        logger.warning(
            "BETALT-LANE-BRUD: %s peger paa en betalt vaert. Bjoerns regel er at "
            "kun hans egne ture (visible/primary) maa koste penge — baggrund "
            "koerer paa ollama. Ret i ~/.jarvis-v2/config/provider_router.json.",
            ", ".join("%s -> %s/%s" % (x["lane"], x["provider"], x["model"]) for x in leaks),
        )
        try:
            from core.services.central_core import central
            central().observe({
                "cluster": "cost", "nerve": "paid_lane_leak",
                "count": len(leaks), "lanes": [x["lane"] for x in leaks],
                "detail": leaks[:4],
            })
        except Exception:
            pass
    return {"checked": True, "leaks": leaks}


def build_paid_lane_guard_surface() -> dict[str, Any]:
    leaks = audit_paid_lanes()
    return {
        "active": True,
        "ok": not leaks,
        "leaks": leaks,
        "summary": (
            "kun hans egne ture koster penge"
            if not leaks
            else "%d lane(s) paa betalt vaert: %s" % (
                len(leaks), ", ".join(x["lane"] for x in leaks))
        ),
    }
