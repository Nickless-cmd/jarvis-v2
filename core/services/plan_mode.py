"""Server-authoritative Plan mode for the visible code lane.

Plan mode is a collaboration state, not text in the user's message.  The
state is persisted per chat session so reconnects and recovery runs cannot
silently regain write access.  A request with ``plan_mode=False`` explicitly
leaves the mode again.
"""
from __future__ import annotations

import contextvars
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from core.runtime.db import connect

logger = logging.getLogger(__name__)

_active: contextvars.ContextVar[bool | None] = contextvars.ContextVar(
    "jarvis_plan_mode", default=None,
)

# Fail-closed allowlist. Shell is handled separately because its effect depends
# on the concrete command. ``propose_plan``/``revise_plan`` are the only state
# writes allowed: they create the planning artifact, not the implementation.
_READ_ONLY_TOOLS = frozenset({
    "read_file", "find_files", "search", "grep", "glob", "list_dir",
    "semantic_search_code",
    "find_symbol", "find_usages", "smart_outline", "read_tool_result",
    "read_attachment", "pdf_read", "web_search", "web_fetch", "db_query",
    "process_list", "process_tail", "verification_status",
    "verify_file_contains", "verify_service_active", "verify_endpoint_responds",
    "git_status", "git_log", "git_diff", "git_branch", "git_blame",
    "operator_read_file", "operator_glob", "operator_grep", "operator_list_dir",
    "repo_recall", "todo_list", "inbox", "desk_get_layout",
    "jarvis_browser_read", "jarvis_browser_tabs",
    "list_plans", "propose_plan", "revise_plan",
})
_SHELL_TOOLS = frozenset({"bash", "bash_session_run", "operator_bash"})


def set_session_plan_mode(session_id: str, enabled: bool) -> None:
    """Persist the mode selected by the code client for the session."""
    sid = str(session_id or "").strip()
    if not sid:
        return
    with connect() as conn:
        conn.execute(
            "UPDATE chat_sessions SET plan_mode = ? WHERE session_id = ?",
            (1 if enabled else 0, sid),
        )


def session_plan_mode(session_id: str | None, *, fail_closed: bool = False) -> bool:
    sid = str(session_id or "").strip()
    if not sid:
        return False
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT plan_mode FROM chat_sessions WHERE session_id = ?", (sid,)
            ).fetchone()
        return bool(row and row[0])
    except Exception as exc:
        logger.warning("plan mode: kunne ikke læse sessionstilstand: %s", exc)
        return bool(fail_closed)


def is_active(session_id: str | None = None) -> bool:
    """Current task-local mode, with durable session fallback for recovery."""
    local = _active.get()
    if local is not None:
        return bool(local)
    sid = str(session_id or "").strip()
    if not sid:
        try:
            from core.identity.workspace_context import current_session_id

            sid = str(current_session_id() or "").strip()
        except Exception as exc:
            logger.warning("plan mode: kunne ikke læse aktiv session: %s", exc)
            sid = ""
    return session_plan_mode(sid)


@asynccontextmanager
async def stream_context(enabled: bool) -> AsyncIterator[None]:
    token = _active.set(bool(enabled))
    try:
        yield
    finally:
        _active.reset(token)


async def wrap_stream(stream: Any, *, enabled: bool) -> AsyncIterator[str]:
    """Carry Plan mode through an async generator and its worker contexts."""
    async with stream_context(enabled):
        async for item in stream:
            yield item


def tool_allowed(name: str, arguments: dict[str, Any] | None = None, *,
                 session_id: str | None = None) -> bool:
    """Fail-closed execution verdict for a tool while Plan mode is active."""
    if not is_active(session_id):
        return True
    tool = str(name or "").strip()
    if tool in _READ_ONLY_TOOLS:
        return True
    if tool in _SHELL_TOOLS:
        command = str((arguments or {}).get("command") or "")
        if not command.strip():
            return False
        try:
            from core.services.verification_gate import shell_command_is_mutating

            return not shell_command_is_mutating(command)
        except Exception as exc:
            logger.warning("plan mode: shell-klassifikation fejlede: %s", exc)
            return False
    return False


def filter_definitions(defs: list[dict[str, Any]], *, session_id: str | None = None) -> list[dict[str, Any]]:
    if not is_active(session_id):
        return defs
    out: list[dict[str, Any]] = []
    for definition in defs:
        name = str(((definition.get("function") or {}).get("name") or ""))
        if name in _READ_ONLY_TOOLS or name in _SHELL_TOOLS:
            out.append(definition)
    return out


def prompt_section() -> str | None:
    if not is_active():
        return None
    return """## Plan mode — kun planlægning
Denne tilstand er servervalgt og gælder indtil code-klienten forlader den. Den
overstyrer code mode-reglen om straks at implementere: selv hvis brugeren skriver
\"gør det\", skal du planlægge udførelsen og må ikke ændre repo, runtime eller
eksterne systemer.

Arbejd i tre faser. Først: undersøg repo, konfiguration, kaldere og tests med
read-only værktøjer; spørg ikke om fakta du selv kan finde. Dernæst: afklar kun
produktvalg, scope og tradeoffs der materielt ændrer løsningen. Til sidst: gør
implementeringen beslutningsklar med tilgang, grænseflader/dataflow, fejltilfælde,
kompatibilitet, tests, acceptkriterier og eksplicitte antagelser.

Du må læse, søge og køre dokumenteret read-only inspektion og verifikation. Du
må ikke skrive filer, formatere med omskrivning, migrere, committe, deploye,
sende beskeder eller udføre andre mutationer. Runtime håndhæver grænsen.

Når planen er beslutningsklar, kald `propose_plan` én gang med en kort titel,
en præcis begrundelse og konkrete trin. Indbyg testplan og vigtige antagelser i
forslaget. Spørg ikke bagefter om du skal fortsætte. En accepteret plan er et
godkendt design, ikke en omgåelse af normale tool-approvals; implementering sker
først i en senere tur uden Plan mode."""


__all__ = [
    "filter_definitions", "is_active", "prompt_section", "session_plan_mode",
    "set_session_plan_mode", "stream_context", "tool_allowed", "wrap_stream",
]
