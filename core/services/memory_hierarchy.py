"""Memory hierarchy — explicit hot/warm/cold tiers + recall-before-act.

Existing memory infrastructure has many sources but no explicit tier
structure. This module formalises three tiers (per Jarvis' implementation
plan):

- **Hot** — currently in active context: session messages, current goals,
  recent eventbus, active reflection. Read every tick.
- **Warm** — curated and always available: MEMORY.md, USER.md, IDENTITY.md,
  active goal list, recent chronicle entries. Pulled on demand, cheap.
- **Cold** — semantic-search territory: full chronicle history, sensory
  archive, private brain records, dream hypotheses. Only fetched when
  query is specific.

Adds **recall-before-act** pattern: before each heartbeat tick (or major
action), automatically pull warm + targeted-cold memories matching the
goal/priority context. Adds them to the act-phase context.

Doesn't move data — tiers are derivative classifications. Existing
recall paths still work; this module orchestrates them.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Tier classification ──────────────────────────────────────────────


def _hot_tier_snapshot() -> dict[str, Any]:
    """In-context-now: signals + active state."""
    snapshot: dict[str, Any] = {"tier": "hot"}
    try:
        from core.services.heartbeat_phases import sense_phase
        signals = sense_phase()
        snapshot["signals"] = {
            k: v for k, v in signals.items()
            if k in ("mood_name", "mood_intensity", "active_goals",
                     "events_last_hour", "context_pressure_level")
        }
    except Exception:
        pass
    return snapshot


def _warm_tier_snapshot(*, query: str = "") -> dict[str, Any]:
    """Curated, always-available: workspace files + active goals + chronicle excerpt."""
    snapshot: dict[str, Any] = {"tier": "warm", "query": query}
    try:
        from core.services.autonomous_goals import list_goals
        active = list_goals(status="active", parent_id="any", limit=5)
        snapshot["active_goals"] = [
            {"title": g.get("title"), "priority": g.get("priority")}
            for g in active
        ]
    except Exception:
        snapshot["active_goals"] = []

    if query:
        try:
            from core.services.memory_search import search_memory
            results = search_memory(query, limit=4) or []
            snapshot["workspace_hits"] = [
                {"source": r.get("source"), "section": r.get("section"),
                 "text": str(r.get("text", ""))[:200]}
                for r in results
            ]
        except Exception:
            snapshot["workspace_hits"] = []

    try:
        from core.services.chronicle_engine import get_chronicle_context_for_prompt
        snapshot["chronicle_excerpt"] = get_chronicle_context_for_prompt(n=2, max_chars=600) or ""
    except Exception:
        snapshot["chronicle_excerpt"] = ""

    return snapshot


def _cold_tier_search(*, query: str, max_results: int = 6) -> dict[str, Any]:
    """Semantic-search across full archive — only invoked when query is specific."""
    snapshot: dict[str, Any] = {"tier": "cold", "query": query, "results": []}
    if not query or len(query) < 3:
        return snapshot
    try:
        from core.services.memory_recall_engine import unified_recall
        result = unified_recall(query=query, total_limit=max_results, with_mood=True)
        snapshot["results"] = [
            {
                "source": r.get("source"),
                "text": str(r.get("text", ""))[:240],
                "score": r.get("weighted_score", r.get("score", 0)),
            }
            for r in (result.get("results") or [])
        ]
        snapshot["mood_boosted"] = bool(result.get("mood_boosted"))
    except Exception as exc:
        logger.debug("cold tier search failed: %s", exc)
    return snapshot


# ── Recall-before-act orchestrator ──────────────────────────────────


def recall_before_act(
    *,
    query: str = "",
    include_cold: bool = True,
    cold_max: int = 6,
) -> dict[str, Any]:
    """Compose hot+warm+(optional cold) tier snapshot before an action."""
    composed: dict[str, Any] = {
        "hot": _hot_tier_snapshot(),
        "warm": _warm_tier_snapshot(query=query),
    }
    if include_cold and query:
        composed["cold"] = _cold_tier_search(query=query, max_results=cold_max)
    return composed


def recall_before_act_summary(query: str = "") -> str | None:
    """Compact text summary of recall-before-act for prompt awareness."""
    bundle = recall_before_act(query=query, include_cold=bool(query))
    parts: list[str] = []

    hot = bundle.get("hot", {}).get("signals", {})
    if hot.get("active_goals"):
        goal_titles = [g.get("title", "") for g in (hot.get("active_goals") or [])][:3]
        parts.append(f"🎯 Aktive: {'; '.join(goal_titles)}")

    warm = bundle.get("warm", {})
    if warm.get("workspace_hits"):
        hit_count = len(warm["workspace_hits"])
        parts.append(f"📚 Warm-tier: {hit_count} workspace-træf")

    cold = bundle.get("cold", {})
    if cold.get("results"):
        results = cold["results"]
        if results:
            parts.append(f"🔍 Cold-tier ({len(results)}):")
            for r in results[:2]:
                src = str(r.get("source", "?"))
                txt = str(r.get("text", ""))[:120]
                parts.append(f"   • [{src}] {txt}")

    if not parts:
        return None
    return "Recall-before-act:\n" + "\n".join(parts)


# ── Tools ──────────────────────────────────────────────────────────


def _exec_recall_before_act(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "bundle": recall_before_act(
            query=str(args.get("query") or ""),
            include_cold=bool(args.get("include_cold", True)),
            cold_max=int(args.get("cold_max") or 6),
        ),
    }


def _exec_hot_tier(args: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "snapshot": _hot_tier_snapshot()}


def _exec_warm_tier(args: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "snapshot": _warm_tier_snapshot(query=str(args.get("query") or ""))}


def _exec_cold_tier(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "snapshot": _cold_tier_search(
            query=str(args.get("query") or ""),
            max_results=int(args.get("max_results") or 6),
        ),
    }


MEMORY_HIERARCHY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "recall_before_act",
            "description": (
                "Compose hot (current signals) + warm (workspace + goals + "
                "chronicle) + cold (full semantic search) memory bundle "
                "before an action. Use BEFORE major decisions or sub-agent "
                "spawns to ensure relevant past context surfaces."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query for warm/cold tier semantic search."},
                    "include_cold": {"type": "boolean"},
                    "cold_max": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_hot_tier",
            "description": "Read hot-tier snapshot only (signals + active state). Cheap, no I/O.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_warm_tier",
            "description": "Read warm-tier (workspace + goals + chronicle excerpt). Pass query for workspace search.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_cold_tier",
            "description": "Cold-tier semantic search across full archive. Only invoke with specific query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
]
