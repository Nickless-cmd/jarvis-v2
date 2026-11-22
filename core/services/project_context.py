"""Durable chat projects that bind sessions to files and text material."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.runtime import db_core


class ProjectNotFound(LookupError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_projects (
            project_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            owner_user_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_project_sessions (
            session_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            bound_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_project_sessions_project "
        "ON chat_project_sessions(project_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_project_materials (
            material_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            kind TEXT NOT NULL CHECK (kind IN ('file', 'text')),
            title TEXT NOT NULL,
            path TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_project_materials_project "
        "ON chat_project_materials(project_id, created_at, material_id)"
    )


def _require_project(conn, project_id: str) -> None:
    if conn.execute(
        "SELECT 1 FROM chat_projects WHERE project_id = ?", (project_id,)
    ).fetchone() is None:
        raise ProjectNotFound(project_id)


def create_project(
    *, session_id: str, name: str, owner_user_id: str = ""
) -> dict[str, Any]:
    sid = str(session_id or "").strip()
    project_name = str(name or "").strip()
    if not sid:
        raise ValueError("session_id is required")
    if not project_name:
        raise ValueError("name is required")
    project_id = f"project-{uuid4().hex}"
    now = _now()
    with db_core.connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            "INSERT INTO chat_projects "
            "(project_id, name, owner_user_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_id, project_name, str(owner_user_id or "").strip(), now, now),
        )
        conn.execute(
            "INSERT INTO chat_project_sessions (session_id, project_id, bound_at) "
            "VALUES (?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET "
            "project_id = excluded.project_id, bound_at = excluded.bound_at",
            (sid, project_id, now),
        )
        row = conn.execute(
            "SELECT * FROM chat_projects WHERE project_id = ?", (project_id,)
        ).fetchone()
    return dict(row)


def bind_session(project_id: str, session_id: str) -> None:
    pid = str(project_id or "").strip()
    sid = str(session_id or "").strip()
    if not pid or not sid:
        raise ValueError("project_id and session_id are required")
    now = _now()
    with db_core.connect() as conn:
        _ensure_tables(conn)
        _require_project(conn, pid)
        conn.execute(
            "INSERT INTO chat_project_sessions (session_id, project_id, bound_at) "
            "VALUES (?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET "
            "project_id = excluded.project_id, bound_at = excluded.bound_at",
            (sid, pid, now),
        )
        conn.execute(
            "UPDATE chat_projects SET updated_at = ? WHERE project_id = ?", (now, pid)
        )


def _add_material(
    project_id: str, *, kind: str, title: str, path: str = "", content: str = ""
) -> dict[str, Any]:
    pid = str(project_id or "").strip()
    if not pid:
        raise ValueError("project_id is required")
    material_id = f"material-{uuid4().hex}"
    now = _now()
    with db_core.connect() as conn:
        _ensure_tables(conn)
        _require_project(conn, pid)
        conn.execute(
            "INSERT INTO chat_project_materials "
            "(material_id, project_id, kind, title, path, content, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (material_id, pid, kind, title, path, content, now),
        )
        conn.execute(
            "UPDATE chat_projects SET updated_at = ? WHERE project_id = ?", (now, pid)
        )
        row = conn.execute(
            "SELECT * FROM chat_project_materials WHERE material_id = ?", (material_id,)
        ).fetchone()
    return dict(row)


def add_file_material(
    project_id: str, *, path: str, title: str = ""
) -> dict[str, Any]:
    candidate = Path(str(path or "")).expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(str(candidate))
    return _add_material(
        project_id,
        kind="file",
        title=str(title or candidate.name).strip() or candidate.name,
        path=str(candidate),
    )


def add_text_material(
    project_id: str, *, content: str, title: str = "Note"
) -> dict[str, Any]:
    return _add_material(
        project_id,
        kind="text",
        title=str(title or "Note").strip() or "Note",
        content=str(content or ""),
    )


def get_project(project_id: str) -> dict[str, Any] | None:
    pid = str(project_id or "").strip()
    if not pid:
        return None
    with db_core.connect() as conn:
        _ensure_tables(conn)
        project = conn.execute(
            "SELECT * FROM chat_projects WHERE project_id = ?", (pid,)
        ).fetchone()
        if project is None:
            return None
        materials = conn.execute(
            "SELECT * FROM chat_project_materials WHERE project_id = ? "
            "ORDER BY created_at, material_id",
            (pid,),
        ).fetchall()
    return {**dict(project), "materials": [dict(row) for row in materials]}


def get_project_for_session(session_id: str) -> dict[str, Any] | None:
    sid = str(session_id or "").strip()
    if not sid:
        return None
    with db_core.connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT project_id FROM chat_project_sessions WHERE session_id = ?", (sid,)
        ).fetchone()
    return get_project(str(row["project_id"])) if row is not None else None


def unbind_session(session_id: str) -> None:
    """Fjern samtalens projekt-binding. Materialet på projektet røres ikke."""
    sid = str(session_id or "").strip()
    if not sid:
        raise ValueError("session_id is required")
    with db_core.connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            "DELETE FROM chat_project_sessions WHERE session_id = ?", (sid,)
        )


def list_projects(*, owner_user_id: str = "", limit: int = 200) -> list[dict[str, Any]]:
    """Projekter nyeste først, hver med sit materiale.

    Uden ``owner_user_id`` returneres alle — kalderen (ruten) filtrerer selv på ejer,
    så en tom ejer ikke ved et uheld skjuler projekter oprettet før ejer-feltet fandtes.
    """
    owner = str(owner_user_id or "").strip()
    sql = "SELECT * FROM chat_projects"
    args: list[Any] = []
    if owner:
        sql += " WHERE owner_user_id = ?"
        args.append(owner)
    sql += " ORDER BY updated_at DESC, project_id LIMIT ?"
    args.append(max(1, int(limit)))
    with db_core.connect() as conn:
        _ensure_tables(conn)
        projects = [dict(row) for row in conn.execute(sql, tuple(args)).fetchall()]
        if not projects:
            return []
        ids = [str(p["project_id"]) for p in projects]
        marks = ",".join("?" for _ in ids)
        rows = conn.execute(
            "SELECT * FROM chat_project_materials WHERE project_id IN "
            f"({marks}) ORDER BY created_at, material_id",
            tuple(ids),
        ).fetchall()
    by_project: dict[str, list[dict[str, Any]]] = {pid: [] for pid in ids}
    for row in rows:
        by_project.setdefault(str(row["project_id"]), []).append(dict(row))
    return [{**p, "materials": by_project.get(str(p["project_id"]), [])} for p in projects]
