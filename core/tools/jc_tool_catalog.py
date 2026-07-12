"""Single source of truth for what jarvis-code (jc) presents as tools.

Defines the curated default companion set, the runtime_-alias for the four
colliding file/shell primitives, and (in later tasks) the load_more contents.
Kept tiny and dependency-light so both the /v1/tools/catalog endpoint and tests
import it.
"""
from __future__ import annotations

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
