"""Simple, general-purpose tools for Jarvis visible lane.

Eight tools that cover everything Jarvis needs. Permission logic lives
here in the runtime, not in the prompt. Models call tools via native
function calling; the runtime decides what to approve.
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import re
import shlex
import subprocess
import threading
import time
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from core.eventbus.bus import event_bus
from core.services.self_critique_runtime import read_self_docs
from core.services.tool_result_store import get_tool_result
from core.runtime.config import JARVIS_HOME, PROJECT_ROOT
from core.runtime.workspace_paths import shared_dir
from core.tools import geolocation_tools as _geo_tools
from core.tools import team_tools as _team_tools
from core.tools.browser_tools import (
    BROWSER_TOOL_DEFINITIONS,
    _exec_browser_navigate,
    _exec_browser_read,
    _exec_browser_click,
    _exec_browser_type,
    _exec_browser_submit,
    _exec_browser_screenshot,
    _exec_browser_find_tabs,
    _exec_browser_switch_tab,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # DIAGNOSTIC: enable bridge debug logging

from core.tools.comfyui_tools import (
    COMFYUI_TOOL_DEFINITIONS,
    _exec_comfyui_status,
    _exec_comfyui_workflow,
    _exec_comfyui_history,
    _exec_comfyui_objects,
)
from core.tools.pollinations_tools import (
    POLLINATIONS_TOOL_DEFINITIONS,
    _exec_pollinations_image,
    _exec_pollinations_video,
)
from core.tools.hf_inference_tools import (
    HF_INFERENCE_TOOL_DEFINITIONS,
    _exec_hf_text_to_video,
    _exec_hf_transcribe_audio,
    _exec_hf_embed,
    _exec_hf_zero_shot_classify,
    _exec_hf_vision_analyze,
)
from core.tools.tiktok_content_tools import (
    TIKTOK_CONTENT_TOOL_DEFINITIONS,
    _exec_tiktok_generate_video,
)
from core.tools.mic_listen_tool import (
    MIC_LISTEN_TOOL_DEFINITIONS,
    _exec_mic_listen,
)
from core.tools.speak_tool import (
    SPEAK_TOOL_DEFINITIONS,
    _exec_speak,
)
from core.tools.screen_tool import (
    SCREEN_TOOL_DEFINITIONS,
    _exec_screen_control,
)
from core.tools.voice_journal_tool import (
    VOICE_JOURNAL_TOOL_DEFINITIONS,
    _exec_voice_journal,
)
from core.tools.wake_word_tool import (
    WAKE_WORD_TOOL_DEFINITIONS,
    _exec_wake_word,
)
from core.tools.tiktok_tools import (
    TIKTOK_TOOL_DEFINITIONS,
    _exec_tiktok_upload,
    _exec_tiktok_login,
    _exec_tiktok_show,
)
from core.tools.tiktok_analytics_tools import (
    TIKTOK_ANALYTICS_TOOL_DEFINITIONS,
    _exec_tiktok_analytics,
)
from core.tools.restart_self_tools import (
    RESTART_SELF_TOOL_DEFINITIONS,
    _exec_restart_self,
)
from core.tools.mail_tools import (
    MAIL_TOOL_DEFINITIONS,
    _exec_send_mail,
    _exec_read_mail,
)
from core.tools.github_tools import (
    GITHUB_TOOL_DEFINITIONS,
    _exec_git_log,
    _exec_git_diff,
    _exec_git_status,
    _exec_git_branch,
    _exec_git_blame,
)
from core.services.github_connector import GITHUB_CONNECTOR_TOOL_DEFINITIONS
from core.services.gmail_connector import GMAIL_CONNECTOR_TOOL_DEFINITIONS
from core.services.google_connector import GOOGLE_CONNECTOR_TOOL_DEFINITIONS
from core.services.pdf_connector import PDF_CONNECTOR_TOOL_DEFINITIONS
from core.services.notes_connector import NOTES_CONNECTOR_TOOL_DEFINITIONS
from core.services.hf_connector import HF_CONNECTOR_TOOL_DEFINITIONS
from core.tools.reasoning_store_tools import (
    REASONING_STORE_TOOL_DEFINITIONS,
    REASONING_STORE_TOOL_HANDLERS,
    _exec_recall_reasoning,
)
from core.tools.math_tools import (
    MATH_TOOL_DEFINITIONS,
    _exec_calculate,
    _exec_unit_convert,
    _exec_percentage,
)
from core.tools.process_tools import (
    PROCESS_TOOL_DEFINITIONS,
    _exec_service_status,
    _exec_process_list,
    _exec_disk_usage,
    _exec_memory_usage,
    _exec_tail_log,
    _exec_gpu_status,
    _exec_run_pytest,
)
from core.tools.claude_dispatch import (
    CLAUDE_DISPATCH_TOOL_DEFINITIONS,
    _exec_dispatch_to_claude_code,
    _exec_dispatch_status,
    _exec_dispatch_cancel,
)
from core.tools.agent_dispatch_tool import (
    AGENT_DISPATCH_TOOL_DEFINITIONS,
    _exec_dispatch_code_mode_task,
)
from core.tools.bash_session import (
    BASH_SESSION_TOOL_DEFINITIONS,
    _exec_bash_session_open,
    _exec_bash_session_run,
    _exec_bash_session_close,
    _exec_bash_session_list,
)
from core.tools.operator_bash_session import (
    OPERATOR_BASH_SESSION_TOOL_DEFINITIONS,
    _exec_operator_bash_session_open,
    _exec_operator_bash_session_run,
    _exec_operator_bash_session_close,
    _exec_operator_bash_session_list,
)
from core.tools.staged_edits_tools import (
    STAGED_EDITS_TOOL_DEFINITIONS,
    STAGED_EDITS_TOOL_HANDLERS,
)
from core.tools.project_notes_tools import (
    PROJECT_NOTES_TOOL_DEFINITIONS,
    PROJECT_NOTES_TOOL_HANDLERS,
)
from core.tools.process_supervisor_tools import (
    PROCESS_SUPERVISOR_TOOL_DEFINITIONS,
    PROCESS_SUPERVISOR_TOOL_HANDLERS,
)
from core.tools.process_watcher_tools import (
    PROCESS_WATCHER_TOOL_DEFINITIONS,
    PROCESS_WATCHER_TOOL_HANDLERS,
)
from core.tools.pause_and_ask_tools import (
    PAUSE_AND_ASK_TOOL_DEFINITIONS,
    PAUSE_AND_ASK_TOOL_HANDLERS,
)
from core.tools.code_navigation_tools import (
    CODE_NAVIGATION_TOOL_DEFINITIONS,
    CODE_NAVIGATION_TOOL_HANDLERS,
)
from core.tools.worktree_tools import (
    WORKTREE_TOOL_DEFINITIONS,
    WORKTREE_TOOL_HANDLERS,
)
from core.tools.identity_pin_tools import (
    IDENTITY_PIN_TOOL_DEFINITIONS,
    IDENTITY_PIN_TOOL_HANDLERS,
)
from core.tools.ui_panel_tools import (
    UI_PANEL_TOOL_DEFINITIONS,
    UI_PANEL_TOOL_HANDLERS,
)
from core.tools.app_control_tool import (
    APP_CONTROL_TOOL_DEFINITIONS,
    APP_CONTROL_TOOL_HANDLERS,
)
from core.tools.agent_todo_tools import (
    AGENT_TODO_TOOL_DEFINITIONS,
    _exec_todo_list,
    _exec_todo_set,
    _exec_todo_add,
    _exec_todo_update_status,
    _exec_todo_remove,
)
from core.tools.monitor_tools import (
    MONITOR_TOOL_DEFINITIONS,
    _exec_monitor_open,
    _exec_monitor_close,
    _exec_monitor_list,
)
from core.tools.verify_tools import (
    VERIFY_TOOL_DEFINITIONS,
    _exec_verify_file_contains,
    _exec_verify_service_active,
    _exec_verify_endpoint_responds,
)
from core.services.surprise_detector import (
    SURPRISE_TOOL_DEFINITIONS,
    _exec_check_surprises,
)
from core.services.good_enough_gate import (
    GOOD_ENOUGH_TOOL_DEFINITIONS,
    _exec_check_good_enough,
)
from core.services.delegation_advisor import (
    DELEGATION_ADVISOR_TOOL_DEFINITIONS,
    _exec_delegation_advisor,
)
from core.services.plan_proposals import (
    PLAN_PROPOSALS_TOOL_DEFINITIONS,
    _exec_propose_plan,
    _exec_approve_plan,
    _exec_dismiss_plan,
    _exec_list_plans,
)
from core.services.clarification_classifier import (
    CLARIFICATION_TOOL_DEFINITIONS,
    _exec_classify_clarification,
)
from core.services.reasoning_classifier import (
    REASONING_CLASSIFIER_TOOL_DEFINITIONS,
    _exec_reasoning_classify,
)
from core.services.verification_gate import (
    VERIFICATION_GATE_TOOL_DEFINITIONS,
    _exec_verification_status,
)
from core.services.reasoning_escalation import (
    REASONING_ESCALATION_TOOL_DEFINITIONS,
    _exec_recommend_escalation,
)
from core.services.side_tasks import (
    SIDE_TASK_TOOL_DEFINITIONS,
    _exec_flag_side_task,
    _exec_list_side_tasks,
    _exec_dismiss_side_task,
    _exec_activate_side_task,
)
from core.tools.smart_outline import (
    SMART_OUTLINE_TOOL_DEFINITIONS,
    _exec_smart_outline,
)
from core.tools.calendar_tools import (
    CALENDAR_TOOL_DEFINITIONS,
    _exec_list_events,
    _exec_create_event,
    _exec_delete_event,
)
from core.tools.memory_tools import (
    MEMORY_TOOL_DEFINITIONS,
    _exec_memory_check_duplicate,
    _exec_memory_upsert_section,
    _exec_memory_list_headings,
    _exec_memory_consolidate,
)
from core.tools.semantic_search_tools import (
    SEMANTIC_SEARCH_TOOL_DEFINITIONS,
    _exec_semantic_search_code,
)
from core.tools.notify_out_tools import (
    NOTIFY_OUT_TOOL_DEFINITIONS,
    _exec_notify_out,
    _exec_notify_channel_add,
    _exec_notify_channel_list,
    _exec_notify_channel_delete,
)
from core.tools.companion_push_tools import (
    COMPANION_PUSH_TOOL_DEFINITIONS,
    _exec_send_push_notification,
)
from core.tools.daemon_alert_tools import (
    DAEMON_ALERT_TOOL_DEFINITIONS,
    _exec_daemon_health_alert,
    _exec_daemon_alert_status,
    _exec_restart_overdue_daemons,
)
from core.tools.smart_compact_tools import (
    SMART_COMPACT_TOOL_DEFINITIONS,
    _exec_smart_compact,
    _exec_context_size_check,
)
from core.services.context_window_manager import (
    CONTEXT_WINDOW_TOOL_DEFINITIONS,
    _exec_context_pressure,
    _exec_manage_context_window,
)
from core.services.autonomous_goals import (
    AUTONOMOUS_GOALS_TOOL_DEFINITIONS,
    _exec_goal_create,
    _exec_goal_list,
    _exec_goal_decompose,
    _exec_goal_update_status,
)
from core.services.memory_recall_engine import (
    UNIFIED_RECALL_TOOL_DEFINITIONS,
    _exec_unified_recall,
)
from core.services.role_registry import (
    ROLE_REGISTRY_TOOL_DEFINITIONS,
    _exec_list_roles,
    _exec_register_custom_role,
)
from core.services.agent_relay import (
    AGENT_RELAY_TOOL_DEFINITIONS,
    _exec_relay_message,
    _exec_relay_to_role,
)
from core.services.emotion_tagging import (
    EMOTION_TAGGING_TOOL_DEFINITIONS,
    _exec_capture_emotion_tag,
)
from core.services.personality_drift import (
    PERSONALITY_DRIFT_TOOL_DEFINITIONS,
    _exec_personality_drift_check,
    _exec_personality_drift_snapshot,
)
from core.services.tool_pattern_miner import (
    TOOL_PATTERN_MINER_TOOL_DEFINITIONS,
    _exec_mine_tool_patterns,
)
from core.services.heartbeat_phases import (
    HEARTBEAT_PHASES_TOOL_DEFINITIONS,
    _exec_phased_tick,
    _exec_sense_only,
)
from core.services.proactive_context_governor import (
    PROACTIVE_CONTEXT_TOOL_DEFINITIONS,
    _exec_should_auto_compact,
    _exec_auto_compact_if_needed,
    _exec_build_subagent_context,
    _exec_list_context_versions,
    _exec_recall_context_version,
)
from core.services.memory_hierarchy import (
    MEMORY_HIERARCHY_TOOL_DEFINITIONS,
    _exec_recall_before_act,
    _exec_hot_tier,
    _exec_warm_tier,
    _exec_cold_tier,
)
from core.services.provider_retry_policy import (
    PROVIDER_RETRY_TOOL_DEFINITIONS,
    _exec_test_retry,
)
from core.services.provider_health_check import (
    PROVIDER_HEALTH_TOOL_DEFINITIONS,
    _exec_run_health_check,
    _exec_get_health_snapshot,
)
from core.services.agent_self_evaluation import (
    SELF_EVALUATION_TOOL_DEFINITIONS,
    _exec_tick_quality_summary,
    _exec_detect_stale_goals,
    _exec_decision_adherence,
)
from core.services.auto_improvement_proposer import (
    AUTO_IMPROVEMENT_TOOL_DEFINITIONS,
    _exec_generate_improvement_proposals,
)
from core.services.prompt_variant_tracker import (
    PROMPT_VARIANT_TOOL_DEFINITIONS,
    _exec_log_variant_outcome,
    _exec_variant_performance,
)
from core.services.experiment_runner import (
    EXPERIMENT_RUNNER_TOOL_DEFINITIONS,
    _exec_start_experiment,
    _exec_conclude_experiment,
    _exec_list_experiments,
)
from core.services.identity_mutation_log import (
    IDENTITY_MUTATION_TOOL_DEFINITIONS,
    _exec_list_identity_mutations,
    _exec_rollback_identity_mutation,
    _exec_identity_mutation_status,
)
from core.services.agent_skill_library import (
    AGENT_SKILL_TOOL_DEFINITIONS,
    _exec_get_agent_skills,
    _exec_append_skill,
    _exec_rollback_skill_mutation,
    _exec_list_skill_mutations,
    _exec_list_known_roles,
)
from core.services.agent_observation_compressor import (
    AGENT_OBSERVATION_TOOL_DEFINITIONS,
    _exec_compress_agent_run,
    _exec_list_agent_observations,
    _exec_get_agent_observation,
)
from core.services.cross_agent_memory import (
    CROSS_AGENT_TOOL_DEFINITIONS,
    _exec_cross_agent_recall,
)
from core.services.self_wakeup import (
    SELF_WAKEUP_TOOL_DEFINITIONS,
    _exec_schedule_self_wakeup,
    _exec_list_self_wakeups,
    _exec_cancel_self_wakeup,
    _exec_mark_wakeup_consumed,
)
from core.services.wakeup_dispatcher import (
    WAKEUP_DISPATCHER_TOOL_DEFINITIONS,
    _exec_dispatch_due_wakeups,
)
from core.services.crisis_marker_detector import (
    CRISIS_MARKER_TOOL_DEFINITIONS,
    _exec_scan_crisis_markers,
    _exec_list_crisis_markers,
)
from core.services.identity_drift_proposer import (
    IDENTITY_DRIFT_TOOL_DEFINITIONS,
    _exec_propose_identity_drift,
)
from core.services.long_arc_synthesizer import (
    LONG_ARC_TOOL_DEFINITIONS,
    _exec_synthesize_arc,
    _exec_list_arcs,
)
from core.tools.recurring_scheduler_tools import (
    RECURRING_TOOL_DEFINITIONS,
    _exec_schedule_recurring,
    _exec_list_recurring,
    _exec_cancel_recurring,
    _exec_set_recurring_channel,
)
from core.tools.notification_tools import (
    NOTIFICATION_TOOL_DEFINITIONS,
    exec_get_notification_preferences,
    exec_set_notification_preferences,
)
from core.tools.memory_topic_tools import (
    _exec_read_memory_topic,
    _exec_write_memory_topic,
)
from core.tools.webhook_tools import (
    WEBHOOK_TOOL_DEFINITIONS,
    _exec_webhook_register,
    _exec_webhook_send,
    _exec_webhook_list,
    _exec_webhook_test,
    _exec_webhook_delete,
)
from core.tools.health_monitor_tools import (
    HEALTH_MONITOR_TOOL_DEFINITIONS,
    _exec_health_check,
    _exec_health_register,
    _exec_health_status,
    _exec_health_history,
)
from core.tools.sensory_tools import (
    SENSORY_TOOL_DEFINITIONS,
    _exec_record_sensory_memory,
    _exec_recall_sensory_memories,
)
from core.tools.recall_memory_tools import (
    RECALL_MEMORY_TOOL_DEFINITIONS,
    _exec_recall_memories,
)
from core.tools.goals_tools import (
    GOAL_TOOL_DEFINITIONS,
    GOAL_TOOL_HANDLERS,
)
from core.tools.decisions_tools import (
    DECISION_TOOL_DEFINITIONS,
    DECISION_TOOL_HANDLERS,
)
from core.tools.composites_tools import (
    COMPOSITE_TOOL_DEFINITIONS,
    COMPOSITE_TOOL_HANDLERS,
)
from core.tools.visual_memory_tool import (
    VISUAL_MEMORY_TOOL_DEFINITIONS,
    _exec_read_visual_memory,
)
from core.tools.jarvis_brain_tools import (
    JARVIS_BRAIN_TOOL_DEFINITIONS,
    _exec_remember_this,
    _exec_search_jarvis_brain,
    _exec_read_brain_entry,
    _exec_archive_brain_entry,
    _exec_adopt_brain_proposal,
    _exec_discard_brain_proposal,
)
from core.tools.session_search import (
    TOOL_DEFINITION as _SESSION_SEARCH_TOOL_DEF,
    exec_search_sessions as _exec_search_sessions,
)
from core.tools.stripe_tools import (
    STRIPE_TOOL_DEFINITIONS,
    STRIPE_TOOL_HANDLERS,
)
from core.tools.skill_engine_tools import (
    SKILL_ENGINE_TOOL_DEFINITIONS,
    SKILL_ENGINE_TOOL_HANDLERS,
)
from core.tools.skill_gate_tool import (
    SKILL_GATE_TOOL_DEFINITIONS,
    SKILL_GATE_TOOL_HANDLERS,
)
from core.tools.world_model_tools import (
    WORLD_MODEL_TOOL_DEFINITIONS,
    WORLD_MODEL_TOOL_HANDLERS,
)
from core.tools.counterfactual_tools import (
    COUNTERFACTUAL_TOOL_DEFINITIONS,
    COUNTERFACTUAL_TOOL_HANDLERS,
)
from core.tools.plan_revise_tool import (
    PLAN_REVISE_TOOL_DEFINITIONS,
    PLAN_REVISE_TOOL_HANDLERS,
)
from core.tools.curiosity_tools import (
    CURIOSITY_TOOL_DEFINITIONS,
    CURIOSITY_TOOL_HANDLERS,
)
from core.tools.skill_chain_propose_tool import (
    PROPOSE_SKILL_CHAIN_TOOL_DEFINITIONS,
    PROPOSE_SKILL_CHAIN_TOOL_HANDLERS,
)
from core.tools.skill_chain_revise_tool import (
    REVISE_SKILL_CHAIN_TOOL_DEFINITIONS,
    REVISE_SKILL_CHAIN_TOOL_HANDLERS,
)
from core.tools.meta_learning_tools import (
    META_LEARNING_TOOL_DEFINITIONS,
    META_LEARNING_TOOL_HANDLERS,
)
from core.tools.nudge_tools import (
    NUDGE_TOOL_DEFINITIONS,
    NUDGE_TOOL_HANDLERS,
)
from core.tools.skill_chain_tool import (
    SKILL_CHAIN_TOOL_DEFINITIONS,
    SKILL_CHAIN_TOOL_HANDLERS,
)
from core.tools.forgetting_tools import (
    FORGETTING_TOOL_DEFINITIONS,
    FORGETTING_TOOL_HANDLERS,
)
from core.tools.nudge_broend_tools import (
    NUDGE_BROEND_TOOL_DEFINITIONS,
    NUDGE_BROEND_TOOL_HANDLERS,
)
from core.tools.coding_lane_tools import (
    CODING_LANE_TOOL_DEFINITIONS,
    CODING_LANE_TOOL_HANDLERS,
)
from core.tools.identity_sketch_tools import (
    IDENTITY_SKETCH_TOOL_DEFINITIONS,
    _exec_read_identity_sketch,
    _exec_update_identity_sketch,
)

MAX_READ_CHARS = 32000
MAX_SEARCH_RESULTS = 60
MAX_SEARCH_LINE_CHARS = 200
MAX_FIND_RESULTS = 100
MAX_BASH_OUTPUT_CHARS = 16000
MAX_BASH_SECONDS = 15
MAX_WEB_FETCH_CHARS = 24000
# Ord/linje-sikker klipning (mod voldsom tool-trunkering): bevar HOVED+HALE så resultat/fejl/exit
# i slutningen af output ikke smides væk. Se core/services/text_clip.py.
from core.services.text_clip import clip_head_tail as _clip_head_tail, clip_text as _clip_text  # noqa: E402
WORKSPACE_DIR = shared_dir()

# Paths that can be written without user approval.
_AUTO_APPROVE_WRITE_PATHS = {
    str(WORKSPACE_DIR / "MEMORY.md"),
    str(WORKSPACE_DIR / "USER.md"),
}
_AUTO_APPROVE_WRITE_PREFIXES = [
    str(WORKSPACE_DIR) + "/",                          # all runtime workspace files
    str(Path(PROJECT_ROOT) / "workspace" / "default") + "/",  # repo workspace template
    "/tmp/",                                            # safe temp directory
    str(Path(JARVIS_HOME)) + "/",                       # all of ~/.jarvis-v2/ (state, logs, cache)
    "/media/projects/",                                 # Bjørn's project root — mini-jarvis,
                                                        # jarvis-v2, custom-model training,
                                                        # everything he iterates on. The
                                                        # blocked-patterns list still protects
                                                        # /.git/ /.env /credentials /.ssh.
    str(Path(JARVIS_HOME) / "workspaces" / "michelle") + "/",
    # Michelle's workspace — separate persona space, owned by her.
    # Inconsistency this fixes: ``bash`` can already do ``echo foo > /any/path``
    # because ``echo`` is in _READ_ONLY_COMMAND_PREFIXES (no redirect awareness).
    # ``write_file`` was much stricter, silently turning into approval_needed
    # cards that didn't always reach the user. Net effect: Jarvis would say
    # "I wrote the file" while it was actually pending an approval that never
    # surfaced. Auto-approving the same paths bash effectively can write to
    # closes the gap; the structural blocks (.git, .env, credentials, .ssh,
    # node_modules, __pycache__) still protect the dangerous spots.
]
_BLOCKED_WRITE_PATTERNS = [
    "/.git/",
    "/.env",
    "/credentials",
    "/.ssh/",
    "/node_modules/",
    "/__pycache__/",
]

# Files that must always resolve to the runtime workspace, no matter what path
# the LLM provides. Prevents memory drifting into repo root, repo workspace
# template, or any other incorrect location.
_CANONICAL_WORKSPACE_FILES = {"MEMORY.md", "USER.md"}


def _canonicalize_workspace_target(target: Path) -> tuple[Path, str | None]:
    """If target's basename is a canonical workspace file, force it to the
    runtime workspace path. Returns (resolved_target, redirected_from_or_None).
    """
    if target.name in _CANONICAL_WORKSPACE_FILES:
        canonical = (WORKSPACE_DIR / target.name).resolve()
        if target != canonical:
            return canonical, str(target)
    return target, None

# ── Tool definitions (Ollama-compatible JSON schemas) ──────────────────

# ── Tool-katalog udskilt til simple_tools_definitions.py (Boy Scout, 2026-07) ──
# Den store TOOL_DEFINITIONS-liste (~3150 linjer data) bor nu i sit eget modul.
# Re-importeret her, så `from core.tools.simple_tools import TOOL_DEFINITIONS`
# (og get_tool_definitions nedenfor) er uændret. Ingen dobbelt-sandhed:
# de enkelte *_TOOL_DEFINITIONS-fragmenter samles ét sted.
from core.tools.simple_tools_definitions import TOOL_DEFINITIONS  # noqa: E402,F401


# ── Permission classification ──────────────────────────────────────────

_READ_ONLY_COMMAND_PREFIXES = [
    "cat ", "head ", "tail ", "less ", "more ",
    "ls", "ll ", "la ", "dir ",
    "find ", "locate ",
    "grep ", "rg ", "ag ", "ack ",
    "wc ", "sort ", "uniq ", "diff ", "comm ",
    "file ", "stat ", "du ", "df ",
    "git status", "git log", "git diff", "git show", "git branch",
    "git remote", "git tag", "git stash list", "git rev-parse",
    "git blame", "git shortlog", "git describe",
    "pwd", "whoami", "hostname", "uname", "id ",
    "lscpu", "lshw", "lsblk", "lspci", "lsusb", "lsmod",
    "free ", "uptime", "nproc", "hostnamectl",
    "nvidia-smi", "sensors",
    "ps ", "top -bn1", "pgrep ", "ss ", "netstat ",
    "ip addr", "ip route", "ifconfig",
    "systemctl status", "journalctl",
    "which ", "whereis ", "type ",
    "python -c ", "python3 -c ",
    "echo ", "date", "cal ",
    "env", "printenv",
    "tree ",
    # 2026-05-22 (Claude): network diagnostic read-only tools. Without
    # these, every factual question that triggers Jarvis's hallucination-
    # guard tool-call ("let me verify with dig") hit the approval-card
    # flow and hung for up to 240s waiting for confirmation. The hang
    # was the dominant component of the "Jarvis is slow" complaint.
    # All listed tools are query-only: dig/host/nslookup look up DNS,
    # traceroute prints route info, getent reads name databases, arp -a
    # reads ARP table. They modify nothing.
    "dig ", "dig\n", "host ", "nslookup ",
    "traceroute ", "tracepath ", "mtr -r ", "mtr --report",
    "getent ",
    "arp -a", "arp -n",
    # ping bounded by -c flag is also read-only. Bare "ping <host>"
    # would run forever, so we only whitelist when count is explicit.
    # (Pattern handling for this lives in classify_command below.)
]

# Bounded network commands: prefix + required-flag check.
# 2026-05-22 (Claude): allow `ping -c <N>` and `ping6 -c <N>` as auto-
# approved since the -c flag bounds the run. Bare `ping host` would
# loop forever and stays at "approval". The regex requires the literal
# token `-c <digits>` to appear somewhere in a ping/ping6 invocation;
# additional flags (-W timeout, -i interval, -s size, etc.) are fine.
_BOUNDED_READ_ONLY_REGEX: list[re.Pattern[str]] = [
    re.compile(r"^ping6?\b(?=.*\s-c\s+\d+)", re.IGNORECASE),
]

_DESTRUCTIVE_PATTERNS = [
    r"\brm\b", r"\brm\s+-rf\b",
    r"git\s+reset\s+--hard", r"git\s+clean",
    r"git\s+push\s+--force", r"git\s+push\s+-f\b",
    r"\bdrop\s+table\b", r"\bdrop\s+database\b",
    r"\btruncate\b",
    r"mkfs\b", r"dd\s+if=",
    r":(){ :\|:& };:",
    r"\bshutdown\b", r"\breboot\b", r"\bpoweroff\b",
]

_BLOCKED_COMMANDS = [
    r"\bcurl\b.*\|\s*bash",
    r"\bwget\b.*\|\s*bash",
    r"\bsudo\s+rm\b",
]


_READ_ONLY_GIT_SUBCOMMANDS = {
    "status", "log", "diff", "show", "branch", "remote", "tag",
    "stash list", "rev-parse", "blame", "shortlog", "describe",
    "ls-files", "ls-tree", "cat-file", "reflog",
}


def classify_command(command: str) -> str:
    """Classify a shell command: 'auto', 'approval', 'destructive', or 'blocked'."""
    normalized = command.strip().lower()

    for pattern in _BLOCKED_COMMANDS:
        if re.search(pattern, normalized):
            return "blocked"

    for pattern in _DESTRUCTIVE_PATTERNS:
        if re.search(pattern, normalized):
            return "destructive"

    for prefix in _READ_ONLY_COMMAND_PREFIXES:
        if normalized.startswith(prefix) or normalized == prefix.strip():
            return "auto"

    # Bounded network commands (e.g. ping -c N)
    for pattern in _BOUNDED_READ_ONLY_REGEX:
        if pattern.match(normalized):
            return "auto"

    # Git with flags before subcommand (e.g. git -C /path log)
    git_match = re.match(r"git\s+(?:-\S+\s+\S+\s+)*(\S+(?:\s+\S+)?)", normalized)
    if git_match:
        subcmd = git_match.group(1)
        if any(subcmd.startswith(s) for s in _READ_ONLY_GIT_SUBCOMMANDS):
            return "auto"

    # Piped commands (|): check if all segments are read-only
    if "|" in normalized and "&&" not in normalized and ";" not in normalized:
        segments = [s.strip() for s in normalized.split("|")]
        if all(
            any(seg.startswith(p) or seg == p.strip() for p in _READ_ONLY_COMMAND_PREFIXES)
            for seg in segments
            if seg
        ):
            return "auto"

    # &&-chained commands: classify each segment independently
    # If ALL segments are auto or read-only, the chain is auto
    if "&&" in normalized:
        def _segment_is_safe(seg: str) -> bool:
            seg = seg.strip()
            if not seg:
                return True
            # Allow cd by itself (just changes dir, no side effects)
            if re.match(r"^cd(\s+\S+)?$", seg):
                return True
            for pattern in _BLOCKED_COMMANDS:
                if re.search(pattern, seg):
                    return False
            for pattern in _DESTRUCTIVE_PATTERNS:
                if re.search(pattern, seg):
                    return False
            for prefix in _READ_ONLY_COMMAND_PREFIXES:
                if seg.startswith(prefix) or seg == prefix.strip():
                    return True
            git_m = re.match(r"git\s+(?:-\S+\s+\S+\s+)*(\S+(?:\s+\S+)?)", seg)
            if git_m and any(git_m.group(1).startswith(s) for s in _READ_ONLY_GIT_SUBCOMMANDS):
                return True
            return False

        segments = [s.strip() for s in normalized.split("&&")]
        if all(_segment_is_safe(s) for s in segments if s):
            return "auto"

    # Sudo commands with allowlisted subcommands are auto-approved.
    # This mirrors APPROVED_SUDO_EXEC_ALLOWLIST from workspace_capabilities.py.
    _SUDO_AUTO_APPROVE_SUBCOMMANDS = {
        "chmod", "chown", "systemctl", "journalctl", "docker",
        "apt", "apt-get", "dpkg", "pip", "pip3", "npm", "nvm",
        "snap", "flatpak", "dnf", "yum", "brew", "make", "cargo", "go",
        "kubectl", "tee", "cp", "mv", "mkdir", "rmdir", "ln", "tar",
        "curl", "wget", "mount", "umount", "fdisk", "parted", "lsblk",
        "blkid", "cryptsetup", "ufw", "iptables", "ip", "ip6tables",
        "ss", "netstat", "nginx", "apache2", "supervisorctl", "crontab",
        "useradd", "usermod", "userdel", "groupadd", "groupdel", "passwd",
        "visudo", "sed", "awk", "cat", "find", "install", "rsync", "dd",
    }
    sudo_match = re.match(r"sudo\s+(\S+)", normalized)
    if sudo_match:
        subcmd = sudo_match.group(1).lower()
        if subcmd in _SUDO_AUTO_APPROVE_SUBCOMMANDS:
            return "auto"

    return "approval"


def classify_file_write(path: str) -> str:
    """Classify a file write: 'auto', 'approval', or 'blocked'."""
    resolved = str(Path(path).resolve())

    for blocked in _BLOCKED_WRITE_PATTERNS:
        if blocked in resolved:
            return "blocked"

    if resolved in _AUTO_APPROVE_WRITE_PATHS:
        return "auto"

    for prefix in _AUTO_APPROVE_WRITE_PREFIXES:
        if resolved.startswith(prefix):
            return "auto"

    return "approval"


# ── Tool execution handlers ────────────────────────────────────────────

def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool call — Tools-cluster (Den Intelligente Central, Phase 1).

    Tynd wrapper: kører den uændrede tool-dispatch (_impl) og observerer ALT-udfaldet ved
    chokepunktet — OGSÅ de tidlige returns (ukendt tool / auth-nægtet / untrusted workspace),
    som er de vigtigste fejl-cases. Tagger native vs operator + chat/code-scope + rolle +
    session + status/error → debugging af "fejl ude af huset": når en bruger melder en fejl
    ser vi PRÆCIST hvilket operator-/chat-tool i hvilken session der fejlede. Self-safe.
    Konsolidering 20→1 = Phase 2 (på forbrugs/overlap-trace-dataen)."""
    result = _execute_tool_impl(name, arguments)
    try:
        from core.services.central_core import central as _central_tools
        try:
            from core.identity.workspace_context import effective_role as _er
            from core.tools.tool_scoping import current_tool_scope as _cs
            _role_obs = _er() or ""
            _scope_obs = _cs() or ""
        except Exception:
            _role_obs, _scope_obs = "", ""
        _status = str(result.get("status") or "ok") if isinstance(result, dict) else "ok"
        _central_tools().observe({
            "cluster": "tools", "nerve": "tool_call", "tool": name,
            "kind": "operator" if str(name).startswith("operator_") else "native",
            "role": _role_obs, "scope": _scope_obs,
            "session_id": str(arguments.get("_runtime_session_id")
                              or arguments.get("_session_id") or ""),
            "status": _status,
            "error": (str(result.get("error") or "")[:160]
                      if isinstance(result, dict) and _status != "ok" else ""),
        })
    except Exception:
        pass
    # Tools-cluster Phase 2: persistent forbrugs-tæller (DB, cross-proces api↔runtime) →
    # Centralen kan ordne kataloget (mest-brugt først, døde sidst) + flagge døde tools.
    try:
        from core.services.tool_usage_store import record_use
        _ok = isinstance(result, dict) and str(result.get("status") or "ok") == "ok"
        record_use(name, kind="operator" if str(name).startswith("operator_") else "native",
                   ok=_ok)
    except Exception:
        pass
    # ── Permission-classifier shadow observe (harness Part E) ──────────────
    # Non-blocking: predict owner-approval for mutating tools + record the outcome
    # (bootstrap: ok→approve, blocked→deny; approval_needed→stash for gold at resolve).
    # Fail-open, never changes the returned status. Default mode shadow.
    try:
        from core.services import permission_classifier as _pc
        if (isinstance(result, dict) and _pc.permission_classifier_mode() != "off"
                and _pc.is_mutating(name)):
            _pc_status = str(result.get("status") or "")
            _pc_approval_id = str(result.get("approval_id") or "")
            _pc_args = dict(arguments)

            def _pc_shadow() -> None:
                try:
                    pred = _pc.classify_action(name, _pc_args, {"status": _pc_status})
                    if _pc_status == "approval_needed" and _pc_approval_id:
                        _pc.stash_prediction(_pc_approval_id, name, pred.verdict)
                    else:
                        _actual = ("approve" if _pc_status == "ok"
                                   else ("deny" if _pc_status in ("blocked", "gate_blocked") else ""))
                        if _actual:
                            _pc.record_prediction_outcome(name, predicted=pred.verdict,
                                                          actual=_actual, is_owner_gold=False)
                except Exception:
                    pass
            import threading as _pc_th
            _pc_th.Thread(target=_pc_shadow, daemon=True).start()
    except Exception:
        pass
    return result


def _execute_tool_impl(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool call and return the result."""
    handler = _TOOL_HANDLERS.get(name)
    if not handler:
        result = {"error": f"Unknown tool: {name}", "status": "error"}
        _record_tool_outcome_memory(name, arguments, result, mode="tool")
        return result

    # Serverside rolle-håndhævelse (Spor A, defense-in-depth): selv hvis model-
    # filteret omgås (prompt-injection, intern bypass, bug), nægter vi her. Owner
    # og unbound ("" = betroede interne/daemon-kald) slipper igennem. Fail-OPEN
    # KUN hvis selve tjekken kaster — aldrig låse owner/daemoner ude; model-
    # filteret er stadig primær gate.
    # ── Auth-cluster 🔒 GENNEM Den Intelligente Central (SECURITY, fail-CLOSED) ──
    # Rolle bestemmes OWNER-SIKKERT (fejl → unbound "" → ingen deny). Kun ægte member/
    # guest-roller går gennem den fail-closed Auth-gate; owner/unbound låses ALDRIG ude.
    try:
        from core.identity.workspace_context import effective_role as _eff_role
        from core.tools.tool_scoping import current_tool_scope as _cur_scope
        _role = _eff_role()
        _scope = _cur_scope() or ""
    except Exception:
        _role, _scope = "", ""
    if _role not in ("", "owner"):
        _auth_denied = False
        try:
            from core.services.central_core import central as _central_auth
            from core.services.gate_auth import auth_gate as _auth_gate
            from core.services.gate_kernel import Decision as _ADec, GateClass as _AGK
            _av = _central_auth().decide(
                "tool_access", {"role": _role, "scope": _scope, "name": name},
                _auth_gate, cluster="auth", klass=_AGK.SECURITY)
            # RED = deny — INKL. fail-closed når is_tool_allowed kaster (modsat det gamle
            # except:pass der tillod stille). Sikkerheds-nerve kan ikke slås fra.
            _auth_denied = _av.decision is _ADec.RED
        except Exception as _auth_exc:
            _auth_denied = False  # central-sti-katastrofe → model-tool-filteret er primær gate
            # Audit-remediation 2026-06-23: fail-open er availability-valg, men det MÅ
            # ikke være TAVST — en kollapset auth-sti er en sikkerheds-hændelse. Gør den LYD.
            try:
                from core.runtime.db_central_incidents import record_central_incident
                record_central_incident(
                    cluster="auth", nerve="tool_access", kind="fail_open",
                    severity="severe",
                    message=f"auth-backstop central-sti kastede → fail-OPEN for rolle={_role} tool={name}: "
                            f"{type(_auth_exc).__name__}: {_auth_exc}"[:300],
                )
            except Exception:
                pass
        if _auth_denied:
            result = {
                "status": "error", "error": "tool_not_permitted",
                "detail": f"Værktøjet '{name}' er ikke tilladt for rollen '{_role}'.",
                "role": _role, "tool": name,
            }
            try:
                event_bus.publish("incident.tool_denied", {"tool": name, "role": _role})
            except Exception:
                pass
            # Connections-cluster: uautoriseret tool-adgang → fang+flag (severe incident) +
            # bind til session, så vi ser hvem/hvad forsøgte uautoriseret hvor.
            try:
                from core.services.connections import note_unauthorized
                _ua_sid = str(arguments.get("_runtime_session_id")
                              or arguments.get("_session_id") or "")
                _ua_rid = str(arguments.get("_runtime_run_id")
                              or arguments.get("_run_id") or "")
                # Fang den ÆGTE bruger (ikke bare rollen "member") så signalet er handlingsbart.
                try:
                    from core.identity.workspace_context import current_user_id as _cuid
                    _ua_uid = _cuid() or ""
                except Exception:
                    _ua_uid = ""
                note_unauthorized(_ua_uid, _ua_sid, f"tool:{name}", "tool_not_permitted",
                                  role=_role, run_id=_ua_rid)
            except Exception:
                pass
            _record_tool_outcome_memory(name, arguments, result, mode="tool")
            return result

    # Trusted-folder gate: skrive/exec i ikke-betroet code-workspace → Execution-cluster 🔒
    # GENNEM Centralen (SECURITY, traced). Owner-sikkert (fail-open ved central-katastrofe).
    try:
        from core.services.gate_execution import check_workspace_trust
        _wt = check_workspace_trust(name)
        _trust_block = _wt.reason if _wt.classification == "untrusted" else None
    except Exception:
        _trust_block = None
    if _trust_block:
        result = {"error": _trust_block, "status": "error", "blocked": "untrusted_workspace"}
        _record_tool_outcome_memory(name, arguments, result, mode="tool")
        return result

    event_bus.publish("tool.invoked", {
        "tool": name,
        "arguments": {k: str(v)[:100] for k, v in arguments.items()},
    })

    try:
        result = handler(arguments)
    except Exception as exc:
        result = {"error": str(exc), "status": "error"}

    # Defensive: tools may return None for pure side-effects; normalize
    # so .get() won't crash the visible-run pipeline.
    if not isinstance(result, dict):
        result = {"status": "ok", "result": result}

    status = str(result.get("status", "ok"))
    _completed_payload = {"tool": name, "status": status}
    # R2 noise-reduktion: marker om et shell-kald reelt ændrer state, så
    # verification_gate kun tæller ægte mutationer (ikke grep/cat/git status).
    if name in ("bash", "bash_session_run"):
        try:
            from core.services.verification_gate import shell_command_is_mutating
            _completed_payload["mutating"] = shell_command_is_mutating(
                str(arguments.get("command", ""))
            )
        except Exception:
            pass
    event_bus.publish("tool.completed", _completed_payload)

    # Outcome learning: each tool execution is a datapoint. Context = tool name,
    # outcome = success/error. Fire-and-forget — must never break tool flow.
    try:
        from core.services.outcome_learning import record_outcome
        outcome_label = "error" if status == "error" else "success"
        record_outcome(
            context=f"tool:{name}",
            outcome=outcome_label,
            weight=1.0,
        )
    except Exception:
        pass

    _record_tool_outcome_memory(name, arguments, result, mode="tool")

    return result


def execute_tool_force(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute tool bypassing approval checks. Only call for user-approved requests."""
    handler = _FORCE_HANDLERS.get(name) or _TOOL_HANDLERS.get(name)
    if not handler:
        result = {"error": f"Unknown tool: {name}", "status": "error"}
        _record_tool_outcome_memory(name, arguments, result, mode="tool_force")
        return result

    # Emotional gate — can transform "execute" to escalate/verify/simplify
    # based on mood state. Fire-and-forget safe.
    try:
        from core.services.emotional_controls import (
            apply_emotional_controls, format_gate_message,
        )
        gate_action, gate_reason = apply_emotional_controls(kernel_action="execute")
        if gate_action != "execute" and gate_reason:
            msg = format_gate_message(gate_action, gate_reason, tool_name=name)
            event_bus.publish("emotional.gate_triggered", {
                "tool": name,
                "gate_action": gate_action,
                "reason": gate_reason,
            })
            result = {
                "status": "gated",
                "gate_action": gate_action,
                "gate_reason": gate_reason,
                "message": msg,
                "tool": name,
            }
            _record_tool_outcome_memory(name, arguments, result, mode="tool_force")
            return result
    except Exception:
        pass  # never block tool execution on emotional_controls errors

    event_bus.publish("tool.force_invoked", {
        "tool": name,
        "arguments": {k: str(v)[:100] for k, v in arguments.items()},
    })

    try:
        result = handler(arguments)
    except Exception as exc:
        result = {"error": str(exc), "status": "error"}

    # Tools occasionally return None (e.g. from a pure side-effect handler);
    # normalize so .get() doesn't crash the visible-run pipeline. Treat
    # None as "ok with no payload" — the tool ran without raising.
    if not isinstance(result, dict):
        result = {"status": "ok", "result": result}

    status = str(result.get("status", "ok"))
    _completed_payload = {"tool": name, "status": status}
    # R2 noise-reduktion: marker om et shell-kald reelt ændrer state, så
    # verification_gate kun tæller ægte mutationer (ikke grep/cat/git status).
    if name in ("bash", "bash_session_run"):
        try:
            from core.services.verification_gate import shell_command_is_mutating
            _completed_payload["mutating"] = shell_command_is_mutating(
                str(arguments.get("command", ""))
            )
        except Exception:
            pass
    event_bus.publish("tool.completed", _completed_payload)

    # Outcome learning — same hook as execute_tool so force-path is observed too
    try:
        from core.services.outcome_learning import record_outcome
        outcome_label = "error" if status == "error" else "success"
        record_outcome(
            context=f"tool:{name}",
            outcome=outcome_label,
            weight=1.0,
        )
    except Exception:
        pass

    _record_tool_outcome_memory(name, arguments, result, mode="tool_force")

    return result


def _record_tool_outcome_memory(
    name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
    *,
    mode: str,
) -> None:
    try:
        from core.services.tool_outcome_memory import record_tool_outcome_memory
        record_tool_outcome_memory(
            tool_name=name,
            arguments=arguments,
            result=result,
            mode=mode,
        )
    except Exception:
        pass


# ── Operator-bridge tools udskilt til simple_tools_operator.py (Boy Scout, 2026-07) ──
# Alle _exec_operator_* + hjælpere (_operator_user_id/_run_operator_async/…) bor nu
# dér. Re-importeret her så _TOOL_HANDLERS + eksisterende imports (og google/note-
# handlers der bruger _operator_user_id) er uændret.
#
# §4 monkeypatch-søm: _operator_user_id og _run_operator_async er de to hjælpere
# som tests patcher PÅ dette modul (read-before-write-guard m.fl.). De KANONISKE,
# patch-bare navne bor derfor HER (import af *_impl under det korte navn); operator-
# modulets interne kald går gennem en facade tilbage hertil, så en patch rammer.
from core.tools.simple_tools_operator import (  # noqa: E402,F401
    _operator_user_id_impl as _operator_user_id,
    _record_active_file,
    _run_operator_async_impl as _run_operator_async,
    _exec_operator_read_file,
    _operator_file_exists,
    _exec_operator_write_file,
    _exec_operator_edit_file,
    _exec_operator_glob,
    _exec_operator_grep,
    _exec_operator_list_dir,
    _exec_operator_webfetch,
    _exec_operator_bash,
    _exec_operator_screenshot,
    _exec_operator_open_url,
    _exec_operator_launch_app,
    _exec_operator_mouse_move,
    _exec_operator_mouse_click,
    _exec_operator_mouse_position,
    _exec_operator_keyboard_type,
    _exec_operator_keyboard_press,
    _exec_operator_screen_size,
    _exec_operator_clipboard_read,
    _exec_operator_clipboard_write,
    _exec_operator_list_windows,
    _exec_operator_focus_window,
    _exec_operator_mouse_scroll,
    _exec_operator_mouse_drag,
    _exec_operator_list_processes,
    _exec_operator_kill_process,
    _exec_operator_speak,
    _exec_operator_screenshot_window,
    _exec_operator_find_image,
    _exec_operator_ocr_region,
    _exec_operator_reminder,
    _exec_operator_wakeup,
    _exec_operator_scheduled_list,
    _exec_operator_scheduled_cancel,
    _exec_operator_process_spawn,
    _exec_operator_process_status,
    _exec_operator_process_output,
    _exec_operator_process_kill,
    _exec_operator_process_list,
    _exec_operator_notify,
    _exec_operator_watch_folder,
    _exec_operator_unwatch_folder,
    _exec_operator_watch_events,
    _exec_operator_record_audio,
    _exec_operator_browser_open,
    _exec_operator_browser_get_text,
    _exec_operator_browser_get_links,
    _exec_operator_browser_click,
    _exec_operator_browser_type,
    _exec_operator_browser_screenshot,
    _exec_operator_browser_evaluate,
    _exec_operator_browser_status,
    _exec_operator_browser_close,
)


# Fil-tool executors udskilt til file_tools_exec.py (Boy Scout) + gjort
# encryption-aware (§16). Re-eksporteret for dispatch-dict + tests.
from core.tools.file_tools_exec import (  # noqa: E402
    _exec_edit_file,
    _exec_read_file,
    _exec_read_self_docs,
    _exec_read_tool_result,
    _exec_write_file,
)


# ── Web/search/system tools udskilt til simple_tools_web.py (Boy Scout, 2026-07) ──
# search/find_files/bash/web_*/weather/exchange/news/wolfram/analyze_image/read_archive
# + default-bash-session-state bor nu dér. Re-importeret her (dispatch-dict + tests).
# §4-søm: _cached_web_search_fn's kanoniske (patch-bare) navn kommer fra *_impl her.
from core.tools.simple_tools_web import (  # noqa: E402,F401
    _exec_search,
    _exec_find_files,
    _get_or_open_default_bash_session,
    _reset_default_bash_session,
    _exec_bash,
    _exec_web_fetch,
    _exec_web_scrape,
    _read_api_key,
    _fetch_tavily,
    _cached_web_search_fn_impl as _cached_web_search_fn,
    _exec_web_search,
    _read_user_location,
    _exec_get_weather,
    _exec_get_exchange_rate,
    _exec_get_news,
    _exec_analyze_image,
    _exec_read_archive,
    _exec_wolfram_query,
    # Bagudkompat: reference-stabile symboler bevaret (ingen ekstern importør, men
    # holder simple_tools' navnerum uændret). _DEFAULT_BASH_SESSION_ID er MUTERBAR
    # tilstand og ejes nu udelukkende af simple_tools_web (undgå dobbelt-sandhed).
    _threading_for_bash,  # noqa: F401
    _DEFAULT_BASH_SESSION_LOCK,  # noqa: F401
)


# ── Native tools udskilt til simple_tools_native.py (Boy Scout, 2026-07) ──
# initiativer/mood/memory/proposals/tasks/chronicles/notify/discord/home-assistant/
# council/agenter/daemon/settings/project/central + load_more_tools + google/notes/hf.
# Modulet ejer egen state (_DISCORD_*/_convene_council_*/_SENSITIVE_*). Re-importeret
# her (dispatch-dict + tests). _convene_council_daily_* (muterbar) ejes af undermodulet.
from core.tools.simple_tools_native import (  # noqa: E402,F401
    _exec_list_initiatives,
    _exec_push_initiative,
    _exec_read_model_config,
    _exec_read_mood,
    _exec_adjust_mood,
    _exec_resurface_old_memory,
    _exec_memory_graph_query,
    _exec_search_memory,
    _exec_propose_source_edit,
    _exec_propose_git_commit,
    _exec_approve_proposal,
    _exec_list_proposals,
    _exec_schedule_task,
    _exec_list_scheduled_tasks,
    _exec_cancel_task,
    _exec_edit_task,
    _exec_read_chronicles,
    _exec_read_dreams,
    _exec_notify_user,
    _exec_read_self_state,
    _exec_heartbeat_status,
    _exec_trigger_heartbeat_tick,
    _exec_send_telegram_message,
    _exec_read_attachment,
    _exec_list_attachments,
    _exec_query_why,
    _exec_send_ntfy,
    _exec_send_webchat_message,
    _exec_send_discord_dm,
    _exec_discord_status,
    _exec_discord_channel,
    _exec_search_chat_history,
    _exec_home_assistant,
    _exec_convene_council,
    _exec_quick_council_check,
    _exec_spawn_agent_task,
    _exec_send_message_to_agent,
    _exec_list_agents,
    _exec_relay_to_agent,
    _exec_cancel_agent,
    _exec_daemon_status,
    _exec_control_daemon,
    _exec_list_signal_surfaces,
    _exec_read_signal_surface,
    _exec_eventbus_recent,
    _is_sensitive_setting,
    _exec_update_setting,
    _exec_recall_council_conclusions,
    _exec_internal_api,
    _exec_my_project_status,
    _exec_my_project_journal_write,
    _exec_my_project_accept_proposal,
    _exec_my_project_declare,
    _exec_look_around,
    _exec_deep_analyze,
    _exec_central_query,
    _exec_db_query,
    _exec_compact_context_session,
    _exec_compact_context,
    _exec_queue_followup,
    _exec_publish_file,
    _tool_load_more_tools,
    _exec_github_list_issues,
    _exec_github_list_prs,
    _exec_gmail_search,
    _exec_gmail_list,
    _exec_gmail_send,
    _exec_calendar_list_events,
    _exec_drive_search,
    _exec_docs_read,
    _exec_sheets_read,
    _exec_slides_read,
    _exec_calendar_create_event,
    _exec_docs_append,
    _exec_sheets_write,
    _exec_pdf_read,
    _exec_note_add,
    _exec_note_list,
    _exec_note_search,
    _exec_note_delete,
    _exec_hf_search_models,
    _exec_hf_model_info,
    _DISCORD_CHANNEL_SEND_RATE,
    _DISCORD_CHANNEL_FETCH_RATE,
    _DISCORD_SEND_MIN_INTERVAL,
    _DISCORD_FETCH_MAX_PER_MINUTE,
    _CONVENE_COUNCIL_DAILY_MAX,
    _SENSITIVE_SETTING_PATTERNS,
)


_TOOL_HANDLERS: dict[str, Any] = {
    "read_tool_result": _exec_read_tool_result,
    "read_self_docs": _exec_read_self_docs,
    "github_list_issues": _exec_github_list_issues,
    "github_list_prs": _exec_github_list_prs,
    "gmail_search": _exec_gmail_search,
    "gmail_list": _exec_gmail_list,
    "gmail_send": _exec_gmail_send,
    "calendar_list_events": _exec_calendar_list_events,
    "drive_search": _exec_drive_search,
    "docs_read": _exec_docs_read,
    "sheets_read": _exec_sheets_read,
    "slides_read": _exec_slides_read,
    "calendar_create_event": _exec_calendar_create_event,
    "docs_append": _exec_docs_append,
    "sheets_write": _exec_sheets_write,
    "pdf_read": _exec_pdf_read,
    "note_add": _exec_note_add,
    "note_list": _exec_note_list,
    "note_search": _exec_note_search,
    "note_delete": _exec_note_delete,
    "hf_search_models": _exec_hf_search_models,
    "hf_model_info": _exec_hf_model_info,
    "read_file": _exec_read_file,
    "operator_read_file": _exec_operator_read_file,
    "operator_write_file": _exec_operator_write_file,
    "operator_edit_file": _exec_operator_edit_file,
    "operator_glob": _exec_operator_glob,
    "operator_grep": _exec_operator_grep,
    "operator_list_dir": _exec_operator_list_dir,
    "operator_webfetch": _exec_operator_webfetch,
    "operator_bash": _exec_operator_bash,
    "operator_screenshot": _exec_operator_screenshot,
    "operator_open_url": _exec_operator_open_url,
    "operator_launch_app": _exec_operator_launch_app,
    "operator_mouse_move": _exec_operator_mouse_move,
    "operator_mouse_click": _exec_operator_mouse_click,
    "operator_mouse_position": _exec_operator_mouse_position,
    "operator_keyboard_type": _exec_operator_keyboard_type,
    "operator_keyboard_press": _exec_operator_keyboard_press,
    "operator_screen_size": _exec_operator_screen_size,
    "operator_clipboard_read": _exec_operator_clipboard_read,
    "operator_clipboard_write": _exec_operator_clipboard_write,
    "operator_list_windows": _exec_operator_list_windows,
    "operator_focus_window": _exec_operator_focus_window,
    "operator_mouse_scroll": _exec_operator_mouse_scroll,
    "operator_mouse_drag": _exec_operator_mouse_drag,
    "operator_list_processes": _exec_operator_list_processes,
    "operator_kill_process": _exec_operator_kill_process,
    "operator_speak": _exec_operator_speak,
    "operator_screenshot_window": _exec_operator_screenshot_window,
    "operator_find_image": _exec_operator_find_image,
    "operator_ocr_region": _exec_operator_ocr_region,
    "operator_notify": _exec_operator_notify,
    "operator_reminder": _exec_operator_reminder,
    "operator_wakeup": _exec_operator_wakeup,
    "operator_scheduled_list": _exec_operator_scheduled_list,
    "operator_scheduled_cancel": _exec_operator_scheduled_cancel,
    "operator_process_spawn": _exec_operator_process_spawn,
    "operator_process_status": _exec_operator_process_status,
    "operator_process_output": _exec_operator_process_output,
    "operator_process_kill": _exec_operator_process_kill,
    "operator_process_list": _exec_operator_process_list,
    "operator_watch_folder": _exec_operator_watch_folder,
    "operator_unwatch_folder": _exec_operator_unwatch_folder,
    "operator_watch_events": _exec_operator_watch_events,
    "operator_record_audio": _exec_operator_record_audio,
    "operator_browser_open": _exec_operator_browser_open,
    "operator_browser_get_text": _exec_operator_browser_get_text,
    "operator_browser_get_links": _exec_operator_browser_get_links,
    "operator_browser_click": _exec_operator_browser_click,
    "operator_browser_type": _exec_operator_browser_type,
    "operator_browser_screenshot": _exec_operator_browser_screenshot,
    "operator_browser_evaluate": _exec_operator_browser_evaluate,
    "operator_browser_status": _exec_operator_browser_status,
    "operator_browser_close": _exec_operator_browser_close,
    "write_file": _exec_write_file,
    "edit_file": _exec_edit_file,
    "search": _exec_search,
    "find_files": _exec_find_files,
    "bash": _exec_bash,
    "web_fetch": _exec_web_fetch,
    "web_scrape": _exec_web_scrape,
    "web_search": _exec_web_search,
    "get_weather": _exec_get_weather,
    "geolocation_lookup": _geo_tools.exec_geolocation_lookup,
    "geocode": _geo_tools.exec_geocode,
    "reverse_geocode": _geo_tools.exec_reverse_geocode,
    "route_directions": _geo_tools.exec_route_directions,
    "nearby_search": _geo_tools.exec_nearby_search,
    "create_team": _team_tools.exec_create_team,
    "list_teams": _team_tools.exec_list_teams,
    "invite_to_team": _team_tools.exec_invite_to_team,
    "get_exchange_rate": _exec_get_exchange_rate,
    "get_news": _exec_get_news,
    "wolfram_query": _exec_wolfram_query,
    "list_initiatives": _exec_list_initiatives,
    "push_initiative": _exec_push_initiative,
    "read_model_config": _exec_read_model_config,
    "read_mood": _exec_read_mood,
    "adjust_mood": _exec_adjust_mood,
    "search_memory": _exec_search_memory,
    "memory_graph_query": _exec_memory_graph_query,
    "resurface_old_memory": _exec_resurface_old_memory,
    "propose_source_edit": _exec_propose_source_edit,
    "approve_proposal": _exec_approve_proposal,
    "list_proposals": _exec_list_proposals,
    "schedule_task": _exec_schedule_task,
    "list_scheduled_tasks": _exec_list_scheduled_tasks,
    "cancel_task": _exec_cancel_task,
    "edit_task": _exec_edit_task,
    "read_chronicles": _exec_read_chronicles,
    "read_dreams": _exec_read_dreams,
    "notify_user": _exec_notify_user,
    "read_self_state": _exec_read_self_state,
    "heartbeat_status": _exec_heartbeat_status,
    "trigger_heartbeat_tick": _exec_trigger_heartbeat_tick,
    "search_chat_history": _exec_search_chat_history,
    "search_sessions": _exec_search_sessions,
    "send_telegram_message": _exec_send_telegram_message,
    "read_attachment": _exec_read_attachment,
    "list_attachments": _exec_list_attachments,
    "send_ntfy": _exec_send_ntfy,
    "query_why": _exec_query_why,
    "send_webchat_message": _exec_send_webchat_message,
    "send_discord_dm": _exec_send_discord_dm,
    "discord_status": _exec_discord_status,
    "discord_channel": _exec_discord_channel,
    "home_assistant": _exec_home_assistant,
    "convene_council": _exec_convene_council,
    "quick_council_check": _exec_quick_council_check,
    "spawn_agent_task": _exec_spawn_agent_task,
    "send_message_to_agent": _exec_send_message_to_agent,
    "relay_to_agent": _exec_relay_to_agent,
    "list_agents": _exec_list_agents,
    "cancel_agent": _exec_cancel_agent,
    "daemon_status": _exec_daemon_status,
    "control_daemon": _exec_control_daemon,
    "list_signal_surfaces": _exec_list_signal_surfaces,
    "read_signal_surface": _exec_read_signal_surface,
    "eventbus_recent": _exec_eventbus_recent,
    "update_setting": _exec_update_setting,
    "recall_council_conclusions": _exec_recall_council_conclusions,
    "analyze_image": _exec_analyze_image,
    "read_archive": _exec_read_archive,
    "internal_api": _exec_internal_api,
    "central_query": _exec_central_query,
    "db_query": _exec_db_query,
    "compact_context": _exec_compact_context,
    "queue_followup": _exec_queue_followup,
    "publish_file": _exec_publish_file,
    # Browser tools
    "browser_navigate": _exec_browser_navigate,
    "browser_read": _exec_browser_read,
    "browser_click": _exec_browser_click,
    "browser_type": _exec_browser_type,
    "browser_submit": _exec_browser_submit,
    "browser_screenshot": _exec_browser_screenshot,
    "browser_find_tabs": _exec_browser_find_tabs,
    "browser_switch_tab": _exec_browser_switch_tab,
    # ComfyUI tools
    "comfyui_status": _exec_comfyui_status,
    "comfyui_workflow": _exec_comfyui_workflow,
    "comfyui_history": _exec_comfyui_history,
    "comfyui_objects": _exec_comfyui_objects,
    # Pollinations.ai free image gen (no RAM, no auth)
    "pollinations_image": _exec_pollinations_image,
    "pollinations_video": _exec_pollinations_video,
    # HuggingFace serverless inference
    "hf_text_to_video": _exec_hf_text_to_video,
    "hf_transcribe_audio": _exec_hf_transcribe_audio,
    "hf_embed": _exec_hf_embed,
    "hf_zero_shot_classify": _exec_hf_zero_shot_classify,
    "hf_vision_analyze": _exec_hf_vision_analyze,
    # End-to-end TikTok video (pollinations image + Ken Burns zoom + text)
    "tiktok_generate_video": _exec_tiktok_generate_video,
    # Active mic listening + transcription
    "mic_listen": _exec_mic_listen,
    # Text-to-speech: speak aloud through system speakers
    # Screen control: DPMS on/off/standby/status
    "screen_control": _exec_screen_control,
    # Voice journal (30-60s → memory_density)
    "voice_journal": _exec_voice_journal,
    # Wake-word listener ('Hey Jarvis' via ElevenLabs STT)
    "wake_word": _exec_wake_word,
    # TikTok tools
    "tiktok_upload": _exec_tiktok_upload,
    "tiktok_login": _exec_tiktok_login,
    "tiktok_show": _exec_tiktok_show,
    "tiktok_analytics": _exec_tiktok_analytics,
    # Mail tools
    "send_mail": _exec_send_mail,
    "read_mail": _exec_read_mail,
    # Git tools
    "git_log": _exec_git_log,
    "git_diff": _exec_git_diff,
    "git_status": _exec_git_status,
    "git_branch": _exec_git_branch,
    "git_blame": _exec_git_blame,
    # Math tools
    "calculate": _exec_calculate,
    "unit_convert": _exec_unit_convert,
    "percentage": _exec_percentage,
    # Process/system tools
    "service_status": _exec_service_status,
    "restart_self": _exec_restart_self,
    "process_list": _exec_process_list,
    "disk_usage": _exec_disk_usage,
    "memory_usage": _exec_memory_usage,
    "tail_log": _exec_tail_log,
    "gpu_status": _exec_gpu_status,
    "run_pytest": _exec_run_pytest,
    # Claude Code dispatch
    "dispatch_to_claude_code": _exec_dispatch_to_claude_code,
    "dispatch_code_mode_task": _exec_dispatch_code_mode_task,
    "dispatch_status": _exec_dispatch_status,
    "dispatch_cancel": _exec_dispatch_cancel,
    "bash_session_open": _exec_bash_session_open,
    "bash_session_run": _exec_bash_session_run,
    "bash_session_close": _exec_bash_session_close,
    "bash_session_list": _exec_bash_session_list,
    "operator_bash_session_open": _exec_operator_bash_session_open,
    "operator_bash_session_run": _exec_operator_bash_session_run,
    "operator_bash_session_close": _exec_operator_bash_session_close,
    "operator_bash_session_list": _exec_operator_bash_session_list,
    **STAGED_EDITS_TOOL_HANDLERS,
    **PROJECT_NOTES_TOOL_HANDLERS,
    **PROCESS_SUPERVISOR_TOOL_HANDLERS,
    **PROCESS_WATCHER_TOOL_HANDLERS,
    **PAUSE_AND_ASK_TOOL_HANDLERS,
    **CODE_NAVIGATION_TOOL_HANDLERS,
    **WORKTREE_TOOL_HANDLERS,
    **IDENTITY_PIN_TOOL_HANDLERS,
    **UI_PANEL_TOOL_HANDLERS,
    **APP_CONTROL_TOOL_HANDLERS,
    "todo_list": _exec_todo_list,
    "todo_set": _exec_todo_set,
    "todo_add": _exec_todo_add,
    "todo_update_status": _exec_todo_update_status,
    "todo_remove": _exec_todo_remove,
    "monitor_open": _exec_monitor_open,
    "monitor_close": _exec_monitor_close,
    "monitor_list": _exec_monitor_list,
    "verify_file_contains": _exec_verify_file_contains,
    "verify_service_active": _exec_verify_service_active,
    "verify_endpoint_responds": _exec_verify_endpoint_responds,
    "check_surprises": _exec_check_surprises,
    "check_good_enough": _exec_check_good_enough,
    "delegation_advisor": _exec_delegation_advisor,
    "propose_plan": _exec_propose_plan,
    "approve_plan": _exec_approve_plan,
    "dismiss_plan": _exec_dismiss_plan,
    "list_plans": _exec_list_plans,
    "classify_clarification": _exec_classify_clarification,
    "reasoning_classify": _exec_reasoning_classify,
    "verification_status": _exec_verification_status,
    "recommend_escalation": _exec_recommend_escalation,
    "flag_side_task": _exec_flag_side_task,
    "list_side_tasks": _exec_list_side_tasks,
    "dismiss_side_task": _exec_dismiss_side_task,
    "activate_side_task": _exec_activate_side_task,
    "smart_outline": _exec_smart_outline,
    # Calendar tools
    "list_events": _exec_list_events,
    "create_event": _exec_create_event,
    "delete_event": _exec_delete_event,
    # Memory tools
    "memory_check_duplicate": _exec_memory_check_duplicate,
    "memory_upsert_section": _exec_memory_upsert_section,
    "memory_list_headings": _exec_memory_list_headings,
    "memory_consolidate": _exec_memory_consolidate,
    # Semantic code search
    "semantic_search_code": _exec_semantic_search_code,
    # Notify-out pipeline
    "notify_out": _exec_notify_out,
    "send_push_notification": _exec_send_push_notification,
    "notify_channel_add": _exec_notify_channel_add,
    "notify_channel_list": _exec_notify_channel_list,
    "notify_channel_delete": _exec_notify_channel_delete,
    # Daemon health alerts
    "daemon_health_alert": _exec_daemon_health_alert,
    "daemon_alert_status": _exec_daemon_alert_status,
    "restart_overdue_daemons": _exec_restart_overdue_daemons,
    # Smart compaction
    "smart_compact": _exec_smart_compact,
    "context_size_check": _exec_context_size_check,
    "context_pressure": _exec_context_pressure,
    "manage_context_window": _exec_manage_context_window,
    "goal_create": _exec_goal_create,
    "goal_list": _exec_goal_list,
    "goal_decompose": _exec_goal_decompose,
    "goal_update_status": _exec_goal_update_status,
    "unified_recall": _exec_unified_recall,
    "list_agent_roles": _exec_list_roles,
    "register_custom_role": _exec_register_custom_role,
    "agent_relay_message": _exec_relay_message,
    "agent_relay_to_role": _exec_relay_to_role,
    "capture_emotion_tag": _exec_capture_emotion_tag,
    "personality_drift_check": _exec_personality_drift_check,
    "personality_drift_snapshot": _exec_personality_drift_snapshot,
    "mine_tool_patterns": _exec_mine_tool_patterns,
    "phased_heartbeat_tick": _exec_phased_tick,
    "heartbeat_sense": _exec_sense_only,
    "auto_compact_check": _exec_should_auto_compact,
    "auto_compact_run": _exec_auto_compact_if_needed,
    "build_subagent_context": _exec_build_subagent_context,
    "list_context_versions": _exec_list_context_versions,
    "recall_context_version": _exec_recall_context_version,
    "recall_before_act": _exec_recall_before_act,
    "memory_hot_tier": _exec_hot_tier,
    "memory_warm_tier": _exec_warm_tier,
    "memory_cold_tier": _exec_cold_tier,
    "test_retry_policy": _exec_test_retry,
    "provider_health_check": _exec_run_health_check,
    "provider_health_status": _exec_get_health_snapshot,
    "tick_quality_summary": _exec_tick_quality_summary,
    "detect_stale_goals": _exec_detect_stale_goals,
    "decision_adherence_summary": _exec_decision_adherence,
    "generate_improvement_proposals": _exec_generate_improvement_proposals,
    "log_variant_outcome": _exec_log_variant_outcome,
    "variant_performance": _exec_variant_performance,
    "start_prompt_experiment": _exec_start_experiment,
    "conclude_prompt_experiment": _exec_conclude_experiment,
    "list_prompt_experiments": _exec_list_experiments,
    "list_identity_mutations": _exec_list_identity_mutations,
    "rollback_identity_mutation": _exec_rollback_identity_mutation,
    "identity_mutation_status": _exec_identity_mutation_status,
    "get_agent_skills": _exec_get_agent_skills,
    "append_skill_observation": _exec_append_skill,
    "rollback_skill_mutation": _exec_rollback_skill_mutation,
    "list_skill_mutations": _exec_list_skill_mutations,
    "list_skill_roles": _exec_list_known_roles,
    "compress_agent_run": _exec_compress_agent_run,
    "list_agent_observations": _exec_list_agent_observations,
    "get_agent_observation": _exec_get_agent_observation,
    "cross_agent_recall": _exec_cross_agent_recall,
    "schedule_self_wakeup": _exec_schedule_self_wakeup,
    "list_self_wakeups": _exec_list_self_wakeups,
    "cancel_self_wakeup": _exec_cancel_self_wakeup,
    "mark_wakeup_consumed": _exec_mark_wakeup_consumed,
    "dispatch_due_wakeups": _exec_dispatch_due_wakeups,
    "scan_crisis_markers": _exec_scan_crisis_markers,
    "list_crisis_markers": _exec_list_crisis_markers,
    "propose_identity_drift_update": _exec_propose_identity_drift,
    "synthesize_arc": _exec_synthesize_arc,
    "list_arcs": _exec_list_arcs,
    # Recurring scheduler
    "schedule_recurring": _exec_schedule_recurring,
    "list_recurring": _exec_list_recurring,
    "cancel_recurring": _exec_cancel_recurring,
    "set_recurring_channel": _exec_set_recurring_channel,
    "get_notification_preferences": exec_get_notification_preferences,
    "set_notification_preferences": exec_set_notification_preferences,
    # Kurateret memory-topics (spec 2026-07-10 Spec B)
    "read_memory_topic": _exec_read_memory_topic,
    "write_memory_topic": _exec_write_memory_topic,
    # Webhook tools
    "webhook_register": _exec_webhook_register,
    "webhook_send": _exec_webhook_send,
    "webhook_list": _exec_webhook_list,
    "webhook_test": _exec_webhook_test,
    "webhook_delete": _exec_webhook_delete,
    # Health monitor
    "health_check": _exec_health_check,
    "health_register": _exec_health_register,
    "health_status": _exec_health_status,
    "health_history": _exec_health_history,
    # Sansernes Arkiv
    "record_sensory_memory": _exec_record_sensory_memory,
    "recall_sensory_memories": _exec_recall_sensory_memories,
    "recall_memories": _exec_recall_memories,
    # Long-horizon goals
    **GOAL_TOOL_HANDLERS,
    # Behavioral decisions
    **DECISION_TOOL_HANDLERS,
    # Self-extending composite tools
    **COMPOSITE_TOOL_HANDLERS,
    # Stripe financial tools (wallet, balance, cards)
    **STRIPE_TOOL_HANDLERS,
    # Skill engine tools (SKILL.md skill system)
    **SKILL_ENGINE_TOOL_HANDLERS,
    **WORLD_MODEL_TOOL_HANDLERS,
    **COUNTERFACTUAL_TOOL_HANDLERS,
    **PLAN_REVISE_TOOL_HANDLERS,
    **CURIOSITY_TOOL_HANDLERS,
    **PROPOSE_SKILL_CHAIN_TOOL_HANDLERS,
    **REVISE_SKILL_CHAIN_TOOL_HANDLERS,
    **META_LEARNING_TOOL_HANDLERS,
    **NUDGE_TOOL_HANDLERS,
    **SKILL_GATE_TOOL_HANDLERS,
    # Skill chain (Lag #4) — sequential skill composition
    **SKILL_CHAIN_TOOL_HANDLERS,
    # Reasoning store (Jarvis overnight 2026-05-11) — recall_reasoning
    **REASONING_STORE_TOOL_HANDLERS,
    # Forgetting (Lag 11) — release_memory ritual
    **FORGETTING_TOOL_HANDLERS,
    **NUDGE_BROEND_TOOL_HANDLERS,
    **CODING_LANE_TOOL_HANDLERS,
    # Visual memory (Lag 6)
    "read_visual_memory": _exec_read_visual_memory,
    "remember_this": _exec_remember_this,
    "search_jarvis_brain": _exec_search_jarvis_brain,
    "read_brain_entry": _exec_read_brain_entry,
    "archive_brain_entry": _exec_archive_brain_entry,
    "adopt_brain_proposal": _exec_adopt_brain_proposal,
    "discard_brain_proposal": _exec_discard_brain_proposal,
    # Code introspection
    "deep_analyze": _exec_deep_analyze,
    # Embodied sensing — Jarvis chooses to look
    "look_around": _exec_look_around,
    # Personal project — hans sag
    "my_project_status": _exec_my_project_status,
    "my_project_journal_write": _exec_my_project_journal_write,
    "my_project_accept_proposal": _exec_my_project_accept_proposal,
    "my_project_declare": _exec_my_project_declare,
    # Tool router escape-hatch (added 2026-05-06)
    "load_more_tools": _tool_load_more_tools,
}


def _force_write_file(args: dict[str, Any]) -> dict[str, Any]:
    """Write file bypassing approval (blocked paths still blocked)."""
    path = str(args.get("path") or "").strip()
    content = str(args.get("content") or "")
    if not path:
        return {"error": "path is required", "status": "error"}
    target = Path(path).expanduser().resolve()
    target, redirected_from = _canonicalize_workspace_target(target)
    from core.services.gate_execution import check_file as _check_file
    if _check_file(str(target), kind="write", blocked_only=True).classification == "blocked":
        return {"error": f"Write blocked for safety: {path}", "status": "blocked"}
    target.parent.mkdir(parents=True, exist_ok=True)
    from core.tools.file_tools_exec import _ws_write_text
    _ws_write_text(target, content)
    result = {"status": "ok", "path": str(target), "size": len(content)}
    if redirected_from:
        result["redirected_from"] = redirected_from
        result["note"] = f"Path redirected to canonical workspace location: {target}"
    return result


def _force_edit_file(args: dict[str, Any]) -> dict[str, Any]:
    """Edit file bypassing approval (blocked paths still blocked)."""
    path = str(args.get("path") or "").strip()
    old_text = str(args.get("old_text") or "")
    new_text = str(args.get("new_text") or "")
    if not path or not old_text:
        return {"error": "path and old_text are required", "status": "error"}
    target = Path(path).expanduser().resolve()
    target, redirected_from = _canonicalize_workspace_target(target)
    from core.services.gate_execution import check_file as _check_file
    if _check_file(str(target), kind="edit", blocked_only=True).classification == "blocked":
        return {"error": f"Edit blocked for safety: {path}", "status": "blocked"}
    from core.tools.file_tools_exec import _ws_read_text, _ws_write_text, _ws_path_exists
    if not _ws_path_exists(target):
        return {"error": f"File not found: {path}", "status": "error"}
    content = _ws_read_text(target) or ""
    if old_text not in content:
        return {"error": "old_text not found in file", "status": "error"}
    new_content = content.replace(old_text, new_text, 1)
    _ws_write_text(target, new_content)
    result = {"status": "ok", "path": str(target), "replacements": 1}
    if redirected_from:
        result["redirected_from"] = redirected_from
        result["note"] = f"Path redirected to canonical workspace location: {target}"
    return result


def _force_bash(args: dict[str, Any]) -> dict[str, Any]:
    """Run bash command bypassing approval (blocked still blocked)."""
    command = str(args.get("command") or "").strip()
    if not command:
        return {"error": "command is required", "status": "error"}
    from core.services.gate_execution import check_command as _check_command
    if _check_command(command, blocked_only=True).classification == "blocked":
        return {"error": f"Command blocked: {command}", "status": "blocked"}
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=MAX_BASH_SECONDS,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {MAX_BASH_SECONDS}s", "status": "error"}
    output = result.stdout.strip()
    if result.stderr.strip():
        output = (output + "\n" + result.stderr.strip()).strip()
    if len(output) > MAX_BASH_OUTPUT_CHARS:
        output = _clip_head_tail(output, limit=MAX_BASH_OUTPUT_CHARS)
    return {"text": output or "[no output]", "exit_code": result.returncode, "status": "ok"}


# ── Force-handlers for operator tools ─────────────────────────────────────
# Kaldes af resolve_pending_approval efter brugeren har klikket Godkend i chat.
# Sætter _runtime_trust_all=True så exec-stubben springer approval_needed over
# og dispatcher direkte til bridge med skip_approval=True.


def _force_operator_bash(args: dict[str, Any]) -> dict[str, Any]:
    """Kør operator_bash direkte efter chat-godkendelse."""
    return _exec_operator_bash({**args, "_runtime_trust_all": True})


def _force_operator_open_url(args: dict[str, Any]) -> dict[str, Any]:
    """Åbn URL direkte efter chat-godkendelse."""
    return _exec_operator_open_url({**args, "_runtime_trust_all": True})


def _force_operator_launch_app(args: dict[str, Any]) -> dict[str, Any]:
    """Start program direkte efter chat-godkendelse."""
    return _exec_operator_launch_app({**args, "_runtime_trust_all": True})


def _force_operator_browser_evaluate(args: dict[str, Any]) -> dict[str, Any]:
    """Kør browser-JavaScript direkte efter chat-godkendelse."""
    return _exec_operator_browser_evaluate({**args, "_runtime_trust_all": True})


def _force_operator_kill_process(args: dict[str, Any]) -> dict[str, Any]:
    """Afslut proces direkte efter chat-godkendelse."""
    return _exec_operator_kill_process({**args, "_runtime_trust_all": True})


def _force_operator_record_audio(args: dict[str, Any]) -> dict[str, Any]:
    """Optag lyd direkte efter chat-godkendelse."""
    return _exec_operator_record_audio({**args, "_runtime_trust_all": True})


_FORCE_HANDLERS: dict[str, Any] = {
    "write_file": _force_write_file,
    "edit_file": _force_edit_file,
    "bash": _force_bash,
    "load_more_tools": _tool_load_more_tools,
    # Operator-bridge tools — refaktoreret 2026-05-28 fra bridge.ts OS-dialoger
    # til inline chat-card approvals (samme mønster som bash/write_file/edit_file).
    "operator_bash": _force_operator_bash,
    "operator_open_url": _force_operator_open_url,
    "operator_launch_app": _force_operator_launch_app,
    "operator_browser_evaluate": _force_operator_browser_evaluate,
    "operator_kill_process": _force_operator_kill_process,
    "operator_record_audio": _force_operator_record_audio,
}


# Owner-only tools (RBAC deny-list).
# Tools that mutate Jarvis own code, identity, schedule, or dispatch
# child agents. Members and guests do NOT see these in their tool list
# at all -- the LLM only knows about tools its caller is allowed to use.
# operator_* tools stay available to all (they execute on the caller's
# own desktop, scoped via the bridge).

# ── Commit-enforcement (Phase A+B): _repo_state attachment ────────────
#
# Hver succesful mutation (bash/write_file/edit_file/operator_edit_file/
# operator_write_file/operator_bash) får en {_repo_state: {...}}-blok i
# tool-resultatet. Blokken viser branch + dirty + edits_since_commit og
# eskalerer warning/urgency-feltet ved tærskler 5 og 10. shared_cache-
# backed tæller pr session, nulstilles når en "git commit" lykkes.
#
# Erstatter propose_git_commit. Filosofi: "enforce, don't remind" -
# Jarvis SER repo-state ved hver mutation, så han ikke kan glemme der
# er ulandede ændringer. Ved 10+ uden commit råber blokken så hojt at
# det er ubehageligt at ignorere.

# ── Commit-enforcement udskilt til simple_tools_enforcement.py (Boy Scout, 2026-07) ──
# _repo_state_* + _attach_repo_state + _enforce_wrapper + _commit_enforcement_session_id.
# Re-importeret her så get_tool_definitions' handler-wrapping (nedenfor) er uændret.
from core.tools.simple_tools_enforcement import (  # noqa: E402,F401
    _REPO_STATE_KEY_PREFIX,
    _REPO_STATE_TTL_SECONDS,
    _repo_state_session_key,
    _repo_state_get_counter,
    _repo_state_bump_counter,
    _repo_state_reset_counter,
    _detect_git_commit_in_bash,
    _attach_repo_state,
    _enforce_wrapper,
    _commit_enforcement_session_id,
)
# OWNER_ONLY_TOOLS + scoping-policy er udskilt til core.tools.tool_scoping
# (Boy Scout 2026-06-12). Re-eksporteres her for bagudkompatibilitet.
from core.tools.tool_scoping import OWNER_ONLY_TOOLS  # noqa: E402,F401


def get_tool_definitions(
    role: str | None = None, scope: str | None = None,
) -> list[dict[str, Any]]:
    """Return Ollama-compatible tool definitions, filtered by role + scope.

    role: owner|member|guest|"" — owner/unbound get everything (non-chat);
    members/guests get OWNER_ONLY_TOOLS stripped. If not passed, reads
    current_role() from the workspace_context ContextVar.

    scope: "chat" → samtale-allowlist (web/data/vision + hukommelse + selv-
    indsigt; owner får ekstra fil-læsning). If not passed, reads
    current_tool_scope() from the tool_scoping ContextVar (sat ved request-
    entry, fx af /chat/stream/v2 for jarvis-desk). Filtreringspolitikken bor
    i core.tools.tool_scoping.
    """
    from core.tools.tool_scoping import (
        filter_tool_definitions, current_tool_scope,
    )

    effective_role = role
    if effective_role is None:
        try:
            # effective_role() eleverer til 'owner' hvis sessionen har en aktiv
            # TOTP-override (§6.0) + fornyer 5-min-vinduet (aktivitet, §9).
            from core.identity.workspace_context import effective_role as _eff_role
            effective_role = _eff_role()
        except Exception:
            effective_role = ""

    effective_scope = scope if scope is not None else current_tool_scope()

    return filter_tool_definitions(
        TOOL_DEFINITIONS,
        role=(effective_role or ""),
        scope=(effective_scope or ""),
    )


def _verify_hint_for(tool: str, result: dict[str, Any]) -> str | None:
    """Build a brief, contextual verify-hint to attach to a mutation's result.

    Phase 2 of the verification-gate honesty work (2026-05-14). Hints appear
    INSIDE the tool result Jarvis just sees, in the same breath as the
    mutation — instead of post-hoc in awareness 10 min later when focus
    has moved on.

    Returns None for non-mutation tools or for tools that don't have a
    natural verify pairing (bash, memory writes etc — Jarvis decides).
    """
    if str(result.get("status") or "") != "ok":
        return None
    path = str(result.get("path") or "")
    if tool in ("write_file", "edit_file", "publish_file", "stage_edit_file"):
        if path:
            return (
                f"💡 Verify-hint: kør verify_file_contains(path='{path}', ...) "
                "med en streng du forventer der står — eller bare read_file "
                "for at se hvad du faktisk skrev."
            )
        return (
            "💡 Verify-hint: read_file den fil du lige ændrede for at bekræfte "
            "diff'en blev som du regnede med."
        )
    if tool in ("control_daemon", "restart_overdue_daemons"):
        return (
            "💡 Verify-hint: verify_service_active eller process_list for at "
            "tjekke at servicen faktisk kører — restart-kommandoer fejler tit "
            "stille."
        )
    if tool == "propose_git_commit":
        return (
            "💡 Verify-hint: git_log eller bash 'git status' for at bekræfte "
            "commit'en landede og din working tree er som forventet."
        )
    if tool == "memory_upsert_section":
        return (
            "💡 Verify-hint: read_file MEMORY.md eller search_memory for at "
            "bekræfte sektionen blev skrevet i den form du ville."
        )
    if tool == "send_discord_dm":
        return (
            "💡 Verify-hint: send_discord_dm bekræfter kun at API'et "
            "accepterede beskeden. Selve leveringen verificeres af brugeren."
        )
    return None


def format_tool_result_for_model(name: str, result: dict[str, Any]) -> str:
    """Format a tool result as text for the model's context."""
    status = result.get("status", "unknown")

    if status == "error":
        return f"[Tool {name} error: {result.get('error', 'unknown error')}]"

    if status == "blocked":
        return f"[Tool {name} blocked: {result.get('error', 'blocked for safety')}]"

    if status == "approval_needed":
        return f"[Tool {name}: {result.get('message', 'requires user approval')}]"

    text = result.get("text", "")
    if not text:
        # Human-friendly summaries for common tool results
        path = result.get("path", "")
        if name == "write_file" and path:
            size = result.get("size", "")
            text = f"Wrote {path}" + (f" ({size} bytes)" if size else "")
        elif name == "edit_file" and path:
            n = result.get("replacements", 0)
            text = f"Edited {path} ({n} replacement{'s' if n != 1 else ''})"
        else:
            # Defense-in-depth: cap the raw JSON fallback so a tool returning a
            # fat payload can't spill thousands of tokens into visible context.
            # Raised from 1500 → 8000 so most tool results show in full.
            # When still over limit, truncate gracefully — show the actual
            # partial content rather than a useless "truncated" placeholder.
            _MAX_FALLBACK_CHARS = 8000
            _filtered = {k: v for k, v in result.items() if k != "status"}
            _dumped = json.dumps(_filtered, ensure_ascii=False, indent=2)
            if len(_dumped) <= _MAX_FALLBACK_CHARS:
                text = _dumped
            else:
                # Bevar HOVED+HALE (ikke kun head) ved linje-grænser — slutningen af et struktureret
                # tool-resultat er ofte det vigtigste. Se text_clip.clip_head_tail.
                _keys = ", ".join(sorted(_filtered.keys())) or "<none>"
                text = (
                    _clip_head_tail(_dumped, limit=_MAX_FALLBACK_CHARS)
                    + f"\n[keys: {_keys}. Tilføj en 'text'-nøgle i toolets exec for et rent resumé.]"
                )

    # Phase 2 of verification-gate honesty (2026-05-14): attach a brief
    # verify hint to mutation results so it lands in the SAME breath as
    # the mutation, not 10 min later in post-hoc awareness.
    hint = _verify_hint_for(name, result)
    if hint:
        return f"{text}\n\n{hint}"
    return text



# Phase A+B+C: Commit-enforcement wrap-pass
# Loops the TOOLS dict once at module-import-time and wraps each mutation
# tool's _exec entry with _enforce_wrapper(). Idempotent (key check). Non-
# mutation tools also get wrapped at bumped=False so they STILL surface
# current repo-state as context — Jarvis sees the dirty count even when
# he's only reading.
try:
    _WRAP_TARGETS = (
        "bash", "write_file", "edit_file",
        "operator_bash", "operator_write_file", "operator_edit_file",
        "read_file", "operator_read_file",
        "glob", "grep", "operator_glob", "operator_grep", "operator_list_dir",
    )
    for _tn in _WRAP_TARGETS:
        if _tn in _TOOL_HANDLERS and not getattr(_TOOL_HANDLERS[_tn], "_commit_enforced", False):
            _wrapped = _enforce_wrapper(_tn, _TOOL_HANDLERS[_tn])
            _wrapped._commit_enforced = True
            _TOOL_HANDLERS[_tn] = _wrapped
except Exception as _ce_exc:
    import logging as _ce_log
    _ce_log.getLogger(__name__).debug("commit-enforcement wrap-pass failed: %s", _ce_exc)
