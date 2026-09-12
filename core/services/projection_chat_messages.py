"""Kompatibilitets-projektoren — ledger-hændelser → `chat_messages`-rækker.

Spec: Fase 1, udgangskriterium «projector can rebuild selected `chat_messages`
rows from an empty projection».

## Hvorfor den findes

`chat_messages` er hele husets læse-flade. Fase 0 talte 61 læsere fordelt på
API, tjenester og UI. Hvis ledgeren skulle blive sandheden, kan de 61 ikke
skrives om på én gang — og skal de ikke. Så bliver `chat_messages` en
PROJEKTION: stadig den flade alle læser, men ikke længere noget nogen skriver
direkte for en ledger-session.

Det er hele forskellen på en migration og et skifte man kan fortryde.

## Hvorfor en genafspilning ikke fordobler

Det oprindelige skrive-kald finder sit `message_id` med `uuid4()`. Kørte
projektoren to gange over samme hændelse med den regel, ville den lave to
rækker med samme indhold og forskelligt id — og ingen ville kunne se hvilken
der var den ægte.

Derfor UDLEDES id'et af hændelsen: samme hændelse giver altid samme
`message_id`. Så er den anden kørsel en `ON CONFLICT` frem for en dublet.
Dét er grunden til at markøren ikke behøver være atomisk med rækkearbejdet:
et nedbrud imellem dem koster en gentagelse, ikke en fordobling.

`DO UPDATE` frem for `DO NOTHING`, fordi en projektion skal KONVERGERE: retter
en senere version af folden en fejl, skal genfoldningen rette rækkerne — ikke
bevare den gamle udregning fordi rækken tilfældigvis fandtes.

## Én ugyldig hændelse må ikke gøre samtalen ulæselig

Validering der KASTER ville betyde at én misformet hændelse spærrede resten af
sessionen for altid. Validering der TIER ville være værre. Så: ugyldige
hændelser springes over, og de står med grund i projektionens tilstand og i
loggen. Man kan tælle dem.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

PROJEKTION = "chat_messages"
VERSION = "1"

#: Beskrivelsen af projektionen som DATA. Drift-sammenligneren slog
#: tidligere disse op ved at importere netop dette modul og hardkode
#: tabelnavn, hændelsestype og kolonner — hvilket gjorde den til en
#: `chat_messages`-sammenligner der hed noget generelt.
KIND = "message"
TABEL = "chat_messages"
NOEGLE = "session_id"
SAMMENLIGN = ("role", "content", "reasoning_content", "content_json", "created_at")

#: Hændelsen skal have en rolle og et indhold. Alt andet har et forsvarligt
#: standardsvar; disse to har ikke — en række uden dem ville være støj.
PAAKRAEVET = ("role", "content")

_KOLONNER = ("role", "content", "user_id", "workspace_name",
             "reasoning_content", "git_sha", "content_json", "created_at")


def message_id_for(session_id: str, event_id: str) -> str:
    """Udled et stabilt `message_id`. Samme hændelse → altid samme id.

    Hashet er over BEGGE dele fordi `event_id` kun er unik pr. session, mens
    `chat_messages.message_id` er unik i hele tabellen.

    Bruges kun når hændelsen ikke ALLEREDE bærer et id — se `_message_id`.
    """
    h = hashlib.sha1(f"{session_id}\x00{event_id}".encode()).hexdigest()
    return f"message-{h}"


def _message_id(session_id: str, e: dict[str, Any], payload: dict[str, Any]) -> str:
    """Et id sessionen allerede har, VINDER over et udledt.

    Skygge-tilstanden skriver begge steder: rækken får sit `message_id` af
    `uuid4()`, og hændelsen bærer det med. Udledte projektoren sit eget ved
    skiftet, ville den lægge et NYT sæt rækker ved siden af de gamle — samme
    samtale, to gange, uden at nogen kunne se hvilken var den ægte.

    Hændelser født i ledgeren har intet id at bevare, og dér udledes det.
    """
    givet = str(payload.get("message_id") or "").strip()
    return givet or message_id_for(session_id, str(e["event_id"]))


def valider(payload: dict[str, Any]) -> str | None:
    """Returnér en grund hvis hændelsen ikke kan blive en række, ellers None."""
    if not isinstance(payload, dict):
        return "payload er ikke et objekt"
    for n in PAAKRAEVET:
        if not str(payload.get(n) or "").strip():
            return f"mangler {n}"
    cj = payload.get("content_json")
    if cj is not None and not isinstance(cj, (str, list, dict)):
        return "content_json er hverken tekst, liste eller objekt"
    return None


def _raekke(session_id: str, e: dict[str, Any]) -> dict[str, Any]:
    p = dict(e.get("payload") or {})
    cj = p.get("content_json")
    if isinstance(cj, (list, dict)):
        cj = json.dumps(cj, ensure_ascii=False)
    return {
        "message_id": _message_id(session_id, e, p),
        "session_id": str(session_id),
        "role": str(p["role"]).strip(),
        "content": str(p["content"]),
        "user_id": str(p.get("user_id") or ""),
        "workspace_name": str(p.get("workspace_name") or ""),
        "reasoning_content": str(p.get("reasoning_content") or ""),
        "git_sha": str(p.get("git_sha") or ""),
        # Tiden kommer fra HÆNDELSEN, aldrig fra now(): ellers ville en
        # genfoldning flytte hele samtalen frem i tid.
        "created_at": str(p.get("created_at") or e.get("created_at") or ""),
        "content_json": cj,
    }


def _skriv(raekke: dict[str, Any]) -> None:
    from core.runtime.db import connect
    # `git_sha` er en DOVEN kolonne: den står ikke i CREATE TABLE, kun i en
    # migration der køres af den der skriver kompakt-markører. En frisk database
    # har den derfor ikke, og projektoren ville falde over sit første INSERT.
    sat = ", ".join(f"{k} = excluded.{k}" for k in _KOLONNER)
    with connect() as conn:
        try:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN git_sha TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass  # kolonnen findes allerede
        conn.execute(
            "INSERT INTO chat_messages "
            "(message_id, session_id, role, content, user_id, workspace_name, "
            " reasoning_content, git_sha, created_at, content_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            f"ON CONFLICT(message_id) DO UPDATE SET {sat}",
            (raekke["message_id"], raekke["session_id"], raekke["role"],
             raekke["content"], raekke["user_id"], raekke["workspace_name"],
             raekke["reasoning_content"], raekke["git_sha"],
             raekke["created_at"], raekke["content_json"]),
        )


def start() -> dict[str, Any]:
    """Formen ligger i STARTEN, ikke i den første fold.

    Ellers ville en tom session svare `{}` og en tom session med hændelser
    svare med tællere — to former for det samme, og en læser der skulle gætte.
    """
    return {"skrevet": 0, "sprunget_over": 0, "afviste": []}


def fold(state: dict[str, Any], e: dict[str, Any]) -> dict[str, Any]:
    """Ren pr. hændelse og idempotent: samme hændelse igen ændrer ingenting."""
    if str(e.get("kind") or "") != "message":
        state["sprunget_over"] += 1
        return state

    grund = valider(e.get("payload") or {})
    if grund is not None:
        # Ikke tavst, og ikke fatalt: én misformet hændelse må hverken spærre
        # resten af samtalen eller forsvinde.
        state["afviste"].append({"event_id": e.get("event_id"), "grund": grund})
        logger.warning("projection_chat_messages: afviste %s: %s", e.get("event_id"), grund)
        return state

    _skriv(_raekke(str(e["session_id"]), e))
    state["skrevet"] += 1
    return state


def register() -> None:
    from core.services.projection_runtime import register as _r
    _r(PROJEKTION, version=VERSION, fold=fold, start=start)


def rebuild(session_id: str) -> dict[str, Any]:
    """Genskab sessionens `chat_messages`-rækker fra ledgeren.

    Kaldes både ved indhentning og som prøve: kan rækkerne IKKE genskabes fra
    en tom projektion, er ledgeren ikke sandheden — og så skal man ikke skifte.
    """
    from core.services import projection_runtime as pr
    if PROJEKTION not in pr.registered():
        register()
    return pr.project(session_id, PROJEKTION, force_refold=True)


# ── kun projektoren må skrive kompatibilitets-rækker ─────────────────────

class DirekteSkrivningAfvist(RuntimeError):
    """En ledger-session fik et direkte skrive-forsøg uden om projektoren."""


def guard_direct_write(session_id: str, *, conn=None) -> None:
    """Afvis direkte `chat_messages`-skrivninger for en ledger-session.

    Uden denne vagt ville skiftet give DOBBELT sandhed i stedet for at flytte
    den: nogle rækker foldet fra ledgeren, andre skrevet udenom — og ingen
    måde at se hvilke. Vagten er grunden til at et skifte kan fortrydes.

    Tilstanden læses fra databasen hver gang, ikke fra en cache i processen:
    et skifte sker i den ene proces og skal ses i den anden med det samme.
    Kan tilstanden ikke læses, tillades skrivningen — en utilgængelig
    tilstands-kolonne må ikke gøre samtalen skrivebeskyttet.

    `conn` SKAL gives når kalderen allerede har en forbindelse åben:
    forbindelserne er poolede, så et nyt `with connect()` ville være den samme
    forbindelse og committe kalderens transaktion for tidligt.
    """
    try:
        from core.runtime.db_session_ledger import storage_mode
        mode = storage_mode(session_id, conn=conn)
    except Exception:
        logger.warning("projection_chat_messages: kunne ikke laese storage_mode", exc_info=True)
        return
    if mode == "ledger":
        raise DirekteSkrivningAfvist(
            f"session {session_id!r} er i ledger-tilstand: rækker skrives af "
            "projektoren, ikke direkte. Skriv hændelsen til ledgeren i stedet."
        )
