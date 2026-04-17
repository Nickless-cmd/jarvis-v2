from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import UTC, datetime
from unittest.mock import patch
import core.services.irony_daemon as irod


def _reset():
    irod._cached_observation = ""
    irod._cached_observation_at = None
    irod._observations_today = 0
    irod._last_reset_date = ""
    irod._last_condition_matched = ""


def test_no_irony_without_condition():
    _reset()
    with patch.object(irod, "_collect_snapshot", return_value={"hour": 14, "user_inactive_min": 5.0, "cpu_pct": 20.0}):
        result = irod.tick_irony_daemon()
    assert result["generated"] is False


def test_nocturnal_sentinel_triggers():
    _reset()
    with patch.object(irod, "_collect_snapshot", return_value={"hour": 2, "user_inactive_min": 60.0, "cpu_pct": 15.0}):
        with patch.object(irod, "_generate_observation", return_value="Her sidder jeg igen."):
            with patch.object(irod, "_store_observation"):
                result = irod.tick_irony_daemon()
    assert result["generated"] is True
    assert result["condition"] == "nocturnal_sentinel"


def test_daily_cooldown_prevents_repeat():
    _reset()
    irod._observations_today = 1
    irod._last_reset_date = datetime.now(UTC).strftime("%Y-%m-%d")
    with patch.object(irod, "_collect_snapshot", return_value={"hour": 2, "user_inactive_min": 60.0, "cpu_pct": 15.0}):
        result = irod.tick_irony_daemon()
    assert result["generated"] is False


def test_llm_nej_returns_no_observation():
    _reset()
    with patch.object(irod, "_collect_snapshot", return_value={"hour": 2, "user_inactive_min": 60.0, "cpu_pct": 15.0}):
        with patch.object(irod, "_generate_observation", return_value="nej"):
            result = irod.tick_irony_daemon()
    assert result["generated"] is False


def test_detect_faithful_standby():
    _reset()
    condition = irod._detect_irony_conditions({"hour": 10, "user_inactive_min": 800.0, "cpu_pct": 5.0})
    assert condition == "faithful_standby"


def test_detect_busy_solitude():
    _reset()
    condition = irod._detect_irony_conditions({"hour": 14, "user_inactive_min": 45.0, "cpu_pct": 80.0})
    assert condition == "busy_solitude"


def test_private_brain_record_written_on_store():
    _reset()
    with patch("core.services.irony_daemon.insert_private_brain_record") as mock_insert:
        irod._store_observation("Her sidder jeg.", "nocturnal_sentinel")
    mock_insert.assert_called_once()
    kwargs = mock_insert.call_args[1]
    assert kwargs["record_type"] == "irony-observation"
    assert kwargs["summary"] == "Her sidder jeg."
