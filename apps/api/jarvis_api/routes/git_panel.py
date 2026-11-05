"""Git-panelets ruter: status, diff, stage, unstage, commit, log, push, worktrees.

Det der ALLEREDE fandtes bliver ikke gentaget her:

- branch-liste, branch-skift og «opret worktree» ligger i
  `routes/chat.py` (`/chat/git/branches`, `/chat/git/checkout`,
  `/chat/git/worktree`) og i `core/services/git_workspace_actions.py`.
  Panelet kalder dem direkte.
- git-kørslen selv (`_koer`) deler container-vejen (subprocess med argv, ingen
  shell) og workstation-vejen (operator-bro med `shlex.quote`) med de
  eksisterende ruter. Her er ingen kommandostrenge bygget af brugerinput.
- commit går gennem `commit_with_attribution` / det samme workstation-script
  som `/chat/git/commit-all` bruger, så de seks påkrævede trailere (Actor,
  Actor-Type, Run-ID, Session-ID, Origin, Approved-By) sættes af serveren —
  aldrig af klienten.

Forskellen fra `/chat/git/commit-all`: panelet committer KUN det der er staged.
`commit-all` kører `git add -A` først, og det er netop det panelet skal kunne
undgå.

Auth/fejlmodel følger `chat.py`: container kræver owner (`_owner_repo_base`),
ugyldigt input giver HTTP 400, og en git-fejl giver `{"ok": False, "error": …}`
med git's egen begrundelse.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/chat/git-panel", tags=["git-panel"])

# En diff over dette er ikke noget man læser i et panel. Afkortes, og klienten
# får `truncated: true` så den kan sige det højt i stedet for at vise en halv diff.
MAX_DIFF_TEGN = 200_000

_DIFF_MODES = ("unstaged", "staged", "head")


# ── Rene funktioner (testes uden git) ───────────────────────────────────────

def _afkvot(sti: str) -> str:
    """`git status` citerer stier med mellemrum/specialtegn: "a b.txt"."""
    s = sti.strip()
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        s = s[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return s


def parse_status(tekst: str) -> dict[str, Any]:
    """`git status --porcelain=v1 --branch` → branch, tracking og filliste."""
    branch = ""
    upstream = ""
    ahead = behind = 0
    detached = False
    filer: list[dict[str, Any]] = []
    for linje in (tekst or "").splitlines():
        if linje.startswith("## "):
            rest = linje[3:]
            if rest.startswith("No commits yet on "):
                branch = rest[len("No commits yet on "):].strip()
            elif rest.startswith("HEAD (no branch)"):
                branch, detached = "HEAD", True
            else:
                m = re.match(
                    r"^(?P<br>.+?)(?:\.\.\.(?P<up>\S+))?(?: \[(?P<st>[^\]]*)\])?$", rest,
                )
                if m:
                    branch = m.group("br")
                    upstream = m.group("up") or ""
                    st = m.group("st") or ""
                    a = re.search(r"ahead (\d+)", st)
                    b = re.search(r"behind (\d+)", st)
                    ahead = int(a.group(1)) if a else 0
                    behind = int(b.group(1)) if b else 0
            continue
        if len(linje) < 4 or linje[2] != " ":
            continue
        x, y, sti = linje[0], linje[1], linje[3:]
        gammel = ""
        if x in "RC" and " -> " in sti:
            gammel, sti = sti.split(" -> ", 1)
            gammel = _afkvot(gammel)
        sti = _afkvot(sti)
        if x == "!":  # ignoreret — vises ikke
            continue
        filer.append({
            "path": sti,
            "old_path": gammel,
            "index": x,
            "worktree": y,
            "untracked": x == "?",
            "staged": x not in (" ", "?"),
            "unstaged": y != " ",
            "conflict": x == "U" or y == "U" or (x, y) in (("A", "A"), ("D", "D")),
        })
    return {
        "branch": branch, "upstream": upstream, "ahead": ahead, "behind": behind,
        "detached": detached, "files": filer, "dirty": len(filer),
        "staged_count": sum(1 for f in filer if f["staged"]),
        "unstaged_count": sum(1 for f in filer if f["unstaged"]),
    }


def parse_log(tekst: str) -> list[dict[str, str]]:
    """Format `%H\\x1f%h\\x1f%an\\x1f%aI\\x1f%s\\x1e` → liste af commits."""
    ud: list[dict[str, str]] = []
    for blok in (tekst or "").split("\x1e"):
        blok = blok.strip("\n")
        if not blok.strip():
            continue
        d = blok.split("\x1f")
        if len(d) < 5:
            continue
        ud.append({"sha": d[0], "short": d[1], "author": d[2], "date": d[3], "subject": d[4]})
    return ud


def parse_worktrees(tekst: str) -> list[dict[str, Any]]:
    """`git worktree list --porcelain` → liste. Første post er hovedtræet."""
    ud: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for linje in (tekst or "").splitlines():
        if not linje.strip():
            cur = None
            continue
        nøgle, _, værdi = linje.partition(" ")
        if nøgle == "worktree":
            cur = {"path": værdi, "head": "", "branch": "", "detached": False,
                   "bare": False, "locked": False, "main": not ud}
            ud.append(cur)
        elif cur is None:
            continue
        elif nøgle == "HEAD":
            cur["head"] = værdi[:12]
        elif nøgle == "branch":
            cur["branch"] = værdi.removeprefix("refs/heads/")
        elif nøgle in ("detached", "bare", "locked"):
            cur[nøgle] = True
    return ud


def rens_sti(sti: str) -> str:
    """Afvis stier der kunne læses som flag eller bryde ud af repoet.

    Argv-vejen er allerede shell-sikker; dette er grænsen mod `-` (flag),
    absolutte stier og `..`.
    """
    s = (sti or "").strip()
    dele = s.replace("\\", "/").split("/")
    if (not s or s.startswith("-") or s.startswith("/") or "\x00" in s
            or "\n" in s or ".." in dele):
        raise HTTPException(status_code=400, detail=f"ugyldig sti: {sti!r}")
    return s


# ── Mål + kørsel ────────────────────────────────────────────────────────────

def _mål(kind: str, root: str) -> tuple[str, str, str]:
    """Validér target → (kind, rod, uid). Container = owner + server-repo."""
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or ""
    if kind == "container":
        from apps.api.jarvis_api.routes.chat import _owner_repo_base
        return "container", str(_owner_repo_base(root or "repo")), uid
    if kind == "workstation":
        if not (root or "").strip():
            raise HTTPException(status_code=400, detail="root må ikke være tom")
        return "workstation", root, uid
    raise HTTPException(status_code=400, detail="ukendt kind")


def _git(kind: str, rod: str, uid: str, *args: list[str]) -> tuple[bool, list[str]]:
    from core.services.git_workspace_actions import _koer
    return _koer(kind, rod, list(args), uid)


def _fejl(ud: list[str], standard: str = "git svarede ikke") -> dict[str, Any]:
    grund = next((x.strip() for x in reversed(ud) if x and x.strip()), "")
    return {"ok": False, "error": grund or standard}


def _status_sync(kind: str, rod: str, uid: str) -> dict[str, Any]:
    ok, ud = _git(kind, rod, uid,
                  ["-c", "core.quotepath=false", "status", "--porcelain=v1", "--branch"])
    if not ok or not ud or not ud[0].strip():
        return _fejl(ud, "ikke et git-repo")
    return {"ok": True, **parse_status(ud[0])}


def _diff_sync(kind: str, rod: str, uid: str, path: str, mode: str) -> dict[str, Any]:
    if path:
        ok, ud = _git(kind, rod, uid, ["status", "--porcelain=v1", "--", path])
        if not ok:
            return _fejl(ud)
        untracked = any(l.startswith("?? ") for l in (ud[0] or "").splitlines())
        if untracked and mode == "unstaged":
            # Eneste vej til en diff af en fil git ikke kender. Exit 1 = «der er
            # forskel» og er ikke en fejl; `_koer` accepterer det når der er output.
            args = ["diff", "--no-index", "--", "/dev/null", path]
        elif mode == "staged":
            args = ["diff", "--cached", "--", path]
        elif mode == "head":
            args = ["diff", "HEAD", "--", path]
        else:
            args = ["diff", "--", path]
    else:
        args = {"staged": ["diff", "--cached"], "head": ["diff", "HEAD"]}.get(mode, ["diff"])
    ok, ud = _git(kind, rod, uid, args)
    if not ok:
        return _fejl(ud)
    tekst = ud[0] or ""
    afkortet = len(tekst) > MAX_DIFF_TEGN
    if afkortet:
        tekst = tekst[:MAX_DIFF_TEGN]
    return {"ok": True, "path": path, "mode": mode, "diff": tekst,
            "truncated": afkortet, "binary": "Binary files" in tekst}


def _stage_sync(kind: str, rod: str, uid: str, paths: list[str], alle: bool) -> dict[str, Any]:
    args = ["add", "-A"] if alle else ["add", "--", *paths]
    ok, ud = _git(kind, rod, uid, args)
    return {"ok": True, "paths": paths, "all": alle} if ok else _fejl(ud)


def _unstage_sync(kind: str, rod: str, uid: str, paths: list[str], alle: bool) -> dict[str, Any]:
    mål = ["--", *paths] if not alle else ["--", "."]
    # Uden commits findes HEAD ikke, og `restore --staged` har intet at gå tilbage
    # til. Dér er `rm --cached` det rigtige — men KUN dér: på et repo med HEAD
    # ville den stage en SLETNING. Derfor spørges der først.
    ok_h, hd = _git(kind, rod, uid, ["rev-parse", "--verify", "-q", "HEAD"])
    # `ok_h` først: ved fejl indeholder listen git's FEJLTEKST, ikke en sha.
    har_head = bool(ok_h and hd and hd[0].strip())
    if har_head:
        ok, ud = _git(kind, rod, uid, ["restore", "--staged", *mål])
    else:
        ok, ud = _git(kind, rod, uid, ["rm", "--cached", "-r", "-q", *mål])
    return {"ok": True, "paths": paths, "all": alle} if ok else _fejl(ud)


def _commit_sync(kind: str, rod: str, uid: str, besked: str) -> dict[str, Any]:
    ok, ud = _git(kind, rod, uid, ["diff", "--cached", "--name-only"])
    if not ok:
        return _fejl(ud)
    if not (ud[0] or "").strip():
        return {"ok": False, "error": "Ingen staged ændringer at committe"}
    from core.services import git_actions
    if kind == "container":
        from core.services.attributed_git_commit import commit_with_attribution
        r = commit_with_attribution(
            repo=Path(rod), message=besked, attribution=git_actions._human_attribution(),
        )
        if r.returncode != 0:
            blob = ((r.stdout or "") + (r.stderr or "")).strip()
            return {"ok": False, "error": blob[:400] or "git commit fejlede"}
        return {"ok": True, "sha": (r.sha or "")[:12], "message": besked}
    rc, out, err = git_actions._ws_attributed_commit(rod, uid, besked)
    if rc != 0:
        return {"ok": False, "error": (out + err).strip()[:400] or "git commit fejlede"}
    _, sha, _ = git_actions._ws_git(rod, uid, "rev-parse --short HEAD")
    return {"ok": True, "sha": sha.strip(), "message": besked}


def _log_sync(kind: str, rod: str, uid: str, grænse: int) -> dict[str, Any]:
    ok, ud = _git(kind, rod, uid, [
        "log", f"-n{grænse}", "--format=%H%x1f%h%x1f%an%x1f%aI%x1f%s%x1e",
    ])
    if not ok:
        # Et nyt repo uden commits er ikke en fejl — der er bare intet at vise.
        if "does not have any commits" in " ".join(ud):
            return {"ok": True, "commits": []}
        return _fejl(ud)
    return {"ok": True, "commits": parse_log(ud[0])}


def _push_sync(kind: str, rod: str, uid: str) -> dict[str, Any]:
    ok, ud = _git(kind, rod, uid, ["rev-parse", "--abbrev-ref", "HEAD"])
    branch = (ud[0].strip().splitlines() or [""])[0] if ok and ud else ""
    if not branch:
        return _fejl(ud, "kunne ikke aflæse branch")
    if branch == "HEAD":
        return {"ok": False, "error": "Afkoblet HEAD — skift til en branch før push"}
    ok_u, ud_u = _git(kind, rod, uid, ["rev-parse", "--abbrev-ref", "@{u}"])
    har_upstream = bool(ok_u and ud_u and ud_u[0].strip())
    args = ["push"] if har_upstream else ["push", "-u", "origin", branch]
    ok, ud = _git(kind, rod, uid, args)
    if not ok:
        return _fejl(ud, "push fejlede")
    # Sandheden står i repoet, ikke i exit-koden: over broen kommer exit-kode og
    # stderr ikke med tilbage, så et mislykket push ville ellers se ud som succes.
    st = _status_sync(kind, rod, uid)
    if not st.get("ok"):
        return st
    if not st["upstream"] or st["ahead"] > 0:
        return {"ok": False, "error": "Push gik ikke igennem — der er stadig upushede commits",
                "branch": branch, "ahead": st["ahead"]}
    return {"ok": True, "branch": branch, "upstream": st["upstream"], "set_upstream": not har_upstream}


def _worktrees_sync(kind: str, rod: str, uid: str) -> dict[str, Any]:
    ok, ud = _git(kind, rod, uid, ["worktree", "list", "--porcelain"])
    if not ok:
        return _fejl(ud)
    trær = parse_worktrees(ud[0])
    nu = rod.rstrip("/")
    for t in trær:
        t["current"] = str(t["path"]).rstrip("/") == nu
    return {"ok": True, "worktrees": trær}


# ── Ruter ───────────────────────────────────────────────────────────────────

class _PathsBody(BaseModel):
    kind: str = "container"
    root: str = "repo"
    paths: list[str] = []
    all: bool = False


class _CommitBody(BaseModel):
    kind: str = "container"
    root: str = "repo"
    message: str = ""


class _PushBody(BaseModel):
    kind: str = "container"
    root: str = "repo"


@router.get("/status")
async def git_panel_status(kind: str = "container", root: str = "repo") -> dict:
    k, rod, uid = _mål(kind, root)
    return await asyncio.to_thread(_status_sync, k, rod, uid)


@router.get("/diff")
async def git_panel_diff(
    kind: str = "container", root: str = "repo", path: str = "", mode: str = "unstaged",
) -> dict:
    """Diff for én fil (`path`) eller samlet (uden `path`).

    mode: `unstaged` (working tree mod index), `staged` (index mod HEAD) eller
    `head` (working tree mod HEAD).
    """
    if mode not in _DIFF_MODES:
        raise HTTPException(status_code=400, detail=f"mode skal være en af {', '.join(_DIFF_MODES)}")
    ren = rens_sti(path) if path.strip() else ""
    k, rod, uid = _mål(kind, root)
    return await asyncio.to_thread(_diff_sync, k, rod, uid, ren, mode)


def _paths_eller_alle(body: _PathsBody) -> tuple[list[str], bool]:
    if body.all:
        return [], True
    if not body.paths:
        raise HTTPException(status_code=400, detail="paths må ikke være tom (eller sæt all)")
    return [rens_sti(p) for p in body.paths], False


@router.post("/stage")
async def git_panel_stage(body: _PathsBody) -> dict:
    paths, alle = _paths_eller_alle(body)
    k, rod, uid = _mål(body.kind, body.root)
    return await asyncio.to_thread(_stage_sync, k, rod, uid, paths, alle)


@router.post("/unstage")
async def git_panel_unstage(body: _PathsBody) -> dict:
    paths, alle = _paths_eller_alle(body)
    k, rod, uid = _mål(body.kind, body.root)
    return await asyncio.to_thread(_unstage_sync, k, rod, uid, paths, alle)


@router.post("/commit")
async def git_panel_commit(body: _CommitBody) -> dict:
    """Commit KUN det staged, med serverens attribution-trailere."""
    besked = (body.message or "").strip()
    if not besked:
        raise HTTPException(status_code=400, detail="message må ikke være tom")
    k, rod, uid = _mål(body.kind, body.root)
    return await asyncio.to_thread(_commit_sync, k, rod, uid, besked)


@router.get("/log")
async def git_panel_log(kind: str = "container", root: str = "repo", limit: int = 30) -> dict:
    k, rod, uid = _mål(kind, root)
    return await asyncio.to_thread(_log_sync, k, rod, uid, max(1, min(int(limit), 200)))


@router.post("/push")
async def git_panel_push(body: _PushBody) -> dict:
    """Push den aktuelle branch (sætter upstream til origin første gang).

    Udadvendt — kaldes kun når brugeren selv trykker. Aldrig `--force`.
    """
    k, rod, uid = _mål(body.kind, body.root)
    return await asyncio.to_thread(_push_sync, k, rod, uid)


@router.get("/worktrees")
async def git_panel_worktrees(kind: str = "container", root: str = "repo") -> dict:
    k, rod, uid = _mål(kind, root)
    return await asyncio.to_thread(_worktrees_sync, k, rod, uid)
