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


# Tier 1 — tools that are always included in the pruned set, regardless of
# user message or recent usage. Goal: cover Jarvis' daily-driver toolkit so
# pruning never hides something he reaches for routinely.
#
# Last regenerated: 2026-04-29 (data-driven from 30-day usage).
# Composition: tools used >= 3 times in the last 30 days, UNIONed with a
# safety floor (notify_user, approve_proposal, etc.) that must always be
# available regardless of past usage.
#
# To regenerate after Jarvis' tool habits drift:
#   conda activate ai
#   python scripts/regenerate_tier1.py [--apply]
#
# Trimmed from 185 -> 103 tools on 2026-04-29 (saved ~7,500 tokens / call).
TIER_1_ALWAYS_ON: frozenset[str] = frozenset({
    "adjust_mood", "analyze_image", "approve_proposal", "bash",
    "bash_session_open", "bash_session_run", "browser_click", "browser_navigate",
    "browser_read", "browser_screenshot", "browser_type", "cancel_agent",
    "cancel_task", "comfyui_history", "comfyui_objects", "comfyui_status",
    "comfyui_workflow", "compact_context", "control_daemon", "convene_council",
    "daemon_status", "db_query", "decision_create", "decision_list",
    "deep_analyze", "discord_channel", "discord_status", "edit_file",
    "edit_task", "eventbus_recent", "find_files", "get_news",
    "get_weather", "git_diff", "git_log", "git_status",
    "goal_create", "goal_list", "heartbeat_status", "hf_vision_analyze",
    "home_assistant", "internal_api", "list_agents", "list_events",
    "list_initiatives", "list_plans", "list_proposals", "list_recurring",
    "list_scheduled_tasks", "list_self_wakeups", "list_signal_surfaces", "look_around",
    "mark_wakeup_consumed", "memory_check_duplicate", "memory_list_headings", "memory_upsert_section",
    "my_project_journal_write", "my_project_status", "notify_user", "propose_git_commit",
    "propose_source_edit", "publish_file", "push_initiative", "quick_council_check",
    "read_chronicles", "read_dreams", "read_file", "read_mail",
    "read_model_config", "read_mood", "read_self_docs", "read_self_state",
    "read_signal_surface", "read_tool_result", "read_visual_memory", "recall_before_act",
    "recall_memories", "recall_sensory_memories", "schedule_self_wakeup", "schedule_task",
    "search", "search_chat_history", "search_memory", "search_sessions",
    "semantic_search_code", "send_discord_dm", "send_ntfy", "send_webchat_message",
    "service_status", "smart_outline", "spawn_agent_task", "tiktok_analytics",
    "tiktok_login", "tiktok_show", "tiktok_upload", "todo_update_status",
    "trigger_heartbeat_tick", "verify_file_contains", "web_fetch", "web_scrape",
    "web_search", "wolfram_query", "write_file",
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
    max_tools: int = 128,
) -> list[dict]:
    """Provider-neutral pruning wrapper for the visible lane.

    Same scoring as ``select_tools_for_copilot``. Cap history:
      - 140 (initial) — fitted Tier 1 + a small Tier 2 cushion
      - 200 (2026-04-27) — bumped because Tier 1 had grown to ~183 and
        the user noticed schedule_self_wakeup getting pruned
      - 128 (2026-04-29) — restored after Tier 1 was data-driven trimmed
        from 185 → 103 tools. The new Tier 1 already covers actually-used
        tools; the remaining 25 slots go to keyword-matched Tier 2 plus
        comfort defaults. Saves ~8K tokens per visible-chat call vs 200
        cap, while still leaving keyword-routed headroom.
    """
    return select_tools_for_copilot(
        tools, user_message=user_message, session_id=session_id, max_tools=max_tools,
    )
