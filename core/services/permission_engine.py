"""Permission engine — rollebaseret tool-adgang pr. mode (fail-closed).

Kanonisk kilde: docs/superpowers/specs/tool_access_matrix.md (godkendt 14. juni).

Sikkerhedsmodel — **fail-closed default-deny**:
- **Owner** (Bjørn): ALLE tools, alle modes (sentinel ALL_TOOLS).
- **Member** (fx Mikkel): KUN de eksplicit listede tools pr. mode nedenfor.
- **Guest**: ∅ (læser kun samtalen).
- Ukendt rolle/mode → ∅.

Alt der IKKE står på en member-liste er automatisk owner-only. Derfor er Jarvis'
egen kode (skill_*, bash, git_*, restart_self, dispatch_to_claude_code), native
indre tools (mood, dream, brain, identitet), finans (stripe_*) og runtime
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
    # Madopskrifter (25/10-2026). Nøglefri, read-only eksterne opslag — samme
    # familie som vejr og nyheder, og Michelle er præcis den bruger der
    # spurgte efter det.
    "madopskrift",
    "geolocation_lookup", "geocode", "reverse_geocode", "route_directions", "nearby_search",
})
_MEMBER_CHAT_UTIL = frozenset({
    "calculate", "unit_convert", "percentage",
    # Self-scoped in the handler; members can change only their own Desk UI.
    "set_chat_flow_preference",
})
# 🔒 path-jailed til eget workspace
_MEMBER_CHAT_MEM = frozenset({
    "remember_this", "search_memory", "recall_memories", "memory_list_headings",
})
# Billeder — at SE et og at TEGNE et.
#
# `analyze_image` stod allerede i `_MEMBER_CHAT_WEB`, altsaa kunne Michelle
# kigge paa et billede men ikke lave et. Bjoern bad 13/9-2026 om at aabne begge
# veje for hende.
#
# BEMÆRK at det koster penge: `openrouter_image` bruger betalingsnoeglen, og
# free-tier-profilen er eksplicit forbudt i vaerktoejet. Det er derfor et
# bevidst valg og ikke en oprydning — en ikke-ejer kan nu bruge af puljen.
_MEMBER_IMAGE = frozenset({"openrouter_image", "openrouter_image_edit"})

# Visning — at TEGNE en graf eller et diagram i samtalen (27/10-2026).
# Samme familie som billedvaerktoejerne: rene praesentationslag uden
# data-adgang. De stod i INGEN scope-liste overhovedet, saa hverken Bjoern
# eller husstanden kunne faa en kurve tegnet hvor samtalen foregaar.
_MEMBER_VISNING = frozenset({"vis_graf", "vis_widget", "render_mermaid"})

# Dokumenter — at SKABE en fil (27/10-2026, Bjørn: «dem skal vi osse have»).
#
# Målt før denne ændring: nul opret-værktøjer i hele kataloget. Huset kunne
# læse fem Google-formater gennem connectorer, men ikke lave en PDF, et
# regneark, et Word-dokument eller en præsentation — den ene ChatGPT-evne der
# slet ikke fandtes.
#
# De er sikre for husstanden af én grund: de genererer en NY fil og sender den
# gennem `publish_file`, som skriver i den kaldende brugers EGEN isolerede
# mappe. De læser intet og kan ikke overskrive noget.
#
# `pdf_read` er BEVIDST ikke med: den læser en vilkårlig sti eller URL og er
# derfor owner-only, som `read_file`.
_MEMBER_DOKUMENTER = frozenset({"pdf_create", "docx_create", "xlsx_create", "pptx_create"})

# Google-familien — kalender, mail, Drive, dokumenter (20/11-2026).
#
# Bjørn bad om at udvide husstandens værktøjer. Det her er den ene familie hvor
# udvidelsen er sikker af en STRUKTUREL grund og ikke af en vurdering: hvert kald
# går gennem `get_fresh_token(user_id, "google")`, og den slår op på den
# KALDENDE brugers EGEN forbindelse. Den falder ikke tilbage til ejeren — den
# returnerer None når brugeren ikke har forbundet sin konto. Michelle har sin
# egen Google-konto, så hun læser sin egen mail og sit eget drev, ikke Bjørns.
#
# Grænsen går ved de værktøjer der læser Jarvis' EGEN hukommelse på tværs af
# husstanden (`search_chat_history`, `search_sessions`, `recall`,
# `search_jarvis_brain`). De er BEVIDST ikke her: en samtale er privat, og det
# er netop den grænse §16.2's kryptering værner.
_MEMBER_GOOGLE = frozenset({
    "calendar_list_events", "calendar_create_event",
    "list_events", "create_event",
    "gmail_search", "gmail_list", "gmail_get", "gmail_modify", "gmail_send",
    "drive_search", "drive_download",
    "docs_read", "docs_append",
    "sheets_read", "sheets_write",
    "slides_read",
})

# Hverdagen — naa, planlaeg, husk (20/11-2026, Bjoern: «partner tool saet
# udvides med disse»). Oenskelisten kom fra en samtale mellem Michelle og
# Jarvis, hvor hun bad om de vaerktoejer en almindelig dag kraever.
#
# Hvert eneste af dem er sikre af en STRUKTUREL grund, ikke en vurdering:
#
#   `send_push_notification` laeser `current_user_id()` og pusher til den
#   bruger Jarvis betjener NU. Der findes ingen parameter for en modtager —
#   den kan per konstruktion ikke naa nogen andre end hende selv.
#
#   `pollinations_image` er noeglefri og gratis (samme familie som
#   `openrouter_image`, der allerede er tillad), saa den tilfoejer ingen
#   udgift ved siden af det hun allerede kan.
#
#   `todo_*` er bundet til sessionen, og `inbox*` er isoleret paa `bruger_id`
#   i db_inbox — hver bruger ser og afgoer kun sine EGNE poster. Det er den
#   samme isolation `CHAT_MODE_TOOLS_BASE` allerede regner med for ejeren.
#
# BEVIDST UDELADT — `notify_out`, `notify_channel_add/list/delete`:
# de laeser og skriver `~/.jarvis-v2/state/notify_channels.json`, som er ÉN
# global fil uden ejerskab. En husstandsbrugers `notify_channel_list` ville
# vise Bjoerns webhooks, og `notify_channel_delete` kunne fjerne dem. Det er
# ikke et rollevalg der mangler — det er en fil der mangler en ejer. Familien
# bliver tilgaengelig i det oejeblik kanalerne er per-bruger.
#
# BEVIDST UDELADT — `schedule_recurring`, `set_recurring_weekday_times`:
# de skriver til Jarvis' EGEN scheduler og opretter varige jobs der overlever
# samtalen. Det er en anden slags handling end at naa sit eget liv.
_MEMBER_HVERDAG = frozenset({
    # Proaktiv push — self-scoped gennem current_user_id()
    "send_push_notification",
    # Gratis billedgenerering (openrouter_image er allerede tillad)
    "pollinations_image",
    # Arbejdsliste — per session
    "todo_add", "todo_list", "todo_set", "todo_update_status", "todo_remove",
    # Indbakken — isoleret per bruger_id
    "inbox", "inbox_done", "inbox_drop",
})

_MEMBER_CHAT = (_MEMBER_CHAT_WEB | _MEMBER_CHAT_UTIL | _MEMBER_CHAT_MEM
                | _MEMBER_IMAGE | _MEMBER_VISNING | _MEMBER_DOKUMENTER
                | _MEMBER_GOOGLE | _MEMBER_HVERDAG)


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
_MEMBER_CODE_WEB = frozenset({"web_search", "web_scrape", "web_fetch", "analyze_image", "madopskrift"})
# 🔒 path-jailed til eget workspace (server-side, IKKE Jarvis' repo)
_MEMBER_CODE_FILE = frozenset({"read_file", "write_file", "edit_file", "find_files"})
# 🔒 connector-tools: bruger member'ens EGEN OAuth-token (per-bruger krypteret).
# Rører aldrig ejerens/Jarvis' GitHub. Yderligere gated af connected+enabled i runtime.
_MEMBER_CODE_CONNECTOR = frozenset({"github_list_issues", "github_list_prs"})
_MEMBER_CODE = (
    _MEMBER_CODE_OPERATOR | _MEMBER_CODE_WEB | _MEMBER_CODE_FILE
    | _MEMBER_CODE_CONNECTOR | _MEMBER_IMAGE | _MEMBER_VISNING
    | _MEMBER_DOKUMENTER
)


# ── Member COWORK ───────────────────────────────────────────────────────────
_MEMBER_COWORK = frozenset({
    "propose_plan", "revise_plan", "list_plans", "dismiss_plan",
    "todo_add", "todo_list", "todo_set", "todo_update_status", "todo_remove",
    "list_proposals", "discord_channel",
    # Madopskrifter (25/10-2026): read-only eksternt opslag, ingen skrivning
    # og ingen adgang til andres data — derfor også i cowork.
    "madopskrift",
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
    # `partner` har nøjagtig medlems-rettigheder. Husstands-adgangen (Sansernes
    # Arkiv) er en SEPARAT gate og giver ingen ekstra tools.
    from core.identity.household import is_member_like
    if is_member_like(role):
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
