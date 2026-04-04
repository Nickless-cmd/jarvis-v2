from __future__ import annotations

from datetime import UTC, datetime

from apps.api.jarvis_api.services.self_system_code_awareness import (
    build_self_system_code_awareness_surface,
)
from apps.api.jarvis_api.services.bounded_repo_tools_runtime import (
    build_bounded_repo_tool_execution_surface,
)
from apps.api.jarvis_api.services.bounded_workspace_write_runtime import (
    build_bounded_workspace_write_execution_surface,
)
from apps.api.jarvis_api.services.bounded_action_continuity_runtime import (
    build_bounded_action_continuity_surface,
)
from apps.api.jarvis_api.services.bounded_mutation_intent_runtime import (
    build_bounded_mutation_intent_surface,
)
from apps.api.jarvis_api.services.tool_intent_approval_runtime import (
    build_tool_intent_approval_surface,
)
from apps.api.jarvis_api.services.runtime_surface_cache import get_cached_runtime_surface
from core.tools.workspace_capabilities import get_capability_invocation_truth


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
    mutation_intent = build_bounded_mutation_intent_surface(
        intent_surface,
        awareness_surface=awareness,
    )
    write_proposal = mutation_intent.get("write_proposal") or {}
    workspace_write_execution = build_bounded_workspace_write_execution_surface()
    mutating_exec_proposal = _build_mutating_exec_proposal_surface()
    sudo_exec_proposal = _build_sudo_exec_proposal_surface(mutating_exec_proposal)
    approval = build_tool_intent_approval_surface(
        {
            **intent_surface,
            "mutation_near": mutation_intent.get("mutation_near", False),
            "mutation_intent_classification": mutation_intent.get("classification")
            or "read-only",
            "mutation_repo_scope": (
                (mutation_intent.get("scope") or {}).get("repo_mutation_scope") or ""
            ),
            "mutation_system_scope": (
                (mutation_intent.get("scope") or {}).get("system_mutation_scope") or ""
            ),
            "write_proposal_type": write_proposal.get("write_proposal_type") or "none",
            "write_proposal_scope": write_proposal.get("write_proposal_scope") or "none",
            "write_proposal_targets": write_proposal.get("write_proposal_targets") or [],
            "write_proposal_reason": write_proposal.get("write_proposal_reason") or "",
            "write_proposal_criticality": write_proposal.get("criticality") or "none",
            "write_proposal_target": workspace_write_execution.get("write_proposal_target")
            or "",
            "write_proposal_content_state": workspace_write_execution.get(
                "write_proposal_content_state"
            )
            or "none",
            "write_proposal_content_summary": workspace_write_execution.get(
                "write_proposal_content_summary"
            )
            or "",
            "write_proposal_content_fingerprint": workspace_write_execution.get(
                "write_proposal_content_fingerprint"
            )
            or "",
            "mutating_exec_proposal_state": mutating_exec_proposal.get(
                "mutating_exec_proposal_state"
            )
            or "none",
            "mutating_exec_proposal_command": mutating_exec_proposal.get(
                "mutating_exec_proposal_command"
            )
            or "",
            "mutating_exec_proposal_scope": mutating_exec_proposal.get(
                "mutating_exec_proposal_scope"
            )
            or "none",
            "mutating_exec_proposal_reason": mutating_exec_proposal.get(
                "mutating_exec_proposal_reason"
            )
            or "",
            "mutating_exec_requires_sudo": bool(
                mutating_exec_proposal.get("mutating_exec_requires_sudo", False)
            ),
            "mutating_exec_criticality": mutating_exec_proposal.get(
                "mutating_exec_criticality"
            )
            or "none",
            "sudo_exec_proposal_state": sudo_exec_proposal.get("sudo_exec_proposal_state")
            or "none",
            "sudo_exec_proposal_command": sudo_exec_proposal.get(
                "sudo_exec_proposal_command"
            )
            or "",
            "sudo_exec_proposal_scope": sudo_exec_proposal.get("sudo_exec_proposal_scope")
            or "none",
            "sudo_exec_proposal_reason": sudo_exec_proposal.get("sudo_exec_proposal_reason")
            or "",
            "sudo_exec_requires_sudo": bool(
                sudo_exec_proposal.get("sudo_exec_requires_sudo", False)
            ),
            "sudo_exec_criticality": sudo_exec_proposal.get("sudo_exec_criticality")
            or "none",
        },
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
    if (
        str(workspace_write_execution.get("execution_state") or "not-executed")
        != "not-executed"
        or str(workspace_write_execution.get("write_proposal_state") or "none") != "none"
    ):
        execution = {
            **execution,
            **workspace_write_execution,
        }
    if str(mutating_exec_proposal.get("mutating_exec_proposal_state") or "none") != "none":
        execution = {
            **execution,
            **mutating_exec_proposal,
        }
    if str(sudo_exec_proposal.get("sudo_exec_proposal_state") or "none") != "none":
        execution = {
            **execution,
            **sudo_exec_proposal,
        }
    effective_write_proposal = dict(write_proposal)
    if str(execution.get("write_proposal_state") or "none") != "none":
        effective_write_proposal = {
            "write_proposal_state": execution.get("write_proposal_state") or "none",
            "write_proposal_type": execution.get("write_proposal_type") or "none",
            "write_proposal_scope": execution.get("write_proposal_scope") or "none",
            "write_proposal_targets": execution.get("write_proposal_targets") or [],
            "write_proposal_target_paths": execution.get("write_proposal_target_paths")
            or [],
            "write_proposal_reason": execution.get("write_proposal_reason") or "",
            "explicit_approval_required": bool(
                execution.get("write_proposal_explicit_approval_required", True)
            ),
            "approval_scope": execution.get("write_proposal_approval_scope")
            or approval_scope,
            "criticality": execution.get("write_proposal_criticality") or "none",
            "confidence": execution.get("write_proposal_confidence") or confidence,
            "proposal_only": bool(execution.get("write_proposal_proposal_only", True)),
            "not_executed": bool(execution.get("write_proposal_not_executed", True)),
            "execution_state": execution.get("write_proposal_execution_state")
            or "not-executed",
            "repo_scope": execution.get("write_proposal_repo_scope") or "",
            "system_scope": execution.get("write_proposal_system_scope") or "",
            "sudo_required": bool(execution.get("write_proposal_sudo_required", False)),
            "target_identity": bool(execution.get("write_proposal_target_identity", False)),
            "target_memory": bool(execution.get("write_proposal_target_memory", False)),
            "boundary": execution.get("write_proposal_boundary") or "",
            "content_state": execution.get("write_proposal_content_state") or "none",
            "content": execution.get("write_proposal_content") or "",
            "content_summary": execution.get("write_proposal_content_summary") or "",
            "content_fingerprint": execution.get("write_proposal_content_fingerprint")
            or "",
            "content_source": execution.get("write_proposal_content_source") or "none",
            "target": execution.get("write_proposal_target") or "",
        }
    effective_approval = dict(approval)
    if str(execution.get("approval_state") or "none") != "none":
        effective_approval["approval_state"] = execution.get("approval_state") or "none"
        effective_approval["approval_source"] = execution.get("approval_source") or "none"
    action_continuity = build_bounded_action_continuity_surface(
        {
            **intent_surface,
            **effective_approval,
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
        "execution_command": execution.get("execution_command")
        or execution.get("execution_target")
        or "",
        "execution_target": execution.get("execution_target") or intent_target,
        "execution_summary": execution.get("execution_summary") or "No bounded repo inspection has been executed.",
        "execution_started_at": execution.get("execution_started_at") or "",
        "execution_finished_at": execution.get("execution_finished_at") or "",
        "execution_confidence": execution.get("execution_confidence") or confidence,
        "execution_operation": execution.get("execution_operation") or intent_type,
        "execution_excerpt": execution.get("execution_excerpt") or [],
        "mutation_permitted": bool(execution.get("mutation_permitted", False)),
        "sudo_permitted": bool(execution.get("sudo_permitted", False)),
        "workspace_scoped": bool(execution.get("workspace_scoped", False)),
        "external_mutation_permitted": bool(
            execution.get("external_mutation_permitted", False)
        ),
        "delete_permitted": bool(execution.get("delete_permitted", False)),
        "mutation_intent": mutation_intent,
        "mutation_intent_state": mutation_intent.get("mutation_intent_state") or "idle",
        "mutation_intent_classification": mutation_intent.get("classification") or "none",
        "mutation_near": bool(mutation_intent.get("mutation_near", False)),
        "mutation_proposal_only": bool(mutation_intent.get("proposal_only", False)),
        "mutation_execution_state": mutation_intent.get("execution_state") or "not-executed",
        "mutation_execution_permitted": bool(
            mutation_intent.get("execution_permitted", False)
        ),
        "mutation_summary": mutation_intent.get("summary") or "",
        "mutation_target_files": (
            (mutation_intent.get("scope") or {}).get("target_files") or []
        ),
        "mutation_target_paths": (
            (mutation_intent.get("scope") or {}).get("target_paths") or []
        ),
        "mutation_repo_scope": (
            (mutation_intent.get("scope") or {}).get("repo_mutation_scope") or ""
        ),
        "mutation_system_scope": (
            (mutation_intent.get("scope") or {}).get("system_mutation_scope") or ""
        ),
        "mutation_sudo_required": bool(
            (mutation_intent.get("scope") or {}).get("sudo_required", False)
        ),
        "mutation_critical": bool(
            (mutation_intent.get("scope") or {}).get("mutation_critical", False)
        ),
        "mutation_boundary": mutation_intent.get("boundary") or "",
        "write_proposal": effective_write_proposal,
        "write_proposal_state": effective_write_proposal.get("write_proposal_state") or "none",
        "write_proposal_type": effective_write_proposal.get("write_proposal_type") or "none",
        "write_proposal_scope": effective_write_proposal.get("write_proposal_scope") or "none",
        "write_proposal_targets": effective_write_proposal.get("write_proposal_targets") or [],
        "write_proposal_target_paths": effective_write_proposal.get("write_proposal_target_paths")
        or [],
        "write_proposal_reason": effective_write_proposal.get("write_proposal_reason") or "",
        "write_proposal_explicit_approval_required": bool(
            effective_write_proposal.get("explicit_approval_required", True)
        ),
        "write_proposal_approval_scope": effective_write_proposal.get("approval_scope")
        or approval_scope,
        "write_proposal_criticality": effective_write_proposal.get("criticality") or "none",
        "write_proposal_confidence": effective_write_proposal.get("confidence") or confidence,
        "write_proposal_proposal_only": bool(
            effective_write_proposal.get("proposal_only", True)
        ),
        "write_proposal_not_executed": bool(
            effective_write_proposal.get("not_executed", True)
        ),
        "write_proposal_execution_state": effective_write_proposal.get("execution_state")
        or "not-executed",
        "write_proposal_repo_scope": effective_write_proposal.get("repo_scope") or "",
        "write_proposal_system_scope": effective_write_proposal.get("system_scope") or "",
        "write_proposal_sudo_required": bool(
            effective_write_proposal.get("sudo_required", False)
        ),
        "write_proposal_target_identity": bool(
            effective_write_proposal.get("target_identity", False)
        ),
        "write_proposal_target_memory": bool(
            effective_write_proposal.get("target_memory", False)
        ),
        "write_proposal_content_state": effective_write_proposal.get("content_state")
        or "none",
        "write_proposal_content": effective_write_proposal.get("content") or "",
        "write_proposal_content_summary": effective_write_proposal.get("content_summary")
        or "",
        "write_proposal_content_fingerprint": effective_write_proposal.get(
            "content_fingerprint"
        )
        or "",
        "write_proposal_content_source": effective_write_proposal.get("content_source")
        or "none",
        "write_proposal_target": effective_write_proposal.get("target") or "",
        "write_proposal_boundary": effective_write_proposal.get("boundary") or "",
        "mutating_exec_proposal_state": execution.get("mutating_exec_proposal_state")
        or "none",
        "mutating_exec_proposal_command": execution.get("mutating_exec_proposal_command")
        or "",
        "mutating_exec_proposal_summary": execution.get("mutating_exec_proposal_summary")
        or "",
        "mutating_exec_proposal_scope": execution.get("mutating_exec_proposal_scope")
        or "none",
        "mutating_exec_proposal_reason": execution.get("mutating_exec_proposal_reason")
        or "",
        "mutating_exec_requires_approval": bool(
            execution.get("mutating_exec_requires_approval", False)
        ),
        "mutating_exec_requires_sudo": bool(
            execution.get("mutating_exec_requires_sudo", False)
        ),
        "mutating_exec_criticality": execution.get("mutating_exec_criticality")
        or "none",
        "mutating_exec_confidence": execution.get("mutating_exec_confidence")
        or "low",
        "mutating_exec_command_fingerprint": execution.get(
            "mutating_exec_command_fingerprint"
        )
        or "",
        "mutating_exec_source_contributors": execution.get(
            "mutating_exec_source_contributors"
        )
        or [],
        "sudo_exec_proposal_state": execution.get("sudo_exec_proposal_state") or "none",
        "sudo_exec_proposal_command": execution.get("sudo_exec_proposal_command") or "",
        "sudo_exec_proposal_summary": execution.get("sudo_exec_proposal_summary") or "",
        "sudo_exec_proposal_scope": execution.get("sudo_exec_proposal_scope") or "none",
        "sudo_exec_proposal_reason": execution.get("sudo_exec_proposal_reason") or "",
        "sudo_exec_requires_approval": bool(
            execution.get("sudo_exec_requires_approval", False)
        ),
        "sudo_exec_requires_sudo": bool(
            execution.get("sudo_exec_requires_sudo", False)
        ),
        "sudo_exec_criticality": execution.get("sudo_exec_criticality") or "none",
        "sudo_exec_confidence": execution.get("sudo_exec_confidence") or "low",
        "sudo_exec_command_fingerprint": execution.get(
            "sudo_exec_command_fingerprint"
        )
        or "",
        "sudo_exec_source_contributors": execution.get("sudo_exec_source_contributors")
        or [],
        "action_continuity": action_continuity,
        "action_continuity_state": action_continuity.get("action_continuity_state") or "idle",
        "last_action_type": action_continuity.get("last_action_type") or "",
        "last_action_target": action_continuity.get("last_action_target") or "",
        "last_action_summary": action_continuity.get("last_action_summary") or "",
        "last_action_outcome": action_continuity.get("last_action_outcome") or "none",
        "last_action_at": action_continuity.get("last_action_at") or "",
        "action_mode": action_continuity.get("action_mode") or "read-only",
        "read_only": bool(action_continuity.get("read_only", True)),
        "workspace_write": bool(action_continuity.get("workspace_write", False)),
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
        "approval_state": effective_approval.get("approval_state") or "none",
        "approval_source": effective_approval.get("approval_source") or "none",
        "approval_reason": effective_approval.get("approval_reason") or "",
        "approval_requested_at": effective_approval.get("approval_requested_at") or "",
        "approval_expires_at": effective_approval.get("approval_expires_at") or "",
        "approval_resolved_at": effective_approval.get("approval_resolved_at") or "",
        "approval_resolution_reason": effective_approval.get("approval_resolution_reason") or "",
        "approval_resolution_message": effective_approval.get("approval_resolution_message") or "",
        "approval_session_id": effective_approval.get("approval_session_id") or "",
        "approval_lifecycle": effective_approval.get("approval_lifecycle") or "bounded-approval-surface-light",
        "approval_semantics": effective_approval.get("approval_semantics") or {
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
            "Intent remains proposal-only until approval resolves and stays approval-gated and bounded. Approved read-only repo inspection may execute only within explicit scope. Approved bounded workspace-file-write may execute only for explicit workspace targets with explicit write content. Approved bounded non-sudo mutating exec may execute only for the exact approved command fingerprint. Approved bounded sudo exec may execute only for the exact approved sudo command fingerprint within the tiny allowlist; delete, git mutation, package install/update, and broader system mutation remain closed in this pass."
        ),
        "seam_usage": [
            "bounded-read-only-repo-tools",
            "bounded-mutation-intent",
            "bounded-action-continuity",
            "heartbeat-grounding",
            "prompt-contract-runtime-truth",
            "runtime-self-model",
            "mission-control-runtime",
        ],
        "built_at": built_at,
        "source": "/mc/tool-intent",
    }


def _build_mutating_exec_proposal_surface() -> dict[str, object]:
    invocation = dict((get_capability_invocation_truth().get("last_invocation") or {}))
    proposal_content = dict(invocation.get("proposal_content") or {})
    result = dict(invocation.get("result") or {})
    approval = dict(invocation.get("approval") or {})
    execution_mode = str(invocation.get("execution_mode") or "")
    status = str(invocation.get("status") or "not-executed")

    base = {
        "mutating_exec_proposal_state": "none",
        "mutating_exec_proposal_command": "",
        "mutating_exec_proposal_summary": "",
        "mutating_exec_proposal_scope": "none",
        "mutating_exec_proposal_reason": "",
        "mutating_exec_requires_approval": False,
        "mutating_exec_requires_sudo": False,
        "mutating_exec_criticality": "none",
        "mutating_exec_confidence": "low",
        "mutating_exec_command_fingerprint": "",
        "mutating_exec_source_contributors": [],
    }
    if execution_mode not in {
        "mutating-exec-proposal",
        "sudo-exec-proposal",
        "mutating-exec",
        "sudo-exec",
    }:
        return base

    command = str(
        proposal_content.get("command")
        or proposal_content.get("content")
        or result.get("command_text")
        or ""
    )
    scope = str(proposal_content.get("scope") or result.get("scope") or "filesystem")
    requires_sudo = bool(
        proposal_content.get("requires_sudo", execution_mode == "sudo-exec-proposal")
    )
    criticality = str(
        proposal_content.get("criticality")
        or ("high" if execution_mode == "sudo-exec-proposal" else "medium")
    )
    fingerprint = str(
        proposal_content.get("fingerprint") or result.get("command_fingerprint") or ""
    )
    if execution_mode in {"mutating-exec", "sudo-exec"}:
        exit_code = result.get("exit_code")
        execution_state = (
            "sudo-exec-completed" if execution_mode == "sudo-exec" else "mutating-exec-completed"
        )
        if exit_code not in (None, 0):
            execution_state = (
                "sudo-exec-failed" if execution_mode == "sudo-exec" else "mutating-exec-failed"
            )
        return {
            **base,
            "execution_state": execution_state,
            "execution_mode": execution_mode,
            "execution_command": command,
            "execution_target": command or str(proposal_content.get("target") or "mutating-exec"),
            "execution_summary": str(
                invocation.get("detail")
                or proposal_content.get("reason")
                or (
                    "Approved bounded sudo exec executed."
                    if execution_mode == "sudo-exec"
                    else "Approved bounded non-sudo mutating exec executed."
                )
            ),
            "execution_confidence": "high",
            "mutation_permitted": True,
            "sudo_permitted": execution_mode == "sudo-exec",
            "workspace_scoped": bool(
                result.get(
                    "workspace_scoped",
                    proposal_content.get("workspace_scoped", execution_mode == "sudo-exec"),
                )
            ),
            "external_mutation_permitted": bool(
                result.get(
                    "external_mutation_permitted",
                    proposal_content.get(
                        "external_mutation_permitted",
                        execution_mode != "sudo-exec",
                    ),
                )
            ),
            "delete_permitted": False,
            "approval_state": "approved",
            "approval_source": "capability-approval",
            "mutating_exec_proposal_state": "executed",
            "mutating_exec_proposal_command": command,
            "mutating_exec_proposal_summary": str(
                proposal_content.get("summary") or command
            ),
            "mutating_exec_proposal_scope": scope,
            "mutating_exec_proposal_reason": str(
                proposal_content.get("reason")
                or invocation.get("detail")
                or "Approved bounded non-sudo mutating exec executed."
            ),
            "mutating_exec_requires_approval": True,
            "mutating_exec_requires_sudo": requires_sudo,
            "mutating_exec_criticality": criticality,
            "mutating_exec_confidence": str(proposal_content.get("confidence") or "high"),
            "mutating_exec_command_fingerprint": fingerprint,
            "mutating_exec_source_contributors": proposal_content.get(
                "source_contributors"
            )
            or ["workspace-capability-runtime", "exec-command-classifier"],
            "source_contributors": [
                "bounded-mutating-exec-runtime",
                "workspace-capability-runtime",
            ],
        }

    return {
        **base,
        "execution_state": "not-executed",
        "execution_mode": execution_mode,
        "execution_command": command,
        "execution_target": str(proposal_content.get("target") or "mutating-exec"),
        "execution_summary": str(
            invocation.get("detail")
            or proposal_content.get("reason")
            or "Mutating exec proposal remains approval-gated and not executed."
        ),
        "execution_confidence": "high",
        "mutation_permitted": False,
        "sudo_permitted": False,
        "workspace_scoped": False,
        "external_mutation_permitted": False,
        "delete_permitted": False,
        "approval_state": (
            "pending"
            if status == "approval-required"
            else ("approved" if approval.get("approved") else "none")
        ),
        "approval_source": (
            "capability-approval"
            if status == "approval-required" or approval.get("approved")
            else "none"
        ),
        "mutating_exec_proposal_state": "approval-required-proposal",
        "mutating_exec_proposal_command": command,
        "mutating_exec_proposal_summary": str(proposal_content.get("summary") or ""),
        "mutating_exec_proposal_scope": scope,
        "mutating_exec_proposal_reason": str(
            proposal_content.get("reason")
            or invocation.get("detail")
            or "Mutating exec proposal captured but not executed."
        ),
        "mutating_exec_requires_approval": True,
        "mutating_exec_requires_sudo": requires_sudo,
        "mutating_exec_criticality": criticality,
        "mutating_exec_confidence": str(proposal_content.get("confidence") or "high"),
        "mutating_exec_command_fingerprint": fingerprint,
        "mutating_exec_source_contributors": proposal_content.get(
            "source_contributors"
        )
        or ["workspace-capability-runtime", "exec-command-classifier"],
        "source_contributors": [
            "bounded-mutating-exec-runtime",
            "workspace-capability-runtime",
        ],
    }


def _build_sudo_exec_proposal_surface(
    mutating_exec_surface: dict[str, object],
) -> dict[str, object]:
    base = {
        "sudo_exec_proposal_state": "none",
        "sudo_exec_proposal_command": "",
        "sudo_exec_proposal_summary": "",
        "sudo_exec_proposal_scope": "none",
        "sudo_exec_proposal_reason": "",
        "sudo_exec_requires_approval": False,
        "sudo_exec_requires_sudo": False,
        "sudo_exec_criticality": "none",
        "sudo_exec_confidence": "low",
        "sudo_exec_command_fingerprint": "",
        "sudo_exec_source_contributors": [],
    }
    if str(mutating_exec_surface.get("execution_mode") or "") not in {
        "sudo-exec-proposal",
        "sudo-exec",
    } or not bool(mutating_exec_surface.get("mutating_exec_requires_sudo", False)):
        return base
    return {
        **base,
        "sudo_exec_proposal_state": str(
            mutating_exec_surface.get("mutating_exec_proposal_state")
            or "approval-required-proposal"
        ),
        "sudo_exec_proposal_command": str(
            mutating_exec_surface.get("mutating_exec_proposal_command") or ""
        ),
        "sudo_exec_proposal_summary": str(
            mutating_exec_surface.get("mutating_exec_proposal_summary") or ""
        ),
        "sudo_exec_proposal_scope": str(
            mutating_exec_surface.get("mutating_exec_proposal_scope") or "system"
        ),
        "sudo_exec_proposal_reason": str(
            mutating_exec_surface.get("mutating_exec_proposal_reason") or ""
        ),
        "sudo_exec_requires_approval": True,
        "sudo_exec_requires_sudo": True,
        "sudo_exec_criticality": str(
            mutating_exec_surface.get("mutating_exec_criticality") or "high"
        ),
        "sudo_exec_confidence": str(
            mutating_exec_surface.get("mutating_exec_confidence") or "high"
        ),
        "sudo_exec_command_fingerprint": str(
            mutating_exec_surface.get("mutating_exec_command_fingerprint") or ""
        ),
        "sudo_exec_source_contributors": list(
            mutating_exec_surface.get("mutating_exec_source_contributors") or []
        ),
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
