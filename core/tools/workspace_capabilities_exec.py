"""Exec-kommando-klassifikation for workspace-capabilities.

Udskilt fra workspace_capabilities.py (Boy Scout-reglen) som den sammenhængende
enhed, der afgør om en EXEC_COMMAND er bounded/tilladt, kræver approval-proposal
eller er hårdt blokeret — inkl. git-, cd- og shell-komponerede kommandoer.

Ren klassifikations-logik: ingen udførelse, ingen persistering, ingen side-
effekter ud over path-eksistens-tjek. Afhænger kun af delte konstanter.

Alle funktioner re-eksporteres fra core.tools.workspace_capabilities for
bagudkompatibilitet.
"""
from __future__ import annotations

import re
import shlex
from pathlib import Path

from core.runtime.config import PROJECT_ROOT

from core.tools.workspace_capabilities_const import (
    GIT_BLOCKED_SUBCOMMANDS,
    GIT_MUTATING_SUBCOMMANDS,
    GIT_READ_EXEC_ALLOWLIST,
    HARD_BLOCKED_EXEC_TOKENS,
    MUTATING_EXEC_PROPOSAL_TOKENS,
    NON_DESTRUCTIVE_EXEC_ALLOWLIST,
    NON_DESTRUCTIVE_EXEC_REDIRECTION_PATTERNS,
    NON_DESTRUCTIVE_EXEC_SEGMENT_SEPARATORS,
)


def _classify_exec_command(command_text: str) -> dict[str, object]:
    normalized = str(command_text or "").strip()
    if not normalized:
        return {
            "allowed": False,
            "status": "blocked-missing-command",
            "detail": "Non-destructive exec requires a non-empty command.",
        }
    if any(pattern in normalized for pattern in NON_DESTRUCTIVE_EXEC_REDIRECTION_PATTERNS):
        return {
            "allowed": False,
            "status": "blocked-shell-redirection",
            "detail": "Shell redirection is not allowed in non-destructive exec.",
        }
    if "$(" in normalized or "`" in normalized:
        return {
            "allowed": False,
            "status": "blocked-shell-substitution",
            "detail": "Command substitution is not allowed in non-destructive exec.",
        }
    if any(separator in normalized for separator in NON_DESTRUCTIVE_EXEC_SEGMENT_SEPARATORS):
        return _classify_shell_composed_exec_command(normalized)
    try:
        argv = shlex.split(normalized, posix=True)
    except ValueError:
        return {
            "allowed": False,
            "status": "blocked-invalid-command",
            "detail": "Command could not be parsed safely.",
        }
    if not argv:
        return {
            "allowed": False,
            "status": "blocked-missing-command",
            "detail": "Non-destructive exec requires a non-empty command.",
        }
    normalized_argv, normalization_sources = _normalize_exec_argv(argv)
    command_name = normalized_argv[0]
    if "/" in command_name:
        return {
            "allowed": False,
            "status": "blocked-command-path",
            "detail": "Explicit binary paths are not allowed in non-destructive exec.",
        }
    lowered = [part.lower() for part in argv]
    if any(token in HARD_BLOCKED_EXEC_TOKENS for token in lowered):
        blocked = next(token for token in lowered if token in HARD_BLOCKED_EXEC_TOKENS)
        return {
            "allowed": False,
            "status": "blocked-destructive-command",
            "detail": f"Destructive or arbitrary-exec token is not allowed in this pass: {blocked}",
        }
    if command_name == "cd":
        return _classify_cd_exec_command(
            normalized_argv,
            path_normalization_applied=bool(normalization_sources),
            normalization_source=(
                "+".join(normalization_sources) if normalization_sources else "none"
            ),
        )
    if command_name == "git":
        return _classify_git_exec_command(
            normalized_argv,
            path_normalization_applied=bool(normalization_sources),
            normalization_source=(
                "+".join(normalization_sources) if normalization_sources else "none"
            ),
        )
    proposal_metadata = _mutating_exec_proposal_metadata(argv)
    if proposal_metadata is not None:
        return {
            "allowed": False,
            "proposal_required": True,
            **proposal_metadata,
        }
    if command_name not in NON_DESTRUCTIVE_EXEC_ALLOWLIST:
        return {
            "allowed": False,
            "status": "blocked-command-not-allowlisted",
            "detail": f"Command is not in the bounded non-destructive allowlist: {command_name}",
        }
    return {
        "allowed": True,
        "argv": normalized_argv,
        "normalized_command_text": shlex.join(normalized_argv),
        "path_normalization_applied": bool(normalization_sources),
        "normalization_source": "+".join(normalization_sources) if normalization_sources else "none",
    }


def _classify_shell_composed_exec_command(command_text: str) -> dict[str, object]:
    segments = _split_shell_exec_segments(command_text)
    if not segments:
        return {
            "allowed": False,
            "status": "blocked-invalid-command",
            "detail": "Command could not be segmented safely.",
        }

    execution_scope = "filesystem"
    repo_scoped = False
    normalized_segments: list[str] = []
    normalization_sources: list[str] = []

    for segment in segments:
        verdict = _classify_exec_command_no_shell(segment)
        if verdict.get("proposal_required"):
            return {
                "allowed": False,
                "proposal_required": True,
                **{
                    key: value
                    for key, value in verdict.items()
                    if key != "allowed"
                },
            }
        if not verdict.get("allowed"):
            return verdict
        normalized_segments.append(
            str(verdict.get("normalized_command_text") or segment).strip()
        )
        if verdict.get("repo_scoped"):
            repo_scoped = True
        if str(verdict.get("execution_scope") or "") == "git-read":
            execution_scope = "git-read"
        for source in str(verdict.get("normalization_source") or "none").split("+"):
            normalized_source = source.strip()
            if (
                normalized_source
                and normalized_source != "none"
                and normalized_source not in normalization_sources
            ):
                normalization_sources.append(normalized_source)

    return {
        "allowed": True,
        "argv": ["/bin/bash", "-lc", command_text],
        "shell_mode": True,
        "normalized_command_text": " ".join(normalized_segments).strip(),
        "path_normalization_applied": bool(normalization_sources),
        "normalization_source": (
            "+".join(normalization_sources) if normalization_sources else "none"
        ),
        "execution_scope": execution_scope,
        "execution_classification": (
            "git-read-allowed"
            if execution_scope == "git-read"
            else "non-destructive-read-allowed"
        ),
        "repo_scoped": repo_scoped,
        "shell_segments": normalized_segments,
    }


def _classify_exec_command_no_shell(command_text: str) -> dict[str, object]:
    normalized = str(command_text or "").strip()
    if not normalized:
        return {
            "allowed": False,
            "status": "blocked-missing-command",
            "detail": "Non-destructive exec requires a non-empty command.",
        }
    try:
        argv = shlex.split(normalized, posix=True)
    except ValueError:
        return {
            "allowed": False,
            "status": "blocked-invalid-command",
            "detail": "Command could not be parsed safely.",
        }
    if not argv:
        return {
            "allowed": False,
            "status": "blocked-missing-command",
            "detail": "Non-destructive exec requires a non-empty command.",
        }
    normalized_argv, normalization_sources = _normalize_exec_argv(argv)
    command_name = normalized_argv[0]
    if "/" in command_name:
        return {
            "allowed": False,
            "status": "blocked-command-path",
            "detail": "Explicit binary paths are not allowed in non-destructive exec.",
        }
    lowered = [part.lower() for part in argv]
    if any(token in HARD_BLOCKED_EXEC_TOKENS for token in lowered):
        blocked = next(token for token in lowered if token in HARD_BLOCKED_EXEC_TOKENS)
        return {
            "allowed": False,
            "status": "blocked-destructive-command",
            "detail": f"Destructive or arbitrary-exec token is not allowed in this pass: {blocked}",
        }
    if command_name == "cd":
        return _classify_cd_exec_command(
            normalized_argv,
            path_normalization_applied=bool(normalization_sources),
            normalization_source=(
                "+".join(normalization_sources) if normalization_sources else "none"
            ),
        )
    if command_name == "git":
        return _classify_git_exec_command(
            normalized_argv,
            path_normalization_applied=bool(normalization_sources),
            normalization_source=(
                "+".join(normalization_sources) if normalization_sources else "none"
            ),
        )
    proposal_metadata = _mutating_exec_proposal_metadata(argv)
    if proposal_metadata is not None:
        return {
            "allowed": False,
            "proposal_required": True,
            **proposal_metadata,
        }
    if command_name not in NON_DESTRUCTIVE_EXEC_ALLOWLIST:
        return {
            "allowed": False,
            "status": "blocked-command-not-allowlisted",
            "detail": f"Command is not in the bounded non-destructive allowlist: {command_name}",
        }
    return {
        "allowed": True,
        "argv": normalized_argv,
        "normalized_command_text": shlex.join(normalized_argv),
        "path_normalization_applied": bool(normalization_sources),
        "normalization_source": (
            "+".join(normalization_sources) if normalization_sources else "none"
        ),
    }


def _split_shell_exec_segments(command_text: str) -> list[str]:
    parts = re.split(r"\s*(?:\&\&|\|\||\||;)\s*", str(command_text or "").strip())
    return [part.strip() for part in parts if part.strip()]


def _normalize_exec_argv(argv: list[str]) -> tuple[list[str], list[str]]:
    if not argv:
        return [], []

    normalized = [str(argv[0])]
    normalization_sources: list[str] = []
    home = str(Path.home())

    for arg in argv[1:]:
        updated = str(arg)
        sources_for_arg: list[str] = []

        if "~" in updated:
            expanded = str(Path(updated).expanduser())
            if expanded != updated:
                updated = expanded
                sources_for_arg.append("tilde")

        if "$HOME" in updated:
            replaced = updated.replace("$HOME", home)
            if replaced != updated:
                updated = replaced
                sources_for_arg.append("home-env")

        normalized.append(updated)
        for source in sources_for_arg:
            if source not in normalization_sources:
                normalization_sources.append(source)

    return normalized, normalization_sources


def _classify_git_exec_command(
    argv: list[str],
    *,
    path_normalization_applied: bool = False,
    normalization_source: str = "none",
) -> dict[str, object]:
    subcommand_index, execution_cwd, option_error = _resolve_git_exec_context(argv)
    if option_error:
        return option_error
    if len(argv) <= subcommand_index:
        return {
            "allowed": False,
            "status": "blocked-git-command",
            "detail": "Git exec requires one explicit bounded git subcommand.",
        }

    subcommand = str(argv[subcommand_index]).strip().lower()
    shape = tuple(str(part) for part in argv[subcommand_index:])

    if shape in GIT_READ_EXEC_ALLOWLIST:
        return {
            "allowed": True,
            "argv": argv,
            "normalized_command_text": shlex.join(argv),
            "path_normalization_applied": path_normalization_applied,
            "normalization_source": normalization_source,
            "execution_scope": "git-read",
            "execution_classification": "git-read-allowed",
            "repo_scoped": True,
            "execution_cwd": execution_cwd,
        }

    if subcommand == "log":
        if _is_allowed_bounded_git_log_args(list(argv[subcommand_index + 1 :])):
            return {
                "allowed": True,
                "argv": argv,
                "normalized_command_text": shlex.join(argv),
                "path_normalization_applied": path_normalization_applied,
                "normalization_source": normalization_source,
                "execution_scope": "git-read",
                "execution_classification": "git-read-allowed",
                "repo_scoped": True,
                "execution_cwd": execution_cwd,
            }
        return {
            "allowed": False,
            "status": "blocked-git-command-shape",
            "detail": "Bounded git log allows only: git log --oneline -n N or git log -N --oneline",
        }

    if subcommand in GIT_MUTATING_SUBCOMMANDS:
        git_mutation_class = _classify_git_mutation_subcommand(subcommand)
        return {
            "allowed": False,
            "proposal_required": True,
            "matched_token": "git",
            "effective_token": "git",
            "requires_sudo": False,
            "proposal_scope": "git",
            "proposal_execution_mode": "mutating-exec-proposal",
            "criticality": "high",
            "git_mutation_class": git_mutation_class,
            "repo_stewardship_domain": "git",
            "argv": list(argv),
            "detail": (
                f"Git mutation subcommand {subcommand} was classified as {git_mutation_class} and captured as an approval-gated repo stewardship proposal only."
            ),
        }

    if subcommand == "clean":
        return {
            "allowed": False,
            "status": "blocked-git-destructive",
            "detail": "Git clean is destructive and stays blocked in this pass.",
        }

    if subcommand in GIT_BLOCKED_SUBCOMMANDS:
        return {
            "allowed": False,
            "status": "blocked-git-command",
            "detail": (
                f"Git subcommand {subcommand} is outside the bounded read/mutate model for this pass."
            ),
        }

    return {
        "allowed": False,
        "status": "blocked-git-command",
        "detail": (
            f"Git subcommand {subcommand or 'unknown'} is not in the bounded git read allowlist and is not opened for execution in this pass."
        ),
    }


def _resolve_git_exec_context(
    argv: list[str],
) -> tuple[int, Path, dict[str, object] | None]:
    execution_cwd = PROJECT_ROOT
    index = 1
    while index < len(argv):
        token = str(argv[index]).strip()
        if token != "-C":
            break
        if index + 1 >= len(argv):
            return index, execution_cwd, {
                "allowed": False,
                "status": "blocked-git-command",
                "detail": "Git -C requires one explicit directory path.",
            }
        candidate = Path(str(argv[index + 1])).expanduser()
        if not candidate.exists() or not candidate.is_dir():
            return index, execution_cwd, {
                "allowed": False,
                "status": "blocked-git-command",
                "detail": f"Git -C target is not an existing directory: {candidate}",
            }
        execution_cwd = candidate
        index += 2
    return index, execution_cwd, None


def _is_allowed_bounded_git_log_args(log_args: list[str]) -> bool:
    if len(log_args) == 3 and log_args[0] == "--oneline" and log_args[1] == "-n":
        return bool(re.fullmatch(r"[1-9][0-9]?", log_args[2]))
    if len(log_args) == 2 and re.fullmatch(r"-[1-9][0-9]?", log_args[0]) and log_args[1] == "--oneline":
        return True
    return False


def _classify_cd_exec_command(
    argv: list[str],
    *,
    path_normalization_applied: bool = False,
    normalization_source: str = "none",
) -> dict[str, object]:
    if len(argv) != 2:
        return {
            "allowed": False,
            "status": "blocked-command-shape",
            "detail": "Bounded cd allows only one explicit target directory.",
        }
    candidate = Path(str(argv[1])).expanduser()
    if not candidate.exists() or not candidate.is_dir():
        return {
            "allowed": False,
            "status": "blocked-invalid-target-path",
            "detail": f"cd target is not an existing directory: {candidate}",
        }
    return {
        "allowed": True,
        "argv": argv,
        "normalized_command_text": shlex.join(argv),
        "path_normalization_applied": path_normalization_applied,
        "normalization_source": normalization_source,
        "execution_scope": "filesystem",
        "execution_classification": "non-destructive-navigation-allowed",
        "repo_scoped": str(candidate.resolve()).startswith(str(PROJECT_ROOT.resolve())),
    }


def _classify_git_mutation_subcommand(subcommand: str) -> str:
    normalized = str(subcommand or "").strip().lower()
    if normalized == "add":
        return "git-stage"
    if normalized == "commit":
        return "git-commit"
    if normalized in {"push", "pull", "fetch", "merge"}:
        return "git-sync"
    if normalized in {"checkout", "switch", "restore"}:
        return "git-branch-switch"
    if normalized in {"reset", "rebase", "cherry-pick", "revert"}:
        return "git-history-rewrite"
    if normalized == "stash":
        return "git-stash"
    return "git-other-mutate"


def _mutating_exec_proposal_metadata(argv: list[str]) -> dict[str, object] | None:
    lowered = [part.lower() for part in argv]
    matched_token = next(
        (token for token in lowered if token in MUTATING_EXEC_PROPOSAL_TOKENS),
        None,
    )
    if matched_token is None:
        return None

    requires_sudo = "sudo" in lowered
    scope = "filesystem"
    criticality = "medium"
    proposal_execution_mode = "mutating-exec-proposal"
    effective_token = matched_token

    if matched_token == "sudo":
        effective_token = lowered[1] if len(lowered) > 1 else "sudo"
        scope = "system"
        criticality = "high"
        proposal_execution_mode = "sudo-exec-proposal"
    elif matched_token in {"git"}:
        scope = "git"
        criticality = "high"
    elif matched_token in {"npm", "pip", "pip3", "apt", "apt-get", "dnf", "yum", "brew"}:
        scope = "package"
        criticality = "high"
    elif matched_token in {"docker", "kubectl"}:
        scope = "system"
        criticality = "high"

    if requires_sudo and proposal_execution_mode != "sudo-exec-proposal":
        proposal_execution_mode = "sudo-exec-proposal"
        criticality = "high"

    return {
        "matched_token": matched_token,
        "effective_token": effective_token,
        "requires_sudo": requires_sudo,
        "proposal_scope": scope,
        "proposal_execution_mode": proposal_execution_mode,
        "criticality": criticality,
        "argv": list(argv),
        "detail": (
            "sudo-near command was captured as an approval-gated proposal only and was not executed."
            if requires_sudo
            else f"Mutating command token {matched_token} was captured as an approval-gated proposal only and was not executed."
        ),
    }
