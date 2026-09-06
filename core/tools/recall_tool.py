"""`recall` — the one memory-search tool (memory repair 2026-09-04, R5).

Replaces the need to pick between search_memory / search_jarvis_brain /
recall_memories / unified_recall / recall_before_act / memory_*_tier: one
query, every source, one ranked list. The older tools stay callable but
their descriptions point here.
"""
from __future__ import annotations

from typing import Any

RECALL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "recall",
            "description": (
                "Søg i HELE din hukommelse på én gang og få én rangeret liste: "
                "MEMORY.md/USER.md/kuraterede noter/daily notes (workspace), din hjerne "
                "(brain), aktive private-brain-poster, session-resuméer og kronik. "
                "Brug den FØRST når du skal huske noget — beslutninger, fakta, hvad I "
                "talte om, hvad Bjørn har sagt. Valgfrit: sources=[...] for at afgrænse, "
                "eller tilføj 'chat' for at søge i selve chat-historikken."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Hvad du leder efter — spørgsmål, emne, nøgleord",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maks. antal resultater (default 8, maks 50)",
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Delmængde af: workspace, brain, private_brain, session_summary, "
                            "chronicle, chat, sensory. Default = de fem første."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
]


def _exec_recall(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.recall import recall

    query = str(args.get("query") or "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}
    try:
        limit = int(args.get("limit") or 8)
    except (TypeError, ValueError):
        limit = 8
    raw_sources = args.get("sources")
    sources: list[str] | None = None
    if isinstance(raw_sources, str):
        sources = [s.strip() for s in raw_sources.split(",") if s.strip()]
    elif isinstance(raw_sources, list):
        sources = [str(s).strip() for s in raw_sources if str(s).strip()]
    session_id = str(args.get("_runtime_session_id") or "") or None
    return recall(query, limit=limit, sources=sources or None, session_id=session_id)
