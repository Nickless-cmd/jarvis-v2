from __future__ import annotations

from datetime import UTC, datetime

from apps.api.jarvis_api.services.self_system_code_awareness import (
    build_self_system_code_awareness_surface,
)
from apps.api.jarvis_api.services.bounded_repo_tools_runtime import (
    build_bounded_repo_tool_execution_surface,
)
from apps.api.jarvis_api.services.bounded_action_continuity_runtime import (
    build_bounded_action_continuity_surface,
)
from apps.api.jarvis_api.services.tool_intent_approval_runtime import (
    build_tool_intent_approval_surface,
)
from apps.api.jarvis_api.services.runtime_surface_cache import get_cached_runtime_surface


def build_tool_intent_runtime_surface() -> dict[str, object]:
    return get_cached_runtime_surface(
        "tool_intent_runtime_surface",
        _build_tool_intent_runtime_surface,
    )


def _build_tool_intent_runtime_surface() -> dict[str, object]:
    built_at = datetime.now(UTC).isoformat()
    awareness = build_self_system_code_awareness_surface()
    repo_observation = awareness.get("repo_observation") or {}

    (
        intent_state,
        intent_type,
        intent_target,
        intent_reason,
        approval_scope,
        urgency,
        confidence,
    ) = _derive_intent_from_awareness(awareness=awareness, repo_observation=repo_observation)

    intent_surface = {
        "intent_state": intent_state,
        "intent_type": intent_type,
        "intent_target": intent_target,
        "approval_scope": approval_scope,
        "approval_required": True,
        "execution_state": "not-executed",
    }
    approval = build_tool_intent_approval_surface(
        intent_surface,
        requested_at=built_at,
    )
    execution = build_bounded_repo_tool_execution_surface(
        {
            **intent_surface,
            "approval_state": approval.get("approval_state") or "none",
            "approval_source": approval.get("approval_source") or "none",
            "confidence": confidence,
        },
        awareness_surface=awareness,
    )
    action_continuity = build_bounded_action_continuity_surface(
        {
            **intent_surface,
            **approval,
            **execution,
            "confidence": confidence,
        },
        awareness_surface=awareness,
    )
    execution_state = str(execution.get("execution_state") or "not-executed")
    truth = "derived-runtime-truth" if execution_state != "not-executed" else "proposal-only"

    return {
        "active": intent_state != "idle",
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "truth": truth,
        "kind": "approval-gated-tool-intent-light",
        "execution_state": execution_state,
        "execution_mode": execution.get("execution_mode") or "read-only",
        "execution_target": execution.get("execution_target") or intent_target,
        "execution_summary": execution.get("execution_summary") or "No bounded repo inspection has been executed.",
        "execution_started_at": execution.get("execution_started_at") or "",
        "execution_finished_at": execution.get("execution_finished_at") or "",
        "execution_confidence": execution.get("execution_confidence") or confidence,
        "execution_operation": execution.get("execution_operation") or intent_type,
        "execution_excerpt": execution.get("execution_excerpt") or [],
        "mutation_permitted": bool(execution.get("mutation_permitted", False)),
        "action_continuity": action_continuity,
        "action_continuity_state": action_continuity.get("action_continuity_state") or "idle",
        "last_action_type": action_continuity.get("last_action_type") or "",
        "last_action_target": action_continuity.get("last_action_target") or "",
        "last_action_summary": action_continuity.get("last_action_summary") or "",
        "last_action_outcome": action_continuity.get("last_action_outcome") or "none",
        "last_action_at": action_continuity.get("last_action_at") or "",
        "action_mode": action_continuity.get("action_mode") or "read-only",
        "read_only": bool(action_continuity.get("read_only", True)),
        "followup_state": action_continuity.get("followup_state") or "none",
        "followup_hint": action_continuity.get("followup_hint") or "",
        "post_action_understanding": action_continuity.get("post_action_understanding") or "",
        "post_action_concern": action_continuity.get("post_action_concern") or "stable",
        "action_continuity_confidence": action_continuity.get("confidence") or confidence,
        "action_continuity_boundary": action_continuity.get("boundary")
        or (
            "Bounded action continuity carries the latest read-only execution truth only; "
            "it is runtime continuity, not MEMORY.md, not identity, and not permission to act."
        ),
        "intent_state": intent_state,
        "intent_type": intent_type,
        "intent_target": intent_target,
        "intent_reason": intent_reason,
        "approval_required": True,
        "approval_scope": approval_scope,
        "approval_state": approval.get("approval_state") or "none",
        "approval_source": approval.get("approval_source") or "none",
        "approval_reason": approval.get("approval_reason") or "",
        "approval_requested_at": approval.get("approval_requested_at") or "",
        "approval_expires_at": approval.get("approval_expires_at") or "",
        "approval_resolved_at": approval.get("approval_resolved_at") or "",
        "approval_resolution_reason": approval.get("approval_resolution_reason") or "",
        "approval_resolution_message": approval.get("approval_resolution_message") or "",
        "approval_session_id": approval.get("approval_session_id") or "",
        "approval_lifecycle": approval.get("approval_lifecycle") or "bounded-approval-surface-light",
        "approval_semantics": approval.get("approval_semantics") or {
            "verbal_supported": True,
            "mc_supported": True,
            "mode": "explicit-bounded-approval-only",
        },
        "urgency": urgency,
        "confidence": confidence,
        "source_contributors": [
            *[
                contributor
                for contributor in (execution.get("source_contributors") or [])
                if contributor not in {"self-system-code-awareness"}
            ],
            "self-system-code-awareness",
            *[
                contributor
                for contributor in (awareness.get("source_contributors") or [])
                if contributor
                not in {
                    "self-system-code-awareness",
                    *(execution.get("source_contributors") or []),
                }
            ],
        ],
        "boundary": (
            "Intent remains proposal-only until approval resolves and stays approval-gated and bounded. Approved read-only repo inspection may execute only within explicit scope; mutation_permitted=false and no git fetch, pull, commit, reset, checkout, apply, install, or file/system write has been performed."
        ),
        "seam_usage": [
            "bounded-read-only-repo-tools",
            "bounded-action-continuity",
            "heartbeat-grounding",
            "prompt-contract-runtime-truth",
            "runtime-self-model",
            "mission-control-runtime",
        ],
        "built_at": built_at,
        "source": "/mc/tool-intent",
    }


def _derive_intent_from_awareness(
    *,
    awareness: dict[str, object],
    repo_observation: dict[str, object],
) -> tuple[str, str, str, str, str, str, str]:
    branch_name = str(repo_observation.get("branch_name") or "repo")
    upstream_ref = str(repo_observation.get("upstream_ref") or "upstream")
    concern_state = str(awareness.get("concern_state") or "stable")
    repo_status = str(awareness.get("repo_status") or "not-git")
    local_change_state = str(awareness.get("local_change_state") or "unknown")
    upstream_awareness = str(awareness.get("upstream_awareness") or "unknown")
    code_awareness_state = str(awareness.get("code_awareness_state") or "repo-unavailable")

    if upstream_awareness in {"behind", "diverged"}:
        return (
            "approval-required",
            "inspect-upstream-divergence",
            upstream_ref if upstream_ref else branch_name,
            (
                f"Read-only awareness sees branch {branch_name} as {upstream_awareness}; "
                "Jarvis can form a bounded intent to inspect divergence, but any update check or sync step still requires approval."
            ),
            "repo-update-check",
            "high",
            "high",
        )

    if local_change_state == "mixed":
        return (
            "approval-required",
            "inspect-local-changes",
            branch_name,
            (
                f"Read-only awareness sees both modified and untracked changes on {branch_name}; "
                "Jarvis can ask to inspect them, but may not act without approval."
            ),
            "repo-read",
            "high",
            "high",
        )

    if local_change_state == "modified":
        return (
            "formed",
            "inspect-working-tree",
            branch_name,
            (
                f"Read-only awareness sees local modifications on {branch_name}; "
                "Jarvis can form a bounded inspect intent, but no git action has occurred."
            ),
            "repo-read",
            "medium",
            "high",
        )

    if upstream_awareness == "ahead":
        return (
            "formed",
            "inspect-concern",
            branch_name,
            (
                f"Read-only awareness sees branch {branch_name} ahead of upstream; "
                "Jarvis can flag the divergence and ask to inspect it under approval."
            ),
            "bounded-diagnostic",
            "medium",
            "medium",
        )

    if concern_state in {"notice", "concern", "action-requires-approval"}:
        return (
            "watchful",
            "request-bounded-diagnostic",
            branch_name,
            (
                f"Awareness reports {concern_state} around repo={repo_status}, changes={local_change_state}, upstream={upstream_awareness}; "
                "Jarvis can surface a bounded diagnostic intent, but remains proposal-only."
            ),
            "bounded-diagnostic",
            "low" if concern_state == "notice" else "medium",
            "medium",
        )

    if code_awareness_state != "repo-visible":
        return (
            "watchful",
            "inspect-repo-status",
            "workspace",
            (
                "Repo visibility is limited under read-only awareness; Jarvis can ask to inspect repo state, "
                "but any deeper action would require approval."
            ),
            "repo-read",
            "low",
            "low",
        )

    return (
        "idle",
        "inspect-repo-status",
        branch_name,
        (
            f"Repo {branch_name} looks stable under read-only awareness; no tool action has been taken, "
            "but any future repo inspection beyond this bounded snapshot would still require approval."
        ),
        "repo-read",
        "low",
        "medium",
    )
