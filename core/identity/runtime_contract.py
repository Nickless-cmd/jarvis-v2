from __future__ import annotations

from pathlib import Path

from core.identity.runtime_candidates import (
    build_runtime_candidate_workflows,
    build_runtime_candidate_write_history,
    total_pending_runtime_candidates,
)
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.tools.workspace_capabilities import load_workspace_capabilities

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CANONICAL_WORKSPACE_FILES = (
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "TOOLS.md",
    "SKILLS.md",
    "MEMORY.md",
    "HEARTBEAT.md",
)

DERIVED_RUNTIME_FILES = (
    "runtime/RUNTIME_CAPABILITIES.md",
    "runtime/RUNTIME_FEEDBACK.md",
    "runtime/HEARTBEAT_STATE.json",
)

REFERENCE_ONLY_FILES = (
    "docs/runtime_contract/reference_old/AGENTS.md",
    "docs/runtime_contract/reference_old/BOOTSTRAP.md",
    "docs/runtime_contract/reference_old/HEARTBEAT_COMPANION.md",
    "docs/runtime_contract/reference_old/RUNTIME_CAPABILITIES.md",
    "docs/runtime_contract/reference_old/RUNTIME_FEEDBACK.md",
    "docs/runtime_contract/reference_old/SYSTEM_PROMPT_STUDY.md",
    "docs/runtime_contract/reference_old/boredom_templates.json",
)

VISIBLE_CHAT_ORDER = (
    "runtime capability and safety truth",
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "MEMORY.md (retrieved slice only)",
    "TOOLS.md / SKILLS.md (relevant slice only)",
    "bounded session continuity",
    "bounded derived runtime support signals",
    "recent transcript slice",
    "current user message",
)

HEARTBEAT_ORDER = (
    "runtime heartbeat policy, schedule, and budget truth",
    "HEARTBEAT.md",
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "MEMORY.md (relevant slice only)",
    "due schedules and open-loop summary",
    "compact capability truth",
    "optional compact continuity summary",
)

FUTURE_AGENT_ORDER = (
    "runtime role, scope, and capability truth",
    "SOUL.md",
    "IDENTITY.md",
    "USER.md (task-relevant only)",
    "delegated task brief",
    "MEMORY.md (relevant slice only)",
    "TOOLS.md / SKILLS.md (relevant slice only)",
    "bounded delegated continuity context",
)


def build_runtime_contract_state(name: str = "default") -> dict[str, object]:
    workspace_dir = ensure_default_workspace(name=name)
    canonical_files = [
        _file_state(
            workspace_dir / filename,
            name=filename,
            role="canonical",
            loaded_by_default=filename in {"SOUL.md", "IDENTITY.md", "USER.md"},
            activation=_canonical_activation(filename),
            writer=_canonical_writer(filename),
        )
        for filename in CANONICAL_WORKSPACE_FILES
    ]
    derived_files = [
        _file_state(
            workspace_dir / rel_path,
            name=rel_path,
            role="derived",
            loaded_by_default=False,
            activation="inspect-only",
            writer="runtime-only",
        )
        for rel_path in DERIVED_RUNTIME_FILES
    ]
    reference_files = [
        _file_state(
            PROJECT_ROOT / rel_path,
            name=rel_path,
            role="reference-only",
            loaded_by_default=False,
            activation="never-default",
            writer="reference-only",
        )
        for rel_path in REFERENCE_ONLY_FILES
    ]

    bootstrap = _bootstrap_status(workspace_dir)
    pending_writes = build_runtime_candidate_workflows()
    write_history = build_runtime_candidate_write_history()
    capability_truth = load_workspace_capabilities(name=name)
    capability_contract = _capability_contract_state(capability_truth)
    prompt_modes = {
        "visible_chat": {
            "id": "visible_chat",
            "label": "Visible Chat",
            "status": "active",
            "implementation_state": "loader-implemented",
            "load_order": list(VISIBLE_CHAT_ORDER),
            "always_loaded": ["SOUL.md", "IDENTITY.md", "USER.md"],
            "conditional_files": ["MEMORY.md", "TOOLS.md", "SKILLS.md"],
            "derived_inputs": [
                "bounded session continuity",
                "bounded runtime support signals",
                "policy-filtered capability truth",
            ],
            "excluded_by_default": [
                "BOOTSTRAP.md",
                "HEARTBEAT.md",
                "runtime/RUNTIME_FEEDBACK.md",
                "raw private state dumps",
            ],
            "summary": "Identity-led visible prompt with bounded continuity and runtime truth.",
            "source": "/mc/runtime-contract",
        },
        "heartbeat": {
            "id": "heartbeat",
            "label": "Heartbeat",
            "status": "active",
            "implementation_state": "runtime-implemented",
            "load_order": list(HEARTBEAT_ORDER),
            "always_loaded": ["HEARTBEAT.md", "SOUL.md", "IDENTITY.md", "USER.md"],
            "conditional_files": ["MEMORY.md"],
            "derived_inputs": [
                "schedule truth",
                "budget truth",
                "due-loop summary",
                "capability truth",
            ],
            "excluded_by_default": [
                "BOOTSTRAP.md",
                "runtime/RUNTIME_FEEDBACK.md",
                "full transcript",
                "boredom_templates.json",
            ],
            "summary": "Bounded proactive contract with manual tick runtime, policy gating, and Mission Control visibility.",
            "source": "/mc/runtime-contract",
        },
        "future_agent_task": {
            "id": "future_agent_task",
            "label": "Future Agent Task",
            "status": "declared",
            "implementation_state": "loader-implemented",
            "load_order": list(FUTURE_AGENT_ORDER),
            "always_loaded": ["SOUL.md", "IDENTITY.md"],
            "conditional_files": ["USER.md", "MEMORY.md", "TOOLS.md", "SKILLS.md"],
            "derived_inputs": [
                "delegated scope truth",
                "budget truth",
                "delegated continuity",
            ],
            "excluded_by_default": [
                "BOOTSTRAP.md",
                "HEARTBEAT.md",
                "runtime/RUNTIME_FEEDBACK.md",
                "raw private state dumps",
            ],
            "summary": "Shared-identity agent contract declared with stricter runtime scope.",
            "source": "/mc/runtime-contract",
        },
    }

    canonical_present = sum(1 for item in canonical_files if item["present"])
    derived_present = sum(1 for item in derived_files if item["present"])
    active_modes = sum(1 for item in prompt_modes.values() if item["status"] == "active")

    pending_write_count = total_pending_runtime_candidates(pending_writes)

    return {
        "workspace": str(workspace_dir),
        "contract_version": "jarvis-v2-runtime-contract-v1",
        "summary": {
            "bootstrap_status": bootstrap["status"],
            "canonical_present": canonical_present,
            "canonical_expected": len(canonical_files),
            "derived_present": derived_present,
            "derived_expected": len(derived_files),
            "prompt_modes_declared": len(prompt_modes),
            "prompt_modes_active": active_modes,
            "pending_write_count": pending_write_count,
            "runtime_capabilities_available": capability_contract["available_now_count"],
            "runtime_capabilities_gated": capability_contract["approval_required_count"],
        },
        "bootstrap": bootstrap,
        "capability_contract": capability_contract,
        "files": {
            "canonical": canonical_files,
            "derived": derived_files,
            "reference_only": reference_files,
        },
        "prompt_modes": prompt_modes,
        "pending_writes": pending_writes,
        "write_history": write_history,
        "roles": {
            "canonical": "Workspace truth intended to shape behavior directly.",
            "derived": "Runtime-generated artifacts that are inspectable but not canonical identity truth.",
            "reference-only": "Reference material retained for study and contract design, not runtime prompt input.",
        },
    }


def _bootstrap_status(workspace_dir: Path) -> dict[str, object]:
    bootstrap_path = workspace_dir / "BOOTSTRAP.md"
    onboarding_ready = all(
        (workspace_dir / filename).exists()
        for filename in ("SOUL.md", "IDENTITY.md", "USER.md")
    )
    if bootstrap_path.exists():
        status = "ready-to-retire" if onboarding_ready else "active"
        detail = (
            "Bootstrap file is still present. Archive or mark inactive once onboarding is complete."
            if onboarding_ready
            else "Bootstrap remains active until core onboarding files are established."
        )
    else:
        status = "retired" if onboarding_ready else "active"
        detail = (
            "Bootstrap is not active in this workspace."
            if onboarding_ready
            else "Bootstrap is effectively active because core onboarding files are incomplete."
        )

    return {
        "status": status,
        "file": "BOOTSTRAP.md",
        "path": str(bootstrap_path),
        "present": bootstrap_path.exists(),
        "retirement_trigger": "SOUL.md + IDENTITY.md + USER.md established and onboarding marked complete",
        "summary": detail,
        "source": "/mc/runtime-contract",
    }


def _file_state(
    path: Path,
    *,
    name: str,
    role: str,
    loaded_by_default: bool,
    activation: str,
    writer: str,
) -> dict[str, object]:
    present = path.exists()
    return {
        "name": name,
        "path": str(path),
        "role": role,
        "present": present,
        "loaded_by_default": loaded_by_default,
        "activation": activation,
        "writer": writer,
        "summary": _file_summary(name, role, present, loaded_by_default),
        "source": "/mc/runtime-contract",
    }


def _canonical_activation(filename: str) -> str:
    if filename in {"SOUL.md", "IDENTITY.md", "USER.md"}:
        return "always-active"
    if filename == "HEARTBEAT.md":
        return "heartbeat-only"
    return "conditional"


def _canonical_writer(filename: str) -> str:
    if filename in {"USER.md", "MEMORY.md"}:
        return "user-or-governed-runtime"
    return "user-approved"


def _file_summary(name: str, role: str, present: bool, loaded_by_default: bool) -> str:
    parts = [role]
    parts.append("present" if present else "missing")
    if loaded_by_default:
        parts.append("default-load")
    if name in {"TOOLS.md", "SKILLS.md"}:
        parts.append("guidance-only")
    return " · ".join(parts)


def _capability_contract_state(capability_truth: dict[str, object]) -> dict[str, object]:
    authority = capability_truth.get("authority") or {}
    runtime_capabilities = list(capability_truth.get("runtime_capabilities") or [])
    available = [item for item in runtime_capabilities if item.get("available_now")]
    approval_required = [
        item for item in runtime_capabilities if item.get("runtime_status") == "approval-required"
    ]
    guidance_only = [
        item for item in runtime_capabilities if item.get("runtime_status") == "guidance-only"
    ]
    return {
        "authority_source": authority.get("authority_source") or "runtime.workspace_capabilities",
        "runtime_authoritative": bool(authority.get("runtime_authoritative", True)),
        "guidance_only_docs": bool(authority.get("guidance_only_docs", True)),
        "guidance_sources": list(authority.get("guidance_sources") or ["TOOLS.md", "SKILLS.md"]),
        "summary": authority.get("summary")
        or "Runtime capability truth is authoritative. TOOLS.md and SKILLS.md are workspace guidance only.",
        "described_count": int(authority.get("described_count") or len(runtime_capabilities)),
        "runtime_count": int(authority.get("runtime_count") or len(runtime_capabilities)),
        "available_now_count": int(authority.get("available_now_count") or len(available)),
        "approval_required_count": int(
            authority.get("approval_required_count") or len(approval_required)
        ),
        "guidance_only_count": int(authority.get("guidance_only_count") or len(guidance_only)),
        "unavailable_count": int(authority.get("unavailable_count") or 0),
        "currently_available": available[:8],
        "approval_gated": approval_required[:8],
        "guidance_descriptions": guidance_only[:8],
        "source": "/mc/runtime-contract",
    }
