from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.services.chat_sessions import (
    append_chat_message,
    create_chat_session,
    delete_chat_session,
    get_chat_session,
    list_chat_sessions,
    rename_chat_session,
)
from core.services.visible_runs import (
    cancel_visible_run,
    resolve_pending_approval,
    start_visible_run,
)

router = APIRouter(prefix="/chat", tags=["chat"])

# ── Preview-panel: path-jailed fil-læsning (jarvis-desk) ──
_LANG_BY_EXT = {
    ".py": "python", ".ts": "typescript", ".tsx": "tsx", ".js": "javascript",
    ".json": "json", ".md": "markdown", ".css": "css", ".sh": "bash", ".txt": "text",
}


def _repo_root() -> Path:
    # chat.py: apps/api/jarvis_api/routes/ → fire niveauer op til repo-rod.
    return Path(__file__).resolve().parents[4]


def _allowed_roots(role: str, user_id: str) -> dict[str, Path]:
    """Navngivne server-side roots pr. rolle (spec file-tree-control 2026-06-15).

    owner: kodebasen (repo) + ~/.jarvis-v2/ + eget workspace.
    member/guest: KUN eget workspace (må ALDRIG browse repoet eller andres data).
    """
    from core.runtime.config import JARVIS_HOME
    from core.runtime.workspace_paths import workspace_dir
    # Eget workspace kræver bruger-kontekst. Owner-egen-session (ingen uid) har
    # ikke nødvendigvis en sat kontekst → spring workspace over hvis uresolverbart.
    ws: Path | None = None
    try:
        ws = workspace_dir(user_id or None).resolve()
    except Exception:
        ws = None
    if (role or "").lower() == "owner":
        roots = {
            "repo": _repo_root().resolve(),
            "jarvis-v2": Path(JARVIS_HOME).resolve(),
        }
        if ws is not None:
            roots["workspace"] = ws
        return roots
    return {"workspace": ws} if ws is not None else {}


def _resolve_role(uid: str) -> str:
    """Rolle for request-brugeren. Ingen uid = owner-egen-session (default)."""
    if not uid:
        return "owner"
    try:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(uid)
        return (getattr(u, "role", "") or "guest") if u else "guest"
    except Exception:
        return "guest"


@router.get("/file")
async def chat_read_file(
    path: str = Query(...), root: str = "", kind: str = "container",
) -> dict:
    """Læs en fil til preview-panelet. `root` er det navngivne server-root (owner:
    repo/jarvis-v2/workspace, member: workspace); `path` er rel inde i det root.
    Workstation: `root` = trusted folder (absolut), `path` = rel. Blokerende fs/bro-
    kald offloades til tråd (--workers 1 frys-fælde)."""
    import asyncio
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or ""
    role = _resolve_role(uid)
    return await asyncio.to_thread(_read_file_sync, path, root, kind, role, uid)


def _read_file_sync(
    path: str, root: str, kind: str, role: str = "owner", uid: str = "",
) -> dict:
    """Container: navngivne rolle-scopede roots, path-jailed. Workstation: via broen."""
    if kind == "workstation":
        full = (root.rstrip("/") + "/" + path) if root else path
        res = _operator_exec("operator_read_file", {"path": full, "_user_id": uid})
        if res.get("status") != "ok":
            raise HTTPException(status_code=502, detail=str(res.get("error") or res.get("reason") or "operator-read fejlede"))
        # _run_operator_async pakker bro-svaret i {"status","result"}.
        # operator_read_file_async returnerer filindholdet som ren streng.
        content = str(res.get("result") if res.get("result") is not None else "")
        ext = ("." + full.rsplit(".", 1)[-1]) if "." in full.rsplit("/", 1)[-1] else ""
        return {"path": full, "content": content, "language": _LANG_BY_EXT.get(ext, "text")}

    roots = _allowed_roots(role, uid)
    base = roots.get(root)
    if base is None:
        raise HTTPException(status_code=403, detail=f"root '{root}' ikke tilladt for rollen")
    candidate = (base / path).resolve()
    if not str(candidate).startswith(str(base)):
        raise HTTPException(status_code=403, detail="path uden for jail")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="ikke fundet")
    content = candidate.read_text(encoding="utf-8", errors="replace")
    return {"path": path, "content": content, "language": _LANG_BY_EXT.get(candidate.suffix, "text")}


class _FileWriteBody(BaseModel):
    root: str = ""
    path: str
    content: str
    kind: str = "container"


@router.post("/file")
async def chat_write_file(body: _FileWriteBody) -> dict:
    """Gem en redigeret fil fra in-app editoren (code mode). Rolle-scopet + jailet
    som GET; container skriver direkte (owner: repo/jarvis-v2/workspace, member:
    workspace), workstation via operator-broen. Blokerende I/O → to_thread."""
    import asyncio
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or ""
    role = _resolve_role(uid)
    return await asyncio.to_thread(
        _write_file_sync, body.path, body.root, body.content, body.kind, role, uid,
    )


def _write_file_sync(
    path: str, root: str, content: str, kind: str, role: str = "owner", uid: str = "",
) -> dict:
    if kind == "workstation":
        full = (root.rstrip("/") + "/" + path) if root else path
        res = _operator_exec("operator_write_file", {"path": full, "content": content, "force": True, "_user_id": uid})
        if res.get("status") != "ok":
            raise HTTPException(status_code=502, detail=str(res.get("error") or "operator-write fejlede"))
        return {"status": "ok", "path": full}

    roots = _allowed_roots(role, uid)
    base = roots.get(root)
    if base is None:
        raise HTTPException(status_code=403, detail=f"root '{root}' ikke tilladt for rollen")
    candidate = (base / path).resolve()
    if not str(candidate).startswith(str(base)):
        raise HTTPException(status_code=403, detail="path uden for jail")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(content, encoding="utf-8")
    return {"status": "ok", "path": path}


@router.get("/active-file")
async def chat_active_file() -> dict:
    """Live: den sti Jarvis senest læste/skrev (file-tree live-highlight). Desk
    poller dette når fil-træet er åbent og markerer filen. Pr. bruger."""
    import asyncio
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or "owner"
    rec = await asyncio.to_thread(_active_file_sync, uid)
    return rec or {"path": "", "op": "", "ts": None}


def _active_file_sync(uid: str) -> dict | None:
    from core.services.active_file_store import get_active_file
    return get_active_file(uid)


class _OpenExternalBody(BaseModel):
    root: str = ""
    path: str
    kind: str = "container"


@router.post("/open-external")
async def chat_open_external(body: _OpenExternalBody) -> dict:
    """"Åbn i editor" for workstation-filer: åbn i brugerens lokale OS-editor via
    xdg-open over operator-broen. Container håndteres af in-app editoren i stedet."""
    import asyncio
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or ""
    role = _resolve_role(uid)
    return await asyncio.to_thread(_open_external_sync, body.path, body.root, body.kind, role, uid)


def _open_external_sync(
    path: str, root: str, kind: str, role: str = "owner", uid: str = "",
) -> dict:
    import shlex
    if kind != "workstation":
        raise HTTPException(status_code=400, detail="open-external er kun for workstation (container bruger in-app editor)")
    full = (root.rstrip("/") + "/" + path) if root else path
    res = _operator_exec("operator_bash", {"command": f"xdg-open {shlex.quote(full)}", "_user_id": uid})
    if res.get("status") != "ok":
        raise HTTPException(status_code=502, detail=str(res.get("error") or "xdg-open fejlede"))
    return {"status": "ok", "path": full}


class _CommitMsgBody(BaseModel):
    root: str = ""
    path: str
    content: str
    kind: str = "container"


def _file_diff_sync(root: str, path: str, new_content: str, role: str, uid: str) -> tuple[str, int, int, bool]:
    """Unified diff (gammelt indhold vs. nyt) for en jailet container-fil.
    Returnerer (diff_tekst, added, removed, er_ny_fil)."""
    import difflib
    roots = _allowed_roots(role, uid)
    base = roots.get(root)
    if base is None:
        raise HTTPException(status_code=403, detail=f"root '{root}' ikke tilladt for rollen")
    candidate = (base / path).resolve()
    if not str(candidate).startswith(str(base)):
        raise HTTPException(status_code=403, detail="path uden for jail")
    is_new = not candidate.is_file()
    old = "" if is_new else candidate.read_text(encoding="utf-8", errors="replace")
    diff_lines = list(difflib.unified_diff(old.splitlines(), new_content.splitlines(), lineterm="", n=2))
    added = sum(1 for ln in diff_lines if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in diff_lines if ln.startswith("-") and not ln.startswith("---"))
    return "\n".join(diff_lines[:240]), added, removed, is_new


@router.post("/file/commit-message")
async def chat_commit_message(body: _CommitMsgBody) -> dict:
    """Auto-genereret (redigerbar) commit-besked til "Gem & commit". Bruger lokal
    ollama (privat-sikker — repo-kode må ALDRIG til fri/cloud-model) med en
    diff-template som fallback. Blokerende → to_thread."""
    import asyncio
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or ""
    role = _resolve_role(uid)
    return await asyncio.to_thread(_commit_message_sync, body.path, body.root, body.content, role, uid)


def _commit_message_sync(path: str, root: str, content: str, role: str, uid: str) -> dict:
    diff, added, removed, is_new = _file_diff_sync(root, path, content, role, uid)
    base_name = path.rsplit("/", 1)[-1]
    template = f"{'add' if is_new else 'update'} {base_name} (+{added} −{removed})"
    if not diff.strip():
        return {"message": template, "auto": True}
    try:
        from core.memory.inner_llm_enrichment import (
            _resolve_ollama_fallback_target, _call_ollama_chat,
        )
        tgt = _resolve_ollama_fallback_target()
        if tgt and tgt.get("model"):
            sys = (
                "Du skriver KORTE git commit-beskeder på dansk i imperativ, ÉN linje, "
                "under 72 tegn, ingen anførselstegn eller punktum. Svar KUN med beskeden."
            )
            usr = f"Fil: {path}\nÆndringer (unified diff):\n{diff[:3000]}"
            txt = _call_ollama_chat(
                model=str(tgt.get("model") or ""), base_url=str(tgt.get("base_url") or ""),
                system_prompt=sys, user_message=usr, timeout=8,
            )
            if txt:
                msg = txt.strip().splitlines()[0].strip().strip('"').strip()[:120]
                if msg:
                    return {"message": msg, "auto": True}
    except Exception:
        pass
    return {"message": template, "auto": True}


class _CommitBody(BaseModel):
    root: str = ""
    path: str
    content: str
    message: str
    kind: str = "container"


@router.post("/file/commit")
async def chat_commit_file(body: _CommitBody) -> dict:
    """"Gem & commit": skriv filen + git add/commit på den AKTUELLE branch (ingen
    push). KUN repo-root (git findes kun der) og OWNER. Blokerende → to_thread."""
    import asyncio
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or ""
    if uid:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(str(uid))
        if not u or getattr(u, "role", "") != "owner":
            raise HTTPException(status_code=403, detail="owner only")
    role = _resolve_role(uid)
    return await asyncio.to_thread(_commit_file_sync, body.path, body.root, body.content, body.message, role, uid)


def _commit_file_sync(path: str, root: str, content: str, message: str, role: str, uid: str) -> dict:
    import subprocess
    if root != "repo":
        raise HTTPException(status_code=400, detail="commit kun for repo-root (git findes kun der)")
    roots = _allowed_roots(role, uid)
    base = roots.get("repo")
    if base is None:
        raise HTTPException(status_code=403, detail="repo ikke tilladt for rollen")
    candidate = (base / path).resolve()
    if not str(candidate).startswith(str(base)):
        raise HTTPException(status_code=403, detail="path uden for jail")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(content, encoding="utf-8")
    repo = str(base)
    msg = (message or "").strip() or f"update {path}"

    def _git(*a: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, timeout=20)

    add = _git("add", "--", path)
    if add.returncode != 0:
        raise HTTPException(status_code=500, detail=f"git add fejlede: {add.stderr[:200]}")
    cm = _git("commit", "-m", msg, "--", path)
    if cm.returncode != 0:
        out = (cm.stdout or "") + (cm.stderr or "")
        if "nothing to commit" in out or "no changes added" in out:
            return {"status": "nochange", "message": msg}
        raise HTTPException(status_code=500, detail=f"git commit fejlede: {out[:200]}")
    sha = _git("rev-parse", "--short", "HEAD").stdout.strip()
    return {"status": "ok", "sha": sha, "message": msg}


class _CommitAllBody(BaseModel):
    target: dict = {"kind": "container", "root": "repo"}
    message: str = ""


class _CreatePrBody(BaseModel):
    target: dict = {"kind": "container", "root": "repo"}
    title: str = ""
    body: str = ""


def _owner_repo_base(root: str) -> Path:
    """Validér owner + repo-root og returnér repo-stien. Deler vagt-logik med
    commit-file: KUN owner, KUN repo-root (git findes der)."""
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or ""
    if uid:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(str(uid))
        if not u or getattr(u, "role", "") != "owner":
            raise HTTPException(status_code=403, detail="owner only")
    if root != "repo":
        raise HTTPException(status_code=400, detail="kun repo-root (git findes der)")
    base = _allowed_roots(_resolve_role(uid), uid).get("repo")
    if base is None:
        raise HTTPException(status_code=403, detail="repo ikke tilladt for rollen")
    return base


def _git_target_uid(target: dict) -> tuple[str, str]:
    """Validér target + returnér (container_repo_sti, uid). Rolle-gate:
    container → owner-only (server-repo); workstation → ejeren af broen (uid)."""
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or ""
    if (target or {}).get("kind") == "container":
        base = _owner_repo_base("repo")  # owner-gate + repo-sti
        return (str(base), uid)
    return ("", uid)  # workstation: git_actions bruger target.root via broen


@router.post("/git/commit-all")
async def chat_commit_all(body: _CommitAllBody) -> dict:
    """Commit ALLE ændringer (git add -A + commit). Rolle-aware: container=owner+
    server-repo (subprocess), workstation=brugerens bro. Blokerende → to_thread."""
    import asyncio
    from core.services import git_actions
    repo, uid = _git_target_uid(body.target)
    return await asyncio.to_thread(git_actions.commit_all, body.target, repo, uid, body.message)


@router.post("/git/create-pr")
async def chat_create_pr(body: _CreatePrBody) -> dict:
    """Opret pull request: commit → branch (hvis på default) → push → PR via
    GitHub-OAuth-API (primært) ellers gh CLI. Rolle-aware. Blokerende → to_thread.

    BEMÆRK: udadvendt handling — kaldes KUN når brugeren selv trykker på knappen
    i appen (per-handling-godkendelse)."""
    import asyncio
    from core.services import git_actions
    repo, uid = _git_target_uid(body.target)
    return await asyncio.to_thread(git_actions.create_pr, body.target, repo, uid, body.title, body.body)


def _operator_exec(name: str, args: dict) -> dict:
    """Kør et operator-tool via simple_tools (router'er til brugerens bridge).
    Seam til test-mock (workstation fil-træ)."""
    from core.tools.simple_tools import execute_tool
    return execute_tool(name, args) or {}


@router.get("/tree")
async def chat_tree(kind: str = "container", root: str = "", path: str = "") -> dict:
    """Mappe-listing til Code-mode fil-træ. Blokerende fs/bro-kald offloades til tråd
    (--workers 1 frys-fælde: ellers fryser hele API'et og tree timer ud for BEGGE
    modes — observeret 2026-06-15). Server-roots er rolle-scopede."""
    import asyncio
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or ""
    role = _resolve_role(uid)
    return await asyncio.to_thread(_tree_sync, kind, root, path, role, uid)


def _tree_sync(kind: str, root: str, path: str, role: str = "owner", uid: str = "") -> dict:
    """Container: navngivne rolle-scopede roots, path-jailed. Workstation: via broen."""
    if kind == "container":
        roots = _allowed_roots(role, uid)
        base = roots.get(root)
        if base is None:
            raise HTTPException(status_code=403, detail=f"root '{root}' ikke tilladt for rollen")
        target = (base / path).resolve() if path else base
        if not str(target).startswith(str(base)):
            raise HTTPException(status_code=403, detail="path uden for jail")
        if not target.is_dir():
            raise HTTPException(status_code=404, detail="ikke en mappe")
        entries = []
        for p in sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if p.name.startswith(".") or p.name in ("__pycache__", "node_modules"):
                continue
            entries.append({"name": p.name, "kind": "dir" if p.is_dir() else "file"})
        return {"entries": entries}

    if kind == "workstation":
        full = (root.rstrip("/") + "/" + path).rstrip("/") if path else root
        res = _operator_exec("operator_list_dir", {"path": full, "_user_id": uid})
        if res.get("status") != "ok":
            raise HTTPException(status_code=502, detail=str(res.get("error") or res.get("reason") or "operator-list fejlede"))
        # _run_operator_async pakker bro-svaret i {"status","result"}.
        # operator_list_dir_async returnerer en liste af {name, type, size} —
        # type er "file"|"dir"|"symlink" (IKKE is_dir). Symlink behandles som fil.
        entries = [
            {"name": e.get("name") or "", "kind": "dir" if e.get("type") == "dir" else "file"}
            for e in (res.get("result") or [])
            if e.get("name") and not str(e.get("name")).startswith(".")
        ]
        return {"entries": entries}

    raise HTTPException(status_code=400, detail="ukendt kind")


def _parse_git_status(branch_out: str, porcelain_out: str, numstat_out: str) -> dict:
    """Parse git-output → {branch, dirty, added, removed}."""
    branch = (branch_out or "").strip().splitlines()[0].strip() if branch_out.strip() else ""
    dirty = len([ln for ln in (porcelain_out or "").splitlines() if ln.strip()])
    added = removed = 0
    for ln in (numstat_out or "").splitlines():
        parts = ln.split("\t")
        if len(parts) >= 2:
            try:
                added += int(parts[0]); removed += int(parts[1])
            except ValueError:
                pass  # binære filer giver "-" — ignorér
    return {"branch": branch, "dirty": dirty, "added": added, "removed": removed}


_GIT_NONE = {"branch": "", "dirty": 0, "added": 0, "removed": 0, "is_git": False}


def _git_status_sync(kind: str, root: str, uid: str = "") -> dict:
    """BLOKERENDE git-opsamling — KØRES I TRÅD (asyncio.to_thread) så uvicorn-
    worker'en (--workers 1) ikke fryser på subprocess/bro-kald."""
    if kind == "workstation":
        if not root.strip():
            return dict(_GIT_NONE)
        cmd = (
            f'git -C "{root}" rev-parse --abbrev-ref HEAD 2>/dev/null; echo "@@@"; '
            f'git -C "{root}" status --porcelain 2>/dev/null; echo "@@@"; '
            f'git -C "{root}" diff --numstat HEAD 2>/dev/null'
        )
        res = _operator_exec("operator_bash", {"command": cmd, "_user_id": uid})
        # operator_bash-svaret pakkes af broen som {"status","result":{"stdout",...}}
        # — stdout ligger UNDER result, ikke på toppen (jf. git_actions._run). Det
        # gamle res.get("stdout") var altid None → is_git=False → hele git-sektionen
        # skjult i workstation-mode selvom commit/PR faktisk virkede.
        r = res.get("result") or {}
        out = str(r.get("stdout") or "") if res.get("status") == "ok" else ""
        segs = out.split("@@@")
        if len(segs) < 3 or not segs[0].strip():
            return dict(_GIT_NONE)
        d = _parse_git_status(segs[0], segs[1], segs[2])
        d["is_git"] = True
        return d

    import subprocess
    repo = str(_repo_root())
    def _git(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", "-C", repo, *args], capture_output=True, text=True, timeout=8,
            ).stdout
        except Exception:
            return ""
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if not branch.strip():
        return dict(_GIT_NONE)
    d = _parse_git_status(branch, _git("status", "--porcelain"), _git("diff", "--numstat", "HEAD"))
    d["is_git"] = True
    return d


@router.get("/git-status")
async def chat_git_status(kind: str = "container", root: str = "") -> dict:
    """Git-state for det aktive workspace (header-chip i code-mode). Det blokerende
    arbejde (subprocess/bro) offloades til en tråd så event-loop'en ikke fryser."""
    import asyncio
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or ""
    return await asyncio.to_thread(_git_status_sync, kind, root, uid)


@router.get("/workspace-trust")
async def get_workspace_trust(kind: str = "container", root: str = "") -> dict:
    """Er det aktuelle workspace betroet for den indloggede bruger?"""
    from core.identity.workspace_context import current_user_id
    from core.services.workspace_trust import is_trusted
    uid = current_user_id() or None
    return {"kind": kind, "root": root, "trusted": is_trusted(uid, kind, root)}


class WorkspaceTrustRequest(BaseModel):
    kind: str = "container"
    root: str = ""
    trusted: bool = True


@router.post("/workspace-trust")
async def set_workspace_trust(request: WorkspaceTrustRequest) -> dict:
    """Markér/afmarkér et workspace som betroet (skrive/exec-gate i code-mode)."""
    from core.identity.workspace_context import current_user_id
    from core.services.workspace_trust import set_trusted
    if not request.root.strip():
        raise HTTPException(status_code=400, detail="root må ikke være tom")
    uid = current_user_id() or None
    trusted = set_trusted(uid, request.kind, request.root, request.trusted)
    return {"kind": request.kind, "root": request.root, "trusted": trusted}


class ChatStreamRequest(BaseModel):
    message: str = ""
    session_id: str = ""
    attachment_ids: list[str] = []
    approval_mode: str = "ask"  # "ask" | "trust"
    # Thinking mode for reasoning-capable models (deepseek-v4-flash et al.).
    # "fast" = no thinking (intuitive answer)
    # "think" = default thinking (balanced)
    # "deep" = max reasoning effort (slowest, hardest problems)
    # Ignored for models that don't support thinking parameters.
    thinking_mode: str = "think"
    # UI-mode: "chat" begrænser værktøjer til en samtale-allowlist; "code"
    # låser kode-tools op (tool_scope="code"). "" = ubegrænset (rolle-filter
    # gælder stadig). Sættes af jarvis-desk pr. mode.
    mode: str = ""
    # Code-mode workspace (hvor Jarvis' fil-tools arbejder).
    workspace_kind: str = ""   # "container" | "workstation" | ""
    workspace_root: str = ""
    # Rolle-bevidst model/provider-valg (2026-06-13). provider_choice er KUN
    # for owner ("deepseek"|"ollama"); members tvinges server-side til ollama.
    # model = konkret model-id (owner kan vælge enhver ollama-model); members
    # clampes til deepseek-v4-flash/pro:cloud ud fra om "pro" indgår.
    provider_choice: str = ""
    model: str = ""
    # Path B (server-owned code-lane transcript, LOCAL tool execution). When true AND
    # the run is in code scope, tool_calls are emitted to the jarvis-code client and
    # executed there (via the local_tool_broker) instead of server-side. Default OFF →
    # byte-identical to existing clients.
    local_tool_exec: bool = False


def _resolve_visible_target(uid: str | None, provider_choice: str, model: str) -> tuple[str, str]:
    """Rolle-bevidst (provider, model)-override for en visible-run.

    - member → ALTID ollama + deepseek-v4-flash:cloud (eller -pro:cloud hvis
      model'en indeholder "pro"). provider_choice ignoreres (kan ikke eskalere).
    - owner  → honorér provider_choice ("deepseek"|"ollama") + valgfri model.
      Tom/ukendt provider_choice → ("","") = fald tilbage til global config.

    Returnerer ("","") når der ikke skal overrides (global config bruges).
    Ingen uid = lokal/owner-konvention (matcher cowork _role_owner).
    """
    role = "owner"
    if uid:
        try:
            from core.identity.users import find_user_by_discord_id
            u = find_user_by_discord_id(str(uid))
            role = (getattr(u, "role", "") or "member") if u else "member"
        except Exception:
            role = "member"
    if role != "owner":
        is_pro = "pro" in (model or "").lower()
        return ("ollama", "deepseek-v4-pro:cloud" if is_pro else "deepseek-v4-flash:cloud")
    # Owner: honorér ENHVER visible-klar provider (2026-06-13 — udvidet fra
    # kun deepseek/ollama). Den valgte (provider, model) sendes igennem som
    # override; tom provider → global config. Backenden kan eksekvere alle
    # providers i _VISIBLE_CAPABLE_PROVIDERS (openai-compat + ollama/copilot/codex).
    prov = (provider_choice or "").strip().lower()
    if not prov:
        return ("", "")
    m = (model or "").strip()
    if not m:
        if prov == "ollama":
            m = "deepseek-v4-flash:cloud"
        elif prov == "deepseek":
            from core.runtime.settings import load_settings
            m = load_settings().visible_model_name
    # MIDLERTIDIG bro (2026-06-21): desk-composer-regression viser kun gpt-4/gpt-4.1
    # for github-copilot — begge cappet til ~12k kontekst, kan IKKE rumme Jarvis'
    # ~130k prompt → HTTP 400. Substituér disse små Copilot-modeller til den globale
    # store model (fx gpt-5-mini) indtil composer-vælgeren viser hele kataloget igen.
    if prov in ("github-copilot", "copilot") and m.lower().startswith("gpt-4"):
        from core.runtime.settings import load_settings as _ls_bridge
        _big = (_ls_bridge().visible_model_name or "").strip()
        if _big and not _big.lower().startswith("gpt-4"):
            m = _big
    return (prov, m)


def _visible_capable_providers() -> set[str]:
    """Providers som stream_visible_model faktisk kan eksekvere til chat."""
    try:
        from core.services.cheap_provider_runtime import _OPENAI_COMPATIBLE_PROVIDERS
        base = set(_OPENAI_COMPATIBLE_PROVIDERS)
    except Exception:
        base = {"groq", "nvidia-nim", "openrouter", "mistral", "sambanova", "opencode", "deepseek"}
    return base | {"ollama", "github-copilot", "openai-codex"}


def _list_visible_providers_sync() -> list[dict]:
    """{id, models[]} for hver visible-klar provider med enabled modeller i
    provider_router. Ollama suppleres med den live /api/tags-liste."""
    capable = _visible_capable_providers()
    by_provider: dict[str, list[str]] = {}
    try:
        from core.runtime.provider_router import load_provider_router_registry
        reg = load_provider_router_registry() or {}
        for m in reg.get("models", []) or []:
            if not isinstance(m, dict):
                continue
            prov = str(m.get("provider") or "").strip()
            mdl = str(m.get("model") or "").strip()
            if prov in capable and mdl and m.get("enabled"):
                by_provider.setdefault(prov, [])
                if mdl not in by_provider[prov]:
                    by_provider[prov].append(mdl)
    except Exception:
        pass
    # Ollama: merge live container-liste (modeller pulles løbende).
    try:
        live = _list_ollama_models_sync()
        ol = by_provider.setdefault("ollama", [])
        for mdl in live:
            if mdl and mdl not in ol:
                ol.append(mdl)
    except Exception:
        pass
    # Readiness-filter: vis KUN providers der reelt er auth-klare for den
    # synlige lane (undgå tavse run-fejl). De cheap-only providers (groq,
    # mistral...) er IKKE klar under visible-profilen → udelades fra chat-
    # vælgeren (de er til swarm/council). copilot tjekkes mod den profil der
    # faktisk har dens creds (kan ligge under "copilot", ikke "default").
    try:
        from core.runtime.provider_router import _credentials_ready
        from core.runtime.settings import load_settings
        prof = (load_settings().visible_auth_profile or "default")
        ready: set[str] = {"ollama"}
        for p in list(by_provider):
            try:
                if _credentials_ready(provider=p, auth_profile=prof):
                    ready.add(p)
            except Exception:
                pass
        if "github-copilot" in by_provider:
            try:
                from core.auth.profiles import get_provider_state
                from core.services.visible_model import _resolve_copilot_profile
                rp = _resolve_copilot_profile(prof)
                if get_provider_state(profile=rp, provider="github-copilot") is not None:
                    ready.add("github-copilot")
            except Exception:
                pass
        by_provider = {p: ms for p, ms in by_provider.items() if p in ready}
    except Exception:
        pass
    # github-copilot: kun gpt-4o-familien virker via /chat/completions-stien
    # (verificeret 2026-06-13). claude-* kræver plan-enablement; gpt-5.x kræver
    # /responses-endpointet — begge fejler tavst. Filtrér til det der virker, så
    # vælgeren ikke tilbyder døde modeller. (GPT-5.x: brug openai-codex i stedet.)
    if "github-copilot" in by_provider:
        working = [m for m in by_provider["github-copilot"] if "gpt-4o" in m.lower()]
        if working:
            by_provider["github-copilot"] = working
        else:
            by_provider.pop("github-copilot", None)
    return [{"id": p, "models": sorted(ms)} for p, ms in sorted(by_provider.items()) if ms]


def _list_ollama_models_sync() -> list[str]:
    import json as _json
    import urllib.request as _ur
    with _ur.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as r:
        data = _json.loads(r.read().decode("utf-8"))
    return [m.get("name") for m in data.get("models", []) if m.get("name")]


@router.get("/ollama-models")
async def chat_ollama_models() -> dict:
    """Tilgængelige ollama-modeller på containeren (OWNER-only).

    Bruges af composer'ens dynamiske model-vælger så owner kan teste nye
    modeller efterhånden som de pulles. Members ser den aldrig (UI-gated +
    server-gated). Blokerende urlopen → asyncio.to_thread (--workers 1).
    """
    import asyncio
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    if uid:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(str(uid))
        if not u or getattr(u, "role", "") != "owner":
            raise HTTPException(status_code=403, detail="owner only")
    try:
        models = await asyncio.to_thread(_list_ollama_models_sync)
        return {"models": models}
    except Exception as exc:
        return {"models": [], "error": str(exc)[:200]}


class _TerminalRunBody(BaseModel):
    command: str
    cwd: str = ""


def _terminal_run_sync(command: str, cwd: str) -> dict:
    """BLOKERENDE server-side kommando-kørsel — KØRES I TRÅD. cwd contained til
    repo-roden (ingen escape via .. eller absolut sti udenfor repo)."""
    import os
    import subprocess
    repo = str(_repo_root())
    raw = (cwd or "").strip()
    if raw and os.path.isabs(raw):
        target = os.path.abspath(raw)
    else:
        target = os.path.abspath(os.path.join(repo, raw)) if raw else repo
    if not (target == repo or target.startswith(repo + os.sep)) or not os.path.isdir(target):
        target = repo
    try:
        p = subprocess.run(["bash", "-lc", command], cwd=target,
                           capture_output=True, text=True, timeout=60)
        return {"stdout": p.stdout, "stderr": p.stderr, "exit_code": p.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "timeout (60s)", "exit_code": -1}
    except Exception as exc:
        return {"stdout": "", "stderr": str(exc)[:500], "exit_code": -1}


@router.post("/terminal/run")
async def chat_terminal_run(body: _TerminalRunBody) -> dict:
    """Code-mode terminal-rude (§17), container-side: kør én kommando server-side
    i repo-workspace (OWNER-only; cwd contained til repo). Blokerende subprocess →
    asyncio.to_thread (--workers 1 frys-fælde)."""
    import asyncio
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    if uid:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(str(uid))
        if not u or getattr(u, "role", "") != "owner":
            raise HTTPException(status_code=403, detail="owner only")
    cmd = (body.command or "").strip()
    if not cmd:
        return {"stdout": "", "stderr": "", "exit_code": 0}
    return await asyncio.to_thread(_terminal_run_sync, cmd, body.cwd)


@router.get("/visible-providers")
async def chat_visible_providers() -> dict:
    """Alle visible-klare providers + deres modeller (OWNER-only).

    Lader composeren eksponere hele paletten (groq, mistral, gemini-via-compat,
    nvidia-nim, openrouter, sambanova, opencode, deepseek, ollama, github-
    copilot...) i stedet for kun deepseek/ollama. Blokerende I/O → to_thread.
    """
    import asyncio
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    if uid:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(str(uid))
        if not u or getattr(u, "role", "") != "owner":
            raise HTTPException(status_code=403, detail="owner only")
    try:
        providers = await asyncio.to_thread(_list_visible_providers_sync)
        return {"providers": providers}
    except Exception as exc:
        return {"providers": [], "error": str(exc)[:200]}


class ChatSessionCreateRequest(BaseModel):
    title: str = "New chat"
    workspace_kind: str = ""   # "container" | "workstation" | "" (Code mode)
    workspace_root: str = ""


class ChatSessionRenameRequest(BaseModel):
    title: str


@router.get("/sessions")
async def chat_sessions() -> dict:
    """List chat sessions.

    When the request carries an X-JarvisX-User header (set by the
    JarvisX desktop app), only sessions that user has actually
    participated in are returned — this is what keeps Bjørn's and
    Mikkel's chat histories from bleeding into each other in the
    sidebar. Webchat without the header returns the unfiltered list,
    same as before.
    """
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    return {"items": list_chat_sessions(user_id=uid)}


# Bemærk: defineres FØR /sessions/{session_id} så "search" ikke fanges som id.
@router.get("/sessions/search")
async def chat_search_sessions(q: str = "", limit: int = 30) -> dict:
    """Søg sessioner på titel + besked-indhold. Scopes pr. bruger som
    /sessions. Returnerer {items: [{session_id, title, snippet, updated_at}]}."""
    from core.identity.workspace_context import current_user_id
    from core.services.chat_sessions import search_chat_sessions
    uid = current_user_id() or None
    return {"items": search_chat_sessions(q, user_id=uid, limit=limit)}


@router.get("/active-runs")
async def chat_active_runs() -> dict:
    """Sessioner med et aktivt visible-run lige nu (#8 — autonome/baggrunds-runs).

    Bruges af Sidebar til at vise en arbejds-indikator på en session der ikke er
    fremme. Højst ét aktivt visible-run ad gangen. Friskheds-guard mod phantom-
    state (et run der døde uden at rydde op): kun med hvis < 10 min gammelt og
    ikke cancelled."""
    # Autoritativ liveness via run_follow-bufferen (SAMME proces som de afkoblede
    # runs + dette endpoint) — paalideligt for detached A3-runs og rydder
    # OEJEBLIKKELIGT op naar et run afsluttes (end_follow). Erstatter det DELTE
    # active-run-heartbeat, der halter cross-proces for detached runs og fik
    # desktop-aktivitetsprikkerne til at haenge (Bjoern 2026-06-18).
    from core.runtime.settings import load_settings
    if load_settings().server_authoritative_runs:
        import core.services.run_event_log as rel
        sids: list[str] = []
        for rid in rel.live_run_ids():
            sid = rel.session_for_run(rid)
            if sid and sid not in sids:
                sids.append(sid)
        return {"session_ids": sids}
    # FLAG OFF -> run_follow.live_sessions (uaendret)
    from core.services.run_follow import live_sessions
    try:
        return {"session_ids": live_sessions()}
    except Exception:
        return {"session_ids": []}


@router.post("/sessions/{session_id}/cancel-active")
async def chat_cancel_active(session_id: str) -> dict:
    """Afbryd det run der kører for sessionen (mobil/desk stop-knap naar klienten
    ikke selv streamer runnet — fx efter baggrund hvor serveren stadig arbejder)."""
    from core.services.visible_runs import (
        _get_active_visible_run_state,
        cancel_visible_run,
    )
    sid = (session_id or "").strip()
    try:
        st = _get_active_visible_run_state() or {}
        if str(st.get("session_id") or "") == sid:
            rid = str(st.get("run_id") or "")
            if rid:
                return {"cancelled": bool(cancel_visible_run(rid)), "run_id": rid}
    except Exception:
        pass
    return {"cancelled": False}


@router.get("/runs/{run_id}/subscribe")
async def chat_run_subscribe(run_id: str, from_idx: int = 0):
    """Gen-abonner paa et server-autoritativt run fra et offset (mobil-reconnect
    efter socket-drop). Catch-up fra from_idx + live-hale til done. 404 hvis
    run_id ukendt/pruned -> klient falder tilbage til sessions.select."""
    import asyncio
    from fastapi import HTTPException
    from fastapi.responses import StreamingResponse
    import core.services.run_event_log as rel

    if rel.session_for_run(run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")

    async def _gen():
        import time as _xt
        from apps.api.jarvis_api.sse_v2_events import Ping as _Ping
        rel.subscriber_opened(run_id)
        saw_stop = False
        # Klient-keepalive: egen ping hvert _PING_GAP_S i content-gap, så klientens
        # 90s ping-watchdog ikke fyrer mens et langt run/tool-runde er stille
        # (detached-pings droppes fra relay-bufferen → når aldrig klienten). Se chat_stream_v2.
        _PING_GAP_S = 5.0
        _last_emit = _xt.monotonic()
        try:
            idx = max(0, int(from_idx))
            empty = 0
            while True:
                frames, done = rel.read(run_id, idx)
                for f in frames:
                    idx += 1
                    if "message_stop" in f:
                        saw_stop = True
                    yield f
                    _last_emit = _xt.monotonic()
                if done:
                    # Terminal-garanti: run done UDEN message_stop → syntetisér (ellers
                    # hænger en re-subscriber/reattach på 'working'). Se chat_stream_v2.
                    if not saw_stop:
                        yield rel.synthetic_terminal_frame(run_id, reason="run_done_no_stop")
                    rel.mark_consumed(run_id)
                    break
                if frames:
                    empty = 0
                else:
                    empty += 1
                    if (_xt.monotonic() - _last_emit) >= _PING_GAP_S:
                        yield _Ping().to_sse_line()
                        _last_emit = _xt.monotonic()
                    if empty > 300 and rel.is_live(run_id):
                        empty = 0  # run lever stadig (langsom) → bliv ved (se chat_stream_v2)
                    elif empty > 300:
                        # H1/G6: syntetisk terminal-frame + subscriber_timeout-nerve.
                        yield rel.synthetic_terminal_frame(
                            run_id, reason="run_subscribe_idle"
                        )
                        break
                await asyncio.sleep(0.08)
        finally:
            rel.subscriber_closed(run_id)

    return StreamingResponse(_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Run-Id": run_id})


@router.get("/sessions/{session_id}/live")
async def chat_session_live(session_id: str):
    """Attach til sessionens aktive run fra offset 0 (cross-device + foreground-
    attach). 204 hvis intet aktivt run."""
    import asyncio
    from fastapi import Response
    from fastapi.responses import StreamingResponse
    import core.services.run_event_log as rel

    run_id = rel.active_run_for_session(session_id)
    if not run_id:
        return Response(status_code=204)

    async def _gen():
        import time as _xt
        from apps.api.jarvis_api.sse_v2_events import Ping as _Ping
        rel.subscriber_opened(run_id)
        saw_stop = False
        _PING_GAP_S = 5.0          # klient-keepalive i content-gap (se chat_stream_v2)
        _last_emit = _xt.monotonic()
        try:
            idx = 0
            empty = 0
            while True:
                frames, done = rel.read(run_id, idx)
                for f in frames:
                    idx += 1
                    if "message_stop" in f:
                        saw_stop = True
                    yield f
                    _last_emit = _xt.monotonic()
                if done:
                    if not saw_stop:
                        yield rel.synthetic_terminal_frame(
                            run_id, session_id, reason="run_done_no_stop")
                    rel.mark_consumed(run_id)
                    break
                if frames:
                    empty = 0
                else:
                    empty += 1
                    if (_xt.monotonic() - _last_emit) >= _PING_GAP_S:
                        yield _Ping().to_sse_line()
                        _last_emit = _xt.monotonic()
                    if empty > 300 and rel.is_live(run_id):
                        empty = 0  # run lever stadig (langsom) → bliv ved (se chat_stream_v2)
                    elif empty > 300:
                        # H1/G6: syntetisk terminal-frame + subscriber_timeout-nerve.
                        yield rel.synthetic_terminal_frame(
                            run_id, session_id, reason="session_live_idle"
                        )
                        break
                await asyncio.sleep(0.08)
        finally:
            rel.subscriber_closed(run_id)

    return StreamingResponse(_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Run-Id": run_id})


@router.get("/sessions/{session_id}/follow")
async def chat_session_follow(session_id: str):
    """Token-stream det aktive autonome run i sessionen (desk-pickup af wakeup).

    Poller run_follow-bufferen og videresender v2-SSE-frames: catch-up fra start
    (så en sen attach stadig får hele svaret) + live-tail indtil done. Desk'en
    fodrer dem ind i SAMME streamReducer → renderer token-for-token i stedet for
    at "dumpe" den færdige besked ind (Bjørn 2026-06-13)."""
    import asyncio

    from fastapi.responses import StreamingResponse

    from core.services.run_follow import _snapshot
    import core.services.run_event_log as rel

    async def _gen():
        idx = 0
        empty_polls = 0
        saw_stop = False
        while True:
            frames, done = _snapshot(session_id, idx)  # hurtig in-memory + lock
            for f in frames:
                idx += 1
                if "message_stop" in f:
                    saw_stop = True
                yield f
            if done:
                if not saw_stop:
                    run_id = rel.active_run_for_session(session_id) or ""
                    yield rel.synthetic_terminal_frame(
                        run_id, session_id, reason="run_done_no_stop")
                break
            if frames:
                empty_polls = 0
            else:
                empty_polls += 1
                if empty_polls > 150:  # ~12s uden frames → intet aktivt run, giv op
                    # H1/G6 (§11.2 4. site): syntetisk terminal-frame + nerve så en
                    # desk-follow ikke hænger i 'working' når runnet aldrig dukker op.
                    run_id = rel.active_run_for_session(session_id) or ""
                    yield rel.synthetic_terminal_frame(
                        run_id, session_id, reason="session_follow_idle"
                    )
                    break
            await asyncio.sleep(0.08)

    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.get("/context-info")
async def chat_context_info() -> dict:
    """Kontekst-tærskler til composer-ringen (#9). Kun ægte config-tal:
    autocompact-punktet (context_compact_threshold_tokens). Klienten holder
    selv tælleren (usage.input + cache fra streamen)."""
    from core.runtime.settings import load_settings
    s = load_settings()
    # 2026-07-18: ringen måler nu mod ATTENTION-budgettet (den PRIMÆRE trigger), så den
    # rammer ~100% netop når compaction fyrer — ikke mod de gamle 130k som aldrig blev nået.
    return {
        "compact_at": int(getattr(s, "context_attention_budget_tokens", 35_000) or 35_000),
        "run_compact_at": int(s.context_run_compact_threshold_tokens or 0),
    }


@router.get("/context-usage")
async def chat_context_usage(
    session_id: str = "", provider: str = "", model: str = "",
) -> dict:
    """ÆGTE kontekst-fyld for en session — backend-autoritativt.

    Returnerer `tokens` = estimat af det FAKTISKE transcript der sendes til modellen siden
    sidste compact (præcis det tal autocompact selv måler mod context_compact_threshold_tokens).
    DERFOR harmonerer ringen med autocompact: den vokser mod loftet og FALDER når compaction
    fyrer — i stedet for den gamle per-tur stream-usage der nulstilledes hver besked.

    Plus `compacting` (baggrunds-compaction kører lige nu) + `compacted` (en summary findes)
    til liveness/compaction-indikatoren over composeren.
    """
    import asyncio

    from core.runtime.settings import load_settings
    s = load_settings()
    # Ringen måler mod attention-budgettet (primær trigger, 2026-07-18) → falder når
    # baggrunds-compaction fyrer ved 35k, i stedet for at snige mod de gamle 130k.
    compact_at = int(getattr(s, "context_attention_budget_tokens", 35_000) or 35_000)

    # System-overhead (stabil prefix: SOUL/IDENTITY/USER/regler/tools) — det FASTE der
    # sendes til modellen udover samtalen. Til tooltip'ens ÆGTE total-tal. Memoiseret
    # (skifter kun ved workspace-edit), self-safe → 0.
    overhead_tokens = await asyncio.to_thread(_system_overhead_tokens, provider, model, session_id)

    tokens = 0
    compacted = False
    if session_id:
        try:
            from core.context.token_estimate import estimate_messages_tokens
            from core.services.prompt_contract import _build_structured_transcript_messages
            msgs = await asyncio.to_thread(
                _build_structured_transcript_messages, session_id, limit=60, include=True,
            )
            tokens = int(estimate_messages_tokens(msgs))
        except Exception:
            tokens = 0
        try:
            from core.services.chat_sessions import get_compact_marker
            compacted = bool(await asyncio.to_thread(get_compact_marker, session_id))
        except Exception:
            compacted = False

    # Model-BEVIDST: det AKTIVE models reelle vindue (glm-5.1 256k / glm-5.2·flash 1M).
    model_window = 0
    if provider or model:
        try:
            from core.services.model_context import model_context_window
            model_window = int(model_context_window(provider, model) or 0)
        except Exception:
            model_window = 0
    effective = min(model_window, compact_at) if model_window > 0 else compact_at

    compacting = False
    try:
        from core.services import prompt_contract as _pc
        compacting = bool(session_id) and session_id in getattr(_pc, "_compact_inflight", set())
    except Exception:
        compacting = False

    return {
        "tokens": tokens,
        "compact_at": compact_at,
        "effective": effective,
        "model_window": model_window,
        "overhead_tokens": overhead_tokens,
        "compacting": compacting,
        "compacted": compacted,
    }


# System-overhead-cache (stabil prefix ændrer sig kun ved workspace-edit → 60s TTL nok).
_overhead_cache: dict[tuple, tuple[float, int]] = {}


def _system_overhead_tokens(provider: str, model: str, session_id: str) -> int:
    """Estimér tokens i den STABILE system-prefix (identitet + regler + tool-katalog) — det
    faste overhead udover samtalen. Memoiseret pr. (provider, model). Self-safe → 0."""
    import time as _t
    key = (str(provider or ""), str(model or ""))
    now = _t.monotonic()
    hit = _overhead_cache.get(key)
    if hit and (now - hit[0]) < 60:
        return hit[1]
    try:
        from core.services.prompt_contract import build_visible_stable_prefix
        from core.context.token_estimate import estimate_tokens
        name = "default"
        try:
            from core.services.chat_sessions import get_session_owner
            from core.identity.users import find_user_by_discord_id
            oid = get_session_owner(session_id) or "" if session_id else ""
            u = find_user_by_discord_id(oid) if oid else None
            if u and getattr(u, "workspace", ""):
                name = u.workspace
        except Exception:
            pass
        prefix = build_visible_stable_prefix(provider=provider, model=model, name=name)
        val = int(estimate_tokens(prefix))
        _overhead_cache[key] = (now, val)
        return val
    except Exception:
        return 0


class _CompactNowBody(BaseModel):
    session_id: str
    focus: str = ""


@router.post("/compact-now")
async def chat_compact_now(body: _CompactNowBody) -> dict:
    """Manuel compaction (som Claude Codes /compact). Udløser den SAMME baggrunds-motor som
    auto-triggeren — round-atomisk 2-trins struktureret summary — men NU, uanset om
    attention-budgettet er nået. Valgfri `focus` styrer hvad summary'en prioriterer.
    Sætter `_compact_inflight` så desk-liveness-linjen tænder. Non-blocking: returnerer straks.
    """
    import threading as _t

    session_id = (body.session_id or "").strip()
    focus = (body.focus or "").strip() or None
    if not session_id:
        return {"started": False, "reason": "missing session_id"}

    from core.services import prompt_contract as _pc
    from core.runtime.settings import load_settings
    s = load_settings()
    low_water = int(getattr(s, "context_attention_low_water_tokens", 15_000) or 15_000)
    keep_recent = int(getattr(s, "context_keep_recent", 20) or 20)

    lock = getattr(_pc, "_compact_inflight_lock", None)
    inflight = getattr(_pc, "_compact_inflight", None)
    if lock is None or inflight is None:
        return {"started": False, "reason": "compaction unavailable"}
    with lock:
        if session_id in inflight:
            return {"started": False, "reason": "already compacting"}
        inflight.add(session_id)
    try:
        _t.Thread(
            target=_pc._run_session_compaction,
            args=(session_id, keep_recent),
            kwargs={"low_water_tokens": low_water, "focus": focus},
            name=f"compact-manual-{session_id[:10]}", daemon=True,
        ).start()
    except Exception as exc:
        with lock:
            inflight.discard(session_id)
        return {"started": False, "reason": f"spawn failed: {exc}"}
    return {"started": True, "reason": "manual", "focus": focus or ""}


@router.get("/session-milestones")
async def chat_session_milestones(session_id: str = "") -> dict:
    """Milepæle (kapitler) til navigations-rail'en — som Claude Code's mark_chapter. Segmenterer
    samtalen i titlede kapitler ankret på user-beskeder, i stedet for ét anker pr. besked. Cached
    + cheap-lane; self-safe → tom liste ved fejl."""
    import asyncio

    if not session_id:
        return {"milestones": []}
    try:
        from core.services.session_milestones import get_session_milestones
        ms = await asyncio.to_thread(get_session_milestones, session_id)
        return {"milestones": ms or []}
    except Exception:
        return {"milestones": []}


@router.get("/model-context")
async def chat_model_context(provider: str = "", model: str = "") -> dict:
    """Ægte context-ring pr. provider/model: modellens vindue + autocompact-punkt
    + det effektive loft (det første der rammer = min). Klienten bruger 'effective'
    som ring-nævner, så ringen er nøjagtig for HVER model (deepseek 1M vs et 64k-
    model fylder forskelligt)."""
    from core.runtime.settings import load_settings
    from core.services.model_context import model_context_window, effective_context_limit
    compact = int(load_settings().context_compact_threshold_tokens or 0)
    window = model_context_window(provider, model)
    effective = effective_context_limit(provider, model, compact)
    return {"window": window, "compact_at": compact, "effective": int(effective)}


@router.post("/sessions")
async def chat_create_session(request: ChatSessionCreateRequest) -> dict:
    """Opret en ny chat-session (valgfrit bundet til et code-mode workspace).
    Returnerer {session: ...}."""
    return {"session": create_chat_session(
        title=request.title,
        workspace_kind=request.workspace_kind or None,
        workspace_root=request.workspace_root or None,
    )}


@router.get("/sessions/{session_id}")
async def chat_session(session_id: str) -> dict:
    """Hent én chat-session ud fra id. 404 hvis den ikke findes; ellers {session: ...}."""
    session = get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"session": session}


@router.put("/sessions/{session_id}/rename")
async def chat_rename_session(session_id: str, request: ChatSessionRenameRequest) -> dict:
    """Omdøb en chat-session til request.title. 404 hvis sessionen ikke findes;
    ellers {session: ...}."""
    session = rename_chat_session(session_id, title=request.title)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"session": session}


@router.delete("/sessions/{session_id}")
async def chat_delete_session(session_id: str) -> dict:
    """Slet en chat-session. 404 hvis den ikke findes; ellers {ok: True, session_id}."""
    if not delete_chat_session(session_id):
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"ok": True, "session_id": session_id}


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    """Legacy/mobil chat-stream-endpoint (v1 SSE). Injicerer commit-enforcement-
    hint ved dirty state, validerer + persisterer bruger-beskeden (stamplet med
    workspace-user_id), håndterer attachment-kontekst, `!override`-kommandoer og
    identity-guard som legacy-SSE-kortslutninger, og starter ellers et
    visible-run streamet som text/event-stream."""
    # ── commit-enforcement-context-inject (Phase C-lite) ────────────────
    # Hvis session har dirty state med 3+ edits siden sidste commit, prepend
    # en hård system-besked til chat-konteksten. Jarvis ser den hver tur
    # indtil han committer. Ikke blokkerende — bare meget højlydt awareness.
    try:
        from core.services import shared_cache as _sc_ce
        from apps.api.jarvis_api.routes.chat import _git_status_sync as _gss_ce
        _sid_ce = str(request.session_id or "default")
        _cnt = _sc_ce.get("commit_enforcement:" + _sid_ce)
        _edits = int(_cnt.get("edits", 0)) if isinstance(_cnt, dict) else 0
        if _edits >= 3:
            _g = _gss_ce("container", "")
            if _g.get("dirty"):
                _hint = (
                    f"\n\n[SYSTEM — commit-enforcement]\n"
                    f"Du har {_edits} mutations-kald siden sidste commit, og "
                    f"branch {_g.get('branch', '?')} er stadig dirty "
                    f"({len(_g.get('modified', []))} ændrede filer). "
                    "Commit FØRST i denne tur før du laver nye mutationer."
                )
                # Prepend uden at ændre request-shape: tilføj til besked-feltet
                # så LLM\'en ser det inline i sin context for denne tur.
                try:
                    request.message = (request.message or "") + _hint  # type: ignore[attr-defined]
                except Exception:
                    pass
    except Exception:
        pass


    session_id = request.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id must be a non-empty string")
    if get_chat_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    print(
        f"[chat/stream] session={session_id[:20]} "
        f"attachment_ids={list(request.attachment_ids or [])} "
        f"message_len={len(request.message)}",
        flush=True,
    )

    # Prepend attachment-direktiv-blok (delt helper — bruges også af v2) så Jarvis
    # ved HVORDAN han ser filen (analyze_image med eksakt sti).
    from apps.api.jarvis_api.routes.attachments import apply_attachment_context
    effective_message = apply_attachment_context(request.message, request.attachment_ids)

    # Reject empty / whitespace-only messages cleanly (400) instead of
    # letting append_chat_message raise a ValueError that becomes a 500.
    # JarvisX UI occasionally sends empty payloads (e.g. accidental enter-
    # press) and we don't want that to look like a server crash.
    if not (effective_message or "").strip():
        raise HTTPException(
            status_code=400,
            detail="message must not be empty or whitespace-only",
        )

    # Stamp user_id from workspace context (resolved by jarvisx_user_routing
    # middleware from the Bearer token's `sub` claim). Without this the
    # message is anonymized in storage → prompt_contract's multi-user
    # speaker prefix can't label it → Jarvis falls back to assuming it's
    # the owner (Bjørn) regardless of who actually typed it.
    from core.identity.workspace_context import current_user_id
    _uid = current_user_id() or None
    append_chat_message(
        session_id=session_id,
        role="user",
        content=effective_message,
        user_id=_uid,
    )

    # Paste-store (spec 2026-07-09): persistér den kompakte reference, men send den
    # FULDE paste-tekst til modellen (flag `paste_inline_to_model`, default ON).
    # Ukendt id → behold referencen (degradér). Se chat_stream_v2 for detaljer.
    try:
        from core.services.paste_store import project_paste_for_model
        model_message = project_paste_for_model(effective_message)
    except Exception:
        model_message = effective_message

    from core.services.notification_bridge import pin_session
    pin_session(session_id)

    # Owner-override (§6.3) i v1/mobil-stien — samme wiring som v2 (kill-switch skal
    # virke fra ALLE klienter, ikke kun desk). `!override <TOTP>` kortsluttes med en
    # legacy-SSE-kvittering (delta+done), ingen LLM-run. Lazy import undgår circular
    # (chat_stream_v2 importerer ChatStreamRequest herfra). Bjørn 2026-06-21.
    from apps.api.jarvis_api.routes.chat_stream_v2 import maybe_handle_override
    _ov = maybe_handle_override(request.message, session_id)
    if _ov is not None:
        _reply = str(_ov.get("reply") or "")
        try:
            append_chat_message(session_id=session_id, role="assistant",
                                content=_reply, user_id=None)
        except Exception:
            pass
        print(f"[chat/stream] override-kommando: session={session_id[:20]} "
              f"ok={_ov.get('ok')} action={_ov.get('action') or _ov.get('reason')}", flush=True)
        from core.services.visible_runs import _sse as _sse_legacy

        def _ov_gen():
            yield _sse_legacy("delta", {"type": "delta", "run_id": "override", "delta": _reply})
            yield _sse_legacy("done", {"type": "done", "run_id": "override",
                                       "status": "completed", "input_tokens": 0, "output_tokens": 0})
        return StreamingResponse(_ov_gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})

    # Normal besked i en ELEVET session → forny override-vinduet (5 min rullende),
    # så det ikke udløber midt i en operator-sekvens (jf. v2-fix). Korrekt session_id.
    try:
        from core.services import override_store as _ovs
        if _ovs.is_active(session_id):
            _ovs.touch(session_id)
    except Exception:
        pass

    # Identity-guard & session-lock (spec 2026-06-21) — samme som v2. Låst session/
    # konto eller uverificeret identitets-claim → kortslut med legacy-SSE-kvittering.
    try:
        from core.services import identity_guard as _ig
        _guard = _ig.guard_incoming(request.message, session_id=session_id, user_id=_uid or "")
    except Exception:
        _guard = None
    if _guard is not None:
        _greply = str(_guard.get("reply") or "")
        try:
            append_chat_message(session_id=session_id, role="assistant",
                                content=_greply, user_id=None)
        except Exception:
            pass
        from core.services.visible_runs import _sse as _sse_legacy

        def _guard_gen():
            yield _sse_legacy("delta", {"type": "delta", "run_id": "guard", "delta": _greply})
            yield _sse_legacy("done", {"type": "done", "run_id": "guard",
                                       "status": "completed", "input_tokens": 0, "output_tokens": 0})
        return StreamingResponse(_guard_gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})

    return StreamingResponse(
        start_visible_run(
            message=model_message,
            session_id=session_id,
            approval_mode=request.approval_mode,
            thinking_mode=request.thinking_mode,
            # Pass current user_id explicitly. The streaming generator
            # body runs AFTER the middleware has reset workspace_context
            # (call_next returns the response object before the body
            # streams), so the generator must rebind context itself.
            # Without this, operator_* tools dispatch to owner via
            # _operator_user_id fallback. See 2026-05-28 bug investigation.
            force_user_id=_uid,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/approvals/{approval_id}/approve")
async def chat_approve_tool(approval_id: str) -> dict:
    """Approve a pending tool approval and run it. Resolves in a thread (deadlock-
    avoidance, see comment). 404 if the approval id is unknown; else the tool result."""
    # CRITICAL: must run in a thread, not on the event loop directly.
    # resolve_pending_approval → execute_tool_force → _run_operator_async
    # uses asyncio.run_coroutine_threadsafe(coro, main_loop) + cf_fut.result()
    # which deadlocks if called from main_loop itself (loop blocked → coroutine
    # can't run → future never resolves → 60s timeout → tool returns error
    # AND THEN the coroutine finally runs after the deadlock returns).
    # Observed live 2026-05-28: operator_bash "echo hej" returned timeout-error
    # ~60s after user clicked Approve, even though the bridge replied in 20ms.
    import asyncio
    result = await asyncio.to_thread(resolve_pending_approval, approval_id, approved=True)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.post("/approvals/{approval_id}/deny")
async def chat_deny_tool(approval_id: str) -> dict:
    """Deny a pending tool approval (does not run the tool). Resolves in a thread.
    404 if the approval id is unknown; else the resolution result."""
    # Same deadlock-avoidance as /approve: see comment there. Deny doesn't
    # actually run the tool, but resolve_pending_approval is sync either way
    # and consistency keeps the codepath simple.
    import asyncio
    result = await asyncio.to_thread(resolve_pending_approval, approval_id, approved=False)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.post("/runs/{run_id}/cancel")
async def chat_cancel_run(run_id: str) -> dict:
    """Afbryd et aktivt visible-run via run_id. 404 hvis runnet ikke er aktivt;
    ellers {ok: True, run_id, status: "cancelled"}."""
    if not cancel_visible_run(run_id):
        raise HTTPException(status_code=404, detail="Visible run not active")
    return {
        "ok": True,
        "run_id": run_id,
        "status": "cancelled",
    }


@router.post("/runs/{run_id}/steer")
async def chat_steer_run(run_id: str, body: dict) -> dict:
    """Mid-flight steer: inject a user message into a running visible-run.
    The agentic loop picks it up at the next round boundary."""
    from core.services.visible_runs import append_visible_run_steer
    content = str((body or {}).get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content required")
    ok = append_visible_run_steer(run_id, content)
    if not ok:
        raise HTTPException(status_code=404, detail="Visible run not active")
    return {"ok": True, "run_id": run_id, "queued": True}


@router.post("/runs/{run_id}/tool-result")
async def chat_client_tool_result(run_id: str, body: dict) -> dict:
    """Fase 1 (jarvis-code↔v2 forening): klienten leverer resultatet af et
    delegeret execution=="client"-tool. Serverens turn-loop emitterede tool_use
    og venter (poll) på dette. Body: {call_id, result}. 404 hvis call_id ikke er
    en pending delegeret tool (ukendt/allerede resolved/expired)."""
    from core.services.visible_runs import resolve_visible_client_tool
    call_id = str((body or {}).get("call_id") or "").strip()
    if not call_id:
        raise HTTPException(status_code=400, detail="call_id required")
    result_text = str((body or {}).get("result") or "")
    ok = resolve_visible_client_tool(call_id, result_text)
    if not ok:
        raise HTTPException(status_code=404, detail="No pending client tool for call_id")
    return {"ok": True, "run_id": run_id, "call_id": call_id, "resolved": True}
