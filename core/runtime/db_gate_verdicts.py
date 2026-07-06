"""Gate-verdict-ledger — PERSISTENT optælling af hvert governet gate-udfald.

`central().decide` fælder et Verdict (green/yellow/red/skip) pr. kald. Fordelingen af
de verdicts er ground-truth for beslutningen "kan denne gate flippes fra shadow til
enforce?" — men den levede kun i den in-memory tidsserie (`central_timeseries`), som er
per-proces og TABES ved genstart. Efter en runtime-restart står vi uden data.

Denne tabel PERSISTERER en aggregeret tæller pr. (nerve, decision) så en uges verdicts
overlever genstarter og kan læses på tværs af processer (jarvis-api + jarvis-runtime).
Skrivning sker BATCHET (via gate_verdict_ledger.flush på cadence) — aldrig i decide-hot-
pathen — så vi ikke genindfører connect()-churn (DB #1, 6. jul).

Selv-sikker: alle skrive-/læse-fejl sluges (en statistik-tæller må ALDRIG vælte runtime).
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect

# Kanoniske decision-værdier (Decision.value). Andre sluges ikke — de gemmes som-de-er,
# men dette er forventnings-sættet til rapportering.
_DECISIONS = ("green", "yellow", "red", "skip")


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gate_verdict_counts (
            nerve TEXT NOT NULL,
            cluster TEXT NOT NULL DEFAULT '',
            decision TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            last_ts TEXT NOT NULL DEFAULT '',
            last_reason TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (nerve, decision)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gate_verdict_nerve "
        "ON gate_verdict_counts (nerve, decision)"
    )


def apply_deltas(deltas: list[dict[str, Any]]) -> int:
    """UPSERT en batch af akkumulerede tæller-deltas. Returnerer antal rækker rørt.

    Hvert delta: {nerve, cluster, decision, count, last_ts, last_reason}. Én DB-tur for
    hele batchen. Selv-sikker — returnerer 0 ved fejl.
    """
    if not deltas:
        return 0
    try:
        with connect() as conn:
            _ensure_table(conn)
            n = 0
            for d in deltas:
                try:
                    conn.execute(
                        """
                        INSERT INTO gate_verdict_counts
                            (nerve, cluster, decision, count, last_ts, last_reason)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(nerve, decision) DO UPDATE SET
                            count = count + excluded.count,
                            cluster = excluded.cluster,
                            last_ts = excluded.last_ts,
                            last_reason = excluded.last_reason
                        """,
                        (
                            str(d.get("nerve") or ""),
                            str(d.get("cluster") or ""),
                            str(d.get("decision") or ""),
                            int(d.get("count") or 0),
                            str(d.get("last_ts") or datetime.now(UTC).isoformat()),
                            str(d.get("last_reason") or "")[:240],
                        ),
                    )
                    n += 1
                except Exception:
                    continue
            conn.commit()
            return n
    except Exception:
        return 0


def read_counts(nerve: str | None = None) -> list[dict[str, Any]]:
    """Læs aggregerede tællere. Filtrér på nerve hvis givet. Selv-sikker → [] ved fejl."""
    try:
        with connect() as conn:
            _ensure_table(conn)
            if nerve:
                rows = conn.execute(
                    "SELECT nerve, cluster, decision, count, last_ts, last_reason "
                    "FROM gate_verdict_counts WHERE nerve = ? ORDER BY decision",
                    (nerve,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT nerve, cluster, decision, count, last_ts, last_reason "
                    "FROM gate_verdict_counts ORDER BY nerve, decision"
                ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def summary() -> dict[str, dict[str, Any]]:
    """Aggregér pr. nerve: {nerve: {cluster, total, green, yellow, red, skip,
    non_green_pct, last_ts}}. Til flip-beslutning + CLI/rapport. Selv-sikker."""
    out: dict[str, dict[str, Any]] = {}
    for row in read_counts():
        nerve = row["nerve"]
        entry = out.setdefault(
            nerve,
            {"cluster": row.get("cluster", ""), "total": 0,
             "green": 0, "yellow": 0, "red": 0, "skip": 0, "last_ts": ""},
        )
        dec = row["decision"]
        cnt = int(row["count"] or 0)
        entry["total"] += cnt
        if dec in _DECISIONS:
            entry[dec] += cnt
        if row.get("last_ts", "") > entry["last_ts"]:
            entry["last_ts"] = row["last_ts"]
        if row.get("cluster"):
            entry["cluster"] = row["cluster"]
    for entry in out.values():
        total = entry["total"] or 1
        non_green = entry["total"] - entry["green"]
        entry["non_green_pct"] = round(100.0 * non_green / total, 2)
    return out
