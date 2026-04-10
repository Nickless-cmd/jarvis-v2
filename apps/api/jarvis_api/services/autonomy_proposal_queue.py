"""Autonomy proposal queue — Niveau 2 fundament.

Holder strukturerede proposals fra Jarvis der venter på Bjørns
godkendelse. Dette er en separat lane fra capability-approvals
fordi:

- Capability approvals er per-call og kortvarige
- Autonomy proposals er forslag om bounded actions Jarvis vil tage
  selv hvis han fik lov, og kan godkendes asynkront via MC

Proposals har en kind, en payload, og et eksekvering-løfte.
Når en proposal approves kalder service'en den korrekte executor
og opdaterer status til executed eller failed.

Design-principper:
- Aldrig auto-approval (Bjørn er gate)
- Aldrig irreversible actions uden eksplicit confirmation
- Hver kind har sin egen executor — ny kind = ny handler
- Alle execution attempts logges som event for audit
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Callable
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    create_autonomy_proposal,
    get_autonomy_proposal,
    list_autonomy_proposals,
    resolve_autonomy_proposal,
)

logger = logging.getLogger(__name__)


# Registry of executors per kind. Each executor takes the proposal
# payload and returns an execution result dict. Register additional
# kinds via register_proposal_executor().
_PROPOSAL_EXECUTORS: dict[str, Callable[[dict], dict]] = {}


def register_proposal_executor(kind: str, fn: Callable[[dict], dict]) -> None:
    """Register an executor for a proposal kind."""
    _PROPOSAL_EXECUTORS[kind] = fn


def get_registered_proposal_kinds() -> list[str]:
    return sorted(_PROPOSAL_EXECUTORS.keys())


def file_proposal(
    *,
    kind: str,
    title: str,
    rationale: str = "",
    payload: dict | None = None,
    created_by: str = "",
    session_id: str = "",
    run_id: str = "",
    tick_id: str = "",
    canonical_key: str = "",
) -> dict[str, object]:
    """File a new proposal in the queue.

    Returns the persisted proposal record (with generated proposal_id).
    """
    proposal_id = f"prop-{uuid4().hex[:16]}"
    proposal = create_autonomy_proposal(
        proposal_id=proposal_id,
        kind=kind,
        title=title.strip()[:200],
        rationale=rationale.strip()[:1000],
        payload=payload or {},
        created_by=created_by,
        session_id=session_id,
        run_id=run_id,
        tick_id=tick_id,
        canonical_key=canonical_key,
    )
    try:
        event_bus.publish(
            "autonomy_proposal.filed",
            {
                "proposal_id": proposal_id,
                "kind": kind,
                "title": title[:120],
                "created_by": created_by,
            },
        )
    except Exception:
        pass

    # Notify via Discord DM if gateway is running
    try:
        _notify_discord_proposal(proposal_id, kind, title)
    except Exception:
        pass

    return proposal


def _notify_discord_proposal(proposal_id: str, kind: str, title: str) -> None:
    """Send a DM to the owner when a proposal is filed — fire and forget."""
    from apps.api.jarvis_api.services.discord_gateway import (
        _client, _loop, _discord_sessions, _discord_sessions_lock,
    )
    from apps.api.jarvis_api.services.chat_sessions import list_chat_sessions

    if _client is None or _loop is None:
        return

    # Find the DM channel ID
    channel_id: int | None = None
    with _discord_sessions_lock:
        for sess_id, ch_id in _discord_sessions.items():
            sessions = list_chat_sessions()
            for s in sessions:
                if str(s.get("id")) == sess_id and s.get("title") == "Discord DM":
                    channel_id = ch_id
                    break
            if channel_id:
                break

    if channel_id is None:
        return

    msg = (
        f"Nyt forslag til godkendelse [{proposal_id}]\n"
        f"**{kind}**: {title[:100]}\n"
        f"Godkend i Mission Control → Operations → Autonomy Proposals\n"
        f"eller svar `godkend {proposal_id}` her."
    )

    import asyncio as _asyncio

    async def _send() -> None:
        from apps.api.jarvis_api.services.discord_gateway import _client as _c
        if _c is None:
            return
        ch = _c.get_channel(channel_id)
        if ch is None:
            ch = await _c.fetch_channel(channel_id)
        await ch.send(msg)

    _asyncio.run_coroutine_threadsafe(_send(), _loop)


def list_pending_proposals(*, limit: int = 50) -> list[dict[str, object]]:
    return list_autonomy_proposals(status="pending", limit=limit)


def list_recent_proposals(*, limit: int = 50) -> list[dict[str, object]]:
    return list_autonomy_proposals(limit=limit)


def approve_proposal(
    proposal_id: str,
    *,
    resolution_note: str = "",
) -> dict[str, object]:
    """Bjørn approves a proposal — execute it immediately if we have an
    executor for the kind, otherwise just mark as approved.
    """
    proposal = get_autonomy_proposal(proposal_id)
    if not proposal:
        return {"status": "not-found", "proposal_id": proposal_id}
    if str(proposal.get("status") or "") != "pending":
        return {
            "status": "not-pending",
            "proposal_id": proposal_id,
            "current_status": proposal.get("status"),
        }
    kind = str(proposal.get("kind") or "")
    executor = _PROPOSAL_EXECUTORS.get(kind)
    if executor is None:
        # Approved but we have no executor — mark approved without executing
        resolved = resolve_autonomy_proposal(
            proposal_id,
            status="approved",
            resolved_by="bjorn",
            resolution_note=resolution_note or "Approved — no executor registered",
        )
        try:
            event_bus.publish(
                "autonomy_proposal.approved_no_executor",
                {"proposal_id": proposal_id, "kind": kind},
            )
        except Exception:
            pass
        return {"status": "approved", "proposal": resolved}
    # Execute
    payload = proposal.get("payload") or {}
    try:
        result = executor(dict(payload) if isinstance(payload, dict) else {})
    except Exception as exc:
        logger.exception("autonomy proposal executor failed for %s", kind)
        resolved = resolve_autonomy_proposal(
            proposal_id,
            status="failed",
            resolved_by="executor",
            resolution_note=f"Executor raised: {exc}",
            execution_result={"error": str(exc)},
        )
        try:
            event_bus.publish(
                "autonomy_proposal.execution_failed",
                {"proposal_id": proposal_id, "kind": kind, "error": str(exc)},
            )
        except Exception:
            pass
        return {"status": "failed", "proposal": resolved, "error": str(exc)}
    resolved = resolve_autonomy_proposal(
        proposal_id,
        status="executed",
        resolved_by="bjorn",
        resolution_note=resolution_note or "Approved and executed",
        execution_result=result if isinstance(result, dict) else {"value": result},
    )
    try:
        event_bus.publish(
            "autonomy_proposal.executed",
            {
                "proposal_id": proposal_id,
                "kind": kind,
                "result_summary": str(result)[:200] if result else "",
            },
        )
    except Exception:
        pass
    return {"status": "executed", "proposal": resolved}


def reject_proposal(
    proposal_id: str,
    *,
    resolution_note: str = "",
) -> dict[str, object]:
    proposal = get_autonomy_proposal(proposal_id)
    if not proposal:
        return {"status": "not-found", "proposal_id": proposal_id}
    if str(proposal.get("status") or "") != "pending":
        return {
            "status": "not-pending",
            "proposal_id": proposal_id,
            "current_status": proposal.get("status"),
        }
    resolved = resolve_autonomy_proposal(
        proposal_id,
        status="rejected",
        resolved_by="bjorn",
        resolution_note=resolution_note or "Rejected",
    )
    try:
        event_bus.publish(
            "autonomy_proposal.rejected",
            {"proposal_id": proposal_id, "kind": str(proposal.get("kind") or "")},
        )
    except Exception:
        pass
    return {"status": "rejected", "proposal": resolved}


def build_autonomy_proposal_surface(*, limit: int = 20) -> dict[str, object]:
    """MC-friendly view of the proposal queue."""
    pending = list_pending_proposals(limit=limit)
    recent = list_recent_proposals(limit=limit)
    return {
        "active": bool(pending),
        "pending_count": len(pending),
        "registered_kinds": get_registered_proposal_kinds(),
        "items": pending,
        "recent": recent,
        "summary": (
            f"{len(pending)} autonomy proposal(s) awaiting Bjørn approval"
            if pending
            else "No autonomy proposals pending"
        ),
    }


# ---------------------------------------------------------------------------
# Built-in executors
# ---------------------------------------------------------------------------


def _execute_memory_rewrite_proposal(payload: dict) -> dict:
    """Execute an approved memory-rewrite proposal.

    Payload schema:
        {"target": "MEMORY.md" | "USER.md", "new_content": "..."}
    """
    from core.tools.workspace_capabilities import invoke_workspace_capability

    target = str(payload.get("target") or "MEMORY.md")
    new_content = str(payload.get("new_content") or "")
    if not new_content:
        return {"status": "error", "error": "missing new_content in payload"}
    result = invoke_workspace_capability(
        "tool:rewrite-workspace-memory",
        write_content=new_content,
        approved=True,
        target_path=target,
    )
    return {
        "status": result.get("status"),
        "detail": result.get("detail"),
        "result": result.get("result"),
    }


def _execute_source_edit_proposal(payload: dict) -> dict:
    """Execute an approved source-edit proposal.

    Payload schema (set by tool:propose-source-edit handler):
        {
            "target_path": "/abs/path/to/file",
            "relative_path": "core/foo.py",
            "base_fingerprint": "sha1[:16]",
            "new_content": "...",
            "bytes_delta": int,
            ...
        }

    Verification at execute time:
    - target file still exists
    - current disk fingerprint == base_fingerprint
      (otherwise: someone else has touched the file since the
       proposal was filed and we abort to avoid clobber)
    - readback after write matches new_fingerprint
    """
    from pathlib import Path as _Path
    from hashlib import sha1 as _sha1

    target_path = str(payload.get("target_path") or "")
    base_fingerprint = str(payload.get("base_fingerprint") or "")
    new_content = str(payload.get("new_content") or "")
    if not target_path or not new_content:
        return {"status": "error", "error": "missing target_path or new_content"}

    path = _Path(target_path)
    if not path.exists() or not path.is_file():
        return {
            "status": "error",
            "error": f"target file no longer exists: {target_path}",
        }

    def _fp(text: str) -> str:
        return _sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]

    try:
        current_content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"status": "error", "error": f"read failed: {exc}"}

    current_fingerprint = _fp(current_content)
    if base_fingerprint and base_fingerprint != current_fingerprint:
        return {
            "status": "stale",
            "error": (
                f"file changed under proposal: base={base_fingerprint} "
                f"now={current_fingerprint}"
            ),
            "current_fingerprint": current_fingerprint,
            "base_fingerprint": base_fingerprint,
        }

    # Apply
    try:
        path.write_text(new_content, encoding="utf-8")
    except Exception as exc:
        return {"status": "error", "error": f"write failed: {exc}"}

    # Readback verification
    try:
        readback_content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"status": "error", "error": f"readback failed: {exc}"}
    readback_fingerprint = _fp(readback_content)
    new_fingerprint = _fp(new_content)
    readback_match = readback_fingerprint == new_fingerprint

    return {
        "status": "executed",
        "target_path": target_path,
        "bytes_before": len(current_content.encode("utf-8")),
        "bytes_after": len(new_content.encode("utf-8")),
        "bytes_delta": len(new_content.encode("utf-8")) - len(current_content.encode("utf-8")),
        "base_fingerprint": current_fingerprint,
        "new_fingerprint": new_fingerprint,
        "readback_fingerprint": readback_fingerprint,
        "readback_match": readback_match,
    }


def _execute_git_commit_proposal(payload: dict) -> dict:
    """Execute an approved git-commit proposal.

    Payload schema:
        {
            "files": ["path/to/file", ...],  # relative paths to stage; ["."] for all
            "message": "commit message",
            "project_root": "/abs/path/to/repo",
        }
    """
    import subprocess as _sp
    from pathlib import Path as _Path

    files = payload.get("files") or ["."]
    message = str(payload.get("message") or "").strip()
    project_root = str(payload.get("project_root") or "")

    if not message:
        return {"status": "error", "error": "commit message is required"}
    if not project_root or not _Path(project_root).is_dir():
        return {"status": "error", "error": f"project_root not found: {project_root}"}

    # Stage files
    add_cmd = ["git", "add", "--"] + [str(f) for f in files]
    add_result = _sp.run(add_cmd, capture_output=True, text=True, cwd=project_root)
    if add_result.returncode != 0:
        return {
            "status": "error",
            "error": f"git add failed: {add_result.stderr.strip()}",
        }

    # Commit
    commit_result = _sp.run(
        ["git", "commit", "-m", message],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    if commit_result.returncode != 0:
        stderr = commit_result.stderr.strip()
        stdout = commit_result.stdout.strip()
        # "nothing to commit" is not an error
        if "nothing to commit" in stdout or "nothing to commit" in stderr:
            return {"status": "ok", "skipped": True, "reason": "nothing to commit"}
        return {"status": "error", "error": f"git commit failed: {stderr or stdout}"}

    output = commit_result.stdout.strip()
    # Extract commit hash from output like "[main abc1234] message"
    import re as _re
    m = _re.search(r"\[(?:\S+)\s+([0-9a-f]+)\]", output)
    commit_hash = m.group(1) if m else "unknown"

    return {
        "status": "executed",
        "commit": commit_hash,
        "message": message,
        "files": files,
        "output": output,
    }


# Register built-ins on import
register_proposal_executor("memory-rewrite", _execute_memory_rewrite_proposal)
register_proposal_executor("source-edit", _execute_source_edit_proposal)
register_proposal_executor("git-commit", _execute_git_commit_proposal)
