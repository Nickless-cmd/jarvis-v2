"""Projektion: `tool_router_decisions` foldet fra sessionens hændelser.

Anden projektion efter `chat_messages`, og den er valgt først af de tre der
mangler i fase 11, punkt 4, fordi den er den mindste: ét skrivested
(`tool_router.py:471`), og den er nøglet på `session_id` ligesom hovedbogen
selv.

Rækketallet her stod først som 183. Det var arbejdsstationens database;
runtime'ens ligger på serveren og havde 1905 rækker den 12/9-2026. Et tal
uden en maskine er ikke en måling.

**Hvad der IKKE fulgte med fra `chat_messages`.** Tabellen har ingen naturlig
nøgle — kun `id INTEGER PRIMARY KEY`. Uden en udledt nøgle ville en genfoldning
lægge et nyt sæt rækker ved siden af de gamle i stedet for at opdatere dem, og
så ville tabellen have to svar på hvad routeren besluttede. Derfor
`decision_id`, udledt af (session_id, event_id) præcis som `message_id_for`,
og en doven migration der tilføjer kolonnen og dens unikke indeks.

**Tidsformatet skifter med denne projektion.** Det gamle skrivested brugte
`datetime('now')`, som giver `2026-09-11 19:38:09` — mellemrum som separator og
ingen zone. Hver anden tabel i huset skriver ISO med `+00:00`. En læser med
`fromisoformat` får en naiv datetime og behandler den som lokal tid, altså to
timer forkert om sommeren. Projektionen skriver ISO. Det betyder at gamle og
nye rækker har hver sit format, og at drift-sammenligningen SKAL normalisere
tid — ellers ville hver eneste række se ud som en afvigelse.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

PROJEKTION = "tool_router_decisions"
VERSION = "1"

#: Hændelsens type i hovedbogen. `chat_messages` folder `kind == "message"`.
KIND = "tool_router_decision"

#: Tabellen projektionen skriver til, og nøglen sessionen findes på. Står her
#: som data frem for i drift-sammenligneren, så den kan slå dem op i stedet for
#: at kende hver enkelt projektion ved navn.
TABEL = "tool_router_decisions"
NOEGLE = "session_id"

#: Uden `lane` ved vi ikke hvilken bane beslutningen gjaldt, og uden
#: `selected_names_json` er der ingen beslutning at gemme. Resten har et
#: forsvarligt standardsvar.
PAAKRAEVET = ("lane", "selected_names_json")

_KOLONNER = ("run_id", "session_id", "lane", "user_message_preview",
             "selected_names_json", "always_core_names_json",
             "embedding_picks_json", "confidence", "threshold",
             "fallback_used", "fallback_reason", "elapsed_ms",
             "tokens_saved_estimate", "created_at")

#: Kolonnerne drift-sammenligningen ser på. `run_id` er udenfor med vilje: den
#: er sessionens løbenummer og siger intet om hvad routeren besluttede.
SAMMENLIGN = ("lane", "selected_names_json", "always_core_names_json",
              "confidence", "threshold", "fallback_used", "created_at")


def decision_id_for(session_id: str, event_id: str) -> str:
    """Stabilt id: samme hændelse giver altid samme id.

    Hashet er over begge dele fordi `event_id` kun er unik pr. session, mens
    `decision_id` skal være unik i hele tabellen.
    """
    h = hashlib.sha1(f"{session_id}\x00{event_id}".encode()).hexdigest()
    return f"decision-{h}"


def _decision_id(session_id: str, e: dict[str, Any], payload: dict[str, Any]) -> str:
    """Et id hændelsen allerede bærer VINDER over et udledt.

    Samme grund som i `chat_messages`: i skygge-tilstand skrives der begge
    steder, og rækken har sit id før hændelsen når hovedbogen. Udledte
    projektoren sit eget ved skiftet, ville den lægge en dublet ved siden af.
    """
    givet = str(payload.get("decision_id") or "").strip()
    return givet or decision_id_for(session_id, str(e["event_id"]))


def _json_tekst(v: Any) -> str:
    """Lister og objekter gemmes som tekst; tekst gemmes uændret.

    Hændelsen kan bære begge former afhængigt af om den kom fra det gamle
    skrivested (som allerede havde kaldt `json.dumps`) eller fra hovedbogen.
    """
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def valider(payload: dict[str, Any]) -> str | None:
    """Returnér en grund hvis hændelsen ikke kan blive en række, ellers None."""
    if not isinstance(payload, dict):
        return "payload er ikke et objekt"
    if not str(payload.get("lane") or "").strip():
        return "mangler lane"
    valgte = payload.get("selected_names_json", payload.get("selected_names"))
    if valgte is None or _json_tekst(valgte).strip() in ("", "[]", "null"):
        return "mangler selected_names"
    for navn in ("confidence", "threshold"):
        v = payload.get(navn)
        if v is not None and not isinstance(v, (int, float)):
            return f"{navn} er ikke et tal"
    return None


def _raekke(session_id: str, e: dict[str, Any]) -> dict[str, Any]:
    p = dict(e.get("payload") or {})
    return {
        "decision_id": _decision_id(session_id, e, p),
        "run_id": str(p.get("run_id") or ""),
        "session_id": str(session_id),
        "lane": str(p["lane"]).strip(),
        "user_message_preview": str(p.get("user_message_preview") or ""),
        "selected_names_json": _json_tekst(
            p.get("selected_names_json", p.get("selected_names"))),
        "always_core_names_json": _json_tekst(
            p.get("always_core_names_json", p.get("always_core"))),
        "embedding_picks_json": _json_tekst(
            p.get("embedding_picks_json", p.get("embedding_picks"))),
        "confidence": float(p.get("confidence") or 0.0),
        "threshold": float(p.get("threshold") or 0.0),
        "fallback_used": 1 if p.get("fallback_used") else 0,
        "fallback_reason": str(p.get("fallback_reason") or ""),
        "elapsed_ms": int(p.get("elapsed_ms") or 0),
        "tokens_saved_estimate": int(p.get("tokens_saved_estimate") or 0),
        # Tiden kommer fra HÆNDELSEN, aldrig fra now(): ellers ville en
        # genfoldning flytte hele sessionens beslutninger frem i tid.
        "created_at": str(p.get("created_at") or e.get("created_at") or ""),
    }


def _migrer(conn) -> None:
    """Doven migration: `decision_id` og dens unikke indeks.

    Samme mønster som `git_sha` i `chat_messages` — kolonnen står ikke i
    `CREATE TABLE`, så en frisk database har den ikke, og projektoren ville
    falde over sit første INSERT.
    """
    try:
        conn.execute("ALTER TABLE tool_router_decisions ADD COLUMN decision_id TEXT")
    except Exception:
        pass  # kolonnen findes allerede
    try:
        # IKKE partielt (`WHERE decision_id IS NOT NULL`): SQLite kan kun
        # bruge et FULDT unikt indeks som `ON CONFLICT`-maal, og et partielt
        # gav «does not match any PRIMARY KEY or UNIQUE constraint». Det er
        # ufarligt, fordi SQLite tæller NULL'er som forskellige fra hinanden —
        # de gamle rækker uden `decision_id` (1905 paa serveren 12/9) kolliderer
        # altsaa ikke.
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_tool_router_decisions_decision_id "
            "ON tool_router_decisions(decision_id)"
        )
    except Exception:
        logger.warning("projection_tool_router: kunne ikke oprette unikt indeks", exc_info=True)


def _skriv(raekke: dict[str, Any]) -> None:
    from core.runtime.db import connect
    sat = ", ".join(f"{k} = excluded.{k}" for k in _KOLONNER)
    with connect() as conn:
        _migrer(conn)
        conn.execute(
            "INSERT INTO tool_router_decisions "
            "(decision_id, run_id, session_id, lane, user_message_preview, "
            " selected_names_json, always_core_names_json, embedding_picks_json, "
            " confidence, threshold, fallback_used, fallback_reason, "
            " elapsed_ms, tokens_saved_estimate, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            f"ON CONFLICT(decision_id) DO UPDATE SET {sat}",
            (raekke["decision_id"], raekke["run_id"], raekke["session_id"],
             raekke["lane"], raekke["user_message_preview"],
             raekke["selected_names_json"], raekke["always_core_names_json"],
             raekke["embedding_picks_json"], raekke["confidence"],
             raekke["threshold"], raekke["fallback_used"],
             raekke["fallback_reason"], raekke["elapsed_ms"],
             raekke["tokens_saved_estimate"], raekke["created_at"]),
        )


def start() -> dict[str, Any]:
    """Formen ligger i STARTEN, ikke i den første fold — som `chat_messages`."""
    return {"skrevet": 0, "sprunget_over": 0, "afviste": []}


def fold(state: dict[str, Any], e: dict[str, Any]) -> dict[str, Any]:
    """Ren pr. hændelse og idempotent: samme hændelse igen ændrer ingenting."""
    if str(e.get("kind") or "") != KIND:
        state["sprunget_over"] += 1
        return state

    grund = valider(e.get("payload") or {})
    if grund is not None:
        state["afviste"].append({"event_id": e.get("event_id"), "grund": grund})
        logger.warning("projection_tool_router: afviste %s: %s", e.get("event_id"), grund)
        return state

    _skriv(_raekke(str(e["session_id"]), e))
    state["skrevet"] += 1
    return state


def register() -> None:
    from core.services.projection_runtime import register as _r
    _r(PROJEKTION, version=VERSION, fold=fold, start=start)


def rebuild(session_id: str) -> dict[str, Any]:
    """Genskab sessionens router-beslutninger fra hovedbogen.

    Kan de IKKE genskabes fra en tom projektion, er hovedbogen ikke sandheden
    — og så skal man ikke skifte.
    """
    from core.services import projection_runtime as pr
    if PROJEKTION not in pr.registered():
        register()
    return pr.project(session_id, PROJEKTION, force_refold=True)


# ── kun projektoren må skrive kompatibilitets-rækker ─────────────────────

from core.services.projection_guard import (  # noqa: E402
    DirekteSkrivningAfvist,  # noqa: F401  (re-eksporteret, som i chat_messages)
    guard_direct_write as _guard,
)


def guard_direct_write(session_id: str, *, conn=None) -> None:
    """Afvis direkte `tool_router_decisions`-skrivninger for en ledger-session.

    Uden den ville et skifte give TO rækker pr. beslutning: projektionens med
    udledt `decision_id`, og skrivestedets med NULL — som det fulde unikke
    indeks netop tillader.
    """
    _guard(session_id, projektion=PROJEKTION, tabel=TABEL, conn=conn)
