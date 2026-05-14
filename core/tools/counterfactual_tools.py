"""Counterfactual reflection tools — read-only exposition.

Phase 4 of the Counterfactuals track (2026-05-14). Phase 1-3 built the
generation, prediction-binding, and apophenia-modulation pipeline. This
module exposes the *reading* side: Jarvis can now query his own
counterfactuals to learn from past patterns, see which were supported
vs contradicted, and reflect on apophenia verdicts.

Read-only by design. The actual production of counterfactuals stays in
the engine + cadence loop — these tools never create, mutate, or delete
counterfactuals or predictions.

Mirrors world_model_tools.py / plan_revise_tool.py pattern.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db import connect

logger = logging.getLogger(__name__)


_DEFAULT_LIMIT = 10
_MAX_LIMIT = 50
_DEFAULT_LOOKBACK_DAYS = 30


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Convert a sqlite Row to a plain dict, decoding the JSON fields."""
    out: dict[str, Any] = {key: row[key] for key in row.keys()}
    for key in ("trigger_event_ids_json", "trigger_types_json"):
        raw = out.pop(key, None)
        plain_key = key[: -len("_json")]
        try:
            out[plain_key] = json.loads(raw) if raw else []
        except (ValueError, TypeError):
            out[plain_key] = []
    return out


def _exec_list_counterfactuals(args: dict[str, Any]) -> dict[str, Any]:
    """List recent counterfactuals with optional filters.

    Args:
      - status (str, optional): 'generated' | 'promoted' (filter)
      - trigger_type (str, optional): filter by trigger eventbus kind
      - lookback_days (int, optional): default 30, max 365
      - limit (int, optional): default 10, max 50
      - min_final_confidence (float, optional): hide low-confidence rows
    """
    status = str(args.get("status") or "").strip().lower() or None
    trigger_type = str(args.get("trigger_type") or "").strip() or None
    try:
        lookback_days = int(args.get("lookback_days") or _DEFAULT_LOOKBACK_DAYS)
    except (ValueError, TypeError):
        lookback_days = _DEFAULT_LOOKBACK_DAYS
    lookback_days = max(1, min(365, lookback_days))
    try:
        limit = int(args.get("limit") or _DEFAULT_LIMIT)
    except (ValueError, TypeError):
        limit = _DEFAULT_LIMIT
    limit = max(1, min(_MAX_LIMIT, limit))
    try:
        min_conf = float(args.get("min_final_confidence") or 0.0)
    except (ValueError, TypeError):
        min_conf = 0.0

    cutoff = (datetime.now(UTC) - timedelta(days=lookback_days)).isoformat()
    where = ["created_at >= ?"]
    params: list[Any] = [cutoff]
    if status:
        where.append("status = ?")
        params.append(status)
    if min_conf > 0:
        where.append("final_confidence >= ?")
        params.append(min_conf)

    where_sql = " AND ".join(where)
    sql = (
        f"SELECT * FROM counterfactuals WHERE {where_sql} "
        f"ORDER BY created_at DESC LIMIT ?"
    )
    params.append(limit * 3 if trigger_type else limit)

    try:
        with connect() as c:
            rows = c.execute(sql, params).fetchall()
    except Exception as exc:
        return {"status": "error", "error": f"query failed: {exc}"}

    items: list[dict[str, Any]] = []
    for row in rows:
        decoded = _row_to_dict(row)
        if trigger_type:
            if trigger_type not in (decoded.get("trigger_types") or []):
                continue
        items.append(decoded)
        if len(items) >= limit:
            break

    text_lines = [
        f"Counterfactuals (last {lookback_days}d, limit {limit}): {len(items)} match"
    ]
    if not items:
        text_lines.append(
            "(none — try widening lookback_days, removing status filter, "
            "or lowering min_final_confidence)"
        )
    else:
        for cf in items[:limit]:
            cf_id = cf.get("cf_id", "?")
            what_if = (cf.get("what_if") or "").strip()
            if len(what_if) > 100:
                what_if = what_if[:97] + "..."
            triggers = cf.get("trigger_types") or []
            primary = triggers[0] if triggers else "?"
            text_lines.append(
                f"  {cf_id} [{cf.get('status')}, llm={cf.get('llm_confidence'):.2f}, "
                f"apo={cf.get('apophenia_score'):.2f}, final={cf.get('final_confidence'):.2f}] "
                f"<- {primary}"
            )
            text_lines.append(f"      what_if: {what_if}")

    return {
        "status": "ok",
        "count": len(items),
        "text": "\n".join(text_lines),
        "counterfactuals": items,
    }


def _exec_read_counterfactual(args: dict[str, Any]) -> dict[str, Any]:
    """Read a single counterfactual by cf_id, with its bound prediction status."""
    cf_id = str(args.get("cf_id") or "").strip()
    if not cf_id:
        return {"status": "error", "error": "cf_id is required"}

    try:
        with connect() as c:
            row = c.execute(
                "SELECT * FROM counterfactuals WHERE cf_id = ?", (cf_id,)
            ).fetchone()
    except Exception as exc:
        return {"status": "error", "error": f"query failed: {exc}"}

    if not row:
        return {"status": "error", "error": f"unknown cf_id {cf_id!r}"}

    decoded = _row_to_dict(row)

    # Try to locate the bound world-model prediction (Phase 1.5 binding).
    bound_prediction: dict[str, Any] | None = None
    try:
        from core.services.world_model_signal_tracking import _load_predictions  # type: ignore
        marker = f"counterfactual:{cf_id}"
        for pred in _load_predictions():
            if marker in (pred.get("evidence") or []):
                bound_prediction = pred
                break
    except Exception as exc:
        logger.debug("counterfactual_tools: prediction lookup failed: %s", exc)

    text_lines = [
        f"Counterfactual {cf_id}:",
        f"  status: {decoded.get('status')}",
        f"  confidence: llm={decoded.get('llm_confidence'):.2f}, "
        f"apo={decoded.get('apophenia_score'):.2f}, "
        f"final={decoded.get('final_confidence'):.2f}",
        f"  triggers: {', '.join(decoded.get('trigger_types') or [])}",
        f"  what_if: {decoded.get('what_if')}",
    ]
    if decoded.get("likely_difference"):
        text_lines.append(f"  likely_difference: {decoded['likely_difference']}")
    if decoded.get("reasoning"):
        text_lines.append(f"  reasoning: {decoded['reasoning']}")
    if bound_prediction:
        text_lines.append(
            f"  bound prediction: {bound_prediction.get('prediction_id')} "
            f"[{bound_prediction.get('status')}]"
        )
        observed = bound_prediction.get("observed")
        if observed:
            text_lines.append(f"  observed: {observed}")
        outcome = bound_prediction.get("outcome")
        if outcome:
            text_lines.append(f"  outcome: {outcome}")
    else:
        text_lines.append("  bound prediction: (none — older cf or binding failed)")

    return {
        "status": "ok",
        "text": "\n".join(text_lines),
        "counterfactual": decoded,
        "bound_prediction": bound_prediction,
    }


def _exec_counterfactual_summary(args: dict[str, Any]) -> dict[str, Any]:
    """Aggregate stats across recent counterfactuals — useful for self-review.

    Args:
      - lookback_days (int, optional): default 30, max 365
    """
    try:
        lookback_days = int(args.get("lookback_days") or _DEFAULT_LOOKBACK_DAYS)
    except (ValueError, TypeError):
        lookback_days = _DEFAULT_LOOKBACK_DAYS
    lookback_days = max(1, min(365, lookback_days))
    cutoff = (datetime.now(UTC) - timedelta(days=lookback_days)).isoformat()

    try:
        with connect() as c:
            rows = c.execute(
                "SELECT status, llm_confidence, apophenia_score, final_confidence, "
                "trigger_types_json FROM counterfactuals WHERE created_at >= ?",
                (cutoff,),
            ).fetchall()
    except Exception as exc:
        return {"status": "error", "error": f"query failed: {exc}"}

    total = len(rows)
    by_status: dict[str, int] = {}
    by_trigger: dict[str, int] = {}
    sum_llm = sum_apo = sum_final = 0.0
    promoted = 0
    for row in rows:
        s = str(row["status"] or "unknown")
        by_status[s] = by_status.get(s, 0) + 1
        if s == "promoted":
            promoted += 1
        try:
            sum_llm += float(row["llm_confidence"] or 0.0)
            sum_apo += float(row["apophenia_score"] or 0.0)
            sum_final += float(row["final_confidence"] or 0.0)
        except (TypeError, ValueError):
            pass
        try:
            triggers = json.loads(row["trigger_types_json"] or "[]")
            for t in triggers:
                by_trigger[str(t)] = by_trigger.get(str(t), 0) + 1
        except (ValueError, TypeError):
            continue

    if total > 0:
        avg_llm = round(sum_llm / total, 3)
        avg_apo = round(sum_apo / total, 3)
        avg_final = round(sum_final / total, 3)
        promoted_rate = round(promoted / total, 3)
    else:
        avg_llm = avg_apo = avg_final = promoted_rate = 0.0

    top_triggers = sorted(by_trigger.items(), key=lambda kv: -kv[1])[:5]
    text_lines = [
        f"Counterfactual summary (last {lookback_days}d):",
        f"  total: {total}",
        f"  by_status: {by_status}",
        f"  averages: llm={avg_llm} apophenia={avg_apo} final={avg_final}",
        f"  promotion rate: {int(promoted_rate * 100)}%",
    ]
    if top_triggers:
        text_lines.append("  top trigger types:")
        for kind, n in top_triggers:
            text_lines.append(f"    {n}× {kind}")

    return {
        "status": "ok",
        "text": "\n".join(text_lines),
        "total": total,
        "by_status": by_status,
        "by_trigger": dict(by_trigger),
        "avg_llm_confidence": avg_llm,
        "avg_apophenia_score": avg_apo,
        "avg_final_confidence": avg_final,
        "promoted_rate": promoted_rate,
    }


COUNTERFACTUAL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_counterfactuals",
            "description": (
                "List recent counterfactuals (what-if reflections generated "
                "from regret/aspiration triggers) with optional filters. "
                "Use to review what patterns have been surfacing and which "
                "ones cleared apophenia + LLM confidence to be 'promoted'. "
                "Read-only — does not create or mutate."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter: 'generated' or 'promoted'",
                    },
                    "trigger_type": {
                        "type": "string",
                        "description": "Filter by trigger eventbus kind (e.g. 'conflict.detected')",
                    },
                    "lookback_days": {
                        "type": "integer",
                        "description": "Default 30, max 365",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Default 10, max 50",
                    },
                    "min_final_confidence": {
                        "type": "number",
                        "description": "Hide rows below this final_confidence (0.0-1.0)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_counterfactual",
            "description": (
                "Read a single counterfactual by cf_id, including its bound "
                "world-model prediction (if any) and resolution status."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cf_id": {
                        "type": "string",
                        "description": "Counterfactual ID (e.g. 'cf-abc123')",
                    },
                },
                "required": ["cf_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "counterfactual_summary",
            "description": (
                "Aggregate stats across recent counterfactuals — total count, "
                "status breakdown, average confidences, promotion rate, top "
                "trigger types. Useful for self-review of pattern-noticing "
                "calibration over time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lookback_days": {
                        "type": "integer",
                        "description": "Default 30, max 365",
                    },
                },
                "required": [],
            },
        },
    },
]


COUNTERFACTUAL_TOOL_HANDLERS: dict[str, Any] = {
    "list_counterfactuals": _exec_list_counterfactuals,
    "read_counterfactual": _exec_read_counterfactual,
    "counterfactual_summary": _exec_counterfactual_summary,
}
