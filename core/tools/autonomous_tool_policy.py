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


def is_allowed(name: str) -> bool:
    """Fail closed for autonomous calls; visible runs use their normal policy."""
    from core.services.run_autonomy_context import is_autonomous

    if not is_autonomous():
        return True
    return str(name or "").strip() in AUTONOMOUS_TOOLS
