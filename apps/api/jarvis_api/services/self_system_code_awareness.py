from __future__ import annotations

import platform
import shutil
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from core.tools.workspace_capabilities import load_workspace_capabilities


def build_self_system_code_awareness_surface() -> dict[str, object]:
    built_at = datetime.now(UTC).isoformat()
    capabilities = load_workspace_capabilities()
    workspace_root = Path(str(capabilities.get("workspace") or "")).resolve()
    cwd = Path.cwd().resolve()
    repo_root = _detect_repo_root(cwd, workspace_root, Path(__file__).resolve())
    git_present = shutil.which("git") is not None

    source_contributors = [
        "cwd",
        "workspace-capabilities",
        "host-runtime",
    ]
    if workspace_root.exists():
        source_contributors.append("workspace-root")
    if repo_root is not None:
        source_contributors.append("repo-root")
    if git_present:
        source_contributors.append("git-status")

    host_readiness = "host-ready" if cwd.exists() and workspace_root.exists() else "host-limited"
    approval_required_count = int(
        ((capabilities.get("authority") or {}).get("approval_required_count") or 0)
    )

    observation = _default_repo_observation()
    code_awareness_state = "repo-unavailable"
    confidence = "low"

    if repo_root is not None and git_present:
        observation = _observe_repo_status(repo_root)
        code_awareness_state = (
            "repo-visible" if str(observation.get("repo_status") or "") != "git-observation-failed" else "repo-limited"
        )
        confidence = "high" if code_awareness_state == "repo-visible" else "medium"
    elif repo_root is not None:
        observation["repo_status"] = "git-unavailable"
        observation["local_change_state"] = "unknown"
        observation["upstream_awareness"] = "unknown"
        code_awareness_state = "repo-limited"
        confidence = "low"

    concern_state, concern_hint = _derive_concern_state(
        repo_status=str(observation.get("repo_status") or "not-git"),
        local_change_state=str(observation.get("local_change_state") or "unknown"),
        upstream_awareness=str(observation.get("upstream_awareness") or "unknown"),
        branch_name=str(observation.get("branch_name") or "none"),
    )

    return {
        "active": True,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "truth": "read-only-observation",
        "kind": "self-system-code-awareness-light",
        "observation_mode": "read-only",
        "system_awareness_state": host_readiness,
        "code_awareness_state": code_awareness_state,
        "repo_status": str(observation.get("repo_status") or "not-git"),
        "local_change_state": str(observation.get("local_change_state") or "unknown"),
        "upstream_awareness": str(observation.get("upstream_awareness") or "unknown"),
        "concern_state": concern_state,
        "concern_hint": concern_hint,
        "action_requires_approval": True,
        "confidence": confidence,
        "source_contributors": source_contributors,
        "approval_boundary": (
            "Observation is read-only. Any exec, git, fetch, pull, commit, reset, checkout, or apply step would require explicit approval."
        ),
        "host_context": {
            "hostname": socket.gethostname(),
            "platform": platform.system().lower() or "unknown",
            "cwd": str(cwd),
            "workspace_root": str(workspace_root),
            "repo_root": str(repo_root) if repo_root is not None else "",
            "git_present": git_present,
        },
        "repo_observation": {
            **observation,
            "repo_root_detected": repo_root is not None,
            "approval_required_capability_count": approval_required_count,
        },
        "seam_usage": [
            "heartbeat-grounding",
            "prompt-contract-runtime-truth",
            "runtime-self-model",
            "mission-control-runtime",
        ],
        "built_at": built_at,
        "source": "/mc/self-system-code-awareness",
    }


def _default_repo_observation() -> dict[str, object]:
    return {
        "branch_name": "none",
        "upstream_ref": "",
        "ahead_count": 0,
        "behind_count": 0,
        "dirty_working_tree": False,
        "untracked_present": False,
        "modified_present": False,
        "recent_local_changes_present": False,
        "repo_status": "not-git",
        "local_change_state": "unknown",
        "upstream_awareness": "unknown",
    }


def _detect_repo_root(*starts: Path) -> Path | None:
    for start in starts:
        try:
            current = start if start.is_dir() else start.parent
            current = current.resolve()
        except Exception:
            continue
        for candidate in [current, *current.parents]:
            if (candidate / ".git").exists():
                return candidate
    return None


def _observe_repo_status(repo_root: Path) -> dict[str, object]:
    result = _run_read_only_command(
        ["git", "-C", str(repo_root), "status", "--porcelain=2", "--branch"]
    )
    if not result["ok"]:
        return {
            **_default_repo_observation(),
            "repo_status": "git-observation-failed",
            "local_change_state": "unknown",
            "upstream_awareness": "unknown",
        }

    branch_name = "detached"
    upstream_ref = ""
    ahead_count = 0
    behind_count = 0
    modified_present = False
    untracked_present = False

    for raw_line in str(result.get("stdout") or "").splitlines():
        line = raw_line.strip()
        if line.startswith("# branch.head "):
            branch_name = line.removeprefix("# branch.head ").strip() or "detached"
        elif line.startswith("# branch.upstream "):
            upstream_ref = line.removeprefix("# branch.upstream ").strip()
        elif line.startswith("# branch.ab "):
            parts = line.removeprefix("# branch.ab ").split()
            for part in parts:
                if part.startswith("+"):
                    ahead_count = _safe_int(part[1:])
                elif part.startswith("-"):
                    behind_count = _safe_int(part[1:])
        elif line.startswith("? "):
            untracked_present = True
        elif line.startswith(("1 ", "2 ", "u ")):
            modified_present = True

    local_change_state = "clean"
    if modified_present and untracked_present:
        local_change_state = "mixed"
    elif modified_present:
        local_change_state = "modified"
    elif untracked_present:
        local_change_state = "untracked"

    dirty_working_tree = modified_present or untracked_present
    repo_status = "dirty" if dirty_working_tree else "clean"
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

    return {
        "branch_name": branch_name,
        "upstream_ref": upstream_ref,
        "ahead_count": ahead_count,
        "behind_count": behind_count,
        "dirty_working_tree": dirty_working_tree,
        "untracked_present": untracked_present,
        "modified_present": modified_present,
        "recent_local_changes_present": dirty_working_tree,
        "repo_status": repo_status,
        "local_change_state": local_change_state,
        "upstream_awareness": upstream_awareness,
    }


def _derive_concern_state(
    *,
    repo_status: str,
    local_change_state: str,
    upstream_awareness: str,
    branch_name: str,
) -> tuple[str, str]:
    if repo_status in {"not-git", "git-unavailable", "git-observation-failed"}:
        return (
            "notice",
            "Read-only awareness can see limited repo truth right now; any deeper repo action would still require approval.",
        )
    if upstream_awareness in {"behind", "diverged"}:
        return (
            "action-requires-approval",
            f"Branch {branch_name} is {upstream_awareness} from upstream; awareness is read-only and any sync action would require approval.",
        )
    if local_change_state == "mixed":
        return (
            "action-requires-approval",
            f"Branch {branch_name} has both modified and untracked local changes; observation is bounded and any git handling would require approval.",
        )
    if local_change_state == "modified":
        return (
            "concern",
            f"Branch {branch_name} has local modifications visible in read-only awareness; no action has been taken.",
        )
    if upstream_awareness == "ahead":
        return (
            "concern",
            f"Branch {branch_name} is ahead of upstream; awareness can see divergence, but reconciliation would require approval.",
        )
    if local_change_state == "untracked" or upstream_awareness == "no-upstream":
        return (
            "notice",
            f"Branch {branch_name} is readable with bounded local variation; no action has been taken.",
        )
    return (
        "stable",
        f"Branch {branch_name} looks stable under read-only awareness; action would still require approval if needed.",
    )


def _run_read_only_command(args: list[str]) -> dict[str, object]:
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except Exception:
        return {"ok": False, "stdout": "", "stderr": "", "returncode": 1}
    return {
        "ok": completed.returncode == 0,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "returncode": completed.returncode,
    }


def _safe_int(raw: str) -> int:
    try:
        return int(raw)
    except Exception:
        return 0
