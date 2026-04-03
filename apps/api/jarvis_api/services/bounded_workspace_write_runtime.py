from __future__ import annotations

from core.tools.workspace_capabilities import get_capability_invocation_truth


def build_bounded_workspace_write_execution_surface() -> dict[str, object]:
    invocation = dict(
        (get_capability_invocation_truth().get("last_invocation") or {})
    )
    capability = dict(invocation.get("capability") or {})
    approval = dict(invocation.get("approval") or {})
    execution_mode = str(invocation.get("execution_mode") or "")
    status = str(invocation.get("status") or "not-executed")
    target_path = str(capability.get("target_path") or "")
    detail = str(invocation.get("detail") or "")
    result_preview = str(invocation.get("result_preview") or "").strip()
    invoked_at = str(invocation.get("invoked_at") or "")
    finished_at = str(invocation.get("finished_at") or invoked_at)

    base = {
        "execution_state": "not-executed",
        "execution_mode": "workspace-write",
        "execution_target": target_path or "workspace",
        "execution_summary": "No approved bounded workspace write has been executed.",
        "execution_started_at": "",
        "execution_finished_at": "",
        "execution_confidence": "low",
        "execution_operation": "write-workspace-file",
        "execution_excerpt": [],
        "mutation_permitted": False,
        "workspace_scoped": False,
        "external_mutation_permitted": False,
        "delete_permitted": False,
        "approval_state": "none",
        "approval_source": "none",
        "source_contributors": ["bounded-workspace-write-runtime"],
        "write_proposal_state": "none",
        "write_proposal_type": "none",
        "write_proposal_scope": "none",
        "write_proposal_targets": [],
        "write_proposal_target_paths": [],
        "write_proposal_reason": "",
        "write_proposal_explicit_approval_required": True,
        "write_proposal_approval_scope": "workspace-write",
        "write_proposal_criticality": "none",
        "write_proposal_confidence": "low",
        "write_proposal_proposal_only": True,
        "write_proposal_not_executed": True,
        "write_proposal_execution_state": "not-executed",
        "write_proposal_repo_scope": "",
        "write_proposal_system_scope": "",
        "write_proposal_sudo_required": False,
        "write_proposal_target_identity": False,
        "write_proposal_target_memory": False,
        "write_proposal_boundary": (
            "Workspace write proposal truth is bounded to explicit approval and workspace-only targets."
        ),
        "boundary": (
            "Workspace write execution may occur only after explicit approval, only for workspace-scoped file writes, and never for external paths, delete, git mutation, or system mutation."
        ),
    }

    if execution_mode != "workspace-file-write":
        return base

    proposal_fields = {
        "write_proposal_state": "scoped-proposal",
        "write_proposal_type": "propose-file-modification",
        "write_proposal_scope": "workspace-file",
        "write_proposal_targets": [target_path] if target_path else [],
        "write_proposal_target_paths": [target_path] if target_path else [],
        "write_proposal_criticality": "medium",
        "write_proposal_confidence": "high",
    }

    if status == "approval-required":
        return {
            **base,
            **proposal_fields,
            "execution_summary": detail
            or "Workspace write capability is awaiting explicit approval.",
            "approval_state": "pending",
            "approval_source": "capability-approval",
            "write_proposal_reason": (
                detail
                or "A bounded workspace file write is proposed and still requires explicit approval."
            ),
        }

    if status == "executed":
        return {
            **base,
            **proposal_fields,
            "execution_state": "workspace-write-completed",
            "execution_target": target_path or "workspace",
            "execution_summary": detail
            or f"Approved workspace write executed for {target_path or 'workspace'}.",
            "execution_started_at": invoked_at,
            "execution_finished_at": finished_at,
            "execution_confidence": "high",
            "execution_excerpt": [result_preview] if result_preview else [],
            "mutation_permitted": True,
            "workspace_scoped": True,
            "approval_state": "approved" if approval.get("granted") else "pending",
            "approval_source": "capability-approval",
            "source_contributors": [
                "bounded-workspace-write-runtime",
                "workspace-capability-runtime",
            ],
            "write_proposal_state": "executed",
            "write_proposal_reason": (
                f"Approved workspace write executed within bounded scope for {target_path or 'workspace'}."
            ),
            "write_proposal_proposal_only": False,
            "write_proposal_not_executed": False,
            "write_proposal_execution_state": "workspace-write-completed",
        }

    return {
        **base,
        **proposal_fields,
        "execution_state": "workspace-write-failed",
        "execution_target": target_path or "workspace",
        "execution_summary": detail
        or "Approved workspace write execution did not complete successfully.",
        "execution_started_at": invoked_at,
        "execution_finished_at": finished_at,
        "approval_state": "approved" if approval.get("approved") else "none",
        "approval_source": "capability-approval" if approval.get("approved") else "none",
        "source_contributors": [
            "bounded-workspace-write-runtime",
            "workspace-capability-runtime",
        ],
        "write_proposal_reason": detail
        or "Approved workspace write execution failed inside bounded scope.",
        "write_proposal_execution_state": "workspace-write-failed",
    }
