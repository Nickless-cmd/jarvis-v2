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
import logging
from contextlib import contextmanager
from typing import Any, Iterable, Iterator

logger = logging.getLogger(__name__)

try:  # defensiv — undgå circular-import-brud ved boot
    from core.identity.workspace_context import current_user_id
except Exception:  # pragma: no cover
    def current_user_id():  # type: ignore
        return None

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
    "dispatch_code_mode_task",
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
    # Geolocation (read-only eksterne opslag)
    "geolocation_lookup", "geocode", "reverse_geocode", "route_directions", "nearby_search",
    # Teams
    "create_team", "list_teams", "invite_to_team",
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
    # UI-panel-kald (desk) — fremvis noget i preview/højre-panel (§8.2)
    "open_ui_panel",
    # App-self-control (desk) — foreslå skift chat→code mode (brugeren godkender)
    "request_app_action",
    # Companion-push — naa brugeren proaktivt paa deres egne enheder (device-routet)
    "send_push_notification",
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
    "operator_bash_session_open", "operator_bash_session_run",
    "operator_bash_session_close", "operator_bash_session_list",
    # App-self-control (desk) — foreslå fuld adgang (trust) i code mode
    "request_app_action",
})
CODE_MODE_OWNER_EXTRA: frozenset[str] = frozenset({
    "read_file", "write_file", "edit_file", "search", "find_files", "bash",
    "dispatch_to_claude_code", "dispatch_code_mode_task",
    # Owner-only operator backup-channel (jarvis-code bash reroute). Deliberately
    # NOT in the member/guest base scope — a non-owner must never get the
    # dialog-free operator reroute.
    "operator_session_open", "operator_session_run", "operator_session_close",
})

# §17: værktøjer der eksekverer LOKALT på brugerens maskine i code mode. Deres rå
# resultat bliver på maskinen; kun summary krydser via bro_broker. bridge.ts bruger
# dette til mode-aware routing (§17.6.1).
LOCAL_EXECUTION_TOOLS: frozenset[str] = CODE_MODE_TOOLS_BASE | CODE_MODE_OWNER_EXTRA


def is_local_execution_tool(name: str) -> bool:
    """True hvis værktøjet kører lokalt i code mode (resultat forlader ikke maskinen)."""
    return str(name or "") in LOCAL_EXECUTION_TOOLS


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


# --- Path B / jarvis-code-surface ContextVar (local_tool_exec) ---
# Sat ved run-setup fra VisibleRun.local_tool_exec. True = jarvis-code kører tools
# LOKALT (Path B) → prompten injicerer jarvis-codes egen 3-lags-toolbox-forklaring
# (native=Bjørns maskine / runtime_*=container / operator_*=bro), IKKE desks katalog.
_local_exec_var: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "jarvis_tool_local_exec", default=False,
)


def current_local_exec() -> bool:
    """True når det aktive run er en jarvis-code Path B lokal-exec-tur."""
    return bool(_local_exec_var.get())


def set_local_exec(on: bool) -> contextvars.Token:
    return _local_exec_var.set(bool(on))


@contextmanager
def tool_scope(scope: str) -> Iterator[None]:
    token = set_tool_scope(scope)
    try:
        yield
    finally:
        reset_tool_scope(token)


def _owner_has_live_bridge() -> bool:
    """True hvis der findes en levende desk-bro for nuværende bruger (presence, cross-proces).
    Grundlaget for 'operator-tools i owner-chat KUN når paret'. Self-safe → False ved tvivl."""
    try:
        from core.identity.workspace_context import current_user_id
        from core.services import bridge_presence
        uid = current_user_id()
        if not uid:
            return False
        return bridge_presence.process_for_user(str(uid)) is not None
    except Exception:
        return False


def allowed_tool_names(
    *, role: str, scope: str, all_names: Iterable[str],
) -> set[str]:
    """Beregn det tilladte sæt tool-navne for (role, scope).

    Konsolideret 2026-06-14 (TOTP Fase 4.1) — **permission_engine er eneste
    sandhed for sikkerhed** (no-dual-truth):

    - **Owner** (role in {"", "owner"}; "" = unbound legacy): mode-kuration for
      UX-fokus (chat/code-allowlists), men INGEN sikkerheds-begrænsning. Owner
      ser alt mode-passende. Bevaret bit-for-bit fra før konsolideringen.
    - **Member/guest**: `permission_engine.allowed_tools(role, mode)` ER både
      sikkerhed OG det mode-passende sæt (matrixen er et tæt pr-mode-sæt). Owner-
      autoritet kan kun nås via TOTP-override (håndteres i kald-laget, ikke her).

    scope "chat"/"code"/"cowork" → mode; alt andet ("") → cowork (fail-closed
    for non-owner; "alt" for owner).
    """
    role = (role or "").strip().lower()
    scope = (scope or "").strip().lower()
    names = set(all_names)
    is_owner = role in ("", "owner")

    if is_owner:
        if scope == "code":
            result = (set(CODE_MODE_TOOLS_BASE) | CODE_MODE_OWNER_EXTRA) & names
        elif scope == "chat":
            result = (set(CHAT_MODE_TOOLS_BASE) | CHAT_MODE_OWNER_EXTRA) & names
            # Bjørn 2026-07-01: owner skal kunne nå sin EGEN paret desktop fra mobil chat
            # (bro-tools kører på hans maskine). Men KUN når en desk-bro faktisk er forbundet
            # (presence) — så mobil-chat får operator-tools uden at skulle i code mode, og
            # overfladen udvides ikke når intet er paret. Godkendelses-kort gater risiko.
            if _owner_has_live_bridge():
                result |= set(CODE_MODE_TOOLS_BASE) & names
        else:
            result = names  # cowork / ubegrænset: alt mode-passende = alt
    else:
        # Non-owner: permission_engine er sandheden (sikkerhed + mode-passende sæt).
        from core.services.permission_engine import allowed_tools as _perm_allowed
        mode = scope if scope in ("chat", "code", "cowork") else "cowork"
        perm = _perm_allowed(role=role, mode=mode)
        result = set(perm) & names

    return _apply_computer_use_policy(result)


def is_tool_allowed(*, role: str, scope: str, name: str) -> bool:
    """Må (role, scope) eksekvere værktøjet `name`? (Spor A — serverside håndhævelse.)

    Owner / unbound ("") → altid True: dig + betroede interne/daemon-kald, der
    kører uden bundet non-owner-rolle. Non-owner → `allowed_tool_names` (som er
    permission_engine + computer-use-policy → samme sandhed som model-filteret).
    """
    r = (role or "").strip().lower()
    if r in ("", "owner"):
        return True
    return name in allowed_tool_names(role=r, scope=scope, all_names={name})


def _apply_computer_use_policy(result: set[str]) -> set[str]:
    """Computer-use-toggle (§4.7): fjern operator/computer-tools hvis brugeren har
    slået computer-use fra. Defensiv — fejler altid TIL (uændret) for ikke at låse
    sig selv ude ved fejl."""
    try:
        from core.services.computer_use_policy import (
            computer_use_enabled,
            is_computer_use_tool,
        )
        if not computer_use_enabled(current_user_id() or ""):
            return {t for t in result if not is_computer_use_tool(t)}
    except Exception:
        # Fail-open (defensivt, jf. docstring) MEN ikke længere stille: en fejl her
        # betyder operator/computer-tools IKKE blev filtreret. Primær gate er
        # permission_engine member-listen; dette er en backstop. (Auth-cluster
        # trace-kontrakt, 2026-06-22 — fail-retning ændres bevidst først ved
        # sikkerheds-migrationen med fail-closed paritet.)
        logger.warning(
            "computer-use-policy fejlede — operator-tools blev IKKE filtreret "
            "(fail-open backstop)", exc_info=True,
        )
    return result


def _fn_name(td: dict[str, Any]) -> str:
    return str(((td or {}).get("function") or {}).get("name") or "")


def filter_tool_definitions(
    defs: list[dict[str, Any]], *, role: str, scope: str,
) -> list[dict[str, Any]]:
    """Filtrér Ollama-tool-definitioner ned til det tilladte sæt for (role, scope).

    Owner-styret native-tool-lås (native_tool_gate) trækkes fra ovenpå: låste tools
    fjernes helt, så Jarvis hverken ser eller kalder dem. Fail-open (intet låst)."""
    allow = allowed_tool_names(
        role=role, scope=scope, all_names=[_fn_name(d) for d in defs],
    )
    try:
        from core.tools.native_tool_gate import disabled_tools
        locked = disabled_tools()
    except Exception:
        locked = set()
    return [d for d in defs if _fn_name(d) in allow and _fn_name(d) not in locked]
