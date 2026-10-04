"""start_session — Jarvis starter selv et run i en session der er Bjørns.

Motoren fandtes, men knappen gjorde ikke. ``visible_runs.start_autonomous_run``
er den funktion ALLE system-startere går gennem (recurring, wakeup, drømme,
heartbeat), og den kan ramme en bestemt session — men den var ikke nåbar som
værktøj. Jarvis kunne derfor ikke bede om et run i en navngiven session.

Ejerskabet klarer sig selv, og det er målt: baggrundstråden i
``start_autonomous_run`` binder ``owner_user_id()`` som context-var, så hver
besked i runnet stemples med Bjørns id. ``list_chat_sessions(user_id=...)``
viser netop de sessioner hvor mindst én besked bærer det id — så en session
jeg starter, lander automatisk i hans liste i desk. Målt 4/10-2026:
auto-dream 36/36 og auto-recurring 75/75 beskeder stemplede.

Rate-guarden er et rullende vindue, ikke en daglig cap. Samme valg som
operator-wakeup'en tog: en hård daglig cap dræber funktionen TAVST, og en
funktion der fejler tavst er værre end ingen funktion.
"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Rullende time. Et selv-startet run er den dyreste handling jeg kan tage på
# egen hånd — hele værktøjskassen, ingen bruger til at godkende undervejs.
_SPAWN_TIMES: list[float] = []
_MAX_PER_HOUR = 10

# Et run læser prompten som sin opgave. Er den længere end dette, er den ikke
# en opgave men et dokument — og et dokument hører i en fil, ikke i en prompt.
_MAX_PROMPT_CHARS = 8000


def _ryd_gamle(now: float) -> None:
    """Drop tidsstempler ældre end en time — rullende vindue."""
    graense = now - 3600.0
    while _SPAWN_TIMES and _SPAWN_TIMES[0] < graense:
        _SPAWN_TIMES.pop(0)


def antal_sidste_time() -> int:
    """Hvor mange selv-startede runs ligger i det rullende vindue lige nu."""
    _ryd_gamle(time.time())
    return len(_SPAWN_TIMES)


def start_session(
    prompt: str,
    *,
    session_id: str | None = None,
    title: str | None = None,
    origin: str = "self",
) -> dict[str, Any]:
    """Start et autonomt run i en session der tilhører Bjørn.

    Tre veje til hvilken session runnet lander i:
      * ``session_id`` givet      → skriv i den (den findes, eller oprettes af
                                    run-stien; eksplicit vinder altid)
      * ``title`` givet, intet id → opret en NY navngivet session med titlen
      * ingen af dem              → rotatoren vælger ``auto-{origin}-{dato}``

    Returnerer ``{"status": "ok", ...}`` eller ``{"status": "error", "error": ...}``.
    Kaster aldrig — et værktøj der kaster efterlader kalderen uden svar.
    """
    tekst = str(prompt or "").strip()
    if not tekst:
        return {
            "status": "error",
            "error": (
                "tom prompt — et run uden en opgave ville bruge tokens på at "
                "gætte hvad jeg mente"
            ),
        }

    if len(tekst) > _MAX_PROMPT_CHARS:
        return {
            "status": "error",
            "error": (
                f"prompten er {len(tekst)} tegn; loftet er {_MAX_PROMPT_CHARS}. "
                "Læg dokumentet i en fil og henvis til stien i stedet."
            ),
        }

    now = time.time()
    _ryd_gamle(now)
    if len(_SPAWN_TIMES) >= _MAX_PER_HOUR:
        return {
            "status": "error",
            "error": (
                f"rate-guard: {_MAX_PER_HOUR} selv-startede runs i timen. "
                "Vinduet ruller — vent og prøv igen."
            ),
        }

    mål = str(session_id or "").strip()
    oprettet = False

    if not mål and str(title or "").strip():
        # En NY session skal have en titel. Uden den står den som «New chat»
        # i Bjørns liste, og en session han ikke kan kende på navnet er en
        # session han ikke ved hvad er.
        try:
            from core.services.chat_sessions import create_chat_session

            mål = str(create_chat_session(title=str(title).strip()[:120])["id"])
            oprettet = True
        except Exception as exc:
            logger.warning("start_session: kunne ikke oprette session: %s", exc)
            return {
                "status": "error",
                "error": f"kunne ikke oprette session: {type(exc).__name__}: {exc}",
            }

    try:
        from core.services.visible_runs import start_autonomous_run

        start_autonomous_run(tekst, session_id=(mål or None), origin=origin)
    except Exception as exc:
        logger.warning("start_session fejlede: %s", exc)
        return {
            "status": "error",
            "error": f"kunne ikke starte run: {type(exc).__name__}: {exc}",
        }

    _SPAWN_TIMES.append(now)
    return {
        "status": "ok",
        "session_id": mål or None,
        "oprettet": oprettet,
        "origin": origin,
        "note": (
            "Runnet kører i baggrunden. Sessionen bærer Bjørns id og vises i "
            "hans liste i desk."
        ),
    }


def _exec_start_session(args: dict[str, Any]) -> dict[str, Any]:
    return start_session(
        str(args.get("prompt") or ""),
        session_id=(str(args.get("session_id") or "").strip() or None),
        title=(str(args.get("title") or "").strip() or None),
        origin=(str(args.get("origin") or "self").strip() or "self"),
    )


SESSION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "start_session",
            "description": (
                "Start et selvstændigt run i en session der tilhører Bjørn — så "
                "jeg kan sætte mig selv i gang med en opgave i en anden session, "
                "agent-til-agent. Sessionen stempler Bjørns id og dukker "
                "automatisk op i hans sessions-liste i desk. Uden session_id "
                "vælger rotatoren en auto-session for dagen; med title oprettes "
                "en ny navngivet session. Loft: 10 selv-startede runs i timen."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Opgaven der skal løses i den nye session.",
                    },
                    "session_id": {
                        "type": "string",
                        "description": (
                            "Eksisterende session at skrive i. Udelades → "
                            "rotatoren vælger (eller title opretter en ny)."
                        ),
                    },
                    "title": {
                        "type": "string",
                        "description": (
                            "Titel til en NY session. Bruges kun når session_id "
                            "udelades."
                        ),
                    },
                    "origin": {
                        "type": "string",
                        "description": "Kort oprindelses-label til logning. Default 'self'.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
]
