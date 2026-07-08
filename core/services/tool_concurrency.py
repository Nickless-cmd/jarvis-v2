"""Tool-concurrency policy (harness Part C).

Decides whether a round's tool calls may execute concurrently. ALLOWLIST +
ALL-OR-NOTHING: a round parallelizes only if EVERY call is a known read-only,
side-effect-free tool. Anything unlisted/new/mutating → the whole round runs
sequentially (fail-safe). Default mode is off (byte-identical to today).

This module only CLASSIFIES — it never executes. The executor
(simple_tool_executor.py) enforces the safe-invocation mechanics.
"""
from __future__ import annotations

import os

_MAX_CONCURRENCY = 6  # IO-bound reads; fixed (model-tiering the cap is a later lever)

# Curated read-only allowlist. Every entry is side-effect-free (reads/searches/
# list/status/network-GET). Writes, operator_bash*, click/type/key, mutations,
# rollbacks, and approval-gated tools are DELIBERATELY excluded.
_PARALLEL_SAFE: frozenset[str] = frozenset({
    "read_file", "read_tool_result", "read_attachment", "read_self_docs",
    "read_model_config", "read_mood", "read_self_state", "read_chronicles",
    "read_dreams", "list_dir", "find_files", "search", "search_memory",
    "search_chat_history", "search_sessions", "list_initiatives",
    "list_proposals", "list_scheduled_tasks", "heartbeat_status",
    "operator_read_file", "operator_list_dir", "operator_list_windows",
    "operator_list_processes", "operator_process_status", "operator_process_list",
    "operator_scheduled_list", "operator_browser_get_text",
    "operator_browser_get_links", "operator_browser_status",
    "operator_clipboard_read", "operator_find_image", "web_fetch", "web_search",
    "operator_webfetch", "get_weather", "get_exchange_rate", "get_news",
    "github_list_issues", "github_list_prs", "gmail_search", "gmail_list",
    "calendar_list_events", "drive_search", "docs_read", "sheets_read",
    "slides_read", "pdf_read", "note_list", "note_search", "hf_search_models",
    "hf_model_info",
})

_MODE_ENV = "JARVIS_TOOL_CONCURRENCY_MODE"
_VALID_MODES = ("off", "on")


def concurrency_mode() -> str:
    """Current mode: 'off' | 'on'. Default 'off'. Env wins over config. Self-safe."""
    env = os.environ.get(_MODE_ENV)
    if env is not None:
        v = env.strip().lower()
        if v in _VALID_MODES:
            return v
    try:
        from core.runtime.settings import load_settings
        v = str(load_settings().extra.get("tool_concurrency_mode", "off")).strip().lower()
        return v if v in _VALID_MODES else "off"
    except Exception:
        return "off"


def _call_name(tc: dict) -> str:
    fn = tc.get("function") or {}
    return str(fn.get("name") or "")


def is_parallelizable(tool_calls: list[dict], *, mode: str) -> bool:
    """True iff mode=='on' AND >=2 calls AND every call name is in the allowlist.
    All-or-nothing: any unlisted/unnamed call → False. Never raises."""
    try:
        if mode != "on":
            return False
        if not tool_calls or len(tool_calls) < 2:
            return False
        for tc in tool_calls:
            name = _call_name(tc)
            if not name or name not in _PARALLEL_SAFE:
                return False
        return True
    except Exception:
        return False
