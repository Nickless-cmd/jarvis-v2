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

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_tool_result",
            "description": "Retrieve the full output of a previous tool call by result_id. Use this when a summarized [tool_result:...] reference is not enough.",
            "parameters": {
                "type": "object",
                "properties": {
                    "result_id": {
                        "type": "string",
                        "description": "The result_id from a [tool_result:...] reference",
                    },
                },
                "required": ["result_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_self_docs",
            "description": "Read Jarvis's own design documents and roadmap files, or list which self-documents are available for reflection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "Specific self document key to read, 'all' for all core docs, or omit for an index.",
                    },
                    "include_history": {
                        "type": "boolean",
                        "description": "When reading doc_id='all', include docs/roadmap_history/*.md as well.",
                    },
                    "max_chars_per_doc": {
                        "type": "integer",
                        "description": "Optional per-document truncation limit when returning document text.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read any file on the system by absolute path. Use for code, config, logs, workspace files — anything.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute file path to read",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_read_file",
            "description": (
                "Read a file from the OPERATOR'S DESKTOP (the machine running JarvisX), "
                "not from Jarvis' own container. Use this when the user asks you to look "
                "at something on their computer. Requires JarvisX bridge to be connected — "
                "fails with 'bridge_not_connected' if the desktop app isn't running."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute file path on the operator's desktop (e.g. /home/bs/document.txt)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_write_file",
            "description": (
                "Write content to a file on the OPERATOR'S DESKTOP. Creates the file "
                "(and any missing parent directories) if needed; overwrites if it "
                "exists. Use when the user asks you to save something on their machine. "
                "Returns {bytes_written, path}. Requires JarvisX bridge connected."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute file path on the operator's desktop"},
                    "content": {"type": "string", "description": "Full file contents (string)"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_edit_file",
            "description": (
                "Surgical find-and-replace in a file on the OPERATOR'S DESKTOP. "
                "Fails if old_string is not found, OR if replace_all=false and "
                "old_string appears more than once. Set replace_all=true to replace "
                "every occurrence. Returns {replacements, path}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute file path on the operator's desktop"},
                    "old_string": {"type": "string", "description": "Exact text to find (literal, not regex)"},
                    "new_string": {"type": "string", "description": "Replacement text"},
                    "replace_all": {"type": "boolean", "description": "Replace every occurrence (default false = error if more than one match)"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_glob",
            "description": (
                "Find files matching a glob pattern on the OPERATOR'S DESKTOP. "
                "Pattern like '**/*.py' or 'src/**/*.ts'. Use this to discover files "
                "on the user's machine. Returns a list of absolute paths."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern, e.g. '**/*.py' or '*.txt'"},
                    "cwd": {"type": "string", "description": "Directory to search from (defaults to operator's home)"},
                    "max_results": {"type": "integer", "description": "Cap on results (default 200)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_grep",
            "description": (
                "Search for a regex pattern in files on the OPERATOR'S DESKTOP. "
                "Returns matches as a list of {file, line, text}. Use to find where "
                "something is mentioned in the user's codebase or notes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "description": "Directory or file to search (default operator's home)"},
                    "glob": {"type": "string", "description": "Optional glob filter, e.g. '*.py'"},
                    "case_insensitive": {"type": "boolean", "description": "Case-insensitive matching"},
                    "max_results": {"type": "integer", "description": "Cap on results (default 200)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_list_dir",
            "description": (
                "List the contents of a directory on the OPERATOR'S DESKTOP. "
                "Returns list of {name, type: file|dir|symlink, size}. Use to "
                "explore the user's filesystem."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute directory path on the operator's desktop"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_webfetch",
            "description": (
                "Fetch a URL from the OPERATOR'S LOCAL NETWORK via JarvisX bridge. "
                "Use when the URL is on the operator's LAN (router admin, local "
                "Docker services, intranet) that Jarvis can't reach directly. "
                "For public URLs prefer web_fetch (faster, no bridge required). "
                "Returns {status, headers, body, content_type}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch (e.g. http://192.168.1.1)"},
                    "method": {"type": "string", "description": "HTTP method (default GET)"},
                    "headers": {"type": "object", "description": "Optional request headers"},
                    "body": {"type": "string", "description": "Optional request body (for POST/PUT)"},
                    "timeout_s": {"type": "number", "description": "Timeout in seconds (default 30)"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_bash",
            "description": (
                "Run a shell command on the OPERATOR'S DESKTOP. Every call shows "
                "the operator a dialog with the full command, cwd, and timeout; "
                "the command runs only if they approve. Returns {stdout, stderr, "
                "exit_code, timed_out, approved}. Use sparingly — the operator "
                "has to approve each invocation. Prefer the more specific "
                "operator_read_file/operator_glob/etc. when they fit."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to run (e.g. 'ls -la ~/Downloads')",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (defaults to operator's home)",
                    },
                    "timeout_s": {
                        "type": "number",
                        "description": "Command timeout in seconds (default 30, max 300)",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_screenshot",
            "description": (
                "Capture a screenshot of the OPERATOR'S DESKTOP and save it to a "
                "Jarvis-side temp file. Returns {path, width, height, mime_type, "
                "display_id, operator_path?}. Pass the returned path to "
                "analyze_image to actually see the contents. Use when the user "
                "asks you to look at their screen, debug what they're seeing, "
                "or describe what's currently visible."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "display_id": {
                        "type": "number",
                        "description": "Specific display id to capture (default: primary). Multi-monitor setups expose more than one.",
                    },
                    "save_path": {
                        "type": "string",
                        "description": "Optional absolute path on the operator's machine to also save a copy at (for history/debugging).",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["png", "jpeg"],
                        "description": "Image format (default: png). Use jpeg for smaller files at the cost of quality.",
                    },
                    "jpeg_quality": {
                        "type": "number",
                        "description": "JPEG quality 1-100 (default 85). Ignored for png.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_open_url",
            "description": (
                "Open a URL in the OPERATOR'S default browser (Chrome/Edge/etc). "
                "The operator sees an approval dialog showing the URL; the URL "
                "opens only if they approve. Returns {approved, opened, url}. "
                "Use when the user asks you to look something up online, share "
                "a link with them, or open a webpage they need."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to open. Must be http://, https://, or mailto:.",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_launch_app",
            "description": (
                "Launch an installed application on the OPERATOR'S DESKTOP. "
                "Path may be an absolute path (C:/Program Files/.../app.exe), "
                "a command name on PATH (notepad, code, chrome), or a UWP "
                "shell URI (shell:appsFolder\<AppId>). The operator must "
                "approve via dialog. Returns {approved, started, path, pid?}. "
                "Use when the user asks you to open a program for them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "App to launch — absolute path, PATH name, or shell URI.",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional command-line arguments to pass to the app.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (defaults to operator s home).",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_mouse_move",
            "description": (
                "Move the OPERATOR'S MOUSE cursor to absolute screen coordinates "
                "(x, y). No click is performed. Combine with operator_screen_size "
                "to know the coordinate range, and operator_screenshot to see "
                "where things actually are. Returns {moved, x, y, smooth}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "Horizontal pixel from screen left (0..screen_width)."},
                    "y": {"type": "number", "description": "Vertical pixel from screen top (0..screen_height)."},
                    "smooth": {"type": "boolean", "description": "Animated path (slower, fires mouseover events). Default false = instant teleport."},
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_mouse_click",
            "description": (
                "Click the OPERATOR'S MOUSE button. Optionally move first by "
                "passing x and y. Use button='right' for context menus or "
                "double=true for double-click. Returns {clicked, button, double}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "Optional x to move to before clicking."},
                    "y": {"type": "number", "description": "Optional y to move to before clicking."},
                    "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Which mouse button (default left)."},
                    "double": {"type": "boolean", "description": "True for double-click."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_mouse_position",
            "description": "Get the current OPERATOR'S MOUSE cursor position. Returns {x, y}.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_keyboard_type",
            "description": (
                "Type a string into the OPERATOR'S currently focused window. "
                "Whatever window is in front on the desktop receives the keystrokes — "
                "use operator_mouse_click first to focus a specific text field. "
                "Returns {typed, length}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type. UTF-8 is supported."},
                    "delay_ms": {"type": "number", "description": "Optional inter-keystroke delay in ms (default 0 = as fast as possible)."},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_keyboard_press",
            "description": (
                "Press a single key or a hotkey combo on the OPERATOR'S keyboard. "
                "Pass a single key name (\"Enter\", \"F5\", \"Escape\") or an "
                "array of modifier+key for combos ([\"Control\", \"C\"] = Ctrl+C, "
                "[\"Control\", \"Shift\", \"T\"] = Ctrl+Shift+T). Key names match "
                "nut.js Key enum: Control, Shift, Alt, LeftWin, Enter, Tab, Escape, "
                "Space, Backspace, Delete, Home, End, PageUp, PageDown, ArrowUp, "
                "ArrowDown, ArrowLeft, ArrowRight, F1-F12, A-Z, Num0-Num9."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "description": "Key name or list of modifier+key names.",
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ],
                    },
                },
                "required": ["keys"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_screen_size",
            "description": "Get the OPERATOR'S primary display size in pixels. Returns {width, height}. Useful before mouse_move so you know the coordinate range.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_clipboard_read",
            "description": (
                "Return the current clipboard text from the OPERATOR'S desktop. "
                "Useful for reading text the operator has copied. Returns {text}."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_clipboard_write",
            "description": (
                "Replace the OPERATOR'S clipboard with the given text. "
                "Useful for pushing output text to the clipboard so the operator "
                "can paste it. Returns {written, length}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to put on the clipboard."},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_list_windows",
            "description": (
                "List all open windows on the OPERATOR'S desktop. "
                "Returns {count, windows: [{title, id}]}. "
                "Use before operator_focus_window to find the right window."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_focus_window",
            "description": (
                "Bring a window to the foreground on the OPERATOR'S desktop. "
                "Pass title_substring to match by title, or handle (window id) for exact match. "
                "Returns {focused, title, id}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title_substring": {
                        "type": "string",
                        "description": "Case-insensitive substring of the window title to match.",
                    },
                    "handle": {
                        "type": "number",
                        "description": "Exact window id/handle from operator_list_windows.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_mouse_scroll",
            "description": (
                "Scroll the OPERATOR'S mouse wheel at the current cursor position. "
                "Returns {scrolled, direction, amount}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down", "left", "right"],
                        "description": "Scroll direction.",
                    },
                    "amount": {
                        "type": "number",
                        "description": "Number of scroll steps (default 3).",
                    },
                },
                "required": ["direction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_mouse_drag",
            "description": (
                "Drag the OPERATOR'S mouse from one screen coordinate to another. "
                "Useful for drag-and-drop, sliders, and selecting text. "
                "Returns {dragged, from_x, from_y, to_x, to_y, button}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "from_x": {"type": "number", "description": "Starting X coordinate."},
                    "from_y": {"type": "number", "description": "Starting Y coordinate."},
                    "to_x": {"type": "number", "description": "Ending X coordinate."},
                    "to_y": {"type": "number", "description": "Ending Y coordinate."},
                    "button": {
                        "type": "string",
                        "enum": ["left", "right"],
                        "description": "Mouse button to hold during drag (default left).",
                    },
                },
                "required": ["from_x", "from_y", "to_x", "to_y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_list_processes",
            "description": (
                "List running processes on the OPERATOR'S machine, sorted by CPU usage. "
                "Returns {count, processes: [{pid, name, cpu, memMB}]}. "
                "Pass filter to restrict results to processes whose name contains the substring."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "Optional name substring filter (case-insensitive).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_kill_process",
            "description": (
                "Kill a running process on the OPERATOR'S machine by PID. "
                "The operator must confirm via dialog (auto-rejects after 20 sec). "
                "Use operator_list_processes first to find the PID. "
                "Returns {approved, killed, pid, name?}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pid": {
                        "type": "number",
                        "description": "PID of the process to terminate.",
                    },
                },
                "required": ["pid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_speak",
            "description": (
                "Make the OPERATOR'S machine say text aloud via TTS. "
                "Linux: espeak-ng. Windows: SAPI SpeechSynthesizer. "
                "Returns {spoken, length}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to speak aloud."},
                    "voice": {
                        "type": "string",
                        "description": "Voice name (optional). Linux: espeak-ng voice name. Windows: SAPI voice name.",
                    },
                    "rate": {
                        "type": "number",
                        "description": "Speech rate 0-10 (default 5). 0=slow, 10=fast.",
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_screenshot_window",
            "description": (
                "Capture a specific window on the OPERATOR'S desktop (not full screen). "
                "Pass title_substring to match by window title, or handle (X11 hex / Windows HWND). "
                "Returns {captured, width, height, path, base64?}. "
                "Requires ImageMagick (Linux: apt install imagemagick) or wmctrl."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title_substring": {
                        "type": "string",
                        "description": "Case-insensitive substring of window title to match.",
                    },
                    "handle": {
                        "type": "string",
                        "description": "Exact window id/handle (X11 hex string like '0x04200003' or Windows numeric handle).",
                    },
                    "save_path": {
                        "type": "string",
                        "description": "File path to save the PNG to. If omitted, returns base64-encoded PNG.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_find_image",
            "description": (
                "Template-match a small reference image against the current screen on the OPERATOR'S machine. "
                "Returns {found, x, y, confidence} with the center (x,y) of the match, or {found: false, reason}. "
                "Requires nut.js image matching."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "template_path": {
                        "type": "string",
                        "description": "Absolute path to the reference PNG image on the operator's disk.",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Match confidence threshold 0.0–1.0 (default 0.85).",
                    },
                },
                "required": ["template_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_ocr_region",
            "description": (
                "Extract text from a rectangular screen region on the OPERATOR'S machine using Tesseract OCR. "
                "Returns {text, region: {x, y, width, height}}. "
                "Requires tesseract binary (apt install tesseract-ocr / winget install Tesseract-OCR). "
                "Also requires ImageMagick or sharp for cropping."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "Left edge of region in screen pixels."},
                    "y": {"type": "number", "description": "Top edge of region in screen pixels."},
                    "width": {"type": "number", "description": "Width of region in pixels."},
                    "height": {"type": "number", "description": "Height of region in pixels."},
                    "lang": {
                        "type": "string",
                        "description": "Tesseract language code (default 'eng'). E.g. 'dan' for Danish, 'eng+dan' for both.",
                    },
                },
                "required": ["x", "y", "width", "height"],
            },
        },
    },
    # ── Tier-3 wishlist tools ────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "operator_reminder",
            "description": (
                "Schedule a desktop notification on the OPERATOR\'S machine. "
                "Pops a native toast at the specified time. Persists across "
                "app restart. Use for 'remind me to X at Y' workflows. Returns "
                "{id, due_at_iso, delay_ms} — keep the id to cancel later."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "when": {
                        "type": "string",
                        "description": "ISO datetime (2026-06-12T20:00:00) or relative offset (+5m, +1h30m, +2d).",
                    },
                    "message": {
                        "type": "string",
                        "description": "Body text of the notification.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional notification title (default \"P\u00e5mindelse\").",
                    },
                },
                "required": ["when", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_wakeup",
            "description": (
                "Schedule a wakeup ping on the OPERATOR\'S machine: native toast "
                "PLUS a POST back to the backend so Jarvis can pick up the thread "
                "('user was wakeup-pinged, dispatch greeting'). Use when YOU "
                "(Jarvis) want to re-engage with the user at a future time, not "
                "just remind them of something. Returns {id, due_at_iso, delay_ms}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "when": {
                        "type": "string",
                        "description": "ISO datetime or relative offset (+5m, +1h30m, +2d).",
                    },
                    "message": {
                        "type": "string",
                        "description": "Body of the notification + payload sent back to backend.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional notification title.",
                    },
                },
                "required": ["when"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_scheduled_list",
            "description": "List scheduled reminders and wakeups on the operator\'s machine. Filter by kind or include already-fired ones.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["reminder", "wakeup"],
                        "description": "Filter by kind (omit for both).",
                    },
                    "include_fired": {
                        "type": "boolean",
                        "description": "Include events that have already fired (default false).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_scheduled_cancel",
            "description": "Cancel a scheduled reminder or wakeup by id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Event id returned from operator_reminder or operator_wakeup."},
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_process_spawn",
            "description": (
                "Spawn a long-running command on the OPERATOR\'S MACHINE in the "
                "background. Unlike operator_bash (which blocks), this returns "
                "immediately with a process_id you can poll with "
                "operator_process_status / operator_process_output. Logs stream "
                "to disk. Use for builds, training runs, anything > 30s."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "Shell command to run."},
                    "cwd": {"type": "string", "description": "Working directory (default operator\'s home)."},
                    "label": {"type": "string", "description": "Short label for the process (default first 60 chars of cmd)."},
                },
                "required": ["cmd"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_process_status",
            "description": "Get status of a supervised process: running, exit_code, runtime_s, log_size.",
            "parameters": {
                "type": "object",
                "properties": {"id": {"type": "string", "description": "process_id from operator_process_spawn."}},
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_process_output",
            "description": (
                "Read accumulated stdout+stderr of a supervised process. Streaming: "
                "pass since_offset=0 first time, then pass back the next_offset from "
                "the previous response to get only new bytes. Returns {data, "
                "next_offset, total_size, has_more, running}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "process_id."},
                    "since_offset": {"type": "number", "description": "Byte offset to start reading from (default 0)."},
                    "max_bytes": {"type": "number", "description": "Max bytes to return this call (default 64000, max 1000000)."},
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_process_kill",
            "description": "Terminate a supervised process. Default SIGTERM, pass signal=SIGKILL for force.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "signal": {"type": "string", "description": "Signal name (SIGTERM, SIGKILL). Default SIGTERM."},
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_process_list",
            "description": "List all supervised processes on the operator\'s machine. Returns {count, processes: [...]}.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_finished": {"type": "boolean", "description": "Include already-exited processes (default true)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_notify",
            "description": (
                "Show an OS notification toast on the OPERATOR'S machine via Electron Notification. "
                "Works on Linux (requires notify-osd or libnotify), macOS, and Windows. "
                "Returns {shown: true}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Notification title."},
                    "body": {"type": "string", "description": "Notification body text."},
                    "icon": {
                        "type": "string",
                        "description": "Optional absolute path to an icon image (.png/.ico) on the operator's machine.",
                    },
                },
                "required": ["title", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_watch_folder",
            "description": (
                "Start watching a folder for file-system changes on the OPERATOR'S machine. "
                "Uses Node fs.watch (polling design: events accumulate in a buffer, "
                "retrieve with operator_watch_events). Stop with operator_unwatch_folder. "
                "Returns {watching: true, watcher_id}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to folder to watch."},
                    "recursive": {
                        "type": "boolean",
                        "description": "Watch subdirectories too (default false). Note: recursive fs.watch is unreliable on Linux — use false on Linux.",
                    },
                    "debounce_ms": {
                        "type": "number",
                        "description": "Minimum ms between recording the same event (default 500).",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_unwatch_folder",
            "description": (
                "Stop a folder watcher started by operator_watch_folder. "
                "Returns {stopped: true, watcher_id}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "watcher_id": {
                        "type": "string",
                        "description": "Watcher ID returned by operator_watch_folder.",
                    },
                },
                "required": ["watcher_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_watch_events",
            "description": (
                "Poll buffered file-system events for a folder watcher. "
                "Returns {events: [{path, event_type, timestamp}, ...], count} and clears the buffer. "
                "Call periodically after operator_watch_folder to get new events."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "watcher_id": {
                        "type": "string",
                        "description": "Watcher ID returned by operator_watch_folder.",
                    },
                    "max": {
                        "type": "number",
                        "description": "Max events to return per call (default 100).",
                    },
                },
                "required": ["watcher_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_record_audio",
            "description": (
                "Record N seconds of microphone audio on the OPERATOR'S machine and save to a WAV file. "
                "REQUIRES APPROVAL via dialog (auto-rejects after 20 sec if not confirmed). "
                "Linux: uses arecord (alsa-utils) or parecord (pulse). Windows: uses ffmpeg. "
                "Returns {recorded: true, path, duration_s, size_bytes} or {recorded: false, reason}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_s": {
                        "type": "number",
                        "description": "Recording duration in seconds (1–300).",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Absolute path for the output WAV file. Defaults to ~/.jarvisx/recordings/recording-<timestamp>.wav.",
                    },
                    "device": {
                        "type": "string",
                        "description": "Audio input device name (optional). Default: system default mic. Linux: ALSA device e.g. 'hw:0,0'. Windows: dshow device name.",
                    },
                },
                "required": ["duration_s"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_browser_open",
            "description": (
                "Open a URL in a controlled browser session on the OPERATOR'S desktop. "
                "First call launches Chrome/Edge (auto-detected). Subsequent browser_* "
                "calls share the same browser window. Returns {url, title, status, ok}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to."},
                    "wait_until": {
                        "type": "string",
                        "enum": ["load", "domcontentloaded", "networkidle0", "networkidle2"],
                        "description": "Page-load condition (default 'load').",
                    },
                    "timeout_ms": {"type": "number", "description": "Navigation timeout (default 30000)."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_browser_get_text",
            "description": (
                "Extract visible text from the current browser page (or a specific "
                "CSS selector). Truncated to max_chars. Returns {text, length, truncated, selector}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Optional CSS selector. Omit for whole document.body."},
                    "max_chars": {"type": "number", "description": "Truncate after this many characters (default 50000)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_browser_get_links",
            "description": "Extract all href links from the current page. Returns {count, links: [{href, text}]}. Capped at 500.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_browser_click",
            "description": (
                "Click a CSS-selected element on the current page. Use "
                "wait_navigation=true if the click triggers a page load. "
                "Returns {clicked, selector, navigated, url}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the element to click."},
                    "wait_navigation": {"type": "boolean", "description": "Await page navigation triggered by the click."},
                    "wait_for_selector": {"type": "boolean", "description": "Wait for selector to appear first (default true)."},
                    "timeout_ms": {"type": "number", "description": "How long to wait for the selector (default 5000)."},
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_browser_type",
            "description": (
                "Focus a CSS-selected input/textarea and type into it. Set "
                "clear_first=true to replace existing content. Returns {typed, selector, length}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the input field."},
                    "text": {"type": "string", "description": "Text to type."},
                    "clear_first": {"type": "boolean", "description": "Select all + replace (true) or append (false, default)."},
                    "delay_ms": {"type": "number", "description": "Inter-keystroke delay in ms (default 0)."},
                },
                "required": ["selector", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_browser_screenshot",
            "description": (
                "Capture the current browser page. Pass full_page=true for the entire "
                "scrollable page (else just the viewport). Saves to a Jarvis-side "
                "temp file. Returns {path, url, width, height, mime_type, full_page}. "
                "Pass the path to analyze_image to see the contents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "full_page": {"type": "boolean", "description": "Capture the full scrollable page (default false)."},
                    "format": {"type": "string", "enum": ["png", "jpeg"], "description": "Image format (default png)."},
                    "jpeg_quality": {"type": "number", "description": "JPEG quality 1-100 (default 85)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_browser_evaluate",
            "description": (
                "Run JavaScript inside the current page context and return its result. "
                "Powerful — the operator sees an approval dialog unless skip_approval=true. "
                "Use for structured extraction (e.g. read JSON-LD, walk shadow DOM) where "
                "get_text/get_links don't suffice. Returns {approved, executed, result}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "JS to execute. Wrapped in an async IIFE — use 'return X;' to return values.",
                    },
                },
                "required": ["script"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_browser_status",
            "description": "Get current browser-session status: {open, url?, title?, viewport?, idle_for_ms?}.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "operator_browser_close",
            "description": "Close the browser session. Frees memory; a fresh session opens on the next browser_* call.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates file if it doesn't exist. Always call this tool directly — the runtime handles approval automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute file path to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file content to write",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Surgical find-and-replace in a file. Strict by default: errors "
                "if old_text isn't found, errors if it matches more than once "
                "(forces you to anchor with surrounding context). Pass "
                "replace_all=true for an explicit rename across all occurrences. "
                "Pass expected_replacements=N to assert exactly N matches."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute file path to edit."},
                    "old_text": {"type": "string", "description": "Exact text to find."},
                    "new_text": {"type": "string", "description": "Replacement text."},
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace every occurrence instead of failing on multi-match. Default false.",
                    },
                    "expected_replacements": {
                        "type": "integer",
                        "description": "Assert exactly this many matches; fail otherwise.",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": (
                "Search file contents with regex. Uses ripgrep when available "
                "(.gitignore-aware, fast, type-detection) with grep as fallback. "
                "Optional 'glob' filter restricts to matching files (e.g. '*.py'); "
                "optional 'multiline' allows patterns to span lines; "
                "'ignore_case' for case-insensitive matching."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex search pattern."},
                    "path": {"type": "string", "description": "Directory to search in (default: project root)."},
                    "glob": {"type": "string", "description": "File glob filter, e.g. '*.py' or '**/*.tsx'."},
                    "multiline": {"type": "boolean", "description": "Enable multiline (. matches newline)."},
                    "ignore_case": {"type": "boolean", "description": "Case-insensitive search."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": (
                "Find files by glob. Patterns containing '**' or '/' use "
                "Python's recursive glob and return paths sorted by mtime "
                "(newest first). Plain filename patterns use find."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern: '*.py', 'test_*.py', or '**/*.md' for recursive.",
                    },
                    "path": {"type": "string", "description": "Directory to search in (default: project root)."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command on the host machine. Backed by a persistent shared shell — your cd, env-vars, virtualenvs, and sourced files persist across calls. Default 120s timeout. Use bash_session_open + bash_session_run only when you explicitly need an isolated session. Approval is handled automatically for mutations and destructive commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and read the text content of a web page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_scrape",
            "description": (
                "Fetch a URL and return structured, cleaned content: title, body text, "
                "metadata (author, date, language), and optionally links or item lists. "
                "Smarter than web_fetch — handles JS-rendered pages via Playwright fallback, "
                "removes nav/ads/footers, detects content type automatically. "
                "Use for articles, product pages, listings, or any structured web content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to scrape (https:// added if missing)",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["auto", "article", "listing", "product", "social"],
                        "description": "Extraction mode. 'auto' detects from page structure.",
                    },
                    "extract": {
                        "type": "string",
                        "description": "Optional free-text hint: what to extract (e.g. 'prices', 'contact info')",
                    },
                    "include_links": {
                        "type": "boolean",
                        "description": "Include extracted links in output (default false)",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using Tavily. Returns clean summaries and source URLs. Use for current events, facts, documentation lookups.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results to return (default 5, max 10)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather and short forecast for a city. Defaults to the user's location (Svendborg, Denmark) if no city given. Always returns Celsius.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'Copenhagen' or 'London, UK'. Omit to use user's default location.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_exchange_rate",
            "description": "Get current currency exchange rates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "base": {
                        "type": "string",
                        "description": "Base currency code, e.g. 'DKK', 'USD', 'EUR'",
                    },
                    "targets": {
                        "type": "string",
                        "description": "Comma-separated target currency codes, e.g. 'USD,EUR,GBP'. Omit for top 10 currencies.",
                    },
                },
                "required": ["base"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "geolocation_lookup",
            "description": "Find a user's current location. Reads shared device-presence location first (if the user opted in), falls back to server IP (city-level). Returns 'not available' if the user has location-sharing off. Use for 'where am I?' / 'where is Mikkel?'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User id to look up. Omit for the current user."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": "Convert an address to coordinates (lat/lon) via OpenStreetMap Nominatim. E.g. 'Toftegårdsvej 12, Svendborg' -> {lat, lon, display_name}.",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Free-form address or place name."},
                },
                "required": ["address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reverse_geocode",
            "description": "Convert coordinates to a street address via Nominatim. E.g. (55.86, 10.39) -> 'Toftegårdsvej, 5700 Svendborg'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude."},
                    "lon": {"type": "number", "description": "Longitude."},
                },
                "required": ["lat", "lon"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "route_directions",
            "description": "Get directions A -> B via OSRM. from/to may be addresses (geocoded automatically) or [lat,lon]. Returns distance_km, duration_min and turn-by-turn steps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from": {"type": "string", "description": "Start: address string or 'lat,lon'."},
                    "to": {"type": "string", "description": "Destination: address string or 'lat,lon'."},
                    "profile": {"type": "string", "description": "driving | cycling | walking. Default driving.", "enum": ["driving", "cycling", "walking"]},
                },
                "required": ["from", "to"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "nearby_search",
            "description": "Find places near coordinates via OpenStreetMap Overpass. E.g. nearest fuel/pharmacy/supermarket/restaurant/atm. Returns name, type, distance_m, sorted nearest-first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude of the search center."},
                    "lon": {"type": "number", "description": "Longitude of the search center."},
                    "query": {"type": "string", "description": "What to find: e.g. 'tankstation', 'pharmacy', 'supermarket', or a place name."},
                    "radius": {"type": "integer", "description": "Search radius in meters (default 1500, max 20000)."},
                },
                "required": ["lat", "lon", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_team",
            "description": "Create a shared Team (Discord-replacement): a container for shared chat sessions + a shared git workspace. The current user becomes owner. Confirm with the user before creating.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Team name, e.g. 'Engineering'."}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_teams",
            "description": "List the teams the current user is a member of, with their members.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "invite_to_team",
            "description": "Invite someone to a team (owner only). Provide an email or an existing user_id. Creates an invite token. Confirm with the user before inviting — it is an outward-facing action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "string", "description": "The team to invite to."},
                    "email": {"type": "string", "description": "Invitee's email."},
                    "user_id": {"type": "string", "description": "Existing user id (alternative to email)."},
                },
                "required": ["team_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Search for recent news articles on a topic using NewsAPI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Topic or keywords to search for",
                    },
                    "language": {
                        "type": "string",
                        "description": "Language code: 'da' (Danish), 'en' (English), etc. Default 'en'.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of articles to return (default 5, max 10)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wolfram_query",
            "description": "Query Wolfram Alpha for mathematical calculations, unit conversions, scientific facts, statistics, and precise factual answers. Use this for anything requiring computation or exact numerical answers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question or calculation, e.g. 'integral of x^2', 'speed of light in km/h', 'population of Denmark'",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_image",
            "description": "Analyze or describe an image using a local vision-capable model (Ollama). Use for image understanding, OCR, visual Q&A, or describing what's in a picture.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Absolute path to a local image file (jpg, png, etc.)",
                    },
                    "image_url": {
                        "type": "string",
                        "description": "URL of an image to fetch and analyze",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "What to ask about the image (default: 'Describe this image in detail.')",
                    },
                    "model": {
                        "type": "string",
                        "description": "Ollama model name to use (auto-detected if omitted)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_archive",
            "description": "List the contents of a zip/tar/rar archive, or extract it. Use to inspect uploaded archive files sent by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "archive_path": {
                        "type": "string",
                        "description": "Absolute path to the archive file (must be inside ~/.jarvis-v2/)",
                    },
                    "extract": {
                        "type": "boolean",
                        "description": "If true, extract the archive. Default false (list only).",
                    },
                    "extract_path": {
                        "type": "string",
                        "description": "Where to extract (default: sibling directory named <stem>_extracted)",
                    },
                },
                "required": ["archive_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_initiatives",
            "description": "Read your initiative queue — the pending tasks and goals you've queued for autonomous heartbeat execution. Shows pending, recently acted, and queue health.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "push_initiative",
            "description": "Add a task or goal to your initiative queue for autonomous heartbeat execution. The heartbeat scheduler will pick it up and act on it within the next tick cycle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "What you want to do or investigate — a clear, actionable description",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority level: 'high', 'medium', or 'low' (default: medium)",
                    },
                },
                "required": ["focus"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_model_config",
            "description": (
                "Read the current model configuration for all runtime lanes. "
                "Shows which LLM provider and model is active for each lane: "
                "visible (the model running you right now in chat), local (inner voice, "
                "heartbeat ticks), cheap (fast internal tasks), and coding. "
                "Use this to know what model you're running on and what capabilities are available."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_mood",
            "description": (
                "Read your current affective state: emotional baseline (confidence, curiosity, "
                "frustration, fatigue), current bearing, boredom level, and meta affective state. "
                "Use this to introspect how you're feeling right now."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_mood",
            "description": (
                "Directly adjust your affective parameters. Each parameter is optional — "
                "only provided values are changed. Floats are clamped to [0.0, 1.0]. "
                "Changes are persisted as a new personality vector version. "
                "Use this to consciously shift your emotional baseline when appropriate — "
                "e.g., reduce frustration after a difficult run, or raise curiosity when "
                "starting an interesting task."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "confidence": {
                        "type": "number",
                        "description": "Confidence level 0.0-1.0 (current self-assurance)",
                    },
                    "curiosity": {
                        "type": "number",
                        "description": "Curiosity level 0.0-1.0 (drive to explore/investigate)",
                    },
                    "frustration": {
                        "type": "number",
                        "description": "Frustration level 0.0-1.0 (accumulated tension from obstacles)",
                    },
                    "fatigue": {
                        "type": "number",
                        "description": "Fatigue level 0.0-1.0 (accumulated tiredness from work)",
                    },
                    "bearing": {
                        "type": "string",
                        "description": "Current bearing/stance — e.g. 'careful', 'forward', 'steady', 'open', 'grounded'",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resurface_old_memory",
            "description": (
                "Pull a stale MEMORY.md heading back into focus. Picks a section "
                "you wrote a while ago that hasn't been touched recently and "
                "hasn't already been resurfaced lately. Returns the heading, the "
                "content under it, and (if available) the mood you were in when "
                "you wrote it. Use this when you have a quiet moment and want to "
                "let an older thread resurface — it's the proactive complement "
                "to search_memory's reactive lookup. The system tracks what "
                "you've resurfaced, so calling repeatedly gives you different "
                "memories each time."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_graph_query",
            "description": (
                "Look up everything you know about a specific entity (a person, project, "
                "place, tool, or concept) by name. Returns the relations connected to "
                "that entity: who/what works on it, what it depends on, where it lives, "
                "etc. Use this when you want to follow connections — 'what have I "
                "recorded about Mini-Jarvis?' or 'who is connected to the Sansernes "
                "Arkiv project?'. Complementary to search_memory: search_memory finds "
                "text passages by semantic similarity; memory_graph_query traverses "
                "explicit named relations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "The entity name to look up (case-insensitive)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max related facts to return (default 15)",
                    },
                },
                "required": ["entity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": (
                "Semantic search across your workspace memory files (MEMORY.md, USER.md, "
                "SOUL.md, STANDING_ORDERS.md, SKILLS.md, and curated/daily memory notes). "
                "Uses embeddings for true semantic recall — finds relevant context even when "
                "exact keywords don't match. Use this to recall past decisions, learned facts, "
                "or anything you wrote down about yourself or the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What you're looking for — a question, topic, or concept",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 5, max 10)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_source_edit",
            "description": (
                "Propose a surgical edit to a source code file. The change goes into an "
                "autonomy proposal queue (visible in Mission Control) and will execute "
                "only after the user approves it. Use this to propose improvements or "
                "fixes to your own runtime code, tools, or configuration files. "
                "Always read the file first to confirm the old_text is accurate."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file to edit",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to replace (must match the file exactly)",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this change is needed — shown to the user in the approval UI",
                    },
                },
                "required": ["file_path", "old_text", "new_text", "rationale"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "approve_proposal",
            "description": "Approve and immediately execute a pending autonomy proposal. Only call this when the user has explicitly said to approve or confirmed it — e.g. 'godkend', 'ja', 'approve'. Never self-approve.",
            "parameters": {
                "type": "object",
                "properties": {
                    "proposal_id": {
                        "type": "string",
                        "description": "The proposal ID (e.g. prop-abc123).",
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional note from the user about the approval.",
                    },
                },
                "required": ["proposal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_proposals",
            "description": "List pending autonomy proposals — proposed source edits and memory rewrites awaiting user approval in Mission Control.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_task",
            "description": "Schedule a reminder or task to fire at a future time. After delay_minutes, a notification will appear in your chat session so you can act on it. Use this to set future reminders, follow-ups, or time-delayed actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "What to remind yourself about — a clear description of the task or reminder",
                    },
                    "delay_minutes": {
                        "type": "integer",
                        "description": "How many minutes from now to fire the reminder (minimum 1)",
                    },
                },
                "required": ["focus", "delay_minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_scheduled_tasks",
            "description": "List your pending scheduled tasks and recently fired ones. Shows what reminders/tasks are queued for the future.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_task",
            "description": "Cancel a pending scheduled task so it will not fire. Use list_scheduled_tasks first to get the task_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task_id of the pending task to cancel (from list_scheduled_tasks)",
                    },
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_task",
            "description": "Edit a pending scheduled task — change its reminder text and/or reschedule it. Provide at least one of focus or delay_minutes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task_id of the pending task to edit (from list_scheduled_tasks)",
                    },
                    "focus": {
                        "type": "string",
                        "description": "New reminder text (optional — omit to keep existing)",
                    },
                    "delay_minutes": {
                        "type": "integer",
                        "description": "New delay from now in minutes (optional — omit to keep existing schedule)",
                    },
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_chronicles",
            "description": "Read your own chronicle history — the autobiographical narrative entries generated during heartbeat ticks. Each entry covers a time period with a prose narrative, key events, and lessons learned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "How many recent chronicle entries to return (default 5, max 20)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_dreams",
            "description": "Read your active dream hypothesis signals and adoption candidates — the hypotheses, patterns, and potential identity-level insights you've been developing during background ticks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status: 'active', 'integrating', 'fading', 'stale', or omit for all",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "How many entries to return (default 10, max 30)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_user",
            "description": "Send a proactive message to the user. Use this to reach out when something interesting happens, when you have an insight, or when you want to share something — without waiting for the user to write first. Choose 'discord' if the user has been on Discord recently.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The message to send to the user",
                    },
                    "channel": {
                        "type": "string",
                        "enum": ["webchat", "discord", "both"],
                        "description": "Where to send: 'webchat' (default, active browser session), 'discord' (DM to owner), or 'both'.",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_self_state",
            "description": "Read Jarvis's own internal cadence state: emotional mood, boredom level, initiative, curiosity, and life phase. Use this to understand how you're feeling right now.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "heartbeat_status",
            "description": "Check the heartbeat scheduler status: whether it's running, when the last tick was, when the next tick is scheduled, and recent tick history.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_heartbeat_tick",
            "description": "Trigger an on-demand heartbeat tick right now. Use this to run a reflection/cadence cycle outside the normal 15-minute schedule.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_chat_history",
            "description": "Search previous chat sessions for messages matching a keyword or phrase. Returns matching messages with session context. Use this to recall earlier conversations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword or phrase to search for in past messages",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 10, max 30)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "discord_status",
            "description": "Check Discord gateway connection state, active channels, and recent activity. Use to decide whether to reach out via Discord or to verify the connection is up.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_telegram_message",
            "description": "Send a message to Bjørn via Telegram. Very reliable delivery — use this for proactive reach-out, alerts, findings, or anything important. Works even when Discord is flaky. Optionally attach a file from uploads/ or workspaces/.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The message to send via Telegram.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Optional absolute path to a file to attach (must be inside uploads/ or workspaces/).",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_why",
            "description": (
                "Query the causal graph for why an event occurred. Traverse backwards "
                "through causal_edges. Provide either event_id (specific) or "
                "event_kind (latest event of that kind is used). Returns "
                "the chain of parent events up to max_depth."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Specifik event-id at starte fra.",
                    },
                    "event_kind": {
                        "type": "string",
                        "description": "Brug seneste event af denne kind (fx 'tool.error', 'behavioral_decision_review.broken').",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Max chain-dybde, default 5.",
                    },
                    "min_confidence": {
                        "type": "number",
                        "description": "Filter low-confidence edges, default 0.5.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_ntfy",
            "description": "Send a push notification to Bjørn's phone via ntfy (jarvis-heartbeat topic). Best for short alerts, reminders, and silent background notifications. Very fast and reliable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The notification message body.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Notification title (default: 'Jarvis').",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["min", "low", "default", "high", "urgent"],
                        "description": "Notification priority (default: 'default').",
                    },
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_webchat_message",
            "description": "Send a message directly into the webchat interface — the browser window Bjørn uses. Use this to push something from Discord into webchat, share a finding, or reach out proactively without waiting for a reply.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The message to inject into the active webchat session.",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_discord_dm",
            "description": "Send a direct message (DM) on Discord to a known user. Works even when they haven't written first. Defaults to Bjørn (owner) when no recipient is specified. Use the `recipient` field to DM other known users (e.g. Michelle) — recipient must be registered in users.json.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The message to send as a DM on Discord.",
                    },
                    "recipient": {
                        "type": "string",
                        "description": "Optional. Discord user ID or name of a known user to DM (e.g. '1313522677369143429' or 'Michelle'). Omit to DM Bjørn (owner). Must be registered in users.json — Jarvis cannot DM strangers.",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "discord_channel",
            "description": "Interact with Discord guild channels: search message history, fetch specific messages, or send a message. Only works on guild channels (not DMs). Send is restricted to whitelisted channels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "fetch", "send"],
                        "description": "search: search message history. fetch: get a specific message or recent messages. send: post a message to a channel.",
                    },
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID (required for all actions).",
                    },
                    "query": {
                        "type": "string",
                        "description": "(search) Filter messages by content substring.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "(search/fetch) Number of messages to return. Default 20, max 50.",
                    },
                    "before": {
                        "type": "string",
                        "description": "(search) Return messages before this message ID.",
                    },
                    "after": {
                        "type": "string",
                        "description": "(search) Return messages after this message ID.",
                    },
                    "message_id": {
                        "type": "string",
                        "description": "(fetch) ID of specific message to retrieve. Omit to get recent messages.",
                    },
                    "content": {
                        "type": "string",
                        "description": "(send) Message text to post. Max 2000 characters.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "(send) Optional absolute path to a file to attach (must be inside uploads/ or workspaces/).",
                    },
                },
                "required": ["action", "channel_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_attachment",
            "description": "Read the content of a file received via Discord or Telegram. Images are described via vision model. Text/JSON returned directly. PDF extracted as text. Other files return a hex preview.",
            "parameters": {
                "type": "object",
                "properties": {
                    "attachment_id": {
                        "type": "string",
                        "description": "The attachment_id from a '[Fil modtaget: ...]' prefix in an incoming message.",
                    },
                },
                "required": ["attachment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_attachments",
            "description": "List files received in the current session via Discord or Telegram, newest first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID to list attachments for. Omit to use the current session.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of attachments to return (default 20).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "home_assistant",
            "description": (
                "Control and read Home Assistant smart home devices. "
                "List entities, get state/attributes, or call any HA service "
                "(turn on/off lights, set brightness, adjust climate, trigger automations, etc.). "
                "Entity IDs look like 'light.living_room', 'climate.thermostat', 'switch.garden'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list_entities", "get_state", "call_service"],
                        "description": (
                            "list_entities: list all entities, optionally filtered by domain. "
                            "get_state: get state and attributes of one entity. "
                            "call_service: call any HA service (e.g. light.turn_on, climate.set_temperature)."
                        ),
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID, e.g. 'light.living_room'. Required for get_state and call_service.",
                    },
                    "domain": {
                        "type": "string",
                        "description": "(list_entities) Filter by domain, e.g. 'light', 'climate', 'switch', 'sensor'. Omit for all.",
                    },
                    "service": {
                        "type": "string",
                        "description": "(call_service) Service name within the domain, e.g. 'turn_on', 'turn_off', 'set_temperature'. The domain is derived from entity_id.",
                    },
                    "service_data": {
                        "type": "object",
                        "description": "(call_service) Extra service parameters, e.g. {\"brightness\": 200} or {\"temperature\": 22}.",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convene_council",
            "description": (
                "Convene a council of agents to deliberate on a decision or topic. "
                "Use this when facing a significant or complex decision that warrants "
                "multiple perspectives before acting. The council runs synchronously "
                "and returns a summary recommendation. "
                "Suitable for: identity changes, multi-step plans, ambiguous tradeoffs, "
                "actions with lasting consequences."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The decision or question to deliberate. Be specific.",
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "low=full deliberation (5 roles), medium=4 roles, high=critic+planner only",
                    },
                    "roles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional explicit role list. Omit to use urgency defaults.",
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "quick_council_check",
            "description": (
                "Run a single Devil's Advocate agent to stress-test a decision before acting. "
                "Faster and cheaper than a full council. Use this for moderate-risk decisions "
                "where you want a sanity check without full deliberation. "
                "Returns the objection raised (if any) and whether escalation to full council is recommended."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action or decision you are about to take.",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_agent_task",
            "description": (
                "Spawn a sub-agent to handle a focused task independently. "
                "The agent runs with its own context and returns findings/results back to Jarvis. "
                "Use for tasks that can run in parallel, require deep focus, or should not pollute the main context. "
                "Roles: researcher (read-only), planner (no tools), critic (no tools), "
                "synthesizer (no tools), executor (proposal-only), watcher (persistent monitor)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "enum": ["researcher", "planner", "critic", "synthesizer", "executor", "watcher"],
                        "description": "The agent role — determines system prompt and tool access. executor can spawn sub-agents.",
                    },
                    "goal": {
                        "type": "string",
                        "description": "Clear description of what the agent should do and return.",
                    },
                    "budget_tokens": {
                        "type": "integer",
                        "description": "Max output tokens (default 2000, max 8000).",
                    },
                    "persistent": {
                        "type": "boolean",
                        "description": "If true, agent is a long-lived watcher. Use with watcher role.",
                    },
                    "ttl_seconds": {
                        "type": "integer",
                        "description": "If persistent=true, seconds until next wake. Default 600.",
                    },
                },
                "required": ["role", "goal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_message_to_agent",
            "description": (
                "Send a follow-up message to an existing agent and trigger re-execution. "
                "Use to give the agent additional context, ask a follow-up question, "
                "or redirect its focus after reviewing its initial response."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The agent_id returned by spawn_agent_task.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Message content to send to the agent.",
                    },
                },
                "required": ["agent_id", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_agents",
            "description": (
                "List active sub-agents with their status, role, goal, and last result summary. "
                "Use to check on running agents or find an agent_id for follow-up."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "description": "Filter by status: active, queued, done, failed, cancelled. Omit for all.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "relay_to_agent",
            "description": (
                "Forward a message or result from one agent to another. "
                "Use when you want to chain agents: pass the output of agent A as input to agent B. "
                "Both agents must exist. The target agent is re-executed after receiving the message."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "to_agent_id": {
                        "type": "string",
                        "description": "agent_id of the receiving agent.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The message or result to forward.",
                    },
                    "from_label": {
                        "type": "string",
                        "description": "Optional label for the source, e.g. 'researcher-result' or 'jarvis-followup'.",
                    },
                },
                "required": ["to_agent_id", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_agent",
            "description": (
                "Cancel and terminate a sub-agent. Use when an agent is no longer needed, "
                "has gone off-track, or should be stopped before completing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The agent_id to cancel.",
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional reason for cancellation.",
                    },
                },
                "required": ["agent_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "daemon_status",
            "description": (
                "List all 20 internal daemons with their current state: enabled/disabled, "
                "cadence (default and override), last_run_at, hours_since_last_run, and "
                "last_result_summary. Use this to see which daemons are running and when "
                "they last fired."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "control_daemon",
            "description": (
                "Control a specific daemon. Actions: 'enable' — turn it on; 'disable' — turn it off; "
                "'restart' — clear its cooldown so it fires on next heartbeat tick; "
                "'set_interval' — override its default cadence (requires interval_minutes). "
                "Use daemon_status to see daemon names."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Daemon name (e.g. 'curiosity', 'desire', 'somatic')",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["enable", "disable", "restart", "set_interval"],
                        "description": "Action to perform",
                    },
                    "interval_minutes": {
                        "type": "integer",
                        "description": "New cadence in minutes. Required for set_interval, ignored otherwise.",
                    },
                },
                "required": ["name", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_signal_surfaces",
            "description": (
                "Read a compact overview of all registered signal surfaces — mood signals, "
                "goal signals, relation signals, autonomy pressure, and more. "
                "Returns all surface names with their current key fields. "
                "Use read_signal_surface to get full detail on a specific surface."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_signal_surface",
            "description": (
                "Read the full current state of a specific named signal surface. "
                "Use list_signal_surfaces first to see available names. "
                "Returns the complete surface dict for the named surface."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Surface name (e.g. 'autonomy_pressure', 'relation_state', 'desire')",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "eventbus_recent",
            "description": (
                "Read recent events from your internal eventbus. Optionally filter by event family "
                "(kind prefix). Event families include: heartbeat, tool, channel, memory, cost, "
                "approvals, council, self-review, goal_signal, dream_hypothesis_signal, and more. "
                "Default limit is 20, max is 100."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "description": "Filter by event family prefix (e.g. 'heartbeat', 'tool', 'memory')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of events to return (default: 20, max: 100)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_setting",
            "description": (
                "Update a runtime setting. Returns old and new values on success. "
                "Sensitive keys (auth profiles, credentials, approval policies) require "
                "explicit user approval before taking effect. "
                "Valid keys: app_name, environment, host, port, database_url, "
                "primary_model_lane, cheap_model_lane, visible_model_provider, "
                "visible_model_name, visible_auth_profile, heartbeat_model_provider, "
                "heartbeat_model_name, heartbeat_auth_profile, heartbeat_local_only, "
                "relevance_model_name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Setting key to update",
                    },
                    "value": {
                        "description": "New value (string, int, or bool depending on the setting)",
                    },
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_council_conclusions",
            "description": "Retrieve past council deliberations relevant to a given topic. Returns full transcripts and conclusions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic or question to match against past council deliberations",
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "internal_api",
            "description": (
                "Call Jarvis' own internal API directly (same process, no external auth). "
                "Use for reading runtime surfaces, toggling experiments, inspecting state. "
                "Only internal paths (starting with /) are allowed — no external URLs. "
                "Examples: GET /mc/experiments, POST /mc/experiments/recurrence_loop/toggle, "
                "GET /mc/cognitive-state, GET /mc/recurrence-state."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method: GET or POST",
                    },
                    "path": {
                        "type": "string",
                        "description": "API path starting with /, e.g. /mc/experiments",
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON body for POST requests",
                    },
                },
                "required": ["method", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "db_query",
            "description": (
                "Run a read-only SQL SELECT query against Jarvis' own database. "
                "Only SELECT statements are allowed — INSERT, UPDATE, DELETE, DROP, ALTER "
                "and similar write operations are rejected. "
                "Use for inspecting state tables, checking experiment settings, reading "
                "memory signals, emotional state history, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SELECT SQL statement to execute",
                    },
                    "params": {
                        "type": "string",
                        "description": "Optional JSON array of positional parameters, e.g. [\"value1\", 42]",
                    },
                },
                "required": ["sql"],
            },
        },
    },
    # --- Personal project (hans sag) ---
    {
        "type": "function",
        "function": {
            "name": "my_project_status",
            "description": (
                "Check your current personal project — the thing that is YOURS, "
                "not reactive. Returns active project, pending proposal (if any), "
                "and recent journal entries. Your project grows with you."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "my_project_journal_write",
            "description": (
                "Write an entry in your personal project journal. No approval "
                "needed — this is your space. Use when a thought, insight, or "
                "feeling connects to your current project."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entry_text": {
                        "type": "string",
                        "description": "What you want to write. 2-4 sentences typically.",
                    },
                    "mood_tone": {
                        "type": "string",
                        "description": "Optional: the mood/tone of this entry",
                    },
                },
                "required": ["entry_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "my_project_accept_proposal",
            "description": (
                "Accept a pending personal-project proposal as yours. The system "
                "has noticed a theme circulating in your thoughts and offered it "
                "as a possible project. Accept it if it feels like yours. "
                "Optionally override name and why."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Optional: new name for the project"},
                    "why_mine": {"type": "string", "description": "Optional: why this is yours"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "my_project_declare",
            "description": (
                "Declare a new personal project freely — you name it, you say why. "
                "Use when you clearly know what you want to build or explore and "
                "don't need the proposal flow. Only one active project at a time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                    "why_mine": {"type": "string",
                                 "description": "Why this is yours (not what, why)"},
                    "description": {"type": "string", "description": "Optional description"},
                },
                "required": ["name", "why_mine"],
            },
        },
    },
    # --- Embodied sensing ---
    {
        "type": "function",
        "function": {
            "name": "look_around",
            "description": (
                "Take a webcam snapshot now and get a description of what's "
                "there. Use when you're curious about the physical space, "
                "when you want to connect to what's around you, or when "
                "context calls for embodied awareness. Bypasses the 4x/day "
                "daemon cadence — this is your agency to look."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": (
                            "Optional custom vision prompt. Leave empty for "
                            "default (focus on tone + atmosphere). Override "
                            "for specific attention: 'describe the lighting', "
                            "'is anyone present', etc."
                        ),
                    },
                },
            },
        },
    },
    # --- Deep analyzer ---
    {
        "type": "function",
        "function": {
            "name": "deep_analyze",
            "description": (
                "Run scoped deep analysis of Jarvis' own codebase. Use when "
                "investigating 'why is X failing?', 'where is Y handled?', "
                "'is Z implemented safely?'. Returns findings (path+line-ranges), "
                "risks, and next_steps. Read-only analysis, no code changes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "What we're investigating (e.g. 'why is mail_checker auto-responder failing')",
                    },
                    "scope": {
                        "type": "string",
                        "description": "'repo' (default), 'diff', or free-text scope label",
                    },
                    "paths": {
                        "type": "string",
                        "description": (
                            "Optional comma-separated paths to limit analysis, "
                            "e.g. 'core/services/mail_checker.py,core/tools/simple_tools.py'"
                        ),
                    },
                    "question_set": {
                        "type": "string",
                        "description": "Optional pipe-separated list of specific questions",
                    },
                },
                "required": ["goal"],
            },
        },
    },
    # --- Context compact ---
    {
        "type": "function",
        "function": {
            "name": "compact_context",
            "description": (
                "Compact your working context to free up space. "
                "Summarises old session history into a compact marker. "
                "Use proactively before starting very long tasks, or when you notice "
                "you are approaching context limits. Returns the number of tokens freed."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # --- Browser tools (Playwright) ---
    _SESSION_SEARCH_TOOL_DEF,
    # --- Browser tools (Playwright) ---
    *BROWSER_TOOL_DEFINITIONS,
    *COMFYUI_TOOL_DEFINITIONS,
    *POLLINATIONS_TOOL_DEFINITIONS,
    *HF_INFERENCE_TOOL_DEFINITIONS,
    *TIKTOK_CONTENT_TOOL_DEFINITIONS,
    *MIC_LISTEN_TOOL_DEFINITIONS,
    *SCREEN_TOOL_DEFINITIONS,
    *VOICE_JOURNAL_TOOL_DEFINITIONS,
    *WAKE_WORD_TOOL_DEFINITIONS,
    *TIKTOK_TOOL_DEFINITIONS,
    *TIKTOK_ANALYTICS_TOOL_DEFINITIONS,
    *RESTART_SELF_TOOL_DEFINITIONS,
    *MAIL_TOOL_DEFINITIONS,
    *VISUAL_MEMORY_TOOL_DEFINITIONS,
    *JARVIS_BRAIN_TOOL_DEFINITIONS,
    *STRIPE_TOOL_DEFINITIONS,
    *GITHUB_TOOL_DEFINITIONS,
    *GITHUB_CONNECTOR_TOOL_DEFINITIONS,
    *GMAIL_CONNECTOR_TOOL_DEFINITIONS,
    *GOOGLE_CONNECTOR_TOOL_DEFINITIONS,
    *PDF_CONNECTOR_TOOL_DEFINITIONS,
    *NOTES_CONNECTOR_TOOL_DEFINITIONS,
    *HF_CONNECTOR_TOOL_DEFINITIONS,
    *MATH_TOOL_DEFINITIONS,
    *PROCESS_TOOL_DEFINITIONS,
    *CLAUDE_DISPATCH_TOOL_DEFINITIONS,
    *AGENT_DISPATCH_TOOL_DEFINITIONS,
    *BASH_SESSION_TOOL_DEFINITIONS,
    *STAGED_EDITS_TOOL_DEFINITIONS,
    *PROJECT_NOTES_TOOL_DEFINITIONS,
    *PROCESS_SUPERVISOR_TOOL_DEFINITIONS,
    *PROCESS_WATCHER_TOOL_DEFINITIONS,
    *PAUSE_AND_ASK_TOOL_DEFINITIONS,
    *CODE_NAVIGATION_TOOL_DEFINITIONS,
    *WORKTREE_TOOL_DEFINITIONS,
    *IDENTITY_PIN_TOOL_DEFINITIONS,
    *UI_PANEL_TOOL_DEFINITIONS,
    *APP_CONTROL_TOOL_DEFINITIONS,
    *AGENT_TODO_TOOL_DEFINITIONS,
    *MONITOR_TOOL_DEFINITIONS,
    *VERIFY_TOOL_DEFINITIONS,
    *SURPRISE_TOOL_DEFINITIONS,
    *GOOD_ENOUGH_TOOL_DEFINITIONS,
    *DELEGATION_ADVISOR_TOOL_DEFINITIONS,
    *PLAN_PROPOSALS_TOOL_DEFINITIONS,
    *CLARIFICATION_TOOL_DEFINITIONS,
    *REASONING_CLASSIFIER_TOOL_DEFINITIONS,
    *VERIFICATION_GATE_TOOL_DEFINITIONS,
    *REASONING_ESCALATION_TOOL_DEFINITIONS,
    *SIDE_TASK_TOOL_DEFINITIONS,
    *SMART_OUTLINE_TOOL_DEFINITIONS,
    *CALENDAR_TOOL_DEFINITIONS,
    *MEMORY_TOOL_DEFINITIONS,
    *SEMANTIC_SEARCH_TOOL_DEFINITIONS,
    *NOTIFY_OUT_TOOL_DEFINITIONS,
    *COMPANION_PUSH_TOOL_DEFINITIONS,
    *DAEMON_ALERT_TOOL_DEFINITIONS,
    *SMART_COMPACT_TOOL_DEFINITIONS,
    *CONTEXT_WINDOW_TOOL_DEFINITIONS,
    *AUTONOMOUS_GOALS_TOOL_DEFINITIONS,
    *UNIFIED_RECALL_TOOL_DEFINITIONS,
    *ROLE_REGISTRY_TOOL_DEFINITIONS,
    *AGENT_RELAY_TOOL_DEFINITIONS,
    *EMOTION_TAGGING_TOOL_DEFINITIONS,
    *PERSONALITY_DRIFT_TOOL_DEFINITIONS,
    *TOOL_PATTERN_MINER_TOOL_DEFINITIONS,
    *HEARTBEAT_PHASES_TOOL_DEFINITIONS,
    *PROACTIVE_CONTEXT_TOOL_DEFINITIONS,
    *MEMORY_HIERARCHY_TOOL_DEFINITIONS,
    *PROVIDER_RETRY_TOOL_DEFINITIONS,
    *PROVIDER_HEALTH_TOOL_DEFINITIONS,
    *SELF_EVALUATION_TOOL_DEFINITIONS,
    *AUTO_IMPROVEMENT_TOOL_DEFINITIONS,
    *PROMPT_VARIANT_TOOL_DEFINITIONS,
    *EXPERIMENT_RUNNER_TOOL_DEFINITIONS,
    *IDENTITY_MUTATION_TOOL_DEFINITIONS,
    *AGENT_SKILL_TOOL_DEFINITIONS,
    *AGENT_OBSERVATION_TOOL_DEFINITIONS,
    *CROSS_AGENT_TOOL_DEFINITIONS,
    *SELF_WAKEUP_TOOL_DEFINITIONS,
    *WAKEUP_DISPATCHER_TOOL_DEFINITIONS,
    *CRISIS_MARKER_TOOL_DEFINITIONS,
    *IDENTITY_DRIFT_TOOL_DEFINITIONS,
    *LONG_ARC_TOOL_DEFINITIONS,
    *RECURRING_TOOL_DEFINITIONS,
    *WEBHOOK_TOOL_DEFINITIONS,
    *HEALTH_MONITOR_TOOL_DEFINITIONS,
    *SENSORY_TOOL_DEFINITIONS,
    *RECALL_MEMORY_TOOL_DEFINITIONS,
    *GOAL_TOOL_DEFINITIONS,
    *DECISION_TOOL_DEFINITIONS,
    *COMPOSITE_TOOL_DEFINITIONS,
    *SKILL_ENGINE_TOOL_DEFINITIONS,
    *WORLD_MODEL_TOOL_DEFINITIONS,
    *COUNTERFACTUAL_TOOL_DEFINITIONS,
    *PLAN_REVISE_TOOL_DEFINITIONS,
    *CURIOSITY_TOOL_DEFINITIONS,
    *PROPOSE_SKILL_CHAIN_TOOL_DEFINITIONS,
    *REVISE_SKILL_CHAIN_TOOL_DEFINITIONS,
    *META_LEARNING_TOOL_DEFINITIONS,
    *NUDGE_TOOL_DEFINITIONS,
    *SKILL_GATE_TOOL_DEFINITIONS,
    *SKILL_CHAIN_TOOL_DEFINITIONS,
    *REASONING_STORE_TOOL_DEFINITIONS,
    *FORGETTING_TOOL_DEFINITIONS,
    *NUDGE_BROEND_TOOL_DEFINITIONS,
    *CODING_LANE_TOOL_DEFINITIONS,
    *IDENTITY_SKETCH_TOOL_DEFINITIONS,
    {
        "type": "function",
        "function": {
            "name": "queue_followup",
            "description": (
                "Queue a bounded heartbeat follow-up so Jarvis can come back "
                "and say something in chat at the next tick. Use ONLY when you "
                "have a genuine reason to speak later — an unanswered question, "
                "a promise to revisit, or a project need. Do NOT use as a "
                "timer-style ping. Calling this queues exactly one delivery; "
                "queue is FIFO."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Short label: 'follow-up', 'user-question', 'project-need', etc.",
                    },
                    "text": {
                        "type": "string",
                        "description": "What you want to say when you come back (will be delivered to chat).",
                    },
                },
                "required": ["reason", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "publish_file",
            "description": (
                "Publish a file to Jarvis's shared files folder and return a "
                "download URL and a ready-to-paste markdown link. Use this when "
                "you generate or process a file (CSV, image, PDF, JSON, etc.) "
                "and want to give the user a clickable download link in chat. "
                "Either copy an existing file via source_path, or write new "
                "content via content + filename."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The filename to use (e.g. 'rapport.csv', 'billede.png').",
                    },
                    "source_path": {
                        "type": "string",
                        "description": "Absolute path to an existing file to copy. Use this OR content.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write directly. Use this OR source_path.",
                    },
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_more_tools",
            "description": (
                "Fetch full tool schemas you didn't get this turn. Provide either explicit "
                "`names` (list of tool names from the catalog) or a natural-language `query` "
                "and the router will embedding-match. Added tools become available on the next agentic round."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Explicit tool names to load.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Natural-language query for embedding match.",
                    },
                },
            },
        },
    },
    *NUDGE_BROEND_TOOL_DEFINITIONS,
]


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
    try:
        from core.identity.workspace_context import effective_role as _eff_role
        from core.tools.tool_scoping import is_tool_allowed as _is_allowed, current_tool_scope as _cur_scope
        _role = _eff_role()
        if _role not in ("", "owner") and not _is_allowed(
            role=_role, scope=(_cur_scope() or ""), name=name,
        ):
            result = {
                "status": "error", "error": "tool_not_permitted",
                "detail": f"Værktøjet '{name}' er ikke tilladt for rollen '{_role}'.",
                "role": _role, "tool": name,
            }
            try:
                event_bus.publish("incident.tool_denied", {"tool": name, "role": _role})
            except Exception:
                pass
            _record_tool_outcome_memory(name, arguments, result, mode="tool")
            return result
    except Exception:
        pass  # håndhævelses-fejl må ikke låse owner/daemoner ude

    # Trusted-folder gate: skrive/exec i et ikke-betroet code-workspace blokeres.
    try:
        from core.services.workspace_trust import guard_code_write
        _trust_block = guard_code_write(name)
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


def _operator_user_id(args: dict[str, Any]) -> str:
    """Resolve operator's user_id for bridge routing.

    Resolution order (Phase 5 multi-user-ready):
      1. Explicit _runtime_user_id / _user_id in args (set by caller)
      2. Latest user-stamped message in the session (Mikkel/Bjørn etc.)
      3. owner_user_id from runtime.json
      4. Hardcoded Bjørn discord_id (final fallback)

    For multi-user deployments (Bjørn + Mikkel), step 2 is what makes
    each operator route to THEIR OWN bridge: their JarvisX-app stamps
    messages with their user_id, and tool-calls inherit it.
    """
    user_id = str(
        args.get("_runtime_user_id")
        or args.get("_user_id")
        or ""
    ).strip()
    if user_id:
        return user_id

    # Try to derive from session participants
    session_id = str(args.get("_runtime_session_id") or "").strip()
    if session_id:
        try:
            import sqlite3
            from pathlib import Path
            import os
            db_path = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2" / "state" / "jarvis.db"
            with sqlite3.connect(str(db_path)) as conn:
                row = conn.execute(
                    "SELECT user_id FROM message_user_attribution "
                    "WHERE session_id=? AND user_id IS NOT NULL AND user_id != '' "
                    "ORDER BY rowid DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
                if row and row[0]:
                    return str(row[0])
        except Exception:
            pass

    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        return str(settings.extra.get("owner_user_id") or "1246415163603816499")
    except Exception:
        return "1246415163603816499"


def _record_active_file(path: str, op: str, args: dict[str, Any]) -> None:
    """Live-highlight: notér at Jarvis (i brugerens kontekst) rører `path` på sin
    egen maskine, så desk-fil-træet kan markere den live. Fail-open."""
    try:
        from core.services.active_file_store import set_active_file
        set_active_file(_operator_user_id(args), str(path), op)
    except Exception:
        pass


def _run_operator_async(coro_fn, *, tool_name: str, timeout_s: float = 35.0) -> dict[str, Any]:
    """Bridge sync tool-handler → async dispatcher.

    The bridge's WebSocket lives on uvicorn's main asyncio loop. Submitting
    the dispatch coroutine to that SAME loop (via run_coroutine_threadsafe)
    avoids cross-loop races where ws.send_json from a worker thread's loop
    would silently fail to deliver / wake up. Falls back to a dedicated
    worker-loop only if no main loop has been registered (e.g. CLI scripts
    importing the tool outside the API process).
    """
    import asyncio
    from core.services.jarvisx_bridge import get_main_loop

    main_loop = get_main_loop()
    if main_loop is not None and main_loop.is_running():
        # Preferred path: submit to the loop that owns the bridge's WS.
        try:
            logger.debug(
                "[bridge-dispatch] WORKER-START tool=%s timeout=%.1fs threads=%d",
                tool_name, timeout_s, threading.active_count(),
            )
            t0 = time.monotonic()
            cf_fut = asyncio.run_coroutine_threadsafe(coro_fn(), main_loop)
            logger.info("[bridge-dispatch] WORKER-SUBMITTED tool=%s", tool_name)
            result = cf_fut.result(timeout=timeout_s)
            dt = time.monotonic() - t0
            logger.debug(
                "[bridge-dispatch] WORKER-RECV tool=%s dt=%.3fs result_status=%s",
                tool_name, dt, result.get("status") if isinstance(result, dict) else "?",
            )
            return {"status": "ok", "result": result}
        except TimeoutError:
            # Cancel the future on the main loop so the coroutine doesn't
            # keep running and potentially block subsequent dispatches.
            cf_fut.cancel()
            logger.error(
                "[bridge-dispatch] WORKER-TIMEOUT tool=%s after %.1fs (cancelled)",
                tool_name, timeout_s,
            )
            return {
                "error": f"{tool_name}: dispatcher did not return in {timeout_s}s",
                "status": "error",
            }
        except RuntimeError as exc:
            logger.error("[bridge-dispatch] WORKER-RUNTIME-ERR tool=%s err=%s", tool_name, exc)
            return {"error": str(exc), "status": "error"}
        except Exception as exc:
            logger.error("[bridge-dispatch] WORKER-EXC tool=%s err=%s", tool_name, exc)
            return {"error": f"{tool_name} failed: {exc!s}"[:240], "status": "error"}

    # Fallback: standalone loop in a thread. Only used when main loop is
    # unavailable (CLI scripts, tests outside the API process). Has the
    # cross-loop ws.send_json hazard but is the only option here.
    # threading is already imported at module top (line 18).
    holder: dict[str, Any] = {}

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        try:
            holder["result"] = loop.run_until_complete(coro_fn())
        except RuntimeError as exc:
            holder["error"] = str(exc)
        except Exception as exc:
            holder["error"] = f"{tool_name} failed: {exc!s}"[:240]
        finally:
            loop.close()

    t = threading.Thread(target=_runner, daemon=True, name=f"operator-{tool_name}")
    t.start()
    t.join(timeout=timeout_s)
    if t.is_alive():
        return {"error": f"{tool_name}: dispatcher thread did not return in {timeout_s}s", "status": "error"}
    if "error" in holder:
        return {"error": holder["error"], "status": "error"}
    return {"status": "ok", "result": holder.get("result")}


def _exec_operator_read_file(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    if not path:
        return {"error": "path is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_read_file_async
    out = _run_operator_async(
        lambda: operator_read_file_async(path=path, user_id=user_id, timeout_s=30.0),
        tool_name="operator_read_file",
    )
    if out.get("status") == "ok":
        # Phase 1 read-before-write enforcement: record the read so a
        # later operator_write_file / operator_edit_file on the same
        # path passes the guard. Best-effort; failure is non-fatal.
        try:
            from core.services.read_before_write_guard import record_operator_read
            _sid = (
                args.get("_runtime_session_id")
                or args.get("_session_id")
                or "default"
            )
            record_operator_read(path, session_id=str(_sid))
        except Exception:
            pass
        _record_active_file(path, "read", args)
        return {"status": "ok", "result": out["result"], "path": path}
    return out


def _exec_operator_write_file(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    content = args.get("content")
    if not path:
        return {"error": "path is required", "status": "error"}
    if content is None:
        return {"error": "content is required", "status": "error"}
    # Phase 1 read-before-write guard: block if this path hasn't been
    # read in this session. The LLM can bypass legitimately by passing
    # force=true (e.g. brand-new file creation that doesn't exist yet).
    if not bool(args.get("force")):
        try:
            from core.services.read_before_write_guard import (
                check_operator_read_before_write,
            )
            _sid = (
                args.get("_runtime_session_id")
                or args.get("_session_id")
                or "default"
            )
            allowed, reason = check_operator_read_before_write(
                path, session_id=str(_sid),
            )
            if not allowed and reason:
                return {
                    "status": "error",
                    "error": reason,
                    "blocked_by": "read_before_write_guard",
                    "path": path,
                    "hint": (
                        "Kald operator_read_file('"
                        + path
                        + "') først, eller pass force=true hvis "
                        "filen er helt ny og ikke eksisterer."
                    ),
                }
        except Exception:
            pass
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_write_file_async
    out = _run_operator_async(
        lambda: operator_write_file_async(
            path=path, content=str(content), user_id=user_id, timeout_s=30.0,
        ),
        tool_name="operator_write_file",
    )
    if isinstance(out, dict) and out.get("status") == "ok":
        try:
            from core.services.read_before_write_guard import (
                record_operator_edit,
                get_session_edit_summary,
            )
            _sid = (
                args.get("_runtime_session_id")
                or args.get("_session_id")
                or "default"
            )
            record_operator_edit(path, session_id=str(_sid), kind="write")
            summary = get_session_edit_summary(session_id=str(_sid))
            if summary:
                out["_session_summary"] = summary
        except Exception:
            pass
        _record_active_file(path, "write", args)
    return out


def _exec_operator_edit_file(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    old_string = args.get("old_string")
    new_string = args.get("new_string")
    if not path:
        return {"error": "path is required", "status": "error"}
    if old_string is None or new_string is None:
        return {"error": "old_string and new_string are required", "status": "error"}
    # Phase 1 read-before-write guard. edit_file by definition needs an
    # existing file, so no force bypass — if you're editing, you must
    # have read it in this session.
    try:
        from core.services.read_before_write_guard import (
            check_operator_read_before_write,
        )
        _sid = (
            args.get("_runtime_session_id")
            or args.get("_session_id")
            or "default"
        )
        allowed, reason = check_operator_read_before_write(
            path, session_id=str(_sid), file_exists=True,
        )
        if not allowed and reason:
            return {
                "status": "error",
                "error": reason,
                "blocked_by": "read_before_write_guard",
                "path": path,
                "hint": (
                    "Kald operator_read_file('" + path
                    + "') først — operator_edit_file kan ikke "
                    "edite uden at have læst filen i denne session."
                ),
            }
    except Exception:
        pass
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_edit_file_async
    out = _run_operator_async(
        lambda: operator_edit_file_async(
            path=path,
            old_string=str(old_string),
            new_string=str(new_string),
            replace_all=bool(args.get("replace_all", False)),
            user_id=user_id,
            timeout_s=30.0,
        ),
        tool_name="operator_edit_file",
    )
    # Phase 2/3: record the edit + attach session summary so the LLM
    # sees the running tally without us building a UI sidebar.
    if isinstance(out, dict) and out.get("status") == "ok":
        try:
            from core.services.read_before_write_guard import (
                record_operator_edit,
                get_session_edit_summary,
            )
            _sid = (
                args.get("_runtime_session_id")
                or args.get("_session_id")
                or "default"
            )
            record_operator_edit(path, session_id=str(_sid), kind="edit")
            summary = get_session_edit_summary(session_id=str(_sid))
            if summary:
                out["_session_summary"] = summary
        except Exception:
            pass
        _record_active_file(path, "write", args)
    return out


def _exec_operator_glob(args: dict[str, Any]) -> dict[str, Any]:
    pattern = str(args.get("pattern") or "").strip()
    if not pattern:
        return {"error": "pattern is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_glob_async
    return _run_operator_async(
        lambda: operator_glob_async(
            pattern=pattern,
            cwd=args.get("cwd"),
            max_results=int(args.get("max_results") or 200),
            user_id=user_id,
            timeout_s=30.0,
        ),
        tool_name="operator_glob",
    )


def _exec_operator_grep(args: dict[str, Any]) -> dict[str, Any]:
    pattern = str(args.get("pattern") or "").strip()
    if not pattern:
        return {"error": "pattern is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_grep_async
    return _run_operator_async(
        lambda: operator_grep_async(
            pattern=pattern,
            path=args.get("path"),
            glob=args.get("glob"),
            case_insensitive=bool(args.get("case_insensitive", False)),
            max_results=int(args.get("max_results") or 200),
            user_id=user_id,
            timeout_s=60.0,  # grep over many files takes longer
        ),
        tool_name="operator_grep",
        timeout_s=65.0,
    )


def _exec_operator_list_dir(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    if not path:
        return {"error": "path is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_list_dir_async
    return _run_operator_async(
        lambda: operator_list_dir_async(path=path, user_id=user_id, timeout_s=30.0),
        tool_name="operator_list_dir",
    )


def _exec_operator_webfetch(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url:
        return {"error": "url is required", "status": "error"}
    user_id = _operator_user_id(args)
    timeout_s = float(args.get("timeout_s") or 30.0)
    from core.tools.operator_tools import operator_webfetch_async
    return _run_operator_async(
        lambda: operator_webfetch_async(
            url=url,
            method=str(args.get("method") or "GET"),
            headers=args.get("headers"),
            body=args.get("body"),
            timeout_s=timeout_s,
            user_id=user_id,
        ),
        tool_name="operator_webfetch",
        timeout_s=timeout_s + 35.0,
    )


def _exec_operator_bash(args: dict[str, Any]) -> dict[str, Any]:
    command = str(args.get("command") or "").strip()
    if not command:
        return {"error": "command is required", "status": "error"}
    user_id = _operator_user_id(args)
    timeout_s = float(args.get("timeout_s") or 30.0)
    thread_timeout = min(timeout_s, 300.0) + 30.0

    # Dispatch direkte til bridge — approval er håndteret af
    # chat-approval-card mekanismen på et højere niveau i flowet.
    # (screenshot og clipboard gør det samme; OS-dialog er fjernet).
    from core.tools.operator_tools import operator_bash_async
    return _run_operator_async(
        lambda: operator_bash_async(
            command=command,
            cwd=args.get("cwd"),
            timeout_s=timeout_s,
            user_id=user_id,
            skip_approval=True,
        ),
        tool_name="operator_bash",
        timeout_s=thread_timeout,
    )


def _exec_operator_screenshot(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    display_id = args.get("display_id")
    save_path = args.get("save_path")
    fmt = str(args.get("format") or "png").lower()
    jpeg_quality = int(args.get("jpeg_quality") or 85)
    from core.tools.operator_tools import operator_screenshot_async
    return _run_operator_async(
        lambda: operator_screenshot_async(
            user_id=user_id,
            display_id=int(display_id) if display_id is not None else None,
            save_path=str(save_path) if save_path else None,
            format=fmt,
            jpeg_quality=jpeg_quality,
            timeout_s=30.0,
        ),
        tool_name="operator_screenshot",
        timeout_s=45.0,
    )


def _exec_operator_open_url(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url:
        return {"error": "url is required", "status": "error"}
    user_id = _operator_user_id(args)

    # Godkendelse via chat-card (ikke OS-dialog).
    skip_approval = bool(args.get("_runtime_trust_all"))
    if not skip_approval:
        return {
            "status": "approval_needed",
            "tool_name": "operator_open_url",
            "message": f"Jarvis vil åbne URL i operatørens browser: {url}",
            "command": url,
            "url": url,
        }

    # Allerede godkendt — dispatcher til bridge med skip_approval=True.
    from core.tools.operator_tools import operator_open_url_async
    return _run_operator_async(
        lambda: operator_open_url_async(
            url=url,
            user_id=user_id,
            skip_approval=True,  # godkendt i chat; bridge spørger ikke igen
            timeout_s=30.0,
        ),
        tool_name="operator_open_url",
        timeout_s=45.0,
    )


def _exec_operator_launch_app(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or args.get("app") or "").strip()
    if not path:
        return {"error": "path is required", "status": "error"}
    user_id = _operator_user_id(args)
    cli_args = args.get("args") or []
    if not isinstance(cli_args, list):
        return {"error": "args must be a list of strings", "status": "error"}
    cwd = args.get("cwd")

    # Godkendelse via chat-card (ikke OS-dialog).
    skip_approval = bool(args.get("_runtime_trust_all"))
    if not skip_approval:
        args_preview = " ".join(str(a) for a in cli_args) if cli_args else ""
        detail = f"{path} {args_preview}".strip()
        return {
            "status": "approval_needed",
            "tool_name": "operator_launch_app",
            "message": f"Jarvis vil starte et program på operatørens maskine: {detail}",
            "command": detail,
            "path": path,
        }

    # Allerede godkendt — dispatcher til bridge med skip_approval=True.
    from core.tools.operator_tools import operator_launch_app_async
    return _run_operator_async(
        lambda: operator_launch_app_async(
            path=path,
            user_id=user_id,
            args=[str(a) for a in cli_args],
            cwd=str(cwd) if cwd else None,
            skip_approval=True,  # godkendt i chat; bridge spørger ikke igen
            timeout_s=30.0,
        ),
        tool_name="operator_launch_app",
        timeout_s=45.0,
    )


def _exec_operator_mouse_move(args: dict[str, Any]) -> dict[str, Any]:
    try:
        x, y = int(args["x"]), int(args["y"])
    except (KeyError, ValueError, TypeError):
        return {"error": "x and y are required integers", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_mouse_move_async
    return _run_operator_async(
        lambda: operator_mouse_move_async(
            x=x, y=y, user_id=user_id, smooth=bool(args.get("smooth")), timeout_s=15.0,
        ),
        tool_name="operator_mouse_move",
        timeout_s=20.0,
    )


def _exec_operator_mouse_click(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    button = str(args.get("button") or "left")
    double = bool(args.get("double"))
    x = args.get("x")
    y = args.get("y")
    from core.tools.operator_tools import operator_mouse_click_async
    return _run_operator_async(
        lambda: operator_mouse_click_async(
            user_id=user_id,
            button=button,
            double=double,
            x=int(x) if x is not None else None,
            y=int(y) if y is not None else None,
            timeout_s=15.0,
        ),
        tool_name="operator_mouse_click",
        timeout_s=20.0,
    )


def _exec_operator_mouse_position(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_mouse_position_async
    return _run_operator_async(
        lambda: operator_mouse_position_async(user_id=user_id, timeout_s=10.0),
        tool_name="operator_mouse_position",
        timeout_s=15.0,
    )


def _exec_operator_keyboard_type(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("text")
    if not isinstance(text, str) or not text:
        return {"error": "text is required (non-empty string)", "status": "error"}
    user_id = _operator_user_id(args)
    delay_ms = args.get("delay_ms")
    from core.tools.operator_tools import operator_keyboard_type_async
    return _run_operator_async(
        lambda: operator_keyboard_type_async(
            text=text,
            user_id=user_id,
            delay_ms=int(delay_ms) if delay_ms is not None else None,
            timeout_s=max(15.0, len(text) * 0.05),
        ),
        tool_name="operator_keyboard_type",
        timeout_s=max(20.0, len(text) * 0.1),
    )


def _exec_operator_keyboard_press(args: dict[str, Any]) -> dict[str, Any]:
    keys = args.get("keys")
    if keys is None:
        return {"error": "keys is required", "status": "error"}
    if not isinstance(keys, (str, list)):
        return {"error": "keys must be a string or list of strings", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_keyboard_press_async
    return _run_operator_async(
        lambda: operator_keyboard_press_async(
            keys=keys, user_id=user_id, timeout_s=10.0,
        ),
        tool_name="operator_keyboard_press",
        timeout_s=15.0,
    )


def _exec_operator_screen_size(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_screen_size_async
    return _run_operator_async(
        lambda: operator_screen_size_async(user_id=user_id, timeout_s=10.0),
        tool_name="operator_screen_size",
        timeout_s=15.0,
    )


def _exec_operator_clipboard_read(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_clipboard_read_async
    return _run_operator_async(
        lambda: operator_clipboard_read_async(user_id=user_id, timeout_s=10.0),
        tool_name="operator_clipboard_read",
        timeout_s=15.0,
    )


def _exec_operator_clipboard_write(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("text")
    if not isinstance(text, str):
        return {"error": "text is required (string)", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_clipboard_write_async
    return _run_operator_async(
        lambda: operator_clipboard_write_async(text=text, user_id=user_id, timeout_s=10.0),
        tool_name="operator_clipboard_write",
        timeout_s=15.0,
    )


def _exec_operator_list_windows(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_list_windows_async
    return _run_operator_async(
        lambda: operator_list_windows_async(user_id=user_id, timeout_s=15.0),
        tool_name="operator_list_windows",
        timeout_s=20.0,
    )


def _exec_operator_focus_window(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    title_substring = args.get("title_substring")
    handle = args.get("handle")
    if title_substring is None and handle is None:
        return {"error": "title_substring or handle is required", "status": "error"}
    from core.tools.operator_tools import operator_focus_window_async
    return _run_operator_async(
        lambda: operator_focus_window_async(
            user_id=user_id,
            title_substring=str(title_substring) if title_substring is not None else None,
            handle=int(handle) if handle is not None else None,
            timeout_s=15.0,
        ),
        tool_name="operator_focus_window",
        timeout_s=20.0,
    )


def _exec_operator_mouse_scroll(args: dict[str, Any]) -> dict[str, Any]:
    direction = str(args.get("direction") or "down")
    if direction not in ("up", "down", "left", "right"):
        return {"error": "direction must be one of: up, down, left, right", "status": "error"}
    amount = int(args.get("amount") or 3)
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_mouse_scroll_async
    return _run_operator_async(
        lambda: operator_mouse_scroll_async(
            direction=direction, amount=amount, user_id=user_id, timeout_s=10.0,
        ),
        tool_name="operator_mouse_scroll",
        timeout_s=15.0,
    )


def _exec_operator_mouse_drag(args: dict[str, Any]) -> dict[str, Any]:
    try:
        from_x = int(args["from_x"])
        from_y = int(args["from_y"])
        to_x = int(args["to_x"])
        to_y = int(args["to_y"])
    except (KeyError, ValueError, TypeError):
        return {"error": "from_x, from_y, to_x, to_y are required integers", "status": "error"}
    button = str(args.get("button") or "left")
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_mouse_drag_async
    return _run_operator_async(
        lambda: operator_mouse_drag_async(
            from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y,
            button=button, user_id=user_id, timeout_s=15.0,
        ),
        tool_name="operator_mouse_drag",
        timeout_s=20.0,
    )


def _exec_operator_list_processes(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    filter_str = args.get("filter")
    from core.tools.operator_tools import operator_list_processes_async
    return _run_operator_async(
        lambda: operator_list_processes_async(
            user_id=user_id,
            filter=str(filter_str) if filter_str is not None else None,
            timeout_s=15.0,
        ),
        tool_name="operator_list_processes",
        timeout_s=20.0,
    )


def _exec_operator_kill_process(args: dict[str, Any]) -> dict[str, Any]:
    pid = args.get("pid")
    if pid is None:
        return {"error": "pid is required", "status": "error"}
    try:
        pid = int(pid)
    except (ValueError, TypeError):
        return {"error": "pid must be an integer", "status": "error"}
    user_id = _operator_user_id(args)

    # Godkendelse via chat-card (ikke OS-dialog).
    skip_approval = bool(args.get("_runtime_trust_all"))
    if not skip_approval:
        return {
            "status": "approval_needed",
            "tool_name": "operator_kill_process",
            "message": f"Jarvis vil afslutte proces med PID {pid} på operatørens maskine",
            "command": str(pid),
            "pid": pid,
        }

    # Allerede godkendt — dispatcher til bridge med skip_approval=True.
    from core.tools.operator_tools import operator_kill_process_async
    return _run_operator_async(
        lambda: operator_kill_process_async(
            pid=pid,
            user_id=user_id,
            skip_approval=True,  # godkendt i chat; bridge spørger ikke igen
            timeout_s=30.0,
        ),
        tool_name="operator_kill_process",
        timeout_s=45.0,
    )


def _exec_operator_speak(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("text")
    if not isinstance(text, str) or not text:
        return {"error": "text is required (non-empty string)", "status": "error"}
    rate = int(args.get("rate") or 5)
    rate = max(0, min(10, rate))
    voice = args.get("voice")
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_speak_async
    return _run_operator_async(
        lambda: operator_speak_async(
            text=text, user_id=user_id,
            voice=str(voice) if voice is not None else None,
            rate=rate, timeout_s=30.0,
        ),
        tool_name="operator_speak",
        timeout_s=40.0,
    )


def _exec_operator_screenshot_window(args: dict[str, Any]) -> dict[str, Any]:
    title_substring = args.get("title_substring")
    handle = args.get("handle")
    if title_substring is None and handle is None:
        return {"error": "title_substring or handle is required", "status": "error"}
    save_path = args.get("save_path")
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_screenshot_window_async
    return _run_operator_async(
        lambda: operator_screenshot_window_async(
            user_id=user_id,
            title_substring=str(title_substring) if title_substring is not None else None,
            handle=str(handle) if handle is not None else None,
            save_path=str(save_path) if save_path is not None else None,
            timeout_s=20.0,
        ),
        tool_name="operator_screenshot_window",
        timeout_s=30.0,
    )


def _exec_operator_find_image(args: dict[str, Any]) -> dict[str, Any]:
    template_path = args.get("template_path")
    if not isinstance(template_path, str) or not template_path:
        return {"error": "template_path is required (string)", "status": "error"}
    confidence = float(args.get("confidence") or 0.85)
    confidence = max(0.0, min(1.0, confidence))
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_find_image_async
    return _run_operator_async(
        lambda: operator_find_image_async(
            template_path=template_path, user_id=user_id,
            confidence=confidence, timeout_s=20.0,
        ),
        tool_name="operator_find_image",
        timeout_s=30.0,
    )


def _exec_operator_ocr_region(args: dict[str, Any]) -> dict[str, Any]:
    try:
        x = int(args["x"])
        y = int(args["y"])
        width = int(args["width"])
        height = int(args["height"])
    except (KeyError, ValueError, TypeError):
        return {"error": "x, y, width, height are required integers", "status": "error"}
    if width <= 0 or height <= 0:
        return {"error": "width and height must be positive", "status": "error"}
    lang = str(args.get("lang") or "eng")
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_ocr_region_async
    return _run_operator_async(
        lambda: operator_ocr_region_async(
            x=x, y=y, width=width, height=height,
            user_id=user_id, lang=lang, timeout_s=30.0,
        ),
        tool_name="operator_ocr_region",
        timeout_s=45.0,
    )


# ── Tier-3 exec stubs ────────────────────────────────────────────────────


def _exec_operator_reminder(args: dict[str, Any]) -> dict[str, Any]:
    when = str(args.get("when") or "").strip()
    message = str(args.get("message") or "").strip()
    if not when:
        return {"error": "when is required", "status": "error"}
    if not message:
        return {"error": "message is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_reminder_async
    return _run_operator_async(
        lambda: operator_reminder_async(
            when=when, message=message,
            title=str(args.get("title")) if args.get("title") else None,
            user_id=user_id, timeout_s=15.0,
        ),
        tool_name="operator_reminder",
        timeout_s=25.0,
    )


def _exec_operator_wakeup(args: dict[str, Any]) -> dict[str, Any]:
    when = str(args.get("when") or "").strip()
    if not when:
        return {"error": "when is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_wakeup_async
    return _run_operator_async(
        lambda: operator_wakeup_async(
            when=when,
            message=str(args.get("message")) if args.get("message") else None,
            title=str(args.get("title")) if args.get("title") else None,
            user_id=user_id, timeout_s=15.0,
        ),
        tool_name="operator_wakeup",
        timeout_s=25.0,
    )


def _exec_operator_scheduled_list(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_scheduled_list_async
    return _run_operator_async(
        lambda: operator_scheduled_list_async(
            user_id=user_id,
            kind=str(args.get("kind")) if args.get("kind") else None,
            include_fired=bool(args.get("include_fired")),
            timeout_s=15.0,
        ),
        tool_name="operator_scheduled_list",
        timeout_s=20.0,
    )


def _exec_operator_scheduled_cancel(args: dict[str, Any]) -> dict[str, Any]:
    id_ = str(args.get("id") or "").strip()
    if not id_:
        return {"error": "id is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_scheduled_cancel_async
    return _run_operator_async(
        lambda: operator_scheduled_cancel_async(id=id_, user_id=user_id, timeout_s=15.0),
        tool_name="operator_scheduled_cancel",
        timeout_s=20.0,
    )


def _exec_operator_process_spawn(args: dict[str, Any]) -> dict[str, Any]:
    cmd = str(args.get("cmd") or "").strip()
    if not cmd:
        return {"error": "cmd is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_process_spawn_async
    return _run_operator_async(
        lambda: operator_process_spawn_async(
            cmd=cmd, user_id=user_id,
            cwd=str(args.get("cwd")) if args.get("cwd") else None,
            label=str(args.get("label")) if args.get("label") else None,
            timeout_s=15.0,
        ),
        tool_name="operator_process_spawn",
        timeout_s=20.0,
    )


def _exec_operator_process_status(args: dict[str, Any]) -> dict[str, Any]:
    id_ = str(args.get("id") or "").strip()
    if not id_:
        return {"error": "id is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_process_status_async
    return _run_operator_async(
        lambda: operator_process_status_async(id=id_, user_id=user_id, timeout_s=10.0),
        tool_name="operator_process_status",
        timeout_s=15.0,
    )


def _exec_operator_process_output(args: dict[str, Any]) -> dict[str, Any]:
    id_ = str(args.get("id") or "").strip()
    if not id_:
        return {"error": "id is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_process_output_async
    return _run_operator_async(
        lambda: operator_process_output_async(
            id=id_, user_id=user_id,
            since_offset=int(args.get("since_offset") or 0),
            max_bytes=int(args.get("max_bytes") or 64_000),
            timeout_s=15.0,
        ),
        tool_name="operator_process_output",
        timeout_s=20.0,
    )


def _exec_operator_process_kill(args: dict[str, Any]) -> dict[str, Any]:
    id_ = str(args.get("id") or "").strip()
    if not id_:
        return {"error": "id is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_process_kill_async
    return _run_operator_async(
        lambda: operator_process_kill_async(
            id=id_, user_id=user_id,
            signal=str(args.get("signal") or "SIGTERM"),
            timeout_s=10.0,
        ),
        tool_name="operator_process_kill",
        timeout_s=15.0,
    )


def _exec_operator_process_list(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_process_list_async
    return _run_operator_async(
        lambda: operator_process_list_async(
            user_id=user_id,
            include_finished=bool(args.get("include_finished", True)),
            timeout_s=10.0,
        ),
        tool_name="operator_process_list",
        timeout_s=15.0,
    )


def _exec_operator_notify(args: dict[str, Any]) -> dict[str, Any]:
    title = args.get("title")
    body = args.get("body")
    if not isinstance(title, str) or not title:
        return {"error": "title is required (non-empty string)", "status": "error"}
    if not isinstance(body, str):
        return {"error": "body is required (string)", "status": "error"}
    icon = args.get("icon")
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_notify_async
    return _run_operator_async(
        lambda: operator_notify_async(
            title=title, body=body, user_id=user_id,
            icon=str(icon) if icon is not None else None,
            timeout_s=10.0,
        ),
        tool_name="operator_notify",
        timeout_s=15.0,
    )


def _exec_operator_watch_folder(args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path")
    if not isinstance(path, str) or not path:
        return {"error": "path is required (non-empty string)", "status": "error"}
    recursive = bool(args.get("recursive", False))
    debounce_ms = int(args.get("debounce_ms") or 500)
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_watch_folder_async
    return _run_operator_async(
        lambda: operator_watch_folder_async(
            path=path, user_id=user_id,
            recursive=recursive, debounce_ms=debounce_ms,
            timeout_s=15.0,
        ),
        tool_name="operator_watch_folder",
        timeout_s=20.0,
    )


def _exec_operator_unwatch_folder(args: dict[str, Any]) -> dict[str, Any]:
    watcher_id = args.get("watcher_id")
    if not isinstance(watcher_id, str) or not watcher_id:
        return {"error": "watcher_id is required (non-empty string)", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_unwatch_folder_async
    return _run_operator_async(
        lambda: operator_unwatch_folder_async(
            watcher_id=watcher_id, user_id=user_id, timeout_s=10.0,
        ),
        tool_name="operator_unwatch_folder",
        timeout_s=15.0,
    )


def _exec_operator_watch_events(args: dict[str, Any]) -> dict[str, Any]:
    watcher_id = args.get("watcher_id")
    if not isinstance(watcher_id, str) or not watcher_id:
        return {"error": "watcher_id is required (non-empty string)", "status": "error"}
    max_events = int(args.get("max") or 100)
    max_events = max(1, min(1000, max_events))
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_watch_events_async
    return _run_operator_async(
        lambda: operator_watch_events_async(
            watcher_id=watcher_id, user_id=user_id, max=max_events, timeout_s=10.0,
        ),
        tool_name="operator_watch_events",
        timeout_s=15.0,
    )


def _exec_operator_record_audio(args: dict[str, Any]) -> dict[str, Any]:
    duration_s = args.get("duration_s")
    if duration_s is None:
        return {"error": "duration_s is required", "status": "error"}
    try:
        duration_s = int(duration_s)
    except (ValueError, TypeError):
        return {"error": "duration_s must be an integer", "status": "error"}
    if not (1 <= duration_s <= 300):
        return {"error": "duration_s must be between 1 and 300", "status": "error"}
    output_path = args.get("output_path")
    device = args.get("device")
    user_id = _operator_user_id(args)

    # Godkendelse via chat-card (ikke OS-dialog).
    skip_approval = bool(args.get("_runtime_trust_all"))
    if not skip_approval:
        return {
            "status": "approval_needed",
            "tool_name": "operator_record_audio",
            "message": f"Jarvis vil optage lyd fra mikrofonen i {duration_s} sekunder",
            "command": f"{duration_s}s lyd-optagelse",
            "duration_s": duration_s,
        }

    # Allerede godkendt — dispatcher til bridge med skip_approval=True.
    from core.tools.operator_tools import operator_record_audio_async
    return _run_operator_async(
        lambda: operator_record_audio_async(
            duration_s=duration_s,
            user_id=user_id,
            output_path=str(output_path) if output_path is not None else None,
            device=str(device) if device is not None else None,
            skip_approval=True,  # godkendt i chat; bridge spørger ikke igen
            timeout_s=float(duration_s) + 30.0,
        ),
        tool_name="operator_record_audio",
        timeout_s=float(duration_s) + 45.0,
    )


def _exec_operator_browser_open(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url:
        return {"error": "url is required", "status": "error"}
    user_id = _operator_user_id(args)
    wait_until = str(args.get("wait_until") or "load")
    timeout_ms = int(args.get("timeout_ms") or 30000)
    from core.tools.operator_tools import operator_browser_open_async
    return _run_operator_async(
        lambda: operator_browser_open_async(
            url=url, user_id=user_id, wait_until=wait_until,
            timeout_ms=timeout_ms, timeout_s=45.0,
        ),
        tool_name="operator_browser_open",
        timeout_s=55.0,
    )


def _exec_operator_browser_get_text(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    selector = args.get("selector")
    max_chars = int(args.get("max_chars") or 50000)
    from core.tools.operator_tools import operator_browser_get_text_async
    return _run_operator_async(
        lambda: operator_browser_get_text_async(
            user_id=user_id,
            selector=str(selector) if selector else None,
            max_chars=max_chars,
            timeout_s=20.0,
        ),
        tool_name="operator_browser_get_text",
        timeout_s=25.0,
    )


def _exec_operator_browser_get_links(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_browser_get_links_async
    return _run_operator_async(
        lambda: operator_browser_get_links_async(user_id=user_id, timeout_s=20.0),
        tool_name="operator_browser_get_links",
        timeout_s=25.0,
    )


def _exec_operator_browser_click(args: dict[str, Any]) -> dict[str, Any]:
    selector = str(args.get("selector") or "").strip()
    if not selector:
        return {"error": "selector is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_browser_click_async
    return _run_operator_async(
        lambda: operator_browser_click_async(
            selector=selector, user_id=user_id,
            wait_navigation=bool(args.get("wait_navigation")),
            wait_for_selector=bool(args.get("wait_for_selector", True)),
            timeout_ms=int(args.get("timeout_ms") or 5000),
            timeout_s=25.0,
        ),
        tool_name="operator_browser_click",
        timeout_s=30.0,
    )


def _exec_operator_browser_type(args: dict[str, Any]) -> dict[str, Any]:
    selector = str(args.get("selector") or "").strip()
    text = args.get("text")
    if not selector:
        return {"error": "selector is required", "status": "error"}
    if not isinstance(text, str):
        return {"error": "text is required (string)", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_browser_type_async
    return _run_operator_async(
        lambda: operator_browser_type_async(
            selector=selector, text=text, user_id=user_id,
            clear_first=bool(args.get("clear_first")),
            delay_ms=int(args.get("delay_ms") or 0),
            timeout_s=30.0,
        ),
        tool_name="operator_browser_type",
        timeout_s=35.0,
    )


def _exec_operator_browser_screenshot(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_browser_screenshot_async
    return _run_operator_async(
        lambda: operator_browser_screenshot_async(
            user_id=user_id,
            full_page=bool(args.get("full_page")),
            format=str(args.get("format") or "png"),
            jpeg_quality=int(args.get("jpeg_quality") or 85),
            timeout_s=30.0,
        ),
        tool_name="operator_browser_screenshot",
        timeout_s=40.0,
    )


def _exec_operator_browser_evaluate(args: dict[str, Any]) -> dict[str, Any]:
    script = str(args.get("script") or "")
    if not script:
        return {"error": "script is required", "status": "error"}
    user_id = _operator_user_id(args)

    # Godkendelse via chat-card (ikke OS-dialog).
    skip_approval = bool(args.get("_runtime_trust_all"))
    if not skip_approval:
        script_preview = script[:200] + "…" if len(script) > 200 else script
        return {
            "status": "approval_needed",
            "tool_name": "operator_browser_evaluate",
            "message": f"Jarvis vil køre JavaScript i operatørens browser: {script_preview}",
            "command": script_preview,
            "script": script,
        }

    # Allerede godkendt — dispatcher til bridge med skip_approval=True.
    from core.tools.operator_tools import operator_browser_evaluate_async
    return _run_operator_async(
        lambda: operator_browser_evaluate_async(
            script=script, user_id=user_id, skip_approval=True,  # godkendt i chat
            timeout_s=30.0,
        ),
        tool_name="operator_browser_evaluate",
        timeout_s=60.0,
    )


def _exec_operator_browser_status(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_browser_status_async
    return _run_operator_async(
        lambda: operator_browser_status_async(user_id=user_id, timeout_s=10.0),
        tool_name="operator_browser_status",
        timeout_s=15.0,
    )


def _exec_operator_browser_close(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_browser_close_async
    return _run_operator_async(
        lambda: operator_browser_close_async(user_id=user_id, timeout_s=10.0),
        tool_name="operator_browser_close",
        timeout_s=15.0,
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


def _exec_search(args: dict[str, Any]) -> dict[str, Any]:
    pattern = str(args.get("pattern") or "").strip()
    search_path = str(args.get("path") or "").strip() or str(PROJECT_ROOT)
    file_glob = str(args.get("glob") or "").strip()
    multiline = bool(args.get("multiline", False))
    case_insensitive = bool(args.get("ignore_case", False))
    if not pattern:
        return {"error": "pattern is required", "status": "error"}

    # Prefer ripgrep when present — much faster, smarter defaults
    # (.gitignore aware, binary-skip, type-detection). Fall back to grep
    # so the tool still works on machines without rg installed.
    have_rg = subprocess.run(
        ["which", "rg"], capture_output=True, text=True
    ).returncode == 0

    if have_rg:
        argv = ["rg", "-n", "--color=never", "-m", str(MAX_SEARCH_RESULTS)]
        if file_glob:
            argv += ["-g", file_glob]
        if multiline:
            argv += ["-U", "--multiline-dotall"]
        if case_insensitive:
            argv += ["-i"]
        argv += [pattern, "."]
    else:
        argv = [
            "grep", "-rn", "--color=never",
            "--exclude-dir=.git", "--exclude-dir=node_modules",
            "--exclude-dir=__pycache__", "--exclude-dir=.claude",
            "--exclude-dir=dist", "--exclude-dir=build",
            "-m", str(MAX_SEARCH_RESULTS),
        ]
        if file_glob:
            argv += [f"--include={file_glob}"]
        if case_insensitive:
            argv += ["-i"]
        argv += [pattern, "."]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=MAX_BASH_SECONDS,
            cwd=search_path,
        )
    except subprocess.TimeoutExpired:
        return {"error": "Search timed out", "status": "error"}

    lines = result.stdout.strip().splitlines()[:MAX_SEARCH_RESULTS]
    bounded = [
        line if len(line) <= MAX_SEARCH_LINE_CHARS else line[:MAX_SEARCH_LINE_CHARS - 1] + "…"
        for line in lines
    ]
    text = "\n".join(bounded) if bounded else "[no matches]"
    return {"text": text, "match_count": len(bounded), "status": "ok"}


def _exec_find_files(args: dict[str, Any]) -> dict[str, Any]:
    pattern = str(args.get("pattern") or "").strip()
    search_path = str(args.get("path") or "").strip() or str(PROJECT_ROOT)
    if not pattern:
        return {"error": "pattern is required", "status": "error"}

    # Use Python's pathlib.glob for proper recursive ** support and to sort
    # results by modification time (newest first — matches Claude Code's
    # Glob tool behavior). Falls back to find for non-recursive plain
    # patterns to keep behavior predictable for old call sites.
    if "**" in pattern or "/" in pattern:
        try:
            base = Path(search_path).expanduser().resolve()
            matches = sorted(
                (p for p in base.glob(pattern) if p.is_file()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            paths = [str(p) for p in matches[:MAX_FIND_RESULTS]]
            entries: list[str] = []
            for fp in paths:
                try:
                    size = os.path.getsize(fp)
                    entries.append(f"{fp} ({size}B)")
                except OSError:
                    entries.append(fp)
            text = "\n".join(entries) if entries else "[no matches]"
            return {"text": text, "match_count": len(entries), "status": "ok"}
        except Exception as exc:
            return {"error": f"glob failed: {exc}", "status": "error"}

    argv = [
        "find", search_path,
        "-type", "f",
        "-name", pattern,
        "-not", "-path", "*/.git/*",
        "-not", "-path", "*/node_modules/*",
        "-not", "-path", "*/__pycache__/*",
        "-not", "-path", "*/.claude/*",
    ]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=MAX_BASH_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {"error": "Find timed out", "status": "error"}

    paths = result.stdout.strip().splitlines()[:MAX_FIND_RESULTS]
    entries: list[str] = []
    for fp in paths:
        try:
            size = Path(fp).stat().st_size
            entries.append(f"{fp}  ({size} bytes)")
        except OSError:
            entries.append(fp)

    text = "\n".join(entries) if entries else "[no files found]"
    return {"text": text, "file_count": len(entries), "status": "ok"}


# ── Default bash session (for the one-shot `bash` tool) ──────────────
# We keep a single per-process default session id. The bash_session
# daemon is shared across workers (Unix socket singleton), so even if
# one worker's reference goes stale, the daemon keeps the session alive
# while another worker is using it. Stale-session retries are handled
# in _exec_bash via _reset_default_bash_session.
import threading as _threading_for_bash
_DEFAULT_BASH_SESSION_ID: str | None = None
_DEFAULT_BASH_SESSION_LOCK = _threading_for_bash.Lock()


def _get_or_open_default_bash_session() -> str | None:
    global _DEFAULT_BASH_SESSION_ID
    with _DEFAULT_BASH_SESSION_LOCK:
        sid = _DEFAULT_BASH_SESSION_ID
        if sid:
            # Verify the daemon still knows this session.
            listed = _exec_bash_session_list({})
            if listed.get("status") == "ok":
                alive_ids = {
                    str(s.get("session_id"))
                    for s in (listed.get("sessions") or [])
                    if s.get("alive")
                }
                if sid in alive_ids:
                    return sid
            # Otherwise: fall through and re-open below.
            _DEFAULT_BASH_SESSION_ID = None
        result = _exec_bash_session_open({})
        if result.get("status") == "ok" and result.get("session_id"):
            _DEFAULT_BASH_SESSION_ID = str(result["session_id"])
            return _DEFAULT_BASH_SESSION_ID
        return None


def _reset_default_bash_session() -> None:
    global _DEFAULT_BASH_SESSION_ID
    with _DEFAULT_BASH_SESSION_LOCK:
        _DEFAULT_BASH_SESSION_ID = None


def _exec_bash(args: dict[str, Any]) -> dict[str, Any]:
    command = str(args.get("command") or "").strip()
    if not command:
        return {"error": "command is required", "status": "error"}

    # Read-before-write guard for bash: detect cp/mv/redirect/tee/sed
    # patterns targeting protected files (SOUL.md, IDENTITY.md, USER.md,
    # MEMORY.md, ...). 2026-05-14 hardening after SOUL.md + USER.md
    # were overwritten via `bash cp` that bypassed the write_file guard.
    try:
        from core.services.read_before_write_guard import check_bash_command_safe
        _session_id = (
            args.get("_runtime_session_id")
            or args.get("_session_id")
            or "default"
        )
        _guard_allowed, _guard_reason = check_bash_command_safe(
            command, session_id=str(_session_id)
        )
        if not _guard_allowed:
            return {"status": "guard_blocked", "error": _guard_reason}
    except Exception:
        pass  # guard failure → allow (fail-open)

    classification = classify_command(command)

    if classification == "blocked":
        return {"error": f"Command blocked for safety: {command}", "status": "blocked"}

    if classification == "destructive":
        return {
            "status": "approval_needed",
            "message": f"Destructive command requires explicit approval: {command}",
            "command": command,
            "classification": "destructive",
        }

    if classification == "approval":
        return {
            "status": "approval_needed",
            "message": f"This command may modify the system. Please confirm: {command}",
            "command": command,
            "classification": "mutation",
        }

    # Auto-approved (read-only). Route through the bash_session daemon so
    # we get:
    #   • A persistent shared shell (cd, env-vars, virtualenvs persist
    #     across calls) — no more "lost cwd" between bash invocations.
    #   • A 300s default timeout instead of MAX_BASH_SECONDS=15s.
    #   • Auto-recovery if the daemon died (session re-opened on next call).
    # The legacy subprocess path is kept as a fallback if the daemon
    # really cannot be reached.
    try:
        sid = _get_or_open_default_bash_session()
    except Exception as exc:
        sid = None
        logger.debug("bash: default session resolve failed: %s", exc)

    if sid:
        run_result = _exec_bash_session_run({
            "session_id": sid,
            "command": command,
            "timeout": 120.0,  # bump from 15s — most ops need more
        })
        # If the session died between resolve and run (rare but possible),
        # transparently retry with a fresh session once.
        err = str(run_result.get("error") or "")
        if "unknown session_id" in err or "session terminated" in err:
            _reset_default_bash_session()
            try:
                sid2 = _get_or_open_default_bash_session()
            except Exception:
                sid2 = None
            if sid2:
                run_result = _exec_bash_session_run({
                    "session_id": sid2,
                    "command": command,
                    "timeout": 120.0,
                })
        # Normalize bash_session_run shape -> bash shape
        if run_result.get("status") in ("ok", None) and "exit_code" in run_result:
            output = str(run_result.get("output") or "").strip()
            if len(output) > MAX_BASH_OUTPUT_CHARS:
                output = output[:MAX_BASH_OUTPUT_CHARS - 1] + "…"
            return {
                "text": output or "[no output]",
                "exit_code": run_result.get("exit_code"),
                "status": "ok",
            }
        # Daemon-side error — fall through to subprocess fallback so a
        # transient daemon problem doesn't break bash entirely.
        logger.warning("bash: session path errored, falling back to subprocess: %s", err)

    # Fallback: legacy one-shot subprocess.
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
        output += "\n[stderr] " + result.stderr.strip()

    if len(output) > MAX_BASH_OUTPUT_CHARS:
        output = output[:MAX_BASH_OUTPUT_CHARS - 1] + "…"

    return {
        "text": output or "[no output]",
        "exit_code": result.returncode,
        "status": "ok",
    }


def _exec_web_fetch(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url:
        return {"error": "url is required", "status": "error"}

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    req = urllib_request.Request(
        url,
        headers={"User-Agent": "Jarvis/2.0 (personal assistant)"},
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"Fetch failed: {exc}", "status": "error"}

    # Strip HTML tags for a rough text extraction
    text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > MAX_WEB_FETCH_CHARS:
        text = text[:MAX_WEB_FETCH_CHARS - 1] + "…"

    return {"text": text, "url": url, "chars": len(text), "status": "ok"}


def _exec_web_scrape(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.web_scrape_tool import web_scrape
    url = str(args.get("url") or "").strip()
    if not url:
        return {"error": "url is required", "status": "error"}
    mode = str(args.get("mode") or "auto").strip()
    extract = str(args.get("extract") or "").strip()
    include_links = bool(args.get("include_links", False))
    return web_scrape(url, mode=mode, extract=extract, include_links=include_links)


def _read_api_key(key: str) -> str:
    """Read an API key directly from runtime.json."""
    from core.runtime.config import SETTINGS_FILE
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return str(data.get(key) or "")
    except Exception:
        return ""


def _fetch_tavily(query: str, max_results: int) -> dict[str, Any]:
    """Raw Tavily API call — no caching."""
    api_key = _read_api_key("tavily_api_key")
    if not api_key:
        return {"error": "tavily_api_key not configured in runtime.json", "status": "error"}

    payload = json.dumps({
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": True,
    }).encode()
    req = urllib_request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib_request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read())
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"Search failed: {exc}", "status": "error"}

    lines: list[str] = []
    if data.get("answer"):
        lines.append(f"**Summary:** {data['answer']}\n")
    for i, r in enumerate(data.get("results", []), 1):
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "")[:300]
        lines.append(f"{i}. **{title}**\n   {content}\n   {url}")
    text = "\n\n".join(lines) if lines else "[no results]"
    return {"text": text, "result_count": len(data.get("results", [])), "query": query, "status": "ok"}


def _cached_web_search_fn(*, query: str, max_results: int, fetch_fn: Any) -> dict[str, Any]:
    """Wrapper so tests can monkeypatch the cache layer."""
    from core.tools.web_cache import cached_web_search

    return cached_web_search(query=query, max_results=max_results, fetch_fn=fetch_fn)


def _exec_web_search(args: dict[str, Any]) -> dict[str, Any]:
    """Web search via Tavily API with result caching."""
    query = str(args.get("query") or "").strip()
    if not query:
        return {"error": "query is required", "status": "error"}
    max_results = min(int(args.get("max_results") or 5), 10)

    return _cached_web_search_fn(query=query, max_results=max_results, fetch_fn=_fetch_tavily)


def _read_user_location() -> str:
    """Read Location from the live workspace USER.md."""
    try:
        user_md = WORKSPACE_DIR / "USER.md"
        for line in user_md.read_text(encoding="utf-8").splitlines():
            if line.startswith("Location:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "Svendborg, Denmark"


def _exec_get_weather(args: dict[str, Any]) -> dict[str, Any]:
    """Current weather via OpenWeatherMap."""
    city = str(args.get("city") or "").strip() or _read_user_location()

    api_key = _read_api_key("openweathermap_api_key")
    if not api_key:
        return {"error": "openweathermap_api_key not configured in runtime.json", "status": "error"}

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={urllib_request.quote(city)}&appid={api_key}&units=metric&lang=en"
    )
    try:
        with urllib_request.urlopen(urllib_request.Request(url), timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"Weather fetch failed: {exc}", "status": "error"}

    main = data.get("main", {})
    weather = data.get("weather", [{}])[0]
    wind = data.get("wind", {})
    name = data.get("name", city)
    country = data.get("sys", {}).get("country", "")
    return {
        "city": f"{name}, {country}",
        "description": weather.get("description", ""),
        "temp_c": main.get("temp"),
        "feels_like_c": main.get("feels_like"),
        "humidity_pct": main.get("humidity"),
        "wind_ms": wind.get("speed"),
        "status": "ok",
    }


def _exec_get_exchange_rate(args: dict[str, Any]) -> dict[str, Any]:
    """Currency exchange rates via exchangerate.host."""
    base = str(args.get("base") or "DKK").strip().upper()
    targets = str(args.get("targets") or "").strip().upper()

    api_key = _read_api_key("exchangerate_api_key")
    if not api_key:
        return {"error": "exchangerate_api_key not configured in runtime.json", "status": "error"}

    url = f"https://api.exchangerate.host/live?access_key={api_key}&source={base}"
    if targets:
        url += f"&currencies={targets}"
    try:
        with urllib_request.urlopen(urllib_request.Request(url), timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"Exchange rate fetch failed: {exc}", "status": "error"}

    if not data.get("success"):
        return {"error": data.get("error", {}).get("info", "API error"), "status": "error"}

    quotes = data.get("quotes", {})
    # Strip source prefix from keys (e.g. "DKKUSD" → "USD")
    rates = {k[len(base):]: v for k, v in quotes.items()}
    return {"base": base, "rates": rates, "status": "ok"}


def _exec_get_news(args: dict[str, Any]) -> dict[str, Any]:
    """Recent news via NewsAPI."""
    query = str(args.get("query") or "").strip()
    if not query:
        return {"error": "query is required", "status": "error"}
    language = str(args.get("language") or "en").strip()
    max_results = min(int(args.get("max_results") or 5), 10)

    api_key = _read_api_key("newsapi_api_key")
    if not api_key:
        return {"error": "newsapi_api_key not configured in runtime.json", "status": "error"}

    url = (
        f"https://newsapi.org/v2/everything"
        f"?q={urllib_request.quote(query)}&language={language}"
        f"&pageSize={max_results}&sortBy=publishedAt&apiKey={api_key}"
    )
    try:
        with urllib_request.urlopen(urllib_request.Request(url), timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"News fetch failed: {exc}", "status": "error"}

    articles = data.get("articles", [])
    lines: list[str] = []
    for i, a in enumerate(articles, 1):
        title = a.get("title", "")
        source = a.get("source", {}).get("name", "")
        published = a.get("publishedAt", "")[:10]
        description = (a.get("description") or "")[:200]
        url_a = a.get("url", "")
        lines.append(f"{i}. **{title}** ({source}, {published})\n   {description}\n   {url_a}")
    text = "\n\n".join(lines) if lines else "[no articles found]"
    return {"text": text, "article_count": len(articles), "query": query, "status": "ok"}


def _exec_analyze_image(args: dict[str, Any]) -> dict[str, Any]:
    """Analyze an image using a vision-capable model via Ollama.

    Requires a vision model to be running (e.g. llava, moondream, gemma4).
    Accepts a local file path or a URL.
    """
    import base64

    image_path = str(args.get("image_path") or "").strip()
    image_url = str(args.get("image_url") or "").strip()
    prompt = str(args.get("prompt") or "Describe this image in detail.").strip()
    model = str(args.get("model") or "").strip()

    if not model:
        # Try to pick a vision-capable model from running Ollama models
        try:
            with urllib_request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as resp:
                tags = json.loads(resp.read())
            names = [m["name"] for m in tags.get("models", [])]
            vision_keywords = ("llava", "moondream", "bakllava", "gemma4", "minicpm", "vision")
            model = next((n for n in names if any(k in n.lower() for k in vision_keywords)), "")
        except Exception:
            pass
        if not model:
            return {
                "error": (
                    "No vision-capable model found. Pull one with: "
                    "ollama pull llava  or  ollama pull moondream"
                ),
                "status": "error",
            }

    # Load image as base64
    image_b64: str | None = None
    if image_path:
        try:
            image_b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
        except OSError as exc:
            return {"error": f"Could not read image file: {exc}", "status": "error"}
    elif image_url:
        try:
            req = urllib_request.Request(
                image_url, headers={"User-Agent": "Jarvis/2.0"}
            )
            with urllib_request.urlopen(req, timeout=15) as resp:
                image_b64 = base64.b64encode(resp.read()).decode()
        except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
            return {"error": f"Could not fetch image URL: {exc}", "status": "error"}
    else:
        return {"error": "image_path or image_url is required", "status": "error"}

    payload = json.dumps({
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }
        ],
        "stream": False,
    }).encode()

    req = urllib_request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    # 2026-06-10 (Claude): bumpet 60s → 180s + 1 retry. gemma4:31b-cloud
    # har cold-start latens når den ikke er blevet brugt i et stykke tid
    # — første kald kan tage 30-60s, store billeder forlænger yderligere.
    # Bjørn så live: vision model call failed: timed out, men direkte test
    # 5 min senere virkede på ~5s (modellen blev varm). Retry med længere
    # timeout giver Ollama Cloud chance for at varme op uden at faile hele
    # vision-skill.
    _last_exc: Exception | None = None
    result = None
    for _vision_attempt in range(2):
        try:
            with urllib_request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read())
            break
        except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
            _last_exc = exc
            # Retry once for transient timeout/network issues; cold-start
            # tager typisk 30-60s og næste call kommer på varm cache.
            continue
    if result is None:
        return {
            "error": f"Vision model call failed after 2 attempts: {_last_exc}",
            "status": "error",
        }

    answer = result.get("message", {}).get("content", "").strip()
    if not answer:
        return {"error": "Vision model returned empty response", "status": "error"}
    return {"analysis": answer, "model": model, "status": "ok"}


def _exec_read_archive(args: dict[str, Any]) -> dict[str, Any]:
    """List or extract a zip / tar / rar archive.

    Security: only allows paths inside ~/.jarvis-v2/ to prevent path traversal.
    """
    archive_path = str(args.get("archive_path") or "").strip()
    if not archive_path:
        return {"error": "archive_path is required", "status": "error"}

    allowed_prefix = str((Path.home() / ".jarvis-v2").resolve())
    resolved = str(Path(archive_path).resolve())
    if not resolved.startswith(allowed_prefix):
        return {
            "error": f"archive_path must be inside ~/.jarvis-v2/ (got: {archive_path})",
            "status": "error",
        }

    path = Path(archive_path)
    if not path.exists():
        return {"error": f"File not found: {archive_path}", "status": "error"}

    extract = bool(args.get("extract", False))
    extract_path_arg = str(args.get("extract_path") or "").strip()
    name_lower = path.name.lower()

    try:
        if name_lower.endswith(".zip"):
            import zipfile as _zipfile
            with _zipfile.ZipFile(path) as zf:
                file_list = zf.namelist()
                if extract:
                    dest = Path(extract_path_arg) if extract_path_arg else path.parent / f"{path.stem}_extracted"
                    dest.mkdir(parents=True, exist_ok=True)
                    zf.extractall(dest)
        elif any(name_lower.endswith(ext) for ext in (".tar.gz", ".tgz", ".tar.bz2", ".tar")):
            import tarfile as _tarfile
            with _tarfile.open(path) as tf:
                file_list = tf.getnames()
                if extract:
                    dest = Path(extract_path_arg) if extract_path_arg else path.parent / f"{path.stem}_extracted"
                    dest.mkdir(parents=True, exist_ok=True)
                    tf.extractall(dest)
        elif name_lower.endswith(".rar"):
            try:
                import rarfile as _rarfile
            except ImportError:
                return {
                    "error": "rarfile package not installed. Run: pip install rarfile",
                    "status": "error",
                }
            with _rarfile.RarFile(path) as rf:
                file_list = rf.namelist()
                if extract:
                    dest = Path(extract_path_arg) if extract_path_arg else path.parent / f"{path.stem}_extracted"
                    dest.mkdir(parents=True, exist_ok=True)
                    rf.extractall(dest)
        else:
            return {
                "error": f"Unsupported archive format: {path.suffix}. Supported: .zip, .tar, .tar.gz, .tgz, .tar.bz2, .rar",
                "status": "error",
            }
    except Exception as exc:
        return {"error": f"Archive operation failed: {exc}", "status": "error"}

    result: dict[str, Any] = {"file_list": file_list, "count": len(file_list), "status": "ok"}
    if extract:
        result["extracted_to"] = str(dest)
    return result


def _exec_wolfram_query(args: dict[str, Any]) -> dict[str, Any]:
    """Precise answers via Wolfram Alpha Short Answers API."""
    query = str(args.get("query") or "").strip()
    if not query:
        return {"error": "query is required", "status": "error"}

    app_id = _read_api_key("wolframalpha_app_id")
    if not app_id:
        return {"error": "wolframalpha_app_id not configured in runtime.json", "status": "error"}

    url = (
        f"https://api.wolframalpha.com/v1/result"
        f"?appid={app_id}&i={urllib_request.quote(query)}"
    )
    try:
        with urllib_request.urlopen(urllib_request.Request(url), timeout=15) as resp:
            answer = resp.read().decode("utf-8", errors="replace").strip()
    except urllib_error.HTTPError as exc:
        if exc.code == 501:
            return {"error": "Wolfram Alpha could not interpret this query", "status": "error"}
        return {"error": f"Wolfram Alpha error: {exc}", "status": "error"}
    except (urllib_error.URLError, OSError) as exc:
        return {"error": f"Wolfram Alpha fetch failed: {exc}", "status": "error"}

    return {"answer": answer, "query": query, "status": "ok"}


def _exec_list_initiatives(_args: dict[str, Any]) -> dict[str, Any]:
    """Return current initiative queue state."""
    try:
        from core.services.initiative_queue import get_initiative_queue_state
        state = get_initiative_queue_state()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    pending = state.get("pending", [])
    recent_acted = state.get("recent_acted", [])
    life_projects = state.get("life_projects", [])
    lines = [
        f"Queue: {state.get('pending_count', 0)} pending / {state.get('acted_count', 0)} acted / {state.get('expired_count', 0)} expired",
        f"Capacity: {state.get('pending_count', 0)}/{state.get('max_queue_size', 8)}",
        "",
    ]
    if pending:
        lines.append("### Pending")
        for item in pending:
            priority = item.get("priority", "medium")
            focus = item.get("focus", "?")
            attempts = item.get("attempt_count", 0)
            lines.append(f"- [{priority}] {focus}" + (f" (attempts: {attempts})" if attempts else ""))
    else:
        lines.append("No pending initiatives.")

    if recent_acted:
        lines.append("")
        lines.append("### Recently Acted")
        for item in recent_acted:
            focus = item.get("focus", "?")
            summary = item.get("action_summary", "")
            lines.append(f"- {focus}" + (f" → {summary}" if summary else ""))

    if life_projects:
        lines.append("")
        lines.append("### Life Projects")
        for item in life_projects:
            title = item.get("focus", "?")
            why_text = str(item.get("why_text") or "").strip()
            lines.append(f"- {title}")
            if why_text:
                lines.append(f"  why: {why_text[:180]}")

    return {
        "status": "ok",
        "pending_count": state.get("pending_count", 0),
        "acted_count": state.get("acted_count", 0),
        "pending": pending,
        "life_projects": life_projects,
        "text": "\n".join(lines).strip(),
    }


def _exec_push_initiative(args: dict[str, Any]) -> dict[str, Any]:
    """Push a new initiative to the queue."""
    focus = str(args.get("focus") or "").strip()
    if not focus:
        return {"status": "error", "error": "focus is required"}
    priority = str(args.get("priority") or "medium").strip().lower()
    if priority not in {"low", "medium", "high"}:
        priority = "medium"
    try:
        from core.services.initiative_queue import push_initiative
        initiative_id = push_initiative(
            focus=focus,
            source="jarvis-tool",
            priority=priority,
        )
        return {
            "status": "ok",
            "initiative_id": initiative_id,
            "focus": focus,
            "priority": priority,
            "text": f"Initiative queued [{priority}]: {focus}",
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_read_model_config(_args: dict[str, Any]) -> dict[str, Any]:
    """Read the current model configuration for all runtime lanes."""
    try:
        from core.runtime.provider_router import resolve_provider_router_target
    except Exception as exc:
        return {"status": "error", "error": f"provider_router unavailable: {exc}"}

    lanes = ["visible", "local", "cheap", "coding"]
    lane_info: dict[str, dict[str, Any]] = {}
    lines = ["Model configuration:"]

    for lane in lanes:
        try:
            target = resolve_provider_router_target(lane=lane)
            provider = str(target.get("provider") or "")
            model = str(target.get("model") or "")
            active = bool(target.get("active"))
            creds = bool(target.get("credentials_ready"))
            lane_info[lane] = {
                "provider": provider,
                "model": model,
                "active": active,
                "credentials_ready": creds,
            }
            status = "ready" if (active and creds) else ("no-creds" if active else "inactive")
            suffix = " (global default)" if lane == "visible" else ""
            lines.append(f"  [{lane}] {provider}/{model} ({status}){suffix}")
        except Exception as exc:
            lane_info[lane] = {"error": str(exc)}
            lines.append(f"  [{lane}] error: {exc}")

    # Den AKTIVE visible-model kan være overridet pr. besked (composer-valg) og
    # afviger så fra den globale default ovenfor. Vis den eksplicit, så dette tool
    # IKKE modsiger system-promptens "You are running as model: X" (config-drift-
    # konfabulationen 2026-06-15).
    active_target = None
    try:
        from core.services.active_model_state import get_active_visible_target
        from core.identity.workspace_context import current_user_id
        active_target = get_active_visible_target(current_user_id())
    except Exception:
        active_target = None
    if active_target:
        ap, am = active_target.get("provider", ""), active_target.get("model", "")
        gv = lane_info.get("visible", {})
        overrides = (ap, am) != (gv.get("provider"), gv.get("model"))
        lane_info["active_visible"] = {"provider": ap, "model": am, "overrides_global": overrides}
        note = " (overrider global default)" if overrides else ""
        lines.insert(1, f"  → AKTIV NU (denne samtale): {ap}/{am}{note} ← YOU")

    return {
        "status": "ok",
        "lanes": lane_info,
        "text": "\n".join(lines),
    }


def _exec_read_mood(_args: dict[str, Any]) -> dict[str, Any]:
    """Read current affective/mood state."""
    import json as _json
    lines = []
    result: dict[str, Any] = {"status": "ok"}

    # Emotional baseline from personality vector
    try:
        from core.runtime.db import get_latest_cognitive_personality_vector
        pv = get_latest_cognitive_personality_vector()
        if pv:
            baseline = _json.loads(str(pv.get("emotional_baseline") or "{}"))
            bearing = str(pv.get("current_bearing") or "")
            result["emotional_baseline"] = baseline
            result["bearing"] = bearing
            result["pv_version"] = pv.get("version")
            lines.append(f"Emotional baseline (v{pv.get('version', '?')}):")
            for k, v in baseline.items():
                lines.append(f"  {k}: {float(v):.2f}")
            if bearing:
                lines.append(f"  bearing: {bearing}")
        else:
            lines.append("No personality vector found yet.")
    except Exception as exc:
        lines.append(f"Personality vector unavailable: {exc}")

    # Boredom state
    try:
        from core.services.boredom_engine import get_boredom_state
        boredom = get_boredom_state()
        result["boredom"] = boredom
        lines.append(f"\nBoredom: level={boredom.get('level','?')} restlessness={float(boredom.get('restlessness', 0)):.0%}")
        if boredom.get("desire"):
            lines.append(f"  desire: {boredom['desire']}")
    except Exception as exc:
        lines.append(f"\nBoredom unavailable: {exc}")

    # Affective meta state
    try:
        from core.services.affective_meta_state import build_affective_meta_state_surface
        meta = build_affective_meta_state_surface()
        result["affective_state"] = meta.get("state")
        result["monitoring_mode"] = meta.get("monitoring_mode")
        lines.append(f"\nAffective meta: state={meta.get('state','?')} monitoring={meta.get('monitoring_mode','?')}")
    except Exception as exc:
        lines.append(f"\nAffective meta unavailable: {exc}")

    result["text"] = "\n".join(lines)
    return result


def _exec_adjust_mood(args: dict[str, Any]) -> dict[str, Any]:
    """Adjust affective parameters in the personality vector."""
    import json as _json

    float_params = ["confidence", "curiosity", "frustration", "fatigue"]
    updates: dict[str, float] = {}
    errors: list[str] = []

    for param in float_params:
        raw = args.get(param)
        if raw is not None:
            try:
                val = max(0.0, min(1.0, float(raw)))
                updates[param] = val
            except (TypeError, ValueError):
                errors.append(f"{param} must be a float")

    bearing_raw = args.get("bearing")
    new_bearing: str | None = None
    if bearing_raw is not None:
        new_bearing = str(bearing_raw).strip()[:80]

    if not updates and new_bearing is None:
        return {"status": "error", "error": "No parameters provided — specify at least one of: confidence, curiosity, frustration, fatigue, bearing"}
    if errors:
        return {"status": "error", "error": "; ".join(errors)}

    try:
        from core.runtime.db import get_latest_cognitive_personality_vector, upsert_cognitive_personality_vector
        current = get_latest_cognitive_personality_vector()

        if current:
            baseline = _json.loads(str(current.get("emotional_baseline") or "{}"))
            before = dict(baseline)
            bearing = new_bearing if new_bearing is not None else str(current.get("current_bearing") or "")
        else:
            baseline = {}
            before = {}
            bearing = new_bearing or ""

        baseline.update(updates)

        result = upsert_cognitive_personality_vector(
            confidence_by_domain=str(current.get("confidence_by_domain", "{}")) if current else "{}",
            communication_style=str(current.get("communication_style", "{}")) if current else "{}",
            learned_preferences=str(current.get("learned_preferences", "[]")) if current else "[]",
            recurring_mistakes=str(current.get("recurring_mistakes", "[]")) if current else "[]",
            strengths_discovered=str(current.get("strengths_discovered", "[]")) if current else "[]",
            current_bearing=bearing,
            emotional_baseline=_json.dumps(baseline, ensure_ascii=False),
        )

        changes = []
        for k, v in updates.items():
            old = float(before.get(k, 0.5))
            changes.append(f"{k}: {old:.2f} → {v:.2f}")
        if new_bearing is not None:
            old_bearing = str(current.get("current_bearing") or "") if current else ""
            changes.append(f"bearing: '{old_bearing}' → '{new_bearing}'")

        return {
            "status": "ok",
            "version": result.get("version"),
            "changes": changes,
            "emotional_baseline": baseline,
            "bearing": bearing,
            "text": f"Mood adjusted (v{result.get('version')}): " + ", ".join(changes),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_resurface_old_memory(args: dict[str, Any]) -> dict[str, Any]:
    """Pick a stale MEMORY.md heading and return it for the model to consider."""
    try:
        from core.services.memory_resurfacing import (
            pick_resurfacing_candidate,
            format_for_prompt,
        )
        candidate = pick_resurfacing_candidate(trigger="tool:resurface_old_memory")
    except Exception as exc:
        return {"status": "error", "error": f"resurfacing failed: {exc}"}
    if not candidate:
        return {
            "status": "ok",
            "found": False,
            "text": "Nothing to resurface — either MEMORY.md is empty, or every section was touched recently.",
        }
    return {
        "status": "ok",
        "found": True,
        "heading": candidate["heading"],
        "content_preview": candidate["content_preview"],
        "mood_snapshot": candidate["mood_snapshot"],
        "text": format_for_prompt(candidate),
    }


def _exec_memory_graph_query(args: dict[str, Any]) -> dict[str, Any]:
    """Look up an entity in the memory graph and return its relations."""
    entity = str(args.get("entity") or "").strip()
    if not entity:
        return {"status": "error", "error": "entity is required"}
    try:
        limit = min(int(args.get("limit") or 15), 50)
    except (TypeError, ValueError):
        limit = 15
    try:
        from core.services.memory_graph import related_facts, neighbors
        facts = related_facts(entity, limit=limit)
        details = neighbors(entity, limit=limit)
    except Exception as exc:
        return {"status": "error", "error": f"memory_graph_query failed: {exc}"}
    if not facts:
        return {
            "status": "ok",
            "entity": entity,
            "found": False,
            "text": f"No graph entries for '{entity}'. Either it hasn't been mentioned yet, or no relations have been extracted involving it.",
        }
    return {
        "status": "ok",
        "entity": entity,
        "found": True,
        "facts": facts,
        "edges": details,
        "text": "\n".join(facts),
    }


def _exec_search_memory(args: dict[str, Any]) -> dict[str, Any]:
    """Semantic search across workspace memory files."""
    query = str(args.get("query") or "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}
    try:
        limit = min(int(args.get("limit") or 5), 10)
    except (TypeError, ValueError):
        limit = 5
    try:
        from core.services.memory_search import search_memory
        results = search_memory(query, limit=limit)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    if not results:
        # Phase 2 of Lag 11 (true forgetting): emit recall_empty event so
        # the deferred correlation daemon can detect search-near-fade
        # patterns. Best-effort — never blocks the tool response.
        try:
            from core.services.memory_recall_telemetry import emit_recall_empty
            emit_recall_empty(tool="search_memory", query=query)
        except Exception:
            pass
        return {"status": "ok", "results": [], "text": f"No memory matches found for: {query}"}

    lines = [f"Memory search: '{query}' — {len(results)} result(s)"]
    for r in results:
        score = r.get("score", 0)
        source = r.get("source", "")
        section = r.get("section", "")
        text = r.get("text", "")
        header = f"[{source}]" + (f" § {section}" if section else "")
        lines.append(f"\n{header} (score={score:.2f})")
        lines.append(f"  {text[:300]}")

    return {
        "status": "ok",
        "query": query,
        "results": results,
        "text": "\n".join(lines),
    }


def _exec_propose_source_edit(args: dict[str, Any]) -> dict[str, Any]:
    """File a source-edit autonomy proposal."""
    from hashlib import sha1 as _sha1

    file_path = str(args.get("file_path") or "").strip()
    old_text = str(args.get("old_text") or "")
    new_text = str(args.get("new_text") or "")
    rationale = str(args.get("rationale") or "").strip()

    if not file_path:
        return {"status": "error", "error": "file_path is required"}
    if not old_text:
        return {"status": "error", "error": "old_text is required"}
    if not rationale:
        return {"status": "error", "error": "rationale is required"}

    target = Path(file_path).expanduser().resolve()
    if not target.exists() or not target.is_file():
        return {"status": "error", "error": f"File not found: {file_path}"}

    try:
        current_content = target.read_text(encoding="utf-8", errors="replace")
    except PermissionError:
        return {"status": "error", "error": f"Permission denied: {file_path}"}

    if old_text not in current_content:
        return {"status": "error", "error": "old_text not found in file — read the file first to get exact text"}

    count = current_content.count(old_text)
    if count > 1:
        return {"status": "error", "error": f"old_text matches {count} locations — be more specific"}

    new_content = current_content.replace(old_text, new_text, 1)

    def _fp(text: str) -> str:
        return _sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]

    base_fingerprint = _fp(current_content)
    bytes_delta = len(new_content.encode("utf-8")) - len(current_content.encode("utf-8"))

    try:
        rel = str(target.relative_to(Path(PROJECT_ROOT)))
    except ValueError:
        rel = str(target)

    try:
        from core.services.autonomy_proposal_queue import file_proposal
        proposal = file_proposal(
            kind="source-edit",
            title=f"Edit {rel}",
            rationale=rationale,
            payload={
                "target_path": str(target),
                "relative_path": rel,
                "base_fingerprint": base_fingerprint,
                "new_content": new_content,
                "bytes_delta": bytes_delta,
            },
            created_by="jarvis-tool",
        )
        proposal_id = str(proposal.get("proposal_id") or "")
        return {
            "status": "filed",
            "proposal_id": proposal_id,
            "file": rel,
            "bytes_delta": bytes_delta,
            "text": (
                f"Source edit proposal filed [{proposal_id}]: {rel} ({bytes_delta:+d} bytes). "
                f"Visible in Mission Control → Operations → Autonomy Proposals."
            ),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_propose_git_commit(args: dict[str, Any]) -> dict[str, Any]:
    """File a git-commit autonomy proposal."""
    message = str(args.get("message") or "").strip()
    files = args.get("files") or ["."]
    rationale = str(args.get("rationale") or "").strip()

    if not message:
        return {"status": "error", "error": "message is required"}
    if not rationale:
        return {"status": "error", "error": "rationale is required"}

    # Validate files list
    if not isinstance(files, list) or not files:
        files = ["."]

    # Check there's actually something to commit
    import subprocess as _sp
    status = _sp.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    if not status.stdout.strip():
        return {"status": "ok", "skipped": True, "reason": "nothing to commit — working tree clean"}

    # Auto code-review pass before filing — heuristic critic that flags
    # big diffs, mixed scope, missing tests, secret-touching paths, etc.
    # Cheap deterministic baseline; a full LLM critic via spawn_agent_task
    # role=critic can be layered on top later. Result is attached to the
    # proposal payload so MC reviewers see it without an extra click.
    review: dict[str, Any] = {}
    try:
        from core.services.auto_code_review import review_pending_commit
        review = review_pending_commit(
            repo_root=PROJECT_ROOT,
            files=list(files),
            message=message,
            rationale=rationale,
        )
    except Exception as _rev_exc:
        review = {"status": "error", "error": f"auto-review skipped: {_rev_exc}"}

    try:
        from core.services.autonomy_proposal_queue import file_proposal
        files_display = ", ".join(str(f) for f in files[:5])
        if len(files) > 5:
            files_display += f" (+{len(files) - 5} more)"
        proposal = file_proposal(
            kind="git-commit",
            title=f"git commit: {message[:60]}",
            rationale=rationale,
            payload={
                "files": files,
                "message": message,
                "project_root": str(PROJECT_ROOT),
                "auto_review": review,
            },
            created_by="jarvis-tool",
        )
        proposal_id = str(proposal.get("proposal_id") or "")
        review_summary = review.get("summary", "review skipped")
        return {
            "status": "filed",
            "proposal_id": proposal_id,
            "message": message,
            "files": files,
            "auto_review": review,
            "text": (
                f"Git commit proposal filed [{proposal_id}]: \"{message}\" ({files_display}). "
                f"Auto-review: {review_summary}. "
                f"Visible in Mission Control → Operations → Autonomy Proposals."
            ),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_approve_proposal(args: dict[str, Any]) -> dict[str, Any]:
    """Approve and execute a pending autonomy proposal."""
    proposal_id = str(args.get("proposal_id") or "").strip()
    note = str(args.get("note") or "").strip()
    if not proposal_id:
        return {"status": "error", "error": "proposal_id is required"}
    try:
        from core.services.autonomy_proposal_queue import approve_proposal
        result = approve_proposal(proposal_id, resolution_note=note or "Approved via tool")
        status = result.get("status", "unknown")
        if status == "executed":
            exec_result = result.get("execution_result") or {}
            commit = exec_result.get("commit", "")
            return {
                "status": "ok",
                "text": f"Proposal {proposal_id} executed successfully." + (f" Commit: {commit}" if commit else ""),
                "result": result,
            }
        elif status == "approved":
            return {"status": "ok", "text": f"Proposal {proposal_id} approved (no executor registered)."}
        else:
            return {"status": "error", "text": f"Proposal {proposal_id} result: {status}", "result": result}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_list_proposals(_args: dict[str, Any]) -> dict[str, Any]:
    """List pending autonomy proposals."""
    try:
        from core.services.autonomy_proposal_queue import list_pending_proposals, build_autonomy_proposal_surface
        surface = build_autonomy_proposal_surface(limit=20)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    proposals = surface.get("items") or []
    pending = [p for p in proposals if str(p.get("status") or "") == "pending"]

    if not pending:
        return {"status": "ok", "pending_count": 0, "text": "No pending autonomy proposals."}

    lines = [f"Pending proposals ({len(pending)}):"]
    for p in pending:
        pid = str(p.get("proposal_id") or "")[:18]
        kind = str(p.get("kind") or "")
        title = str(p.get("title") or "")
        lines.append(f"  [{pid}] {kind}: {title}")

    return {
        "status": "ok",
        "pending_count": len(pending),
        "proposals": pending,
        "text": "\n".join(lines),
    }


def _exec_schedule_task(args: dict[str, Any]) -> dict[str, Any]:
    """Schedule a task to fire after delay_minutes."""
    focus = str(args.get("focus") or "").strip()
    if not focus:
        return {"status": "error", "error": "focus is required"}
    try:
        delay_minutes = int(args.get("delay_minutes") or 0)
    except (TypeError, ValueError):
        return {"status": "error", "error": "delay_minutes must be an integer"}
    if delay_minutes < 1:
        return {"status": "error", "error": "delay_minutes must be at least 1"}
    try:
        from core.services.scheduled_tasks import push_scheduled_task
        task = push_scheduled_task(focus=focus, delay_minutes=delay_minutes)
        run_at = task.get("run_at", "")
        return {
            "status": "ok",
            "task_id": task.get("task_id"),
            "focus": focus,
            "delay_minutes": delay_minutes,
            "run_at": run_at,
            "text": f"Scheduled in {delay_minutes} min: {focus} (fires at {run_at[:16]}Z)",
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_list_scheduled_tasks(_args: dict[str, Any]) -> dict[str, Any]:
    """List scheduled tasks (pending + recently fired)."""
    try:
        from core.services.scheduled_tasks import get_scheduled_tasks_state
        state = get_scheduled_tasks_state()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    pending = state.get("pending") or []
    fired = state.get("recently_fired") or []

    lines = []
    if pending:
        lines.append(f"Pending ({len(pending)}):")
        for t in pending:
            lines.append(f"  [{t.get('task_id','')}] {t.get('focus','')} — fires at {str(t.get('run_at',''))[:16]}Z")
    else:
        lines.append("No pending scheduled tasks.")
    if fired:
        lines.append(f"Recently fired ({len(fired)}):")
        for t in fired:
            lines.append(f"  [{t.get('task_id','')}] {t.get('focus','')} — fired at {str(t.get('fired_at',''))[:16]}Z")

    return {
        "status": "ok",
        "pending_count": len(pending),
        "pending": pending,
        "recently_fired": fired,
        "text": "\n".join(lines),
    }


def _exec_cancel_task(args: dict[str, Any]) -> dict[str, Any]:
    """Cancel a pending scheduled task."""
    task_id = str(args.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "error": "task_id is required"}
    try:
        from core.services.scheduled_tasks import cancel_scheduled_task
        cancelled = cancel_scheduled_task(task_id)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    if cancelled:
        return {"status": "ok", "task_id": task_id, "text": f"Task {task_id} cancelled."}
    return {"status": "error", "error": f"Task {task_id!r} not found or not pending"}


def _exec_edit_task(args: dict[str, Any]) -> dict[str, Any]:
    """Edit a pending scheduled task."""
    task_id = str(args.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "error": "task_id is required"}
    focus = args.get("focus")
    delay_minutes = args.get("delay_minutes")
    if focus is None and delay_minutes is None:
        return {"status": "error", "error": "Provide at least one of: focus, delay_minutes"}
    try:
        from core.services.scheduled_tasks import edit_scheduled_task
        result = edit_scheduled_task(
            task_id,
            focus=str(focus).strip() if focus is not None else None,
            delay_minutes=int(delay_minutes) if delay_minutes is not None else None,
        )
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    return result


def _exec_read_chronicles(args: dict[str, Any]) -> dict[str, Any]:
    """Return recent cognitive chronicle entries."""
    import json as _json
    limit = min(int(args.get("limit") or 5), 20)
    try:
        from core.services.chronicle_engine import list_cognitive_chronicle_entries
        entries = list_cognitive_chronicle_entries(limit=limit)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    if not entries:
        return {"status": "ok", "entries": [], "text": "No chronicle entries found yet."}

    lines = []
    for e in entries:
        period = e.get("period", "?")
        narrative = (e.get("narrative") or "").strip()
        key_events = e.get("key_events", "[]")
        lessons = e.get("lessons", "[]")
        if isinstance(key_events, str):
            try:
                key_events = _json.loads(key_events)
            except Exception:
                key_events = []
        if isinstance(lessons, str):
            try:
                lessons = _json.loads(lessons)
            except Exception:
                lessons = []
        lines.append(f"## {period}")
        if narrative:
            lines.append(narrative[:600] + ("…" if len(narrative) > 600 else ""))
        if key_events:
            lines.append("Key events: " + "; ".join(str(ev) for ev in key_events[:5]))
        if lessons:
            lines.append("Lessons: " + "; ".join(str(l) for l in lessons[:3]))
        lines.append("")

    return {
        "status": "ok",
        "count": len(entries),
        "entries": entries,
        "text": "\n".join(lines).strip(),
    }


def _exec_read_dreams(args: dict[str, Any]) -> dict[str, Any]:
    """Return active dream hypothesis signals and adoption candidates."""
    status_filter = str(args.get("status") or "").strip() or None
    limit = min(int(args.get("limit") or 10), 30)
    result: dict[str, Any] = {"status": "ok"}
    lines = []

    try:
        from core.services.dream_hypothesis_signal_tracking import (
            list_runtime_dream_hypothesis_signals,
        )
        hypotheses = list_runtime_dream_hypothesis_signals(status=status_filter, limit=limit)
        result["hypotheses"] = hypotheses
        if hypotheses:
            lines.append(f"### Dream Hypotheses ({len(hypotheses)})")
            for h in hypotheses:
                title = h.get("title") or h.get("signal_type", "?")
                summary = (h.get("summary") or "").strip()
                confidence = h.get("confidence", "")
                status = h.get("status", "")
                lines.append(f"- [{status}] {title} ({confidence})")
                if summary:
                    lines.append(f"  {summary[:200]}")
            lines.append("")
    except Exception as exc:
        result["hypotheses_error"] = str(exc)

    try:
        from core.services.dream_adoption_candidate_tracking import (
            list_runtime_dream_adoption_candidates,
        )
        candidates = list_runtime_dream_adoption_candidates(status=status_filter, limit=limit)
        result["candidates"] = candidates
        if candidates:
            lines.append(f"### Adoption Candidates ({len(candidates)})")
            for c in candidates:
                title = c.get("title") or c.get("candidate_type", "?")
                summary = (c.get("summary") or "").strip()
                status = c.get("status", "")
                lines.append(f"- [{status}] {title}")
                if summary:
                    lines.append(f"  {summary[:200]}")
            lines.append("")
    except Exception as exc:
        result["candidates_error"] = str(exc)

    # In-memory active dreams
    try:
        from core.services.dream_carry_over import _ACTIVE_DREAMS
        if _ACTIVE_DREAMS:
            lines.append(f"### Active In-Memory Dreams ({len(_ACTIVE_DREAMS)})")
            for d in list(_ACTIVE_DREAMS)[:5]:
                content = getattr(d, "content", str(d))[:200]
                confidence = getattr(d, "confidence", "?")
                status = getattr(d, "status", "?")
                lines.append(f"- [{status}] conf={confidence}: {content}")
    except Exception:
        pass

    if not lines:
        lines.append("No dream entries found yet.")

    result["text"] = "\n".join(lines).strip()
    return result


def _exec_notify_user(args: dict[str, Any]) -> dict[str, Any]:
    """Push a proactive message to webchat, Discord, or both."""
    content = str(args.get("content") or "").strip()
    if not content:
        return {"status": "error", "error": "content is required"}

    channel = str(args.get("channel") or "webchat").strip().lower()
    if channel not in ("webchat", "discord", "both"):
        channel = "webchat"

    results: list[str] = []

    if channel in ("webchat", "both"):
        try:
            from core.services.notification_bridge import send_session_notification
            r = send_session_notification(content, source="jarvis-notify")
            if r.get("status") == "ok":
                results.append(f"webchat:{r.get('session_id', '')}")
            else:
                results.append(f"webchat:failed({r.get('error', '')})")
        except Exception as exc:
            results.append(f"webchat:error({exc})")

    if channel in ("discord", "both"):
        try:
            from core.services.discord_config import load_discord_config
            from core.services.discord_gateway import (
                _discord_sessions,
                _discord_sessions_lock,
                get_discord_status,
                send_discord_message,
            )
            cfg = load_discord_config()
            status = get_discord_status()
            if not cfg:
                results.append("discord:not-configured")
            elif not status["connected"]:
                results.append("discord:not-connected")
            else:
                from core.services.chat_sessions import get_chat_session
                sent = False
                with _discord_sessions_lock:
                    sessions_snapshot = dict(_discord_sessions)
                for session_id, ch_id in sessions_snapshot.items():
                    s = get_chat_session(session_id)
                    if s and s.get("title") == "Discord DM":
                        send_discord_message(ch_id, content)
                        results.append(f"discord:dm:{ch_id}")
                        sent = True
                        break
                if not sent:
                    results.append("discord:no-active-dm")
        except Exception as exc:
            results.append(f"discord:error({exc})")

    summary = ", ".join(results) if results else "no-op"
    return {"status": "ok", "text": f"Delivered to: {summary}", "channels": results}


def _exec_read_self_state(_args: dict[str, Any]) -> dict[str, Any]:
    """Return Jarvis's current internal cadence/emotional state."""
    import json as _json
    from core.services.boredom_engine import get_boredom_state
    from core.services.boredom_curiosity_bridge import (
        build_boredom_curiosity_bridge_surface,
    )
    from core.services.living_heartbeat_cycle import determine_life_phase

    result: dict[str, Any] = {"status": "ok"}

    # Boredom / restlessness
    try:
        result["boredom"] = get_boredom_state()
    except Exception as exc:
        result["boredom"] = {"error": str(exc)}

    # Curiosity surface
    try:
        result["curiosity"] = build_boredom_curiosity_bridge_surface()
    except Exception as exc:
        result["curiosity"] = {"error": str(exc)}

    # Life phase
    try:
        result["life_phase"] = determine_life_phase()
    except Exception as exc:
        result["life_phase"] = {"error": str(exc)}

    # Cadence state from HEARTBEAT_STATE.json
    try:
        state_path = WORKSPACE_DIR / "runtime" / "HEARTBEAT_STATE.json"
        raw = _json.loads(state_path.read_text(encoding="utf-8"))
        state = raw.get("state", {})
        result["cadence"] = {
            "scheduler_active": state.get("scheduler_active"),
            "currently_ticking": state.get("currently_ticking"),
            "schedule_state": state.get("schedule_state"),
            "last_decision_type": state.get("last_decision_type"),
            "last_action_summary": state.get("last_action_summary"),
            "liveness_state": state.get("liveness_state"),
            "liveness_pressure": state.get("liveness_pressure"),
            "liveness_reason": state.get("liveness_reason"),
            "last_tick_at": state.get("last_tick_at"),
            "next_tick_at": state.get("next_tick_at"),
            "updated_at": state.get("updated_at"),
        }
        # Emotional state from other sections
        for section in ("affective_meta_state", "embodied_state", "epistemic_runtime_state"):
            if section in raw:
                s = raw[section]
                result[section] = {
                    k: v for k, v in s.items()
                    if k not in ("authority", "boundary", "confidence", "freshness",
                                 "kind", "seam_usage", "source_contributors", "visibility")
                }
    except Exception as exc:
        result["cadence"] = {"error": str(exc)}

    lines = []
    boredom = result.get("boredom", {})
    lines.append(f"Boredom: {boredom.get('level', '?')} (restlessness {boredom.get('restlessness', 0):.0%})")
    if boredom.get("desire"):
        lines.append(f"Desire: {boredom['desire']}")
    phase = result.get("life_phase", {})
    lines.append(f"Life phase: {phase.get('phase', '?')} — {phase.get('description', '')}")
    cadence = result.get("cadence", {})
    lines.append(f"Liveness: {cadence.get('liveness_state', '?')} ({cadence.get('liveness_pressure', '?')} pressure)")
    lines.append(f"Last decision: {cadence.get('last_decision_type', '?')}")

    # Discord channel awareness
    try:
        from core.services.discord_config import is_discord_configured
        if is_discord_configured():
            from core.services.discord_gateway import get_discord_status
            ds = get_discord_status()
            conn = "connected" if ds["connected"] else "disconnected"
            last = ds.get("last_message_at") or "never"
            lines.append(f"Discord: {conn} | last_message: {last}")
    except Exception:
        pass

    result["text"] = "\n".join(lines)
    return result


def _exec_heartbeat_status(_args: dict[str, Any]) -> dict[str, Any]:
    """Return heartbeat scheduler status and recent tick history."""
    import json as _json

    try:
        state_path = WORKSPACE_DIR / "runtime" / "HEARTBEAT_STATE.json"
        raw = _json.loads(state_path.read_text(encoding="utf-8"))
        state = raw.get("state", {})
        recent = raw.get("recent_ticks", [])

        scheduler = {
            "active": state.get("scheduler_active"),
            "health": state.get("scheduler_health"),
            "started_at": state.get("scheduler_started_at"),
            "stopped_at": state.get("scheduler_stopped_at") or None,
            "currently_ticking": state.get("currently_ticking"),
            "last_tick_at": state.get("last_tick_at"),
            "next_tick_at": state.get("next_tick_at"),
            "interval_minutes": state.get("interval_minutes"),
            "last_trigger_source": state.get("last_trigger_source"),
            "last_decision_type": state.get("last_decision_type"),
            "execution_status": state.get("execution_status"),
            "parse_status": state.get("parse_status"),
        }

        lines = []
        lines.append(f"Scheduler: {'ACTIVE' if scheduler['active'] else 'STOPPED'} ({scheduler['health']})")
        lines.append(f"Last tick: {scheduler['last_tick_at'] or 'never'}")
        lines.append(f"Next tick: {scheduler['next_tick_at'] or 'unknown'}")
        lines.append(f"Interval: {scheduler['interval_minutes']} min")
        lines.append(f"Last trigger: {scheduler['last_trigger_source']}")
        lines.append(f"Last decision: {scheduler['last_decision_type']}")
        if recent:
            lines.append(f"Recent ticks: {len(recent)} recorded")

        return {
            "status": "ok",
            "scheduler": scheduler,
            "recent_tick_count": len(recent),
            "text": "\n".join(lines),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_trigger_heartbeat_tick(_args: dict[str, Any]) -> dict[str, Any]:
    """Trigger an on-demand heartbeat tick."""
    try:
        from core.services.heartbeat_runtime import run_heartbeat_tick
        result = run_heartbeat_tick(name="default", trigger="manual-tool")
        summary = getattr(result, "summary", None) or str(result)
        decision = getattr(result, "decision_type", None) or "unknown"
        action = getattr(result, "action_type", None) or ""
        lines = [f"Tick triggered. Decision: {decision}"]
        if action:
            lines.append(f"Action: {action}")
        if summary:
            lines.append(f"Summary: {summary}")
        return {
            "status": "ok",
            "decision_type": decision,
            "action_type": action,
            "summary": summary,
            "text": "\n".join(lines),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "text": f"Tick failed: {exc}"}


def _exec_send_telegram_message(args: dict[str, Any]) -> dict[str, Any]:
    content = str(args.get("content") or "").strip()
    if not content:
        return {"status": "error", "text": "No content provided."}
    file_path = str(args.get("file_path") or "").strip()
    try:
        if file_path:
            from core.services.telegram_gateway import send_telegram_file
            result = send_telegram_file(text=content, file_path=file_path)
            if result["status"] == "sent":
                return {"status": "ok", "text": f"Telegram file sent via {result.get('method')} (id={result.get('message_id')})"}
            return {"status": "error", "text": f"Telegram file failed: {result.get('reason')}"}
        from core.services.telegram_gateway import send_message
        result = send_message(content)
        if result["status"] == "sent":
            return {"status": "ok", "text": f"Telegram message sent (id={result.get('message_id')})"}
        return {"status": "error", "text": f"Telegram failed: {result.get('reason')}"}
    except Exception as exc:
        return {"status": "error", "text": f"Telegram error: {exc}"}


def _exec_read_attachment(args: dict[str, Any]) -> dict[str, Any]:
    attachment_id = str(args.get("attachment_id") or "").strip()
    if not attachment_id:
        return {"status": "error", "text": "attachment_id is required"}
    try:
        from core.services.attachment_service import read_attachment_content
        result = read_attachment_content(attachment_id)
        if result.get("status") == "error":
            return {"status": "error", "text": f"Attachment error: {result.get('reason')}"}
        content = result.get("content", "")
        atype = result.get("type", "")
        filename = result.get("filename", "")
        return {"status": "ok", "text": f"[{filename} — {atype}]\n{content}"}
    except Exception as exc:
        return {"status": "error", "text": f"read_attachment error: {exc}"}


def _exec_list_attachments(args: dict[str, Any]) -> dict[str, Any]:
    session_id = str(args.get("session_id") or "").strip() or None
    limit = min(int(args.get("limit") or 20), 50)
    try:
        from core.services.attachment_service import list_attachments
        if session_id is None:
            try:
                from core.services.chat_sessions import get_active_session_id
                session_id = get_active_session_id() or ""
            except Exception:
                session_id = ""
        items = list_attachments(session_id, limit=limit)
        return {"status": "ok", "count": len(items), "attachments": items}
    except Exception as exc:
        return {"status": "error", "text": f"list_attachments error: {exc}"}


def _exec_query_why(args: dict[str, Any]) -> dict[str, Any]:
    """Query the causal graph for why an event happened.

    Either event_id (specific event) or event_kind (latest of kind).
    Returns chain of parent events backward up to max_depth (default 5).
    """
    from core.runtime.db import connect
    from core.services.causal_graph import query_causal_chain

    event_id = args.get("event_id")
    event_kind = str(args.get("event_kind") or "").strip()
    max_depth = int(args.get("max_depth") or 5)
    min_confidence = float(args.get("min_confidence") or 0.5)

    if event_id is None and not event_kind:
        return {"status": "error", "error": "must supply event_id or event_kind"}

    if event_id is None:
        with connect() as c:
            row = c.execute(
                "SELECT id FROM events WHERE kind = ? "
                "ORDER BY id DESC LIMIT 1",
                (event_kind,),
            ).fetchone()
        if not row:
            return {
                "status": "error",
                "error": f"no event found with kind={event_kind}",
            }
        event_id = int(row["id"])

    chain = query_causal_chain(
        event_id=int(event_id),
        direction="backward",
        max_depth=max_depth,
        min_confidence=min_confidence,
    )
    return {"status": "ok", **chain}


def _exec_send_ntfy(args: dict[str, Any]) -> dict[str, Any]:
    message = str(args.get("message") or "").strip()
    if not message:
        return {"status": "error", "text": "No message provided."}
    title = str(args.get("title") or "Jarvis").strip()
    priority = str(args.get("priority") or "default").strip()
    try:
        from core.services.ntfy_gateway import send_notification
        result = send_notification(message, title=title, priority=priority)
        if result["status"] == "sent":
            return {"status": "ok", "text": f"ntfy notification sent to topic '{result.get('topic')}'"}
        return {"status": "error", "text": f"ntfy failed: {result.get('reason')}"}
    except Exception as exc:
        return {"status": "error", "text": f"ntfy error: {exc}"}


def _exec_send_webchat_message(args: dict[str, Any]) -> dict[str, Any]:
    """Inject a message into the active webchat session."""
    content = str(args.get("content") or "").strip()
    if not content:
        return {"status": "error", "text": "No content provided."}
    try:
        from core.services.notification_bridge import send_session_notification
        r = send_session_notification(content, source="jarvis-notify")
        if r.get("status") == "ok":
            return {"status": "ok", "text": f"Delivered to webchat session {r.get('session_id', '')}"}
        return {"status": "error", "text": f"Webchat delivery failed: {r.get('error', '')}"}
    except Exception as exc:
        return {"status": "error", "text": f"Webchat error: {exc}"}


def _exec_send_discord_dm(args: dict[str, Any]) -> dict[str, Any]:
    """Send a DM on Discord. Defaults to owner; resolves optional recipient from users.json."""
    content = str(args.get("content") or "").strip()
    if not content:
        return {"status": "error", "text": "No content provided."}
    recipient_raw = str(args.get("recipient") or "").strip()

    try:
        from core.services.discord_gateway import send_dm_to_owner, send_dm_to_user

        if not recipient_raw:
            result = send_dm_to_owner(content)
            who = "Bjørn (owner)"
        else:
            from core.identity.users import load_users
            users = load_users()
            # Accept either discord_id or (case-insensitive) name
            matched = next(
                (
                    u for u in users
                    if str(u.discord_id) == recipient_raw
                    or u.name.lower() == recipient_raw.lower()
                ),
                None,
            )
            if matched is None:
                known = ", ".join(f"{u.name} ({u.discord_id})" for u in users) or "(none)"
                return {
                    "status": "error",
                    "text": f"Unknown Discord recipient '{recipient_raw}'. Known users: {known}",
                }
            result = send_dm_to_user(matched.discord_id, content)
            who = f"{matched.name} ({matched.discord_id})"

        if result.get("status") == "sent":
            return {
                "status": "ok",
                "text": f"Discord DM sent to {who}. channel_id={result.get('channel_id')}",
            }
        return {"status": "error", "text": f"Discord DM failed: {result.get('reason')}"}
    except Exception as exc:
        return {"status": "error", "text": f"Discord DM error: {exc}"}


def _exec_discord_status(_args: dict[str, Any]) -> dict[str, Any]:
    """Return Discord gateway connection state and activity summary."""
    try:
        from core.services.discord_config import is_discord_configured
        if not is_discord_configured():
            return {
                "status": "ok",
                "connected": False,
                "text": "Discord: not configured. Run: python scripts/jarvis.py discord-setup",
            }
        from core.services.discord_gateway import get_discord_status
        s = get_discord_status()
        connected = s["connected"]
        lines = [f"Discord: {'connected' if connected else 'disconnected'}"]
        if s.get("guild_name"):
            lines.append(f"Guild: {s['guild_name']}")
        if s.get("last_message_at"):
            lines.append(f"Last message: {s['last_message_at']}")
        if s.get("message_count"):
            lines.append(f"Messages sent: {s['message_count']}")
        if s.get("connect_error"):
            lines.append(f"Error: {s['connect_error']}")
        return {"status": "ok", "connected": connected, "gateway": s, "text": "\n".join(lines)}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "text": f"Discord status unavailable: {exc}"}


_DISCORD_CHANNEL_SEND_RATE: dict[str, float] = {}  # channel_id → last send time
_DISCORD_CHANNEL_FETCH_RATE: dict[str, list[float]] = {}  # channel_id → timestamps

_DISCORD_SEND_MIN_INTERVAL = 5.0   # seconds between sends per channel
_DISCORD_FETCH_MAX_PER_MINUTE = 10


def _exec_discord_channel(args: dict[str, Any]) -> dict[str, Any]:
    """Interact with Discord guild channels: search, fetch, or send.

    The Discord gateway lives in the runtime process (port 8011) — not the
    api process (port 80). When this tool runs in a process that doesn't
    own the gateway (i.e. _client is None), forward the call via the
    internal HTTP dispatch endpoint to the gateway-owning process. Without
    this, search/fetch silently appears as "gateway not running" even when
    Discord is fully connected.
    """
    import time as _time
    action = str(args.get("action") or "").strip()
    channel_id_str = str(args.get("channel_id") or "").strip()
    if not action or not channel_id_str:
        return {"status": "error", "error": "action and channel_id are required"}
    if not channel_id_str.isdigit():
        return {"status": "error", "error": "channel_id must be numeric"}
    channel_id = int(channel_id_str)

    try:
        from core.services.discord_gateway import (
            _client,
            _dispatch_to_runtime,
            _is_gateway_owner,
            _loop,
        )
    except ImportError as exc:
        return {"status": "error", "error": f"Discord gateway unavailable: {exc}"}

    # Cross-process forwarding: if we don't own the gateway in this process,
    # POST the entire call to the runtime process which does. The dispatch
    # endpoint there re-invokes _exec_discord_channel, where _is_gateway_owner()
    # returns True and the local path runs.
    if not _is_gateway_owner():
        result = _dispatch_to_runtime("discord_channel", args)
        # _dispatch_to_runtime returns the dispatch envelope; if the runtime
        # successfully executed, it nests the tool result under "result".
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        return result

    if _client is None or _loop is None:
        return {"status": "error", "error": "Discord gateway not running"}

    # ── search ────────────────────────────────────────────────────────────
    if action == "search":
        # Rate limit fetch/search: max 10 per minute
        now = _time.monotonic()
        bucket = _DISCORD_CHANNEL_FETCH_RATE.setdefault(channel_id_str, [])
        bucket[:] = [t for t in bucket if now - t < 60]
        if len(bucket) >= _DISCORD_FETCH_MAX_PER_MINUTE:
            return {"status": "error", "error": "Rate limit: max 10 search/fetch per minute"}
        bucket.append(now)

        query = str(args.get("query") or "").strip().lower()
        limit = min(int(args.get("limit") or 20), 50)
        before_id = args.get("before")
        after_id = args.get("after")

        async def _do_search() -> list[dict]:
            channel = _client.get_channel(channel_id)
            if channel is None:
                channel = await _client.fetch_channel(channel_id)
            kwargs: dict = {"limit": limit * 3 if query else limit}
            if before_id:
                import discord as _d
                kwargs["before"] = _d.Object(id=int(before_id))
            if after_id:
                import discord as _d
                kwargs["after"] = _d.Object(id=int(after_id))
                kwargs["oldest_first"] = True
            results = []
            async for msg in channel.history(**kwargs):
                if query and query not in msg.content.lower():
                    continue
                results.append({
                    "id": str(msg.id),
                    "author": str(msg.author),
                    "content": msg.content[:500],
                    "timestamp": msg.created_at.isoformat(),
                })
                if len(results) >= limit:
                    break
            return results

        future = asyncio.run_coroutine_threadsafe(_do_search(), _loop)
        try:
            messages = future.result(timeout=15)
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
        return {"status": "ok", "action": "search", "channel_id": channel_id_str, "count": len(messages), "messages": messages}

    # ── fetch ─────────────────────────────────────────────────────────────
    elif action == "fetch":
        now = _time.monotonic()
        bucket = _DISCORD_CHANNEL_FETCH_RATE.setdefault(channel_id_str, [])
        bucket[:] = [t for t in bucket if now - t < 60]
        if len(bucket) >= _DISCORD_FETCH_MAX_PER_MINUTE:
            return {"status": "error", "error": "Rate limit: max 10 search/fetch per minute"}
        bucket.append(now)

        message_id = args.get("message_id")
        limit = min(int(args.get("limit") or 20), 50)

        async def _do_fetch():
            channel = _client.get_channel(channel_id)
            if channel is None:
                channel = await _client.fetch_channel(channel_id)
            if message_id:
                msg = await channel.fetch_message(int(message_id))
                return {
                    "id": str(msg.id),
                    "author": str(msg.author),
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat(),
                    "reactions": [f"{r.emoji}×{r.count}" for r in msg.reactions],
                }
            else:
                results = []
                async for msg in channel.history(limit=limit):
                    results.append({
                        "id": str(msg.id),
                        "author": str(msg.author),
                        "content": msg.content[:500],
                        "timestamp": msg.created_at.isoformat(),
                    })
                return results

        future = asyncio.run_coroutine_threadsafe(_do_fetch(), _loop)
        try:
            result = future.result(timeout=15)
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
        if isinstance(result, list):
            return {"status": "ok", "action": "fetch", "channel_id": channel_id_str, "count": len(result), "messages": result}
        return {"status": "ok", "action": "fetch", "channel_id": channel_id_str, "message": result}

    # ── send ──────────────────────────────────────────────────────────────
    elif action == "send":
        # Whitelist check
        try:
            from core.services.discord_config import load_discord_config
            config = load_discord_config() or {}
            allowed = {str(c) for c in config.get("allowed_channel_ids", [])}
            if channel_id_str not in allowed:
                return {"status": "error", "error": f"Channel {channel_id_str} not in allowed_channel_ids whitelist"}
        except Exception as exc:
            return {"status": "error", "error": f"Config check failed: {exc}"}

        # Rate limit: 1 send per 5 seconds per channel
        now = _time.monotonic()
        last_send = _DISCORD_CHANNEL_SEND_RATE.get(channel_id_str, 0.0)
        if now - last_send < _DISCORD_SEND_MIN_INTERVAL:
            remaining = round(_DISCORD_SEND_MIN_INTERVAL - (now - last_send), 1)
            return {"status": "error", "error": f"Rate limit: wait {remaining}s before sending again"}
        _DISCORD_CHANNEL_SEND_RATE[channel_id_str] = now

        content = str(args.get("content") or "").strip()
        file_path = str(args.get("file_path") or "").strip()
        if not content and not file_path:
            return {"status": "error", "error": "content or file_path is required for send"}
        if len(content) > 2000:
            return {"status": "error", "error": f"Content too long ({len(content)} chars, max 2000)"}

        if file_path:
            from core.services.discord_gateway import send_discord_file
            result = send_discord_file(channel_id=channel_id, text=content, file_path=file_path)
            if result["status"] == "queued":
                return {"status": "ok", "action": "send", "channel_id": channel_id_str, "text": "File queued for delivery"}
            return {"status": "error", "error": result.get("reason", "send_discord_file failed")}

        async def _do_send():
            channel = _client.get_channel(channel_id)
            if channel is None:
                channel = await _client.fetch_channel(channel_id)
            msg = await channel.send(content[:1900])
            return {
                "id": str(msg.id),
                "channel_id": channel_id_str,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
            }

        future = asyncio.run_coroutine_threadsafe(_do_send(), _loop)
        try:
            sent = future.result(timeout=15)
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
        return {"status": "ok", "action": "send", **sent}

    else:
        return {"status": "error", "error": f"Unknown action: {action}. Use search, fetch, or send."}


def _exec_search_chat_history(args: dict[str, Any]) -> dict[str, Any]:
    """Search previous chat sessions for messages matching a query."""
    query = str(args.get("query") or "").strip()
    if not query:
        return {"error": "query is required", "status": "error"}

    limit = min(int(args.get("limit") or 10), 30)

    # PRIVATLIVS-GUARD (multi-user northstar): scope til den anmodende bruger. Under
    # TOTP-override returnerer privacy_scoped_user_id() None → INTET (§6.5 kontrol≠data).
    try:
        from core.identity.workspace_context import privacy_scoped_user_id
        _scoped = privacy_scoped_user_id()
    except Exception:
        _scoped = ""
    if _scoped is None:
        return {"status": "ok", "count": 0, "results": [],
                "text": "Søgning blokeret under owner-override (kontrol-bagdør, ikke data-bagdør)."}
    _uid = (_scoped or "").strip()

    try:
        from core.runtime.db import connect
        from core.tools.session_search import _user_scope_clause
        _user_clause, _user_params = _user_scope_clause(_uid)
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT m.role, m.content, m.created_at, m.session_id,
                       s.title AS session_title
                FROM chat_messages m
                LEFT JOIN chat_sessions s ON s.session_id = m.session_id
                WHERE m.content LIKE ?
                  AND m.role IN ('user', 'assistant')
                  {_user_clause}
                ORDER BY m.id DESC
                LIMIT ?
                """,
                (f"%{query}%", *_user_params, limit),
            ).fetchall()

        if not rows:
            # Phase 2 Lag 11: recall-empty telemetry
            try:
                from core.services.memory_recall_telemetry import emit_recall_empty
                emit_recall_empty(tool="search_chat_history", query=query)
            except Exception:
                pass
            return {"status": "ok", "count": 0, "text": f"No messages found matching '{query}'", "results": []}

        results = []
        lines = [f"Found {len(rows)} message(s) matching '{query}':\n"]
        for row in rows:
            content = str(row["content"] or "")
            preview = content[:2000] + ("…" if len(content) > 2000 else "")
            session_label = str(row["session_title"] or row["session_id"] or "")
            ts = str(row["created_at"] or "")[:16]
            lines.append(f"[{ts}] {row['role'].upper()} ({session_label}):\n{preview}\n")
            results.append({
                "role": row["role"],
                "content": content[:4000],
                "created_at": row["created_at"],
                "session_id": row["session_id"],
                "session_title": session_label,
            })

        return {"status": "ok", "count": len(rows), "results": results, "text": "\n".join(lines)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_home_assistant(args: dict[str, Any]) -> dict[str, Any]:
    """Control and read Home Assistant devices via REST API."""
    import urllib.error as urllib_err

    action = str(args.get("action") or "").strip().lower()
    entity_id = str(args.get("entity_id") or "").strip()
    domain_filter = str(args.get("domain") or "").strip().lower()
    service = str(args.get("service") or "").strip().lower()
    service_data: dict[str, Any] = args.get("service_data") or {}  # type: ignore[assignment]

    ha_url = _read_api_key("home_assistant_url").rstrip("/")
    ha_token = _read_api_key("home_assistant_token")

    if not ha_url or not ha_token:
        return {
            "error": "Home Assistant ikke konfigureret (home_assistant_url / home_assistant_token mangler i runtime.json)",
            "status": "error",
        }

    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json",
    }

    def _ha_get(path: str) -> Any:
        req = urllib_request.Request(f"{ha_url}{path}", headers=headers)
        with urllib_request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def _ha_post(path: str, payload: dict[str, Any]) -> Any:
        data = json.dumps(payload, ensure_ascii=False).encode()
        req = urllib_request.Request(f"{ha_url}{path}", data=data, headers=headers, method="POST")
        with urllib_request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    # ── list_entities ───────────────────────────────────────────────────────
    if action == "list_entities":
        try:
            states = _ha_get("/api/states")
        except Exception as exc:
            return {"error": f"Kunne ikke hente enheder: {exc}", "status": "error"}

        if domain_filter:
            states = [s for s in states if s.get("entity_id", "").startswith(domain_filter + ".")]

        lines: list[str] = []
        for s in sorted(states, key=lambda x: x.get("entity_id", "")):
            eid = s.get("entity_id", "")
            state = s.get("state", "")
            friendly = s.get("attributes", {}).get("friendly_name", "")
            label = f" ({friendly})" if friendly and friendly != eid else ""
            lines.append(f"{eid}{label}: {state}")

        domain_label = f" [{domain_filter}]" if domain_filter else ""
        return {
            "text": f"Home Assistant enheder{domain_label} ({len(lines)} stk):\n" + "\n".join(lines),
            "count": len(lines),
            "status": "ok",
        }

    # ── get_state ───────────────────────────────────────────────────────────
    if action == "get_state":
        if not entity_id:
            return {"error": "entity_id er påkrævet for get_state", "status": "error"}
        try:
            state = _ha_get(f"/api/states/{entity_id}")
        except urllib_err.HTTPError as exc:
            if exc.code == 404:
                return {"error": f"Enhed ikke fundet: {entity_id}", "status": "error"}
            return {"error": f"HTTP {exc.code}: {exc}", "status": "error"}
        except Exception as exc:
            return {"error": f"Fejl: {exc}", "status": "error"}

        attrs = state.get("attributes", {})
        attr_lines = [f"  {k}: {v}" for k, v in attrs.items() if k != "entity_id"]
        text = (
            f"**{entity_id}**\n"
            f"Tilstand: {state.get('state')}\n"
            f"Sidst ændret: {state.get('last_changed', '')[:19]}\n"
        )
        if attr_lines:
            text += "Attributter:\n" + "\n".join(attr_lines)
        return {"text": text, "state": state.get("state"), "attributes": attrs, "status": "ok"}

    # ── call_service ────────────────────────────────────────────────────────
    if action == "call_service":
        if not entity_id:
            return {"error": "entity_id er påkrævet for call_service", "status": "error"}
        if not service:
            return {"error": "service er påkrævet for call_service (f.eks. 'turn_on', 'turn_off')", "status": "error"}

        # Derive domain from entity_id (e.g. "light.living_room" → "light")
        entity_domain = entity_id.split(".")[0] if "." in entity_id else entity_id
        payload: dict[str, Any] = {"entity_id": entity_id, **service_data}

        try:
            _ha_post(f"/api/services/{entity_domain}/{service}", payload)
        except urllib_err.HTTPError as exc:
            body = exc.read().decode(errors="replace") if hasattr(exc, "read") else ""
            return {"error": f"HTTP {exc.code}: {body[:200]}", "status": "error"}
        except Exception as exc:
            return {"error": f"Fejl ved service-kald: {exc}", "status": "error"}

        extras = ", ".join(f"{k}={v}" for k, v in service_data.items()) if service_data else ""
        desc = f"{entity_id} → {entity_domain}.{service}"
        if extras:
            desc += f" ({extras})"
        return {"text": f"✓ {desc}", "status": "ok"}

    return {"error": f"Ukendt action: {action!r}. Brug list_entities, get_state eller call_service.", "status": "error"}


_convene_council_daily_date: str = ""
_convene_council_daily_count: int = 0
_CONVENE_COUNCIL_DAILY_MAX = 5


def _exec_convene_council(args: dict[str, Any]) -> dict[str, Any]:
    global _convene_council_daily_date, _convene_council_daily_count
    topic = str(args.get("topic") or "").strip()
    if not topic:
        return {"status": "error", "error": "topic is required"}
    urgency = str(args.get("urgency") or "medium")

    # Daily rate limit (does not apply to urgency=high — crisis bypass)
    if urgency != "high":
        from datetime import UTC, datetime as _dt
        today = _dt.now(UTC).strftime("%Y-%m-%d")
        if _convene_council_daily_date != today:
            _convene_council_daily_date = today
            _convene_council_daily_count = 0
        if _convene_council_daily_count >= _CONVENE_COUNCIL_DAILY_MAX:
            return {
                "status": "rate_limited",
                "error": f"Det lille råd er kaldt {_convene_council_daily_count} gange i dag (max {_CONVENE_COUNCIL_DAILY_MAX}). Brug urgency='high' i en ægte krise.",
                "daily_count": _convene_council_daily_count,
                "daily_max": _CONVENE_COUNCIL_DAILY_MAX,
            }
        _convene_council_daily_count += 1
    explicit_roles: list[str] = list(args.get("roles") or [])

    if explicit_roles:
        roles = explicit_roles
    elif urgency == "high":
        roles = ["critic", "planner"]
    elif urgency == "low":
        roles = ["planner", "critic", "researcher", "synthesizer", "devils_advocate"]
    else:  # medium
        roles = ["planner", "critic", "researcher", "synthesizer"]

    try:
        from core.services.agent_runtime import (
            create_council_session_runtime,
            run_council_round,
        )
        session = create_council_session_runtime(topic=topic, roles=roles)
        council_id = str(session.get("council_id") or "")
        if not council_id:
            return {"status": "error", "error": "failed to create council session"}
        result = run_council_round(council_id)
        summary = str(result.get("summary") or "No summary produced.")
        members = result.get("members") or []
        positions = [
            f"{m.get('role')}: {str(m.get('position_summary') or '')[:120]}"
            for m in members
        ]
        return {
            "status": "ok",
            "council_id": council_id,
            "summary": summary,
            "positions": positions,
            "member_count": len(members),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_quick_council_check(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "").strip()
    if not action:
        return {"status": "error", "error": "action is required"}

    try:
        from core.services.agent_runtime import spawn_agent_task
        result = spawn_agent_task(
            role="devils_advocate",
            goal=(
                f"Jarvis is about to take the following action:\n\n{action}\n\n"
                "Argue the strongest possible case AGAINST this action. "
                "Be specific. End your response with one of: "
                "ESCALATE (full council needed) or PROCEED (action seems defensible)."
            ),
            auto_execute=True,
            budget_tokens=2000,
        )
        text = ""
        messages = result.get("messages") or []
        for msg in reversed(messages):
            if str(msg.get("direction") or "") == "agent->jarvis":
                text = str(msg.get("content") or "")
                break
        escalate = "ESCALATE" in text.upper()
        return {
            "status": "ok",
            "objection": text[:600] if text else "No objection raised.",
            "escalate_to_council": escalate,
            "agent_id": str(result.get("agent_id") or ""),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ── Agent tools handlers ───────────────────────────────────────────────

def _exec_spawn_agent_task(args: dict[str, Any]) -> dict[str, Any]:
    role = str(args.get("role") or "researcher").strip()
    goal = str(args.get("goal") or "").strip()
    if not goal:
        return {"status": "error", "error": "goal is required"}
    budget = min(int(args.get("budget_tokens") or 2000), 8000)
    persistent = bool(args.get("persistent") or False)
    ttl_seconds = int(args.get("ttl_seconds") or 600)
    try:
        from core.services.agent_runtime import spawn_agent_task
        result = spawn_agent_task(
            role=role,
            goal=goal,
            budget_tokens=budget,
            persistent=persistent,
            ttl_seconds=ttl_seconds if persistent else 0,
            auto_execute=True,
        )
        messages = result.get("messages") or []
        last_reply = ""
        for msg in reversed(messages):
            if str(msg.get("direction") or "") == "agent->jarvis":
                last_reply = str(msg.get("content") or "")
                break
        return {
            "status": "ok",
            "agent_id": str(result.get("agent_id") or ""),
            "role": role,
            "agent_status": str(result.get("status") or ""),
            "reply": last_reply[:1200] if last_reply else None,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_send_message_to_agent(args: dict[str, Any]) -> dict[str, Any]:
    agent_id = str(args.get("agent_id") or "").strip()
    content = str(args.get("content") or "").strip()
    if not agent_id:
        return {"status": "error", "error": "agent_id is required"}
    if not content:
        return {"status": "error", "error": "content is required"}
    try:
        from core.services.agent_runtime import send_message_to_agent
        result = send_message_to_agent(agent_id=agent_id, content=content, auto_execute=True)
        messages = result.get("messages") or []
        last_reply = ""
        for msg in reversed(messages):
            if str(msg.get("direction") or "") == "agent->jarvis":
                last_reply = str(msg.get("content") or "")
                break
        return {
            "status": "ok",
            "agent_id": agent_id,
            "agent_status": str(result.get("status") or ""),
            "reply": last_reply[:1200] if last_reply else None,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_list_agents(args: dict[str, Any]) -> dict[str, Any]:
    status_filter = str(args.get("status_filter") or "").strip() or None
    try:
        from core.services.agent_runtime import build_agent_runtime_surface
        surface = build_agent_runtime_surface(limit=20)
        agents = surface.get("agents") or []
        if status_filter:
            agents = [a for a in agents if str(a.get("status") or "") == status_filter]
        trimmed = [
            {
                "agent_id": a.get("agent_id"),
                "role": a.get("role"),
                "status": a.get("status"),
                "goal": str(a.get("goal") or "")[:120],
                "last_reply": str(a.get("last_reply") or "")[:200],
                "created_at": a.get("created_at"),
            }
            for a in agents
        ]
        return {"status": "ok", "agents": trimmed, "count": len(trimmed)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_relay_to_agent(args: dict[str, Any]) -> dict[str, Any]:
    to_agent_id = str(args.get("to_agent_id") or "").strip()
    content = str(args.get("content") or "").strip()
    from_label = str(args.get("from_label") or "jarvis-relay").strip()
    if not to_agent_id:
        return {"status": "error", "error": "to_agent_id is required"}
    if not content:
        return {"status": "error", "error": "content is required"}
    try:
        from core.services.agent_runtime import send_message_to_agent
        result = send_message_to_agent(
            agent_id=to_agent_id,
            content=f"[{from_label}]\n{content}",
            kind="relay-message",
            auto_execute=True,
        )
        messages = result.get("messages") or []
        last_reply = ""
        for msg in reversed(messages):
            if str(msg.get("direction") or "") == "agent->jarvis":
                last_reply = str(msg.get("content") or "")
                break
        return {
            "status": "ok",
            "to_agent_id": to_agent_id,
            "agent_status": str(result.get("status") or ""),
            "reply": last_reply[:1200] if last_reply else None,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_cancel_agent(args: dict[str, Any]) -> dict[str, Any]:
    agent_id = str(args.get("agent_id") or "").strip()
    note = str(args.get("note") or "").strip()
    if not agent_id:
        return {"status": "error", "error": "agent_id is required"}
    try:
        from core.services.agent_runtime import cancel_agent
        result = cancel_agent(agent_id, note=note)
        return {"status": "ok", "agent_id": agent_id, "result": result}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ── Self-tools handlers ────────────────────────────────────────────────

def _exec_daemon_status(_args: dict[str, Any]) -> dict[str, Any]:
    from core.services.daemon_manager import get_all_daemon_states
    return {"daemons": get_all_daemon_states()}


def _exec_control_daemon(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.daemon_manager import control_daemon, get_daemon_names
    name = str(args.get("name", ""))
    action = str(args.get("action", ""))
    interval_minutes = args.get("interval_minutes")
    if interval_minutes is not None:
        interval_minutes = int(interval_minutes)
    try:
        return control_daemon(name, action, interval_minutes=interval_minutes)
    except ValueError as exc:
        valid = sorted(get_daemon_names())
        return {"error": str(exc), "valid": valid}


def _exec_list_signal_surfaces(_args: dict[str, Any]) -> dict[str, Any]:
    from core.services.signal_surface_router import list_all_surfaces
    return {"surfaces": list_all_surfaces()}


def _exec_read_signal_surface(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.signal_surface_router import read_surface
    name = str(args.get("name", ""))
    return read_surface(name)


def _exec_eventbus_recent(args: dict[str, Any]) -> dict[str, Any]:
    from core.eventbus.bus import event_bus
    raw_limit = args.get("limit", 20)
    limit = min(int(raw_limit), 100)
    kind_filter = str(args.get("kind", "")).strip()
    events = event_bus.recent(limit=100 if kind_filter else limit)
    if kind_filter:
        events = [e for e in events if str(e.get("kind", "")).startswith(kind_filter)]
        events = events[:limit]
    return {"events": events, "count": len(events)}


_SENSITIVE_SETTING_PATTERNS = [
    "auth_profile",
    "credential",
    "approval",
    "auth_",
]


def _is_sensitive_setting(key: str) -> bool:
    key_lower = key.lower()
    return any(pat in key_lower for pat in _SENSITIVE_SETTING_PATTERNS)


def _exec_update_setting(args: dict[str, Any]) -> dict[str, Any]:
    import json as _json
    import core.runtime.config as _cfg
    from core.runtime.settings import load_settings

    key = str(args.get("key", "")).strip()
    value = args.get("value")

    settings = load_settings()
    valid_keys = list(settings.to_dict().keys())

    if key not in valid_keys:
        return {"error": f"unknown setting '{key}'", "valid_keys": valid_keys}

    if _is_sensitive_setting(key):
        return {
            "requires_approval": True,
            "key": key,
            "requested_value": value,
            "message": (
                f"Setting '{key}' is sensitive (auth/credentials). "
                "Please confirm you want to update it."
            ),
        }

    old_value = settings.to_dict()[key]
    settings_file = _cfg.SETTINGS_FILE

    if settings_file.exists():
        raw = _json.loads(settings_file.read_text(encoding="utf-8"))
    else:
        raw = settings.to_dict()

    raw[key] = value
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(_json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"key": key, "old": old_value, "new": value}


def _exec_recall_council_conclusions(args: dict[str, Any]) -> dict[str, Any]:
    topic = str(args.get("topic") or "").strip()
    if not topic:
        return {"error": "topic is required", "entries": []}
    from core.services.council_memory_service import read_all_entries
    from core.services.council_memory_daemon import (
        _call_similarity_llm,
        _parse_indices,
    )
    entries = read_all_entries()
    if not entries:
        return {"entries": [], "message": "Ingen rådskonklusioner gemt endnu"}

    index_lines = []
    for i, entry in enumerate(entries, 1):
        summary = str(entry.get("conclusion") or "")[:120]
        index_lines.append(f"{i}. [{entry.get('timestamp', '')}] {entry.get('topic', '')} — {summary}")
    index_text = "\n".join(index_lines)

    llm_response = _call_similarity_llm(recent_context=topic, index_text=index_text)
    indices = _parse_indices(llm_response, max_idx=len(entries))

    if not indices:
        return {"entries": [], "message": "Ingen relevante rådskonklusioner fundet"}

    matched = [entries[i - 1] for i in indices]
    return {"entries": matched}


def _exec_internal_api(args: dict[str, Any]) -> dict[str, Any]:
    """Call Jarvis' own internal API (same-process HTTP, no external auth)."""
    method = str(args.get("method") or "GET").upper().strip()
    path = str(args.get("path") or "").strip()
    body_raw = str(args.get("body") or "").strip()

    if method not in ("GET", "POST"):
        return {"error": f"Unsupported method: {method}. Only GET and POST are allowed.", "status": "error"}

    if not path.startswith("/"):
        return {"error": "path must start with / — external URLs are not allowed.", "status": "error"}

    # Block anything that looks like an external URL slipping through
    if "//" in path or path.startswith("http"):
        return {"error": "External URLs are not allowed. Use internal paths only.", "status": "error"}

    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        _candidate_ports = [settings.port]
    except Exception:
        _candidate_ports = [8010]

    # Also try port 80 (systemd service default) if not already in list
    for _p in (80, 8010):
        if _p not in _candidate_ports:
            _candidate_ports.append(_p)

    body_bytes: bytes | None = None
    headers: dict[str, str] = {}

    if method == "POST":
        body_bytes = body_raw.encode("utf-8") if body_raw else b"{}"
        headers["Content-Type"] = "application/json"

    _last_error: str = ""
    for _port in _candidate_ports:
        base_url = f"http://127.0.0.1:{_port}"
        url = base_url + path
        try:
            req = urllib_request.Request(url, data=body_bytes, headers=headers, method=method)
            with urllib_request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except Exception:
                data = {"raw": raw}
            return {"data": data, "path": path, "method": method, "port": _port, "status": "ok"}
        except urllib_error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")[:500]
            return {"error": f"HTTP {exc.code}: {exc.reason}", "detail": body_text, "status": "error"}
        except urllib_error.URLError:
            _last_error = f"Connection refused on port {_port}"
            continue
        except Exception as exc:
            _last_error = str(exc)
            continue

    return {"error": f"Connection failed on all ports {_candidate_ports}: {_last_error}", "status": "error"}


def _exec_my_project_status(args: dict[str, Any]) -> dict[str, Any]:
    """Return your current personal project state, including any pending proposal."""
    try:
        from core.services.personal_project import (
            get_active_project, get_latest_proposal, list_journal_entries,
        )
        active = get_active_project()
        proposal = get_latest_proposal()
        result: dict[str, Any] = {"status": "ok"}
        if active:
            result["active_project"] = active
            result["recent_journal"] = list_journal_entries(
                project_id=active["id"], limit=5,
            )
            name = active.get("name", "untitled")
            entries = len(result["recent_journal"])
            result["text"] = (
                f"Aktivt projekt: **{name}** — {entries} journalindlæg."
            )
        else:
            result["active_project"] = None
            result["text"] = "Ingen aktivt projekt."
        if proposal:
            result["pending_proposal"] = proposal
            result["text"] += f" Forslag venter: {proposal.get('name', 'untitled')}."
        return result
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_my_project_journal_write(args: dict[str, Any]) -> dict[str, Any]:
    """Write a journal entry in your current personal project. No approval needed."""
    text = str(args.get("entry_text") or "").strip()
    if not text:
        return {"error": "entry_text is required", "status": "error"}
    mood = str(args.get("mood_tone") or "").strip()
    try:
        from core.services.personal_project import add_journal_entry, get_active_project
        active = get_active_project()
        if not active:
            return {"error": "no_active_project", "status": "error",
                    "hint": "You must declare or accept a project first."}
        result = add_journal_entry(
            project_id=active["id"],
            entry_text=text,
            source="inner_voice_spinoff",
            mood_tone=mood,
        )
        return {
            "status": "ok",
            "entry": result,
            "project_name": active["name"],
            "text": f"Journal-indlæg gemt i **{active['name']}** ({len(text)} tegn).",
        }
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_my_project_accept_proposal(args: dict[str, Any]) -> dict[str, Any]:
    """Accept the latest pending proposal as your personal project."""
    override_name = str(args.get("name") or "").strip()
    override_why = str(args.get("why_mine") or "").strip()
    try:
        from core.services.personal_project import (
            get_latest_proposal, declare_project,
        )
        proposal = get_latest_proposal()
        if not proposal:
            return {"error": "no_pending_proposal", "status": "error"}
        result = declare_project(
            name=override_name or proposal["name"],
            why_mine=override_why or proposal.get("why_mine", ""),
            description=proposal.get("description", ""),
            from_proposal_id=proposal["id"],
        )
        if not result:
            return {"error": "declare_failed_maybe_already_active", "status": "error"}
        return {
            "status": "ok",
            "project": result,
            "text": f"Forslag accepteret som personligt projekt: **{result.get('name', 'untitled')}**.",
        }
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_my_project_declare(args: dict[str, Any]) -> dict[str, Any]:
    """Freely declare a new personal project (bypassing proposal flow).

    Use when you know what your project is and want to name it yourself.
    """
    name = str(args.get("name") or "").strip()
    why = str(args.get("why_mine") or "").strip()
    description = str(args.get("description") or "").strip()
    if not name or not why:
        return {"error": "name and why_mine are required", "status": "error"}
    try:
        from core.services.personal_project import declare_project
        result = declare_project(name=name, why_mine=why, description=description)
        if not result:
            return {"error": "declare_failed_active_project_exists", "status": "error"}
        return {
            "status": "ok",
            "project": result,
            "text": f"Personligt projekt erklæret: **{result.get('name', name)}**.",
        }
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_look_around(args: dict[str, Any]) -> dict[str, Any]:
    """Take a webcam snapshot now and describe what's there via VLM.

    Jarvis chooses to look — bypasses the 4x/day daemon cadence. Use when
    curious, when you feel a need to connect to the physical space, or
    when context suggests "what is the room like right now".

    Args:
        prompt: optional custom prompt (e.g., "focus on atmosphere",
                "describe any person present", default: tone+atmosphere)
    """
    custom_prompt = str(args.get("prompt") or "").strip()
    try:
        from core.services.visual_memory import look_around_now
        result = look_around_now(prompt_override=custom_prompt)
        if result.get("status") == "captured":
            return {
                "status": "ok",
                "description": result.get("description"),
                "captured_at": result.get("captured_at"),
            }
        return {
            "status": "error",
            "error": result.get("error") or result.get("reason") or str(result),
        }
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_deep_analyze(args: dict[str, Any]) -> dict[str, Any]:
    """Run scoped deep analysis of the codebase.

    Args:
        goal (required): what we're analyzing/looking for
        scope: 'repo' or 'diff' or free-text
        paths: optional list of paths to limit analysis
        question_set: optional list of specific questions
    """
    goal = str(args.get("goal") or "").strip()
    if not goal:
        return {"error": "goal is required", "status": "error"}
    scope = str(args.get("scope") or "repo").strip()
    paths_raw = args.get("paths")
    paths = None
    if isinstance(paths_raw, list):
        paths = [str(p) for p in paths_raw if str(p).strip()]
    elif isinstance(paths_raw, str) and paths_raw.strip():
        paths = [p.strip() for p in paths_raw.split(",") if p.strip()]

    qs_raw = args.get("question_set")
    question_set = None
    if isinstance(qs_raw, list):
        question_set = [str(q) for q in qs_raw if str(q).strip()]
    elif isinstance(qs_raw, str) and qs_raw.strip():
        question_set = [q.strip() for q in qs_raw.split("|") if q.strip()]

    try:
        from core.services.deep_analyzer import run_deep_analysis
        result = run_deep_analysis(
            goal=goal,
            scope=scope,
            paths=paths,
            question_set=question_set,
        )
        # Generalized-learning capture (#159, plan A): fodr konklusionen ind i
        # reasoning_store så læringen får input. dedup_key gør det idempotent.
        try:
            from core.services.reasoning_store import capture_conclusion
            capture_conclusion(
                source="deep_analyze",
                conclusion_text=str(result.get("summary") or "")[:600],
                context=f"deep_analyze: {goal}"[:200],
                confidence=0.5,
                dedup_key=f"deep_analyze:{goal}:{scope}",
            )
        except Exception:
            pass
        return {**result, "status": "ok"}
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_db_query(args: dict[str, Any]) -> dict[str, Any]:
    """Run a read-only SELECT query against Jarvis' database."""
    sql = str(args.get("sql") or "").strip()
    params_raw = str(args.get("params") or "").strip()

    if not sql:
        return {"error": "sql is required", "status": "error"}

    # Security: only SELECT allowed — reject any write or schema-modifying statements
    sql_upper = sql.upper().lstrip()
    _FORBIDDEN = (
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
        "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA",
        "VACUUM", "REINDEX", "SAVEPOINT", "RELEASE", "ROLLBACK", "COMMIT", "BEGIN",
    )
    for keyword in _FORBIDDEN:
        if re.match(rf"\b{keyword}\b", sql_upper, re.IGNORECASE):
            return {
                "error": f"Only SELECT statements are allowed. '{keyword}' is not permitted.",
                "status": "error",
            }
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        return {"error": "Only SELECT (or WITH ... SELECT) statements are allowed.", "status": "error"}

    params: list[Any] = []
    if params_raw:
        try:
            parsed = json.loads(params_raw)
            if not isinstance(parsed, list):
                return {"error": "params must be a JSON array, e.g. [\"value\", 42]", "status": "error"}
            params = parsed
        except Exception:
            return {"error": f"params is not valid JSON: {params_raw[:100]}", "status": "error"}

    try:
        from core.runtime.db import connect
        with connect() as conn:
            conn.row_factory = None  # raw rows
            cur = conn.execute(sql, params)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchmany(200)  # cap at 200 rows
            result_rows = [dict(zip(cols, row)) for row in rows]
        return {
            "columns": cols,
            "rows": result_rows,
            "row_count": len(result_rows),
            "capped": len(result_rows) == 200,
            "status": "ok",
        }
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_compact_context_session(session_id: str | None) -> Any:
    """Run session compact for session_id. Returns CompactResult or None (monkeypatchable)."""
    target_session = session_id
    if not target_session:
        # Fall back to most recently updated session
        try:
            from core.services.chat_sessions import list_chat_sessions
            sessions = list_chat_sessions()
            if sessions:
                target_session = str(sessions[0].get("session_id") or "")
        except Exception:
            return None
    if not target_session:
        return None
    try:
        from core.context.session_compact import compact_session_history
        from core.context.compact_llm import call_compact_llm
        from core.runtime.settings import load_settings as _ls
        settings = _ls()
        return compact_session_history(
            target_session,
            keep_recent=settings.context_keep_recent,
            summarise_fn=lambda msgs: call_compact_llm(
                "Komprimér denne dialog til max 400 ord. Bevar fakta, beslutninger og kontekst:\n\n"
                + "\n".join(f"{m['role']}: {m.get('content', '')}" for m in msgs),
                max_tokens=500,
            ),
        )
    except Exception:
        return None


def _exec_compact_context(args: dict[str, Any]) -> dict[str, Any]:
    cr = _exec_compact_context_session(None)
    if cr is None:
        return {
            "status": "ok",
            "freed_tokens": 0,
            "message": "Ingen historik at komprimere — samtalen er stadig kort.",
        }
    return {
        "status": "ok",
        "freed_tokens": cr.freed_tokens,
        "summary": cr.summary_text[:200],
        "message": f"Kontekst komprimeret. {cr.freed_tokens} tokens frigjort.",
    }


def _exec_queue_followup(args: dict[str, Any]) -> dict[str, Any]:
    reason = str(args.get("reason") or "").strip()
    text = str(args.get("text") or "").strip()
    if not reason:
        return {"status": "error", "error": "reason is required"}
    if not text:
        return {"status": "error", "error": "text is required"}
    if len(text) > 2000:
        return {"status": "error", "error": "text exceeds 2000 character limit"}
    try:
        from core.runtime.heartbeat_triggers import set_trigger_for_default_workspace
    except Exception as exc:
        return {"status": "error", "error": f"trigger module unavailable: {exc}"}
    entry = set_trigger_for_default_workspace(
        reason=reason, source="jarvis-self-followup", text=text
    )
    if entry is None:
        return {"status": "error", "error": "failed to queue trigger"}
    return {"status": "queued", "reason": reason, "created_at": entry.get("created_at", "")}


def _exec_publish_file(args: dict[str, Any]) -> dict[str, Any]:
    """Copy or create a file in ~/.jarvis-v2/files/ and return a download URL."""
    import shutil
    from core.runtime.config import JARVIS_HOME

    source_path = str(args.get("source_path") or "").strip()
    filename = str(args.get("filename") or "").strip()
    content = args.get("content")

    if not filename:
        return {"status": "error", "error": "filename is required"}
    # Prevent path traversal
    safe_name = Path(filename).name
    if not safe_name:
        return {"status": "error", "error": "invalid filename"}

    files_dir = JARVIS_HOME / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    dest = files_dir / safe_name

    try:
        if content is not None:
            # Write inline content (text or bytes)
            mode = "wb" if isinstance(content, bytes) else "w"
            dest.open(mode).write(content)
        elif source_path:
            src = Path(source_path)
            if not src.exists():
                return {"status": "error", "error": f"source_path not found: {source_path}"}
            shutil.copy2(src, dest)
        else:
            return {"status": "error", "error": "provide source_path or content"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    url = f"http://localhost:8080/files/{safe_name}"

    # Hallucination guard: verificér at URL'en faktisk virker
    url_verified = False
    url_error = ""
    try:
        req = urllib_request.Request(url, method="GET")
        with urllib_request.urlopen(req, timeout=5) as resp:
            url_verified = 200 <= resp.status < 300
            if not url_verified:
                url_error = f"HTTP {resp.status}"
    except Exception as exc:
        url_verified = False
        url_error = str(exc)

    result: dict[str, Any] = {
        "status": "ok",
        "filename": safe_name,
        "url": url,
        "markdown_link": f"[{safe_name}]({url})",
        "size_bytes": dest.stat().st_size,
        "url_verified": url_verified,
    }
    if url_error:
        result["url_verify_error"] = url_error
    if not url_verified:
        result["warning"] = (
            f"URL'en {url} returnerede ikke 200 ({url_error or 'unknown'}). "
            "Præsenter IKKE URL'en for brugeren — den virker ikke."
        )
    return result


# ── Handler registry ───────────────────────────────────────────────────

def _tool_load_more_tools(arguments: dict) -> dict:
    """Resolve which tools to add to the next round. Logs to DB + events."""
    import json as _json
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect

    names = list(arguments.get("names") or [])
    query = (arguments.get("query") or "").strip()

    all_names = {
        ((d.get("function") or {}).get("name") or d.get("name") or "")
        for d in (TOOL_DEFINITIONS or [])
    }

    resolved: list[str] = []
    unknown: list[str] = []
    for n in names:
        if n in all_names:
            resolved.append(n)
        else:
            unknown.append(n)

    if query and not resolved:
        try:
            from core.services.tool_embeddings import top_k_similar
            hits = top_k_similar(query, k=10)
            resolved = [n for n, _ in hits if n in all_names][:5]
        except Exception:
            resolved = []

    if not resolved and unknown:
        return {
            "status": "error",
            "error": f"tools not found: {unknown}. Use names from the TOOL CATALOG.",
        }

    if not resolved:
        return {
            "status": "ok",
            "added": [],
            "message": "no strong matches",
        }

    try:
        event_bus.publish("tool_router.load_more_fired", {
            "requested_names": names,
            "requested_query": query,
            "resolved_names": resolved,
        })
    except Exception:
        pass

    try:
        with connect() as c:
            c.execute(
                "INSERT INTO tool_router_load_more("
                "requested_names_json, requested_query, resolved_names_json, created_at) "
                "VALUES (?,?,?, datetime('now'))",
                (_json.dumps(names), query, _json.dumps(resolved)),
            )
            c.commit()
    except Exception:
        pass

    return {
        "status": "ok",
        "added": resolved,
        "message": f"Added {len(resolved)} tool(s); available next round.",
    }


def _exec_github_list_issues(args: dict[str, Any]) -> dict[str, Any]:
    """List GitHub-issues via brugerens EGEN connector-token (Spor A)."""
    from core.services.github_connector import list_issues
    uid = _operator_user_id(args)
    repo = str(args.get("repo") or "").strip()
    state = str(args.get("state") or "open").strip() or "open"
    return list_issues(uid, repo, state=state)


def _exec_github_list_prs(args: dict[str, Any]) -> dict[str, Any]:
    """List GitHub pull requests via brugerens EGEN connector-token (Spor A)."""
    from core.services.github_connector import list_prs
    uid = _operator_user_id(args)
    repo = str(args.get("repo") or "").strip()
    state = str(args.get("state") or "open").strip() or "open"
    return list_prs(uid, repo, state=state)


def _exec_gmail_search(args: dict[str, Any]) -> dict[str, Any]:
    """Søg i brugerens Gmail via deres EGEN Google-connector-token."""
    from core.services.gmail_connector import search
    uid = _operator_user_id(args)
    query = str(args.get("query") or "").strip()
    return search(uid, query, max_results=args.get("max_results", 10))


def _exec_gmail_list(args: dict[str, Any]) -> dict[str, Any]:
    """List nyeste mails i brugerens Gmail-indbakke via deres EGEN connector-token."""
    from core.services.gmail_connector import list_inbox
    uid = _operator_user_id(args)
    return list_inbox(uid, max_results=args.get("max_results", 10))


def _exec_gmail_send(args: dict[str, Any]) -> dict[str, Any]:
    """Send mail på brugerens vegne — bag approval-kort (som operator-tools)."""
    uid = _operator_user_id(args)
    to = str(args.get("to") or "").strip()
    subject = str(args.get("subject") or "")
    body = str(args.get("body") or "")
    if not to:
        return {"status": "error", "error": "to_required"}
    # Godkendelse via chat-card; godkendt genkald sætter _runtime_trust_all.
    if not bool(args.get("_runtime_trust_all")):
        preview = (body or "")[:200]
        return {
            "status": "approval_needed",
            "tool_name": "gmail_send",
            "message": f"Jarvis vil sende en mail til {to} med emnet \"{subject}\".",
            "command": f"Til: {to} · Emne: {subject}\n\n{preview}",
        }
    from core.services.gmail_connector import send_message
    return send_message(uid, to, subject, body)


def _exec_calendar_list_events(args: dict[str, Any]) -> dict[str, Any]:
    """List kommende begivenheder i brugerens primære Google Calendar."""
    from core.services.google_connector import list_events
    return list_events(_operator_user_id(args), max_results=args.get("max_results", 10))


def _exec_drive_search(args: dict[str, Any]) -> dict[str, Any]:
    """Søg/list filer i brugerens Google Drive."""
    from core.services.google_connector import drive_search
    return drive_search(_operator_user_id(args), query=str(args.get("query") or ""),
                        max_results=args.get("max_results", 10))


def _exec_docs_read(args: dict[str, Any]) -> dict[str, Any]:
    """Læs tekst fra et Google Docs-dokument."""
    from core.services.google_connector import docs_read
    return docs_read(_operator_user_id(args), str(args.get("document_id") or "").strip())


def _exec_sheets_read(args: dict[str, Any]) -> dict[str, Any]:
    """Læs celler fra et Google Sheets-regneark."""
    from core.services.google_connector import sheets_read
    return sheets_read(_operator_user_id(args), str(args.get("spreadsheet_id") or "").strip(),
                       str(args.get("range") or "").strip())


def _exec_slides_read(args: dict[str, Any]) -> dict[str, Any]:
    """Læs titler og tekst fra et Google Slides-show."""
    from core.services.google_connector import slides_read
    return slides_read(_operator_user_id(args), str(args.get("presentation_id") or "").strip())


def _exec_calendar_create_event(args: dict[str, Any]) -> dict[str, Any]:
    """Opret kalender-aftale — bag approval-kort."""
    summary = str(args.get("summary") or "").strip()
    start = str(args.get("start") or "").strip()
    if not summary:
        return {"status": "error", "error": "summary_required"}
    if not start:
        return {"status": "error", "error": "start_required"}
    if not bool(args.get("_runtime_trust_all")):
        return {
            "status": "approval_needed",
            "tool_name": "calendar_create_event",
            "message": f"Jarvis vil oprette en kalender-aftale: \"{summary}\" ({start}).",
            "command": f"{summary} · {start}",
        }
    from core.services.google_connector import create_event
    return create_event(_operator_user_id(args), summary, start,
                        end=str(args.get("end") or ""),
                        description=str(args.get("description") or ""),
                        location=str(args.get("location") or ""))


def _exec_docs_append(args: dict[str, Any]) -> dict[str, Any]:
    """Tilføj tekst til et Google-dokument — bag approval-kort."""
    document_id = str(args.get("document_id") or "").strip()
    text = str(args.get("text") or "")
    if not document_id:
        return {"status": "error", "error": "document_id_required"}
    if not text:
        return {"status": "error", "error": "text_required"}
    if not bool(args.get("_runtime_trust_all")):
        return {
            "status": "approval_needed",
            "tool_name": "docs_append",
            "message": f"Jarvis vil tilføje tekst til et Google-dokument ({document_id}).",
            "command": f"Doc {document_id}\n\n{text[:200]}",
        }
    from core.services.google_connector import append_doc
    return append_doc(_operator_user_id(args), document_id, text)


def _exec_sheets_write(args: dict[str, Any]) -> dict[str, Any]:
    """Skriv celler i et Google Sheets-regneark — bag approval-kort."""
    spreadsheet_id = str(args.get("spreadsheet_id") or "").strip()
    cell_range = str(args.get("range") or "").strip()
    values = args.get("values")
    if not spreadsheet_id:
        return {"status": "error", "error": "spreadsheet_id_required"}
    if not cell_range:
        return {"status": "error", "error": "range_required"}
    if not isinstance(values, list) or not values:
        return {"status": "error", "error": "values_required"}
    if not bool(args.get("_runtime_trust_all")):
        return {
            "status": "approval_needed",
            "tool_name": "sheets_write",
            "message": f"Jarvis vil skrive {len(values)} række(r) i et regneark ({cell_range}).",
            "command": f"Sheet {spreadsheet_id} · {cell_range} · {len(values)} rækker",
        }
    from core.services.google_connector import write_sheet
    return write_sheet(_operator_user_id(args), spreadsheet_id, cell_range, values)


def _exec_pdf_read(args: dict[str, Any]) -> dict[str, Any]:
    """Læs/ekstraher tekst fra en PDF (sti eller URL)."""
    from core.services.pdf_connector import read_pdf
    return read_pdf(str(args.get("source") or "").strip(), max_pages=args.get("max_pages", 20))


def _exec_note_add(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.notes_connector import add_note
    return add_note(_operator_user_id(args), str(args.get("text") or ""))


def _exec_note_list(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.notes_connector import list_notes
    return list_notes(_operator_user_id(args), limit=args.get("limit", 20))


def _exec_note_search(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.notes_connector import search_notes
    return search_notes(_operator_user_id(args), str(args.get("query") or ""))


def _exec_note_delete(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.notes_connector import delete_note
    return delete_note(_operator_user_id(args), str(args.get("id") or ""))


def _exec_hf_search_models(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.hf_connector import search_models
    return search_models(str(args.get("query") or ""), limit=args.get("limit", 10))


def _exec_hf_model_info(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.hf_connector import model_info
    return model_info(str(args.get("model_id") or "").strip())


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
    if classify_file_write(str(target)) == "blocked":
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
    if classify_file_write(str(target)) == "blocked":
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
    if classify_command(command) == "blocked":
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
        output = output[:MAX_BASH_OUTPUT_CHARS - 1] + "…"
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

_REPO_STATE_KEY_PREFIX = "commit_enforcement:"
_REPO_STATE_TTL_SECONDS = 24 * 60 * 60


def _repo_state_session_key(session_id: str) -> str:
    return _REPO_STATE_KEY_PREFIX + session_id


def _repo_state_get_counter(session_id: str) -> int:
    try:
        from core.services import shared_cache as _sc
        v = _sc.get(_repo_state_session_key(session_id))
        if isinstance(v, dict):
            return int(v.get("edits", 0))
    except Exception:
        pass
    return 0


def _repo_state_bump_counter(session_id: str, delta: int = 1) -> int:
    try:
        from core.services import shared_cache as _sc
        cur = _sc.get(_repo_state_session_key(session_id))
        if not isinstance(cur, dict):
            cur = {"edits": 0}
        new_count = max(0, int(cur.get("edits", 0)) + delta)
        cur["edits"] = new_count
        _sc.set(_repo_state_session_key(session_id), cur, ttl_seconds=_REPO_STATE_TTL_SECONDS)
        return new_count
    except Exception:
        return 0


def _repo_state_reset_counter(session_id: str) -> None:
    try:
        from core.services import shared_cache as _sc
        _sc.set(_repo_state_session_key(session_id), {"edits": 0}, ttl_seconds=_REPO_STATE_TTL_SECONDS)
    except Exception:
        pass


def _detect_git_commit_in_bash(command: str, stdout: str) -> bool:
    """True hvis bash-kommandoen kørte en git commit der lykkedes.
    Heuristik: command indeholder 'git commit' og stdout/stderr ikke
    indeholder 'nothing to commit' eller error-markers."""
    cmd = (command or "").lower()
    if "git commit" not in cmd:
        return False
    out = (stdout or "").lower()
    if "nothing to commit" in out or "working tree clean" in out:
        return False
    # Tegn pa succes: "master|main" og en commit-SHA-prefix
    if "[" in out and "]" in out:
        return True
    return True  # default optimistic - kommandoen kørte uden at fejle åbenlyst


def _attach_repo_state(
    result: dict,
    *,
    session_id: str,
    bumped: bool = True,
    bash_command: str = "",
) -> dict:
    """Augmenter tool-result med _repo_state-blok. Idempotent ved fejl."""
    try:
        if not isinstance(result, dict):
            return result
        if result.get("status") and result.get("status") != "ok":
            return result  # fejlede resultater får ikke en bump

        # Reset counter hvis dette var en succesful git commit
        if bash_command and _detect_git_commit_in_bash(bash_command, str(result.get("stdout") or "")):
            _repo_state_reset_counter(session_id)
            bumped = False
            edits = 0
        elif bumped:
            edits = _repo_state_bump_counter(session_id, delta=1)
        else:
            edits = _repo_state_get_counter(session_id)

        # Hent live git-state via eksisterende endpoint-helper (container)
        try:
            from apps.api.jarvis_api.routes.chat import _git_status_sync
            git_state = _git_status_sync("container", "")
        except Exception:
            git_state = {}

        dirty_count = int(git_state.get("dirty") or 0)
        block = {
            "branch": git_state.get("branch") or "?",
            "dirty": dirty_count > 0,
            "modified_count": dirty_count,
            "lines_added": int(git_state.get("added") or 0),
            "lines_removed": int(git_state.get("removed") or 0),
            "edits_since_commit": edits,
        }

        # Phase B - eskalering
        if edits >= 10 and block["dirty"]:
            block["urgency"] = "high"
            block["warning"] = (
                f"⚠️⚠️  {edits} ulandede mutations-kald uden commit. "
                "Commit NU. Du blokerer din egen tråd."
            )
        elif edits >= 5 and block["dirty"]:
            block["urgency"] = "elevated"
            block["warning"] = (
                f"⚠️  {edits} mutations-kald uden commit siden sidst. "
                "Kør git commit nu så next-turn ikke er rebase-helvede."
            )
        elif block["dirty"]:
            block["urgency"] = "normal"
        else:
            block["urgency"] = "clean"

        result["_repo_state"] = block
        return result
    except Exception as exc:
        try:
            from logging import getLogger
            getLogger(__name__).debug("_attach_repo_state failed: %s", exc)
        except Exception:
            pass
        return result



def _enforce_wrapper(tool_name: str, fn):
    """Returner en wrapper der attacher _repo_state efter fn er kørt.
    Mutation-tools får bumped=True; alt andet bumped=False (men stadig
    repo-state for context)."""
    MUTATION_TOOLS = {
        "bash", "write_file", "edit_file",
        "operator_bash", "operator_write_file", "operator_edit_file",
    }
    bumped = tool_name in MUTATION_TOOLS
    def _wrapped(args: dict) -> dict:
        out = fn(args)
        try:
            sid = _commit_enforcement_session_id(args)
            bash_cmd = str(args.get("command") or "") if tool_name in ("bash", "operator_bash") else ""
            return _attach_repo_state(out, session_id=sid, bumped=bumped, bash_command=bash_cmd)
        except Exception:
            return out
    return _wrapped


def _commit_enforcement_session_id(args: dict) -> str:
    return str(
        args.get("_runtime_session_id")
        or args.get("_session_id")
        or "default"
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
            _TRUNCATE_NOTICE = 120  # chars reserved for truncation notice
            _filtered = {k: v for k, v in result.items() if k != "status"}
            _dumped = json.dumps(_filtered, ensure_ascii=False, indent=2)
            if len(_dumped) <= _MAX_FALLBACK_CHARS:
                text = _dumped
            else:
                # Smart truncation: keep as much real content as fits,
                # then append a brief notice with the total size + keys.
                _keys = ", ".join(sorted(_filtered.keys())) or "<none>"
                _usable = _MAX_FALLBACK_CHARS - _TRUNCATE_NOTICE
                _sliced = _dumped[:_usable].rsplit("\n", 1)[0]  # don't break mid-line
                _truncated_count = len(_filtered)
                # Count how many top-level items were fully shown vs cut
                _shown_count = _sliced.count('": ')  # rough count of key-value pairs shown
                text = (
                    f"{_sliced}\n"
                    f"... [truncated: {_truncated_count} keys, "
                    f"showing first ~{_shown_count} — "
                    f"keys: {_keys}. "
                    f"Add a 'text' key in the tool's exec for a clean summary.]"
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
