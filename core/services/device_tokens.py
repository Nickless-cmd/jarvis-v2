"""Per-bruger FCM device-tokens. Egen tabel — rører ikke db.py's 33k linjer."""
from __future__ import annotations

from datetime import UTC, datetime

from core.runtime.db import connect

_ENSURED = False


def _ensure_table() -> None:
    global _ENSURED
    if _ENSURED:
        return
    with connect() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS device_tokens (
                   token       TEXT PRIMARY KEY,
                   user_id     TEXT NOT NULL,
                   platform    TEXT NOT NULL DEFAULT 'android',
                   updated_at  TEXT NOT NULL
               )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_device_tokens_user ON device_tokens(user_id)")
    _ENSURED = True


def register(user_id: str, token: str, platform: str = "android") -> None:
    uid, tok = (user_id or "").strip(), (token or "").strip()
    if not uid or not tok:
        return
    _ensure_table()
    with connect() as c:
        c.execute(
            """INSERT INTO device_tokens(token, user_id, platform, updated_at)
               VALUES(?,?,?,?)
               ON CONFLICT(token) DO UPDATE SET
                   user_id=excluded.user_id,
                   platform=excluded.platform,
                   updated_at=excluded.updated_at""",
            (tok, uid, (platform or "android").strip(), datetime.now(UTC).isoformat()),
        )


def list_for_user(user_id: str) -> list[str]:
    uid = (user_id or "").strip()
    if not uid:
        return []
    _ensure_table()
    with connect() as c:
        rows = c.execute(
            "SELECT token FROM device_tokens WHERE user_id=? ORDER BY updated_at", (uid,)
        ).fetchall()
    return [r[0] for r in rows]


def delete(token: str) -> None:
    tok = (token or "").strip()
    if not tok:
        return
    _ensure_table()
    with connect() as c:
        c.execute("DELETE FROM device_tokens WHERE token=?", (tok,))
