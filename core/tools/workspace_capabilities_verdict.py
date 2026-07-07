"""Approval-verdicts + proposal/execution-content for mutating/sudo exec.

Udskilt fra workspace_capabilities.py (Boy Scout-reglen) som den sammenhængende
enhed, der — EFTER en exec-kommando er klassificeret som mutating/sudo og
godkendt — afgør om den faktisk må køre (bundet allowlist + shape + owner-bypass)
og bygger proposal-/execution-content-payloads.

Ingen udførelse her (det sker i hoved-modulet via _run_bounded_command); kun
verdict + payload-formning. Afhænger af delte konstanter (const),
result-helpers (results) og workspace-root-guard (workspace_capability_decl).

Alle funktioner re-eksporteres fra core.tools.workspace_capabilities for
bagudkompatibilitet.
"""
from __future__ import annotations

import re
from pathlib import Path

from core.tools.workspace_capabilities_const import (
    APPROVED_MUTATING_EXEC_ALLOWLIST,
    APPROVED_SUDO_EXEC_ALLOWLIST,
)
from core.tools.workspace_capabilities_results import (
    _content_fingerprint,
    _preview_text,
)
from core.tools.workspace_capability_decl import _is_within_workspace_root


def _approved_mutating_exec_verdict(
    classification: dict[str, object],
) -> dict[str, object]:
    matched_token = str(
        classification.get("effective_token")
        or classification.get("matched_token")
        or "unknown"
    )
    if bool(classification.get("requires_sudo", False)):
        return {
            "allowed": False,
            "status": "blocked-sudo-execution-disabled",
            "detail": "Sudo exec remains proposal-only and is not executable in this pass.",
        }
    scope = str(classification.get("proposal_scope") or "filesystem")
    if scope in {"git", "package", "system"}:
        return {
            "allowed": False,
            "status": "blocked-command-class",
            "detail": (
                f"Approved {scope} mutation remains proposal-only in this pass and is not executable."
            ),
        }
    if matched_token not in APPROVED_MUTATING_EXEC_ALLOWLIST:
        return {
            "allowed": False,
            "status": "blocked-command-class",
            "detail": (
                f"Approved mutating exec token {matched_token} is outside the bounded non-sudo execution allowlist for this pass."
            ),
        }
    argv = list(classification.get("argv") or [])
    if len(argv) != 3 or any(part.startswith("-") for part in argv[1:]):
        return {
            "allowed": False,
            "status": "blocked-command-shape",
            "detail": (
                "Approved bounded non-sudo mutating exec currently allows only simple three-part commands without flags."
            ),
        }
    return {
        "allowed": True,
    }


def _approved_sudo_exec_verdict(
    classification: dict[str, object],
    *,
    workspace_dir: Path,
) -> dict[str, object]:
    # Owner-bypass (Bjørn 2026-06-21): på ejerens EGEN container må effektiv-owner
    # (native owner ELLER !override+TOTP) køre VILKÅRLIG sudo — det er hans maskine,
    # og composer-permission (ask/full) + approval-flowet gater allerede selve
    # godkendelsen. Members forbliver i den bundne 4-dels-allowlist nedenfor.
    # Base-rolle røres ALDRIG → privatlivs-carve-out §6.5 intakt.
    try:
        from core.identity.workspace_context import effective_role as _eff_role_sudo
        if _eff_role_sudo() == "owner":
            _argv = [str(p) for p in (classification.get("argv") or [])]
            if len(_argv) >= 2 and _argv[0] == "sudo":
                return {
                    "allowed": True,
                    "argv": _argv,
                    "workspace_scoped": False,
                    "external_mutation_permitted": True,
                    "owner_bypass": True,
                }
    except Exception:
        pass
    if not bool(classification.get("requires_sudo", False)):
        return {
            "allowed": False,
            "status": "blocked-sudo-classification-mismatch",
            "detail": "Approved sudo exec requires a sudo-classified proposal.",
        }
    argv = list(classification.get("argv") or [])
    sudo_subcommand = str(classification.get("effective_token") or "").strip().lower()
    if sudo_subcommand not in APPROVED_SUDO_EXEC_ALLOWLIST:
        return {
            "allowed": False,
            "status": "blocked-sudo-command-class",
            "detail": (
                f"Approved sudo exec token {sudo_subcommand or 'unknown'} is outside the bounded sudo allowlist for this pass."
            ),
        }
    if len(argv) != 4 or argv[0] != "sudo":
        return {
            "allowed": False,
            "status": "blocked-command-shape",
            "detail": (
                "Approved bounded sudo exec currently allows only simple four-part sudo commands."
            ),
        }
    if argv[1] != sudo_subcommand:
        return {
            "allowed": False,
            "status": "blocked-sudo-command-shape",
            "detail": "Approved sudo exec must match the exact bounded subcommand shape.",
        }
    if any(part.startswith("-") for part in argv[2:]):
        return {
            "allowed": False,
            "status": "blocked-command-shape",
            "detail": "Approved bounded sudo exec does not allow flags in this pass.",
        }
    mode = argv[2]
    if sudo_subcommand == "chmod" and not re.fullmatch(r"[0-7]{3,4}", mode):
        return {
            "allowed": False,
            "status": "blocked-sudo-command-shape",
            "detail": "Approved bounded sudo chmod requires a simple octal mode.",
        }
    candidate = _resolve_target_path_for_sudo_exec(workspace_dir, argv[3])
    if candidate is None:
        return {
            "allowed": False,
            "status": "blocked-sudo-target-path",
            "detail": "Approved bounded sudo exec requires a valid target path within the active workspace root.",
        }
    if not candidate.exists():
        return {
            "allowed": False,
            "status": "blocked-sudo-target-missing",
            "detail": "Approved bounded sudo exec target does not exist within the active workspace root.",
        }
    return {
        "allowed": True,
        "argv": ["sudo", sudo_subcommand, mode, str(candidate)],
        "workspace_scoped": True,
        "external_mutation_permitted": False,
    }


def _mutating_exec_proposal_content(
    *,
    command_text: str,
    command_source: str,
    classification: dict[str, object],
) -> dict[str, object]:
    matched_token = str(classification.get("matched_token") or "unknown")
    requires_sudo = bool(classification.get("requires_sudo", False))
    scope = str(classification.get("proposal_scope") or "filesystem")
    criticality = str(classification.get("criticality") or "medium")
    proposal_type = (
        "sudo-exec-proposal" if requires_sudo else "mutating-exec-proposal"
    )
    git_mutation_class = str(classification.get("git_mutation_class") or "none")
    repo_stewardship_domain = str(
        classification.get("repo_stewardship_domain")
        or ("git" if scope == "git" else "none")
    )
    return {
        "state": "approval-required-proposal",
        "type": proposal_type,
        "command": command_text,
        "content": command_text,
        "summary": _preview_text(command_text, limit=160),
        "fingerprint": _content_fingerprint(command_text),
        "source": command_source or "invocation-argument",
        "target": matched_token,
        "reason": str(
            classification.get("detail")
            or "Mutating exec proposal was captured but not executed."
        ),
        "scope": scope,
        "explicit_approval_required": True,
        "approval_scope": "sudo-exec" if requires_sudo else "mutating-exec",
        "requires_sudo": requires_sudo,
        "criticality": criticality,
        "git_mutation_class": git_mutation_class,
        "repo_stewardship_domain": repo_stewardship_domain,
        "confidence": "high",
        "proposal_only": True,
        "not_executed": True,
        "workspace_scoped": False,
        "target_identity": False,
        "target_memory": False,
        "source_contributors": [
            "workspace-capability-runtime",
            "exec-command-classifier",
        ],
    }


def _mutating_exec_execution_content(
    *,
    command_text: str,
    command_source: str,
    classification: dict[str, object],
    exit_code: int | None,
    output_text: str,
) -> dict[str, object]:
    proposal = _mutating_exec_proposal_content(
        command_text=command_text,
        command_source=command_source,
        classification=classification,
    )
    execution_state = "mutating-exec-completed"
    reason = "Approved bounded non-sudo mutating exec completed."
    if exit_code is None:
        execution_state = "mutating-exec-blocked"
        reason = "Approved bounded non-sudo mutating exec timed out before completion."
    elif exit_code != 0:
        execution_state = "mutating-exec-failed"
        reason = "Approved bounded non-sudo mutating exec exited non-zero."
    return {
        **proposal,
        "state": "executed" if exit_code is not None else "blocked",
        "type": "mutating-exec",
        "reason": reason,
        "proposal_only": exit_code is None,
        "not_executed": exit_code is None,
        "execution_state": execution_state,
        "exit_code": exit_code,
        "text": output_text,
    }


def _sudo_exec_execution_content(
    *,
    command_text: str,
    command_source: str,
    classification: dict[str, object],
    exit_code: int | None,
    output_text: str,
) -> dict[str, object]:
    proposal = _mutating_exec_proposal_content(
        command_text=command_text,
        command_source=command_source,
        classification=classification,
    )
    execution_state = "sudo-exec-completed"
    reason = "Approved bounded sudo exec completed."
    if exit_code is None:
        execution_state = "sudo-exec-blocked"
        reason = "Approved bounded sudo exec timed out before completion."
    elif exit_code != 0:
        execution_state = "sudo-exec-failed"
        reason = "Approved bounded sudo exec exited non-zero."
    return {
        **proposal,
        "state": "executed" if exit_code is not None else "blocked",
        "type": "sudo-exec",
        "reason": reason,
        "proposal_only": exit_code is None,
        "not_executed": exit_code is None,
        "execution_state": execution_state,
        "workspace_scoped": True,
        "exit_code": exit_code,
        "text": output_text,
    }


def _resolve_target_path_for_sudo_exec(workspace_dir: Path, target: str) -> Path | None:
    normalized = str(target or "").strip()
    if not normalized:
        return None
    expanded = Path(normalized).expanduser()
    candidate = (
        expanded.resolve()
        if expanded.is_absolute()
        else (workspace_dir / expanded).resolve()
    )
    if not _is_within_workspace_root(workspace_dir, candidate):
        return None
    return candidate
