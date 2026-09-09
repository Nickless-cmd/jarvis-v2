"""Afbrudte sessioner: se på dem uden at røre dem, og luk dem kun med skriveret.

Spec: Fase 1 — «read-only interrupted-session inspection writes nothing;
recovery appends balancing events only under write ownership».

## Hvorfor de to halvdele hører sammen

Den hyppigste grund til at kigge på en afbrudt session er at finde ud af hvad
der gik galt i den. Hvis det at KIGGE kræver skriveretten, sker ét af to: enten
tager man den fra den proces der stadig arbejder, eller også lader man være med
at kigge. Begge dele er værre end problemet.

Så: `inspect()` tager ingen lease, skriver ingen række, opretter ingen tabel.
`recover()` skriver — og kan derfor kun gøre det gennem et handle med lease og
fencing-mønt.

## Hvad «ubalanceret» betyder

En tur består af en brugerbesked og et svar. Slutter ledgeren på en
brugerbesked, blev der aldrig svaret: processen døde, streamen brast, eller
turen blev afbrudt. Rækken findes, men samtalen står åben.

Det er ikke en fejl der skal RETTES — beskeden er rigtig. Det er en tilstand
der skal SIGES, så den næste der læser sessionen, ved at det sidste ord ikke
var det sidste ord.

## Hvorfor en balancerende hændelse frem for en rettelse

Ledgeren er append-only. En afbrudt tur bliver ikke ugjort ved at slette den —
det ville være at lyve om hvad der skete. I stedet tilføjes en hændelse der
siger «denne tur blev aldrig lukket». Historikken bliver længere og sandere,
aldrig kortere.

Hændelsen er `kind="turn_abandoned"`, ikke en besked, så projektoren springer
den over: den skal ikke blive til en række i samtalen. Den er til den der
læser ledgeren, ikke til den der læser chatten.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

BALANCE_KIND = "turn_abandoned"


def inspect(session_id: str) -> dict[str, Any]:
    """Se på sessionen UDEN at røre den. Tager ingen lease, skriver intet."""
    from core.runtime.db_session_ledger import read_session_events, storage_mode
    from core.runtime.session_handle import classify_format

    sid = str(session_id or "").strip()
    haendelser = read_session_events(sid)
    beskeder = [e for e in haendelser if e["kind"] == "message"]
    balancer = {e["payload"].get("for_seq") for e in haendelser
                if e["kind"] == BALANCE_KIND}

    sidste = beskeder[-1] if beskeder else None
    rolle = str(sidste["payload"].get("role") or "") if sidste else ""
    ubalanceret = bool(sidste) and rolle == "user" and sidste["seq"] not in balancer

    return {
        "session_id": sid,
        "storage_mode": storage_mode(sid),
        "format": classify_format(sid),
        "haendelser": len(haendelser),
        "beskeder": len(beskeder),
        "sidste_rolle": rolle,
        "sidste_seq": sidste["seq"] if sidste else 0,
        "ubalanceret": ubalanceret,
        "allerede_balanceret": len(balancer),
    }


def recover(session_id: str, *, owner: str = "recovery",
            grund: str = "turen blev aldrig lukket") -> dict[str, Any]:
    """Luk en åben tur med en balancerende hændelse. Kræver skriveret.

    Gør INTET hvis turen ikke er åben — en genopretning der «for en sikkerheds
    skyld» tilføjer en hændelse, ville gøre historikken usand.
    """
    from core.runtime.session_handle import open_for_write

    sid = str(session_id or "").strip()
    f = inspect(sid)
    if not f["ubalanceret"]:
        return {"session_id": sid, "skrevet": False,
                "grund": "ingen åben tur at lukke", "fund": f}

    h = open_for_write(sid, owner=owner)
    if not h.writable:
        # Uden ejerskab skrives der IKKE. Punktum — det er hele forskellen på
        # at inspicere og at genoprette.
        return {"session_id": sid, "skrevet": False,
                "grund": f"ingen skriveret (format={h.format!r})", "fund": f}
    with h:
        h.append({
            "event_id": f"balance-{sid}-{f['sidste_seq']}",
            "kind": BALANCE_KIND,
            "payload": {"for_seq": f["sidste_seq"], "grund": str(grund),
                        "noteret": datetime.now(UTC).isoformat()},
        })
    return {"session_id": sid, "skrevet": True, "for_seq": f["sidste_seq"],
            "fund": f}
