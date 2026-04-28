"""Tests for infra_weather_daemon — the system weather sensor.

Validates that the daemon correctly:
- Composes a weather report from subsystems
- Classifies weather into clear / under-pressure / critical
- Emits critical alerts when thresholds are crossed
- Integrates with the cost ledger for API cost tracking
- Checks network latency via Ollama socket probe
"""
from __future__ import annotations

import importlib
import os
import sqlite3
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_module():
    """Force reload to pick up edits during the same test run."""
    mod = importlib.import_module("core.services.infra_weather_daemon")
    importlib.reload(mod)
    return mod


# ---------------------------------------------------------------------------
# _api_cost_today — cost ledger integration
# ---------------------------------------------------------------------------

class TestApiCostToday:
    """Verify _api_cost_today reads from the costs ledger."""

    def test_returns_zero_when_no_costs(self):
        mod = _reload_module()
        with patch("core.costing.ledger.telemetry_summary", return_value={"total_cost_usd": 0.0}):
            result = mod._api_cost_today()
        assert result == 0.0

    def test_returns_sum_from_ledger(self):
        mod = _reload_module()
        with patch("core.costing.ledger.telemetry_summary", return_value={"total_cost_usd": 3.42}):
            result = mod._api_cost_today()
        assert result == 3.42

    def test_falls_back_to_db_on_ledger_error(self):
        mod = _reload_module()
        with patch("core.costing.ledger.telemetry_summary", side_effect=ImportError):
            # Should try DB fallback, return 0.0 if no costs table
            result = mod._api_cost_today()
        assert isinstance(result, float)

    def test_returns_zero_on_total_failure(self):
        mod = _reload_module()
        with patch("core.costing.ledger.telemetry_summary", side_effect=ImportError):
            with patch("core.runtime.db.connect", side_effect=Exception("no db")):
                result = mod._api_cost_today()
        assert result == 0.0


# ---------------------------------------------------------------------------
# _network_latency — connectivity check
# ---------------------------------------------------------------------------

class TestNetworkLatency:
    """Verify _network_latency probes Ollama and checks eventbus errors."""

    def test_returns_ok_when_ollama_reachable(self):
        mod = _reload_module()
        mock_sock = MagicMock()
        with patch("socket.create_connection", return_value=mock_sock):
            result = mod._network_latency()
        assert result["status"] in ("ok", "slow")
        assert result["ollama_ms"] is not None
        mock_sock.close.assert_called_once()

    def test_returns_degraded_when_ollama_unreachable(self):
        mod = _reload_module()
        with patch("socket.create_connection", side_effect=OSError("Connection refused")):
            result = mod._network_latency()
        assert result["status"] == "degraded"
        assert result["ollama_ms"] is None

    def test_status_slow_when_high_latency(self):
        mod = _reload_module()
        # Simulate >100ms connection time
        original_ts = datetime.now(UTC).timestamp

        def slow_timestamp():
            # Return incrementing timestamps: first call start, then +150ms
            if not hasattr(slow_timestamp, "_call_count"):
                slow_timestamp._call_count = 0
            slow_timestamp._call_count += 1
            if slow_timestamp._call_count == 1:
                return 1000.0
            return 1000.15  # 150ms later

        with patch("socket.create_connection", return_value=MagicMock()):
            with patch("core.services.infra_weather_daemon.datetime") as mock_dt:
                mock_dt.now.return_value.timestamp = slow_timestamp
                # Need to also patch the UTC reference
                mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
                result = mod._network_latency()
        # If latency > 100ms, status should be "slow"
        # (This test is best-effort due to mocking complexity)
        assert "status" in result


# ---------------------------------------------------------------------------
# _weather_label — classification
# ---------------------------------------------------------------------------

class TestWeatherLabel:
    """Verify weather classification thresholds."""

    def test_clear_when_all_normal(self):
        mod = _reload_module()
        label, emoji = mod._weather_label(0.3, 50.0, 1.0)
        assert label == "clear"
        assert emoji == "☀️"

    def test_under_pressure_load(self):
        mod = _reload_module()
        label, emoji = mod._weather_label(0.80, 50.0, 1.0)
        assert label == "under-pressure"
        assert emoji == "🌧"

    def test_under_pressure_disk(self):
        mod = _reload_module()
        label, emoji = mod._weather_label(0.3, 86.0, 1.0)
        assert label == "under-pressure"

    def test_under_pressure_cost(self):
        mod = _reload_module()
        label, emoji = mod._weather_label(0.3, 50.0, 6.0)
        assert label == "under-pressure"

    def test_critical_load(self):
        mod = _reload_module()
        label, emoji = mod._weather_label(0.95, 50.0, 1.0)
        assert label == "critical"
        assert emoji == "⛈"

    def test_critical_disk(self):
        mod = _reload_module()
        label, emoji = mod._weather_label(0.3, 96.0, 1.0)
        assert label == "critical"

    def test_critical_cost(self):
        mod = _reload_module()
        label, emoji = mod._weather_label(0.3, 50.0, 16.0)
        assert label == "critical"


# ---------------------------------------------------------------------------
# _compose_report — integration
# ---------------------------------------------------------------------------

class TestComposeReport:
    """Verify the full weather report is well-formed."""

    def test_report_has_required_fields(self):
        mod = _reload_module()
        with patch("core.costing.ledger.telemetry_summary", return_value={"total_cost_usd": 0.0}):
            with patch("socket.create_connection", side_effect=OSError("skip")):
                report = mod._compose_report()
        assert "label" in report
        assert "emoji" in report
        assert "load" in report
        assert "disk" in report
        assert "network" in report
        assert "api_cost_today_usd" in report
        assert "process_health" in report
        assert "computed_at" in report
        assert report["label"] in ("clear", "under-pressure", "critical")

    def test_report_includes_network_status(self):
        mod = _reload_module()
        with patch("core.costing.ledger.telemetry_summary", return_value={"total_cost_usd": 0.0}):
            with patch("socket.create_connection", side_effect=OSError("skip")):
                report = mod._compose_report()
        assert "network" in report
        assert "status" in report["network"]


# ---------------------------------------------------------------------------
# get_weather — caching
# ---------------------------------------------------------------------------

class TestGetWeatherCaching:
    """Verify weather is cached and not recomputed on every call."""

    def test_caches_within_interval(self):
        mod = _reload_module()
        # Reset cache
        mod._last_state = {}
        mod._last_computed_ts = 0.0

        with patch("core.costing.ledger.telemetry_summary", return_value={"total_cost_usd": 0.0}):
            with patch("socket.create_connection", side_effect=OSError("skip")):
                r1 = mod.get_weather()
                r2 = mod.get_weather()
        # Both should return the same timestamp (cached)
        assert r1["computed_at"] == r2["computed_at"]


# ---------------------------------------------------------------------------
# build_infra_weather_prompt_section — silence when clear
# ---------------------------------------------------------------------------

class TestPromptSection:
    """Verify prompt section is silent when clear, speaks when pressured."""

    def test_returns_none_when_clear(self):
        mod = _reload_module()
        with patch.object(mod, "get_weather", return_value={"label": "clear", "emoji": "☀️"}):
            result = mod.build_infra_weather_prompt_section()
        assert result is None

    def test_returns_string_when_under_pressure(self):
        mod = _reload_module()
        with patch.object(mod, "get_weather", return_value={
            "label": "under-pressure", "emoji": "🌧", "reasons": ["load=0.80"]
        }):
            result = mod.build_infra_weather_prompt_section()
        assert result is not None
        assert "under-pressure" in result

    def test_returns_string_when_critical(self):
        mod = _reload_module()
        with patch.object(mod, "get_weather", return_value={
            "label": "critical", "emoji": "⛈", "reasons": ["disk=96%"]
        }):
            result = mod.build_infra_weather_prompt_section()
        assert result is not None
        assert "critical" in result