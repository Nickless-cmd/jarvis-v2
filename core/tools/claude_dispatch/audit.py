from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from core.runtime.db import connect
from core.tools.claude_dispatch.spec import TaskSpec


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def start_audit_row(task_id: str, spec: TaskSpec) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO claude_dispatch_audit
                (task_id, started_at, spec_json, status, tokens_used)
            VALUES (?, ?, ?, 'running', 0)
            """,
            (task_id, _now_iso(), json.dumps(asdict(spec))),
        )
        conn.commit()


def finalize_audit_row(
    task_id: str, *, status: str, tokens_used: int,
    exit_code: int | None, diff_summary: str | None, error: str | None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE claude_dispatch_audit
            SET ended_at=?, status=?, tokens_used=?, exit_code=?,
                diff_summary=?, error=?
            WHERE task_id=? AND status='running'
            """,
            (_now_iso(), status, int(tokens_used), exit_code,
             diff_summary, error, task_id),
        )
        conn.commit()


def read_audit_row(task_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM claude_dispatch_audit WHERE task_id=?",
            (task_id,),
        ).fetchone()
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}
