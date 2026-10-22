"""Læseren for breach-events — den manglende anden halvdel af sløjfen.

MÅLT 22/10-2026: `decision_enforcement.detect_breach_in_output` skrev
`decision_breach_recent` (state_store) og publicerede `decision.breach_detected`.
**Ingen læste nogen af dem tilbage.** 1.568 events over tid, 90 den 22/10 — og
ingen beslutning ændrede sig af at blive brudt. Uden en læser er det en log,
ikke en læringssløjfe.

Denne modul er læseren. Den leverer tre ting:

1. ``breach_stats()`` — antal brud, seneste tidspunkt og alder pr. beslutning.
2. ``breach_line()`` — én kort linje til trigger-injektionen, så den beslutning
   der netop fyrede bærer sit eget brud-tal med sig.
3. ``classify()`` / ``health_report()`` — skiller de tre egenskaber ad, så ét
   tal ikke længere betyder tre forskellige ting:

   * **EKSEKVERBAR** — kan gaten eller en trigger overhovedet handle på den?
     (har ``trigger_name`` eller et direktiv gaten kan matche)
   * **MÅLBAR** — findes der en hændelse at vurdere imod?
     (``adherence_score`` er sat, eller der er registreret mindst ét brud)
   * **EFTERLEVET** — blev den fulgt? (kun ``adherence_score``; brud er
     mistanker, ikke domme)

Kilden er ``decision_breach_recent``: LLM-mistanker, ikke verificerede udfald.
De bruges derfor som SIGNAL — en beslutning der brydes ofte er ikke eksekverbar
som skrevet — aldrig som erstatning for den målte ``adherence_score``.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.state_store import load_json

#: Samme nøgle som `decision_enforcement` skriver til. Den står her som en
#: konstant og ikke som en import, fordi enforcement importerer os (lazy) —
#: en top-import ville lukke en cirkel.
RECENT_KEY = "decision_breach_recent"

#: Hvor langt tilbage et brud tæller som «stadig relevant adfærd».
VINDUE_DAGE = 14

#: Antal brud i vinduet hvor en ALDRIG MÅLT beslutning behandles som svag.
#: Tre er valgt fordi ét brud kan være dommerens fejl (kilden kalder dem selv
#: «suspicions»), mens tre uafhængige er et mønster.
BRUD_TAERSKEL_LAV = 3


def _records() -> list[dict[str, Any]]:
    """Læs de rå brud-records. Aldrig en undtagelse — tom liste ved fejl."""
    try:
        raw = load_json(RECENT_KEY, [])
    except Exception:  # korrupt state-fil må ikke vælte gaten — tom liste = ingen brud
        return []
    if not isinstance(raw, list):
        return []
    return [r for r in raw if isinstance(r, dict) and r.get("decision_id")]


def _alder_timer(iso_ts: str, *, now: datetime) -> float | None:
    try:
        dt = datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):  # ugyldigt tidsstempel = ukendt alder, ikke et gæt
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return max(0.0, (now - dt).total_seconds() / 3600.0)


def breach_stats(
    *,
    window_days: int = VINDUE_DAGE,
    now: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    """Aggregér brud pr. beslutning inden for vinduet.

    Returnerer ``{decision_id: {count, last_at, age_hours}}``. Beslutninger uden
    brud i vinduet optræder ikke — fravær er ``.get(id, {})``, ikke et nul der
    kan forveksles med «målt nul».
    """
    nu = now or datetime.now(UTC)
    graense = nu - timedelta(days=max(1, int(window_days)))
    ud: dict[str, dict[str, Any]] = {}
    for r in _records():
        did = str(r.get("decision_id") or "").strip()
        if not did:
            continue
        at_raw = str(r.get("at") or "")
        alder = _alder_timer(at_raw, now=nu)
        if alder is None:
            continue
        at_dt = nu - timedelta(hours=alder)
        if at_dt < graense:
            continue
        post = ud.setdefault(did, {"count": 0, "last_at": None, "age_hours": None})
        post["count"] = int(post["count"]) + 1
        if post["last_at"] is None or alder < float(post["age_hours"] or 1e9):
            post["last_at"] = at_raw
            post["age_hours"] = round(alder, 2)
    return ud


def breach_line(
    decision_id: str,
    stats: dict[str, dict[str, Any]] | None = None,
) -> str | None:
    """Én kort linje til trigger-injektionen, eller ``None`` uden brud."""
    s = (stats if stats is not None else breach_stats()).get(str(decision_id))
    if not s:
        return None
    count = int(s.get("count") or 0)
    if count <= 0:
        return None
    alder = s.get("age_hours")
    if isinstance(alder, (int, float)):
        if alder < 1:
            hvornaar = "inden for den seneste time"
        elif alder < 24:
            hvornaar = f"for {int(alder)}t siden"
        else:
            hvornaar = f"for {int(alder // 24)}d siden"
        return f"{count} brud set, seneste {hvornaar}"
    return f"{count} brud set"


def _direktiv_har_gate_maal(directive: str) -> bool:
    """Kan gaten overhovedet matche dette direktiv?

    Genbruger `decision_gate.directive_har_maal` når den findes, så
    EKSEKVERBAR ikke driver fra den faktiske matcher. Lazy import: gaten
    importerer os.
    """
    try:
        from core.services.decision_gate import directive_har_maal
    except Exception:  # gaten kan ikke importeres (delvis installation) — brug det lokale mønster
        return bool(re.search(
            r"\b(undgå|undlad|ikke|stop|avoid|don'?t|never|altid|always)\b",
            str(directive or "").lower(),
        ))
    return bool(directive_har_maal(directive))


def classify(
    decision: dict[str, Any],
    stats: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Klassificér ÉN beslutning i de tre egenskaber.

    ``adhered`` er ``None`` når beslutningen ikke er målbar — ikke 0,0. Et nul
    ville påstå at den blev brudt hver gang; ``None`` siger sandheden: vi ved
    det ikke.
    """
    did = str(decision.get("decision_id") or "")
    directive = str(decision.get("directive") or "")
    s = (stats if stats is not None else breach_stats()).get(did) or {}
    brud = int(s.get("count") or 0)

    executable = bool(str(decision.get("trigger_name") or "").strip()) or (
        _direktiv_har_gate_maal(directive)
    )
    adh_raw = decision.get("adherence_score")
    maalt = adh_raw is not None
    measurable = bool(maalt or brud > 0)

    adhered: float | None
    if maalt:
        try:
            adhered = round(float(adh_raw), 3)
        except (TypeError, ValueError):
            adhered = None
    else:
        adhered = None

    # Svaghed: målt lav, ELLER aldrig målt men et mønster af brud.
    svag = (adhered is not None and adhered < 0.4) or (not maalt and brud >= BRUD_TAERSKEL_LAV)

    return {
        "decision_id": did,
        "executable": executable,
        "measurable": measurable,
        "adhered": adhered,
        "breaches": brud,
        "last_breach_age_hours": s.get("age_hours"),
        "weak": svag,
        "why_weak": (
            f"målt {adhered:.0%}" if adhered is not None and svag
            else f"aldrig målt, men {brud} brud i {VINDUE_DAGE} dage" if svag
            else None
        ),
    }


def health_report(
    decisions: list[dict[str, Any]] | None = None,
    *,
    stats: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregat over alle aktive beslutninger — og en ærlig opgørelse af huller.

    De tre tællinger er bevidst ikke slået sammen: et gennemsnit af
    ``adherence_score`` er kun et mål for den DEL af systemet der bliver målt.
    """
    if decisions is None:
        try:
            from core.services.behavioral_decisions import list_active_decisions
            decisions = list_active_decisions(limit=500) or []
        except Exception:
            decisions = []
    s = stats if stats is not None else breach_stats()
    rows = [classify(d, s) for d in decisions]

    maalte = [r["adhered"] for r in rows if r["adhered"] is not None]
    aldrig_maalt = [r for r in rows if r["adhered"] is None]
    return {
        "total": len(rows),
        "executable": sum(1 for r in rows if r["executable"]),
        "measurable": sum(1 for r in rows if r["measurable"]),
        "adhered": sum(1 for r in rows if r["adhered"] is not None),
        "mean_adhered": round(sum(maalte) / len(maalte), 3) if maalte else None,
        "never_measured": len(aldrig_maalt),
        # De «aldrig målt» er ikke én gruppe: nogle har brud (adfærd findes),
        # andre har hverken dom eller brud (intet at vide). At blande dem var
        # netop fejlen der gjorde 0,726 til et mål for den kiggede del.
        "never_measured_with_breaches": sum(
            1 for r in aldrig_maalt if int(r["breaches"]) > 0
        ),
        "never_measured_without_signal": sum(
            1 for r in aldrig_maalt if int(r["breaches"]) == 0
        ),
        "weak": sum(1 for r in rows if r["weak"]),
        "rows": rows,
    }
