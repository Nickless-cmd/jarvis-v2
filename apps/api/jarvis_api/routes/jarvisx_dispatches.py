"""JarvisX Claude-Code dispatch dashboard route group.

Read-only observability into Jarvis' parallel Claude-Code dispatches:
list, per-hour budget, single-dispatch detail, and live worktree diff.
Extracted from routes/jarvisx.py.

Behavior-preserving: pure code movement, no logic changes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from core.runtime.jarvisx_auth import require_owner
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(prefix="/api", tags=["jarvisx"])


# ── Claude Code dispatch dashboard ────────────────────────────────
# Backs the JarvisX "Dispatches" view: see Jarvis' parallel
# Claude-Code instances live — what they're working on, how far
# they've gotten (live worktree diff), tokens burned, time elapsed.
# Read-only: dispatching itself happens through the dispatch_to_claude_code
# tool. This is observability, not control.


@router.get("/dispatches", dependencies=[Depends(require_owner)])
def list_dispatches(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    """Recent dispatches, running first then by started_at desc.

    Each row carries a parsed copy of the spec for at-a-glance prompt
    preview + elapsed seconds for live ticker rendering.
    """
    import json as _json
    from core.runtime.db import connect

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT task_id, started_at, ended_at, status, tokens_used,
                   exit_code, diff_summary, error, spec_json
            FROM claude_dispatch_audit
            ORDER BY
                CASE WHEN status = 'running' THEN 0 ELSE 1 END,
                started_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

    out: list[dict[str, Any]] = []
    now = datetime.utcnow()
    for r in rows:
        spec: dict[str, Any] = {}
        try:
            spec = _json.loads(r["spec_json"]) if r["spec_json"] else {}
        except Exception:
            spec = {}
        # Compute elapsed for running tasks (live ticker)
        elapsed: float | None = None
        try:
            t0 = datetime.fromisoformat(str(r["started_at"]).replace("Z", "+00:00"))
            t1_raw = r["ended_at"]
            t1 = (
                datetime.fromisoformat(str(t1_raw).replace("Z", "+00:00"))
                if t1_raw
                else now.replace(tzinfo=t0.tzinfo)
            )
            elapsed = max(0.0, (t1 - t0).total_seconds())
        except Exception:
            elapsed = None
        out.append({
            "task_id": r["task_id"],
            "status": r["status"],
            "started_at": r["started_at"],
            "ended_at": r["ended_at"],
            "elapsed_seconds": elapsed,
            "tokens_used": int(r["tokens_used"] or 0),
            "exit_code": r["exit_code"],
            "diff_summary": r["diff_summary"],
            "error": r["error"],
            "prompt": (spec.get("prompt") or "")[:500],  # preview only
            "branch": f"claude/{r['task_id']}",
            "model": spec.get("model"),
            "max_turns": spec.get("max_turns"),
            "allowed_paths": spec.get("allowed_paths") or [],
        })
    return {"count": len(out), "dispatches": out}


@router.get("/dispatches/budget", dependencies=[Depends(require_owner)])
def dispatch_budget() -> dict[str, Any]:
    """Current hour's dispatch budget — count + tokens vs caps."""
    from core.runtime.db import connect
    from core.tools.claude_dispatch.budget import (
        MAX_DISPATCHES_PER_HOUR,
        MAX_TOKENS_PER_HOUR,
    )

    bucket = datetime.utcnow().strftime("%Y-%m-%dT%H")
    with connect() as conn:
        row = conn.execute(
            "SELECT dispatch_count, tokens_used FROM claude_dispatch_budget WHERE hour_bucket=?",
            (bucket,),
        ).fetchone()
    count = int(row["dispatch_count"]) if row else 0
    tokens = int(row["tokens_used"]) if row else 0
    return {
        "hour_bucket": bucket,
        "dispatches_used": count,
        "dispatches_max": MAX_DISPATCHES_PER_HOUR,
        "tokens_used": tokens,
        "tokens_max": MAX_TOKENS_PER_HOUR,
    }


@router.get("/dispatches/{task_id}", dependencies=[Depends(require_owner)])
def get_dispatch(task_id: str) -> dict[str, Any]:
    """Full audit row + parsed spec for a single dispatch."""
    import json as _json
    from core.tools.claude_dispatch.audit import read_audit_row

    row = read_audit_row(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="dispatch not found")
    spec: dict[str, Any] = {}
    try:
        spec = _json.loads(row.get("spec_json") or "{}")
    except Exception:
        spec = {}
    return {**row, "spec": spec}


@router.get("/dispatches/{task_id}/diff", dependencies=[Depends(require_owner)])
def get_dispatch_diff(task_id: str) -> dict[str, Any]:
    """Live diff of a dispatch's worktree against main.

    For running tasks: subprocess git-diff on the worktree on every
    request (cheap, no caching — we want freshness during a live run).
    For finished tasks: returns the persisted diff_summary if any,
    plus the final stored worktree diff if the worktree still exists.
    Worktrees are cleaned up after dispatch finishes, so finished
    tasks may only have the diff_summary string.
    """
    from core.tools.claude_dispatch.audit import read_audit_row
    from core.tools.claude_dispatch.jail import build_worktree_path
    try:
        from core.tools.claude_dispatch.worktree import worktree_diff
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"worktree module unavailable: {exc}")

    row = read_audit_row(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="dispatch not found")

    # Always try a live diff first — gives us real-time visibility
    # while the task is mid-run, and a final snapshot just after it
    # finishes (before cleanup).
    diff_text = ""
    worktree_alive = False
    try:
        wt_path = build_worktree_path(task_id)
        worktree_alive = wt_path.is_dir()
    except Exception:
        worktree_alive = False
    if worktree_alive:
        try:
            diff_text = worktree_diff(task_id)
        except Exception as exc:
            diff_text = f"(diff unavailable: {exc})"
    return {
        "task_id": task_id,
        "status": row.get("status"),
        "worktree_alive": worktree_alive,
        "diff": diff_text,
        "diff_summary": row.get("diff_summary"),
    }
