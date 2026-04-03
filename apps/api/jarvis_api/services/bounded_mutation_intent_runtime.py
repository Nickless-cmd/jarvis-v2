from __future__ import annotations

from pathlib import PurePosixPath

from core.tools.workspace_capabilities import (
    classify_workspace_execution_mode,
    load_workspace_capabilities,
)

_MUTATION_NEAR_CLASSES = {
    "modify-file",
    "delete-file",
    "git-mutate",
    "system-mutate",
}
_WRITE_PROPOSAL_TYPES = {
    "modify-file": "propose-file-modification",
    "delete-file": "propose-file-deletion",
    "git-mutate": "propose-git-mutation",
    "system-mutate": "propose-system-mutation",
}
_MAX_TARGET_FILES = 8


def build_bounded_mutation_intent_surface(
    intent_surface: dict[str, object],
    *,
    awareness_surface: dict[str, object],
) -> dict[str, object]:
    intent_state = str(intent_surface.get("intent_state") or "idle")
    intent_type = str(intent_surface.get("intent_type") or "inspect-repo-status")
    approval_scope = str(intent_surface.get("approval_scope") or "repo-read")
    repo_observation = awareness_surface.get("repo_observation") or {}

    target_files, target_paths = _derive_targets(repo_observation)
    classification = _derive_classification(
        intent_state=intent_state,
        intent_type=intent_type,
        approval_scope=approval_scope,
        awareness_surface=awareness_surface,
        repo_observation=repo_observation,
    )
    mutation_near = classification in _MUTATION_NEAR_CLASSES
    state = "idle"
    if intent_state != "idle":
        state = "proposal-only" if mutation_near else "read-only"

    repo_scope = _derive_repo_mutation_scope(
        classification=classification,
        approval_scope=approval_scope,
        repo_observation=repo_observation,
    )
    system_scope = _derive_system_mutation_scope(
        classification=classification,
        approval_scope=approval_scope,
        intent_type=intent_type,
    )
    sudo_required = _derive_sudo_required(
        classification=classification,
        approval_scope=approval_scope,
        intent_type=intent_type,
    )
    mutation_critical = classification in {"delete-file", "git-mutate", "system-mutate"}
    capabilities_summary = _approval_required_mutation_capability_summary()
    write_proposal = _build_write_proposal_surface(
        classification=classification,
        mutation_near=mutation_near,
        intent_state=intent_state,
        intent_type=intent_type,
        approval_scope=approval_scope,
        target_files=target_files,
        target_paths=target_paths,
        repo_scope=repo_scope,
        system_scope=system_scope,
        sudo_required=sudo_required,
        mutation_critical=mutation_critical,
    )

    if state == "idle":
        summary = "No bounded mutation intent is active. Current runtime intent is idle."
    elif mutation_near:
        summary = (
            f"Current intent is {state} and mutation-near: classification={classification}; "
            "explicit scoped approval is required before any file, git, package, or system change."
        )
    else:
        summary = (
            "Current intent remains read-only. Jarvis may inspect and propose, but no mutation-near scope is active."
        )

    return {
        "active": state != "idle",
        "kind": "bounded-mutation-intent-light",
        "mutation_intent_state": state,
        "classification": classification,
        "mutation_near": mutation_near,
        "proposal_only": state == "proposal-only",
        "approval_required": bool(intent_surface.get("approval_required", True)),
        "explicit_approval_required": True,
        "not_executed": True,
        "execution_state": "not-executed",
        "execution_permitted": False,
        "summary": summary,
        "write_proposal": write_proposal,
        "scope": {
            "target_files": target_files,
            "target_paths": target_paths,
            "repo_mutation_scope": repo_scope,
            "system_mutation_scope": system_scope,
            "sudo_required": sudo_required,
            "mutation_critical": mutation_critical,
        },
        "capability_boundary": capabilities_summary,
        "boundary": (
            "Bounded mutation intent is classification-only runtime truth. It distinguishes read-only from mutation-near intent, "
            "but remains proposal-only, approval-gated, and not-executed. It is not MEMORY.md, not identity, and not a write path."
        ),
        "source_contributors": [
            "bounded-mutation-intent-runtime",
            "self-system-code-awareness",
            "workspace-capabilities",
        ],
        "source": "/runtime/bounded-mutation-intent",
    }


def _build_write_proposal_surface(
    *,
    classification: str,
    mutation_near: bool,
    intent_state: str,
    intent_type: str,
    approval_scope: str,
    target_files: list[str],
    target_paths: list[str],
    repo_scope: str,
    system_scope: str,
    sudo_required: bool,
    mutation_critical: bool,
) -> dict[str, object]:
    proposal_type = _WRITE_PROPOSAL_TYPES.get(classification, "none")
    if intent_state == "idle" or not mutation_near:
        return {
            "active": False,
            "write_proposal_state": "none",
            "write_proposal_type": "none",
            "write_proposal_scope": "none",
            "write_proposal_targets": [],
            "write_proposal_target_paths": [],
            "write_proposal_reason": "No bounded approval-scoped write proposal is active.",
            "explicit_approval_required": True,
            "approval_scope": approval_scope or "repo-read",
            "criticality": "none",
            "confidence": "low",
            "proposal_only": True,
            "not_executed": True,
            "execution_state": "not-executed",
            "mutation_near": False,
            "repo_scope": "",
            "system_scope": "",
            "sudo_required": False,
            "target_identity": False,
            "target_memory": False,
            "boundary": (
                "Write proposal light is scoped runtime truth only. It is not execution, "
                "not approval itself, not identity, and not MEMORY.md mutation."
            ),
            "source_contributors": ["bounded-mutation-intent-runtime"],
        }

    scope = "repo-file" if proposal_type in {
        "propose-file-modification",
        "propose-file-deletion",
    } else ("git" if proposal_type == "propose-git-mutation" else "system")
    criticality = "high" if mutation_critical else "medium"
    confidence = _derive_write_proposal_confidence(
        proposal_type=proposal_type,
        target_files=target_files,
        repo_scope=repo_scope,
        system_scope=system_scope,
    )
    targets = target_files if target_files else target_paths
    reason = _write_proposal_reason(
        proposal_type=proposal_type,
        approval_scope=approval_scope,
        target_files=target_files,
        repo_scope=repo_scope,
        system_scope=system_scope,
        sudo_required=sudo_required,
        intent_type=intent_type,
    )
    return {
        "active": True,
        "write_proposal_state": "scoped-proposal",
        "write_proposal_type": proposal_type,
        "write_proposal_scope": scope,
        "write_proposal_targets": targets[:_MAX_TARGET_FILES],
        "write_proposal_target_paths": target_paths[:_MAX_TARGET_FILES],
        "write_proposal_reason": reason,
        "explicit_approval_required": True,
        "approval_scope": approval_scope or "repo-read",
        "criticality": criticality,
        "confidence": confidence,
        "proposal_only": True,
        "not_executed": True,
        "execution_state": "not-executed",
        "mutation_near": True,
        "repo_scope": repo_scope,
        "system_scope": system_scope,
        "sudo_required": sudo_required,
        "target_identity": False,
        "target_memory": False,
        "boundary": (
            "Write proposal light is approval-scoped runtime truth only. It stays proposal-only, "
            "approval-gated, and not-executed. It is not identity, not MEMORY.md, and not action by itself."
        ),
        "source_contributors": [
            "bounded-mutation-intent-runtime",
            "self-system-code-awareness",
        ],
    }


def _derive_write_proposal_confidence(
    *,
    proposal_type: str,
    target_files: list[str],
    repo_scope: str,
    system_scope: str,
) -> str:
    if proposal_type in {"propose-file-modification", "propose-file-deletion"} and target_files:
        return "high"
    if proposal_type == "propose-git-mutation" and repo_scope:
        return "high"
    if proposal_type == "propose-system-mutation" and system_scope:
        return "medium"
    return "medium"


def _write_proposal_reason(
    *,
    proposal_type: str,
    approval_scope: str,
    target_files: list[str],
    repo_scope: str,
    system_scope: str,
    sudo_required: bool,
    intent_type: str,
) -> str:
    if proposal_type == "propose-file-modification":
        targets = ", ".join(target_files[:3]) or "bounded repo files"
        return (
            "Runtime sees mutation-near file changes and can carry a bounded file-modification proposal; "
            f"targets={targets}; approval_scope={approval_scope}."
        )
    if proposal_type == "propose-file-deletion":
        targets = ", ".join(target_files[:3]) or "bounded repo files"
        return (
            "Runtime sees deletion-near scope and can carry a bounded file-deletion proposal; "
            f"targets={targets}; approval_scope={approval_scope}."
        )
    if proposal_type == "propose-git-mutation":
        return (
            "Runtime sees repo mutation-near scope and can carry a bounded git proposal; "
            f"repo_scope={repo_scope or 'none'}; approval_scope={approval_scope}."
        )
    if proposal_type == "propose-system-mutation":
        return (
            "Runtime sees system mutation-near scope and can carry a bounded system proposal; "
            f"system_scope={system_scope or intent_type}; sudo_required={sudo_required}; approval_scope={approval_scope}."
        )
    return "No bounded approval-scoped write proposal is active."


def _derive_classification(
    *,
    intent_state: str,
    intent_type: str,
    approval_scope: str,
    awareness_surface: dict[str, object],
    repo_observation: dict[str, object],
) -> str:
    if intent_state == "idle" or intent_type == "idle":
        return "none"
    if approval_scope == "repo-update-check" or intent_type == "inspect-upstream-divergence":
        return "git-mutate"
    if _derive_deleted_paths(repo_observation):
        return "delete-file"
    if _derive_modified_paths(repo_observation) or _derive_untracked_paths(repo_observation):
        return "modify-file"
    local_change_state = str(awareness_surface.get("local_change_state") or "").strip().lower()
    if local_change_state in {"modified", "mixed", "dirty", "untracked"}:
        return "modify-file"
    normalized_scope = approval_scope.strip().lower()
    normalized_type = intent_type.strip().lower()
    if any(token in normalized_scope for token in {"system", "package", "sudo"}):
        return "system-mutate"
    if any(token in normalized_type for token in {"system", "package", "install", "sudo"}):
        return "system-mutate"
    if intent_type in {
        "inspect-working-tree",
        "inspect-local-changes",
        "inspect-concern",
        "request-bounded-diagnostic",
    }:
        return "read-only"
    return "read-only"


def _derive_targets(repo_observation: dict[str, object]) -> tuple[list[str], list[str]]:
    target_files = [
        *_derive_deleted_paths(repo_observation),
        *_derive_modified_paths(repo_observation),
        *_derive_untracked_paths(repo_observation),
    ][:_MAX_TARGET_FILES]
    target_paths = _unique(
        [
            str(PurePosixPath(path).parent)
            for path in target_files
            if str(path).strip()
        ]
    )
    target_paths = [path if path not in {"", "."} else "workspace" for path in target_paths]
    return target_files, target_paths[:_MAX_TARGET_FILES]


def _derive_repo_mutation_scope(
    *,
    classification: str,
    approval_scope: str,
    repo_observation: dict[str, object],
) -> str:
    if classification != "git-mutate":
        return ""
    branch_name = str(repo_observation.get("branch_name") or "repo")
    upstream_ref = str(repo_observation.get("upstream_ref") or "upstream")
    if approval_scope == "repo-update-check":
        return f"upstream-sync:{branch_name}->{upstream_ref}"
    return f"repo-mutate:{branch_name}"


def _derive_system_mutation_scope(
    *,
    classification: str,
    approval_scope: str,
    intent_type: str,
) -> str:
    if classification != "system-mutate":
        return ""
    if approval_scope.strip():
        return approval_scope
    return intent_type


def _derive_sudo_required(
    *,
    classification: str,
    approval_scope: str,
    intent_type: str,
) -> bool:
    if classification != "system-mutate":
        return False
    normalized = f"{approval_scope} {intent_type}".lower()
    return any(token in normalized for token in {"sudo", "apt", "dnf", "yum", "brew", "system"})


def _derive_deleted_paths(repo_observation: dict[str, object]) -> list[str]:
    return _bounded_path_list(repo_observation.get("deleted_paths") or [])


def _derive_modified_paths(repo_observation: dict[str, object]) -> list[str]:
    return _bounded_path_list(repo_observation.get("modified_paths") or [])


def _derive_untracked_paths(repo_observation: dict[str, object]) -> list[str]:
    return _bounded_path_list(repo_observation.get("untracked_paths") or [])


def _bounded_path_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:_MAX_TARGET_FILES]


def _approval_required_mutation_capability_summary() -> dict[str, object]:
    capabilities = load_workspace_capabilities()
    classes: list[str] = []
    for item in capabilities.get("runtime_capabilities") or []:
        if str(item.get("runtime_status") or "") != "approval-required":
            continue
        classification = classify_workspace_execution_mode(
            str(item.get("execution_mode") or "declared-only")
        )
        if bool(classification.get("mutation_near")):
            classes.append(str(classification.get("classification") or "unknown"))
    classes = _unique(classes)
    return {
        "approval_required_mutation_capability_count": len(classes),
        "approval_required_mutation_classes": classes,
    }


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
