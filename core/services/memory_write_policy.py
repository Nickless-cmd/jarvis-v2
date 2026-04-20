"""Memory Write Policy — gating + review queue for inferred memory writes.

Ported concept from jarvis-agent (2026-03): not every memory candidate
should immediately persist. This module evaluates candidate writes against
three gates (rate limit, cooldown, confidence threshold). Candidates that
fail confidence get queued for human review instead of being dropped.

Complements memory_decay_daemon (aging) and memory_breathing (strengthening).
This handles *admission control* — what gets in at all.

Explicit writes (user said "remember this") bypass all gates.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# Defaults (tunable; could move to runtime config later)
_RATE_LIMIT_PER_MINUTE = 10
_COOLDOWN_SECONDS = 60
_CONFIDENCE_THRESHOLD_INFERRED = 0.75
_REVIEW_QUEUE_ENABLED = True

_STORAGE_REL = "workspaces/default/runtime/memory_review_queue.json"


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load_queue() -> list[dict[str, Any]]:
    path = _storage_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("memory_write_policy: load failed: %s", exc)
    return []


def _save_queue(queue: list[dict[str, Any]]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("memory_write_policy: save failed: %s", exc)


# --- Rate tracking (in-memory, per-process) ---
_write_timestamps: list[datetime] = []
_last_write_per_key: dict[str, datetime] = {}


def _prune_rate_window() -> None:
    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=1)
    global _write_timestamps
    _write_timestamps = [ts for ts in _write_timestamps if ts >= cutoff]


def _rate_limit_block() -> tuple[bool, str | None]:
    _prune_rate_window()
    if len(_write_timestamps) >= _RATE_LIMIT_PER_MINUTE:
        return True, f"rate-limit ({_RATE_LIMIT_PER_MINUTE}/min)"
    return False, None


def _cooldown_block(key: str) -> tuple[bool, str | None]:
    last = _last_write_per_key.get(key)
    if not last:
        return False, None
    delta = (datetime.now(UTC) - last).total_seconds()
    if delta < _COOLDOWN_SECONDS:
        return True, f"cooldown ({_COOLDOWN_SECONDS}s)"
    return False, None


@dataclass
class PolicyDecision:
    allowed: bool
    decision: str  # "allowed" | "blocked" | "queued"
    reason: str | None = None
    queue_id: str | None = None


def evaluate_write(
    *,
    key: str,
    content: str,
    confidence: float | None = None,
    write_reason: str = "inferred",
    metadata: dict[str, Any] | None = None,
) -> PolicyDecision:
    """Decide whether to allow, block, or queue this memory candidate.

    - Explicit writes (write_reason in {"user_explicit", "user_approved"}):
      always allowed, bypass all gates.
    - Inferred writes: evaluated through rate limit → cooldown → confidence.
    """
    is_explicit = str(write_reason) in ("user_explicit", "user_approved")

    if not is_explicit:
        blocked, reason = _rate_limit_block()
        if blocked:
            return PolicyDecision(allowed=False, decision="blocked", reason=reason)
        blocked, reason = _cooldown_block(key)
        if blocked:
            return PolicyDecision(allowed=False, decision="blocked", reason=reason)

        # Confidence gate
        if confidence is not None and float(confidence) < _CONFIDENCE_THRESHOLD_INFERRED:
            if _REVIEW_QUEUE_ENABLED:
                queue_id = _enqueue_for_review(
                    key=key, content=content, confidence=confidence,
                    write_reason=write_reason, metadata=metadata or {},
                )
                return PolicyDecision(
                    allowed=False, decision="queued",
                    reason=f"low-confidence ({confidence})",
                    queue_id=queue_id,
                )
            return PolicyDecision(
                allowed=False, decision="blocked",
                reason=f"low-confidence ({confidence}) and queue disabled",
            )

    # Allowed — record the write for rate/cooldown accounting
    now = datetime.now(UTC)
    _write_timestamps.append(now)
    _last_write_per_key[key] = now
    return PolicyDecision(allowed=True, decision="allowed", reason="policy-allowed")


def _enqueue_for_review(
    *,
    key: str,
    content: str,
    confidence: float | None,
    write_reason: str,
    metadata: dict[str, Any],
) -> str:
    queue = _load_queue()
    item_id = f"mem-review-{uuid4().hex[:12]}"
    queue.append({
        "item_id": item_id,
        "key": key,
        "content": content[:2000],
        "confidence": float(confidence) if confidence is not None else None,
        "write_reason": write_reason,
        "metadata": metadata,
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
        "decided_at": None,
        "decided_by": None,
    })
    _save_queue(queue)
    return item_id


def list_pending_reviews(*, limit: int = 50) -> list[dict[str, Any]]:
    queue = _load_queue()
    pending = [q for q in queue if q.get("status") == "pending"]
    return pending[-limit:]


def approve_review(item_id: str, *, decided_by: str = "user") -> bool:
    queue = _load_queue()
    for item in queue:
        if item.get("item_id") == item_id and item.get("status") == "pending":
            item["status"] = "approved"
            item["decided_at"] = datetime.now(UTC).isoformat()
            item["decided_by"] = decided_by
            _save_queue(queue)
            return True
    return False


def reject_review(item_id: str, *, decided_by: str = "user") -> bool:
    queue = _load_queue()
    for item in queue:
        if item.get("item_id") == item_id and item.get("status") == "pending":
            item["status"] = "rejected"
            item["decided_at"] = datetime.now(UTC).isoformat()
            item["decided_by"] = decided_by
            _save_queue(queue)
            return True
    return False


def build_memory_write_policy_surface() -> dict[str, Any]:
    queue = _load_queue()
    pending = [q for q in queue if q.get("status") == "pending"]
    approved = [q for q in queue if q.get("status") == "approved"]
    rejected = [q for q in queue if q.get("status") == "rejected"]
    _prune_rate_window()
    return {
        "active": True,
        "rate_limit_per_minute": _RATE_LIMIT_PER_MINUTE,
        "cooldown_seconds": _COOLDOWN_SECONDS,
        "confidence_threshold": _CONFIDENCE_THRESHOLD_INFERRED,
        "review_queue_enabled": _REVIEW_QUEUE_ENABLED,
        "writes_in_last_minute": len(_write_timestamps),
        "pending_reviews": len(pending),
        "approved_total": len(approved),
        "rejected_total": len(rejected),
        "recent_pending": pending[-5:],
        "summary": (
            f"{len(pending)} afventer review, {len(_write_timestamps)}/min skrivninger"
            if pending else f"{len(_write_timestamps)}/{_RATE_LIMIT_PER_MINUTE} skrivninger/min"
        ),
    }


def build_memory_write_policy_prompt_section() -> str | None:
    queue = _load_queue()
    pending = [q for q in queue if q.get("status") == "pending"]
    if not pending:
        return None
    return (
        f"{len(pending)} memory-kandidat(er) afventer din godkendelse i review-køen "
        "— lav-confidence inferred writes blokeret indtil du vurderer dem."
    )
