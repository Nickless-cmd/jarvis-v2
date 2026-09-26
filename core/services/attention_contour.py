"""Attention Contour — shape of attention.

HVORFOR FORMEN VAR ET TERNINGKAST (rettet 26/9-2026)

Hele modulet var fire linjer omkring:

    def get_attention_shape() -> str:
        return random.choice(_shapes)

Fem poetiske strenge, ét kast. Og formen blev brugt: den injiceres i
hjerteslaget (`_run_heartbeat_tick_locked`) og vises i Centralen
(`mission_control_common._mc_runtime_uncached`).

Værre endnu kaldte fladen terningen TRE gange i samme dict — én gang til
`current_shape`, én gang til `summary`, og én gang inde i `description`. Målt:
**20 af 20 flader modsagde sig selv.** Ét svar kunne sige «kristalliseret som
is», «kaotisk som storm» og «spredt som stjerner» på samme tid.

Ordene er beholdt — de er hans. Det er kastet der er væk. Formen udledes nu af
to kilder der allerede måler noget:

- `thought_thread`: holder han en tråd, hvor lang, og hvor mange afbrydelser
- `temporal_rhythm`: pulsen, udregnet af initiativer, værktøjsrate, chat-rate
  og eventbus-dybde

Målt på CT105 26/9-2026: 74 tanker over 133 minutter med 21 afbrydelser, puls
0,3 («breathing») → «bølgende som tidevand». Han BÆRER en tråd, men den bliver
brudt — og det er en anden form end både laseren og stormen.

Grundlaget gemmes ved siden af ordet, så et ord altid kan føres tilbage til
sit tal. Samme regel som `body_memory._fornemmelse`.

`_current_shape` er væk: den blev sat én gang på modulniveau og aldrig læst.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Hans egne fem ord. Rækkefølgen er fra mest spredt til mest samlet, bortset
#: fra stormen, som er sin egen slags.
SPREDT = "spredt som stjerner"
LASER = "fokuseret som en laser"
TIDEVAND = "bølgende som tidevand"
IS = "kristalliseret som is"
STORM = "kaotisk som storm"

_shapes = [SPREDT, LASER, TIDEVAND, IS, STORM]

#: Over dette er pulsen «racing» i `temporal_rhythm`s egen skala.
_RACENDE_PULS = 1.4
#: Under dette er den «breathing» — samme tal som modulet selv bruger.
_ROLIG_PULS = 0.5
#: Afbrydelser pr. båret tanke. 0,15 er valgt så den MÅLTE tilstand (21/74 =
#: 0,28) lander i tidevandet og ikke i isen; en tråd der brydes hver fjerde
#: tanke er ikke krystalliseret.
_FAA_AFBRYDELSER = 0.15
#: Under dette er tråden for kort til at kalde noget for fokus.
_MINDSTE_TRAAD = 5


def _maal() -> tuple[dict[str, Any], dict[str, Any]]:
    """(tråd, rytme) — tomme dicts når kilderne ikke kan læses."""
    traad: dict[str, Any] = {}
    rytme: dict[str, Any] = {}
    try:
        from core.services.thought_thread import get_current_thread
        traad = get_current_thread() or {}
    except Exception as exc:
        logger.debug("attention_contour: tråden kunne ikke læses: %s", exc)
    try:
        from core.services.temporal_rhythm import get_current_rhythm
        rytme = get_current_rhythm() or {}
    except Exception as exc:
        logger.debug("attention_contour: rytmen kunne ikke læses: %s", exc)
    return traad, rytme


def _form(traad: dict[str, Any], rytme: dict[str, Any]) -> tuple[str, str]:
    """(ord, grundlag) — ordet skal kunne føres tilbage til sit tal."""
    baerer = int(traad.get("carrying_count") or 0)
    afbrydelser = int(traad.get("interruption_count") or 0)
    holder = bool(traad.get("active")) and baerer > 0
    try:
        puls = float(rytme.get("pulse_rate") or 0.0)
    except (TypeError, ValueError):
        puls = 0.0
    tempo = str(rytme.get("subjective_time_pressure") or "")

    if not holder:
        return SPREDT, (f"ingen tråd holdes (puls={puls:.2f})" if rytme
                        else "ingen tråd holdes, ingen rytme målt")

    andel = afbrydelser / max(1, baerer)
    if (tempo == "racing" or puls >= _RACENDE_PULS) and afbrydelser:
        return STORM, (f"puls={puls:.2f} ({tempo}) og {afbrydelser} afbrydelser "
                       f"på {baerer} tanker")
    if afbrydelser == 0 and baerer >= _MINDSTE_TRAAD:
        return LASER, f"{baerer} tanker uden en eneste afbrydelse"
    if andel < _FAA_AFBRYDELSER and puls < _ROLIG_PULS:
        return IS, (f"{afbrydelser}/{baerer} afbrydelser ({andel:.0%}) "
                    f"ved puls={puls:.2f}")
    return TIDEVAND, (f"{afbrydelser}/{baerer} afbrydelser ({andel:.0%}) — "
                      f"tråden bæres, men brydes")


def get_attention_shape() -> str:
    """Formen lige nu. Samme input giver samme svar — hver gang."""
    return _form(*_maal())[0]


def describe_attention() -> str:
    return f"Min opmærksomhed er {get_attention_shape()} lige nu"


def format_attention_for_prompt() -> str:
    return f"[OPMÆRKSOMHED: {describe_attention()}]"


def build_attention_contour_surface() -> dict[str, Any]:
    # ÉN udledning, ikke tre. Fladen kaldte før `get_attention_shape()` tre
    # gange og kunne modsige sig selv inden for ét svar (målt: 20 af 20).
    traad, rytme = _maal()
    ord_, grundlag = _form(traad, rytme)
    return {
        "active": True,
        "current_shape": ord_,
        "grundlag": grundlag,
        "all_shapes": _shapes,
        "description": f"Min opmærksomhed er {ord_} lige nu",
        "summary": ord_,
    }
