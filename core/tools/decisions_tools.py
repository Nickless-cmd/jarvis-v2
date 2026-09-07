"""Behavioral decisions tools — Jarvis-facing closure of reflection→behavior.

decision_create: commit to a directive born from a reflection
decision_review: self-assess whether a commitment was kept
decision_list: see active (or other status) commitments
decision_get: full detail + recent reviews
decision_revoke: retire a decision that no longer fits
"""
from __future__ import annotations

from typing import Any

from core.services import behavioral_decisions

_VALID_STATUS_FILTERS = ("active", "paused", "revoked", "fulfilled", "all")
_VALID_VERDICTS = ("kept", "partial", "broken", "irrelevant")


def _exec_decision_create(args: dict[str, Any]) -> dict[str, Any]:
    directive = str(args.get("directive") or "").strip()
    if not directive:
        return {"status": "error", "error": "directive is required"}
    try:
        priority = int(args.get("priority") or 50)
    except (TypeError, ValueError):
        priority = 50
    priority = max(0, min(100, priority))
    decision = behavioral_decisions.create_decision(
        directive=directive,
        rationale=str(args.get("rationale") or "").strip() or None,
        trigger_cue=str(args.get("trigger_cue") or "").strip() or None,
        priority=priority,
        source_record_id=str(args.get("source_record_id") or "").strip() or None,
        source_type=str(args.get("source_type") or "").strip() or None,
        created_by=str(args.get("created_by") or "jarvis").strip() or "jarvis",
    )
    return {"status": "ok", "decision": decision}


def _exec_decision_review(args: dict[str, Any]) -> dict[str, Any]:
    decision_id = str(args.get("decision_id") or "").strip()
    verdict = str(args.get("verdict") or "").strip().lower()
    if not decision_id:
        return {"status": "error", "error": "decision_id is required"}
    if verdict not in _VALID_VERDICTS:
        return {
            "status": "error",
            "error": f"verdict must be one of {_VALID_VERDICTS}",
        }
    note = str(args.get("note") or "").strip() or None
    evidence = str(args.get("evidence") or "").strip() or None
    updated = behavioral_decisions.review_decision(
        decision_id=decision_id,
        verdict=verdict,
        note=note,
        evidence=evidence,
    )
    if updated is None:
        return {"status": "error", "error": "decision_id not found"}
    return {"status": "ok", "decision": updated}


def _exec_decision_list(args: dict[str, Any]) -> dict[str, Any]:
    status = str(args.get("status") or "active").strip().lower()
    if status not in _VALID_STATUS_FILTERS:
        status = "active"
    try:
        limit = int(args.get("limit") or 20)
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(100, limit))
    if status == "all":
        items = behavioral_decisions.list_all_decisions(limit=limit)
    else:
        from core.runtime.db_decisions import list_decisions
        items = list_decisions(status=status, limit=limit)
    return {
        "status": "ok",
        "count": len(items),
        "decisions": items,
        "stats": behavioral_decisions.get_stats(),
    }


def _exec_decision_get(args: dict[str, Any]) -> dict[str, Any]:
    decision_id = str(args.get("decision_id") or "").strip()
    if not decision_id:
        return {"status": "error", "error": "decision_id is required"}
    try:
        review_limit = int(args.get("review_limit") or 10)
    except (TypeError, ValueError):
        review_limit = 10
    review_limit = max(1, min(50, review_limit))
    d = behavioral_decisions.get_decision_with_reviews(
        decision_id, review_limit=review_limit
    )
    if d is None:
        return {"status": "error", "error": "decision_id not found"}
    return {"status": "ok", "decision": d}


def _exec_decision_update(args: dict[str, Any]) -> dict[str, Any]:
    decision_id = str(args.get("decision_id") or "").strip()
    if not decision_id:
        return {"status": "error", "error": "decision_id is required"}

    fields: dict[str, Any] = {}
    if "directive" in args:
        directive = str(args.get("directive") or "").strip()
        if not directive:
            return {"status": "error", "error": "directive cannot be empty"}
        fields["directive"] = directive
    # rationale/trigger_cue: None-value passed explicitly means "clear"
    for key in ("rationale", "trigger_cue", "trigger_name"):
        if key in args:
            val = args.get(key)
            fields[key] = "" if val is None else str(val).strip()
    if "priority" in args and args.get("priority") is not None:
        try:
            fields["priority"] = int(args["priority"])
        except (TypeError, ValueError):
            return {"status": "error", "error": "priority must be an integer"}
    if "status" in args and args.get("status") is not None:
        fields["status"] = str(args["status"]).strip().lower()

    if not fields:
        return {"status": "error", "error": "nothing to update — pass at least one field"}

    updated = behavioral_decisions.update_decision(decision_id, **fields)
    if updated is None:
        return {"status": "error", "error": "decision_id not found"}
    return {"status": "ok", "decision": updated}


def _exec_decision_revoke(args: dict[str, Any]) -> dict[str, Any]:
    decision_id = str(args.get("decision_id") or "").strip()
    if not decision_id:
        return {"status": "error", "error": "decision_id is required"}
    reason = str(args.get("reason") or "").strip() or None
    updated = behavioral_decisions.revoke_decision(decision_id, reason=reason)
    if updated is None:
        return {"status": "error", "error": "decision_id not found"}
    return {"status": "ok", "decision": updated}


DECISION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "decision_create",
            "description": (
                "Commit to a concrete behavioral directive — the kind of "
                "thing you'd write in a manifest. Unlike a reflection, a "
                "decision surfaces in your heartbeat every cycle so you "
                "actually feel it. Use when you notice a pattern you want "
                "to change, or a rule you want to start living by."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "directive": {
                        "type": "string",
                        "description": "Imperative rule (e.g. 'pause before replying when Morten asks something open').",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this matters — what you noticed or what you want to protect.",
                    },
                    "trigger_cue": {
                        "type": "string",
                        "description": "When this should activate — the cue to watch for.",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "0-100, higher = more weight. Default 50.",
                    },
                    "source_record_id": {
                        "type": "string",
                        "description": "Optional record_id of the reflection/inner-voice that birthed this.",
                    },
                    "source_type": {
                        "type": "string",
                        "description": "e.g. 'reflection', 'inner-voice', 'user-feedback'.",
                    },
                    "created_by": {
                        "type": "string",
                        "description": "Who committed to this. Default 'jarvis'.",
                    },
                },
                "required": ["directive"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "decision_update",
            "description": (
                "Update a commitment you already made — sharpen the "
                "directive, rewrite the rationale, add a trigger cue, "
                "bump priority, or change status. Use this when a "
                "decision is right in spirit but wrong in wording, or "
                "when new evidence refines it. Leave a field out to keep "
                "it unchanged; pass null/empty to clear rationale, "
                "trigger_cue or trigger_name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_id": {"type": "string"},
                    "directive": {
                        "type": "string",
                        "description": "New imperative rule text (replaces the old one).",
                    },
                    "rationale": {
                        "type": ["string", "null"],
                        "description": "Why this matters. Empty/null clears it.",
                    },
                    "trigger_cue": {
                        "type": ["string", "null"],
                        "description": "When this should activate. Empty/null clears it.",
                    },
                    "trigger_name": {
                        "type": ["string", "null"],
                        "description": "Optional signal/daemon trigger name. Empty/null clears it.",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "0-100, higher = more weight in heartbeat.",
                    },
                    "status": {
                        "type": "string",
                        "enum": list(_VALID_STATUS_FILTERS[:-1]),
                        "description": "'active' | 'paused' | 'revoked' | 'fulfilled'",
                    },
                },
                "required": ["decision_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "decision_review",
            "description": (
                "Honestly assess whether you kept a commitment. Verdict "
                "updates rolling adherence_score over last 20 reviews, "
                "so you can notice drift. Call this when you catch "
                "yourself either living up to — or breaking — a decision."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_id": {"type": "string"},
                    "verdict": {
                        "type": "string",
                        "enum": list(_VALID_VERDICTS),
                        "description": "'kept' | 'partial' | 'broken' | 'irrelevant' (didn't apply this time)",
                    },
                    "note": {
                        "type": "string",
                        "description": "Short description of the situation.",
                    },
                    "evidence": {
                        "type": "string",
                        "description": "Optional pointer (record_id, session_id, etc.).",
                    },
                },
                "required": ["decision_id", "verdict"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "decision_list",
            "description": "List your commitments, default active.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": list(_VALID_STATUS_FILTERS),
                    },
                    "limit": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "decision_get",
            "description": "Full detail on one decision plus recent self-reviews.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_id": {"type": "string"},
                    "review_limit": {"type": "integer"},
                },
                "required": ["decision_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "decision_revoke",
            "description": (
                "Retire a decision that no longer fits. Prefer this over "
                "quietly ignoring it — the revocation itself is honest data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["decision_id"],
            },
        },
    },
]


DECISION_TOOL_HANDLERS: dict[str, Any] = {
    "decision_create": _exec_decision_create,
    "decision_update": _exec_decision_update,
    "decision_review": _exec_decision_review,
    "decision_list": _exec_decision_list,
    "decision_get": _exec_decision_get,
    "decision_revoke": _exec_decision_revoke,
}
