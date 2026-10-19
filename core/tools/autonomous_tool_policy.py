"""Explicit tool permissions for runs without a user present.

The ordinary owner cowork scope is intentionally broad. An autonomous run is
still owner-owned, but it must not inherit that scope: it may read, maintain
internal memory and keep plans, while actions in the outside world wait for a
visible user run. New tools are denied until reviewed here.
"""
from __future__ import annotations


AUTONOMOUS_TOOLS: frozenset[str] = frozenset({
    # Local read-only lookup. External connectors/network calls stay out.
    "read_file", "read_tool_result", "search", "grep", "glob", "list_dir",
    "find_files", "find_symbol", "find_usages", "git_status", "git_diff",
    "git_log", "git_show", "git_blame", "git_branch",
    # Runtime, session and internal-state observation.
    "central_query", "eventbus_recent", "context_pressure", "context_size_check",
    "heartbeat_status", "daemon_status", "health_status", "provider_health_status",
    "read_mood", "read_self_state", "read_self_docs", "read_model_config",
    "read_chronicles", "read_dreams", "read_identity_sketch",
    "read_project_notes", "read_signal_surface", "read_visual_memory",
    "search_sessions", "search_chat_history", "list_events", "list_flags",
    "get_flag", "list_signal_surfaces", "list_arcs", "list_crisis_markers",
    "list_context_versions", "list_learning_memos", "read_learning_memo",
    "list_prompt_experiments", "list_identity_pins", "list_proposals",
    "list_process_watches", "list_scheduled_tasks", "list_recurring",
    "list_self_wakeups", "list_initiatives", "list_plans", "list_side_tasks",
    "monitor_list", "verification_status", "decision_adherence_summary",
    "detect_stale_goals", "read_attachment", "verify_file_contains",
    "verify_service_active",
    # Internal memory: reads and additive or corrective writes only.
    "recall", "recall_memories", "recall_before_act", "recall_context_version",
    "recall_sensory_memories", "recall_reasoning", "search_memory",
    "search_jarvis_brain", "read_brain_entry", "read_memory_topic",
    "memory_graph_query", "memory_list_headings", "memory_check_duplicate",
    "memory_usage", "resurface_old_memory", "remember_this",
    "memory_upsert_section", "write_memory_topic", "record_sensory_memory",
    "note_add", "note_list", "note_search",
    # Indbakkens bogfoering (12/10-2026). Gaten naegter enhver mutation saa
    # laenge en af MINE EGNE poster har faaet nok leverede paamindelser — og
    # frigiver den KUN ved `inbox_done`/`inbox_drop` paa dens poster.
    #
    # Uden dem her er gaten en FAELDE, og det er maalt: `_prepare_call`
    # tjekker denne politik FOER inbox_gaten, saa et autonomt run kunne SE
    # posten, men aldrig lukke den — og dermed heller ikke sende, skrive eller
    # mutere resten af runnet. 12/10-2026 blev en recurring-brief blokeret og
    # kunne ikke frigives; indholdet var klaret, kvitteringen var umulig.
    #
    # `inbox` — LAESNINGEN — er fjernet 14/10-2026. Indbakken er den flade hvor
    # Jarvis moeder Bjoern: den kan naegte en mutation, og den laeses der hvor
    # nogen kan svare. Maalt samme dag kaldte et autonomt run `inbox` fem gange
    # og begyndte at arbejde paa Bjoerns poster; konklusionen endte i en session
    # ingen laeser. Udvejen bestaar UDEN den: gatens naegtelse navngiver de
    # id'er der skal lukkes (`inbox_gate._naegtelse`), saa runnet behoever ikke
    # se listen for at komme fri.
    #
    # Begge er bogfoering paa Jarvis' EGNE poster — samme klasse som
    # `remember_this` og `mark_wakeup_consumed`, som allerede er tilladte.
    # `done` kraever et terminalt udfald, `drop` kraever en begrundelse, og
    # begge spores. En AUTONOM afvisning af en post principalen har sat
    # `bloker` paa er naegtet i vaerktoejet selv — se `inbox_tools`.
    "inbox_done", "inbox_drop",
    # Internal plans. Scheduling external jobs and sending messages are excluded.
    "goal_create", "goal_decompose", "goal_get", "goal_list", "goal_update",
    "goal_update_status", "todo_add", "todo_list", "todo_remove", "todo_set",
    "todo_update_status", "todo_complete", "propose_plan", "revise_plan",
    "decision_get", "decision_list", "mark_wakeup_consumed",
    # A loaded schema may be inspected, but the resolved name is checked again
    # by load_more_tools and at execution after call_loaded_tool is unpacked.
    "load_more_tools", "call_loaded_tool",
})


# ── Pr. oprindelse: hver run-type får kun de værktøjer dens opgave kræver ──
#
# Målt 10/10-2026: ÉN global hvidliste tvang alle autonome runs ned på samme
# smalle sæt. En planlagt opgave — en medicin-påmindelse, et wait-state-tjek —
# kunne derfor ikke fuldføres, og natrutinen kunne ikke sanse. Bjørn 10/10-2026:
# «uddelegér tools når du sætter autonome runs og recurring op».
#
# Nøglen er kørslens `origin`: den bæres allerede i run_autonomy_context og
# sættes ét sted — dér hvor kørslen ved besked. En ukendt eller tom origin
# falder tilbage til BUND-sættet alene, så en NY run-type aldrig arver en
# udvidelse den ikke selv har fået. Tilladelsen er altså delegeret, ikke global.
ORIGIN_TOOLS: dict[str, frozenset[str]] = {
    # En recurring-opgave er godkendt af Bjørn på forhånd. Den må røre verden —
    # ellers er en påmindelse der ikke kan sendes ikke en påmindelse.
    "recurring": frozenset({
        "send_ntfy", "notify_user", "send_discord_dm", "send_discord_channel",
        "discord_channel", "send_webchat_message",
        "web_search", "web_fetch", "get_weather", "get_news",
        "bash",
    }),
    # Drømmen skal sanse og arkivere sit indtryk — ikke tale med verden.
    "dream": frozenset({"look_around", "mic_listen"}),
    # Heartbeat er motoren selv: den observerer og holder planer, og kan give
    # besked hvis den ser noget — men den rører ikke verden uden en opgave.
    "heartbeat": frozenset({"send_ntfy"}),
    # En self-wakeup er Jarvis der genoptager sit EGET arbejde i en session.
    # Den skal kunne undersøge og fortælle — ikke begynde nyt arbejde.
    # Nøglen er «wakeup»: det er hvad wakeup_dispatcher sender.
    "wakeup": frozenset({"bash", "send_webchat_message", "send_ntfy"}),
}


def allowed_tools_for_origin(origin: str) -> frozenset[str]:
    """Bund-sættet plus det kørslens oprindelse har fået delegeret."""
    extra = ORIGIN_TOOLS.get(str(origin or "").strip().lower(), frozenset())
    return AUTONOMOUS_TOOLS | extra


def presence_for_run(run) -> bool:
    """Er der et menneske i den anden ende af DENNE kørsel?

    SESSIONEN FØRST — ikke oprindelsen (Bjørn 19/10-2026: «det er en vækning,
    ikke et autonomt baggrunds-run»).

    En vækning lander i den samtale hvor Bjørn er. Behandlede vi den som et
    baggrunds-run, ankom den uden de værktøjer opgaven kræver: målt 19/10 gav
    `origin="inbox"` 104 værktøjer og hverken `bash`, `web_search` eller
    `notify_user`, mens `wakeup` gav 107. Svaret landede stadig i hans samtale
    — det var bare tandløst.

    To led skal holde, og de svarer på hver sit:

    1. Sessionen er ikke en system-silo. En `auto-recurring-…`-silo er ikke et
       sted nogen sidder.
    2. Han har talt i den for nylig. En app-session der ikke har været rørt i
       timer er ikke tilstedeværelse — den er en gammel række, og et run der
       arver hans rettigheder der, gør det uden vidner.

    Vinduet er hans eget: `_BRUGER_KARANTAENE_S` (10 min), den samme grænse
    vækkeren allerede bruger for «han er her». Genbrugt frem for kopieret, så
    de to ikke kan drive fra hinanden.

    Fail-closed: enhver fejl → False, og så gælder den autonome politik som før.
    """
    sid = str(getattr(run, "session_id", "") or "").strip()
    if not sid:
        return False
    try:
        from core.services.autonomous_sessions import is_system_session
    except Exception:  # en manglende klassifikation må lukke sættet, ikke åbne det
        return False
    if is_system_session(sid):
        return False
    try:
        from core.services.wakeup_dispatcher import _bruger_skrev_for_nylig
    except Exception:  # samme: uden en læser kan vi ikke se nogen
        return False
    try:
        return bool(_bruger_skrev_for_nylig(sid))
    except Exception:  # brækket historik-læsning lukker sættet — fail-closed
        return False


def is_allowed(name: str) -> bool:
    """Fail closed for autonomous calls; visible runs use their normal policy."""
    from core.services.run_autonomy_context import (
        current_origin, is_autonomous, user_present,
    )

    if not is_autonomous():
        return True
    # TILSTEDEVÆRELSE (19/10/2026): en kørsel der lander i en samtale hvor
    # Bjørn er, arver den sessions sæt. `is_autonomous` bliver ved med at være
    # sand — det er dét der giver `bash` sin indespærring — men politikken
    # spørger nu også om der er nogen i den anden ende. Uden dette led var
    # vækningen tandløs: den landede i hans samtale uden de værktøjer opgaven
    # krævede.
    if user_present():
        return True
    return str(name or "").strip() in allowed_tools_for_origin(current_origin())
