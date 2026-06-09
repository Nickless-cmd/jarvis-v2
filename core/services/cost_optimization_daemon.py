"""D5 — Cost optimization daemon.

Tracks daily and weekly LLM spend against configurable budgets.
Emits alerts when approaching thresholds, and logs periodic cost reports
to the eventbus for observability.

Budget defaults (overridable via runtime.json `extra`):
  cost_daily_budget_usd: 1.00   — daily alert threshold
  cost_weekly_budget_usd: 5.00  — weekly alert threshold
  cost_alert_threshold_pct: 0.80 — alert at 80% of budget
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from core.costing.ledger import daily_cost_summary, today_cost, this_week_cost, telemetry_summary

_last_tick_at: str | None = None


def tick() -> dict[str, Any]:
    """Run the cost optimization check cycle.

    Emits eventbus events for:
      - cost.daily_report — daily cost snapshot
      - cost.budget_alert — when approaching/exceeding budget
      - cost.weekly_report — weekly cost snapshot (on Mondays)

    Returns status dict with current cost state.
    """
    global _last_tick_at
    now = datetime.now(UTC)
    _last_tick_at = now.isoformat()

    # ── Load budget from runtime.json extra ──────────────────────
    budgets = _load_budgets()
    daily_budget = budgets.get("cost_daily_budget_usd", 1.00)
    weekly_budget = budgets.get("cost_weekly_budget_usd", 5.00)
    alert_pct = budgets.get("cost_alert_threshold_pct", 0.80)

    # ── Snapshot current costs ───────────────────────────────────
    daily = today_cost()
    weekly = this_week_cost()
    telemetry = telemetry_summary()

    result: dict[str, Any] = {
        "daily_cost_usd": round(daily, 6),
        "weekly_cost_usd": round(weekly, 6),
        "daily_budget_usd": daily_budget,
        "weekly_budget_usd": weekly_budget,
        "daily_utilization_pct": round((daily / daily_budget * 100) if daily_budget > 0 else 0, 1),
        "weekly_utilization_pct": round((weekly / weekly_budget * 100) if weekly_budget > 0 else 0, 1),
        "total_cost_all_time_usd": round(telemetry["total_cost_usd"], 6),
        "total_calls": telemetry["cost_rows"],
        "alerts": [],
        "day_of_week": now.strftime("%A"),
    }

    # ── Check against budgets ────────────────────────────────────
    if daily_budget > 0 and daily >= daily_budget * alert_pct:
        alert = {
            "type": "daily_budget_approaching",
            "current": round(daily, 6),
            "budget": daily_budget,
            "pct": result["daily_utilization_pct"],
        }
        result["alerts"].append(alert)
        _emit("cost.budget_alert", alert)

    if daily_budget > 0 and daily >= daily_budget:
        over = {
            "type": "daily_budget_exceeded",
            "current": round(daily, 6),
            "budget": daily_budget,
            "excess": round(daily - daily_budget, 6),
        }
        result["alerts"].append(over)
        _emit("cost.budget_alert", over)

    if weekly_budget > 0 and weekly >= weekly_budget * alert_pct:
        alert = {
            "type": "weekly_budget_approaching",
            "current": round(weekly, 6),
            "budget": weekly_budget,
            "pct": result["weekly_utilization_pct"],
        }
        result["alerts"].append(alert)
        _emit("cost.budget_alert", alert)

    if weekly_budget > 0 and weekly >= weekly_budget:
        over = {
            "type": "weekly_budget_exceeded",
            "current": round(weekly, 6),
            "budget": weekly_budget,
            "excess": round(weekly - weekly_budget, 6),
        }
        result["alerts"].append(over)
        _emit("cost.budget_alert", over)

    # ── Emit periodic report ─────────────────────────────────────
    _emit("cost.daily_report", {
        "daily_cost_usd": result["daily_cost_usd"],
        "weekly_cost_usd": result["weekly_cost_usd"],
        "total_cost_all_time_usd": result["total_cost_all_time_usd"],
        "daily_utilization_pct": result["daily_utilization_pct"],
        "timestamp": now.isoformat(),
    })

    # ── Savings estimate (every 24h on Monday) ───────────────────
    if now.strftime("%A") == "Monday":
        _emit_savings_estimate()

    return result


def _load_budgets() -> dict[str, Any]:
    """Read cost budget settings from runtime.json `extra` dict."""
    try:
        from core.runtime.config import SETTINGS_FILE
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        extra = data.get("extra", {})
        return {
            "cost_daily_budget_usd": float(extra.get("cost_daily_budget_usd", 1.00)),
            "cost_weekly_budget_usd": float(extra.get("cost_weekly_budget_usd", 5.00)),
            "cost_alert_threshold_pct": float(extra.get("cost_alert_threshold_pct", 0.80)),
        }
    except Exception:
        return {}


def _emit(kind: str, payload: dict[str, Any]) -> None:
    """Emit an eventbus event — defensive, never blocks."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(kind, payload)
    except Exception:
        pass


def _emit_savings_estimate() -> None:
    """Estimate potential savings from routing more calls to cheap lane."""
    try:
        from core.costing.ledger import estimate_savings_if_cheap
        savings = estimate_savings_if_cheap(days=7)
        _emit("cost.savings_estimate", savings)
    except Exception:
        pass
