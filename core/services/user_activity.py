"""Bruger-aktivitets-nerve — ét sted der svarer "hvornår var X sidst aktiv, og hvordan".

Bjørn (6. jul): "Kan centralen se hvornår Mikkel sidst har været aktiv?" Dataen lå spredt
(chat_messages / api_connection_presence / visible_runs / device_tokens). Denne nerve fletter
dem pr. bruger → sidst aktiv · via hvad (chat/api/run/device) · aktiv nu · besked-antal ·
token-estimat.

GDPR/§24.4: metadata-only (tidsstempler + tællere + kilde) — ALDRIG besked-INDHOLD. Token er
et ESTIMAT fra samtale-volumen (costs-tabellen er ikke per-bruger), tydeligt markeret. Self-safe.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _q1(conn, sql: str, params: tuple) -> Any:
    try:
        row = conn.execute(sql, params).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def build_user_activity_surface(*, active_within_s: int = 300) -> dict[str, Any]:
    """Pr. registreret bruger: sidst aktiv (flettet fra alle kilder), via hvad, aktiv nu,
    besked-antal, est. tokens. Sorteret efter sidst-aktiv. Self-safe → tom liste ved fejl."""
    out: dict[str, Any] = {"users": [], "active_count": 0, "total_users": 0}
    try:
        from core.identity.users import load_users
        from core.runtime.db_core import connect
    except Exception:
        return out

    try:
        users = load_users()
    except Exception:
        users = []

    now = datetime.now(UTC)
    active_cutoff = datetime.fromtimestamp(now.timestamp() - active_within_s, UTC).isoformat()

    rows: list[dict[str, Any]] = []
    try:
        with connect() as conn:
            for u in users:
                uid = getattr(u, "discord_id", "") or ""
                if not uid:
                    continue
                last_chat = _q1(conn, "SELECT MAX(created_at) FROM chat_messages WHERE user_id=?", (uid,))
                msgs = _q1(conn, "SELECT COUNT(*) FROM chat_messages WHERE user_id=?", (uid,)) or 0
                chars = _q1(conn, "SELECT SUM(LENGTH(content)) FROM chat_messages WHERE user_id=?", (uid,)) or 0
                last_run = _q1(conn, "SELECT MAX(started_at) FROM visible_runs WHERE user_id=?", (uid,))
                last_api = _q1(conn, "SELECT MAX(last_seen) FROM api_connection_presence WHERE user_id=?", (uid,))
                last_dev = _q1(conn, "SELECT MAX(updated_at) FROM device_tokens WHERE user_id=?", (uid,))

                sources = {"chat": last_chat, "api": last_api, "run": last_run, "device": last_dev}
                valid = {k: v for k, v in sources.items() if v}
                last_active = max(valid.values()) if valid else ""
                via = max(valid, key=lambda k: valid[k]) if valid else ""
                rows.append({
                    "name": getattr(u, "name", "") or "?",
                    "role": getattr(u, "role", "") or "member",
                    "workspace": getattr(u, "workspace", "") or "",
                    "user_id": uid,
                    "last_active": last_active,
                    "via": via,
                    "active": bool(last_active and last_active >= active_cutoff),
                    "messages": int(msgs),
                    "est_tokens": int(chars / 4),          # grov char/4-proxy (costs ikke per-bruger)
                    "last_chat": last_chat or "",
                    "last_api": last_api or "",
                    "last_run": last_run or "",
                    "last_device": last_dev or "",
                })
    except Exception:
        return out

    rows.sort(key=lambda r: r.get("last_active") or "", reverse=True)
    out["users"] = rows
    out["active_count"] = sum(1 for r in rows if r.get("active"))
    out["total_users"] = len(rows)
    out["token_note"] = "est_tokens = samtale-volumen/4 (grovt); costs-tabellen er ikke per-bruger"
    return out
