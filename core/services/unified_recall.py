"""Unified recall — krydsreference mellem hukommelsessystemer.

Jarvis har tre hukommelsessystemer der ikke taler sammen:
1. search_memory() — MEMORY.md, USER.md, SOUL.md (tekst + embeddings)
2. search_jarvis_brain() — private brain (embeddings)
3. recall_memories() — Sansernes Arkiv (sensory memories)

Dette modul er en koordinator, ikke et nyt lag. Den søger på tværs
og returnerer hvilke systemer der har data om et emne — uden at
duplikere eller fusionere indhold.

Self-safe: hvert system kaldes uafhængigt med try/except. Hvis et
system fejler, returneres det som utilgængeligt, men de andre
systemers resultater bevares.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def unified_recall(query: str, *, limit: int = 5) -> dict[str, dict[str, Any]]:
    """Søg på tværs af alle 3 hukommelsessystemer.

    Returnerer: {normaliseret_emne: {memory_md: bool, brain: bool, arkiv: bool, last_seen: iso | None}}
    Hvis et system er utilgængeligt, sættes værdien til None (ikke False).
    """
    if not query or not query.strip():
        return {}

    query = query.strip()[:200]  # trunker meget lange queries

    results: dict[str, dict[str, Any]] = {}

    # System 1: search_memory (MEMORY.md, USER.md, SOUL.md)
    memory_hits = _safe_search_memory(query, limit)
    for hit in memory_hits:
        topic = _extract_topic(hit)
        if topic not in results:
            results[topic] = _empty_entry()
        results[topic]["memory_md"] = True
        results[topic]["last_seen"] = _latest_timestamp(
            results[topic]["last_seen"], hit
        )

    # System 2: search_jarvis_brain (private brain)
    brain_hits = _safe_search_brain(query, limit)
    for hit in brain_hits:
        topic = _extract_topic(hit)
        if topic not in results:
            results[topic] = _empty_entry()
        results[topic]["brain"] = True
        results[topic]["last_seen"] = _latest_timestamp(
            results[topic]["last_seen"], hit
        )

    # System 3: recall_memories (Sansernes Arkiv)
    arkiv_hits = _safe_recall_memories(query, limit)
    for hit in arkiv_hits:
        topic = _extract_topic(hit)
        if topic not in results:
            results[topic] = _empty_entry()
        results[topic]["arkiv"] = True
        results[topic]["last_seen"] = _latest_timestamp(
            results[topic]["last_seen"], hit
        )

    return results


def get_unified_recall_hints(query: str | None = None, *, limit: int = 3) -> list[str]:
    """Korte hints til prompt-kontekst.

    Returnerer max `limit` hints à max 80 tegn, fx:
    - "Bjørn findes i brain + arkiv"
    - "Central findes kun i MEMORY.md"

    Hvis query er None, returneres tom liste (ingen aktiv samtale).
    """
    if not query or not query.strip():
        return []

    results = unified_recall(query, limit=10)

    hints: list[str] = []
    for topic, systems in results.items():
        if len(hints) >= limit:
            break
        sources: list[str] = []
        if systems.get("memory_md"):
            sources.append("MEMORY")
        if systems.get("brain"):
            sources.append("brain")
        if systems.get("arkiv"):
            sources.append("arkiv")

        if not sources:
            continue

        # None betyder utilgængeligt — marker det
        unavailable: list[str] = []
        if systems.get("memory_md") is None:
            unavailable.append("MEMORY")
        if systems.get("brain") is None:
            unavailable.append("brain")
        if systems.get("arkiv") is None:
            unavailable.append("arkiv")

        hint = f"{topic} findes i {' + '.join(sources)}"
        if unavailable:
            hint += f" ({', '.join(unavailable)} n/a)"

        hints.append(hint[:80])

    return hints


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _empty_entry() -> dict[str, Any]:
    return {
        "memory_md": False,
        "brain": False,
        "arkiv": False,
        "last_seen": None,
    }


def _extract_topic(hit: dict) -> str:
    """Extract a short topic key from a search hit.

    Uses 'title' if available, then 'heading', then falls back to
    truncating 'content' or 'excerpt'.
    """
    for key in ("title", "heading", "domain"):
        val = hit.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()[:60]

    # Fallback: first 40 chars of content/excerpt
    for key in ("content", "excerpt", "text"):
        val = hit.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()[:40]

    return "ukendt"


def _latest_timestamp(current: str | None, hit: dict) -> str | None:
    """Return the most recent ISO timestamp between current and hit."""
    hit_ts = hit.get("created_at") or hit.get("timestamp") or hit.get("ts")
    if not hit_ts:
        return current
    if not current:
        return str(hit_ts)
    # Keep the more recent one
    try:
        if str(hit_ts) > current:
            return str(hit_ts)
    except Exception:
        pass
    return current


def _safe_search_memory(query: str, limit: int) -> list[dict]:
    """Search MEMORY.md / USER.md / SOUL.md. Returns empty list on failure."""
    try:
        from core.services.memory_search import search_memory
        results = search_memory(query, limit=limit)
        if isinstance(results, list):
            return results
        return []
    except Exception:
        logger.debug("unified_recall: search_memory failed", exc_info=True)
        return []


def _safe_search_brain(query: str, limit: int) -> list[dict]:
    """Search private brain. Returns empty list on failure."""
    try:
        from core.tools.jarvis_brain_tools import search_jarvis_brain
        results = search_jarvis_brain(query, limit=limit)
        if isinstance(results, list):
            return results
        return []
    except Exception:
        logger.debug("unified_recall: search_jarvis_brain failed", exc_info=True)
        return []


def _safe_recall_memories(query: str, limit: int) -> list[dict]:
    """Search Sansernes Arkiv. Returns empty list on failure."""
    try:
        from core.tools.recall_memory_tools import _exec_recall_memories
        result = _exec_recall_memories({
            "query": query,
            "limit": limit,
            "min_score": 0.35,
        })
        if isinstance(result, dict) and "results" in result:
            return result["results"]
        return []
    except Exception:
        logger.debug("unified_recall: recall_memories failed", exc_info=True)
        return []