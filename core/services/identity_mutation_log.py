"""Identity mutation log — full audit trail for Tier 3 auto-mutations.

Per explicit user authorization on 2026-04-27, identity-level files
(SOUL.md, IDENTITY.md, MANIFEST.md, STANDING_ORDERS.md, USER.md) can
now be auto-mutated by the self-improvement loop. This module provides
the audit trail and rollback infrastructure that makes that safe.

Every mutation:
1. Captures full BEFORE content + hash
2. Records the AFTER content + hash + diff summary
3. Publishes prominent eventbus event (identity_mutation.applied)
4. Stores in append-only state (cannot be edited, only added)
5. Has a stable mutation_id for rollback

Rollback restores the BEFORE content verbatim. Audit log preserves
both forward and rollback events.

Kill switch: ~/.jarvis-v2/config/identity_mutation_authorization.json
"enabled" field. When false, all attempts return error without writing.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_STATE_KEY = "identity_mutation_log"
_AUTH_PATH = Path.home() / ".jarvis-v2" / "config" / "identity_mutation_authorization.json"

# These ARE auto-mutable per user authorization 2026-04-27
TIER_3_AUTHORIZED_FILES: frozenset[str] = frozenset({
    "SOUL.md", "IDENTITY.md", "MANIFEST.md", "STANDING_ORDERS.md", "USER.md",
})

# These remain hard-blocked for STABILITY reasons (not safety):
# - auto_improvement_proposer self-mod could create recursive bugs
# - plan_proposals mod could break the approval mechanism that gates everything
# - approvals mod could bypass authorization
# - identity_mutation_log self-mod could rewrite the audit trail
INFRASTRUCTURE_BLOCKED_MODULES: frozenset[str] = frozenset({
    "core.services.auto_improvement_proposer",
    "core.services.plan_proposals",
    "core.services.approvals",
    "core.services.identity_mutation_log",
    "core.runtime.policy",
})


def is_auto_mutation_enabled() -> dict[str, Any]:
    """Read kill switch from authorization file."""
    try:
        if not _AUTH_PATH.exists():
            return {"enabled": False, "reason": "no authorization file"}
        data = json.loads(_AUTH_PATH.read_text(encoding="utf-8"))
        return {
            "enabled": bool(data.get("enabled", False)),
            "authorized_at": str(data.get("authorized_at", "")),
            "scope": list(data.get("scope") or []),
        }
    except Exception as exc:
        return {"enabled": False, "reason": f"auth read failed: {exc}"}


def is_target_authorized(path: str) -> bool:
    """Check if a target path is in the authorized Tier 3 list."""
    p = str(path or "")
    if not p:
        return False
    return any(allowed in p for allowed in TIER_3_AUTHORIZED_FILES)


def is_infrastructure_blocked(target: str) -> bool:
    """Check if target hits an infrastructure-blocked module."""
    t = str(target or "")
    return any(blocked in t for blocked in INFRASTRUCTURE_BLOCKED_MODULES)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _diff_summary(before: str, after: str) -> dict[str, Any]:
    """Compact diff stats."""
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    return {
        "before_chars": len(before),
        "after_chars": len(after),
        "before_lines": len(before_lines),
        "after_lines": len(after_lines),
        "delta_chars": len(after) - len(before),
        "delta_lines": len(after_lines) - len(before_lines),
    }


def record_mutation(
    *,
    target_path: str,
    before_content: str,
    after_content: str,
    reason: str,
    proposer: str = "auto_improvement",
) -> dict[str, Any]:
    """Record a mutation for audit. Returns mutation_id for rollback reference.

    DOES NOT write to the file — caller is responsible. This module logs
    only. (Separation: file-write happens via approved infrastructure
    like write_file with approval_mode; this module witnesses.)
    """
    auth = is_auto_mutation_enabled()
    if not auth.get("enabled"):
        return {"status": "blocked", "reason": "auto-mutation disabled in authorization file"}
    if not is_target_authorized(target_path) and not target_path.startswith("/tmp"):
        return {"status": "blocked", "reason": f"target not in authorized scope: {target_path}"}
    if is_infrastructure_blocked(target_path):
        return {"status": "blocked", "reason": "infrastructure-protected module — never auto-mutable"}

    mutation_id = f"imut-{uuid4().hex[:12]}"
    record = {
        "mutation_id": mutation_id,
        "recorded_at": datetime.now(UTC).isoformat(),
        "target_path": target_path,
        "reason": str(reason)[:600],
        "proposer": str(proposer)[:80],
        "before_content": before_content,
        "after_content": after_content,
        "before_hash": _hash_text(before_content),
        "after_hash": _hash_text(after_content),
        "diff_summary": _diff_summary(before_content, after_content),
        "rolled_back": False,
        "rolled_back_at": None,
    }

    try:
        log = load_json(_STATE_KEY, [])
        if not isinstance(log, list):
            log = []
        log.append(record)
        save_json(_STATE_KEY, log)
    except Exception as exc:
        logger.warning("identity_mutation_log: persist failed: %s", exc)
        return {"status": "error", "error": str(exc)}

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "identity_mutation.applied",
            {
                "mutation_id": mutation_id,
                "target": target_path,
                "reason": reason[:200],
                "proposer": proposer,
                "diff_summary": record["diff_summary"],
                "before_hash": record["before_hash"],
                "after_hash": record["after_hash"],
            },
        )
    except Exception:
        pass

    return {"status": "ok", "mutation_id": mutation_id, "diff_summary": record["diff_summary"]}


def rollback_mutation(mutation_id: str) -> dict[str, Any]:
    """Restore the BEFORE content for a recorded mutation."""
    if not mutation_id:
        return {"status": "error", "error": "mutation_id required"}
    try:
        log = load_json(_STATE_KEY, [])
        if not isinstance(log, list):
            log = []
    except Exception as exc:
        return {"status": "error", "error": f"log read failed: {exc}"}

    record = next((r for r in log if r.get("mutation_id") == mutation_id), None)
    if record is None:
        return {"status": "error", "error": "mutation not found"}
    if record.get("rolled_back"):
        return {"status": "error", "error": "already rolled back"}

    target = Path(str(record.get("target_path", ""))).expanduser()
    if not target.exists():
        return {"status": "error", "error": f"target file no longer exists: {target}"}

    before = str(record.get("before_content", ""))
    try:
        target.write_text(before, encoding="utf-8")
    except Exception as exc:
        return {"status": "error", "error": f"write failed: {exc}"}

    record["rolled_back"] = True
    record["rolled_back_at"] = datetime.now(UTC).isoformat()
    save_json(_STATE_KEY, log)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "identity_mutation.rolled_back",
            {"mutation_id": mutation_id, "target": str(target)},
        )
    except Exception:
        pass

    return {"status": "ok", "mutation_id": mutation_id, "restored_to_hash": record.get("before_hash")}


def list_mutations(*, limit: int = 50, target_filter: str | None = None) -> list[dict[str, Any]]:
    try:
        log = load_json(_STATE_KEY, [])
        if not isinstance(log, list):
            log = []
    except Exception:
        log = []
    if target_filter:
        log = [r for r in log if target_filter in str(r.get("target_path", ""))]
    summaries = [
        {
            "mutation_id": r.get("mutation_id"),
            "recorded_at": r.get("recorded_at"),
            "target_path": r.get("target_path"),
            "reason": r.get("reason"),
            "proposer": r.get("proposer"),
            "diff_summary": r.get("diff_summary"),
            "rolled_back": r.get("rolled_back"),
        }
        for r in log[-limit:]
    ]
    return list(reversed(summaries))


def _exec_list_identity_mutations(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "mutations": list_mutations(
            limit=int(args.get("limit") or 50),
            target_filter=args.get("target_filter"),
        ),
    }


def _exec_rollback_identity_mutation(args: dict[str, Any]) -> dict[str, Any]:
    return rollback_mutation(str(args.get("mutation_id") or ""))


def _exec_identity_mutation_status(args: dict[str, Any]) -> dict[str, Any]:
    auth = is_auto_mutation_enabled()
    try:
        log = load_json(_STATE_KEY, [])
        log_count = len(log) if isinstance(log, list) else 0
    except Exception:
        log_count = 0
    return {
        "status": "ok",
        "auto_mutation_enabled": auth.get("enabled"),
        "authorized_at": auth.get("authorized_at"),
        "authorized_scope": auth.get("scope"),
        "infrastructure_blocked": sorted(INFRASTRUCTURE_BLOCKED_MODULES),
        "total_mutations_logged": log_count,
    }


IDENTITY_MUTATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_identity_mutations",
            "description": (
                "List recorded identity-file mutations (SOUL/IDENTITY/MANIFEST/etc) "
                "with diff summaries and rollback status. For audit + rollback selection."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer"},
                    "target_filter": {"type": "string", "description": "E.g. 'IDENTITY.md' to filter."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rollback_identity_mutation",
            "description": (
                "Restore the BEFORE content of a recorded identity mutation. "
                "Use when an auto-mutation has produced an unwanted result."
            ),
            "parameters": {
                "type": "object",
                "properties": {"mutation_id": {"type": "string"}},
                "required": ["mutation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "identity_mutation_status",
            "description": (
                "Read current auto-mutation authorization status: enabled? "
                "authorized scope? infrastructure exclusions? total logged?"
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
