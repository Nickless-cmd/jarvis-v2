"""Fastlås modellen pr. session, så prompt-præfikset holder (2026-10-03).

Bjørn: «stortset alle mine beskeder kolder starter». Målt på CT105 samme dag.

## Målingen

Runderne INDE i en tur ligger på 95-96,5 % cache-hit. Den FØRSTE kald i hver
tur — åbneren — ligger på 50-56 %. Og hit-tallene gentager sig præcist på
tværs af ture med vidt forskellig størrelse:

    16.512 (×2)   19.584 (×4)   10.112 (×2)      input 41k-126k tokens

Et fast præfiks matcher, resten aldrig. Det er samme signatur som
`session_tool_pin` blev bygget mod 5/9: «`cache_hit_tokens` fryser på
6.400-8.320 — nøjagtig systembeskedens længde — mens `cache_miss_tokens`
vokser lineært med samtalen.»

## Årsagen

Tre modeller betjente nabo-ture i samme samtale:

    12:28  deepseek-v4-flash      12:21  deepseek-v4-flash
    12:25  deepseek-flash         12:19  glm-5.2:cloud
    12:23  deepseek-flash         12:18  deepseek-v4-flash
    12:23  deepseek-v4-flash      11:57  deepseek-flash

DeepSeek cacher **per model**, og glm er en anden udbyder, så to modeller
deler ingen cache uanset hvor byte-stabil prompten er. Dertil står modellens
navn ved tegn ~80 i systembeskeden («You are running as model: X via provider:
Y»), så selv teksten afviger med det samme.

Effekten er målt direkte: timer med ÉN model gav 95,1 % og 96,5 % hit; timer
hvor to blev blandet faldt til 50,4 %.

## Løsningen — samme form som værktøjs-låsen

Ikke at fratage routeren sit valg, men at lade den vælge ÉN gang pr. session:

* første tur router som før, og (udbyder, model) gemmes;
* efterfølgende ture genbruger det, så præfikset rammer samme cache;
* låsen nulstilles ved compaction, hvor historikken alligevel skrives om og
  cachen brydes — så routeren får frisk indflydelse uden at koste noget;
* kan den låste model ikke bruges, falder kalderen tilbage og **re-pinner**.
  En død model må ikke kile sessionen fast; det er hele grunden til at
  `release` findes.

Kill-switch: `settings.session_model_pin_enabled = False` → routeren vælger pr.
tur igen, præcis som før.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_KEY_PREFIX = "session_model_pin:"


def pin_enabled() -> bool:
    """Er låsen slået til? Fail-safe: enhver fejl → til (den nye adfærd)."""
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "session_model_pin_enabled", True))
    except Exception:  # kan indstillingen ikke laeses, gaelder den NYE adfaerd
        # — se docstringen. Den modsatte retning ville goere en
        # konfigurations-fejl til en tavs regression tilbage til kolde aabnere.
        return True


def _key(session_id: str) -> str:
    return f"{_KEY_PREFIX}{str(session_id or '').strip()}"


def _compact_epoch(session_id: str) -> int:
    """Compaction-markøren. Skifter den, er historikken skrevet om og cachen
    brudt alligevel — så må routeren gerne vælge forfra. Samme kilde som
    `session_tool_pin`, så de to låse slipper på samme tidspunkt."""
    try:
        from core.context.tool_result_lifecycle import latest_compact_marker_id
        return int(latest_compact_marker_id(str(session_id or "")) or 0)
    except Exception:  # ukendt epoke -> 0, som er den samme for alle. Laasen
        # holder da paa tvaers af en compaction vi ikke kunne se — mindre godt
        # end at slippe den, men bedre end at kaste i prompt-stien.
        return 0


def _state_get(session_id: str) -> dict[str, Any]:
    try:
        from core.runtime.db import get_runtime_state_value
        raw = get_runtime_state_value(_key(session_id), None)
        return dict(raw) if isinstance(raw, dict) else {}
    except Exception:  # kan laasen ikke laeses, er sessionen ULAAST — routeren
        # vaelger da som foer. At kaste her ville vaelte turen for en cache-
        # optimering, og det er aldrig den rigtige vej rundt.
        return {}


def _state_set(session_id: str, payload: dict[str, Any] | None) -> None:
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(_key(session_id), payload)
    except Exception as exc:
        logger.debug("session_model_pin: kunne ikke gemme laas: %s", exc)


def get_pinned(session_id: str) -> tuple[str, str] | None:
    """Det låste (udbyder, model) — ``None`` når intet er låst, eller når
    compaction har flyttet epoken siden låsen blev sat."""
    sid = str(session_id or "").strip()
    if not sid or not pin_enabled():
        return None
    state = _state_get(sid)
    provider = str(state.get("provider") or "").strip()
    model = str(state.get("model") or "").strip()
    if not provider or not model:
        return None
    if int(state.get("epoch") or 0) != _compact_epoch(sid):
        return None
    return provider, model


def pin(session_id: str, provider: str, model: str) -> tuple[str, str] | None:
    """Lås modellen for sessionen. Returnerer det der FAKTISK blev låst.

    ``None`` når intet blev gemt — uden session-id, uden et helt par, eller med
    kill-switchen slået fra. At returnere parret alligevel ville sige «dette er
    laast» om noget der ikke blev skrevet, og kalderen kan ikke skelne de to.
    """
    sid = str(session_id or "").strip()
    p = str(provider or "").strip()
    m = str(model or "").strip()
    if not sid or not p or not m or not pin_enabled():
        return None
    _state_set(sid, {"provider": p, "model": m, "epoch": _compact_epoch(sid)})
    return p, m


def resolve(
    session_id: str, provider: str, model: str,
) -> tuple[str, str, str]:
    """Modellen turen skal bruge, og hvor valget kom fra.

    Returnerer ``(provider, model, kilde)`` hvor kilde er ``"pin"`` når låsen
    afgjorde det og ``"router"`` når routerens valg blev låst nu. Kalderen kan
    logge kilden, så man kan se om låsen faktisk bider.

    Routerens valg vinder når der ikke er noget låst — ellers ville første tur
    i en session ikke kunne sætte låsen.
    """
    sid = str(session_id or "").strip()
    p = str(provider or "").strip()
    m = str(model or "").strip()
    laast = get_pinned(sid)
    if laast is not None:
        return laast[0], laast[1], "pin"
    if p and m:
        pin(sid, p, m)
        return p, m, "router"
    return p, m, "router"


def release(session_id: str, *, grund: str = "") -> None:
    """Slip låsen — kaldes når den låste model ikke kunne bruges.

    Uden denne vej ville en model der er nede kile sessionen fast: hver tur
    ville vælge den igen, fejle, og falde tilbage uden at låsen nogensinde
    ændrede sig. Næste tur låser så routerens nye valg.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return
    _state_set(sid, None)
    logger.info("session_model_pin: laas sluppet for %s%s",
                sid, f" ({grund})" if grund else "")
