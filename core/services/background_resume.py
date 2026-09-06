"""Turen maa ikke slutte mens en baggrunds-shell stadig producerer.

`operator_run_in_background` blev bygget i dag, men uden det her er den ubrugelig:
man starter en shell, turen slutter med det samme, og man ser aldrig resultatet.
Praecis den sygdom resten af dagen har handlet om — noget der findes uden at
kunne bruges.

jarvis-code loeser det med en delta-tracker i sit in-process register: loopet
genoptager NOEJAGTIG én gang pr. aegte tilstandsaendring (nyt output eller exit)
i stedet for at snurre.

Server-side kan tilstanden ikke ligge i et modul-globalt register: den skal
krydse api/runtime-graensen, og den graense har vaeret aarsag til en stribe fejl
i dag. Derfor runtime-state, noeglet paa session.

Kontrakten er bevidst smal: **kun ÆGTE aendring genoptager.** Uden det ville en
tur med en kørende shell aldrig kunne slutte — den ville genoptage i det
uendelige paa "shell'en koerer stadig".
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_KEY = "background_shells_by_session"
_MAX_PR_SESSION = 8          # loft: en tur maa ikke drukne i baggrunds-stoej

# Naade naar en shell netop er startet og endnu ikke har naaet at skrive noget.
# Uden den er funktionen ubrugelig i praksis: en kommando bruger et par sekunder
# paa sit foerste output, og turen slutter paa under ét — saa er der aldrig en
# aendring at genoptage paa, og man ser aldrig resultatet. Maalt live: shell'en
# skrev efter 3 s, turen sluttede efter 2.
#
# Bevidst KORT og KUN ÉN gang: vi venter paa at noget begynder, ikke paa at det
# bliver faerdigt. En lang kommando skal stadig koere videre uden at holde turen.
_FOERSTE_OUTPUT_NAADE_S = 4.0


def _load() -> dict[str, Any]:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_KEY, {})
        return dict(v) if isinstance(v, dict) else {}
    except Exception:
        return {}


def _save(state: dict[str, Any]) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(_KEY, state)
    except Exception:
        pass


def note_started(session_id: str, shell_id: str) -> None:
    """Husk at DENNE session har startet den shell. Self-safe."""
    sid = str(session_id or "").strip()
    if not sid or not str(shell_id or "").strip():
        return
    st = _load()
    shells = [s for s in (st.get(sid) or []) if isinstance(s, dict)]
    if any(s.get("shell_id") == shell_id for s in shells):
        return
    shells.append({"shell_id": str(shell_id), "offset": 0, "done": False,
                   "startet": time.time()})
    st[sid] = shells[-_MAX_PR_SESSION:]
    _save(st)


def forget_session(session_id: str) -> None:
    """Ryd op naar en session er faerdig, saa staten ikke vokser uendeligt."""
    sid = str(session_id or "").strip()
    if not sid:
        return
    st = _load()
    if st.pop(sid, None) is not None:
        _save(st)


def tracked(session_id: str) -> list[dict[str, Any]]:
    return [s for s in (_load().get(str(session_id or "")) or []) if isinstance(s, dict)]


def build_note(deltas: list[dict[str, Any]]) -> str:
    """Systemnoten der faar Jarvis til at forholde sig til det nye output. Ren.

    Den siger hvad der SKETE, ikke hvad han skal goere — han skal selv vaelge om
    outputtet aendrer noget. En instruks ville goere den til en tvang.
    """
    if not deltas:
        return ""
    linjer = ["[BAGGRUND] Der er nyt fra en kommando du startede:"]
    for d in deltas:
        sid = str(d.get("shell_id") or "?")
        tekst = str(d.get("output") or "").strip()
        if d.get("finished"):
            linjer.append(f"- {sid} er FAERDIG.")
        if tekst:
            klippet = tekst if len(tekst) <= 2000 else tekst[:2000] + "\n… (afkortet)"
            linjer.append(f"- {sid} skrev:\n{klippet}")
    return "\n".join(linjer)


# En baggrundskoersel der tager laenge nok til at Bjoern gaar fra skaermen
# skal sige til NAAR den er faerdig — ikke bare efterlade en note i en samtale
# han ikke sidder i. Under graensen ville en besked bare vaere stoej: han sad
# der stadig. ntfy foerst, jf. [[outreach_ntfy_blindness]].
_LANG_KOERSEL_S = 30.0


def _sig_til_hvis_lang(shell: dict[str, Any], sidste_output: str) -> None:
    """Push besked hvis shellen koerte >= 30 s. Self-safe: fejl → tavshed."""
    try:
        startet = float(shell.get("startet") or 0.0)
        if not startet:
            return
        varighed = time.time() - startet
        if varighed < _LANG_KOERSEL_S:
            return
        hale = " ".join(str(sidste_output or "").split())[-160:]
        besked = (
            f"Baggrundskoersel faerdig efter {int(varighed)} s"
            + (f": {hale}" if hale else ".")
        )
        from core.services.ntfy_gateway import is_configured, send_notification
        if not is_configured():
            return
        send_notification(besked, title="Jarvis", tags=["hourglass_done"])
    except Exception:
        logger.debug("background_resume: kunne ikke sige til", exc_info=True)


async def poll_async(session_id: str, user_id: str) -> str:
    """Er der nyt fra sessionens baggrunds-shells? Returnerer en note, ellers "".

    Kun ÆGTE aendring taeller: nyt output, eller at en shell netop blev faerdig.
    En shell der bare koerer videre giver ingenting — ellers ville turen aldrig
    kunne slutte.

    Self-safe: enhver fejl → "" (turen slutter normalt).
    """
    try:
        from core.tools.operator_background import read_async
    except Exception:
        return ""
    sid = str(session_id or "").strip()
    shells = tracked(sid)
    if not shells:
        return ""

    # Har en netop startet shell endnu ikke skrevet noget, saa giv den ét kort
    # oejeblik — ellers slutter turen foer det foerste output overhovedet findes.
    if all(int(s.get("offset") or 0) == 0 and not s.get("done") for s in shells):
        try:
            await asyncio.sleep(_FOERSTE_OUTPUT_NAADE_S)
        except Exception:
            pass

    deltas: list[dict[str, Any]] = []
    aendret = False
    for s in shells:
        if s.get("done"):
            continue
        try:
            r = await read_async(shell_id=str(s.get("shell_id") or ""),
                                 user_id=user_id, since=int(s.get("offset") or 0))
        except Exception:
            continue
        if r.get("error"):
            s["done"] = True
            aendret = True
            continue
        tekst = str(r.get("output") or "")
        koerer = bool(r.get("running"))
        blev_faerdig = (not koerer) and not s.get("done")
        if tekst or blev_faerdig:
            deltas.append({"shell_id": s.get("shell_id"), "output": tekst,
                           "finished": blev_faerdig})
        if tekst:
            s["offset"] = int(r.get("offset") or s.get("offset") or 0)
            aendret = True
        if blev_faerdig:
            s["done"] = True
            aendret = True
            _sig_til_hvis_lang(s, tekst)

    if aendret:
        st = _load()
        st[sid] = shells
        _save(st)
    return build_note(deltas)
