"""GitHub PR creation and CI status tools via the per-user connector."""
from __future__ import annotations

from typing import Any


def _user_id(args: dict[str, Any]) -> str:
    explicit = str(args.get("_runtime_user_id") or "").strip()
    if explicit:
        return explicit
    from core.identity.workspace_context import current_user_id
    return str(current_user_id() or "")


def execute_github_create_pr(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.github_connector import create_pr

    repo = str(args.get("repo") or "").strip()
    head = str(args.get("head") or "").strip()
    base = str(args.get("base") or "main").strip() or "main"
    title = str(args.get("title") or "").strip()
    if not repo:
        return {"status": "error", "error": "repo_required"}
    if not head:
        return {"status": "error", "error": "head_required"}
    if not title:
        return {"status": "error", "error": "title_required"}
    return create_pr(
        _user_id(args), repo, head=head, base=base, title=title,
        body=str(args.get("body") or ""),
    )


_FAILED = frozenset({
    "failure", "timed_out", "cancelled", "action_required", "startup_failure",
})


def execute_github_ci_status(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.github_connector import _get

    repo = str(args.get("repo") or "").strip()
    sha = str(args.get("commit_sha") or "").strip()
    pull_number = args.get("pull_number")
    if not repo:
        return {"status": "error", "error": "repo_required"}
    if sha and pull_number not in (None, ""):
        return {"status": "error", "error": "choose_commit_sha_or_pull_number"}
    if not sha and pull_number in (None, ""):
        return {"status": "error", "error": "commit_sha_or_pull_number_required"}

    user_id = _user_id(args)
    if not sha:
        try:
            number = int(pull_number)
        except (TypeError, ValueError):  # pull_number er ikke et tal — svar med fejl frem for at gætte
            return {"status": "error", "error": "invalid_pull_number"}
        pr = _get(user_id, f"/repos/{repo}/pulls/{number}")
        if pr.get("status") != "ok":
            return pr
        sha = str(((pr.get("data") or {}).get("head") or {}).get("sha") or "")
        if not sha:
            return {"status": "error", "error": "pull_head_sha_missing"}

    checks_response = _get(user_id, f"/repos/{repo}/commits/{sha}/check-runs")
    if checks_response.get("status") != "ok":
        return checks_response
    status_response = _get(user_id, f"/repos/{repo}/commits/{sha}/status")
    if status_response.get("status") != "ok":
        return status_response

    checks = [
        {
            "name": str(check.get("name") or ""),
            "status": str(check.get("status") or ""),
            "conclusion": check.get("conclusion"),
            "url": check.get("html_url"),
        }
        for check in ((checks_response.get("data") or {}).get("check_runs") or [])
        if isinstance(check, dict)
    ]
    failed = sum(1 for check in checks if str(check.get("conclusion") or "") in _FAILED)
    pending = sum(1 for check in checks if check.get("status") != "completed")
    successful = sum(
        1 for check in checks
        if check.get("status") == "completed" and check.get("conclusion") == "success"
    )
    legacy_state = str((status_response.get("data") or {}).get("state") or "pending")
    if failed or legacy_state in {"failure", "error"}:
        state = "failure"
    elif pending or legacy_state == "pending":
        state = "pending"
    else:
        state = "success"
    return {
        "status": "ok", "repo": repo, "sha": sha, "state": state,
        "summary": {
            "total": len(checks), "successful": successful,
            "pending": pending, "failed": failed,
        },
        "checks": checks,
        "legacy_status": legacy_state,
    }


def execute_github_list_prs(args: dict[str, Any]) -> dict[str, Any]:
    """List PRs through the same per-user connector used by the tool catalog."""
    from core.services.github_connector import list_prs

    repo = str(args.get("repo") or "").strip()
    state = str(args.get("state") or "open").strip() or "open"
    return list_prs(_user_id(args), repo, state=state)


GITHUB_PR_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "github_create_pr",
            "description": "Create a GitHub pull request from an existing branch via the user's connector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "owner/repository"},
                    "head": {"type": "string", "description": "Source branch"},
                    "base": {"type": "string", "description": "Target branch; defaults to main"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["repo", "head", "title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_ci_status",
            "description": "Read GitHub check-run and commit status for one PR or commit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "owner/repository"},
                    "pull_number": {"type": "integer"},
                    "commit_sha": {"type": "string"},
                },
                "required": ["repo"],
            },
        },
    },
]

GITHUB_PR_TOOL_HANDLERS = {
    "github_create_pr": execute_github_create_pr,
    "github_ci_status": execute_github_ci_status,
}

