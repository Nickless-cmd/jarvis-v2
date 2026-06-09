"""Tests for D5 — Cost optimization daemon."""
from __future__ import annotations

from core.services.cost_optimization_daemon import tick, _load_budgets


class TestCostOptimizationDaemon:
    """Verify cost optimization daemon tick produces expected structure."""

    def test_tick_returns_expected_keys(self):
        result = tick()

        assert isinstance(result, dict)
        assert "daily_cost_usd" in result
        assert "weekly_cost_usd" in result
        assert "daily_budget_usd" in result
        assert "weekly_budget_usd" in result
        assert "daily_utilization_pct" in result
        assert "weekly_utilization_pct" in result
        assert "total_cost_all_time_usd" in result
        assert "total_calls" in result
        assert "alerts" in result
        assert "day_of_week" in result

    def test_tick_numeric_types(self):
        result = tick()

        assert isinstance(result["daily_cost_usd"], float)
        assert isinstance(result["weekly_cost_usd"], float)
        assert isinstance(result["daily_utilization_pct"], float)
        assert isinstance(result["weekly_utilization_pct"], float)
        assert isinstance(result["total_cost_all_time_usd"], float)
        assert isinstance(result["total_calls"], int)
        assert isinstance(result["alerts"], list)

    def test_tick_non_negative_costs(self):
        result = tick()

        assert result["daily_cost_usd"] >= 0
        assert result["weekly_cost_usd"] >= 0
        assert result["total_cost_all_time_usd"] >= 0
        assert result["total_calls"] >= 0

    def test_tick_budgets_positive(self):
        result = tick()

        assert result["daily_budget_usd"] > 0
        assert result["weekly_budget_usd"] > 0

    def test_load_budgets_returns_dict(self):
        budgets = _load_budgets()

        assert isinstance(budgets, dict)
        # Should contain at least the defaults
        assert "cost_daily_budget_usd" in budgets
        assert "cost_weekly_budget_usd" in budgets
        assert "cost_alert_threshold_pct" in budgets
