"""Cache-aware ordering for the visible prompt's dynamic tail."""
from __future__ import annotations


_MEMORY_HEADER_PREFIX = "[HUKOMMELSE]"
_MEMORY_SECTION_PREFIXES = (
    "MEMORY.md:",
    "## Min hjerne —",
    "Memory recall bundle:",
    "Lektier (",
    "Lært om ",
    "[CHAT MEMORY BRIEF",
    "Sådan taler ",
    "Hensyn om ",
    "Siden sidst (",
)
_POST_MEMORY_PREFIXES = (
    "[rum ",
    "[RUM ",
    "Recent daily notes ",
    "[enheds-presence]",
    "[override:",
    "[morgentråd]",
    "## Finitud",
    "⚖️ Before you answer:",
    "💾",
    "🔥",
    "⏰",
)


def move_query_memory_to_tail_end(tail: str) -> str:
    """Move the contiguous query-selected memory group to the absolute end.

    The memory group's contents vary with the current user message. Keeping it
    before operational and behavioral blocks makes every later byte a cache
    miss even when those later blocks are unchanged. The group is already
    cache-late; this final ordering step keeps its semantics and system role
    while allowing the stable remainder of the tail to reuse DeepSeek's prefix.

    Fail closed when an unknown block appears inside the group. That prevents a
    new memory-section format from being silently split or reordered.
    """
    text = str(tail or "")
    if not text:
        return text

    header_marker = f"\n\n{_MEMORY_HEADER_PREFIX}"
    start = text.find(header_marker)
    if start < 0:
        start = 0 if text.lstrip().startswith(_MEMORY_HEADER_PREFIX) else -1
    else:
        start += 2
    if start < 0:
        return text

    # Sections may contain their own blank paragraphs (notably "Min hjerne"),
    # so paragraph splitting cannot identify the group boundary. Locate the
    # last known memory-section heading instead, then take that whole section.
    section_starts = [
        position
        for prefix in _MEMORY_SECTION_PREFIXES
        if (position := text.find(f"\n\n{prefix}", start)) >= 0
    ]
    if not section_starts:
        return text
    last_start = max(section_starts) + 2
    end = text.find("\n\n", last_start)
    if end < 0:
        return text
    if text.startswith("## Min hjerne —", last_start):
        # The heading intentionally has one blank line before its bullet list.
        end = text.find("\n\n", end + 2)
        if end < 0:
            return text

    following = text[end + 2 :].lstrip()
    if not following.startswith(_POST_MEMORY_PREFIXES):
        return text

    memory_group = text[start:end]
    before = text[:start].rstrip()
    after = text[end + 2 :].lstrip()
    return "\n\n".join(part for part in (before, after, memory_group) if part)
