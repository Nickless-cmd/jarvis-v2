"""DB helpers for users-tabellen (spec 2026-06-15).

Split ud fra db.py per CLAUDE.md boy scout rule (db.py er 33k linjer).
Re-eksporteres fra core.runtime.db for bagudkompatibilitet.

Rent SQL-lag: ingen kryptering her (det ligger i core/identity/user_db.py).
Tabellen lagrer allerede-krypterede/hashede værdier.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db import connect


def _ensure_users_table(conn: sqlite3.Connection) -> None:
    """Idempotent: brugerstyring. Følsomme felter lagres krypteret
    (email_enc/discord_id_enc/totp_seed_enc/api_key_enc); email_hash er et
    deterministisk opslags-hash så login kan finde brugeren uden at dekryptere."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            email_hash TEXT NOT NULL UNIQUE,
            email_enc BLOB NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            workspace TEXT NOT NULL,
            password_hash TEXT NOT NULL DEFAULT '',
            discord_id_enc BLOB NOT NULL DEFAULT x'',
            totp_seed_enc BLOB NOT NULL DEFAULT x'',
            email_verified INTEGER NOT NULL DEFAULT 0,
            tier TEXT NOT NULL DEFAULT '',
            api_key_enc BLOB NOT NULL DEFAULT x'',
            api_key_jti TEXT NOT NULL DEFAULT '',
            muted INTEGER NOT NULL DEFAULT 0,
            consent_data_processing INTEGER NOT NULL DEFAULT 0,
            consent_marketing INTEGER NOT NULL DEFAULT 0,
            consent_blind_access INTEGER NOT NULL DEFAULT 0,
            language TEXT NOT NULL DEFAULT 'da',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        )
        """
    )
    # Idempotent kolonne-tilføjelse for ældre DB'er (language tilføjet 2026-06-15).
    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "language" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'da'")
    conn.commit()


def insert_user_row(
    *, user_id: str, email_hash: str, email_enc: bytes, name: str, role: str,
    workspace: str, password_hash: str, discord_id_enc: bytes, totp_seed_enc: bytes,
    created_at: str, updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_users_table(conn)
        conn.execute(
            """
            INSERT INTO users
                (user_id, email_hash, email_enc, name, role, workspace,
                 password_hash, discord_id_enc, totp_seed_enc, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, email_hash, email_enc, name, role, workspace,
             password_hash, discord_id_enc, totp_seed_enc, created_at, updated_at),
        )
        conn.commit()
    return get_user_row(user_id) or {}


def get_user_row(user_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_users_table(conn)
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_row_by_email_hash(email_hash: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_users_table(conn)
        row = conn.execute("SELECT * FROM users WHERE email_hash = ?", (email_hash,)).fetchone()
    return dict(row) if row else None


def get_user_row_by_workspace(workspace: str) -> dict[str, object] | None:
    """Opslag pr. workspace-mappenavn (omvendt lookup). Bruges af cutover-resolveren
    + workspace_crypto til at genkende en SQLite-members workspace. Ignorerer
    soft-slettede."""
    ws = str(workspace or "").strip()
    if not ws:
        return None
    with connect() as conn:
        _ensure_users_table(conn)
        row = conn.execute(
            "SELECT * FROM users WHERE workspace = ? "
            "AND (deleted_at IS NULL OR deleted_at = '') LIMIT 1",
            (ws,),
        ).fetchone()
    return dict(row) if row else None


_USER_UPDATABLE = {
    "email_hash", "email_enc", "name", "role", "workspace", "password_hash",
    "discord_id_enc", "totp_seed_enc", "email_verified", "tier",
    "api_key_enc", "api_key_jti", "muted", "language",
    "consent_data_processing", "consent_marketing", "consent_blind_access",
    "updated_at", "deleted_at",
}


def update_user_row(user_id: str, fields: dict[str, object]) -> bool:
    cols = [(k, v) for k, v in fields.items() if k in _USER_UPDATABLE]
    if not cols:
        return False
    set_clause = ", ".join(f"{k} = ?" for k, _ in cols)
    params = [v for _, v in cols] + [user_id]
    with connect() as conn:
        _ensure_users_table(conn)
        cur = conn.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", params)
        conn.commit()
    return cur.rowcount > 0


def soft_delete_user_row(user_id: str, *, deleted_at: str) -> bool:
    return update_user_row(user_id, {"deleted_at": deleted_at})


def hard_delete_user_row(user_id: str) -> bool:
    with connect() as conn:
        _ensure_users_table(conn)
        cur = conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
    return cur.rowcount > 0


def list_user_rows(*, include_deleted: bool = False) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_users_table(conn)
        where = "" if include_deleted else "WHERE deleted_at IS NULL"
        rows = conn.execute(f"SELECT * FROM users {where} ORDER BY id ASC").fetchall()
    return [dict(r) for r in rows]
