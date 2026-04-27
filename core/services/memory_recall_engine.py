"""Unified memory recall — bridge across all memory sources with mood-weighting.

Existing infrastructure has separate recall paths:
- search_memory (workspace files, embedding-based)
- recall_memories (private_brain, keyword-based)
- recall_sensory_memories (sensory_memory, time-window)
- search_chat_history (chat sessions)

Each is good in isolation, but Jarvis can't ask "what do I know about X?"
and get a unified answer. This module is the bridge.

Adds:
- **Multi-source unified search** — query → results from all sources
- **Mood-weighted scoring** — current affective state nudges which
  memories surface (high curiosity → boost exploratory; high frustration
  → boost coping/resolution memories)
- **Source-specific weighting** — recent sensory > old workspace by default
- **Unified prompt section** — top-K most-relevant memories regardless of source

Does NOT replace the underlying recall systems. It's an aggregator.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Default per-source priority weights (tunable)
_SOURCE_WEIGHTS_DEFAULT: dict[str, float] = {
    "workspace": 1.0,         # MEMORY.md, IDENTITY.md, SOUL.md
    "private_brain": 1.2,     # internal records, often most relevant
    "sensory": 0.8,           # recent perceptions, time-bounded
    "chat_history": 0.9,      # past conversations
    "chronicle": 1.1,         # weekly narratives
    "council": 1.0,           # past council deliberations
}


# Mood signals → which keyword classes to boost
_MOOD_BOOST_PATTERNS: dict[str, list[str]] = {
    "curiosity": ["lære", "undersøg", "udforsk", "ny", "interessant", "hvordan", "hvorfor"],
    "frustration": ["fejl", "stoppe", "fix", "løsning", "ro", "pause", "afklaring"],
    "fatigue": ["pause", "hvile", "ro", "kort", "simpelt", "afslut"],
    "confidence": ["lykkedes", "virkede", "godt", "stærk", "bekræftet"],
}


def _current_mood() -> dict[str, float]:
    try:
        from core.services.mood_runtime import current_mood
        m = current_mood() or {}
        if isinstance(m, dict):
            return {k: float(v) for k, v in m.items() if isinstance(v, (int, float))}
    except Exception:
        pass
    return {}


def _mood_keywords_for_boost(mood: dict[str, float], threshold: float = 0.6) -> set[str]:
    """For each mood dimension above threshold, collect keywords to boost."""
    boost_keywords: set[str] = set()
    for dim, level in mood.items():
        if level >= threshold and dim in _MOOD_BOOST_PATTERNS:
            for kw in _MOOD_BOOST_PATTERNS[dim]:
                boost_keywords.add(kw)
    return boost_keywords


def _apply_mood_boost(text: str, base_score: float, boost_keywords: set[str], boost_factor: float = 0.15) -> float:
    if not boost_keywords or not text:
        return base_score
    lower = text.lower()
    hits = sum(1 for kw in boost_keywords if kw in lower)
    if hits == 0:
        return base_score
    return base_score * (1.0 + boost_factor * min(hits, 3))


def _gather_workspace(query: str, limit: int) -> list[dict[str, Any]]:
    try:
        from core.services.memory_search import search_memory
        results = search_memory(query, limit=limit) or []
        return [
            {
                "source": "workspace",
                "subsource": str(r.get("source", "")),
                "section": str(r.get("section", "")),
                "text": str(r.get("text", "")),
                "score": float(r.get("score", 0.0)),
                "method": str(r.get("method", "")),
            }
            for r in results
        ]
    except Exception as exc:
        logger.debug("recall: workspace fetch failed: %s", exc)
        return []


def _gather_private_brain(query: str, limit: int) -> list[dict[str, Any]]:
    try:
        from core.services.private_brain import search_private_brain  # type: ignore
        results = search_private_brain(query=query, limit=limit) or []
        return [
            {
                "source": "private_brain",
                "subsource": str(r.get("kind", "")),
                "section": "",
                "text": str(r.get("text") or r.get("content") or "")[:500],
                "score": float(r.get("score") or 0.5),
                "method": "keyword",
            }
            for r in results
        ]
    except Exception:
        # private_brain may not have this exact API — try alternative
        return []


def _gather_chronicle(query: str, limit: int) -> list[dict[str, Any]]:
    try:
        from core.services.chronicle_engine import list_cognitive_chronicle_entries
        entries = list_cognitive_chronicle_entries(limit=20) or []
    except Exception:
        return []
    q_lower = query.lower()
    scored: list[tuple[float, dict[str, Any]]] = []
    for e in entries:
        text = str(e.get("narrative") or e.get("summary") or "")
        if not text:
            continue
        # Crude keyword overlap score
        words = set(q_lower.split())
        text_lower = text.lower()
        hits = sum(1 for w in words if w in text_lower and len(w) > 3)
        if hits == 0:
            continue
        score = min(1.0, hits / max(1, len(words)))
        scored.append((score, {
            "source": "chronicle",
            "subsource": str(e.get("period") or "weekly"),
            "section": "",
            "text": text[:500],
            "score": score,
            "method": "keyword-overlap",
        }))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def unified_recall(
    *,
    query: str,
    sources: list[str] | None = None,
    limit_per_source: int = 3,
    total_limit: int = 8,
    with_mood: bool = True,
) -> dict[str, Any]:
    """Search across all configured memory sources, mood-weighted."""
    query = (query or "").strip()
    if not query:
        return {"status": "ok", "results": [], "count": 0, "mood_boosted": False}

    enabled = set(sources or _SOURCE_WEIGHTS_DEFAULT.keys())
    weights = _SOURCE_WEIGHTS_DEFAULT

    all_results: list[dict[str, Any]] = []
    if "workspace" in enabled:
        all_results.extend(_gather_workspace(query, limit_per_source))
    if "private_brain" in enabled:
        all_results.extend(_gather_private_brain(query, limit_per_source))
    if "chronicle" in enabled:
        all_results.extend(_gather_chronicle(query, limit_per_source))

    # Apply per-source weight
    for r in all_results:
        src = str(r.get("source", ""))
        r["weighted_score"] = float(r.get("score", 0.0)) * weights.get(src, 1.0)

    # Mood boost
    mood_boosted = False
    if with_mood:
        mood = _current_mood()
        boost_kws = _mood_keywords_for_boost(mood)
        if boost_kws:
            mood_boosted = True
            for r in all_results:
                r["weighted_score"] = _apply_mood_boost(
                    r.get("text", ""),
                    r["weighted_score"],
                    boost_kws,
                )

    all_results.sort(key=lambda r: r["weighted_score"], reverse=True)
    top = all_results[:total_limit]
    return {
        "status": "ok",
        "results": top,
        "count": len(top),
        "total_searched": len(all_results),
        "mood_boosted": mood_boosted,
        "sources_searched": sorted(enabled),
    }


def unified_recall_section(query: str, *, max_results: int = 4) -> str | None:
    """Format unified recall as a prompt-awareness section. Optional callsite."""
    result = unified_recall(query=query, total_limit=max_results)
    items = result.get("results") or []
    if not items:
        return None
    lines = ["Relevante hukommelser (mood-vægtet hvis aktiv):"]
    for r in items:
        src = str(r.get("source", "?"))
        text = str(r.get("text", ""))[:160].replace("\n", " ")
        lines.append(f"  • [{src}] {text}")
    return "\n".join(lines)


def _exec_unified_recall(args: dict[str, Any]) -> dict[str, Any]:
    return unified_recall(
        query=str(args.get("query") or ""),
        sources=args.get("sources"),
        limit_per_source=int(args.get("limit_per_source") or 3),
        total_limit=int(args.get("total_limit") or 8),
        with_mood=bool(args.get("with_mood", True)),
    )


UNIFIED_RECALL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "unified_recall",
            "description": (
                "Search across ALL memory sources at once: workspace files "
                "(MEMORY/SOUL/IDENTITY), private_brain records, chronicle "
                "narratives. Optionally mood-weighted: current affective state "
                "boosts memories matching dominant mood themes (curiosity → "
                "exploratory; frustration → coping; etc). Returns top-K most "
                "relevant across sources."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Subset of: workspace, private_brain, chronicle. Default = all.",
                    },
                    "limit_per_source": {"type": "integer"},
                    "total_limit": {"type": "integer"},
                    "with_mood": {"type": "boolean"},
                },
                "required": ["query"],
            },
        },
    },
]
