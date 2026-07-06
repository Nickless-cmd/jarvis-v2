"""Nudge-broend — daemons drop nudges, Jarvis inspects and decides.

A persistent store for pending proactive messages. Daemons call push() to
deposit. The visible Jarvis calls inspect/pull/send/dismiss to decide what
reaches the user.

Structure: JSON file at ~/.jarvis-v2/state/nudge_broend.json
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_PATH = Path.home() / ".jarvis-v2" / "state" / "nudge_broend.json"
_MAX_NUDGES = 300  # auto-clean oldest dismissed/sent


def _load() -> list[dict[str, Any]]:
    if not _STORAGE_PATH.exists():
        return []
    try:
        with _STORAGE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("nudge_broend: load failed: %s", exc)
    return []


def _save(nudges: list[dict[str, Any]]) -> None:
    try:
        _STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _STORAGE_PATH.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(nudges, f, ensure_ascii=False, indent=2)
        tmp.replace(_STORAGE_PATH)
    except Exception as exc:
        logger.warning("nudge_broend: save failed: %s", exc)


def _cleanup(nudges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove oldest non-pending nudges if over max."""
    if len(nudges) <= _MAX_NUDGES:
        return nudges
    # Sort: pending first, then by created_at desc
    pending = [n for n in nudges if n.get("status") == "pending"]
    non_pending = sorted(
        [n for n in nudges if n.get("status") != "pending"],
        key=lambda n: n.get("created_at", ""),
        reverse=True,
    )
    return pending + non_pending[:_MAX_NUDGES - len(pending)]


def push(
    *,
    source: str = "",
    kind: str = "info",
    message: str = "",
    importance: str = "normal",
    raw_payload: dict[str, Any] | None = None,
) -> str:
    """Deposit a nudge in the broend. Returns nudge_id."""
    nudges = _load()
    nudge_id = f"nudge-{uuid4().hex[:10]}"
    entry = {
        "nudge_id": nudge_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "pending",
        "source": source[:100],
        "kind": kind[:50],
        "message": message[:1000],
        "importance": importance[:20],
    }
    if raw_payload:
        entry["raw"] = raw_payload
    nudges.append(entry)
    _save(_cleanup(nudges))
    logger.info("nudge_broend: %s deposited from %s (importance=%s)", nudge_id, source, importance)
    # Dual-write to outbound_nudges DB (2026-05-13): action_router's nudges
    # used to live ONLY in JSON brønden — never reached Jarvis' prompt. Now
    # mirrors to the unified ledger so awareness picks them up.
    try:
        from core.services.outbound_nudges import push_nudge
        push_nudge(
            source=source or "action_router",
            kind="action_router",
            message=message,
            importance=importance if importance in {"low", "normal", "high", "critical"} else "normal",
        )
    except Exception as exc:
        logger.debug("nudge_broend: dual-write to outbound_nudges failed: %s", exc)
    return nudge_id


def list_pending(limit: int = 10) -> list[dict[str, Any]]:
    """List pending nudges, newest first."""
    nudges = _load()
    pending = [n for n in nudges if n.get("status") == "pending"]
    pending.sort(key=lambda n: n.get("created_at", ""), reverse=True)
    return pending[:limit]


def count_pending() -> int:
    """Return count of pending nudges."""
    nudges = _load()
    return sum(1 for n in nudges if n.get("status") == "pending")


def get(nudge_id: str) -> dict[str, Any] | None:
    """Get a single nudge by ID."""
    nudges = _load()
    for n in nudges:
        if n.get("nudge_id") == nudge_id:
            return n
    return None


def mark_sent(nudge_id: str) -> bool:
    """Mark a nudge as sent."""
    nudges = _load()
    for n in nudges:
        if n.get("nudge_id") == nudge_id and n.get("status") == "pending":
            n["status"] = "sent"
            n["sent_at"] = datetime.now(UTC).isoformat()
            _save(nudges)
            return True
    return False


def mark_dismissed(nudge_id: str, reason: str = "") -> bool:
    """Mark a single nudge as dismissed."""
    nudges = _load()
    for n in nudges:
        if n.get("nudge_id") == nudge_id and n.get("status") == "pending":
            n["status"] = "dismissed"
            n["dismissed_at"] = datetime.now(UTC).isoformat()
            if reason:
                n["dismiss_reason"] = reason[:200]
            _save(nudges)
            return True
    return False


def dismiss_all(reason: str = "") -> int:
    """Dismiss all pending nudges. Returns count."""
    nudges = _load()
    count = 0
    now = datetime.now(UTC).isoformat()
    for n in nudges:
        if n.get("status") == "pending":
            n["status"] = "dismissed"
            n["dismissed_at"] = now
            if reason:
                n["dismiss_reason"] = reason[:200]
            count += 1
    if count:
        _save(nudges)
    return count


