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
import re
from contextlib import contextmanager
from typing import Any, Iterable, Iterator

logger = logging.getLogger(__name__)

# Agent-contract-v1 har EN modelvendt oprettelsesvej: ``Task``. De gamle navne
# bliver ikke blot skjult fra en bestemt mode; de traekkes fra alle scopes og
# afvises i eksekveringsporten. Dermed kan load_more_tools, en gammel session-
# laas eller samtalehistorik ikke genoplive en parallel agent-livscyklus.
RETIRED_AGENT_CREATION_TOOLS: frozenset[str] = frozenset({
    "scout_agent",
    "spawn_agent_task",
    "dispatch_code_mode_task",
    "dispatch_to_claude_code",
    "task",
})

_PERSONAL_CONTEXT_RE = re.compile(
    r"\b(min|mit|mine|vores|jarvis|workspace|memory|hukommelse|huske|aftalt|"
    r"besluttet|my|our|remember|decided)\b",
    re.IGNORECASE,
)
_EXTERNAL_CONTEXT_RE = re.compile(
    r"\b(web|internet|nyheder|latest|seneste|pris|kurs|weather|news|google|"
    r"website|url|http|external|third[- ]party)\b",
    re.IGNORECASE,
)

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
    # Git-laesning af husets kodebase + udlevering af en vilkaarlig source_path
    # (27/10-2026). De staar i BASE for at ejeren kan naa dem i chat, og HER
    # for at husstanden ikke kan — samme moenster som `search_jarvis_brain`
    # ovenfor. En member maa ikke laese serverens kode, og `publish_file` ville
    # give dem den samme fil gennem et download-link i stedet.
    "git_log", "git_diff", "git_status", "git_branch", "git_blame",
    "publish_file",
    # Dokument-laesning (27/10-2026, Bjoern). `pdf_read` kan laese en
    # VILKAARLIG sti eller URL — samme fil-adgang som `read_file`. Den hoerer
    # derfor i owner-strippet og ikke i kernen, selvom den kun laeser.
    "pdf_read",
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
    "cancel_agent",
    # agent-contract-v1: owner-only indtil flerbrugerpiloten (spec 12.4) - andre brugeres
    # agenter kraever den proevede ejer-/rutegraense foer deres modeller faar vaerktoejet.
    "Task", "followup_agent", "wait_agents", "interrupt_agent", "close_agent",
    "integrate_agent_work", "convene_agent_council", "review_agent_work",
    "cancel_recurring",
    "cancel_self_wakeup",
    "cancel_task",
    "list_recurring",
    "list_self_wakeups",
    "mark_wakeup_consumed",
    "add_wakeup_extra",
    "schedule_recurring",
    "schedule_self_wakeup",
    # Selv-startede sessioner (4/10-2026). Owner-only med vilje: et
    # selv-startet run er den dyreste handling jeg kan tage på egen hånd —
    # hele værktøjskassen, ingen bruger til at godkende undervejs. En
    # husstandsmedlem må ikke kunne starte runs i Bjørns navn.
    "start_session",
    # Min egen overdragelse (4/10-2026). Owner-only: capsulen er MIN
    # tilstand, ikke en flade en husstand kan skrive i.
    "write_handover",
    "flag_side_task", "activate_side_task", "dismiss_side_task", "list_side_tasks",
    "snooze_side_task", "wake_side_task",
})

# Chat-mode allowlist (gælder ALLE roller i chat). Member/guest får yderligere
# OWNER_ONLY_TOOLS strippet ovenpå (så fx search_jarvis_brain kun er owner).
CHAT_MODE_TOOLS_BASE: frozenset[str] = frozenset({
    # Fast escape-hatch til katalogets lange hale. Pruneren pinner den, men
    # scope-porten skal lade den passere først — ellers er pinningen virkningsløs.
    "load_more_tools",
    # Self-scoped UI preference; handler derives the verified current principal.
    "set_chat_flow_preference",
    # Owner-only via OWNER_ONLY_TOOLS; kan bruges i både chat og code uden
    # at bryde kontrakten om at CHAT_MODE_OWNER_EXTRA kun er fil-læsning.
    "flag_side_task", "activate_side_task", "dismiss_side_task", "list_side_tasks",
    "snooze_side_task", "wake_side_task",
    # Indbakken (Opgave 5, 3/10-2026). ALLE roller, ikke owner-only:
    # isolationen haandhaeves paa `bruger_id` i db_inbox, saa hver bruger ser
    # og afgoer kun sine EGNE poster. Var de owner-only, kunne et
    # husstandsmedlem hverken se eller lukke det der venter paa dem — og en
    # post de ikke kan lukke er en post der staar for evigt.
    #
    # `inbox` er en LAESNING og skal altid slippe igennem gaten; uden den
    # kunne han ikke se hvad der blokerer. `inbox_done`/`inbox_drop` er de
    # eneste to veje en blokerende post frigives.
    "inbox", "inbox_done", "inbox_drop",
    # Agent-contract-v1: samme Task-vej i chat og code. Runtime udleder selv
    # read-only researcher vs. worktree-executor fra subagent_type.
    "Task", "wait_agents", "list_agents", "send_message_to_agent",
    "followup_agent", "interrupt_agent", "close_agent", "review_agent_work",
    "convene_agent_council", "integrate_agent_work",
    # Kanalen til hans egen maskine. Gaten sidder i modulet (owner-only), ikke
    # her — men uden for scope kunne han slet ikke aabne den.
    "operator_channel",
    # MCP: hele oekosystemet af eksterne vaerktoejer. Uden den i scope er
    # registeret en adressebog uden telefon.
    "mcp",
    # Fortryd en hel redigeringsrunde.
    "checkpoint",
    # ── Kontinuitetens to haandtag (4/10-2026) ────────────────────────────
    #
    # Maalt samme dag: begge laa i `_TOOL_HANDLERS` og i INGEN af listerne
    # der afgoer hvad der faktisk SENDES — hverken her, i
    # `REQUIRED_LAZY_TOOL_NAMES` eller i `SAFETY_FLOOR`. Kaldbare og
    # usynlige, samme moenster som `read_attachment` (6/9) og
    # billedvaerktoejerne (13/9).
    #
    # De staar nu BAADE her og i garantilisten, og det er ikke dobbelt
    # arbejde: garantilisten fæstner dem i det 48-store loft og forener dem
    # ind i session-laasen — men den vej forudsætter at laasen er TÆNDT
    # (`session_tool_pin_enabled`). Uden medlemskab her ville kill-switchen
    # tage dem med sig i chat-scope, og det er den scope Bjoern skriver i.
    #
    # Owner-only: begge staar i `OWNER_ONLY_TOOLS`. Et selv-startet run er
    # den dyreste handling Jarvis kan tage alene — hele vaerktoejskassen,
    # ingen bruger til at godkende undervejs — og en overdragelse skrives i
    # hans navn. Member/guest faar dem strippet af rollegaten.
    "start_session", "write_handover",
    # At se. Desk og mobil kan uploade billeder (POST /attachments), men
    # vaerktoejet der kigger paa dem stod i INGEN scope — saa et skaermbillede
    # i chat var noget han kunne modtage og ikke se paa. 6/9-2026.
    "read_attachment",
    # At VISE. Maalt 27/10-2026 (Bjoern): `vis_graf`, `vis_widget` og
    # `render_mermaid` stod i INGEN scope-liste — hverken chat, code eller
    # cowork — praecis samme moenster som `read_attachment` (6/9) og
    # billedvaerktoejerne (13/9): bygget, korrekt, og usynligt dér hvor
    # samtalen foregaar. En graf eller et diagram ER svaret naar tal eller
    # struktur er pointen; uden dem bliver det en mur af prosa.
    #
    # De hoerer i KERNEN og ikke i owner-listen: de tegner det data kalderen
    # allerede har, laeser intet og skriver intet. Widget'en renderes
    # sandboxet uden netvaerk, og alle tre er rene praesentationslag.
    "vis_graf", "vis_widget", "render_mermaid",
    # Git-laesning + udlevering (27/10-2026, Bjoern). De seks git-vaerktoejer
    # stod i INGEN liste — hverken chat, code eller cowork — saa jeg kunne ikke
    # svare paa «hvad aendrede den commit» i den mode samtalen foregaar i.
    # `git_status` var vaerre: den stod i promptens katalog under «Filer & kode»
    # og i nul scopes, altsaa pegede kataloget paa en doed evne.
    #
    # De staar HER og ikke i CHAT_MODE_OWNER_EXTRA, fordi den liste er
    # kontraktbundet til at vaere ren laesning (se test_tool_scoping). De er i
    # stedet owner-only via OWNER_ONLY_TOOLS nedenfor — samme moenster som
    # `search_jarvis_brain`: de laeser husets kodebase, og et husstandsmedlem
    # maa ikke se den.
    "git_log", "git_diff", "git_status", "git_branch", "git_blame",
    # At UDLEVERE en fil. Den kopierer `source_path` — en VILKAARLIG sti — til
    # brugerens egen files-mappe og returnerer et download-link. Samme
    # fil-adgang som `read_file`, og derfor samme owner-strip: for en member
    # ville den vaere en omvej til serverens filer gennem et link.
    "publish_file",
    # At SKABE et dokument (27/10-2026, Bjoern: «dem skal vi osse have»).
    # Maalt for denne aendring: huset kunne LAESE fem Google-formater gennem
    # connectorer, men der fandtes NUL vaerktoejer der kunne oprette en fil —
    # `pdf_read` fandtes, `pdf_create` gjorde ikke.
    #
    # De fire staar i KERNEN for alle roller, i modsaetning til `pdf_read`
    # ovenfor, fordi de hverken laeser eller overskriver noget: de genererer
    # en ny fil i en midlertidig mappe og sender den gennem `publish_file`,
    # som skriver i den kaldende brugers EGEN isolerede mappe. En member kan
    # altsaa kun skabe sin egen fil, aldrig roere en andens — og en
    # opret-funktion der var owner-only ville goere ChatGPT-pariteten
    # halv, praecis dér hvor husstanden arbejder.
    "pdf_create", "docx_create", "xlsx_create", "pptx_create",
    # `pdf_read` staar HER ogsaa (ikke kun i OWNER_ONLY_TOOLS): rollestrippet
    # fjerner for husstanden, men uden en scope-liste ville den ogsaa vaere
    # usynlig for EJEREN — maalt 27/10-2026, foerste forsoeg gav praecis det.
    "pdf_read",
    # Arbejdshukommelse. Prompten har hele tiden vist hans todos og reglen om
    # max ÉN i gang — uden at han kunne skrive til dem.
    "todo_list", "todo_add", "todo_update_status", "todo_set", "todo_remove",
    # Web / viden
    "web_search", "web_fetch", "web_scrape", "get_news",
    # Data
    "get_weather", "get_exchange_rate", "wolfram_query",
    # Madopskrifter (25/10-2026, Bjørn). Michelle spurgte, og svaret fandtes
    # ikke i nogen scope: kilderne er nøglefri og read-only, og oversættelsen
    # ligger inde i værktøjet selv. Derfor hører det i KERNEN for alle roller
    # — ikke i CHAT_MODE_OWNER_EXTRA, som kun er owner.
    "madopskrift",
    # Geolocation (read-only eksterne opslag)
    "geolocation_lookup", "geocode", "reverse_geocode", "route_directions", "nearby_search",
    # Vision — at SE et billede
    "analyze_image",
    # …og at TEGNE et. Vaerktoejerne blev bygget 13/9-2026 og stod i INGEN
    # mode-liste: maalt gav baade chat og code «INGEN billedvaerktoejer», og de
    # var kun naabare i cowork. Bygget, korrekt, usynligt praecis dér hvor
    # arbejdet foregaar — samme moenster som `read_attachment` ovenfor, hvor et
    # skaermbillede var noget han kunne modtage og ikke se paa.
    "openrouter_image", "openrouter_image_edit",
    # Hukommelse — read (2026-09-04: `recall` = ét tool over alle kilder)
    "recall", "search_memory", "memory_graph_query", "resurface_old_memory",
    "search_jarvis_brain", "read_brain_entry",
    # Repo-dokumentation — SEPARAT pulje fra hukommelsen (23/10-2026). Eget
    # indeks, egen rangering; kan ikke fortrænge Jarvis' egne noter.
    "repo_recall",
    # Hukommelse — write (egen + brugerens)
    "remember_this", "memory_upsert_section", "adjust_mood",
    # Selv-indsigt — read
    "read_mood", "read_self_state", "read_chronicles", "read_dreams",
    "read_model_config",
    # UI-panel-kald (desk) — fremvis noget i preview/højre-panel (§8.2)
    "open_ui_panel",
    # Desk-vinduet indefra (Claude Desktops ccd_view, 19/9-2026)
    "desk_get_layout", "desk_show_pane", "desk_close_pane",
    # Jarvis' EGEN browser inde i desk (21/9-2026) — en flade han og Bjørn deler.
    "jarvis_browser_open", "jarvis_browser_navigate", "jarvis_browser_read",
    "jarvis_browser_click", "jarvis_browser_type", "jarvis_browser_screenshot",
    "jarvis_browser_tabs", "jarvis_browser_close",
    # App-self-control (desk) — foreslå skift chat→code mode (brugeren godkender)
    "request_app_action",
    # Companion-push — naa brugeren proaktivt paa deres egne enheder (device-routet)
    "send_push_notification",
})

# Ekstra værktøjer owner (kun) får i chat — fil-læsning til kode-snak.
# KONTRAKT: denne liste er KUN læsning, og test_tool_scoping kræver eksakt
# disse tre. Git-læsning og `publish_file` ligger derfor i BASE sammen med
# `OWNER_ONLY_TOOLS`-strippet i stedet — samme mønster som `search_jarvis_brain`
# (27/10-2026: de blev først lagt her, og kontrakten fangede det med rette).
CHAT_MODE_OWNER_EXTRA: frozenset[str] = frozenset({
    "read_file", "search", "find_files",
})

# Code-mode allowlist. Owner = container + workstation + dispatch; member/guest =
# kun workstation (operator-bridge, sandboxet til deres egen maskine).
CODE_MODE_TOOLS_BASE: frozenset[str] = frozenset({
    # Indbakken (Opgave 5, 3/10-2026). ALLE roller, ikke owner-only:
    # isolationen haandhaeves paa `bruger_id` i db_inbox, saa hver bruger ser
    # og afgoer kun sine EGNE poster. Var de owner-only, kunne et
    # husstandsmedlem hverken se eller lukke det der venter paa dem — og en
    # post de ikke kan lukke er en post der staar for evigt.
    #
    # `inbox` er en LAESNING og skal altid slippe igennem gaten; uden den
    # kunne han ikke se hvad der blokerer. `inbox_done`/`inbox_drop` er de
    # eneste to veje en blokerende post frigives.
    "inbox", "inbox_done", "inbox_drop",
    # Et skaermbillede af en fejl er ofte den korteste vej til at forstaa den.
    "read_attachment",
    # At VISE — samme begrundelse som i chat-listen ovenfor (27/10-2026). En
    # graf eller et diagram ER svaret naar tal eller struktur er pointen, og
    # behovet er ikke mindre fordi man er i code mode.
    "vis_graf", "vis_widget", "render_mermaid",
    # Git-laesning + udlevering. `git_status` stod i promptens katalog under
    # «Filer & kode» — og i INGEN scope-liste, hverken her eller i chat. Den
    # har altsaa vaeret doed hele tiden, mens kataloget pegede paa den.
    # Maalt 27/10-2026. De seks er read-only opslag i det repo man sidder i;
    # det er praecis den mode de hoerer til.
    "git_log", "git_diff", "git_status", "git_branch", "git_blame",
    "publish_file",
    # Dokumenter (27/10-2026): at SKABE en fil hoerer til i code mode, og
    # `pdf_read` er den naturlige modpart naar man vil laese hvad man lavede.
    "pdf_create", "docx_create", "xlsx_create", "pptx_create", "pdf_read",
    "desk_get_layout", "desk_show_pane", "desk_close_pane",
    # Jarvis' EGEN browser inde i desk (21/9-2026): han kan se en side OG vise
    # den til Bjørn samtidig — den ene flade hvor begge kan pege.
    "jarvis_browser_open", "jarvis_browser_navigate", "jarvis_browser_read",
    "jarvis_browser_click", "jarvis_browser_type", "jarvis_browser_screenshot",
    "jarvis_browser_tabs", "jarvis_browser_close",
    "operator_channel",
    "mcp",
    "checkpoint",
    "operator_read_file", "operator_write_file", "operator_edit_file",
    "operator_bash", "operator_glob", "operator_grep", "operator_list_dir",
    "operator_bash_session_open", "operator_bash_session_run",
    "operator_bash_session_close", "operator_bash_session_list",
    # 6/9-2026: de nye operator-vaerktoejer skal med her, ellers er de usynlige
    # netop dér hvor de betyder mest. Det er ikke nok at registrere et vaerktoej
    # — code-scope annoncerer kun 21, og et vaerktoej uden for listen findes
    # reelt ikke for modellen.
    "operator_multi_edit",
    "operator_run_in_background", "operator_bash_output", "operator_kill_shell",
    # Samme kontraktvej som chat: ingen separat scout- eller kode-dispatcher.
    "Task", "wait_agents", "list_agents", "send_message_to_agent",
    "followup_agent", "interrupt_agent", "close_agent", "review_agent_work",
    "convene_agent_council", "integrate_agent_work",
    # Repo-dokumentation (23/10-2026). Hoerer netop her: en kode-opgave er dér
    # man har brug for at laese hvad der ER skrevet om systemet. (Bemaerk at
    # `recall` selv ikke staar i denne liste — memory-soegning er i dag kun
    # naaelig i chat-scope. Det er en separat mangel, ikke aendret her.)
    "repo_recall",
    # Arbejdshukommelse — en kode-opgave er praecis dér man har brug for den.
    "todo_list", "todo_add", "todo_update_status", "todo_set", "todo_remove",
    # Madopskrifter (25/10-2026): nøglefri, read-only eksterne opslag. Samme
    # familie som vejr — og et værktøj der kun findes i chat findes reelt
    # ikke for den der arbejder i code.
    "madopskrift",
    # App-self-control (desk) — foreslå fuld adgang (trust) i code mode
    "request_app_action",
    # Billeder. Ogsaa i kode-mode: et diagram, en mockup eller en illustration
    # til en README hoerer til i arbejdet, ikke i en anden fane.
    "openrouter_image", "openrouter_image_edit",
})
CODE_MODE_OWNER_EXTRA: frozenset[str] = frozenset({
    "read_file", "write_file", "edit_file", "search", "find_files", "bash",
    "flag_side_task", "activate_side_task", "dismiss_side_task", "list_side_tasks",
    "snooze_side_task", "wake_side_task",
    # Owner-only operator backup-channel (jarvis-code bash reroute). Deliberately
    # NOT in the member/guest base scope — a non-owner must never get the
    # dialog-free operator reroute.
    "operator_session_open", "operator_session_run", "operator_session_close",
})

# Local-exec-ONLY tools: har INGEN server-side executor og kan KUN køre klient-lokalt
# i jarvis-code (Path B). `task` = nested subagent / explore (jc_agent_loop._execute_
# task_tool). Modsat bash/operator_* (der også har en server/bro-executor) må disse
# ALDRIG annonceres uden for et local_tool_exec-run — ellers kunne modellen kalde et
# værktøj serveren ikke kan udføre. Annoncering gates på current_local_exec() nedenfor.
LOCAL_EXEC_ONLY_TOOLS: frozenset[str] = frozenset()

# Computer-use: mus, tastatur, skaermbillede, OCR (21/9-2026).
#
# Bjørn 21/9-2026: «Det skal kun være i code mode, så alle 17». De står derfor i
# deres EGET sæt og IKKE i `CODE_MODE_TOOLS_BASE`: chat-scope arver base-listen
# når en desk-bro er paret (se `allowed_tool_names`), og den arv må ikke omfatte
# musen og tastaturet — i chat kan man ikke se den skærm man peger på.
#
# Kæden er: annonceres kun i code → broen sender mode="code" → bridge.ts'
# `_LOCAL_EXECUTION_MODES` slipper dem igennem. Både scoping og broen håndhæver
# det, så et enkelt lags fejl ikke åbner musen.
#
# Listen er ikke skrevet af her: `computer_use_samtykke` deler dem allerede i
# HANDLENDE (kræver samtykke) og LÆSENDE (frit) — samme familie, og to lister
# ville drive fra hinanden. Ni handlende + otte læsende = 17.
try:
    from core.services.computer_use_samtykke import HANDLENDE as _CU_HANDLENDE
    from core.services.computer_use_samtykke import LAESENDE as _CU_LAESENDE

    COMPUTER_USE_TOOLS: frozenset[str] = _CU_HANDLENDE | _CU_LAESENDE
except Exception:  # pragma: no cover — defensiv: scoping må ikke dø ved import
    # Fejler den, bliver computer-use usynligt (fail-closed for en rettighed der
    # rører hans mus) — men det SKAL siges højt, ikke ske stille.
    logger.warning(
        "computer_use_samtykke kunne ikke importeres — mus/tastatur forbliver usynlige"
    )
    COMPUTER_USE_TOOLS = frozenset()

# §17: værktøjer der eksekverer LOKALT på brugerens maskine i code mode. Deres rå
# resultat bliver på maskinen; kun summary krydser via bro_broker. bridge.ts bruger
# dette til mode-aware routing (§17.6.1).
LOCAL_EXECUTION_TOOLS: frozenset[str] = (
    CODE_MODE_TOOLS_BASE
    | CODE_MODE_OWNER_EXTRA
    | LOCAL_EXEC_ONLY_TOOLS
    | COMPUTER_USE_TOOLS
)


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


def reset_local_exec(token: contextvars.Token) -> None:
    _local_exec_var.reset(token)


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


def _phone_tool_names() -> frozenset[str]:
    """Telefonens vaerktoejer — hentet fra ét sted, ikke gentaget her.

    Lazy import, fordi ``phone_tools`` haenger paa broen og dette modul ligger
    under den. Cachet paa funktionen, saa porten ikke betaler et import-opslag
    pr. tur.
    """
    cache = getattr(_phone_tool_names, "_cache", None)
    if cache is None:
        try:
            from core.tools.phone_tools import PHONE_TOOL_NAMES
            cache = frozenset(PHONE_TOOL_NAMES)
        except Exception:
            cache = frozenset()
        _phone_tool_names._cache = cache  # type: ignore[attr-defined]
    return cache


def _owner_has_live_phone() -> bool:
    """True hvis en TELEFON er forbundet for nuvaerende bruger.

    Skelner paa ``capabilities``, ikke paa klientnavn: en klient der melder
    telefonens vaerktoejer ER telefonen. Det er den samme mekanik som
    routingen bruger, saa porten og valget kan ikke komme til at vaere uenige.

    Modstykket til ``_owner_has_live_bridge``: telefon-vaerktoejerne dukker
    kun op naar der er en telefon at udfoere dem paa — overfladen udvides
    ikke naar intet er paret. Self-safe → False ved tvivl.
    """
    try:
        from core.identity.workspace_context import current_user_id
        from core.services import bridge_presence
        uid = current_user_id()
        if not uid:
            return False
        info = bridge_presence.all_presence().get(str(uid)) or {}
        telefon_navne = _phone_tool_names()
        if not telefon_navne:
            return False
        klienter = info.get("clients")
        if isinstance(klienter, dict):
            for c in klienter.values():
                if telefon_navne & set((c or {}).get("capabilities") or ()):
                    return True
            return False
        # Aeldre presence-form uden «clients» (én proces der endnu ikke har
        # genpubliceret): fald tilbage til den flade capability-liste.
        return bool(telefon_navne & set(info.get("capabilities") or ()))
    except Exception:
        return False


def _phone_adb_tool_names() -> frozenset[str]:
    """ADB-vaerktoejernes navne — ét sted, ikke gentaget her."""
    cache = getattr(_phone_adb_tool_names, "_cache", None)
    if cache is None:
        try:
            from core.tools.phone_adb import PHONE_ADB_TOOL_NAMES
            cache = frozenset(PHONE_ADB_TOOL_NAMES)
        except Exception:
            cache = frozenset()
        _phone_adb_tool_names._cache = cache  # type: ignore[attr-defined]
    return cache


def _adb_er_opsat() -> bool:
    """Er der overhovedet en telefon at pege adb paa?

    Gater paa CONFIG, ikke paa presence — modsat ``_owner_has_live_phone``.
    ADB gaar uden om appen, saa broen siger intet om hvorvidt vejen findes;
    det goer ``phone_adb_address`` i runtime.json. Er den ikke sat, er
    vaerktoejerne ubrugelige, og saa skal de heller ikke staa i kataloget og
    fylde.

    Ikke cachet: adressen kan saettes uden en genstart, og en tur der lige er
    blevet sat op skal virke med det samme.
    """
    try:
        from core.runtime.secrets import read_runtime_key
        return bool(str(read_runtime_key("phone_adb_address") or "").strip())
    except Exception:
        return False


def _forbundne_connector_vaerktoejer() -> frozenset[str]:
    """Vaerktoejer fra apps brugeren FAKTISK har forbundet.

    Fejlen 7/9-2026: alle syv Google-connectors stod som forbundet og
    aktiveret, og prompten fortalte ham «du HAR adgang til dem lige nu via dine
    vaerktoejer — brug dem i stedet for at sige at du ikke kan». Men
    scope-porten havde ingen af dem i chat- eller code-listen; de fandtes kun i
    cowork. Appsne koerer i chat.

    Han fik altsaa at vide at han havde adgang, havde ingen vaerktoejer, og
    blev udtrykkeligt bedt om ikke at sige at han ikke kunne. Den kombination
    inviterer til at han finder paa noget.

    Listen kommer fra connector-registret (``tools`` pr. connector), saa der er
    ét sted der ved hvad en app laaser op. Kun ``connected AND enabled``
    taeller — en frakoblet app aabner ingenting, og overfladen udvides derfor
    ikke naar intet er forbundet. Self-safe: fejler opslaget, gives intet.
    """
    try:
        from core.identity.workspace_context import current_user_id
        from core.services.connectors import list_for_user
        uid = current_user_id()
        if not uid:
            return frozenset()
        ud: set[str] = set()
        for c in list_for_user(str(uid)) or []:
            if not (c.get("connected") and c.get("enabled")):
                continue
            ud.update(str(t) for t in (c.get("tools") or ()) if t)
        return frozenset(ud)
    except Exception:
        return frozenset()


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
            result = (
                set(CODE_MODE_TOOLS_BASE) | CODE_MODE_OWNER_EXTRA | LOCAL_EXEC_ONLY_TOOLS
            ) & names
            # Computer-use (21/9-2026) — KUN her. Bjørn: «Det skal kun være i code
            # mode, så alle 17». Bevidst IKKE i chat-grenen nedenfor: den arver
            # CODE_MODE_TOOLS_BASE når broen er paret, og mus/tastatur hører ikke
            # til i en samtale hvor man ikke kan se skærmen man peger på.
            result |= COMPUTER_USE_TOOLS & names
            if _owner_has_live_phone():
                result |= _phone_tool_names() & names
            if _adb_er_opsat():
                result |= _phone_adb_tool_names() & names
            result |= _forbundne_connector_vaerktoejer() & names
        elif scope == "chat":
            result = (set(CHAT_MODE_TOOLS_BASE) | CHAT_MODE_OWNER_EXTRA) & names
            # Bjørn 2026-07-01: owner skal kunne nå sin EGEN paret desktop fra mobil chat
            # (bro-tools kører på hans maskine). Men KUN når en desk-bro faktisk er forbundet
            # (presence) — så mobil-chat får operator-tools uden at skulle i code mode, og
            # overfladen udvides ikke når intet er paret. Godkendelses-kort gater risiko.
            if _owner_has_live_bridge():
                result |= set(CODE_MODE_TOOLS_BASE) & names
            # Telefonen: samme princip som desk-undtagelsen ovenfor. Bjoern
            # skriver mest fra mobil-chatten, saa uden det her ville
            # telefon-vaerktoejerne vaere usynlige praecis dér hvor de bruges.
            if _owner_has_live_phone():
                result |= _phone_tool_names() & names
            if _adb_er_opsat():
                result |= _phone_adb_tool_names() & names
            # Forbundne apps aabner deres egne vaerktoejer. Uden det staar der
            # i prompten at han har adgang, mens vaerktoejerne er filtreret fra.
            result |= _forbundne_connector_vaerktoejer() & names
        else:
            result = names  # cowork / ubegrænset: alt mode-passende = alt
    else:
        # Non-owner: permission_engine er sandheden (sikkerhed + mode-passende sæt).
        from core.services.permission_engine import allowed_tools as _perm_allowed
        mode = scope if scope in ("chat", "code", "cowork") else "cowork"
        perm = _perm_allowed(role=role, mode=mode)
        result = set(perm) & names

    # Local-exec-only tools (`task`/explore) har ingen server-executor → må KUN
    # præsenteres i et local_tool_exec-run (jarvis-code Path B). Uden for det (autonom,
    # cowork-catch-all `result = names`, desk-container-code) fjernes de, så modellen
    # aldrig ser et værktøj den ikke kan bruge. current_local_exec() sættes ved
    # run-setup (visible_runs) — samme ContextVar som driver Path B-prompt-injektionen.
    if not current_local_exec():
        result = result - LOCAL_EXEC_ONLY_TOOLS

    result -= RETIRED_AGENT_CREATION_TOOLS
    result = _apply_computer_use_policy(result)
    from core.tools.autonomous_tool_policy import is_allowed as _autonomous_allowed
    return {name for name in result if _autonomous_allowed(name)}


def preferred_tools_for_user_message(user_message: str) -> list[str]:
    """Order hint for tool choice; does not grant or revoke permissions."""
    text = str(user_message or "")
    if _PERSONAL_CONTEXT_RE.search(text) and not _EXTERNAL_CONTEXT_RE.search(text):
        return ["recall", "search_memory", "search_jarvis_brain", "read_self_state"]
    if _EXTERNAL_CONTEXT_RE.search(text):
        return ["web_search", "web_fetch", "recall"]
    return []


def tool_routing_hint(user_message: str) -> str:
    """Prompt hint for personal/internal vs external lookup intent."""
    preferred = preferred_tools_for_user_message(user_message)
    if not preferred:
        return ""
    if preferred[0] == "web_search":
        return (
            "Tool routing: brug eksterne web/data-tools kun når brugeren beder om "
            "aktuel/offentlig/ekstern viden; ellers prøv Jarvis' egne kilder først."
        )
    return (
        "Tool routing: dette ligner personlig/intern kontekst. Prøv recall/"
        "search_memory/Jarvis brain før web_search; brug tredjeparts-kilder kun ved "
        "eksplicit ekstern/aktuel forespørgsel."
    )


def is_tool_allowed(*, role: str, scope: str, name: str) -> bool:
    """Må (role, scope) eksekvere værktøjet `name`? (Spor A — serverside håndhævelse.)

    Owner / unbound ("") → altid True: dig + betroede interne/daemon-kald, der
    kører uden bundet non-owner-rolle. Non-owner → `allowed_tool_names` (som er
    permission_engine + computer-use-policy → samme sandhed som model-filteret).
    """
    if name in RETIRED_AGENT_CREATION_TOOLS:
        return False
    from core.tools.autonomous_tool_policy import is_allowed as _autonomous_allowed
    if not _autonomous_allowed(name):
        return False
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
    try:  # agent-contract-v1: kontrakt-vaerktoejerne findes kun naar motoren er taendt
        from core.tools.agent_contract_tools import hidden_contract_tools
        locked = set(locked) | set(hidden_contract_tools())
    except Exception:
        logger.warning("agent-kapabilitetsfilteret kunne ikke koere", exc_info=True)
    return [d for d in defs if _fn_name(d) in allow and _fn_name(d) not in locked]
