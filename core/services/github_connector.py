"""GitHub-connector — API-klient + tool-handlers (v1: issues + PRs).

Bruger BRUGERENS egen token fra oauth_store (get_fresh_token → auto-refresh).
Spor A: members forbinder deres EGET repo; tokenet rører aldrig Jarvis' eller
ejerens GitHub. Intet token → {"status":"error","error":"github_not_connected"}.
"""
from __future__ import annotations

from core.services.oauth_store import get_fresh_token

_API = "https://api.github.com"

GITHUB_CONNECTOR_TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "github_list_issues",
            "description": (
                "List issues i et GitHub-repo via brugerens EGEN forbundne GitHub-konto "
                "(connector). Kræver at brugeren har forbundet GitHub i Marketplace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "owner/navn, fx 'octocat/hello-world'"},
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "Standard: open"},
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_list_prs",
            "description": (
                "List pull requests i et GitHub-repo via brugerens EGEN forbundne "
                "GitHub-konto (connector). Kræver forbundet GitHub i Marketplace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "owner/navn, fx 'octocat/hello-world'"},
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "Standard: open"},
                },
                "required": ["repo"],
            },
        },
    },
]


def _headers(token: dict) -> dict:
    return {
        "Authorization": f"Bearer {token.get('access_token')}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get(user_id: str, path: str, params: dict | None = None) -> dict:
    token = get_fresh_token(user_id, "github")
    if not token or not token.get("access_token"):
        return {"status": "error", "error": "github_not_connected"}
    try:
        import httpx
        r = httpx.get(_API + path, headers=_headers(token), params=params or {}, timeout=20)
        if r.status_code == 401:
            return {"status": "error", "error": "github_not_connected"}
        if r.status_code != 200:
            return {"status": "error", "error": f"github_http_{r.status_code}"}
        return {"status": "ok", "data": r.json()}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"github_request_failed: {e}"}


def list_issues(user_id: str, repo: str, *, state: str = "open") -> dict:
    """Issues i `repo` (owner/name). state: open|closed|all."""
    if not (repo or "").strip():
        return {"status": "error", "error": "repo_required"}
    res = _get(user_id, f"/repos/{repo}/issues", {"state": state, "per_page": 30})
    if res["status"] != "ok":
        return res
    issues = [
        {"number": i.get("number"), "title": i.get("title"), "state": i.get("state"),
         "url": i.get("html_url")}
        for i in res["data"] if isinstance(i, dict) and "pull_request" not in i
    ]
    return {"status": "ok", "issues": issues}


def list_prs(user_id: str, repo: str, *, state: str = "open") -> dict:
    """Pull requests i `repo` (owner/name). state: open|closed|all."""
    if not (repo or "").strip():
        return {"status": "error", "error": "repo_required"}
    res = _get(user_id, f"/repos/{repo}/pulls", {"state": state, "per_page": 30})
    if res["status"] != "ok":
        return res
    prs = [
        {"number": p.get("number"), "title": p.get("title"), "state": p.get("state"),
         "url": p.get("html_url")}
        for p in res["data"] if isinstance(p, dict)
    ]
    return {"status": "ok", "prs": prs}
