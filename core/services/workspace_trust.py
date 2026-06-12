"""Trusted-folder gate for code/cowork workspaces.

Claude Desktop-mønster: et workspace er læsbart med det samme, men skrive- og
exec-værktøjer (write_file/edit_file/bash + operator-modparter) blokeres indtil
brugeren eksplicit har markeret mappen som *betroet*. Trust er vedvarende pr.
(user_id, kind, root) og lever i sin egen tabel — ingen db.py-ændring.

Håndhævelse sker centralt i ``simple_tools.execute_tool`` via ``guard_code_write``,
som læser en request-scopet ContextVar sat i ``visible_runs._stream_visible_run``.
"""
from __future__ import annotations

import contextvars
from datetime import UTC, datetime

from core.runtime.db import connect

# Skrive-/exec-værktøjer der kræver betroet workspace i code-scope.
_CODE_WRITE_TOOLS = frozenset({
    "write_file", "edit_file", "bash",
    "operator_write_file", "operator_edit_file", "operator_bash",
})

# Request-scopet trust-kontekst: {"kind","root","trusted"} sat ved run-entry.
_trust_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "jarvis_ws_trust", default={},
)


def _ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_trust (
            user_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            root TEXT NOT NULL,
            trusted_at TEXT NOT NULL,
            PRIMARY KEY (user_id, kind, root)
        )
        """
    )


def is_trusted(user_id: str | None, kind: str | None, root: str | None) -> bool:
    """True hvis (user_id, kind, root) er markeret betroet."""
    if not kind or not root:
        return False
    with connect() as conn:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT 1 FROM workspace_trust WHERE user_id = ? AND kind = ? AND root = ?",
            (user_id or "", kind, root),
        ).fetchone()
    return row is not None


def set_trusted(
    user_id: str | None, kind: str, root: str, trusted: bool,
) -> bool:
    """Markér/afmarkér et workspace som betroet. Returnerer den nye trust-tilstand."""
    with connect() as conn:
        _ensure_table(conn)
        if trusted:
            conn.execute(
                "INSERT OR REPLACE INTO workspace_trust(user_id, kind, root, trusted_at) "
                "VALUES (?, ?, ?, ?)",
                (user_id or "", kind, root, datetime.now(UTC).isoformat()),
            )
        else:
            conn.execute(
                "DELETE FROM workspace_trust WHERE user_id = ? AND kind = ? AND root = ?",
                (user_id or "", kind, root),
            )
        conn.commit()
    return trusted


# --- Request-scopet kontekst (sættes i visible_runs, læses i execute_tool) ---

def set_trust_context(*, kind: str | None, root: str | None, trusted: bool) -> None:
    _trust_ctx.set({"kind": kind or "", "root": root or "", "trusted": bool(trusted)})


def clear_trust_context() -> None:
    _trust_ctx.set({})


def current_trust_context() -> dict:
    return _trust_ctx.get()


def guard_code_write(tool_name: str) -> str | None:
    """Returnér en fejl-besked hvis ``tool_name`` er en skrive-/exec-handling i et
    ikke-betroet code-workspace; ellers None (tilladt)."""
    if tool_name not in _CODE_WRITE_TOOLS:
        return None
    ctx = _trust_ctx.get()
    # Kun håndhæv når vi faktisk er i et code-workspace med en binding.
    if not ctx or not ctx.get("kind") or not ctx.get("root"):
        return None
    if ctx.get("trusted"):
        return None
    return (
        f"Workspace '{ctx.get('root')}' er ikke betroet. Jarvis kan læse her, "
        f"men skrive- og exec-handlinger ({tool_name}) kræver at brugeren først "
        f"markerer mappen som betroet i Code-fladen."
    )
