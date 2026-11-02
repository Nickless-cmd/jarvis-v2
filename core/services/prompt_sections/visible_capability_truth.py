"""Scope-aware capability truth for visible prompts.

Extracted from ``prompt_contract`` as the required Boy Scout split before its
logic changed.  The public names remain re-exported there for compatibility.
"""
from __future__ import annotations

import logging

from core.runtime.config import PROJECT_ROOT
from core.services.prompt_mode_layout import mode_layout_v2_enabled
from core.tools import tool_scoping


logger = logging.getLogger(__name__)


def _scope() -> str:
    try:
        return str(tool_scoping.current_tool_scope() or "").strip().lower()
    except Exception as exc:
        logger.warning("capability truth: kunne ikke læse tool-scope: %s", exc)
        return ""


def _legacy_capability_truth_instruction(*, compact: bool) -> str:
    lines = [
        "Runtime tool calling:",
        "- You have tools available via native function calling. Use them directly.",
        "- Core tools include read_file, write_file, edit_file, search, find_files, bash, web_fetch, and web_search.",
        "- CRITICAL: ALWAYS use the actual tool call mechanism. NEVER simulate tool usage in text.",
        "- When you need to write a file, CALL write_file. Do NOT say 'I will write' — just call the tool.",
        "- When you need to run a command, CALL bash. Do NOT describe the command — call it.",
        "- Safe workspace paths are auto-approved by runtime; blocked or risky paths require user approval or return error.",
        "- The runtime handles all permissions and approvals automatically. You never need to ask the user.",
        "- If you need information, use tools proactively. Do not guess from fragments.",
        "- BATCH independent calls: when your next steps do not depend on each other's results, emit them as SEVERAL tool calls in the SAME round. Several read-only bash commands, several read_file, a search plus a read — one round, not one round each.",
        "- Go one call per round ONLY when the next call's arguments depend on the previous call's result. Anything that waits for nothing should travel together.",
        "- Continue autonomously instead of asking permission.",
        "- If the user asks for code analysis, read concrete code files — not just README or directory listings.",
        "- Project root (source code): " + str(PROJECT_ROOT),
        "- IMPORTANT: Your live workspace files (SOUL.md, MEMORY.md, USER.md, STANDING_ORDERS.md, SKILLS.md, etc.) are at ~/.jarvis-v2/shared/ — NOT inside the project root. The project contains a workspace/ template directory but those are NOT your live files. Always use ~/.jarvis-v2/shared/ when reading or writing your own identity/memory files.",
    ]
    return "\n".join(lines)


def _visible_capability_truth_instruction(*, compact: bool) -> str | None:
    if not mode_layout_v2_enabled():
        return _legacy_capability_truth_instruction(compact=compact)

    scope = _scope()
    common = [
        "Runtime capability truth:",
        "- The native tools exposed in this request are authoritative. Use their actual call mechanism; never simulate a tool call in prose.",
        "- Use available tools for claims that require inspection. Batch independent calls; sequence only calls whose arguments depend on an earlier result.",
        "- A tool error, policy block or approval request is not success. Report the real state and do not invent a result.",
    ]
    if scope == "chat":
        common.extend([
            "- CHAT MODE can read, search, browse and use memory through its exposed tools. It has no shell, file-write, edit or agent-dispatch capability.",
            "- Answer and investigate directly. If execution or repository mutation is required, say briefly that it belongs in code mode.",
        ])
    elif scope == "code":
        common.extend([
            "- CODE MODE can inspect and mutate the active workspace with its exposed file and shell tools; use them directly when the task calls for action.",
            "- Read concrete code and relevant tests before changing them, then verify the resulting state with tools.",
            "- Project root (source code): " + str(PROJECT_ROOT),
        ])
    else:
        common.append(
            "- No explicit mode signal is present. Do not assume shell or write access; rely only on tools actually exposed in this request."
        )
    common.append(
        "- Live identity and memory files are under ~/.jarvis-v2/shared/; the repository's workspace/ directory is only a template."
    )
    return "\n".join(common)


def _visible_capability_id_summary() -> str | None:
    if not mode_layout_v2_enabled():
        return "\n".join([
            "Available tools: read_file, write_file, edit_file, search, find_files, bash, web_fetch, web_search.",
            "Batch independent tool calls into one round; sequence only what depends on a previous result.",
            "Continue autonomously for read-only tasks.",
        ])
    scope = _scope()
    if scope == "chat":
        first = "CHAT MODE tools: use only the native read, search, web and memory capabilities exposed in this request; no shell or file mutation."
    elif scope == "code":
        first = "CODE MODE tools: use the native file, search, shell and web capabilities exposed in this request."
    else:
        first = "Available tools are exactly the native functions exposed in this request; do not assume hidden write or shell access."
    return "\n".join([
        first,
        "Batch independent tool calls into one round; sequence only what depends on a previous result.",
        "Continue autonomously for safe read-only work.",
    ])


__all__ = ["_visible_capability_id_summary", "_visible_capability_truth_instruction"]
