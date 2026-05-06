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
    "TOOL CATALOG (use load_more_tools(names=[...]) or "
    "load_more_tools(query=\"...\") to fetch full schemas):\n"
)

_cached_text: Optional[str] = None
_cached_hash: Optional[str] = None


def _short_desc(tool_def: dict) -> str:
    fn = tool_def.get("function") or tool_def
    desc = str(fn.get("description") or "").strip()
    head = desc.split("\n", 1)[0]
    if "." in head[:120]:
        head = head.split(".", 1)[0] + "."
    return head[:120].strip() or "(no description)"


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
    lines = [_HEADER]
    for d in sorted(
        defs,
        key=lambda dd: ((dd.get("function") or {}).get("name") or dd.get("name") or ""),
    ):
        name = (d.get("function") or {}).get("name") or d.get("name") or "?"
        lines.append(f"- {name}: {_short_desc(d)}")
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
