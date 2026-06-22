"""Compact tool catalog for system prompt.

Lists all registered tool names + a 1-line description so Jarvis always
knows what exists, even when the full tool definitions sent on a turn
are a subset (selected by tool_router). Cached in-memory; invalidated
when the tool registry hash changes.
"""
from __future__ import annotations

import hashlib
import json
from typing import Optional

from core.tools.simple_tools import get_tool_definitions

_HEADER = (
    "KERNE-VÆRKTØJER (de mest brugte). Du ser de relevante som native "
    "function-defs hver tur; resten findes via load_more_tools(query=\"...\"):\n"
)

# 2026-06-22: the full ~445-tool text catalog was 59% of the visible system
# prompt (~7.5k tokens) and fully redundant with the native tool definitions
# sent on every turn. Replaced with a curated core set + a load_more_tools
# pointer. Discoverability is preserved (native defs + query-based fetch);
# the token cost is not.
_CORE_TOOLS = [
    "read_file", "write_file", "edit_file", "search", "find_files",
    "bash", "run_pytest", "db_query",
    "web_search", "web_fetch",
    "search_memory", "recall_memories", "remember_this",
    "schedule_self_wakeup", "notify_user", "git_status",
]

_cached_text: Optional[str] = None
_cached_hash: Optional[str] = None


def _short_desc(tool_def: dict) -> str:
    # 2026-05-08: cap descriptions at 50 chars (was 120). When tool_router
    # prunes per-turn, the model sees ~70-100 schemas with full descriptions
    # already; the catalog only needs to be a "what else exists" hint so the
    # model can decide which load_more_tools(names=[...]) to call. Cutting
    # descriptions roughly halves the catalog (~25K → ~13K chars).
    fn = tool_def.get("function") or tool_def
    desc = str(fn.get("description") or "").strip()
    head = desc.split("\n", 1)[0]
    if "." in head[:50]:
        head = head.split(".", 1)[0] + "."
    return head[:50].strip() or "(no description)"


def _registry_hash() -> str:
    defs = get_tool_definitions() or []
    payload = json.dumps(
        sorted(
            (
                (d.get("function") or {}).get("name") or d.get("name") or "",
                _short_desc(d),
            )
            for d in defs
        ),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_catalog_text() -> str:
    """Return cached catalog text; rebuild only if tool registry changed."""
    global _cached_text, _cached_hash
    h = _registry_hash()
    if _cached_text is not None and _cached_hash == h:
        return _cached_text
    defs = get_tool_definitions() or []
    by_name = {
        ((d.get("function") or {}).get("name") or d.get("name") or ""): d
        for d in defs
    }
    lines = [_HEADER]
    shown = 0
    for name in _CORE_TOOLS:
        d = by_name.get(name)
        if d:
            lines.append(f"- {name}: {_short_desc(d)}")
            shown += 1
    remaining = max(0, len(defs) - shown)
    if remaining:
        lines.append(
            f"\n+ {remaining} flere værktøjer (operator-desktop, kalender, mail, "
            "discord, billede/video, hjerne, skills, git, home-assistant m.fl.). "
            "Brug load_more_tools(query=\"…\") for at finde dem du mangler ved navn."
        )
    text = "\n".join(lines)
    _cached_text = text
    _cached_hash = h
    return text


def catalog_token_estimate() -> int:
    """Rough char/4 token estimate of the current catalog."""
    return max(1, len(build_catalog_text()) // 4)


def invalidate_cache() -> None:
    """Force next call to rebuild. Useful in tests."""
    global _cached_text, _cached_hash
    _cached_text = None
    _cached_hash = None
