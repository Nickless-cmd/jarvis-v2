"""Single source of truth for what jarvis-code (jc) presents as tools.

Defines the curated default companion set, the runtime_-alias for the four
colliding file/shell primitives, and (in later tasks) the load_more contents.
Kept tiny and dependency-light so both the /v1/tools/catalog endpoint and tests
import it.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

RUNTIME_ALIAS_PREFIX = "runtime_"

# Verified 2026-07-12: only these four native tools share a name with jc's
# client-owned local tools and therefore need aliasing.
COLLIDING_TOOLS: tuple[str, ...] = ("bash", "read_file", "write_file", "edit_file")

# Always-present native companions (unique names -> no alias needed).
DEFAULT_COMPANIONS: tuple[str, ...] = (
    "search_memory", "read_memory_topic", "write_memory_topic",
    "read_project_notes", "update_project_notes",
    "recall_memories", "search_jarvis_brain",
    "remember_this", "archive_brain_entry", "read_mood",
)


def alias_for(name: str) -> str:
    """runtime_ alias for a colliding tool name."""
    return f"{RUNTIME_ALIAS_PREFIX}{name}"


def unalias(name: str) -> str:
    """Strip the runtime_ prefix iff it maps to a colliding tool; else unchanged."""
    if is_runtime_alias(name):
        return name[len(RUNTIME_ALIAS_PREFIX):]
    return name


def is_runtime_alias(name: str) -> bool:
    """True only for runtime_<one-of-the-four-colliding-tools>."""
    if not name.startswith(RUNTIME_ALIAS_PREFIX):
        return False
    return name[len(RUNTIME_ALIAS_PREFIX):] in COLLIDING_TOOLS


LOAD_MORE_TOOL_DEF: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "load_more_tools",
        "description": (
            "Unlock the full runtime toolbox (owner only): runtime_bash/read_file/"
            "write_file/edit_file, advanced memory, identity, operator desktop tools. "
            "Call this when the default set is insufficient."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}


def _def_name(d: dict[str, Any]) -> str:
    return str((d.get("function") or d).get("name") or "")


def _all_native_defs(role: str) -> list[dict[str, Any]]:
    """Full native tool defs for a role. Wrapped as a module function for test injection."""
    from core.tools.simple_tools import get_tool_definitions
    return get_tool_definitions(role=role, scope="")


def build_jc_catalog(*, role: str, unlocked: bool) -> list[dict[str, Any]]:
    """Native-side tool defs jc should present (WITHOUT the 8 local client tools —
    jc prepends those). Locked: companions + load_more. Unlocked: companions +
    runtime_-aliased colliding tools + the rest of native + load_more."""
    all_defs = _all_native_defs(role)
    by_name = {_def_name(d): d for d in all_defs}
    out: list[dict[str, Any]] = []

    for name in DEFAULT_COMPANIONS:
        d = by_name.get(name)
        if d is not None:
            out.append(deepcopy(d))

    if unlocked:
        presented = {_def_name(d) for d in out}
        for d in all_defs:
            nm = _def_name(d)
            if nm in presented or nm == "load_more_tools":
                continue
            if nm in COLLIDING_TOOLS:
                alias = deepcopy(d)
                fn = alias.get("function") or alias
                fn["name"] = alias_for(nm)
                out.append(alias)
            else:
                out.append(deepcopy(d))

    out.append(deepcopy(LOAD_MORE_TOOL_DEF))
    return out
