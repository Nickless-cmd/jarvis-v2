"""Active runs — hvad der kører lige nu, ud over mig selv.

HULLET (målt 28/10-2026). ``cross_session_arc`` er den eneste sektion der
handler om andre sessioner, og den viser FORTIDEN: hvad vi har lavet over de
sidste dage. Intet viste NUTIDEN. Samme dag kl. 17:31 skrev Jarvis «skal jeg
skrive til ham?» om en agent der lukkede side-opgaver — men «ham» var Jarvis
selv i en code-session der kørte samtidig. Brugeren måtte spørge «hvem er
ham?» to gange før det gik op. Kl. 13:22 samme dag blev et autonomt run
dispatchet midt i en levende samtale, uden at nogen af parterne kunne se at
sessionen var i brug.

FORMÅLET ER ORIENTERING, IKKE OVERVÅGNING: jeg skal vide hvor jeg er.

``active``-FLAGET KAN LYVE. Målt 28/10-2026 stod et run fra 27/10 kl. 20:47
stadig ``active: true`` — 1241 minutter gammelt, forladt af en proces der
ikke længere findes. Derfor er flaget aldrig nok alene: hvert flag
kryds-verificeres mod ``visible_runs.status = 'running'``, som er den ægte
sandhed. Et flag uden ``running``-status er en lækage og nævnes ikke som
aktiv — en falsk prompt-sektion er værre end ingen, fordi jeg ville handle
på den.

Procedural — ingen LLM-kald. Self-safe: kaster aldrig, returnerer ``None``.

Awareness-prioritet: 17 — lige over ``cross-session arc`` (18), fordi den
handler om NU hvor arc'en handler om da. Under fejl, narrative-now og
pattern-refleksioner, som skal have budgettet først.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from core.runtime.db import connect

logger = logging.getLogger(__name__)

_CONTROL_PREFIX = "visible_runs.control."

# Loft. QUICK_FACTS-fælden: en sektion uden synligt loft bliver tavst klippet,
# og det der forsvinder er slutningen — altså det nyeste run.
_MAX_RUNS = 3
_MAX_CHARS = 220

# Et run der har kørt længere end agent-loopets eget budget er ikke «hvad der
# sker nu» — det er sandsynligvis hængt. Grænsen matcher
# `agent_worker_runner.DEFAULT_TIMEOUT_S = 4 * 3600.0`, så et legitimt langt
# autonomt run ikke skjules.
_MAX_AGE_MINUTES = 240.0

# Sessioner der ikke er en bruger-samtale, og som derfor ikke kan være «en
# anden session» i nogen meningsfuld forstand.
_IKKE_SESSIONER = frozenset({"__prewarm__"})


def _alder_minutter(streng: object) -> float | None:
    """Alder i minutter fra en ISO-streng, eller None hvis den ikke kan læses."""
    if not streng:
        return None
    try:
        d = datetime.fromisoformat(str(streng))
    except (TypeError, ValueError):  # self-safe: ulæseligt tidsstempel = ukendt alder, ikke en fejl
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return (datetime.now(UTC) - d).total_seconds() / 60.0


def _kort_alder(minutter: float) -> str:
    m = max(0, int(minutter))
    if m < 60:
        return f"{m} min"
    return f"{m // 60}t {m % 60}m"


def _kort_titel(titel: object, session_id: str) -> str:
    t = str(titel or "").strip()
    if not t:
        return session_id[:16]
    if len(t) > 40:
        t = t[:37].rstrip() + "…"
    return t


def _aktive_kandidater() -> list[tuple[str, dict]]:
    """(run_id, control-payload) for hvert flag der står ``active``.

    Læser hele ``visible_runs.%`` og filtrerer i Python: ``_`` er wildcard i
    LIKE, så et mønster med ``visible_runs.control.`` i ville matche mere end
    tilsigtet.
    """
    with connect() as conn:
        rows = conn.execute(
            "SELECT key, value_json FROM runtime_state_kv "
            "WHERE key LIKE 'visible_runs.%'"
        ).fetchall()
    ud: list[tuple[str, dict]] = []
    for r in rows:
        key = str(r["key"] or "")
        if not key.startswith(_CONTROL_PREFIX):
            continue
        try:
            payload = json.loads(r["value_json"])
        except (TypeError, ValueError):  # self-safe: én rå værdi må ikke skjule de øvrige runs
            continue
        if not isinstance(payload, dict) or not payload.get("active"):
            continue
        ud.append((key[len(_CONTROL_PREFIX):], payload))
    return ud


def _levende_runs(run_ids: list[str]) -> dict[str, str]:
    """run_id → started_at, men KUN for dem der reelt er ``running``.

    Det er her lækagen frasorteres: et flag uden en ``running``-row er et
    levn, ikke et run.
    """
    if not run_ids:
        return {}
    pladsholdere = ",".join("?" * len(run_ids))
    with connect() as conn:
        rows = conn.execute(
            f"SELECT run_id, status, started_at FROM visible_runs "  # noqa: S608 — kun «?»-pladsholdere
            f"WHERE run_id IN ({pladsholdere})",
            run_ids,
        ).fetchall()
    ud: dict[str, str] = {}
    for r in rows:
        if str(r["status"] or "") != "running":
            continue
        ud[str(r["run_id"])] = str(r["started_at"] or "")
    return ud


def _titler(session_ids: list[str]) -> dict[str, str]:
    if not session_ids:
        return {}
    pladsholdere = ",".join("?" * len(session_ids))
    with connect() as conn:
        rows = conn.execute(
            f"SELECT session_id, title FROM chat_sessions "  # noqa: S608 — kun «?»-pladsholdere
            f"WHERE session_id IN ({pladsholdere})",
            session_ids,
        ).fetchall()
    return {str(r["session_id"]): str(r["title"] or "") for r in rows}


def active_runs_section(session_id: str | None = None) -> str | None:
    """Andre sessioner der kører lige nu, eller ``None`` når der ikke gør.

    ``None`` — ikke en tom streng og ikke en «0 runs»-linje — fordi en sektion
    der altid er der bliver støj jeg lærer at springe over.

    Uden ``session_id`` returneres ``None``: jeg kan ikke sige hvad der er
    «andre», hvis jeg ikke ved hvor jeg selv er. At gætte ville være værre end
    at tie.
    """
    try:
        egen = str(session_id or "").strip()
        if not egen or egen in _IKKE_SESSIONER:
            return None

        kandidater = [k for k in _aktive_kandidater() if k[0]]
        if not kandidater:
            return None

        levende = _levende_runs([rid for rid, _ in kandidater])
        if not levende:
            return None

        fundet: list[tuple[float, str, str]] = []
        for run_id, payload in kandidater:
            started = levende.get(run_id)
            if started is None:
                continue  # flag uden running-status = lækage
            alder = _alder_minutter(payload.get("last_activity_at") or started)
            if alder is None or alder > _MAX_AGE_MINUTES:
                continue  # for gammel til at være «nu»
            sess = str(payload.get("session_id") or "")
            if not sess or sess == egen:
                continue  # det er mig — det ved jeg godt
            lane = str(payload.get("lane") or "primary")
            fundet.append((alder, sess, lane))

        if not fundet:
            return None

        fundet.sort(key=lambda x: x[0])
        titler = _titler(sorted({s for _, s, _ in fundet}))
        vist = fundet[:_MAX_RUNS]

        linjer = [f"Andre sessioner kører nu ({len(fundet)}):"]
        for alder, sess, lane in vist:
            linjer.append(
                f"- «{_kort_titel(titler.get(sess), sess)}» · {lane} · "
                f"{_kort_alder(alder)}"
            )
        if len(fundet) > len(vist):
            linjer.append(f"- …og {len(fundet) - len(vist)} mere")

        tekst = "\n".join(linjer)
        if len(tekst) > _MAX_CHARS:
            tekst = tekst[: _MAX_CHARS - 1].rstrip() + "…"
        return tekst
    except Exception as exc:  # self-safe: en sektions-fejl må ikke vælte prompten
        logger.debug("active_runs: sektionen kunne ikke bygges: %s", exc)
        return None
