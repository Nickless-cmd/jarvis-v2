"""Tool definitions catalog for Jarvis' visible-lane tools.

Udskilt fra ``simple_tools.py`` (Boy Scout, 2026-07): den store
``TOOL_DEFINITIONS``-liste (~3150 linjer ren data) flyttet hertil for at
holde hoved-filen under kontrol. INGEN logik-ændring — kun flyt. De enkelte
``*_TOOL_DEFINITIONS``-fragmenter importeres fra deres oprindelses-moduler
(ét sted = ingen dobbelt-sandhed); denne fil samler dem til den kanoniske
liste. ``simple_tools`` re-importerer ``TOOL_DEFINITIONS`` herfra, så alle
eksisterende ``from core.tools.simple_tools import TOOL_DEFINITIONS`` virker.
"""

from __future__ import annotations

from typing import Any

from core.tools.browser_tools import (BROWSER_TOOL_DEFINITIONS)
from core.tools.comfyui_tools import (COMFYUI_TOOL_DEFINITIONS)
from core.tools.pollinations_tools import (POLLINATIONS_TOOL_DEFINITIONS)
from core.tools.hf_inference_tools import (HF_INFERENCE_TOOL_DEFINITIONS)
from core.tools.tiktok_content_tools import (TIKTOK_CONTENT_TOOL_DEFINITIONS)
from core.tools.mic_listen_tool import (MIC_LISTEN_TOOL_DEFINITIONS)
from core.tools.screen_tool import (SCREEN_TOOL_DEFINITIONS)
from core.tools.voice_journal_tool import (VOICE_JOURNAL_TOOL_DEFINITIONS)
from core.tools.wake_word_tool import (WAKE_WORD_TOOL_DEFINITIONS)
from core.tools.tiktok_tools import (TIKTOK_TOOL_DEFINITIONS)
from core.tools.tiktok_analytics_tools import (TIKTOK_ANALYTICS_TOOL_DEFINITIONS)
from core.tools.restart_self_tools import (RESTART_SELF_TOOL_DEFINITIONS)
from core.tools.mail_tools import (MAIL_TOOL_DEFINITIONS)
from core.tools.github_tools import (GITHUB_TOOL_DEFINITIONS)
from core.services.github_connector import (GITHUB_CONNECTOR_TOOL_DEFINITIONS)
from core.services.gmail_connector import (GMAIL_CONNECTOR_TOOL_DEFINITIONS)
from core.services.google_connector import (GOOGLE_CONNECTOR_TOOL_DEFINITIONS)
from core.services.pdf_connector import (PDF_CONNECTOR_TOOL_DEFINITIONS)
from core.services.notes_connector import (NOTES_CONNECTOR_TOOL_DEFINITIONS)
from core.services.hf_connector import (HF_CONNECTOR_TOOL_DEFINITIONS)
from core.tools.reasoning_store_tools import (REASONING_STORE_TOOL_DEFINITIONS)
from core.tools.math_tools import (MATH_TOOL_DEFINITIONS)
from core.tools.process_tools import (PROCESS_TOOL_DEFINITIONS)
from core.tools.claude_dispatch import (CLAUDE_DISPATCH_TOOL_DEFINITIONS)
from core.tools.agent_dispatch_tool import (AGENT_DISPATCH_TOOL_DEFINITIONS)
from core.tools.bash_session import (BASH_SESSION_TOOL_DEFINITIONS)
from core.tools.operator_bash_session import (OPERATOR_BASH_SESSION_TOOL_DEFINITIONS)
from core.tools.operator_tools import (OPERATOR_SESSION_TOOL_DEFINITIONS)
from core.tools.staged_edits_tools import (STAGED_EDITS_TOOL_DEFINITIONS)
from core.tools.project_notes_tools import (PROJECT_NOTES_TOOL_DEFINITIONS)
from core.tools.process_supervisor_tools import (PROCESS_SUPERVISOR_TOOL_DEFINITIONS)
from core.tools.process_watcher_tools import (PROCESS_WATCHER_TOOL_DEFINITIONS)
from core.tools.pause_and_ask_tools import (PAUSE_AND_ASK_TOOL_DEFINITIONS)
from core.tools.code_navigation_tools import (CODE_NAVIGATION_TOOL_DEFINITIONS)
from core.tools.worktree_tools import (WORKTREE_TOOL_DEFINITIONS)
from core.tools.identity_pin_tools import (IDENTITY_PIN_TOOL_DEFINITIONS)
from core.tools.ui_panel_tools import (UI_PANEL_TOOL_DEFINITIONS)
from core.tools.state_flag_tools import (STATE_FLAG_TOOL_DEFINITIONS)
from core.tools.app_control_tool import (APP_CONTROL_TOOL_DEFINITIONS)
from core.tools.agent_todo_tools import (AGENT_TODO_TOOL_DEFINITIONS)
from core.tools.monitor_tools import (MONITOR_TOOL_DEFINITIONS)
from core.tools.verify_tools import (VERIFY_TOOL_DEFINITIONS)
from core.services.surprise_detector import (SURPRISE_TOOL_DEFINITIONS)
from core.services.good_enough_gate import (GOOD_ENOUGH_TOOL_DEFINITIONS)
from core.services.delegation_advisor import (DELEGATION_ADVISOR_TOOL_DEFINITIONS)
from core.services.plan_proposals import (PLAN_PROPOSALS_TOOL_DEFINITIONS)
from core.services.clarification_classifier import (CLARIFICATION_TOOL_DEFINITIONS)
from core.services.reasoning_classifier import (REASONING_CLASSIFIER_TOOL_DEFINITIONS)
from core.services.verification_gate import (VERIFICATION_GATE_TOOL_DEFINITIONS)
from core.services.reasoning_escalation import (REASONING_ESCALATION_TOOL_DEFINITIONS)
from core.services.side_tasks import (SIDE_TASK_TOOL_DEFINITIONS)
from core.tools.smart_outline import (SMART_OUTLINE_TOOL_DEFINITIONS)
from core.tools.calendar_tools import (CALENDAR_TOOL_DEFINITIONS)
from core.tools.memory_tools import (MEMORY_TOOL_DEFINITIONS)
from core.tools.semantic_search_tools import (SEMANTIC_SEARCH_TOOL_DEFINITIONS)
from core.tools.notify_out_tools import (NOTIFY_OUT_TOOL_DEFINITIONS)
from core.tools.companion_push_tools import (COMPANION_PUSH_TOOL_DEFINITIONS)
from core.tools.daemon_alert_tools import (DAEMON_ALERT_TOOL_DEFINITIONS)
from core.tools.smart_compact_tools import (SMART_COMPACT_TOOL_DEFINITIONS)
from core.services.context_window_manager import (CONTEXT_WINDOW_TOOL_DEFINITIONS)
from core.services.autonomous_goals import (AUTONOMOUS_GOALS_TOOL_DEFINITIONS)
from core.services.memory_recall_engine import (UNIFIED_RECALL_TOOL_DEFINITIONS)
from core.services.role_registry import (ROLE_REGISTRY_TOOL_DEFINITIONS)
from core.services.agent_relay import (AGENT_RELAY_TOOL_DEFINITIONS)
from core.services.emotion_tagging import (EMOTION_TAGGING_TOOL_DEFINITIONS)
from core.services.personality_drift import (PERSONALITY_DRIFT_TOOL_DEFINITIONS)
from core.services.tool_pattern_miner import (TOOL_PATTERN_MINER_TOOL_DEFINITIONS)
from core.services.heartbeat_phases import (HEARTBEAT_PHASES_TOOL_DEFINITIONS)
from core.services.proactive_context_governor import (PROACTIVE_CONTEXT_TOOL_DEFINITIONS)
from core.services.memory_hierarchy import (MEMORY_HIERARCHY_TOOL_DEFINITIONS)
from core.services.provider_retry_policy import (PROVIDER_RETRY_TOOL_DEFINITIONS)
from core.services.provider_health_check import (PROVIDER_HEALTH_TOOL_DEFINITIONS)
from core.services.agent_self_evaluation import (SELF_EVALUATION_TOOL_DEFINITIONS)
from core.services.auto_improvement_proposer import (AUTO_IMPROVEMENT_TOOL_DEFINITIONS)
from core.services.prompt_variant_tracker import (PROMPT_VARIANT_TOOL_DEFINITIONS)
from core.services.experiment_runner import (EXPERIMENT_RUNNER_TOOL_DEFINITIONS)
from core.services.identity_mutation_log import (IDENTITY_MUTATION_TOOL_DEFINITIONS)
from core.services.agent_skill_library import (AGENT_SKILL_TOOL_DEFINITIONS)
from core.services.agent_observation_compressor import (AGENT_OBSERVATION_TOOL_DEFINITIONS)
from core.services.cross_agent_memory import (CROSS_AGENT_TOOL_DEFINITIONS)
from core.services.self_wakeup import (SELF_WAKEUP_TOOL_DEFINITIONS)
from core.services.wakeup_dispatcher import (WAKEUP_DISPATCHER_TOOL_DEFINITIONS)
from core.services.crisis_marker_detector import (CRISIS_MARKER_TOOL_DEFINITIONS)
from core.services.identity_drift_proposer import (IDENTITY_DRIFT_TOOL_DEFINITIONS)
from core.services.long_arc_synthesizer import (LONG_ARC_TOOL_DEFINITIONS)
from core.tools.recurring_scheduler_tools import (RECURRING_TOOL_DEFINITIONS)
from core.tools.notification_tools import (NOTIFICATION_TOOL_DEFINITIONS)
from core.tools.memory_topic_tools import (MEMORY_TOPIC_TOOL_DEFINITIONS)
from core.tools.webhook_tools import (WEBHOOK_TOOL_DEFINITIONS)
from core.tools.health_monitor_tools import (HEALTH_MONITOR_TOOL_DEFINITIONS)
from core.tools.sensory_tools import (SENSORY_TOOL_DEFINITIONS)
from core.tools.recall_memory_tools import (RECALL_MEMORY_TOOL_DEFINITIONS)
from core.tools.goals_tools import (GOAL_TOOL_DEFINITIONS)
from core.tools.decisions_tools import (DECISION_TOOL_DEFINITIONS)
from core.tools.composites_tools import (COMPOSITE_TOOL_DEFINITIONS)
from core.tools.visual_memory_tool import (VISUAL_MEMORY_TOOL_DEFINITIONS)
from core.tools.jarvis_brain_tools import (JARVIS_BRAIN_TOOL_DEFINITIONS)
from core.tools.stripe_tools import (STRIPE_TOOL_DEFINITIONS)
from core.tools.skill_engine_tools import (SKILL_ENGINE_TOOL_DEFINITIONS)
from core.tools.skill_gate_tool import (SKILL_GATE_TOOL_DEFINITIONS)
from core.tools.world_model_tools import (WORLD_MODEL_TOOL_DEFINITIONS)
from core.tools.counterfactual_tools import (COUNTERFACTUAL_TOOL_DEFINITIONS)
from core.tools.plan_revise_tool import (PLAN_REVISE_TOOL_DEFINITIONS)
from core.tools.curiosity_tools import (CURIOSITY_TOOL_DEFINITIONS)
from core.tools.skill_chain_propose_tool import (PROPOSE_SKILL_CHAIN_TOOL_DEFINITIONS)
from core.tools.skill_chain_revise_tool import (REVISE_SKILL_CHAIN_TOOL_DEFINITIONS)
from core.tools.meta_learning_tools import (META_LEARNING_TOOL_DEFINITIONS)
from core.tools.nudge_tools import (NUDGE_TOOL_DEFINITIONS)
from core.tools.skill_chain_tool import (SKILL_CHAIN_TOOL_DEFINITIONS)
from core.tools.forgetting_tools import (FORGETTING_TOOL_DEFINITIONS)
from core.tools.nudge_broend_tools import (NUDGE_BROEND_TOOL_DEFINITIONS)
from core.tools.coding_lane_tools import (CODING_LANE_TOOL_DEFINITIONS)
from core.tools.identity_sketch_tools import (IDENTITY_SKETCH_TOOL_DEFINITIONS)
from core.tools.session_search import TOOL_DEFINITION as _SESSION_SEARCH_TOOL_DEF


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
            "name": "task",
            "description": (
                "Dispatch a nested subagent for a bounded, well-scoped sub-task. "
                "The subagent runs LOCALLY in jarvis-code with its own tool budget "
                "and its own message history, and can never exceed your approval "
                "mode; it returns only its final summary as the tool result, so "
                "your own context stays clean. Use it to delegate focused "
                "exploration or research — e.g. subagent_type='explorer' to search "
                "the codebase — rather than doing it inline. Only available in "
                "jarvis-code (client-local execution)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Short task label (3-5 words).",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The full task/instructions for the subagent.",
                    },
                    "subagent_type": {
                        "type": "string",
                        "description": (
                            "Kind of subagent: 'explorer' (read-only search/exploration) "
                            "or 'general' (default). Optional."
                        ),
                    },
                },
                "required": ["description", "prompt"],
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
            "description": (
                "Fetch and read the text content of a web page. Long pages are "
                "paginated: you get a contiguous window from `offset` plus "
                "`total_chars`, `has_more` and `next_offset`. When `has_more` is "
                "true, call web_fetch again with the returned `next_offset` to read "
                "the rest — nothing in the middle is dropped."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch",
                    },
                    "offset": {
                        "type": "integer",
                        "description": (
                            "Character offset to start the window at (default 0). "
                            "Use the `next_offset` from a previous call to page "
                            "forward through a long page."
                        ),
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
                "Fan out several agents with DISTINCT perspectives on a question, then "
                "synthesise their positions. This is not a separate 'council system' — "
                "it is one shape of your own dispatch: you decide whether a question needs "
                "WORK (one agent, spawn_agent_task) or PERSPECTIVES (this), and you "
                "CONSTRUCT the roles that fit THIS specific question — e.g. a security "
                "critic, the user's advocate, a refuter, a long-term-consequences lens. "
                "Roles are born from the question and die with it; there is no fixed set. "
                "Use when a decision genuinely benefits from being pulled at from several "
                "angles: identity changes, ambiguous tradeoffs, lasting consequences."
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
                        "description": (
                            "Construct the perspectives that fit THIS question — give each "
                            "agent a distinct lens (e.g. 'security-critic', 'user-advocate', "
                            "'refuter', 'first-principles'). Prefer constructing your own over "
                            "the generic defaults; omit only when generic deliberation is fine."
                        ),
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
                "You write the agent's own prompt: pass a custom `system_prompt` for a freely-shaped agent, "
                "or omit it to fall back to a role start-template. `role` is an optional starting shape "
                "(researcher/planner/critic/synthesizer/executor/watcher, or any free label) — it only supplies "
                "a default prompt/tool-policy when you don't override them. Pass `allowed_tools` to give the "
                "agent hands (a list of tool names it may call); tool EXECUTION only takes effect when the "
                "agent_tools_enabled runtime flag is on, and every tool call still passes through the normal "
                "approval/scoping gates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Clear description of what the agent should do and return.",
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": (
                            "Optional. The agent's full system prompt, written fresh for this exact task. "
                            "When given it REPLACES the role template — this is how you give the agent a "
                            "custom persona/instructions. Omit to use the role's default template."
                        ),
                    },
                    "role": {
                        "type": "string",
                        "description": (
                            "Optional starting shape / label (default 'researcher'). Common templates: "
                            "researcher (read-only), planner, critic, synthesizer, executor (can spawn), "
                            "watcher (persistent monitor). Free text is allowed — an unknown role just uses "
                            "the researcher template as a base unless you pass system_prompt."
                        ),
                    },
                    "allowed_tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional list of tool names the agent may call (e.g. ['read_file','search_files']). "
                            "The tools reach the model and, when agent_tools_enabled is on, the agent can "
                            "actually invoke them — always through the normal approval/scoping gates."
                        ),
                    },
                    "tool_policy": {
                        "type": "string",
                        "description": (
                            "Optional tool-access policy override (e.g. 'none', 'read-only-runtime', 'can-spawn'). "
                            "Defaults to the role template's policy."
                        ),
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
                "required": ["goal"],
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
            "name": "central_query",
            "description": (
                "Din direkte kanal til Den Intelligente Central — jeres fælles terminal. LÆS: "
                "status (nu MED seneste anomalier+kendte signaler), incidents, trace, cluster_health, "
                "nerve_detail, autonomy, learning, drift, breakers, known_signals, instrument. "
                "SKRIV (owner-only): resolve_and_route (rout en ukendt fejl-signatur til rette nerve "
                "så den ikke længere står som anomali), depromote (angre det), resolve_incident (luk "
                "incident N), nerve_observe (injicér en observation til en nerve), note (fri-tekst ind "
                "i Centralens bevidsthed), toggle_nerve/cluster. Returnerer ALTID status=ok/error med "
                "meta — aldrig stille fejl. Paginer med offset ved has_more."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "incidents", "trace", "cluster_health",
                                 "nerve_detail", "autonomy", "learning", "drift",
                                 "breakers", "instrument", "known_signals",
                                 "toggle_nerve", "toggle_cluster",
                                 "resolve_and_route", "depromote", "resolve_incident",
                                 "nerve_observe", "note"],
                        "description": ("LÆS: status, incidents, trace, cluster_health, nerve_detail, "
                                        "autonomy, learning, drift, breakers, known_signals (promoverede "
                                        "signaler), instrument. SKRIV (owner-only): resolve_and_route "
                                        "(kræver signature+nerve, valgfri cluster/action_type/notes), "
                                        "depromote (signature), resolve_incident (incident_id), "
                                        "nerve_observe (nerve+cluster+text), note (text), toggle_*"),
                    },
                    "cluster": {"type": "string", "description": "(trace/cluster_health/toggle_cluster/resolve_and_route/nerve_observe) cluster-navn"},
                    "nerve": {"type": "string", "description": "(nerve_detail/toggle_nerve/resolve_and_route/nerve_observe) nerve-navn"},
                    "enabled": {"type": "boolean", "description": "(toggle_*) True=til, False=fra"},
                    "signature": {"type": "string", "description": "(resolve_and_route/depromote) anomali-signaturen (fra status.anomalies.recent eller known_signals)"},
                    "action_type": {"type": "string", "enum": ["observe", "log_as_known", "route_to_nerve"], "description": "(resolve_and_route) håndtering af fremtidige forekomster (default route_to_nerve)"},
                    "notes": {"type": "string", "description": "(resolve_and_route) valgfri note om hvorfor"},
                    "incident_id": {"type": "integer", "description": "(resolve_incident) incident-ID at lukke"},
                    "text": {"type": "string", "description": "(nerve_observe/note) fri-tekst observation/note"},
                    "importance": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "(nerve_observe) vigtighed (default medium)"},
                    "category": {"type": "string", "description": "(nerve_observe) valgfri kategori-tag"},
                    "limit": {"type": "integer", "description": "max resultater (default 20, max 100)"},
                    "offset": {"type": "integer", "description": "pagina-offset (brug meta.next_offset ved has_more)"},
                },
                "required": ["action"],
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
    *OPERATOR_BASH_SESSION_TOOL_DEFINITIONS,
    *OPERATOR_SESSION_TOOL_DEFINITIONS,
    *STAGED_EDITS_TOOL_DEFINITIONS,
    *PROJECT_NOTES_TOOL_DEFINITIONS,
    *PROCESS_SUPERVISOR_TOOL_DEFINITIONS,
    *PROCESS_WATCHER_TOOL_DEFINITIONS,
    *PAUSE_AND_ASK_TOOL_DEFINITIONS,
    *CODE_NAVIGATION_TOOL_DEFINITIONS,
    *WORKTREE_TOOL_DEFINITIONS,
    *IDENTITY_PIN_TOOL_DEFINITIONS,
    *UI_PANEL_TOOL_DEFINITIONS,
    *STATE_FLAG_TOOL_DEFINITIONS,
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
    *NOTIFICATION_TOOL_DEFINITIONS,
    *MEMORY_TOPIC_TOOL_DEFINITIONS,
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
