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
_FILE_ROOTS = ("docs", "workspace", "core", "apps", "scripts")
_LANG_BY_EXT = {
    ".py": "python", ".ts": "typescript", ".tsx": "tsx", ".js": "javascript",
    ".json": "json", ".md": "markdown", ".css": "css", ".sh": "bash", ".txt": "text",
}


def _repo_root() -> Path:
    # chat.py: apps/api/jarvis_api/routes/ → fire niveauer op til repo-rod.
    return Path(__file__).resolve().parents[4]


@router.get("/file")
async def chat_read_file(path: str = Query(...), kind: str = "container") -> dict:
    """Læs en fil til preview-panelet. Container: path-jail til whitelisted rødder.
    Workstation: via operator-bridgen (operator_read_file) på brugerens computer."""
    if kind == "workstation":
        res = _operator_exec("operator_read_file", {"path": path})
        if res.get("status") != "ok":
            raise HTTPException(status_code=502, detail=str(res.get("reason") or "operator-read fejlede"))
        content = str(res.get("content") or res.get("text") or "")
        ext = ("." + path.rsplit(".", 1)[-1]) if "." in path.rsplit("/", 1)[-1] else ""
        return {"path": path, "content": content, "language": _LANG_BY_EXT.get(ext, "text")}

    root = _repo_root()
    candidate = (root / path).resolve()
    try:
        rel = candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=403, detail="uden for jail")
    if not rel.parts or rel.parts[0] not in _FILE_ROOTS:
        raise HTTPException(status_code=403, detail="ikke-whitelisted rod")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="ikke fundet")
    content = candidate.read_text(encoding="utf-8", errors="replace")
    return {"path": path, "content": content, "language": _LANG_BY_EXT.get(candidate.suffix, "text")}


def _operator_exec(name: str, args: dict) -> dict:
    """Kør et operator-tool via simple_tools (router'er til brugerens bridge).
    Seam til test-mock (workstation fil-træ)."""
    from core.tools.simple_tools import execute_tool
    return execute_tool(name, args) or {}


@router.get("/tree")
async def chat_tree(kind: str = "container", root: str = "", path: str = "") -> dict:
    """Mappe-listing til Code-mode fil-træ. Container: path-jailed til _FILE_ROOTS.
    Workstation: via operator-bridgen (operator_list_dir)."""
    if kind == "container":
        if root not in _FILE_ROOTS:
            raise HTTPException(status_code=403, detail="root uden for jail")
        base = (_repo_root() / root).resolve()
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
        res = _operator_exec("operator_list_dir", {"path": full})
        if res.get("status") != "ok":
            raise HTTPException(status_code=502, detail=str(res.get("reason") or "operator-list fejlede"))
        entries = [
            {"name": e.get("name") or "", "kind": "dir" if e.get("is_dir") else "file"}
            for e in (res.get("entries") or [])
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


def _git_status_sync(kind: str, root: str) -> dict:
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
        res = _operator_exec("operator_bash", {"command": cmd})
        out = str(res.get("stdout") or "") if res.get("status") == "ok" else ""
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
    return await asyncio.to_thread(_git_status_sync, kind, root)


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
    from datetime import UTC, datetime
    from core.services.visible_runs import _get_active_visible_run_state
    out: list[str] = []
    try:
        state = _get_active_visible_run_state() or {}
        sid = str(state.get("session_id") or "").strip()
        if sid and not state.get("cancelled"):
            started = str(state.get("started_at") or "")
            fresh = True
            if started:
                try:
                    age = (datetime.now(UTC) - datetime.fromisoformat(started)).total_seconds()
                    fresh = age < 600
                except (ValueError, TypeError):
                    fresh = True
            if fresh:
                out.append(sid)
    except Exception:
        pass
    return {"session_ids": out}


@router.get("/context-info")
async def chat_context_info() -> dict:
    """Kontekst-tærskler til composer-ringen (#9). Kun ægte config-tal:
    autocompact-punktet (context_compact_threshold_tokens). Klienten holder
    selv tælleren (usage.input + cache fra streamen)."""
    from core.runtime.settings import load_settings
    s = load_settings()
    return {
        "compact_at": int(s.context_compact_threshold_tokens or 0),
        "run_compact_at": int(s.context_run_compact_threshold_tokens or 0),
    }


@router.post("/sessions")
async def chat_create_session(request: ChatSessionCreateRequest) -> dict:
    return {"session": create_chat_session(
        title=request.title,
        workspace_kind=request.workspace_kind or None,
        workspace_root=request.workspace_root or None,
    )}


@router.get("/sessions/{session_id}")
async def chat_session(session_id: str) -> dict:
    session = get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"session": session}


@router.put("/sessions/{session_id}/rename")
async def chat_rename_session(session_id: str, request: ChatSessionRenameRequest) -> dict:
    session = rename_chat_session(session_id, title=request.title)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"session": session}


@router.delete("/sessions/{session_id}")
async def chat_delete_session(session_id: str) -> dict:
    if not delete_chat_session(session_id):
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"ok": True, "session_id": session_id}


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
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
    from core.services.notification_bridge import pin_session
    pin_session(session_id)
    return StreamingResponse(
        start_visible_run(
            message=effective_message,
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
