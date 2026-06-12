"""Tool-scoping policy — hvilke værktøjer er tilgængelige pr. rolle og mode.

Udskilt fra simple_tools.py (Boy Scout 2026-06-12) så scoping-policyen er en
fokuseret, testbar enhed adskilt fra selve tool-definitionerne.

To akser:
  - **role** (owner|member|guest|""): owner/unbound ser alt; member/guest får
    OWNER_ONLY_TOOLS strippet.
  - **scope** (chat|None): i "chat" begrænses til en allowlist af samtale-
    relevante værktøjer (web/data/vision + hukommelse + selv-indsigt). Owner
    får ekstra fil-læsning. Alt der *handler* (OS, fil-skriv, git, scheduling,
    dispatch, kanal-sends) er udelukket i chat — det hører til cowork/code.

Scope sættes typisk via ContextVar ved request-entry (som role), så de mange
get_tool_definitions()-call-sites i visible_model ikke skal ændres.
"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Any, Iterable, Iterator

# Værktøjer kun owner (eller unbound legacy) må se — strippes for member/guest.
# Flyttet hertil fra simple_tools.py; re-eksporteres derfra for bagudkompat.
OWNER_ONLY_TOOLS: frozenset[str] = frozenset({
    # Raw backend shell + file mutation (operator_* counterparts are user-side)
    "bash",
    "bash_session_close",
    "bash_session_list",
    "bash_session_open",
    "bash_session_run",
    "edit_file",
    "write_file",
    # Self-modification / identity / proposals
    "adopt_brain_proposal",
    "discard_brain_proposal",
    "archive_brain_entry",
    "read_brain_entry",
    "search_jarvis_brain",
    "append_skill_observation",
    "generate_improvement_proposals",
    "identity_mutation_status",
    "list_identity_mutations",
    "list_proposals",
    "my_project_accept_proposal",
    "propose_identity_drift_update",
    "read_self_docs",
    "read_self_state",
    "rollback_identity_mutation",
    "approve_plan",
    "approve_proposal",
    # Agent dispatch + scheduling control
    "dispatch_cancel",
    "dispatch_due_wakeups",
    "dispatch_status",
    "dispatch_to_claude_code",
    "cancel_agent",
    "cancel_recurring",
    "cancel_self_wakeup",
    "cancel_task",
    "list_recurring",
    "list_self_wakeups",
    "mark_wakeup_consumed",
    "schedule_recurring",
    "schedule_self_wakeup",
})

# Chat-mode allowlist (gælder ALLE roller i chat). Member/guest får yderligere
# OWNER_ONLY_TOOLS strippet ovenpå (så fx search_jarvis_brain kun er owner).
CHAT_MODE_TOOLS_BASE: frozenset[str] = frozenset({
    # Web / viden
    "web_search", "web_fetch", "web_scrape", "get_news",
    # Data
    "get_weather", "get_exchange_rate", "wolfram_query",
    # Vision
    "analyze_image",
    # Hukommelse — read
    "search_memory", "memory_graph_query", "resurface_old_memory",
    "search_jarvis_brain", "read_brain_entry",
    # Hukommelse — write (egen + brugerens)
    "remember_this", "memory_upsert_section", "adjust_mood",
    # Selv-indsigt — read
    "read_mood", "read_self_state", "read_chronicles", "read_dreams",
    "read_model_config",
})

# Ekstra værktøjer owner (kun) får i chat — fil-læsning til kode-snak.
CHAT_MODE_OWNER_EXTRA: frozenset[str] = frozenset({
    "read_file", "search", "find_files",
})

# Code-mode allowlist. Owner = container + workstation + dispatch; member/guest =
# kun workstation (operator-bridge, sandboxet til deres egen maskine).
CODE_MODE_TOOLS_BASE: frozenset[str] = frozenset({
    "operator_read_file", "operator_write_file", "operator_edit_file",
    "operator_bash", "operator_glob", "operator_grep", "operator_list_dir",
})
CODE_MODE_OWNER_EXTRA: frozenset[str] = frozenset({
    "read_file", "write_file", "edit_file", "search", "find_files", "bash",
    "dispatch_to_claude_code",
})


# --- Scope ContextVar (sættes ved request-entry, læses i get_tool_definitions) ---
_scope_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "jarvis_tool_scope", default="",
)


def current_tool_scope() -> str:
    """Nuværende tool-scope ("chat" eller "" for ubegrænset)."""
    return _scope_var.get()


def set_tool_scope(scope: str) -> contextvars.Token:
    return _scope_var.set((scope or "").strip().lower())


def reset_tool_scope(token: contextvars.Token) -> None:
    _scope_var.reset(token)


@contextmanager
def tool_scope(scope: str) -> Iterator[None]:
    token = set_tool_scope(scope)
    try:
        yield
    finally:
        reset_tool_scope(token)


def allowed_tool_names(
    *, role: str, scope: str, all_names: Iterable[str],
) -> set[str]:
    """Beregn det tilladte sæt tool-navne for (role, scope).

    role: owner|member|guest|"" ("" = unbound legacy → behandles som owner).
    scope: "chat" → allowlist; alt andet → kun rolle-filter.
    """
    role = (role or "").strip().lower()
    names = set(all_names)
    is_owner = role in ("", "owner")

    if scope == "code":
        allowed = set(CODE_MODE_TOOLS_BASE)
        if is_owner:
            allowed |= CODE_MODE_OWNER_EXTRA
        else:
            allowed -= OWNER_ONLY_TOOLS
        return allowed & names

    if scope == "chat":
        allowed = set(CHAT_MODE_TOOLS_BASE)
        if is_owner:
            allowed |= CHAT_MODE_OWNER_EXTRA
        else:
            allowed -= OWNER_ONLY_TOOLS
        return allowed & names

    # Ikke-chat (cowork/code/ubegrænset): kun rolle-filter.
    if is_owner:
        return names
    return {n for n in names if n not in OWNER_ONLY_TOOLS}


def _fn_name(td: dict[str, Any]) -> str:
    return str(((td or {}).get("function") or {}).get("name") or "")


def filter_tool_definitions(
    defs: list[dict[str, Any]], *, role: str, scope: str,
) -> list[dict[str, Any]]:
    """Filtrér Ollama-tool-definitioner ned til det tilladte sæt for (role, scope)."""
    allow = allowed_tool_names(
        role=role, scope=scope, all_names=[_fn_name(d) for d in defs],
    )
    return [d for d in defs if _fn_name(d) in allow]
