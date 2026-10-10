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
    "inbox", "monitor_list", "verification_status", "decision_adherence_summary",
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


def is_allowed(name: str) -> bool:
    """Fail closed for autonomous calls; visible runs use their normal policy."""
    from core.services.run_autonomy_context import current_origin, is_autonomous

    if not is_autonomous():
        return True
    return str(name or "").strip() in allowed_tools_for_origin(current_origin())
