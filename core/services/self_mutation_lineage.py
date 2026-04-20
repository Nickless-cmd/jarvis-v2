"""Runtime self-awareness of self-change and code mutation lineage.

Tracks when Jarvis writes or edits files that are part of his own runtime,
workspace, or application code — distinguishing his own changes from user changes.

This is a read-write-observation truth: it records what happened, not what
Jarvis feels about it. The prompt contract uses it to tell Jarvis what he
recently changed in himself.
"""
from __future__ import annotations

import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from core.runtime.config import PROJECT_ROOT
from core.runtime.db import connect

_init_lock = threading.Lock()
_table_initialized = False

_PROJECT_ROOT = Path(PROJECT_ROOT).resolve()

_PATH_CATEGORIES: list[tuple[str, str]] = [
    ("core/", "core-runtime"),
    ("workspace/", "workspace"),
    ("apps/", "apps"),
    ("scripts/", "scripts"),
]


def _ensure_table() -> None:
    global _table_initialized
    if _table_initialized:
        return
    with _init_lock:
        if _table_initialized:
            return
        with connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS self_code_mutations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mutation_id TEXT NOT NULL UNIQUE,
                    target_path TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    path_category TEXT NOT NULL,
                    session_id TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_self_code_mutations_created
                ON self_code_mutations (created_at DESC)
            """)
        _table_initialized = True


def _categorize_path(path: str) -> str | None:
    """Return category if path is a Jarvis self-file, else None."""
    try:
        resolved = Path(path).resolve()
        rel = resolved.relative_to(_PROJECT_ROOT)
        rel_str = str(rel)
        for prefix, category in _PATH_CATEGORIES:
            if rel_str.startswith(prefix):
                return category
        return "other-self"
    except ValueError:
        return None


def _relative_path(path: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(_PROJECT_ROOT))
    except ValueError:
        return path


def record_self_mutation(
    *,
    target_path: str,
    change_type: str,
    session_id: str | None = None,
) -> None:
    """Record a completed file mutation to a Jarvis self-file.

    Silently ignores non-self-files and failures.
    """
    try:
        category = _categorize_path(target_path)
        if category is None:
            return
        _ensure_table()
        mutation_id = f"mut-{uuid4().hex[:16]}"
        rel_path = _relative_path(target_path)
        now = datetime.now(UTC).isoformat()
        with connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO self_code_mutations
                    (mutation_id, target_path, relative_path, change_type, path_category, session_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (mutation_id, target_path, rel_path, change_type, category, session_id or "", now),
            )
    except Exception:
        pass


def build_self_mutation_lineage_surface(*, limit: int = 20) -> dict:
    """Returns recent self-mutations as a runtime-truth surface."""
    try:
        _ensure_table()
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT mutation_id, relative_path, change_type, path_category, created_at
                FROM self_code_mutations
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        mutations = [
            {
                "mutation_id": row["mutation_id"],
                "path": row["relative_path"],
                "change_type": row["change_type"],
                "category": row["path_category"],
                "when": str(row["created_at"] or "")[:19],
            }
            for row in rows
        ]
        last_at = mutations[0]["when"] if mutations else None
        return {
            "recent_mutations": mutations,
            "mutation_count": len(mutations),
            "last_mutation_at": last_at,
            "authority": "derived-runtime-truth",
            "visibility": "internal-only",
            "kind": "self-mutation-lineage",
        }
    except Exception as exc:
        return {
            "recent_mutations": [],
            "mutation_count": 0,
            "last_mutation_at": None,
            "authority": "derived-runtime-truth",
            "visibility": "internal-only",
            "kind": "self-mutation-lineage",
            "error": str(exc),
        }


def build_self_mutation_prompt_lines(*, limit: int = 5) -> list[str]:
    """Returns compact prompt lines for recent self-mutations."""
    surface = build_self_mutation_lineage_surface(limit=limit)
    mutations = surface.get("recent_mutations") or []
    if not mutations:
        return []
    lines = []
    for m in mutations:
        ts = m["when"][:16] if m["when"] else "?"
        lines.append(f"[{ts}] {m['change_type']} {m['path']} ({m['category']})")
    return lines
