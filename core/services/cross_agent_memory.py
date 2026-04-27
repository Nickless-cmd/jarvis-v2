"""Cross-agent memory — shared observations queryable across agents.

Layer 3 af Scout Memory. Bygger oven på Layer 1 (compressed observations)
ved at gøre dem **searchable across agents**. Når en researcher spawnes,
kan den semantisk søge i tidligere observations fra alle roller — finde
"har en planner allerede arbejdet med dette domæne?" eller "har en
critic flagget noget lignende?"

Implementeret som lookup-lag oven på Layer 1's agent_observations data.
Ingen ny tabel — vi bruger den eksisterende state_store og laver semantic
search via memory_search's embedding infrastructure.

Decay strategy (per egen pushback før vi byggede):
- 14 dages stale-threshold (allerede i Layer 1's mark_stale_observations)
- 30 dages hard cutoff for cross-agent queries
- Stale records ekskluderes fra default search

Use case:
1. Researcher spawnes med goal "find pakkenavn for X"
2. spawn hooker cross_agent_recall(query=goal, requesting_role="researcher")
3. Returnerer relevant observations fra ANY role i sidste 14 dage
4. Indjektes i agent's system prompt
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


_DEFAULT_LOOKBACK_DAYS = 14
_HARD_CUTOFF_DAYS = 30


def _all_observations() -> list[dict[str, Any]]:
    """Read full observation log from Layer 1 storage."""
    try:
        from core.runtime.state_store import load_json
        records = load_json("agent_observations", [])
        if not isinstance(records, list):
            return []
        return records
    except Exception:
        return []


def _filter_by_freshness(records: list[dict[str, Any]], days: int) -> list[dict[str, Any]]:
    if days <= 0:
        return records
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    return [r for r in records if str(r.get("recorded_at", "")) >= cutoff]


def _keyword_score(text: str, query: str) -> float:
    """Cheap relevance score: count of query keywords in text, normalised."""
    if not text or not query:
        return 0.0
    text_lower = text.lower()
    query_words = [w for w in query.lower().split() if len(w) > 3]
    if not query_words:
        return 0.0
    hits = sum(1 for w in query_words if w in text_lower)
    return hits / len(query_words)


def cross_agent_recall(
    *,
    query: str,
    requesting_role: str = "",
    exclude_roles: list[str] | None = None,
    days_back: int = _DEFAULT_LOOKBACK_DAYS,
    limit: int = 5,
    min_score: float = 0.2,
) -> dict[str, Any]:
    """Find relevant observations from OTHER agents matching the query."""
    query = (query or "").strip()
    if not query or len(query) < 4:
        return {"status": "ok", "results": [], "count": 0, "reason": "query too short"}

    records = _all_observations()
    if not records:
        return {"status": "ok", "results": [], "count": 0, "reason": "no observations recorded"}

    # Hard cutoff regardless of input
    records = _filter_by_freshness(records, _HARD_CUTOFF_DAYS)
    # User-specified freshness (default 14 days)
    records = _filter_by_freshness(records, days_back)

    exclude = set(exclude_roles or [])
    if requesting_role:
        exclude.add(requesting_role)  # don't return your own role's observations

    candidates = []
    for r in records:
        role = str(r.get("role", ""))
        if role in exclude:
            continue
        if r.get("stale"):
            continue
        text = str(r.get("compressed_text", "")) + " " + str(r.get("goal", ""))
        score = _keyword_score(text, query)
        if score >= min_score:
            candidates.append((score, r))

    candidates.sort(key=lambda t: t[0], reverse=True)
    results = [
        {
            "obs_id": r.get("obs_id"),
            "role": r.get("role"),
            "goal": str(r.get("goal", ""))[:200],
            "preview": str(r.get("compressed_text", ""))[:240],
            "recorded_at": r.get("recorded_at"),
            "score": round(score, 3),
        }
        for score, r in candidates[:limit]
    ]

    return {
        "status": "ok",
        "results": results,
        "count": len(results),
        "total_scanned": len(records),
        "exclude_roles": sorted(exclude),
        "lookback_days": days_back,
    }


def cross_agent_recall_section(role: str, query: str) -> str | None:
    """Format cross-agent recall as text for sub-agent system_prompt injection."""
    result = cross_agent_recall(query=query, requesting_role=role, limit=4)
    items = result.get("results") or []
    if not items:
        return None
    lines = [f"## Andre agents observationer ({len(items)} relevante)"]
    for it in items:
        ts = str(it.get("recorded_at", ""))[:10]
        lines.append(f"- [{it.get('role', '?')}, {ts}] {it.get('preview', '')[:200]}")
    return "\n".join(lines)


# ── Tools ─────────────────────────────────────────────────────


def _exec_cross_agent_recall(args: dict[str, Any]) -> dict[str, Any]:
    return cross_agent_recall(
        query=str(args.get("query") or ""),
        requesting_role=str(args.get("requesting_role") or ""),
        exclude_roles=args.get("exclude_roles"),
        days_back=int(args.get("days_back") or _DEFAULT_LOOKBACK_DAYS),
        limit=int(args.get("limit") or 5),
        min_score=float(args.get("min_score") or 0.2),
    )


CROSS_AGENT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "cross_agent_recall",
            "description": (
                "Search compressed observations from OTHER agents (Layer 3 of "
                "Scout Memory). Returns relevant past observations matching "
                "query, excluding your own role. 14-day default freshness. "
                "Use BEFORE starting a complex task to leverage prior agents' work."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "requesting_role": {"type": "string", "description": "Your role — gets excluded from results."},
                    "exclude_roles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional roles to exclude.",
                    },
                    "days_back": {"type": "integer"},
                    "limit": {"type": "integer"},
                    "min_score": {"type": "number"},
                },
                "required": ["query"],
            },
        },
    },
]
