"""Tests for core.costing.ledger — cost tracking and D5 optimization utilities."""
from __future__ import annotations

from core.costing.ledger import (
    telemetry_summary,
    recent_costs,
    daily_cost_summary,
    weekly_cost_summary,
    today_cost,
    this_week_cost,
    estimate_savings_if_cheap,
)


class TestTelemetrySummary:
    def test_returns_expected_keys(self):
        result = telemetry_summary()
        assert "cost_rows" in result
        assert "input_tokens" in result
        assert "output_tokens" in result
        assert "total_cost_usd" in result

    def test_numeric_types(self):
        result = telemetry_summary()
        assert isinstance(result["cost_rows"], int)
        assert isinstance(result["input_tokens"], int)
        assert isinstance(result["output_tokens"], int)
        assert isinstance(result["total_cost_usd"], float)


class TestRecentCosts:
    def test_returns_list(self):
        result = recent_costs(limit=3)
        assert isinstance(result, list)

    def test_items_have_expected_keys(self):
        result = recent_costs(limit=1)
        if result:
            item = result[0]
            assert "id" in item
            assert "lane" in item
            assert "provider" in item
            assert "model" in item
            assert "input_tokens" in item
            assert "output_tokens" in item
            assert "cost_usd" in item
            assert "created_at" in item

    def test_limit_respected(self):
        result = recent_costs(limit=5)
        assert len(result) <= 5


class TestDailyCostSummary:
    def test_returns_list(self):
        result = daily_cost_summary()
        assert isinstance(result, list)

    def test_items_have_expected_keys(self):
        if result := daily_cost_summary():
            item = result[0]
            assert "day" in item
            assert "lane" in item
            assert "calls" in item
            assert "total_tokens" in item
            assert "total_cost" in item

    def test_non_negative(self):
        for item in daily_cost_summary():
            assert item["calls"] >= 0
            assert item["total_tokens"] >= 0
            assert item["total_cost"] >= 0


class TestWeeklyCostSummary:
    def test_returns_list(self):
        result = weekly_cost_summary()
        assert isinstance(result, list)

    def test_items_have_expected_keys(self):
        if result := weekly_cost_summary():
            item = result[0]
            assert "week" in item
            assert "lane" in item
            assert "calls" in item
            assert "total_tokens" in item
            assert "total_cost" in item


class TestTodayCost:
    def test_returns_float(self):
        cost = today_cost()
        assert isinstance(cost, float)
        assert cost >= 0


class TestThisWeekCost:
    def test_returns_float(self):
        cost = this_week_cost()
        assert isinstance(cost, float)
        assert cost >= 0


class TestEstimateSavingsIfCheap:
    def test_returns_dict(self):
        result = estimate_savings_if_cheap(days=7)
        assert isinstance(result, dict)
        assert "period_days" in result
        assert "primary_calls" in result
        assert "primary_tokens" in result
        assert "primary_cost" in result
        assert "estimated_cheap_cost" in result
        assert "potential_savings" in result

    def test_non_negative(self):
        result = estimate_savings_if_cheap(days=7)
        assert result["primary_calls"] >= 0
        assert result["primary_tokens"] >= 0
        assert result["primary_cost"] >= 0
        assert result["potential_savings"] >= 0
