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

_SELFHOOD_PROPOSAL_TYPE_LABELS = {
    "voice-shift-proposal": "voice",
    "posture-shift-proposal": "posture",
    "challenge-style-proposal": "challenge-style",
    "caution-shift-proposal": "caution",
}

_MEMORY_PROPOSAL_TYPE_LABELS = {
    "open-followup-update": "open-followup",
    "carry-forward-thread-update": "carry-forward-thread",
    "stable-context-update": "stable-context",
}

_CHRONICLE_PROPOSAL_TYPE_LABELS = {
    "chronicle-proposal": "chronicle",
    "consolidation-proposal": "consolidation",
    "carry-forward-proposal": "carry-forward",
    "anchored-proposal": "anchored",
}

_APPLY_READINESS_RANKS = {"low": 1, "medium": 2, "high": 3}
_SAFE_USER_MD_CANONICAL_KEYS = {
    "user-preference:reply-style:plain-grounded-concise",
    "user-preference:review-style:challenge-before-settling",
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
        elif target_file in {"SOUL.md", "IDENTITY.md"}:
            for proposal_type, label in _SELFHOOD_PROPOSAL_TYPE_LABELS.items():
                if proposal_type in canonical_key or label in canonical_key:
                    if label not in seen:
                        seen.add(label)
                        types.append(label)
        elif target_file == "MEMORY.md":
            for proposal_type, label in _MEMORY_PROPOSAL_TYPE_LABELS.items():
                if proposal_type in canonical_key or label in canonical_key:
                    if label not in seen:
                        seen.add(label)
                        types.append(label)
        elif target_file == "runtime/CHRONICLE.md":
            for proposal_type, label in _CHRONICLE_PROPOSAL_TYPE_LABELS.items():
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
    soul_items = list_runtime_contract_candidates(
        candidate_type="soul_update",
        target_file="SOUL.md",
        limit=8,
    )
    identity_items = list_runtime_contract_candidates(
        candidate_type="identity_update",
        target_file="IDENTITY.md",
        limit=8,
    )
    chronicle_items = list_runtime_contract_candidates(
        candidate_type="chronicle_draft",
        target_file="runtime/CHRONICLE.md",
        limit=8,
    )
    preference_items = [_with_apply_readiness(item) for item in preference_items]
    memory_items = [_with_apply_readiness(item) for item in memory_items]
    prompt_items = [_with_apply_readiness(item) for item in prompt_items]
    soul_items = [_with_apply_readiness(item) for item in soul_items]
    identity_items = [_with_apply_readiness(item) for item in identity_items]
    chronicle_items = [_with_apply_readiness(item) for item in chronicle_items]
    preference_types = _extract_proposal_types(preference_items, "USER.md")
    memory_types = _extract_proposal_types(memory_items, "MEMORY.md")
    prompt_types = _extract_proposal_types(prompt_items, "runtime/RUNTIME_FEEDBACK.md")
    soul_types = _extract_proposal_types(soul_items, "SOUL.md")
    identity_types = _extract_proposal_types(identity_items, "IDENTITY.md")
    chronicle_types = _extract_proposal_types(chronicle_items, "runtime/CHRONICLE.md")
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
            proposal_types=memory_types,
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
        "soul_updates": _workflow_state(
            workflow_id="soul_updates",
            label="SOUL.md Drafts",
            target_file="SOUL.md",
            proposed_count=int(counts.get("soul_update:proposed", 0)),
            approved_count=int(counts.get("soul_update:approved", 0)),
            rejected_count=int(counts.get("soul_update:rejected", 0)),
            applied_count=int(counts.get("soul_update:applied", 0)),
            superseded_count=int(counts.get("soul_update:superseded", 0)),
            items=soul_items,
            proposal_types=soul_types,
            is_canonical_self=True,
        ),
        "identity_updates": _workflow_state(
            workflow_id="identity_updates",
            label="IDENTITY.md Drafts",
            target_file="IDENTITY.md",
            proposed_count=int(counts.get("identity_update:proposed", 0)),
            approved_count=int(counts.get("identity_update:approved", 0)),
            rejected_count=int(counts.get("identity_update:rejected", 0)),
            applied_count=int(counts.get("identity_update:applied", 0)),
            superseded_count=int(counts.get("identity_update:superseded", 0)),
            items=identity_items,
            proposal_types=identity_types,
            is_canonical_self=True,
        ),
        "chronicle_drafts": _workflow_state(
            workflow_id="chronicle_drafts",
            label="Chronicle Drafts",
            target_file="runtime/CHRONICLE.md",
            proposed_count=int(counts.get("chronicle_draft:proposed", 0)),
            approved_count=int(counts.get("chronicle_draft:approved", 0)),
            rejected_count=int(counts.get("chronicle_draft:rejected", 0)),
            applied_count=int(counts.get("chronicle_draft:applied", 0)),
            superseded_count=int(counts.get("chronicle_draft:superseded", 0)),
            items=chronicle_items,
            proposal_types=chronicle_types,
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
    is_canonical_self: bool = False,
) -> dict[str, object]:
    actionable_items = [
        item
        for item in items
        if str(item.get("status") or "") in {"proposed", "approved"}
    ][:8]
    readiness_summary = _workflow_apply_readiness_summary(actionable_items)
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
        "is_canonical_self": is_canonical_self,
        "apply_readiness_high_count": readiness_summary["high_count"],
        "apply_readiness_medium_count": readiness_summary["medium_count"],
        "apply_readiness_low_count": readiness_summary["low_count"],
        "current_apply_readiness": readiness_summary["current_apply_readiness"],
        "current_apply_reason": readiness_summary["current_apply_reason"],
        "source": "/mc/runtime-contract",
    }


def _with_apply_readiness(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    readiness = candidate_apply_readiness(item)
    enriched["apply_readiness"] = readiness["apply_readiness"]
    enriched["apply_reason"] = readiness["apply_reason"]
    return enriched


def candidate_apply_readiness(item: dict[str, object]) -> dict[str, str]:
    status = str(item.get("status") or "")
    candidate_type = str(item.get("candidate_type") or "")
    target_file = str(item.get("target_file") or "")
    confidence = str(item.get("confidence") or "")
    evidence_class = str(item.get("evidence_class") or "")
    canonical_key = str(item.get("canonical_key") or "")

    if status == "approved":
        if candidate_type == "preference_update" and target_file == "USER.md":
            return {"apply_readiness": "high", "apply_reason": "bounded-safe"}
        if candidate_type in {"soul_update", "identity_update"} and target_file in {
            "SOUL.md",
            "IDENTITY.md",
        }:
            return {
                "apply_readiness": "medium",
                "apply_reason": "needs-user-confirmation",
            }
        return {"apply_readiness": "medium", "apply_reason": "needs-review"}

    if candidate_type == "prompt_feedback_update":
        if confidence == "high" and evidence_class in {
            "repeated_cross_session",
            "single_session_pattern",
        }:
            return {"apply_readiness": "medium", "apply_reason": "needs-review"}
        return {"apply_readiness": "low", "apply_reason": "needs-review"}

    if candidate_type == "memory_promotion" and target_file == "MEMORY.md":
        if status == "approved":
            return {"apply_readiness": "medium", "apply_reason": "needs-review"}
        if canonical_key.startswith(
            "workspace-memory:remembered-fact:"
        ) and confidence in {
            "high",
            "medium",
        }:
            return {"apply_readiness": "medium", "apply_reason": "factual-memory"}
        if canonical_key.startswith(
            "workspace-memory:stable-context:"
        ) and confidence in {
            "high",
            "medium",
        }:
            return {"apply_readiness": "medium", "apply_reason": "needs-review"}
        if canonical_key.startswith("workspace-memory:open-followup:"):
            return {"apply_readiness": "low", "apply_reason": "still-tentative"}
        if canonical_key.startswith("workspace-memory:carry-forward-thread:"):
            return {"apply_readiness": "low", "apply_reason": "still-tentative"}
        if canonical_key.startswith("workspace-memory:remembered-fact:"):
            return {"apply_readiness": "low", "apply_reason": "still-tentative"}
        return {"apply_readiness": "low", "apply_reason": "needs-review"}

    if candidate_type == "preference_update" and target_file == "USER.md":
        if confidence == "high" and canonical_key in _SAFE_USER_MD_CANONICAL_KEYS:
            return {"apply_readiness": "high", "apply_reason": "bounded-safe"}
        if confidence == "high" and evidence_class == "repeated_cross_session":
            return {"apply_readiness": "medium", "apply_reason": "bounded-safe"}
        if confidence in {"high", "medium"} and evidence_class in {
            "explicit_user_statement",
            "single_session_pattern",
        }:
            return {
                "apply_readiness": "medium",
                "apply_reason": "needs-user-confirmation",
            }
        return {"apply_readiness": "low", "apply_reason": "still-tentative"}

    if candidate_type in {"soul_update", "identity_update"} and target_file in {
        "SOUL.md",
        "IDENTITY.md",
    }:
        return {"apply_readiness": "low", "apply_reason": "needs-user-confirmation"}

    if candidate_type == "chronicle_draft" and target_file == "runtime/CHRONICLE.md":
        return {"apply_readiness": "low", "apply_reason": "draft-only"}

    return {"apply_readiness": "low", "apply_reason": "needs-review"}


def _workflow_apply_readiness_summary(
    items: list[dict[str, object]],
) -> dict[str, object]:
    counts = {"high_count": 0, "medium_count": 0, "low_count": 0}
    best_item: dict[str, object] | None = None
    for item in items:
        readiness = str(item.get("apply_readiness") or "low")
        if readiness == "high":
            counts["high_count"] += 1
        elif readiness == "medium":
            counts["medium_count"] += 1
        else:
            counts["low_count"] += 1
        if best_item is None or _APPLY_READINESS_RANKS.get(
            readiness, 0
        ) > _APPLY_READINESS_RANKS.get(
            str(best_item.get("apply_readiness") or "low"),
            0,
        ):
            best_item = item
    return {
        **counts,
        "current_apply_readiness": str(
            (best_item or {}).get("apply_readiness") or "low"
        ),
        "current_apply_reason": str(
            (best_item or {}).get("apply_reason") or "still-tentative"
        ),
    }
