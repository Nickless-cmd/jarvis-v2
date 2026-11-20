"""TTFT og tok/s pr. run — målt hos OS, gemt så det kan måles over tid.

## Hvorfor den findes

MÅLT 20/11-2026: `svar_tempo` målte TTFT og tok/s korrekt, men udlæsningen gik
KUN i SSE-payloaden til composeren (`visible_runs_sse_v2.py:1035` og `:1183`).
Der fandtes ingen tabel og intet `INSERT`. Tallet levede i under et sekund,
blev tegnet i composeren og forsvandt.

Konsekvensen var ikke et manglende tal i UI'et — det var at domænet «streaming
og perceived performance» ikke KUNNE måles. Det stod på 42 % gennem 1.027
vektorer, og de 42 % var modellens eget skøn. Samme fejlform som
`X-Jarvis-Build` (25/10-2026): en måling der findes i den ene ende og aldrig
læses i den anden.

## Hvad der IKKE gemmes her

Total tur-tid. Den findes allerede i `visible_runs.started_at/finished_at`, men
den måler noget andet: hele agent-loopet inklusive værktøjskald. Målt 20/11-2026
var medianen for synlige ture 98,1 sekunder — det er ikke den ventetid man
mærker før det første tegn. TTFT er det tal der beskriver *perceived*
performance, og det er derfor netop dét der skulle gemmes.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect

logger = logging.getLogger(__name__)


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS svar_tempo_maalinger (
            run_id        TEXT PRIMARY KEY,
            ttft_ms       REAL,
            tok_per_sek   REAL,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_svar_tempo_created"
        " ON svar_tempo_maalinger(created_at)"
    )


def gem(
    run_id: str,
    *,
    ttft_ms: float | None,
    tok_per_sek: float | None,
    output_tokens: int = 0,
) -> bool:
    """Gem én måling. Returnerer True hvis den landede.

    `run_id` er PRIMARY KEY med vilje: begge SSE-veje (normal afslutning og
    gendannelse) kan nå at aflæse samme run, og en dublet ville tælle turen
    to gange i medianen. `INSERT OR REPLACE` gør det til en opdatering.

    En måling uden TTFT gemmes ikke. `None` betyder «uret nåede ikke at se et
    token» — ikke «0 ms» — og en række med NULL ville trække medianen mod nul
    for hver tur der døde undervejs.
    """
    rid = str(run_id or "").strip()
    if not rid or ttft_ms is None:
        return False
    try:
        with connect() as conn:
            _ensure(conn)
            conn.execute(
                """
                INSERT OR REPLACE INTO svar_tempo_maalinger
                    (run_id, ttft_ms, tok_per_sek, output_tokens, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    rid,
                    float(ttft_ms),
                    float(tok_per_sek) if tok_per_sek is not None else None,
                    int(output_tokens or 0),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return True
    except Exception as exc:  # noqa: BLE001
        # En måling der ikke kunne gemmes må ikke vælte den tur den måler.
        # Vi logger med run_id, så et systematisk frafald kan ses i loggen
        # frem for at give et tavst hul i historikken.
        logger.warning("tempo: kunne ikke gemme måling for %s: %s", rid, exc)
        return False


def seneste(*, limit: int = 200) -> list[dict[str, Any]]:
    """De nyeste målinger, nyeste først."""
    try:
        with connect() as conn:
            _ensure(conn)
            rows = conn.execute(
                """
                SELECT run_id, ttft_ms, tok_per_sek, output_tokens, created_at
                FROM svar_tempo_maalinger
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        # En ulaeselig tabel er ikke «nul målinger». Kalderen skal kunne
        # skelne, så fejlen bæres videre som en tom liste PLUS en loglinje.
        logger.warning("tempo: kunne ikke laese maalinger: %s", exc)
        return []
    return [dict(row) for row in rows]


__all__ = ["gem", "seneste"]
