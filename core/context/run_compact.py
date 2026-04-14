"""Run-level context compaction for the agentic tool-calling loop.

Compresses old message pairs in the running _agentic_messages list.
The base messages (initial prompt + first context) are always kept.
The most recent `keep_recent_pairs` pairs are always kept.
Everything in between is summarised.
"""
from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)


def compact_run_messages(
    messages: list[dict],
    *,
    keep_base: int,
    keep_recent_pairs: int,
    summarise_fn: Callable[[list[dict]], str],
) -> list[dict]:
    """Compact old messages in an agentic loop message list.

    Args:
        messages: The full _agentic_messages list.
        keep_base: Number of initial messages to always keep (prompt context).
        keep_recent_pairs: Number of most-recent assistant+user pairs to keep.
        summarise_fn: Callable that takes a list of messages and returns a summary string.

    Returns:
        A new, shorter messages list. Returns the original list unchanged if
        there is nothing to compact (middle section is empty or too small).
    """
    if len(messages) <= keep_base:
        return messages

    base = messages[:keep_base]
    rest = messages[keep_base:]

    # Each pair is 2 messages: assistant + user(tool results)
    keep_tail_count = keep_recent_pairs * 2
    if len(rest) <= keep_tail_count:
        return messages  # Nothing to compact

    middle = rest[: len(rest) - keep_tail_count]
    tail = rest[len(rest) - keep_tail_count :]

    summary = summarise_fn(middle)
    compact_msg = {
        "role": "user",
        "content": f"[KOMPRIMERET KONTEKST: {summary}]",
    }

    logger.info(
        "run_compact: compressed %d messages → 1 compact block",
        len(middle),
    )
    return base + [compact_msg] + tail
