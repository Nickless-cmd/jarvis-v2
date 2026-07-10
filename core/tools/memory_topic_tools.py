"""Kuraterede memory-topic-tools (spec 2026-07-10 Spec B).

To tynde tool-adaptere over core.memory.memory_topic_store: læs en topic-krop
on-demand (pull, LLM-led) og skriv/opdatér en topic med streng bekraeftelse.
Begge er scoped til den aktuelle bruger via workspace-resolution i store'et —
ingen hardkodet default, ingen cross-user-adgang.
"""
from __future__ import annotations
from typing import Any


def _exec_read_memory_topic(args: dict) -> dict:
    """Læs en kurateret memory-topic-fil (pull, LLM-led). Scoped til aktuel bruger."""
    from core.memory.memory_topic_store import read_topic
    slug = str((args or {}).get("slug") or "")
    content = read_topic(slug)
    if content is None:
        return {"found": False, "slug": slug, "content": ""}
    return {"found": True, "slug": slug, "content": content}


def _exec_write_memory_topic(args: dict) -> dict:
    """Skriv/opdatér en kurateret memory-topic (streng bekraeftelse). Scoped til bruger."""
    from core.memory.memory_topic_store import write_topic_confirmed
    a = args or {}
    return write_topic_confirmed(
        str(a.get("slug") or ""),
        title=str(a.get("title") or ""),
        hook=str(a.get("hook") or ""),
        body=str(a.get("body") or ""),
    )


MEMORY_TOPIC_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_memory_topic",
            "description": (
                "Read a curated memory topic file on demand. The always-loaded "
                "index lists topics one-per-line; pull the full body by slug when "
                "you need it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": "Topic slug from the curated memory index, e.g. 'project-alpha'.",
                    },
                },
                "required": ["slug"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_memory_topic",
            "description": (
                "Create/update a curated memory topic. The index one-liner is "
                "updated only on a confirmed body-write; never report 'saved' on "
                "confirmed=False."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Stable topic slug ([a-z0-9_-]); reused to update in place."},
                    "title": {"type": "string", "description": "Human-readable topic title for the index line."},
                    "hook": {"type": "string", "description": "One-line summary shown in the always-loaded index."},
                    "body": {"type": "string", "description": "Full markdown body stored on-demand in curated/<slug>.md."},
                },
                "required": ["slug", "title", "body"],
            },
        },
    },
]
