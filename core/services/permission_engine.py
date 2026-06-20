"""Permission engine — rollebaseret tool-adgang pr. mode (fail-closed).

Kanonisk kilde: docs/superpowers/specs/tool_access_matrix.md (godkendt 14. juni).

Sikkerhedsmodel — **fail-closed default-deny**:
- **Owner** (Bjørn): ALLE tools, alle modes (sentinel ALL_TOOLS).
- **Member** (fx Mikkel): KUN de eksplicit listede tools pr. mode nedenfor.
- **Guest**: ∅ (læser kun samtalen).
- Ukendt rolle/mode → ∅.

Alt der IKKE står på en member-liste er automatisk owner-only. Derfor er Jarvis'
egen kode (skill_*, bash, git_*, restart_self, dispatch_to_claude_code), native
indre tools (mood, dream, brain, identitet), finans (stripe_*, tiktok_*) og runtime
utilgængelige for member uden at vi opremser dem — de er bare ikke her.

**Vigtigt:** dette er tool-adgang, IKKE data-adgang. En member-tilladt `edit_file`
skal stadig path-jailes til brugerens eget workspace (requires_workspace_jail +
håndhævelse i Fase 4 dispatch). Se project_multiuser_security_northstar.

Listerne er EKSPLICITTE (ikke prefix-regler) med vilje: en fremtidig tool ved navn
fx "operator_wipe_disk" må ikke auto-tilgås via et mønster. Drift fanges af
test_permission_engine::test_all_member_tool_names_exist_in_registry.
"""
from __future__ import annotations


class _AllTools:
    """Sentinel for owner — indeholder enhver tool."""

    def __contains__(self, item: object) -> bool:  # noqa: D401
        return True

    def __repr__(self) -> str:
        return "ALL_TOOLS"


ALL_TOOLS = _AllTools()


# ── Member CHAT ─────────────────────────────────────────────────────────────
_MEMBER_CHAT_WEB = frozenset({
    "web_search", "web_scrape", "web_fetch", "get_news", "get_weather",
    "get_exchange_rate", "wolfram_query", "analyze_image",
    "geolocation_lookup", "geocode", "reverse_geocode", "route_directions", "nearby_search",
})
_MEMBER_CHAT_UTIL = frozenset({"calculate", "unit_convert", "percentage"})
# 🔒 path-jailed til eget workspace
_MEMBER_CHAT_MEM = frozenset({
    "remember_this", "search_memory", "recall_memories", "memory_list_headings",
})
_MEMBER_CHAT = _MEMBER_CHAT_WEB | _MEMBER_CHAT_UTIL | _MEMBER_CHAT_MEM


# ── Member CODE (= det Claude har) ──────────────────────────────────────────
# Operator-tools kører på brugerens EGEN maskine via bridge.
_MEMBER_CODE_OPERATOR = frozenset({
    "operator_bash", "operator_browser_click", "operator_browser_close",
    "operator_browser_evaluate", "operator_browser_get_links",
    "operator_browser_get_text", "operator_browser_open",
    "operator_browser_screenshot", "operator_browser_status",
    "operator_browser_type", "operator_clipboard_read", "operator_clipboard_write",
    "operator_edit_file", "operator_find_image", "operator_focus_window",
    "operator_glob", "operator_grep", "operator_keyboard_press",
    "operator_keyboard_type", "operator_kill_process", "operator_launch_app",
    "operator_list_dir", "operator_list_processes", "operator_list_windows",
    "operator_mouse_click", "operator_mouse_drag", "operator_mouse_move",
    "operator_mouse_position", "operator_mouse_scroll", "operator_notify",
    "operator_ocr_region", "operator_open_url", "operator_process_kill",
    "operator_process_list", "operator_process_output", "operator_process_spawn",
    "operator_process_status", "operator_read_file", "operator_record_audio",
    "operator_reminder", "operator_scheduled_cancel", "operator_scheduled_list",
    "operator_screen_size", "operator_screenshot", "operator_screenshot_window",
    "operator_speak", "operator_unwatch_folder", "operator_wakeup",
    "operator_watch_events", "operator_watch_folder", "operator_webfetch",
    "operator_write_file",
})
_MEMBER_CODE_WEB = frozenset({"web_search", "web_scrape", "web_fetch", "analyze_image"})
# 🔒 path-jailed til eget workspace (server-side, IKKE Jarvis' repo)
_MEMBER_CODE_FILE = frozenset({"read_file", "write_file", "edit_file", "find_files"})
# 🔒 connector-tools: bruger member'ens EGEN OAuth-token (per-bruger krypteret).
# Rører aldrig ejerens/Jarvis' GitHub. Yderligere gated af connected+enabled i runtime.
_MEMBER_CODE_CONNECTOR = frozenset({"github_list_issues", "github_list_prs"})
_MEMBER_CODE = (
    _MEMBER_CODE_OPERATOR | _MEMBER_CODE_WEB | _MEMBER_CODE_FILE | _MEMBER_CODE_CONNECTOR
)


# ── Member COWORK ───────────────────────────────────────────────────────────
_MEMBER_COWORK = frozenset({
    "propose_plan", "revise_plan", "list_plans", "dismiss_plan",
    "todo_add", "todo_list", "todo_set", "todo_update_status", "todo_remove",
    "list_proposals", "discord_channel",
})


# (rolle, mode) → tilladt sæt. Kun member har afgrænsede sæt; owner/guest
# håndteres i allowed_tools().
_MEMBER_BY_MODE: dict[str, frozenset[str]] = {
    "chat": _MEMBER_CHAT,
    "code": _MEMBER_CODE,
    "cowork": _MEMBER_COWORK,
}

# Tools der kræver workspace-jail når member bruger dem (data-isolation).
_JAILED_BY_MODE: dict[str, frozenset[str]] = {
    "chat": _MEMBER_CHAT_MEM,
    "code": _MEMBER_CODE_FILE,
}


def allowed_tools(*, role: str, mode: str) -> "frozenset[str] | _AllTools":
    """Returnér de tools en (rolle, mode) må bruge.

    Owner → ALL_TOOLS-sentinel (enhver tool). Member → eksplicit sæt pr. mode.
    Guest / ukendt rolle / ukendt mode → tom frozenset (fail-closed).
    """
    if role == "owner":
        return ALL_TOOLS
    if role == "member":
        return _MEMBER_BY_MODE.get(mode, frozenset())
    return frozenset()


def is_tool_allowed(tool: str, *, role: str, mode: str) -> bool:
    """True hvis `tool` må kaldes af (rolle, mode)."""
    return tool in allowed_tools(role=role, mode=mode)


def requires_workspace_jail(tool: str, *, role: str, mode: str) -> bool:
    """True hvis tool-kaldet skal path-jailes til brugerens eget workspace.

    Kun relevant for member (owner opererer i egen session). Informativt for
    Fase 4-dispatch — permission_engine håndhæver IKKE jailen selv.
    """
    if role != "member":
        return False
    return tool in _JAILED_BY_MODE.get(mode, frozenset())


def _all_member_tool_names() -> set[str]:
    """Alle navne på tværs af member-lister — til drift-test mod registry."""
    return set(_MEMBER_CHAT | _MEMBER_CODE | _MEMBER_COWORK)
