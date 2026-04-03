from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from core.runtime.db import (
    get_bounded_action_continuity_state,
    upsert_bounded_action_continuity_state,
)


def build_bounded_action_continuity_surface(
    tool_intent_surface: dict[str, object],
    *,
    awareness_surface: dict[str, object] | None = None,
) -> dict[str, object]:
    persisted = get_bounded_action_continuity_state()
    current = _derive_current_action_continuity_surface(
        tool_intent_surface,
        awareness_surface=awareness_surface,
    )
    if current is None:
        if persisted is not None:
            return _normalize_action_continuity_surface(persisted)
        return _normalize_action_continuity_surface(_default_action_continuity_surface())

    if persisted is not None and str(persisted.get("continuity_id") or "") == str(
        current.get("continuity_id") or ""
    ):
        return _normalize_action_continuity_surface(persisted)

    persistable = dict(current)
    persistable.pop("workspace_write", None)
    persistable.pop("mutating_exec", None)
    stored = upsert_bounded_action_continuity_state(**persistable)
    return _normalize_action_continuity_surface(stored)


def _derive_current_action_continuity_surface(
    tool_intent_surface: dict[str, object],
    *,
    awareness_surface: dict[str, object] | None,
) -> dict[str, object] | None:
    execution_state = str(tool_intent_surface.get("execution_state") or "not-executed")
    if execution_state not in {
        "read-only-completed",
        "read-only-failed",
        "workspace-write-completed",
        "workspace-write-failed",
        "mutating-exec-completed",
        "mutating-exec-failed",
    }:
        return None

    action_type = str(
        tool_intent_surface.get("execution_operation")
        or tool_intent_surface.get("intent_type")
        or "inspect-repo-status"
    )
    action_target = str(
        tool_intent_surface.get("execution_target")
        or tool_intent_surface.get("intent_target")
        or "workspace"
    )
    action_summary = str(
        tool_intent_surface.get("execution_summary")
        or "No bounded repo inspection summary recorded."
    )
    action_at = str(
        tool_intent_surface.get("execution_finished_at")
        or tool_intent_surface.get("execution_started_at")
        or datetime.now(UTC).isoformat()
    )
    action_mode = str(tool_intent_surface.get("execution_mode") or "read-only")
    mutation_permitted = bool(tool_intent_surface.get("mutation_permitted", False))
    confidence = str(
        tool_intent_surface.get("execution_confidence")
        or tool_intent_surface.get("confidence")
        or "low"
    )
    followup_state, followup_hint, post_action_understanding, post_action_concern = (
        _derive_followup_from_awareness(
            execution_state=execution_state,
            action_type=action_type,
            action_target=action_target,
            awareness_surface=awareness_surface or {},
        )
    )
    continuity_state = _derive_continuity_state(
        execution_state=execution_state,
        followup_state=followup_state,
    )
    source_contributors = _merge_unique(
        [
            "bounded-action-continuity-runtime",
            "bounded-read-only-repo-tools",
            "tool-intent-runtime",
        ],
        tool_intent_surface.get("source_contributors") or [],
    )
    continuity_id = _continuity_id(
        action_type=action_type,
        action_target=action_target,
        action_summary=action_summary,
        action_outcome=execution_state,
        approval_resolved_at=str(tool_intent_surface.get("approval_resolved_at") or ""),
        approval_source=str(tool_intent_surface.get("approval_source") or "none"),
    )
    return {
        "active": True,
        "kind": "bounded-action-continuity-light",
        "continuity_id": continuity_id,
        "action_continuity_state": continuity_state,
        "last_action_type": action_type,
        "last_action_target": action_target,
        "last_action_summary": action_summary,
        "last_action_outcome": execution_state,
        "last_action_at": action_at,
        "action_mode": action_mode,
        "read_only": action_mode == "read-only",
        "workspace_write": action_mode == "workspace-write",
        "mutating_exec": action_mode == "mutating-exec",
        "mutation_permitted": mutation_permitted,
        "followup_state": followup_state,
        "followup_hint": followup_hint,
        "post_action_understanding": post_action_understanding,
        "post_action_concern": post_action_concern,
        "confidence": confidence,
        "source_contributors": source_contributors,
        "boundary": (
            "Bounded action continuity carries the latest bounded execution truth only; "
            "it is runtime continuity, not MEMORY.md, not identity, and not permission to broaden write scope."
        ),
        "updated_at": action_at,
        "source": "/runtime/bounded-action-continuity",
    }


def _derive_followup_from_awareness(
    *,
    execution_state: str,
    action_type: str,
    action_target: str,
    awareness_surface: dict[str, object],
) -> tuple[str, str, str, str]:
    concern_state = str(awareness_surface.get("concern_state") or "stable")
    local_change_state = str(awareness_surface.get("local_change_state") or "unknown")
    upstream_awareness = str(awareness_surface.get("upstream_awareness") or "unknown")
    repo_status = str(awareness_surface.get("repo_status") or "not-git")

    if execution_state == "read-only-failed":
        return (
            "retry-read-only",
            "Den bounded read-only inspection fejlede; re-check repo-runtime og spørg igen inden en ny inspect-intent dannes.",
            "Read-only execution forsøgte at løbe, men gav ikke et stabilt observationsresultat.",
            "concern",
        )

    if execution_state == "workspace-write-failed":
        return (
            "review-bounded-write",
            "Den bounded workspace write fejlede; bekræft scope, approval og eksplicit write_content før et nyt forsøg.",
            "Workspace write execution nåede ikke et stabilt resultat inden for den godkendte scope.",
            "concern",
        )

    if execution_state == "mutating-exec-failed":
        return (
            "review-bounded-mutating-exec",
            "Den approved bounded non-sudo mutating exec fejlede; review den godkendte kommando og output før et nyt forsøg.",
            "Approved bounded non-sudo mutating exec nåede ikke et stabilt resultat.",
            "concern",
        )

    if execution_state == "workspace-write-completed":
        return (
            "bounded-write-recorded",
            f"Approved workspace write blev udført for {action_target}; næste skridt er review af resultatet inden yderligere mutation.",
            f"Workspace write execution udførte en bounded ændring mod {action_target} inden for eksplicit approval.",
            "stable",
        )

    if execution_state == "mutating-exec-completed":
        return (
            "bounded-mutating-exec-recorded",
            f"Approved bounded non-sudo mutating exec blev udført for {action_target}; næste skridt er review af output og effekt før yderligere mutation.",
            f"Approved bounded non-sudo mutating exec udførte {action_type} mod {action_target} inden for eksplicit approval.",
            "stable",
        )

    if upstream_awareness in {"behind", "diverged"}:
        return (
            "approval-may-be-needed",
            f"Read-only inspection bekræftede upstream {upstream_awareness} for {action_target}; næste relevante skridt vil fortsat kræve eksplicit approval.",
            f"Read-only execution viste, at upstream relationen stadig er {upstream_awareness} efter {action_type}.",
            "action-requires-approval",
        )

    if local_change_state in {"modified", "mixed", "untracked"}:
        return (
            "carry-forward",
            f"Read-only inspection bekræftede lokale ændringer ({local_change_state}); concern bør bæres videre uden mutation.",
            f"Read-only execution viste, at repoet stadig er {repo_status} med lokale ændringer={local_change_state}.",
            concern_state if concern_state != "stable" else "concern",
        )

    if concern_state in {"notice", "concern", "action-requires-approval"}:
        return (
            "monitor",
            "Read-only inspection gav ingen mutation; concern-signalet bør fortsat holdes synligt i runtime-awareness.",
            f"Read-only execution gav bounded repo-truth, men concern er stadig {concern_state}.",
            concern_state,
        )

    return (
        "none",
        "Read-only inspection fandt ingen ny follow-up ud over den bounded observation.",
        "Read-only execution gav et bounded resultat uden ny concern eller opfølgning.",
        "stable",
    )


def _derive_continuity_state(*, execution_state: str, followup_state: str) -> str:
    if execution_state in {
        "read-only-failed",
        "workspace-write-failed",
        "mutating-exec-failed",
    }:
        return "attention-required"
    if followup_state in {
        "approval-may-be-needed",
        "carry-forward",
        "monitor",
        "retry-read-only",
        "review-bounded-write",
        "bounded-write-recorded",
        "review-bounded-mutating-exec",
        "bounded-mutating-exec-recorded",
    }:
        return "carrying-forward"
    return "settled"


def _continuity_id(
    *,
    action_type: str,
    action_target: str,
    action_summary: str,
    action_outcome: str,
    approval_resolved_at: str,
    approval_source: str,
) -> str:
    digest = hashlib.sha1(
        "|".join(
            [
                action_type,
                action_target,
                action_summary,
                action_outcome,
                approval_resolved_at,
                approval_source,
            ]
        ).encode("utf-8")
    ).hexdigest()
    return f"action-continuity:{digest[:16]}"


def _default_action_continuity_surface() -> dict[str, object]:
    return {
        "active": False,
        "kind": "bounded-action-continuity-light",
        "continuity_id": "",
        "action_continuity_state": "idle",
        "last_action_type": "",
        "last_action_target": "",
        "last_action_summary": "No bounded read-only action continuity is being carried yet.",
        "last_action_outcome": "none",
        "last_action_at": "",
        "action_mode": "read-only",
        "read_only": True,
        "workspace_write": False,
        "mutating_exec": False,
        "mutation_permitted": False,
        "followup_state": "none",
        "followup_hint": "",
        "post_action_understanding": "",
        "post_action_concern": "stable",
        "confidence": "low",
        "source_contributors": ["bounded-action-continuity-runtime"],
        "boundary": (
            "Bounded action continuity carries the latest bounded execution truth only; "
            "it is runtime continuity, not MEMORY.md, not identity, and not permission to broaden write scope."
        ),
        "updated_at": "",
        "source": "/runtime/bounded-action-continuity",
    }


def _normalize_action_continuity_surface(surface: dict[str, object]) -> dict[str, object]:
    normalized = dict(surface)
    normalized["workspace_write"] = (
        str(normalized.get("action_mode") or "read-only") == "workspace-write"
    )
    normalized["mutating_exec"] = (
        str(normalized.get("action_mode") or "read-only") == "mutating-exec"
    )
    return normalized


def _merge_unique(left: list[str], right: list[object]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for raw in [*left, *right]:
        item = str(raw or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        merged.append(item)
    return merged
