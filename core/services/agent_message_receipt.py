"""En besked til et barn maa ikke fryse foraelderens tur — Fase 6.

`send_message_to_agent(auto_execute=True)` koerte barnet INLINE og gav
foraelderen hele svaret tilbage. Det faelder to kriterier paa én gang:
kvitteringen, og «foraelderen kan fortsaette mens et accepteret barn koerer».

MAALT 10/9-2026 over 929 aegte agent-koersler:

    median   6,0 s
    p90     36,8 s
    max    430,5 s   (7 minutter)
    over 60 s: 68 koersler

Det tal afgoer formen. En kvittering paa HVER besked ville vaere daarligere
for det almindelige tilfaelde — foraelderen skulle polle efter et
seks-sekunders job. Men halen er hvor det goer ondt: 68 gange stod turen
stille i over et minut.

Derfor: VENT KORT, KVITTÉR DEREFTER. Naar barnet svarer inden for
taalmodigheden, faar foraelderen svaret med det samme, som foer. Naar det ikke
goer, faar han en kvittering der siger hvordan han henter resultatet — og
barnet arbejder videre i stedet for at blive kasseret.

BARNET BAERER FORAELDERENS KONTEKST MED. En almindelig traad mister alle
ContextVars, og to af dem peger i den farlige retning: tomt vaerktoejs-scope
betyder «unbound legacy» (ser alt), og tabt autonomi fjerner sandkasse-kravet
for bash. `copy_context()` bevarer dem, og `uden_foraeldrens_godkendelse()`
rydder praecis det ene der ikke maa arves — samme regel som naar barnet koerer
inline (fase 5).
"""
from __future__ import annotations

import contextvars
import logging
import threading
from typing import Any

logger = logging.getLogger("uvicorn.error")

# Hvor laenge foraelderen venter foer han faar en kvittering i stedet for et
# svar. 20 s ligger mellem median (6 s) og p90 (37 s): det almindelige svar
# naar frem, halen bliver til en kvittering.
TAALMODIGHED_S = 20.0


def _book_completion_wakeup(agent_id: str, resultat: dict[str, Any]) -> None:
    """Book en self-wakeup saa forælderen faar besked naar baggrundsbarnet er faerdigt.

    Kaldes fra baggrundstraadens finally-blok naar forælderen allerede har
    faaet en kvittering (forsent.is_set()). Uden dette er et sent-faerdigt
    baggrundsbarn tavst — forælderen skulle polle med get_agent.
    """
    try:
        from core.services.self_wakeup import schedule_self_wakeup
        status = str(resultat.get("status") or "completed")
        svar = ""
        for msg in reversed(resultat.get("messages") or []):
            if str(msg.get("direction") or "") == "agent->jarvis":
                kind = str(msg.get("kind") or "")
                if kind in ("result", "") and not svar:
                    svar = str(msg.get("content") or "")[:300]
                    break
        schedule_self_wakeup(
            delay_seconds=60,
            prompt=(
                f"Baggrunds-agent {agent_id} er faerdig (status={status}). "
                f"Svar-uddrag: {svar[:200] if svar else '(tomt)'}... "
                f"Hent det fulde resultat med get_agent(agent_id='{agent_id}')."
            ),
            reason=f"agent-completion:{agent_id}",
        )
        logger.info("completion-wakeup booket for %s (status=%s)", agent_id, status)
    except Exception:
        logger.warning("kunne ikke booke completion-wakeup for %s", agent_id, exc_info=True)


def send_med_kvittering(*, agent_id: str, content: str,
                        role: str = "user",
                        kind: str = "jarvis-message",
                        execution_mode: str = "solo-task",
                        taalmodighed_s: float = TAALMODIGHED_S) -> dict[str, Any]:
    """Send beskeden, vent kort, og giv enten svaret eller en kvittering."""
    from core.services.agent_runtime import send_message_to_agent

    # Beskeden landes og agenten saettes i koe UDEN at koere den. Det er den
    # del der skal vaere sket foer vi kvitterer: en kvittering paa noget der
    # ikke er accepteret ville vaere en loegn.
    try:
        send_message_to_agent(agent_id=agent_id, content=content, role=role,
                              kind=kind, auto_execute=False)
    except Exception as exc:
        return {"status": "error", "error": str(exc), "agent_id": agent_id}

    def _udfoer() -> dict[str, Any]:
        from core.services.agent_runtime import execute_agent_task
        return execute_agent_task(agent_id=agent_id, execution_mode=execution_mode) or {}

    return _koer_med_taalmodighed(agent_id, _udfoer, taalmodighed_s)


def _koer_med_taalmodighed(agent_id: str, udfoer, taalmodighed_s: float) -> dict[str, Any]:
    """Kør barnet i en tråd med forælderens kontekst; svar eller kvittér.

    Fælles for `send_med_kvittering` og `spawn_med_kvittering`.

    LÅSEN (17/9-2026): uden den kunne barnet blive færdigt i øjeblikket mellem
    at forælderens ventetid udløb og at «for sent» blev sat. Så sprang
    `finally` vækningen over, forælderen fik en kvittering — og hørte aldrig
    at barnet var færdigt. Nu afgøres «nåede det frem?» og «skal der vækkes?»
    under samme lås, så præcis én af dem sker.
    """
    resultat: dict[str, Any] = {}
    laas = threading.Lock()
    tilstand = {"faerdig": False, "forsent": False}
    faerdig = threading.Event()
    kontekst = contextvars.copy_context()

    def _koer() -> None:
        from core.services.child_authority import uden_foraeldrens_godkendelse
        try:
            with uden_foraeldrens_godkendelse():
                resultat.update(udfoer() or {})
        except Exception as exc:
            # En traad der doer stille efterlader et barn der ser ud til at
            # arbejde for altid.
            logger.warning("barn %s: koerslen fejlede i baggrunden", agent_id,
                           exc_info=True)
            resultat.update({"status": "failed", "error": str(exc)})
            try:
                from core.services.child_failure_signal import note_child_ended
                note_child_ended(agent_id, status="failed",
                                 error="koerslen fejlede i baggrunden")
            except Exception:
                pass
        finally:
            with laas:
                tilstand["faerdig"] = True
                vaek = tilstand["forsent"]
            faerdig.set()
            if vaek:
                _book_completion_wakeup(agent_id, resultat)

    try:
        t = threading.Thread(target=lambda: kontekst.run(_koer),
                             name=f"agent-{str(agent_id)[:12]}", daemon=True)
        t.start()
    except Exception as exc:
        # Kunne vi ikke starte en traad, er det bedre at koere inline end at
        # tabe barnet helt.
        logger.warning("barn %s: kunne ikke starte baggrundstraad — koerer "
                       "inline", agent_id, exc_info=True)
        try:
            return dict(udfoer() or {})
        except Exception:
            return {"status": "error", "error": str(exc), "agent_id": agent_id}

    faerdig.wait(timeout=max(0.0, float(taalmodighed_s)))
    with laas:
        if tilstand["faerdig"]:
            return dict(resultat)
        tilstand["forsent"] = True
    return kvittering(agent_id, taalmodighed_s=taalmodighed_s)


def kvittering(agent_id: str, *, taalmodighed_s: float = TAALMODIGHED_S) -> dict[str, Any]:
    """Hvad der er ACCEPTERET — ikke hvad der blev svaret.

    Den siger ogsaa HVORDAN resultatet hentes. En kvittering der ikke goer
    det, forudsaetter at laeseren kender huset.
    """
    return {
        "status": "accepted",
        "agent_id": agent_id,
        "accepted": True,
        "ventede_sekunder": round(float(taalmodighed_s), 1),
        "hent_resultat": (
            f"Barnet arbejder videre og svarer ikke her. Hent resultatet med "
            f"get_agent(agent_id='{agent_id}') naar du er klar. Du kan roligt "
            "lave andet imens — det bliver ikke kasseret."
        ),
    }


def spawn_med_kvittering(*, taalmodighed_s: float = TAALMODIGHED_S,
                         **spawn_kwargs) -> dict[str, Any]:
    """Spawn en agent, vent kort, returner enten resultat eller kvittering.

    Samme moenster som ``send_med_kvittering``, men for at SPAWNE nye agenter
    i stedet for at sende beskeder til eksisterende. Bruges af explore for at
    undgaa at blokere foraelderens tur paa langsomme research-agenter.

    Maalt 17/9-2026 over 201 explore-koersler:
        median  14,8 s
        p90     51,7 s
        max    430,5 s
        over 60 s: 15 koersler

    Med ``taalmodighed_s=60`` holder ~93% af koerslerne sig inline (186 af
    201); halen bliver asynkron med completion-signal.
    """
    from core.services.agent_runtime import spawn_agent_task, execute_agent_task

    spawn_kwargs["auto_execute"] = False
    try:
        spawn_result = spawn_agent_task(**spawn_kwargs)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    agent_id = str(spawn_result.get("agent_id") or "")
    if not agent_id:
        return {"status": "error", "error": "spawn returnerede ingen agent_id",
                "spawn_result": spawn_result}

    def _udfoer() -> dict[str, Any]:
        return execute_agent_task(agent_id=agent_id) or {}

    svar = _koer_med_taalmodighed(agent_id, _udfoer, taalmodighed_s)
    # Kalderen (explore) skal kunne se model og udbyder, også i en kvittering.
    for felt in ("provider", "model"):
        if felt not in svar and spawn_result.get(felt):
            svar[felt] = spawn_result[felt]
    return svar
