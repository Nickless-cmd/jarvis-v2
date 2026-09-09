"""Efterfyld en session i ledgeren og slå skyggen til.

## Hvorfor efterfyldningen skal ske FØRST

En session der har kørt i månedsvis har hundredvis af beskeder i
`chat_messages` som ledgeren aldrig har set. Slog man bare skyggen til, ville
ledgeren have 3 beskeder og tabellen 300 — drift-detektionen ville melde
uenighed for altid, og porten til et skifte ville aldrig kunne åbne. Skyggen
ville måle ingenting.

Så: skriv historikken ind, og slå SÅ skyggen til. Rækkefølgen er ikke en
detalje. Gjorde man det omvendt, ville nye beskeder få lave sekvensnumre og
historikken lande bagved dem — samme samtale, forkert orden, og en uenighed
der ligner data-tab men er en fejl i overførslen.

## Hvorfor den kan køres igen

`event_id` er beskedens eget `message_id`. En gentagen efterfyldning bliver
derfor til nul nye hændelser. Det er med vilje: det farlige øjeblik er ikke
det første forsøg, men det andet — når nogen er i tvivl om det gik godt.

## Vinduet imellem

Mellem sidste efterfyldte besked og skiftet til `shadow` er der et øjeblik
hvor en ny besked kun lander i tabellen. Derfor rapporterer denne funktion
drift MED DET SAMME bagefter: er der uenighed, er den opdaget i samme minut,
og skyggen kan slås fra igen med `abandon_shadow`.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Felterne der udgør en besked. `git_sha` er en DOVEN kolonne — den står ikke
#: i CREATE TABLE, kun i en migration der køres af den der skriver
#: kompakt-markører. En frisk database har den ikke, så listen skæres ned til
#: det tabellen FAKTISK har frem for at antage en form.
_FELTER = ("message_id", "role", "content", "user_id", "workspace_name",
           "reasoning_content", "git_sha", "content_json", "created_at")


def _kolonner(conn) -> list[str]:
    findes = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)")}
    return [k for k in _FELTER if k in findes]


def backfill(session_id: str) -> dict[str, Any]:
    """Skriv sessionens eksisterende beskeder ind i ledgeren. Idempotent."""
    from core.runtime.db import connect
    from core.runtime.db_session_ledger import (
        acquire_write_lease, append_session_events, release_write_lease,
    )

    sid = str(session_id or "").strip()
    with connect() as conn:
        kols = _kolonner(conn)
        rows = conn.execute(
            f"SELECT {', '.join(kols)} FROM chat_messages WHERE session_id = ? "
            "ORDER BY id", (sid,)
        ).fetchall()
    if not rows:
        return {"session_id": sid, "beskeder": 0, "skrevet": 0,
                "grund": "sessionen har ingen beskeder"}

    haendelser = []
    for r in rows:
        p = {k: r[i] for i, k in enumerate(kols)}
        haendelser.append({"event_id": str(p["message_id"]),
                           "kind": "message", "payload": p})

    token = acquire_write_lease(sid, owner="canary_backfill")
    if token is None:
        return {"session_id": sid, "beskeder": len(rows), "skrevet": 0,
                "grund": "en anden proces holder leasen"}
    try:
        r = append_session_events(sid, owner="canary_backfill",
                                  token=token, events=haendelser)
    finally:
        release_write_lease(sid, owner="canary_backfill", token=token)
    return {"session_id": sid, "beskeder": len(rows),
            "skrevet": r["written"], "dubletter": r["duplicates"]}


def enable_shadow(session_id: str) -> dict[str, Any]:
    """Efterfyld, slå skyggen til, og MÅL med det samme om det holdt."""
    from core.runtime.db_session_ledger import advance_storage_mode, storage_mode
    from core.services.projection_drift import compare

    sid = str(session_id or "").strip()
    nu = storage_mode(sid)
    if nu != "legacy":
        return {"session_id": sid, "ok": False, "grund": f"sessionen er allerede {nu!r}"}

    fyld = backfill(sid)
    if fyld.get("grund") and fyld["skrevet"] == 0 and fyld["beskeder"] == 0:
        return {"session_id": sid, "ok": False, "grund": fyld["grund"], "backfill": fyld}

    if not advance_storage_mode(sid, to="shadow"):
        return {"session_id": sid, "ok": False,
                "grund": "kunne ikke skifte til shadow — findes sessionen?",
                "backfill": fyld}

    # Måles NU, ikke om en uge. Vinduet mellem efterfyldning og skifte er kort,
    # men det findes, og en uenighed skal opdages i samme minut.
    d = compare(sid)
    return {"session_id": sid, "ok": bool(d["enige"]), "backfill": fyld,
            "drift": {"enige": d["enige"], "ledger": d["ledger_beskeder"],
                      "tabel": d["tabel_beskeder"],
                      "uenigheder": d["uenigheder"][:5]}}
