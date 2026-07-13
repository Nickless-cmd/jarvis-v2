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
    record_cost,
)


# ── 2026-06-09 cache_hit_tokens / cache_miss_tokens migration ─────────────


class TestRecordCostCacheColumns:
    def test_record_cost_accepts_cache_kwargs(self, isolated_runtime):
        """record_cost accepterer nye cache_hit_tokens + cache_miss_tokens."""
        record_cost(
            lane="primary",
            provider="deepseek",
            model="deepseek-v4-flash",
            input_tokens=85675,
            output_tokens=357,
            cost_usd=0.0114,
            cache_hit_tokens=5120,
            cache_miss_tokens=80555,
        )
        rows = recent_costs(limit=1)
        assert rows, "record_cost should have inserted a row"
        # cache columns roundtrip via DB
        from core.runtime.db import connect
        with connect() as conn:
            r = conn.execute(
                "SELECT cache_hit_tokens, cache_miss_tokens FROM costs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        assert int(r["cache_hit_tokens"]) == 5120
        assert int(r["cache_miss_tokens"]) == 80555

    def test_record_cost_defaults_cache_to_zero(self, isolated_runtime):
        """Gamle call sites uden cache-info → 0/0 (ingen TypeError)."""
        record_cost(
            lane="cheap",
            provider="ollama",
            model="local",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.0,
        )
        from core.runtime.db import connect
        with connect() as conn:
            r = conn.execute(
                "SELECT cache_hit_tokens, cache_miss_tokens FROM costs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        assert int(r["cache_hit_tokens"]) == 0
        assert int(r["cache_miss_tokens"]) == 0


class TestDeprecatedDeepseekAliasLabel:
    """Wire-laget rewriter deepseek-chat/reasoner → v4-flash (deadline 2026-07-24).
    record_cost er regnskabs-chokepointet → log det ÆRLIGE wire-navn, ikke aliaset."""

    def test_deepseek_chat_label_normalized_to_v4_flash(self, isolated_runtime):
        record_cost(lane="cheap", provider="deepseek", model="deepseek-chat",
                    input_tokens=10, output_tokens=5, cost_usd=0.0)
        from core.runtime.db import connect
        with connect() as conn:
            r = conn.execute("SELECT model FROM costs ORDER BY id DESC LIMIT 1").fetchone()
        assert r["model"] == "deepseek-v4-flash"

    def test_deepseek_reasoner_label_normalized_to_v4_flash(self, isolated_runtime):
        record_cost(lane="cheap", provider="deepseek", model="deepseek-reasoner",
                    input_tokens=10, output_tokens=5, cost_usd=0.0)
        from core.runtime.db import connect
        with connect() as conn:
            r = conn.execute("SELECT model FROM costs ORDER BY id DESC LIMIT 1").fetchone()
        assert r["model"] == "deepseek-v4-flash"

    def test_non_deepseek_model_label_untouched(self, isolated_runtime):
        record_cost(lane="cheap", provider="ollama", model="deepseek-chat",
                    input_tokens=10, output_tokens=5, cost_usd=0.0)
        from core.runtime.db import connect
        with connect() as conn:
            r = conn.execute("SELECT model FROM costs ORDER BY id DESC LIMIT 1").fetchone()
        # kun deepseek-provider normaliseres; andre providers rører vi ikke
        assert r["model"] == "deepseek-chat"


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
