"""API-forbindelses-nerve — persistent, GDPR-bundet metadata om hvem/hvad der rammer API'et.

Bjørn (6. jul): "en nerve hvor du kan se og mærke nye forbindelser via din api ... hvilke ip,
session/user id, aktive, last aktiv. og fejl.. ikke privat samtaler." Device-presence for
HTTP-API-trafikken.

GDPR (data-ansvarlig-valg 6. jul): **metadata-only** (IP/endpoint/metode/status/latens/user/
session/ts/fejl — ALDRIG request/response-body eller samtaleindhold). Formålsbundet: sikkerhed +
fejlfinding. **Fuld IP gemmes → auto-anonymiseres til /24 efter 48t** (retention), rå detalje-log
slettes efter 14 dage. Presence-rækker prunes efter 48t. Alt self-safe.

To tabeller:
  * ``api_connection_presence`` — "hvem er forbundet": aggregat pr. (ip, user_id), first/last_seen,
    tællere, sidste endpoint/status. Live-agtig (opdateres batchet).
  * ``api_request_log`` — rullende detalje til fejl-sporing (retention-styret).
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect

RETENTION_HOURS = 48       # fuld IP → /24 efter dette
LOG_DELETE_DAYS = 14       # rå log-rækker slettes efter dette


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS api_connection_presence (
            ip TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT '',
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            request_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            last_method TEXT NOT NULL DEFAULT '',
            last_path TEXT NOT NULL DEFAULT '',
            last_status INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (ip, user_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS api_request_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            ip TEXT NOT NULL DEFAULT '',
            method TEXT NOT NULL DEFAULT '',
            path TEXT NOT NULL DEFAULT '',
            status INTEGER NOT NULL DEFAULT 0,
            latency_ms INTEGER NOT NULL DEFAULT 0,
            user_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_api_log_ts ON api_request_log (ts)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_api_presence_last ON api_connection_presence (last_seen)")


def flush_records(presence_deltas: list[dict[str, Any]], log_rows: list[dict[str, Any]]) -> int:
    """Batch-skriv: UPSERT presence-aggregater + INSERT detalje-log. Én DB-tur. Self-safe."""
    if not presence_deltas and not log_rows:
        return 0
    try:
        with connect() as conn:
            _ensure_tables(conn)
            for d in presence_deltas:
                try:
                    conn.execute(
                        """
                        INSERT INTO api_connection_presence
                            (ip, user_id, first_seen, last_seen, request_count, error_count,
                             last_method, last_path, last_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(ip, user_id) DO UPDATE SET
                            last_seen = excluded.last_seen,
                            request_count = request_count + excluded.request_count,
                            error_count = error_count + excluded.error_count,
                            last_method = excluded.last_method,
                            last_path = excluded.last_path,
                            last_status = excluded.last_status
                        """,
                        (str(d.get("ip") or ""), str(d.get("user_id") or ""),
                         str(d.get("first_seen") or ""), str(d.get("last_seen") or ""),
                         int(d.get("request_count") or 0), int(d.get("error_count") or 0),
                         str(d.get("last_method") or ""), str(d.get("last_path") or "")[:200],
                         int(d.get("last_status") or 0)),
                    )
                except Exception:
                    continue
            for r in log_rows:
                try:
                    conn.execute(
                        """
                        INSERT INTO api_request_log
                            (ts, ip, method, path, status, latency_ms, user_id, session_id, error)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (str(r.get("ts") or ""), str(r.get("ip") or ""),
                         str(r.get("method") or ""), str(r.get("path") or "")[:200],
                         int(r.get("status") or 0), int(r.get("latency_ms") or 0),
                         str(r.get("user_id") or ""), str(r.get("session_id") or ""),
                         str(r.get("error") or "")[:200]),
                    )
                except Exception:
                    continue
            conn.commit()
            return len(presence_deltas) + len(log_rows)
    except Exception:
        return 0


def anonymize_and_prune(*, retention_hours: int = RETENTION_HOURS,
                        delete_days: int = LOG_DELETE_DAYS) -> dict[str, int]:
    """GDPR-retention: trunkér fuld IP → /24 i log-rækker ældre end retention_hours, slet
    log-rækker ældre end delete_days, prune presence-rækker uden aktivitet i retention_hours.
    Self-safe → nul-tal ved fejl."""
    out = {"anonymized": 0, "deleted": 0, "pruned": 0}
    try:
        now = datetime.now(UTC)
        cutoff_anon = now.timestamp() - retention_hours * 3600
        cutoff_del = now.timestamp() - delete_days * 86400
        cutoff_anon_iso = datetime.fromtimestamp(cutoff_anon, UTC).isoformat()
        cutoff_del_iso = datetime.fromtimestamp(cutoff_del, UTC).isoformat()
        with connect() as conn:
            _ensure_tables(conn)
            # anonymisér: rå IP → /24 (ipv4) på rækker ældre end retention men ikke allerede anon
            rows = conn.execute(
                "SELECT id, ip FROM api_request_log WHERE ts < ? AND ip NOT LIKE '%/24' AND ip != ''",
                (cutoff_anon_iso,),
            ).fetchall()
            for r in rows:
                anon = anonymize_ip(str(r["ip"]))
                conn.execute("UPDATE api_request_log SET ip = ? WHERE id = ?", (anon, r["id"]))
            out["anonymized"] = len(rows)
            cur = conn.execute("DELETE FROM api_request_log WHERE ts < ?", (cutoff_del_iso,))
            out["deleted"] = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            cur = conn.execute("DELETE FROM api_connection_presence WHERE last_seen < ?", (cutoff_anon_iso,))
            out["pruned"] = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            conn.commit()
    except Exception:
        pass
    return out


def anonymize_ip(ip: str) -> str:
    """Trunkér til /24 (ipv4) eller /64 (ipv6). GDPR-anonymisering — beholder subnet, taber vært."""
    ip = (ip or "").strip()
    if not ip or "/" in ip:
        return ip
    if ":" in ip:  # ipv6
        parts = ip.split(":")
        return ":".join(parts[:4]) + "::/64"
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return ip


def read_presence(*, active_within_s: int = 300, limit: int = 100) -> list[dict[str, Any]]:
    """Presence-view: forbindelser set for nylig. active=set inden for active_within_s. Self-safe."""
    try:
        now = datetime.now(UTC)
        active_cutoff = datetime.fromtimestamp(now.timestamp() - active_within_s, UTC).isoformat()
        with connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """SELECT ip, user_id, first_seen, last_seen, request_count, error_count,
                          last_method, last_path, last_status
                   FROM api_connection_presence ORDER BY last_seen DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["active"] = bool(str(r["last_seen"]) >= active_cutoff)
                out.append(d)
            return out
    except Exception:
        return []


def read_recent_errors(*, limit: int = 30) -> list[dict[str, Any]]:
    """Seneste fejl-requests (status ≥ 400) til fejl-sporing. Self-safe."""
    try:
        with connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """SELECT ts, ip, method, path, status, user_id, error
                   FROM api_request_log WHERE status >= 400 ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []
