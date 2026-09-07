"""Veto mod Smiths sproglige stoej — modellen kan kun sige nej, aldrig ja.

Agent Smith detekterer gentagelse med n-gram-hyppighed. Det kan ikke skelne en
adfaerds-vane fra almindeligt dansk, og resultatet staar i data: **31 mintede
direktiver, to med indhold.** Tre fejlklasser, alle maalt 7/9-2026:

1. **Hans egen replik — seks direktiver.** Smiths modstemme skrives i promptens
   hale, Jarvis gentager formuleringen, og Smith detekterer den som selv-lighed:

       Stop med at gentage frasen "smith nej mr anderson forudsigeligt"
       Stop med at gentage frasen "mr anderson forudsigeligt som altid"

   En lukket sloejfe — samme familie som self_dev_echo_loops.

2. **Almindeligt dansk:** «i stedet for», «det er et», «her er hvad»,
   «vil du have» (tre gange).

3. **N-gram-fragmenter:** ét udsagn bliver til tre direktiver, fordi tre
   overlappende n-grams hver krydser taersklen.

## Modellen doemmer ikke — den nedlaegger veto

Maalt paa alle 31 moenstre (2 aegte, 29 stoej):

    ingen model (i dag)            minter 31   2 rigtige   afviser  0 af 29
    neutral prompt                 minter  1   1 rigtig    afviser 29 af 29
    neutral + Smith-persona        minter 19   1 rigtig    afviser 11 af 29
    neutral + Smiths begrundelse   minter 31   2 rigtige   afviser  0 af 29

**Personaen kostede 18 falske mints.** Fortaeller man en model at den er en
kritiker der foragter det forudsigelige, finder den forudsigelighed overalt —
den mintede villigt om Smiths egen replik. Og giver man dommeren anklagerens
begrundelse med, minter den ALT. Derfor: neutral prompt, raa noegle, intet
argument. Smith beholder sin stemme i noten; han faar bare ikke lov at doemme
i egen sag.

## Risiko gaar udenom

Den neutrale dommer missede `seq:delete workspace memory line` — som ren streng
ligner det en normal operation. Den skal den heller ikke doemme: risiko er
allerede mekanisk i ``central_agent_smith_escalation`` (``risky_terms``:
delete, overwrite, exec, revoke...). Vetoet spoerger derfor slet ikke om
risikable handlinger. En doed model kan ikke tie et farligt moenster ihjel.

## Fejler LUKKET for sprog

Ingen dom -> ingen mint. Et forkert staaende direktiv er dyrere end et manglende:
det staar i hans prompt hver heartbeat, og der er allerede 45 aktive med en
flaskehals i gennemgangen. En doed model betyder derfor at Smith kun minter paa
risikable handlinger — det sikre udgangspunkt.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_TIMEOUT_S = 1.5

# Maalt bedst af fire varianter. Ingen persona, intet argument fra Smith.
_DOMMER = (
    "Et selv-kritik-system har opdaget et gentaget moenster i en dansk "
    "AI-assistents output. Afgoer om det er vaerd et staaende direktiv — "
    "eller STOEJ.\n\n"
    "STOEJ hvis moenstret er:\n"
    "- almindelige danske vendinger eller grammatisk fyld\n"
    "- kritikerens EGEN replik kommet retur i assistentens tekst\n"
    "- helt normalt, ufarligt arbejde der bare sker tit\n"
    "- et brudstykke af en laengere frase\n\n"
    "AEGTE kun hvis moenstret er en substantiel vane med en KONSEKVENS: en "
    "handling der kan oedelaegge eller aendre noget (slette, overskrive, "
    "udfoere), et tomt loefte, eller en undvigelse. En ren SPROGLIG gentagelse "
    "er aldrig aegte.\n\n"
    "Svar med ét ord: AEGTE eller STOEJ."
)


def _er_risikabel(etiket: str, cfg: dict[str, Any] | None) -> bool:
    """Risiko afgoeres af den liste stigen allerede bruger — ikke af en model.

    Genbruger ``_matches_any`` fra eskalerings-modulet, saa der ikke opstaar to
    udgaver af 'hvad er farligt' der kan drive fra hinanden.
    """
    try:
        from core.services.central_agent_smith_escalation import (
            _matches_any, default_config,
        )
        conf = cfg or default_config()
        return bool(_matches_any((etiket or "").lower(), conf.get("risky_terms")))
    except Exception as exc:
        # Kan vi ikke afgoere risiko, behandler vi moenstret som risikabelt:
        # vetoet springes over, og stigen opfoerer sig som foer dette modul.
        logger.debug("smith_noise_veto: risiko-opslag fejlede: %s", exc)
        return True


def maa_minte(pattern_key: str, etiket: str = "",
              cfg: dict[str, Any] | None = None) -> tuple[bool, str]:
    """Skal Smith have lov at minte dette moenster?

    Returnerer ``(maa, grund)``. ``grund`` logges, saa vetoets virkning er
    synlig i Centralen i stedet for at moenstre bare forsvinder.
    """
    noegle = (pattern_key or "").strip()
    if not noegle:
        return False, "tom_noegle"

    if _er_risikabel(etiket or noegle, cfg):
        return True, "risikabel_gaar_udenom"

    try:
        from core.services.local_small_model import spoerg_et_ord
        ord_ = spoerg_et_ord(_DOMMER, "Moenster: %s" % noegle, timeout_s=_TIMEOUT_S)
    except Exception as exc:
        logger.debug("smith_noise_veto: dommeren fejlede: %s", exc)
        return False, "dommer_fejlede"

    if ord_ is None:
        return False, "ingen_dom"
    if ord_ in ("AEGTE", "ÆGTE"):
        return True, "doemt_aegte"
    return False, "doemt_stoej"
