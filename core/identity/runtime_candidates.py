from __future__ import annotations

from core.runtime.db import (
    list_runtime_contract_candidates,
    recent_runtime_contract_file_writes,
    runtime_contract_candidate_counts,
    runtime_contract_file_write_counts,
)

_USER_MD_PROPOSAL_TYPE_LABELS = {
    "preference-update": "preference",
    "workstyle-update": "workstyle",
    "cadence-preference-update": "cadence",
    "reminder-worthiness-update": "reminder",
}

_PROMPT_PROPOSAL_TYPE_LABELS = {
    "communication-nudge": "communication",
    "focus-nudge": "focus",
    "challenge-nudge": "challenge",
    "world-caution-nudge": "world-caution",
}


def _extract_proposal_types(
    items: list[dict[str, object]], target_file: str
) -> list[str]:
    seen: set[str] = set()
    types: list[str] = []
    for item in items:
        canonical_key = str(item.get("canonical_key") or "")
        if not canonical_key:
            continue
        if target_file == "USER.md":
            for proposal_type, label in _USER_MD_PROPOSAL_TYPE_LABELS.items():
                if proposal_type in canonical_key or label in canonical_key:
                    if label not in seen:
                        seen.add(label)
                        types.append(label)
        elif target_file == "runtime/RUNTIME_FEEDBACK.md":
            for proposal_type, label in _PROMPT_PROPOSAL_TYPE_LABELS.items():
                if proposal_type in canonical_key or label in canonical_key:
                    if label not in seen:
                        seen.add(label)
                        types.append(label)
    return types


def build_runtime_candidate_workflows() -> dict[str, dict[str, object]]:
    counts = runtime_contract_candidate_counts()
    preference_items = list_runtime_contract_candidates(
        candidate_type="preference_update",
        target_file="USER.md",
        limit=8,
    )
    memory_items = list_runtime_contract_candidates(
        candidate_type="memory_promotion",
        target_file="MEMORY.md",
        limit=8,
    )
    prompt_items = list_runtime_contract_candidates(
        candidate_type="prompt_feedback_update",
        target_file="runtime/RUNTIME_FEEDBACK.md",
        limit=8,
    )
    preference_types = _extract_proposal_types(preference_items, "USER.md")
    prompt_types = _extract_proposal_types(prompt_items, "runtime/RUNTIME_FEEDBACK.md")
    return {
        "preference_updates": _workflow_state(
            workflow_id="preference_updates",
            label="Preference Updates",
            target_file="USER.md",
            proposed_count=int(counts.get("preference_update:proposed", 0)),
            approved_count=int(counts.get("preference_update:approved", 0)),
            rejected_count=int(counts.get("preference_update:rejected", 0)),
            applied_count=int(counts.get("preference_update:applied", 0)),
            superseded_count=int(counts.get("preference_update:superseded", 0)),
            items=preference_items,
            proposal_types=preference_types,
        ),
        "memory_promotions": _workflow_state(
            workflow_id="memory_promotions",
            label="Memory Promotions",
            target_file="MEMORY.md",
            proposed_count=int(counts.get("memory_promotion:proposed", 0)),
            approved_count=int(counts.get("memory_promotion:approved", 0)),
            rejected_count=int(counts.get("memory_promotion:rejected", 0)),
            applied_count=int(counts.get("memory_promotion:applied", 0)),
            superseded_count=int(counts.get("memory_promotion:superseded", 0)),
            items=memory_items,
            proposal_types=[],
        ),
        "prompt_feedback_updates": _workflow_state(
            workflow_id="prompt_feedback_updates",
            label="Prompt Framing Drafts",
            target_file="runtime/RUNTIME_FEEDBACK.md",
            proposed_count=int(counts.get("prompt_feedback_update:proposed", 0)),
            approved_count=int(counts.get("prompt_feedback_update:approved", 0)),
            rejected_count=int(counts.get("prompt_feedback_update:rejected", 0)),
            applied_count=int(counts.get("prompt_feedback_update:applied", 0)),
            superseded_count=int(counts.get("prompt_feedback_update:superseded", 0)),
            items=prompt_items,
            proposal_types=prompt_types,
        ),
    }


def total_pending_runtime_candidates(workflows: dict[str, dict[str, object]]) -> int:
    return sum(
        int(item.get("pending_count") or 0) + int(item.get("approved_count") or 0)
        for item in workflows.values()
    )


def build_runtime_candidate_write_history() -> dict[str, object]:
    counts = runtime_contract_file_write_counts()
    items = recent_runtime_contract_file_writes(limit=8)
    written_total = sum(
        value
        for key, value in counts.items()
        if key.endswith(":written") or key.endswith(":already-present")
    )
    return {
        "total": written_total,
        "items": [
            {
                **item,
                "source": "/mc/runtime-contract",
            }
            for item in items
        ],
        "counts": counts,
        "summary": (
            f"{written_total} applied file writes recorded."
            if written_total
            else "No applied file writes recorded yet."
        ),
        "source": "/mc/runtime-contract",
    }


def _workflow_state(
    *,
    workflow_id: str,
    label: str,
    target_file: str,
    proposed_count: int,
    approved_count: int,
    rejected_count: int,
    applied_count: int,
    superseded_count: int,
    items: list[dict[str, object]],
    proposal_types: list[str] | None = None,
) -> dict[str, object]:
    actionable_items = [
        item
        for item in items
        if str(item.get("status") or "") in {"proposed", "approved"}
    ][:8]
    summary = (
        f"{proposed_count} proposed, {approved_count} approved"
        if proposed_count > 0 or approved_count > 0
        else f"No proposed {target_file} candidates."
    )
    if rejected_count > 0 or applied_count > 0 or superseded_count > 0:
        summary = (
            f"{summary} {rejected_count} rejected, "
            f"{applied_count} applied, {superseded_count} superseded."
        )
    types = proposal_types or []
    return {
        "id": workflow_id,
        "label": label,
        "target_file": target_file,
        "status": "tracking",
        "pending_count": proposed_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "applied_count": applied_count,
        "superseded_count": superseded_count,
        "items": [
            {
                **item,
                "source": "/mc/runtime-contract",
            }
            for item in actionable_items
        ],
        "summary": summary,
        "proposal_types": types,
        "source": "/mc/runtime-contract",
    }
