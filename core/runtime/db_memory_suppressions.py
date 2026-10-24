"""Undertrykkelse af erindringer — «don't mention this again».

## Hvorfor (målt 24/10-2026)

Memory-fladen i Desk kunne VISE hvad Jarvis husker, men ikke ændre det. Der
fandtes ingen mekanisme til at sige «det her skal du holde op med at bruge»:
de `suppress`-fund der ligger i koden handler om signal-dæmpning (flood,
attention, lease), ikke om brugerstyret glemsel.

Uden den er den eneste vej til at fjerne en forkert erindring at redigere
MEMORY.md i hånden — og det er ikke en flade, det er et indgreb.

## Hvad den gør

En række pr. (bruger, emne) med en grund. Undertrykkelsen er en FILTER, ikke
en sletning: intet går tabt, og den kan ophæves igen. Det er med vilje —
en sletning kan ikke fortrydes, og en bruger der fortryder skal ikke have
mistet noget.

Filtrene læses af `er_undertrykt()` og kan kaldes fra recall-laget.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect

_TABLE = "memory_suppressions"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def ensure_table() -> None:
    """Opret tabellen hvis den ikke findes. Idempotent."""
    with connect() as conn:
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS {_TABLE} (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                emne TEXT NOT NULL,
                grund TEXT,
                created_at TEXT NOT NULL,
                lifted_at TEXT
            )"""
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_user "
            f"ON {_TABLE}(user_id, lifted_at)"
        )


def suppress(*, user_id: str, emne: str, grund: str = "") -> dict[str, Any]:
    """Undertryk et emne for en bruger. Returnerer rækken som den blev skrevet."""
    emne = " ".join(str(emne or "").split()).strip()
    if not emne:
        return {"status": "error", "error": "emne er påkrævet"}
    ensure_table()
    rid = f"sup_{uuid.uuid4().hex[:12]}"
    now = _now()
    with connect() as conn:
        conn.execute(
            f"INSERT INTO {_TABLE} (id, user_id, emne, grund, created_at, lifted_at) "
            "VALUES (?, ?, ?, ?, ?, NULL)",
            (rid, str(user_id or ""), emne, str(grund or ""), now),
        )
    return {"status": "ok", "id": rid, "emne": emne, "created_at": now}


def lift(*, user_id: str, suppression_id: str) -> dict[str, Any]:
    """Ophæv en undertrykkelse. Rækken bevares med `lifted_at` sat."""
    ensure_table()
    now = _now()
    with connect() as conn:
        cur = conn.execute(
            f"UPDATE {_TABLE} SET lifted_at = ? WHERE id = ? AND user_id = ? "
            "AND lifted_at IS NULL",
            (now, suppression_id, str(user_id or "")),
        )
        if cur.rowcount == 0:
            return {"status": "error", "error": "ikke fundet eller allerede ophævet"}
    return {"status": "ok", "id": suppression_id, "lifted_at": now}


def list_active(*, user_id: str) -> list[dict[str, Any]]:
    """Aktive undertrykkelser for brugeren, nyeste først."""
    ensure_table()
    with connect() as conn:
        rows = conn.execute(
            f"SELECT id, emne, grund, created_at FROM {_TABLE} "
            "WHERE user_id = ? AND lifted_at IS NULL ORDER BY created_at DESC",
            (str(user_id or ""),),
        ).fetchall()
    return [
        {"id": r[0], "emne": r[1], "grund": r[2], "created_at": r[3]}
        for r in rows
    ]


def er_undertrykt(*, user_id: str, tekst: str) -> list[str]:
    """Hvilke aktive undertrykkelser rammer `tekst`? Tom liste = ingen.

    Simpel delstreng-matchning, med vilje: en semantisk match ville kunne
    undertrykke noget brugeren ikke bad om. Hellere for lidt end for meget.
    """
    tekst_lav = str(tekst or "").lower()
    if not tekst_lav:
        return []
    ramte: list[str] = []
    for rad in list_active(user_id=user_id):
        emne = str(rad.get("emne") or "").lower()
        if emne and emne in tekst_lav:
            ramte.append(rad["emne"])
    return ramte
