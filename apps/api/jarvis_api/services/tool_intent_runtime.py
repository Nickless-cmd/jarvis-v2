from __future__ import annotations

from datetime import UTC, datetime

from apps.api.jarvis_api.services.self_system_code_awareness import (
    build_self_system_code_awareness_surface,
)


def build_tool_intent_runtime_surface() -> dict[str, object]:
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

    return {
        "active": intent_state != "idle",
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "truth": "proposal-only",
        "kind": "approval-gated-tool-intent-light",
        "execution_state": "not-executed",
        "intent_state": intent_state,
        "intent_type": intent_type,
        "intent_target": intent_target,
        "intent_reason": intent_reason,
        "approval_required": True,
        "approval_scope": approval_scope,
        "urgency": urgency,
        "confidence": confidence,
        "source_contributors": [
            "self-system-code-awareness",
            *[
                contributor
                for contributor in (awareness.get("source_contributors") or [])
                if contributor not in {"self-system-code-awareness"}
            ],
        ],
        "boundary": (
            "Intent is proposal-only and approval-gated. No exec, git, fetch, pull, commit, reset, checkout, or apply action has been performed."
        ),
        "seam_usage": [
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
