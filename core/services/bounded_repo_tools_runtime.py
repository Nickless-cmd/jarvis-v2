from __future__ import annotations

import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from core.services.runtime_surface_cache import get_cached_runtime_surface

_MAX_EXCERPT_LINES = 4
_MAX_STATUS_FILES = 6


def build_bounded_repo_tool_execution_surface(
    intent_surface: dict[str, object],
    *,
    awareness_surface: dict[str, object] | None = None,
) -> dict[str, object]:
    key = (
        "bounded_repo_tool_execution_surface",
        str(intent_surface.get("intent_state") or "idle"),
        str(intent_surface.get("intent_type") or "inspect-repo-status"),
        str(intent_surface.get("intent_target") or "workspace"),
        str(intent_surface.get("approval_scope") or "repo-read"),
        str(intent_surface.get("approval_state") or "none"),
        str(
            ((awareness_surface or {}).get("host_context") or {}).get("repo_root") or ""
        ),
    )
    return get_cached_runtime_surface(
        key,
        lambda: _build_bounded_repo_tool_execution_surface(
            intent_surface,
            awareness_surface=awareness_surface,
        ),
    )


def _build_bounded_repo_tool_execution_surface(
    intent_surface: dict[str, object],
    *,
    awareness_surface: dict[str, object] | None,
) -> dict[str, object]:
    intent_state = str(intent_surface.get("intent_state") or "idle")
    intent_type = str(intent_surface.get("intent_type") or "inspect-repo-status")
    intent_target = str(intent_surface.get("intent_target") or "workspace")
    approval_scope = str(intent_surface.get("approval_scope") or "repo-read")
    approval_state = str(intent_surface.get("approval_state") or "none")
    host_context = dict((awareness_surface or {}).get("host_context") or {})
    repo_root_value = str(host_context.get("repo_root") or "").strip()
    repo_root = Path(repo_root_value).resolve() if repo_root_value else None
    git_present = bool(host_context.get("git_present")) and shutil.which("git") is not None
    allowed = _allowed_operation(intent_type)

    base = {
        "execution_state": "not-executed",
        "execution_mode": "read-only",
        "execution_target": intent_target,
        "execution_summary": "No bounded repo inspection has been executed.",
        "execution_started_at": "",
        "execution_finished_at": "",
        "execution_confidence": str(intent_surface.get("confidence") or "low"),
        "execution_operation": intent_type,
        "execution_excerpt": [],
        "mutation_permitted": False,
        "source_contributors": ["tool-intent-runtime"],
    }

    if intent_state == "idle":
        base["execution_summary"] = "No active tool intent is present, so no read-only execution was attempted."
        return base

    if approval_state != "approved":
        base["execution_summary"] = (
            "Read-only execution remains blocked until the current tool intent is explicitly approved; "
            f"approval_state={approval_state}."
        )
        base["source_contributors"] = ["tool-intent-approval-runtime"]
        return base

    if allowed is None:
        base["execution_state"] = "blocked-unsupported"
        base["execution_summary"] = (
            f"Approved tool intent {intent_type} is not in the bounded read-only repo allowlist."
        )
        base["source_contributors"] = ["bounded-read-only-repo-tools"]
        return base

    if approval_scope not in allowed["scopes"]:
        base["execution_state"] = "blocked-scope-mismatch"
        base["execution_summary"] = (
            f"Approved tool intent scope {approval_scope} does not match the bounded read-only policy for {intent_type}."
        )
        base["source_contributors"] = ["bounded-read-only-repo-tools", "tool-intent-approval-runtime"]
        return base

    if repo_root is None or not repo_root.exists() or not git_present:
        base["execution_state"] = "blocked-unavailable"
        base["execution_summary"] = (
            "Repo-root or git runtime is unavailable, so bounded read-only repo inspection could not run."
        )
        base["source_contributors"] = ["bounded-read-only-repo-tools", "self-system-code-awareness"]
        return base

    started_at = datetime.now(UTC).isoformat()
    try:
        result = allowed["handler"](repo_root=repo_root, intent_target=intent_target)
    except Exception as exc:
        finished_at = datetime.now(UTC).isoformat()
        return {
            **base,
            "execution_state": "read-only-failed",
            "execution_summary": f"Bounded read-only repo inspection failed: {exc}",
            "execution_started_at": started_at,
            "execution_finished_at": finished_at,
            "execution_confidence": "low",
            "source_contributors": [
                "bounded-read-only-repo-tools",
                "git-read-only",
            ],
        }

    finished_at = datetime.now(UTC).isoformat()
    return {
        **base,
        **result,
        "execution_state": "read-only-completed",
        "execution_mode": "read-only",
        "execution_target": result.get("execution_target") or intent_target,
        "execution_started_at": started_at,
        "execution_finished_at": finished_at,
        "mutation_permitted": False,
        "source_contributors": _merge_unique(
            [
                "bounded-read-only-repo-tools",
                "git-read-only",
                "self-system-code-awareness",
            ],
            result.get("source_contributors") or [],
        ),
    }


def _allowed_operation(intent_type: str) -> dict[str, object] | None:
    operations: dict[str, dict[str, object]] = {
        "inspect-repo-status": {
            "scopes": {"repo-read"},
            "handler": _inspect_repo_status,
        },
        "inspect-working-tree": {
            "scopes": {"repo-read"},
            "handler": _inspect_working_tree,
        },
        "inspect-local-changes": {
            "scopes": {"repo-read"},
            "handler": _inspect_local_changes,
        },
        "inspect-upstream-divergence": {
            "scopes": {"repo-update-check"},
            "handler": _inspect_upstream_divergence,
        },
        "inspect-concern": {
            "scopes": {"bounded-diagnostic", "repo-read"},
            "handler": _request_bounded_diagnostic,
        },
        "request-bounded-diagnostic": {
            "scopes": {"bounded-diagnostic", "repo-read"},
            "handler": _request_bounded_diagnostic,
        },
    }
    return operations.get(intent_type)


def _inspect_repo_status(*, repo_root: Path, intent_target: str) -> dict[str, object]:
    observation = _git_status_observation(repo_root)
    branch = observation["branch_name"]
    upstream = observation["upstream_ref"] or "no-upstream"
    summary = (
        f"Repo status on {branch}: repo={observation['repo_status']}, changes={observation['local_change_state']}, "
        f"upstream={observation['upstream_awareness']} against {upstream}."
    )
    excerpt = [
        f"branch={branch}",
        f"repo_status={observation['repo_status']}",
        f"local_change_state={observation['local_change_state']}",
        f"upstream_awareness={observation['upstream_awareness']}",
    ]
    return {
        "execution_target": intent_target or branch,
        "execution_summary": summary,
        "execution_confidence": "high" if observation["ok"] else "low",
        "execution_excerpt": excerpt[:_MAX_EXCERPT_LINES],
        "source_contributors": ["git-status"],
    }


def _inspect_working_tree(*, repo_root: Path, intent_target: str) -> dict[str, object]:
    observation = _git_status_observation(repo_root)
    diff_result = _run_git_command(repo_root, ["diff", "--stat", "--compact-summary"])
    excerpt = []
    if diff_result["ok"] and diff_result["stdout"]:
        excerpt.extend(_trim_lines(str(diff_result["stdout"])))
    if not excerpt:
        excerpt.extend(observation["file_excerpt"])
    summary = (
        f"Working tree on {observation['branch_name']}: changes={observation['local_change_state']}, "
        f"dirty={observation['dirty_working_tree']}."
    )
    return {
        "execution_target": intent_target or observation["branch_name"],
        "execution_summary": summary,
        "execution_confidence": "high" if observation["ok"] else "low",
        "execution_excerpt": excerpt[:_MAX_EXCERPT_LINES],
        "source_contributors": ["git-status", "git-diff-stat"],
    }


def _inspect_local_changes(*, repo_root: Path, intent_target: str) -> dict[str, object]:
    observation = _git_status_observation(repo_root)
    changed_count = len(observation["changed_files"])
    summary = (
        f"Local change inspection found {changed_count} bounded file signals on {observation['branch_name']}; "
        f"state={observation['local_change_state']}."
    )
    excerpt = observation["file_excerpt"] or ["No modified or untracked files reported."]
    return {
        "execution_target": intent_target or observation["branch_name"],
        "execution_summary": summary,
        "execution_confidence": "high" if observation["ok"] else "low",
        "execution_excerpt": excerpt[:_MAX_EXCERPT_LINES],
        "source_contributors": ["git-status"],
    }


def _inspect_upstream_divergence(
    *, repo_root: Path, intent_target: str
) -> dict[str, object]:
    observation = _git_status_observation(repo_root)
    upstream_ref = observation["upstream_ref"]
    excerpt = []
    if upstream_ref:
        divergence_result = _run_git_command(
            repo_root,
            ["rev-list", "--left-right", "--count", f"HEAD...{upstream_ref}"],
        )
        if divergence_result["ok"] and divergence_result["stdout"]:
            excerpt.extend(_trim_lines(str(divergence_result["stdout"])))
    summary = (
        f"Upstream divergence on {observation['branch_name']}: ahead={observation['ahead_count']}, "
        f"behind={observation['behind_count']}, upstream={upstream_ref or 'none'}, state={observation['upstream_awareness']}."
    )
    if not excerpt:
        excerpt = [
            f"ahead={observation['ahead_count']}",
            f"behind={observation['behind_count']}",
            f"upstream={upstream_ref or 'none'}",
        ]
    return {
        "execution_target": intent_target or upstream_ref or observation["branch_name"],
        "execution_summary": summary,
        "execution_confidence": "high" if observation["ok"] else "low",
        "execution_excerpt": excerpt[:_MAX_EXCERPT_LINES],
        "source_contributors": ["git-status", "git-rev-list"],
    }


def _request_bounded_diagnostic(
    *, repo_root: Path, intent_target: str
) -> dict[str, object]:
    observation = _git_status_observation(repo_root)
    summary = (
        f"Bounded repo diagnostic for {observation['branch_name']}: repo={observation['repo_status']}, "
        f"changes={observation['local_change_state']}, upstream={observation['upstream_awareness']}."
    )
    excerpt = [
        f"branch={observation['branch_name']}",
        f"repo_status={observation['repo_status']}",
        f"local_change_state={observation['local_change_state']}",
        f"upstream_awareness={observation['upstream_awareness']}",
    ]
    if observation["file_excerpt"]:
        excerpt.extend(observation["file_excerpt"][: max(_MAX_EXCERPT_LINES - len(excerpt), 0)])
    return {
        "execution_target": intent_target or observation["branch_name"],
        "execution_summary": summary,
        "execution_confidence": "medium" if observation["ok"] else "low",
        "execution_excerpt": excerpt[:_MAX_EXCERPT_LINES],
        "source_contributors": ["git-status"],
    }


def _git_status_observation(repo_root: Path) -> dict[str, object]:
    result = _run_git_command(repo_root, ["status", "--porcelain=2", "--branch"])
    if not result["ok"]:
        return {
            "ok": False,
            "branch_name": "unknown",
            "upstream_ref": "",
            "ahead_count": 0,
            "behind_count": 0,
            "dirty_working_tree": False,
            "repo_status": "git-observation-failed",
            "local_change_state": "unknown",
            "upstream_awareness": "unknown",
            "changed_files": [],
            "file_excerpt": ["git status unavailable"],
        }

    branch_name = "detached"
    upstream_ref = ""
    ahead_count = 0
    behind_count = 0
    modified_present = False
    untracked_present = False
    changed_files: list[str] = []

    for raw_line in str(result["stdout"]).splitlines():
        line = raw_line.strip()
        if line.startswith("# branch.head "):
            branch_name = line.removeprefix("# branch.head ").strip() or "detached"
        elif line.startswith("# branch.upstream "):
            upstream_ref = line.removeprefix("# branch.upstream ").strip()
        elif line.startswith("# branch.ab "):
            for part in line.removeprefix("# branch.ab ").split():
                if part.startswith("+"):
                    ahead_count = _safe_int(part[1:])
                elif part.startswith("-"):
                    behind_count = _safe_int(part[1:])
        elif line.startswith("? "):
            untracked_present = True
            changed_files.append(f"untracked:{line.removeprefix('? ').strip()}")
        elif line.startswith(("1 ", "2 ", "u ")):
            modified_present = True
            parts = line.split()
            if len(parts) >= 9:
                changed_files.append(f"modified:{parts[-1]}")

    local_change_state = "clean"
    if modified_present and untracked_present:
        local_change_state = "mixed"
    elif modified_present:
        local_change_state = "modified"
    elif untracked_present:
        local_change_state = "untracked"

    if not upstream_ref:
        upstream_awareness = "no-upstream"
    elif ahead_count > 0 and behind_count > 0:
        upstream_awareness = "diverged"
    elif behind_count > 0:
        upstream_awareness = "behind"
    elif ahead_count > 0:
        upstream_awareness = "ahead"
    else:
        upstream_awareness = "in-sync"

    dirty_working_tree = modified_present or untracked_present
    return {
        "ok": True,
        "branch_name": branch_name,
        "upstream_ref": upstream_ref,
        "ahead_count": ahead_count,
        "behind_count": behind_count,
        "dirty_working_tree": dirty_working_tree,
        "repo_status": "dirty" if dirty_working_tree else "clean",
        "local_change_state": local_change_state,
        "upstream_awareness": upstream_awareness,
        "changed_files": changed_files[:_MAX_STATUS_FILES],
        "file_excerpt": changed_files[:_MAX_EXCERPT_LINES],
    }


def _run_git_command(repo_root: Path, args: list[str]) -> dict[str, object]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except Exception as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc)}
    return {
        "ok": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _trim_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()][: _MAX_EXCERPT_LINES]


def _safe_int(value: str) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _merge_unique(primary: list[str], secondary: list[object]) -> list[str]:
    merged: list[str] = []
    for value in [*primary, *[str(item) for item in secondary if str(item or "").strip()]]:
        if value not in merged:
            merged.append(value)
    return merged