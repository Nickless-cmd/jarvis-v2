"""Contextual tool pruning for GitHub Copilot / OpenAI-compatible providers.

OpenAI's chat completions API enforces a hard limit of 128 tools per request.
Jarvis currently exposes 162 tools. This module picks the best 128 per
request so nothing is silently dropped by the provider.

Strategy is deterministic (no LLM call):
  1. Tier 1 — core tools always included (~95)
  2. Tier 2 default "comfort" set — common channels/HA, always if budget allows
  3. Tier 2 keyword-matched tools — scored against user_message + recent usage
  4. Remainder filled lexicographically for stability

Only applied to Copilot paths (caller decides). Ollama and other providers
keep the full 162-tool catalog.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Iterable


MAX_TOOLS = 128


TIER_1_ALWAYS_ON: frozenset[str] = frozenset({
    "read_file", "write_file", "edit_file", "search", "find_files", "bash",
    "publish_file", "read_tool_result", "read_attachment", "list_attachments",
    "read_self_docs", "read_self_state", "read_mood", "read_model_config",
    "read_chronicles", "read_dreams", "adjust_mood",
    "search_memory", "recall_memories", "memory_upsert_section",
    "memory_list_headings", "memory_check_duplicate", "memory_consolidate",
    "record_sensory_memory", "recall_sensory_memories", "search_chat_history",
    "search_sessions",
    "git_log", "git_diff", "git_status", "git_branch", "git_blame",
    "schedule_task", "list_scheduled_tasks", "cancel_task", "edit_task",
    "list_initiatives", "push_initiative", "queue_followup",
    "propose_source_edit", "propose_git_commit", "approve_proposal",
    "list_proposals",
    "goal_create", "goal_update", "goal_list", "goal_get",
    "decision_create", "decision_review", "decision_list", "decision_get",
    "decision_revoke",
    "composite_propose", "composite_list", "composite_get", "composite_invoke",
    "composite_approve", "composite_revoke",
    "heartbeat_status", "trigger_heartbeat_tick", "eventbus_recent",
    "update_setting", "internal_api", "db_query", "deep_analyze",
    "semantic_search_code",
    "smart_compact", "compact_context", "context_size_check",
    "list_signal_surfaces", "read_signal_surface",
    "my_project_status", "my_project_journal_write",
    "my_project_accept_proposal", "my_project_declare",
    "web_fetch", "web_search", "web_scrape",
    "calculate", "unit_convert", "percentage", "wolfram_query",
    "service_status", "process_list", "disk_usage", "memory_usage",
    "notify_user", "send_webchat_message", "send_ntfy",
    "daemon_status",
    "read_archive", "get_weather", "get_exchange_rate", "get_news",
    "convene_council", "quick_council_check", "recall_council_conclusions",
    "read_visual_memory",
    # New core ergonomics from T/X/E/P-series — must always be visible
    # otherwise Jarvis "forgets" he has them after pruning kicks in.
    "bash_session_open", "bash_session_run", "bash_session_close", "bash_session_list",
    "todo_list", "todo_set", "todo_add", "todo_update_status", "todo_remove",
    "tail_log", "gpu_status", "run_pytest",
    "verify_file_contains", "verify_service_active", "verify_endpoint_responds",
    "monitor_open", "monitor_close", "monitor_list",
    "check_surprises", "check_good_enough",
    "delegation_advisor",
    "propose_plan", "approve_plan", "dismiss_plan", "list_plans",
    "classify_clarification",
    "flag_side_task", "list_side_tasks", "dismiss_side_task", "activate_side_task",
    "smart_outline",
    # Today's additions (2026-04-27) — must be Tier 1 or pruning hides them
    # Reasoning layer (R1/R2/R3)
    "reasoning_classify", "verification_status", "recommend_escalation",
    # Context engineering
    "context_pressure", "manage_context_window",
    "auto_compact_check", "auto_compact_run", "build_subagent_context",
    "list_context_versions", "recall_context_version",
    # Memory hierarchy + recall
    "unified_recall", "recall_before_act",
    "memory_hot_tier", "memory_warm_tier", "memory_cold_tier",
    # Graph memory — relational lookups complement semantic search
    "memory_graph_query",
    # Proactive recall — resurface old memory headings
    "resurface_old_memory",
    # Autonomous goals
    "goal_create", "goal_list", "goal_decompose", "goal_update_status",
    # Multi-agent
    "list_agent_roles", "register_custom_role",
    "agent_relay_message", "agent_relay_to_role",
    # Emotion + drift
    "capture_emotion_tag", "personality_drift_check", "personality_drift_snapshot",
    # Tool patterns
    "mine_tool_patterns",
    # Heartbeat phases
    "phased_heartbeat_tick", "heartbeat_sense",
    # Provider robustness
    "provider_health_check", "provider_health_status",
    # Self-evaluation
    "tick_quality_summary", "detect_stale_goals", "decision_adherence_summary",
    # Auto-improvement loop
    "generate_improvement_proposals",
    "log_variant_outcome", "variant_performance",
    "start_prompt_experiment", "conclude_prompt_experiment", "list_prompt_experiments",
    # Identity mutation
    "list_identity_mutations", "rollback_identity_mutation", "identity_mutation_status",
    # Scout Memory
    "get_agent_skills", "append_skill_observation",
    "rollback_skill_mutation", "list_skill_mutations", "list_skill_roles",
    "compress_agent_run", "list_agent_observations", "get_agent_observation",
    "cross_agent_recall",
    # Self-wakeup
    "schedule_self_wakeup", "list_self_wakeups", "cancel_self_wakeup", "mark_wakeup_consumed",
})


TIER_2_COMFORT_DEFAULTS: tuple[str, ...] = (
    "discord_status", "send_discord_dm", "send_telegram_message", "send_mail",
    "home_assistant", "list_events", "create_event",
    "spawn_agent_task", "list_agents",
)


TIER_2_CATEGORIES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "discord": (
        ("discord", "dm ", "direct message", "guild", "channel"),
        ("discord_status", "send_discord_dm", "discord_channel"),
    ),
    "telegram": (
        ("telegram",),
        ("send_telegram_message",),
    ),
    "email": (
        ("email", "mail", "inbox", "e-mail", "gmail"),
        ("send_mail", "read_mail"),
    ),
    "browser": (
        ("browser", "webpage", "navigate", "click", "screenshot", "website",
         "chromium", "playwright", "tab "),
        ("browser_navigate", "browser_read", "browser_click", "browser_type",
         "browser_submit", "browser_screenshot", "browser_find_tabs",
         "browser_switch_tab"),
    ),
    "voice": (
        ("voice", "mic", "lyt", "høre", "wake", "whisper", "speech"),
        ("mic_listen", "voice_journal", "wake_word"),
    ),
    "webcam_vision": (
        ("kamera", "webcam", "billede", "image", "foto", "photo", "vision",
         "se rummet", "look around", "analyse af billede", "analyse image"),
        ("look_around", "analyze_image", "hf_vision_analyze"),
    ),
    "tiktok": (
        ("tiktok",),
        ("tiktok_generate_video", "tiktok_upload", "tiktok_login",
         "tiktok_show", "tiktok_analytics"),
    ),
    "comfyui": (
        ("comfyui", "comfy", "workflow", "stable diffusion", "sdxl"),
        ("comfyui_status", "comfyui_workflow", "comfyui_history",
         "comfyui_objects"),
    ),
    "pollinations": (
        ("pollinations", "generate image", "generate video", "generér billede",
         "lav video"),
        ("pollinations_image", "pollinations_video"),
    ),
    "hf": (
        ("hugging", "transcribe", "embed", "classify", "zero-shot"),
        ("hf_text_to_video", "hf_transcribe_audio", "hf_embed",
         "hf_zero_shot_classify"),
    ),
    "home_assistant": (
        ("home assistant", "homeassistant", "lamp", "lys ", "lyset",
         "light", "sensor", "switch", "dimmer", "termostat", "thermostat"),
        ("home_assistant",),
    ),
    "agents": (
        ("agent", "sub-agent", "subagent", "delegate", "spawn", "council"),
        ("spawn_agent_task", "send_message_to_agent", "list_agents",
         "relay_to_agent", "cancel_agent"),
    ),
    "daemon_control": (
        ("daemon", "restart", "disable", "enable", "cadence", "overdue"),
        ("control_daemon", "daemon_health_alert", "daemon_alert_status",
         "restart_overdue_daemons"),
    ),
    "webhooks": (
        ("webhook", "web-hook", "callback url"),
        ("webhook_register", "webhook_send", "webhook_list", "webhook_test",
         "webhook_delete"),
    ),
    "health": (
        ("health check", "uptime", "ping", "endpoint", "service status"),
        ("health_check", "health_register", "health_status", "health_history"),
    ),
    "notify_channels": (
        ("notify", "notification channel", "slack", "push notification"),
        ("notify_out", "notify_channel_add", "notify_channel_list",
         "notify_channel_delete"),
    ),
    "calendar": (
        ("calendar", "event", "møde", "appointment", "meeting", "kalender"),
        ("list_events", "create_event", "delete_event"),
    ),
    "recurring": (
        ("recurring", "gentagende", "hver dag", "hver uge", "every day",
         "every week", "interval"),
        ("schedule_recurring", "list_recurring", "cancel_recurring"),
    ),
}


_RECENT_USAGE: deque[tuple[float, str]] = deque(maxlen=200)
_USAGE_LOCK = threading.Lock()
_USAGE_WINDOW_SECONDS = 600.0


def record_tool_usage(tool_name: str) -> None:
    """Record a tool call timestamp for recent-usage boost. Best-effort."""
    with _USAGE_LOCK:
        _RECENT_USAGE.append((time.time(), tool_name))


def _recent_tool_counts() -> dict[str, int]:
    cutoff = time.time() - _USAGE_WINDOW_SECONDS
    counts: dict[str, int] = {}
    with _USAGE_LOCK:
        for ts, name in _RECENT_USAGE:
            if ts >= cutoff:
                counts[name] = counts.get(name, 0) + 1
    return counts


def _keyword_score_for_categories(user_message: str) -> dict[str, int]:
    """Return {tool_name: keyword_score} based on category keyword hits."""
    if not user_message:
        return {}
    haystack = user_message.lower()
    scores: dict[str, int] = {}
    for _category, (keywords, tool_names) in TIER_2_CATEGORIES.items():
        hits = sum(1 for kw in keywords if kw in haystack)
        if hits <= 0:
            continue
        boost = 10 + 2 * (hits - 1)
        for t in tool_names:
            scores[t] = scores.get(t, 0) + boost
    return scores


def select_tools_for_copilot(
    tools: list[dict],
    *,
    user_message: str = "",
    session_id: str | None = None,
    max_tools: int = MAX_TOOLS,
) -> list[dict]:
    """Return at most ``max_tools`` tool definitions, prioritised for this call.

    - Tier 1 tools are always included.
    - Comfort defaults fill first from Tier 2.
    - Remaining slots go to Tier 2 tools scored by user-message keywords
      and recent usage (last ~10 min).
    - If the full catalog already fits, returns it unchanged (order preserved).
    """
    if len(tools) <= max_tools:
        return list(tools)

    by_name: dict[str, dict] = {}
    for tdef in tools:
        name = tdef.get("function", {}).get("name")
        if isinstance(name, str):
            by_name[name] = tdef

    selected_names: list[str] = []
    seen: set[str] = set()

    # Tier 1
    for name in by_name:
        if name in TIER_1_ALWAYS_ON and name not in seen:
            selected_names.append(name)
            seen.add(name)

    remaining = max_tools - len(selected_names)
    if remaining <= 0:
        return [by_name[n] for n in selected_names[:max_tools]]

    # Tier 2 scoring
    keyword_scores = _keyword_score_for_categories(user_message)
    recent_counts = _recent_tool_counts()

    tier2_candidates: list[tuple[int, int, str]] = []
    for name in by_name:
        if name in seen or name in TIER_1_ALWAYS_ON:
            continue
        score = keyword_scores.get(name, 0)
        if name in TIER_2_COMFORT_DEFAULTS:
            score += 5
        usage_boost = min(recent_counts.get(name, 0), 3) * 4
        score += usage_boost
        # negative score because we sort ascending by (-score, name) via tuple
        tier2_candidates.append((-score, _stable_idx(name), name))

    tier2_candidates.sort()
    for _neg_score, _idx, name in tier2_candidates[:remaining]:
        selected_names.append(name)
        seen.add(name)

    # Preserve original catalog order for consistent caching/debug
    original_order: dict[str, int] = {
        (t.get("function", {}).get("name") or ""): i
        for i, t in enumerate(tools)
    }
    selected_names.sort(key=lambda n: original_order.get(n, 10_000))

    return [by_name[n] for n in selected_names if n in by_name]


def _stable_idx(name: str) -> int:
    """Deterministic tiebreak — lexicographic by name."""
    return sum((ord(c) * (i + 1)) for i, c in enumerate(name[:16]))


def select_tools_for_visible(
    tools: list[dict],
    *,
    user_message: str = "",
    session_id: str | None = None,
    max_tools: int = 200,
) -> list[dict]:
    """Provider-neutral pruning wrapper for the visible lane.

    Same scoring as ``select_tools_for_copilot`` but with a softer cap (200
    instead of 128) since non-Copilot providers don't have a hard 128-tool
    limit. 2026-04-27: bumped from 140 → 200 because Tier 1 alone grew to
    ~183 with today's reasoning/scout-memory/self-wakeup additions, and
    the user explicitly noticed when schedule_self_wakeup got pruned.
    Trade-off: ~3 KT extra per turn vs every important tool available.
    """
    return select_tools_for_copilot(
        tools, user_message=user_message, session_id=session_id, max_tools=max_tools,
    )
