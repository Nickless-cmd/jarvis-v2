"""Per-bruger web-push-abonnementer (VAPID). Egen tabel — rører ikke db.py.

Fjerde udgang på push-stakken (side-67aea8c5b6). FCM-tokens ligger i
``device_tokens``; et web-abonnement er ikke et token men et endpoint plus to
nøgler (``p256dh``/``auth``), så det får sin egen tabel frem for at pakke JSON
ind i et token-felt.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect

_ENSURED = False


def _ensure_table() -> None:
    global _ENSURED
    if _ENSURED:
        return
    with connect() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS web_push_subscriptions (
                   endpoint    TEXT PRIMARY KEY,
                   user_id     TEXT NOT NULL,
                   p256dh      TEXT NOT NULL,
                   auth        TEXT NOT NULL,
                   updated_at  TEXT NOT NULL
               )"""
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_push_user ON web_push_subscriptions(user_id)"
        )
    _ENSURED = True


def save(user_id: str, endpoint: str, p256dh: str, auth: str) -> None:
    uid, ep = (user_id or "").strip(), (endpoint or "").strip()
    if not uid or not ep:
        return
    _ensure_table()
    with connect() as c:
        c.execute(
            """INSERT INTO web_push_subscriptions(endpoint, user_id, p256dh, auth, updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(endpoint) DO UPDATE SET
                   user_id=excluded.user_id,
                   p256dh=excluded.p256dh,
                   auth=excluded.auth,
                   updated_at=excluded.updated_at""",
            (ep, uid, (p256dh or "").strip(), (auth or "").strip(),
             datetime.now(UTC).isoformat()),
        )


def list_for_user(user_id: str) -> list[dict[str, Any]]:
    """Alle abonnementer for brugeren som ``[{endpoint, p256dh, auth}]``."""
    uid = (user_id or "").strip()
    if not uid:
        return []
    _ensure_table()
    with connect() as c:
        rows = c.execute(
            "SELECT endpoint, p256dh, auth FROM web_push_subscriptions "
            "WHERE user_id=? ORDER BY updated_at",
            (uid,),
        ).fetchall()
    return [{"endpoint": r[0], "p256dh": r[1], "auth": r[2]} for r in rows]


def delete(endpoint: str) -> None:
    ep = (endpoint or "").strip()
    if not ep:
        return
    _ensure_table()
    with connect() as c:
        c.execute("DELETE FROM web_push_subscriptions WHERE endpoint=?", (ep,))
