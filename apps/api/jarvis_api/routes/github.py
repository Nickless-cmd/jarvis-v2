"""Direct Desk adapter for existing GitHub PR/CI tool handlers."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.tools import github_pr_tools as github_tools

router = APIRouter(prefix="/api/github", tags=["github"])


class CreatePrBody(BaseModel):
    repo: str
    head: str
    base: str = "main"
    title: str
    body: str = ""
    approved: bool = False


def _bruger() -> str:
    from core.identity.workspace_context import current_user_id

    user_id = str(current_user_id() or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Ikke logget ind")
    return user_id


def _result(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=str(result.get("error") or "github_error"))
    return result


@router.get("/prs")
def github_prs(repo: str) -> dict[str, Any]:
    return _result(github_tools.execute_github_list_prs({
        "repo": repo, "state": "open", "_runtime_user_id": _bruger(),
    }))


@router.get("/ci")
def github_ci(repo: str, pull_number: int | None = None, commit_sha: str = "") -> dict[str, Any]:
    return _result(github_tools.execute_github_ci_status({
        "repo": repo, "pull_number": pull_number, "commit_sha": commit_sha,
        "_runtime_user_id": _bruger(),
    }))


@router.post("/pr")
def github_create_pr(body: CreatePrBody) -> dict[str, Any]:
    if not body.approved:
        raise HTTPException(status_code=409, detail="explicit_approval_required")
    return _result(github_tools.execute_github_create_pr({
        **body.model_dump(exclude={"approved"}),
        "_runtime_user_id": _bruger(),
    }))
