from __future__ import annotations

from core.runtime.db import (
    list_runtime_contract_candidates,
    runtime_contract_candidate_counts,
)


def build_runtime_candidate_workflows() -> dict[str, dict[str, object]]:
    counts = runtime_contract_candidate_counts()
    preference_items = list_runtime_contract_candidates(
        candidate_type="preference_update",
        target_file="USER.md",
        status="proposed",
        limit=8,
    )
    memory_items = list_runtime_contract_candidates(
        candidate_type="memory_promotion",
        target_file="MEMORY.md",
        status="proposed",
        limit=8,
    )
    return {
        "preference_updates": _workflow_state(
            workflow_id="preference_updates",
            label="Preference Updates",
            target_file="USER.md",
            proposed_count=int(counts.get("preference_update:proposed", 0)),
            approved_count=int(counts.get("preference_update:approved", 0)),
            rejected_count=int(counts.get("preference_update:rejected", 0)),
            items=preference_items,
        ),
        "memory_promotions": _workflow_state(
            workflow_id="memory_promotions",
            label="Memory Promotions",
            target_file="MEMORY.md",
            proposed_count=int(counts.get("memory_promotion:proposed", 0)),
            approved_count=int(counts.get("memory_promotion:approved", 0)),
            rejected_count=int(counts.get("memory_promotion:rejected", 0)),
            items=memory_items,
        ),
    }


def total_pending_runtime_candidates(workflows: dict[str, dict[str, object]]) -> int:
    return sum(int(item.get("pending_count") or 0) for item in workflows.values())


def _workflow_state(
    *,
    workflow_id: str,
    label: str,
    target_file: str,
    proposed_count: int,
    approved_count: int,
    rejected_count: int,
    items: list[dict[str, object]],
) -> dict[str, object]:
    summary = (
        f"{proposed_count} proposed"
        if proposed_count > 0
        else f"No proposed {target_file} candidates."
    )
    if approved_count > 0 or rejected_count > 0:
        summary = f"{summary} {approved_count} approved, {rejected_count} rejected."
    return {
        "id": workflow_id,
        "label": label,
        "target_file": target_file,
        "status": "tracking",
        "pending_count": proposed_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "items": [
            {
                **item,
                "source": "/mc/runtime-contract",
            }
            for item in items
        ],
        "summary": summary,
        "source": "/mc/runtime-contract",
    }
