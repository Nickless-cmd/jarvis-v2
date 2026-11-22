"""Projekt-kontekst og CI-status til Desk.

Tynd adapter: al logik ligger i ``core.services.project_context`` og
``core.tools.github_pr_tools``. Ejeren er den autentificerede bruger — aldrig et
felt i anmodningen. En andens projekt eller samtale er 404, identisk med «findes
ikke».

Kontrakten er Desk-klientens (``apps/jarvis-desk/src/lib/projektApi.ts`` og
``gitPr.ts``); den er skrevet efter hvad klienten faktisk kalder, ikke omvendt.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat-projects"])


class BindProjektBody(BaseModel):
    project_id: str | None = None


class OpretProjektBody(BaseModel):
    name: str
    session_id: str = ""


def _bruger() -> str:
    from core.identity.workspace_context import current_user_id

    uid = (current_user_id() or "").strip()
    if not uid:
        raise HTTPException(status_code=401, detail="Ikke logget ind")
    return uid


def _kraev_session(session_id: str, uid: str) -> str:
    """Samtalen skal tilhøre kalderen. Ellers 404 — ikke 403, så et gæt ikke kan bekræftes."""
    from core.services.chat_sessions import get_session_owner

    sid = str(session_id or "").strip()
    if not sid or get_session_owner(sid) != uid:
        raise HTTPException(status_code=404, detail="Sessionen findes ikke")
    return sid


def _filstoerrelse(sti: str) -> int | None:
    try:
        return Path(sti).stat().st_size
    except OSError:  # filen kan være flyttet siden materialet blev tilføjet
        return None


def _projekt_ud(projekt: dict[str, Any]) -> dict[str, Any]:
    """Service-form (project_id/materials) → Desk-kontrakt (id/files)."""
    filer: list[dict[str, Any]] = []
    for materiale in projekt.get("materials") or []:
        if str(materiale.get("kind")) != "file":
            continue
        sti = str(materiale.get("path") or "")
        navn = str(materiale.get("title") or "").strip() or sti.rsplit("/", 1)[-1]
        if not navn:
            continue
        filer.append({"name": navn, "size_bytes": _filstoerrelse(sti)})
    return {
        "id": str(projekt.get("project_id") or ""),
        "name": str(projekt.get("name") or ""),
        "files": filer,
    }


@router.get("/api/projects")
def list_projekter() -> dict[str, Any]:
    uid = _bruger()
    from core.services import project_context

    projekter = project_context.list_projects(owner_user_id=uid)
    return {"projects": [_projekt_ud(p) for p in projekter]}


@router.post("/api/projects")
def opret_projekt(body: OpretProjektBody) -> dict[str, Any]:
    uid = _bruger()
    if body.session_id.strip():
        _kraev_session(body.session_id, uid)
    from core.services import project_context

    try:
        projekt = project_context.create_project(
            session_id=body.session_id, name=body.name, owner_user_id=uid
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"project": _projekt_ud(projekt)}


@router.get("/chat/sessions/{session_id}/project")
def hent_session_projekt(session_id: str) -> dict[str, Any]:
    uid = _bruger()
    sid = _kraev_session(session_id, uid)
    from core.services import project_context

    projekt = project_context.get_project_for_session(sid)
    return {"project_id": str(projekt["project_id"]) if projekt else None}


@router.put("/chat/sessions/{session_id}/project")
def bind_session_projekt(session_id: str, body: BindProjektBody) -> dict[str, Any]:
    uid = _bruger()
    sid = _kraev_session(session_id, uid)
    from core.services import project_context

    if body.project_id is None:
        project_context.unbind_session(sid)
        return {"ok": True, "project_id": None}
    projekt = project_context.get_project(body.project_id)
    if projekt is None:
        raise HTTPException(status_code=404, detail="Projektet findes ikke")
    eier = str(projekt.get("owner_user_id") or "").strip()
    if eier and eier != uid:
        raise HTTPException(status_code=404, detail="Projektet findes ikke")
    project_context.bind_session(body.project_id, sid)
    return {"ok": True, "project_id": body.project_id}


def _git(root: str, *args: str) -> str:
    """Kør git i ``root`` uden shell. Fejler lukket — tom streng, ingen gæt."""
    try:
        ud = subprocess.run(  # noqa: S603 - faste argumenter, ingen shell
            ["git", "-C", root, *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # git mangler eller timeout
        logger.debug("git %s fejlede i %s: %s", args, root, exc)
        return ""
    return (ud.stdout or "").strip() if ud.returncode == 0 else ""


def _repo_fra_root(root: str) -> str:
    """``git@github.com:eier/rep.git`` eller https-URL → ``eier/rep``."""
    url = _git(root, "remote", "get-url", "origin")
    if not url:
        return ""
    renset = url.strip().removesuffix(".git")
    if renset.startswith("git@"):
        _, _, rest = renset.partition(":")
        return rest
    if "://" in renset:
        return "/".join(renset.split("://", 1)[1].split("/")[1:])
    return ""


@router.get("/chat/git/ci-status")
def git_ci_status(root: str = "", branch: str = "", kind: str = "") -> dict[str, Any]:
    """CI-status for en branch i et lokalt repo.

    Desk viser resultatet i Git-panelet. En manglende GitHub-forbindelse eller et
    ikke-GitHub-remote giver ``state: "none"`` med en forklarende ``error`` — ikke
    en falsk grøn.
    """
    uid = _bruger()
    sti = str(root or "").strip()
    if not sti or not Path(sti).is_dir():
        return {"ok": False, "state": "none", "checks": [], "error": "ukendt_arbejdstrae"}
    gren = str(branch or "").strip() or _git(sti, "rev-parse", "--abbrev-ref", "HEAD")
    if not gren:
        return {"ok": False, "state": "none", "checks": [], "error": "ingen_branch"}
    repo = _repo_fra_root(sti)
    if not repo:
        return {"ok": False, "state": "none", "checks": [], "error": "remote_er_ikke_github"}
    sha = _git(sti, "rev-parse", gren)
    if not sha:
        return {"ok": False, "state": "none", "checks": [], "error": "ukendt_sha"}

    from core.tools.github_pr_tools import execute_github_ci_status

    svar = execute_github_ci_status({"repo": repo, "commit_sha": sha, "user_id": uid})
    if svar.get("status") == "error":
        return {
            "ok": False,
            "state": "none",
            "checks": [],
            "error": str(svar.get("error") or "ci_status_fejlede"),
        }
    checks = [
        {
            "name": str(c.get("name") or ""),
            "state": "pending" if c.get("status") != "completed"
            else ("success" if c.get("conclusion") == "success" else "failure"),
            "url": c.get("url"),
        }
        for c in (svar.get("checks") or [])
        if isinstance(c, dict)
    ]
    return {
        "ok": True,
        "state": str(svar.get("state") or "none"),
        "checks": checks,
        "url": svar.get("url"),
    }
