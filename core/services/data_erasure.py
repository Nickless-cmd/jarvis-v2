"""GDPR Art. 17 (ret til at blive glemt) — orkestrering.

Design: docs/superpowers/specs/2026-06-17-data-erasure-design.md

- soft (default): revoke connector-tokens + markér bruger slettet (reversibel i grace-periode).
- hard: derudover DELETE pr. user_id-tabel + workspace-mappe + DEK-nøgle (irreversibel).
- Owner (uid="") kan IKKE self-slettes ad denne vej.
- Audit (user_audit_log i runtime_state KV) overlever altid — det er ikke en user_id-tabel.

delete_user() (user_db) håndterer selv user-row, API-nøgle-revoke, keyring-DEK (hard) og audit.
Denne service lægger connector-revoke + tabel-sweep + workspace-wipe omkring den.
"""
from __future__ import annotations

import shutil

import core.runtime.db_core as dbc

# Tabel-navne der indeholder et af disse ord røres ALDRIG (sporbarhed/lovkrav).
_PROTECTED_SUBSTR = ("audit",)


def _user_id_tables(conn) -> list[str]:
    """Tabeller der HAR en user_id-kolonne (minus beskyttede). Eksplicit opdaget,
    ikke gættet — så vi hverken sletter for lidt eller rammer delt/audit-data."""
    out: list[str] = []
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for row in rows:
        name = row[0]
        if any(p in name.lower() for p in _PROTECTED_SUBSTR):
            continue
        cols = [c[1] for c in conn.execute(f"PRAGMA table_info('{name}')").fetchall()]
        if "user_id" in cols:
            out.append(name)
    return out


def _sweep_user_tables(user_id: str, *, connect=dbc.connect) -> dict[str, int]:
    counts: dict[str, int] = {}
    with connect() as conn:
        for tbl in _user_id_tables(conn):
            cur = conn.execute(f"DELETE FROM '{tbl}' WHERE user_id = ?", (user_id,))
            if cur.rowcount:
                counts[tbl] = cur.rowcount
        conn.commit()
    return counts


def _wipe_workspace(user_id: str) -> bool:
    """Slet brugerens workspace-mappe — med STRAM sti-sikkerhed (kun en undermappe
    direkte under .../workspaces/, aldrig roden eller noget udenfor)."""
    try:
        from core.runtime.workspace_paths import workspace_dir
        wd = workspace_dir(user_id).resolve()
        if wd.parent.name == "workspaces" and wd.name and wd.name != "workspaces":
            shutil.rmtree(wd, ignore_errors=True)
            return True
    except Exception:
        pass
    return False


def erase_user(user_id: str, *, mode: str = "soft", actor: str = "owner",
               connect=dbc.connect) -> dict:
    """Slet en brugers data. mode='soft' (reversibel) | 'hard' (permanent)."""
    uid = str(user_id or "").strip()
    if not uid:
        return {"status": "error", "error": "owner_cannot_self_erase"}
    if mode not in ("soft", "hard"):
        return {"status": "error", "error": "invalid_mode"}

    # 1. Revoke connector-tokens straks (uanset mode) — stopper data-adgang hos providers.
    revoked: list[str] = []
    try:
        from core.services.connectors import list_for_user, delete_for_user
        for c in list_for_user(uid):
            if c.get("kind") == "oauth" and c.get("connected"):
                if delete_for_user(uid, c["id"]):
                    revoked.append(c["id"])
    except Exception:
        pass

    swept: dict[str, int] = {}
    workspace_wiped = False
    if mode == "hard":
        swept = _sweep_user_tables(uid, connect=connect)
        workspace_wiped = _wipe_workspace(uid)

    # 2. user-row + API-nøgle-revoke + keyring-DEK (hard) + audit — alt i delete_user.
    from core.identity import user_db
    ok = user_db.delete_user(uid, mode=mode, actor=actor)

    return {
        "status": "ok" if ok else "not_found",
        "mode": mode,
        "revoked_connectors": revoked,
        "swept_tables": swept,
        "workspace_wiped": workspace_wiped,
    }
