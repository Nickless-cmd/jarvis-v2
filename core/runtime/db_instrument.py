"""Persistens for central_instrument — selv-instrumenterings-motorens fund + scan-cache.

To tabeller:
  central_instrument_findings — ét fund pr. signatur (silent-failure-mønster i koden), med
    score + status. Overlever genstart; Claude/Jarvis poller den, proposals filer fra den.
  central_instrument_filehash — pr. fil: indholds-hash + sidste scan, så scanningen er
    INCREMENTAL (kun ændrede filer re-scannes). Deterministisk (hash, ikke tid).

Self-sikker: alle skrive-/læse-fejl sluges (en kode-scanner må aldrig vælte runtime).
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_instrument_findings (
            signature TEXT PRIMARY KEY,
            file TEXT NOT NULL DEFAULT '',
            line INTEGER NOT NULL DEFAULT 0,
            kind TEXT NOT NULL DEFAULT '',
            severity TEXT NOT NULL DEFAULT '',
            score INTEGER NOT NULL DEFAULT 0,
            function TEXT NOT NULL DEFAULT '',
            snippet TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open',
            first_seen TEXT NOT NULL DEFAULT '',
            last_seen TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_instrument_findings_live "
        "ON central_instrument_findings (status, score DESC, severity)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_instrument_filehash (
            file TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL DEFAULT '',
            n_findings INTEGER NOT NULL DEFAULT 0,
            last_scan TEXT NOT NULL DEFAULT ''
        )
        """
    )


def get_file_hash(file: str) -> str | None:
    """Sidst-scannede indholds-hash for en fil (til incremental skip). Self-safe → None."""
    try:
        with connect() as conn:
            _ensure_tables(conn)
            row = conn.execute(
                "SELECT content_hash FROM central_instrument_filehash WHERE file = ?",
                (str(file or ""),),
            ).fetchone()
        return str(row["content_hash"]) if row else None
    except Exception:
        return None


def set_file_hash(file: str, content_hash: str, n_findings: int) -> None:
    try:
        with connect() as conn:
            _ensure_tables(conn)
            conn.execute(
                "INSERT INTO central_instrument_filehash (file, content_hash, n_findings, last_scan) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(file) DO UPDATE SET "
                "content_hash=excluded.content_hash, n_findings=excluded.n_findings, "
                "last_scan=excluded.last_scan",
                (str(file or ""), str(content_hash or ""), int(n_findings),
                 datetime.now(UTC).isoformat()),
            )
    except Exception:
        pass


def replace_file_findings(file: str, findings: list[dict[str, Any]]) -> None:
    """Erstat ALLE åbne fund for én fil (idempotent pr. scan). Bevarer status (fx 'dismissed')
    for signaturer der stadig findes. Self-safe."""
    try:
        with connect() as conn:
            _ensure_tables(conn)
            now = datetime.now(UTC).isoformat()
            # eksisterende statusser for filen (bevar dismissed/accepted)
            prior = {
                str(r["signature"]): (str(r["status"]), str(r["first_seen"]))
                for r in conn.execute(
                    "SELECT signature, status, first_seen FROM central_instrument_findings WHERE file = ?",
                    (str(file or ""),),
                ).fetchall()
            }
            keep = {f["signature"] for f in findings}
            # fjern fund der ikke længere findes (koden er rettet)
            conn.execute("DELETE FROM central_instrument_findings WHERE file = ?", (str(file or ""),))
            for f in findings:
                sig = str(f.get("signature") or "")
                prev_status, prev_first = prior.get(sig, ("open", now))
                conn.execute(
                    "INSERT INTO central_instrument_findings "
                    "(signature, file, line, kind, severity, score, function, snippet, status, first_seen, last_seen) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (sig, str(file or ""), int(f.get("line") or 0), str(f.get("kind") or ""),
                     str(f.get("severity") or ""), int(f.get("score") or 0), str(f.get("function") or ""),
                     str(f.get("snippet") or "")[:300],
                     prev_status if prev_status in ("dismissed", "accepted") else "open",
                     prev_first, now),
                )
            _ = keep  # (dokumentation: kun keep-signaturer skrives)
    except Exception:
        pass


def list_findings(*, status: str = "open", min_score: int = 0, limit: int = 200) -> list[dict[str, Any]]:
    """Fund (højeste score først). Self-safe → []."""
    try:
        with connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                "SELECT * FROM central_instrument_findings "
                "WHERE status = ? AND score >= ? ORDER BY score DESC, severity, file LIMIT ?",
                (str(status or "open"), int(min_score), int(limit)),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def summary() -> dict[str, Any]:
    """Hurtig optælling pr. severity + total (til observe/central_query). Self-safe."""
    out = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "proposals": 0}
    try:
        with connect() as conn:
            _ensure_tables(conn)
            for r in conn.execute(
                "SELECT severity, COUNT(*) n FROM central_instrument_findings "
                "WHERE status = 'open' GROUP BY severity"
            ).fetchall():
                sev = str(r["severity"])
                if sev in out:
                    out[sev] = int(r["n"])
                out["total"] += int(r["n"])
            out["proposals"] = int(conn.execute(
                "SELECT COUNT(*) FROM central_instrument_findings WHERE status='open' AND score >= 3"
            ).fetchone()[0])
    except Exception:
        pass
    return out
