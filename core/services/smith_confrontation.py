"""Trin 3: Smith standser handlingen i realtid og tvinger et nyt valg.

Bjoern 7/9-2026: «trin 3 skal vaere korrektion, det skal tvinge adfaerdsaendring
NU, og det maa aldrig cutte et run — tving ham til at aendre adfaerd aktivt
realtime.»

## Hvad der var galt

Stigen havde tre trin, men alle tre var TEKST i stigende styrke:

    trin 1  kommentér   en linje i promptens hale
    trin 2  bind        en behavioral_decision der surfacer ved heartbeat
    trin 3  konfrontér  en advarsel i raesonnementet

Og trin 3 kunne ikke engang tale. ``_execute_arm_confront`` skrev en staaende
ordre med ``match_key`` = moensterets label, mens modtageren gjorde
``if mk in classes`` mod prefilterens fem faste klassenavne
(cross_user_share, decision_gate, fact_gate, verification, veto). En frase kan
aldrig vaere i det saet. Ti ordrer var oprettet; ingen har nogensinde kunnet
matche. Og verdicten var YELLOW/warn — tekst, ikke tvang.

## Hvad der sker nu

Maskineriet til aegte korrektion fandtes allerede i ``visible_runs``: en RED
verdict fra interceptoren toemmer rundens ventende tool-kald, saa executoren
koerer nul vaerktoejer, og modellen **re-raesonnerer med korrektionen** —
runnet fortsaetter, det annulleres aldrig. Det er praecis det Bjoern beder om.
Det manglede kun nogen der kunne udloese det.

Denne detektor matcher moenstre paa **TRIN 3** mod de tool-kald der er paa vej,
og returnerer RED med en korrektion der navngiver loeftet. Han bliver ikke
stoppet — han bliver tvunget til at vaelge om.

## Tre vaern, og hvorfor de er der

**Bash er helt undtaget.** ``bash_session`` og ``operator_bash_session`` er
Bjoerns vej udenom systemet, og de maa ikke roeres foer gaten er stabil og uden
tavse fejl. Smith faar ingen magt over dem.

**Loft paa antal hold pr. run.** Uden det kunne han re-raesonnere ind i det
samme kald igen og igen, og runnet ville staa stille — hvilket i praksis ER at
cutte det. Efter ``_MAX_HOLD`` gange slipper kaldet igennem; korrektionen staar
stadig i konteksten, saa han ved hvorfor.

**Kun handlings-moenstre (``seq:``).** ``behaviour:``-moenstre som «tomme
loefter» handler om at love uden at kalde noget — der ER intet tool-kald at
holde, og ``hollow_promise_guard`` daekker dem allerede. At holde dér ville
vaere at bygge det samme vaern to gange.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

RUNG_CONFRONT = 3
_MAX_HOLD = 2
_HOLD_TTL_S = 3600

# Substreng-match, lowercase. Undtagelsen er bevidst bred: en fremtidig
# bash-variant skal vaere undtaget fra foerste dag, ikke naar nogen opdager det.
_FRITAGET = ("bash", "shell", "terminal")

_ORD = re.compile(r"[a-zA-Z0-9æøåÆØÅ]+")
# Ord der findes i næsten alle vaerktoejsnavne og derfor ikke skiller noget.
_SVAGE = frozenset({"tool", "run", "get", "set", "the", "and", "med", "til"})


def _ord_i(tekst: str) -> set[str]:
    return {w.lower() for w in _ORD.findall(tekst or "")} - _SVAGE


def _er_fritaget(navn: str) -> bool:
    lav = (navn or "").lower()
    return any(f in lav for f in _FRITAGET)


def _rammer(label: str, tool_navn: str, argumenter: str = "") -> bool:
    """Peger dette tool-kald paa moensteret?

    Kraever at MINDST 60 % af labelens indholdsord staar i kaldet. Ratio frem
    for ordliste, af samme grund som i ``_is_self_bound``: en ordliste ville
    bare udskyde den naeste formulering. Taersklen er sat hoejt fordi et falsk
    hold koster en runde af hans tid — der er raad til at misse et, ikke til at
    stoppe ham i noget rigtigt.
    """
    lab = _ord_i(label.split(":", 1)[-1])
    if not lab:
        return False
    kald = _ord_i(tool_navn) | _ord_i(argumenter[:400])
    if not kald:
        return False
    return (len(lab & kald) / len(lab)) >= 0.6


def _hold_taeller(run_id: str, noegle: str, *, laes_kun: bool = False) -> int:
    """Hvor mange gange har vi holdt dette moenster i dette run?"""
    if not run_id:
        return 0
    cache_noegle = "smith_confront:%s:%s" % (run_id, noegle)
    try:
        from core.services import shared_cache
        n = int(shared_cache.get(cache_noegle) or 0)
        if not laes_kun:
            shared_cache.set(cache_noegle, n + 1, ttl_seconds=_HOLD_TTL_S)
        return n
    except Exception as exc:
        logger.debug("smith_confrontation: taeller utilgaengelig: %s", exc)
        # Kan vi ikke taelle, kan vi heller ikke garantere loftet → hold ikke.
        return _MAX_HOLD


def _trin3_moenstre() -> list[dict[str, Any]]:
    try:
        from core.runtime.db_core import get_runtime_state_value
        st = get_runtime_state_value("agent_smith_escalation", {}) or {}
        ud = []
        for noegle, pat in (st.get("patterns") or {}).items():
            if not isinstance(pat, dict) or int(pat.get("rung") or 0) < RUNG_CONFRONT:
                continue
            if not str(noegle).startswith("seq:"):
                continue          # behaviour/phrase har intet kald at holde
            ud.append({"key": noegle, "label": str(pat.get("label") or "")})
        return ud
    except Exception as exc:
        logger.debug("smith_confrontation: kunne ikke laese stigen: %s", exc)
        return []


def smith_confront_on_action(reasoning_text: str, ctx: dict[str, Any]):
    """RED naar et trin-3-moenster er ved at blive gentaget. ``None`` ellers.

    Selv-sikker: enhver fejl giver ``None`` (afstaa). En detektor der kaster
    ville naa hele vejen ud i en runde, og et vaern maa aldrig vaere det der
    braekker turen.
    """
    try:
        from core.services.gate_kernel import Decision, GateClass, Verdict

        moenstre = _trin3_moenstre()
        if not moenstre:
            return None

        kald = [tc for tc in (ctx.get("tool_calls_this_run") or []) if isinstance(tc, dict)]
        if not kald:
            return None
        run_id = str(ctx.get("run_id") or "")

        for tc in kald:
            fn = tc.get("function") or {}
            navn = str(fn.get("name") or "")
            if not navn or _er_fritaget(navn):
                continue          # bash/shell er Bjoerns vej udenom — aldrig Smiths
            argumenter = str(fn.get("arguments") or "")
            for m in moenstre:
                if not _rammer(m["label"], navn, argumenter):
                    continue
                if _hold_taeller(run_id, m["key"], laes_kun=True) >= _MAX_HOLD:
                    # Loftet er naaet. Vi holder ikke igen — at lade ham
                    # re-raesonnere i ring ville i praksis vaere at cutte runnet.
                    return None
                _hold_taeller(run_id, m["key"])
                return Verdict(
                    "agent_smith", Decision.RED,
                    ("Agent Smith: du forpligtede dig til at stoppe «%s», og du er "
                     "ved at gøre det igen med %s. Kaldet blev ikke udført. "
                     "Vælg en anden fremgangsmåde nu." % (m["label"], navn))[:200],
                    action="hold", klass=GateClass.COGNITIVE,
                )
        return None
    except Exception as exc:
        logger.debug("smith_confrontation: detektor fejlede: %s", exc)
        return None
