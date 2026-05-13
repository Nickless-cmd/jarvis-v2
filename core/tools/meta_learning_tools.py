"""Meta-læring tools — Phase 1 (AGI track #3).

read_learning_memo(memo_id) — fetch full memo + mark as acknowledged.
list_learning_memos(limit=5) — overview of recent memos.

Mirror pattern from curiosity_tools and skill_chain_phase2 tools.
"""
from __future__ import annotations

import logging
from typing import Any

from core.runtime.settings import load_settings
from core.services.meta_learning_retrospective import (
    acknowledge_memo,
    fetch_memo_by_id,
    list_recent_memos,
)

logger = logging.getLogger(__name__)


def _phase1_enabled() -> bool:
    try:
        return bool(load_settings().meta_learning_enabled)
    except Exception:
        return True  # fail-open


def _safe_publish(family_event: str, payload: dict[str, Any]) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(family_event, payload)
    except Exception as exc:
        logger.debug("meta_learning_tools: event publish failed: %s", exc)


def _exec_read_learning_memo(args: dict[str, Any]) -> dict[str, Any]:
    """Read full memo and acknowledge it."""
    if not _phase1_enabled():
        return {"status": "disabled", "note": "meta_learning is disabled"}

    memo_id = str(args.get("memo_id") or "").strip()
    if not memo_id:
        return {"status": "rejected", "reason": "memo_id is required"}

    memo = fetch_memo_by_id(memo_id)
    if not memo:
        return {"status": "error", "reason": f"memo not found: {memo_id}"}

    was_already_acked = memo.get("acknowledged_at") is not None
    acknowledge_memo(memo_id)

    if not was_already_acked:
        _safe_publish("cognitive_meta_learning.memo_acknowledged", {
            "memo_id": memo_id,
            "period_start": memo.get("period_start"),
            "period_end": memo.get("period_end"),
        })

    return {
        "status": "ok",
        "memo_id": memo_id,
        "period_start": memo.get("period_start"),
        "period_end": memo.get("period_end"),
        "narrative": memo.get("narrative"),
        "hypothesis_candidates": memo.get("hypothesis_candidates", []),
        "model_used": memo.get("model_used"),
        "was_already_acknowledged": was_already_acked,
    }


def _exec_list_learning_memos(args: dict[str, Any]) -> dict[str, Any]:
    if not _phase1_enabled():
        return {"status": "disabled", "note": "meta_learning is disabled"}
    try:
        limit = int(args.get("limit") or 5)
    except (TypeError, ValueError):
        limit = 5
    return {
        "status": "ok",
        "memos": list_recent_memos(limit=limit),
    }


META_LEARNING_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_learning_memo",
            "description": (
                "Læs et ugentligt meta-læringsmemo i fuld længde. Hver gang "
                "et nyt memo bliver genereret (søndag morgen), kan du se en "
                "kort teaser i awareness — kald dette tool for at læse hele "
                "memoet og se hypothesis-kandidater. Memo'et markeres som "
                "acknowledged så det ikke længere vises i awareness. "
                "Brug citationsnøgler i memoet (plan_id, prediction_id, "
                "obs_id, ISO-datotid) sammen med curiosity-tools for at "
                "grave i konkrete tilfælde."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "memo_id": {
                        "type": "string",
                        "description": "ID for memoet, fx 'memo-abc123'.",
                    },
                },
                "required": ["memo_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_learning_memos",
            "description": (
                "List dine seneste meta-læringsmemos (kort metadata, "
                "ikke fuld narrative). Bruges til at se historik og finde "
                "memo-IDs til read_learning_memo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Antal memos (default 5, max 50).",
                    },
                },
                "required": [],
            },
        },
    },
]

def _exec_register_hypothesis(args: dict[str, Any]) -> dict[str, Any]:
    """Promote a memo hypothesis_candidate to an active tracked hypothesis."""
    if not _phase1_enabled():
        return {"status": "disabled"}
    memo_id = str(args.get("memo_id") or "").strip()
    try:
        idx = int(args.get("candidate_idx") or 0)
    except (TypeError, ValueError):
        return {"status": "rejected", "reason": "candidate_idx must be integer"}
    if not memo_id:
        return {"status": "rejected", "reason": "memo_id required"}
    try:
        from core.services.meta_learning_hypotheses import register_hypothesis
        return register_hypothesis(memo_id=memo_id, candidate_idx=idx)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_record_hypothesis_sample(args: dict[str, Any]) -> dict[str, Any]:
    if not _phase1_enabled():
        return {"status": "disabled"}
    hyp_id = str(args.get("hypothesis_id") or "").strip()
    supports = bool(args.get("supports"))
    note = args.get("note")
    if not hyp_id:
        return {"status": "rejected", "reason": "hypothesis_id required"}
    try:
        from core.services.meta_learning_hypotheses import record_hypothesis_sample
        return record_hypothesis_sample(hypothesis_id=hyp_id, supports=supports, note=note)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


META_LEARNING_TOOL_DEFINITIONS.extend([
    {
        "type": "function",
        "function": {
            "name": "register_hypothesis",
            "description": (
                "Promovér en hypotese-kandidat fra et meta-læringsmemo til "
                "en aktiv testet hypotese. Efter sample_size_needed prøver "
                "auto-resolves den til supported/contradicted/uncertain."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "memo_id": {"type": "string"},
                    "candidate_idx": {"type": "integer", "description": "0-indekseret position i memo.hypothesis_candidates"},
                },
                "required": ["memo_id", "candidate_idx"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_hypothesis_sample",
            "description": (
                "Registrér én observation der enten understøtter eller "
                "modsiger en aktiv hypotese. supports=true betyder "
                "observationen stemmer med hypotesen."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hypothesis_id": {"type": "string"},
                    "supports": {"type": "boolean"},
                    "note": {"type": "string"},
                },
                "required": ["hypothesis_id", "supports"],
            },
        },
    },
])

META_LEARNING_TOOL_HANDLERS: dict[str, Any] = {
    "read_learning_memo": _exec_read_learning_memo,
    "list_learning_memos": _exec_list_learning_memos,
    "register_hypothesis": _exec_register_hypothesis,
    "record_hypothesis_sample": _exec_record_hypothesis_sample,
}
