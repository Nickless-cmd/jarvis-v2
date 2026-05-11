"""Reasoning Store tools for Jarvis — Phase 1 Generalized Learning.

Provides recall_reasoning as a native runtime tool for semantic retrieval
of reasoning conclusions across sessions.
"""

from __future__ import annotations

from typing import Any

from core.services.reasoning_store import capture_conclusion, recall_reasoning


# ---------------------------------------------------------------------------
# Executor functions
# ---------------------------------------------------------------------------


def _exec_recall_reasoning(args: dict[str, Any]) -> dict[str, Any]:
    """Retrieve stored reasoning conclusions, ranked by relevance.

    Args:
        query: Natural language query for semantic matching.
        source: Optional filter by source type
            (deep_analyze|reasoning_classify|self_evaluation|counterfactual|agent_run|learning_policy).
        min_confidence: Minimum confidence threshold 0.0-1.0 (default 0.0).
        limit: Max results (default 5, max 20).
        days_back: Max age in days (default 30, None = no limit).
    """
    query = args.get("query", "")
    source = args.get("source")
    min_confidence = float(args.get("min_confidence", 0.0))
    limit = min(int(args.get("limit", 5)), 20)
    days_back = args.get("days_back")
    if days_back is not None:
        days_back = int(days_back)

    try:
        results = recall_reasoning(
            query_text=query or None,
            query_embedding=None,
            source_filter=source or None,
            min_confidence=min_confidence,
            limit=limit,
            days_back=days_back,
        )

        if not results:
            return {"status": "ok", "text": "No matching reasoning conclusions found.", "results": []}

        lines = [f"Found {len(results)} reasoning conclusion(s):"]
        for r in results:
            score_str = f" [score={r['score']}]" if r.get("score", 0) > 0 else ""
            lines.append(
                f"\n• **{r['source']}** (conf={r['confidence']:.2f}{score_str})"
                f"\n  {r['conclusion_text'][:300]}"
                f"\n  _context: {r.get('context', '') or '—'}_"
                f"\n  _{r['created_at'][:19]}_"
            )

        return {
            "status": "ok",
            "text": "\n".join(lines),
            "results": results,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Tool definitions (Ollama-compatible JSON schemas)
# ---------------------------------------------------------------------------

REASONING_STORE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "recall_reasoning",
            "description": (
                "Retrieve stored reasoning conclusions from deep_analyze, "
                "reasoning_classify, self_evaluation, counterfactuals, and agent runs. "
                "Results are ranked by recency. Use this to recall past insights, "
                "conclusions, or reasoning traces across sessions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query for matching relevant conclusions.",
                    },
                    "source": {
                        "type": "string",
                        "description": "Filter by source: deep_analyze|reasoning_classify|self_evaluation|counterfactual|agent_run|learning_policy",
                        "enum": [
                            "deep_analyze",
                            "reasoning_classify",
                            "self_evaluation",
                            "counterfactual",
                            "agent_run",
                            "learning_policy",
                        ],
                    },
                    "min_confidence": {
                        "type": "number",
                        "description": "Minimum confidence threshold 0.0-1.0 (default 0.0).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 5, max 20).",
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Max age in days (default 30, null = no limit).",
                    },
                },
            },
        },
    },
]
