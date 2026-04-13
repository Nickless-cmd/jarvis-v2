from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import MagicMock, patch

import apps.api.jarvis_api.services.somatic_daemon as sd


def _reset():
    sd._cached_phrase = ""
    sd._last_cpu_pct = 0.0
    sd._last_latency_ms = 0.0
    sd._last_energy_level = ""
    sd._heartbeat_count_since_gen = 0
    sd._latency_samples.clear()
    sd._active_requests = 0


def test_get_latest_somatic_phrase_returns_empty_when_no_phrase():
    _reset()
    assert sd.get_latest_somatic_phrase() == ""


def test_generates_when_energy_level_changes():
    _reset()
    sd._last_energy_level = "høj"
    with patch.object(sd, "_generate_phrase", return_value="Jeg mærker tyngde."):
        with patch.object(sd, "_store_phrase"):
            result = sd.tick_somatic_daemon(energy_level="lav")
    assert result["generated"] is True


def test_generates_when_cpu_changes_by_20_points():
    _reset()
    sd._last_cpu_pct = 20.0
    sd._last_energy_level = "medium"
    with patch.object(sd, "_collect_snapshot", return_value={
        "cpu_pct": 42.0, "ram_used_gb": 4.0, "ram_total_gb": 16.0,
        "latency_ms": 100.0, "active_requests": 1,
        "energy_level": "medium", "clock_phase": "formiddag",
    }):
        with patch.object(sd, "_generate_phrase", return_value="Let og klar."):
            with patch.object(sd, "_store_phrase"):
                result = sd.tick_somatic_daemon(energy_level="medium")
    assert result["generated"] is True


def test_cache_returned_when_no_trigger():
    _reset()
    sd._cached_phrase = "Stille her."
    sd._last_energy_level = "medium"
    sd._last_cpu_pct = 30.0
    sd._heartbeat_count_since_gen = 2
    with patch.object(sd, "_collect_snapshot", return_value={
        "cpu_pct": 31.0,
        "ram_used_gb": 4.0, "ram_total_gb": 16.0,
        "latency_ms": 100.0, "active_requests": 0,
        "energy_level": "medium", "clock_phase": "formiddag",
    }):
        result = sd.tick_somatic_daemon(energy_level="medium")
    assert result["generated"] is False
    assert result["phrase"] == "Stille her."


def test_generates_after_10_heartbeats_without_trigger():
    _reset()
    sd._cached_phrase = "Stille her."
    sd._last_energy_level = "medium"
    sd._heartbeat_count_since_gen = 9
    with patch.object(sd, "_collect_snapshot", return_value={
        "cpu_pct": 30.0, "ram_used_gb": 4.0, "ram_total_gb": 16.0,
        "latency_ms": 100.0, "active_requests": 0,
        "energy_level": "medium", "clock_phase": "formiddag",
    }):
        with patch.object(sd, "_generate_phrase", return_value="Rolig puls."):
            with patch.object(sd, "_store_phrase"):
                result = sd.tick_somatic_daemon(energy_level="medium")
    assert result["generated"] is True


def test_llm_prompt_contains_hardware_and_energy():
    _reset()
    snapshot = {
        "cpu_pct": 55.0, "ram_used_gb": 8.0, "ram_total_gb": 16.0,
        "latency_ms": 200.0, "active_requests": 2,
        "energy_level": "lav", "clock_phase": "eftermiddag",
    }
    with patch("apps.api.jarvis_api.services.daemon_llm.daemon_llm_call", return_value="Tung og langsom."):
        phrase = sd._generate_phrase(snapshot)
    assert phrase == "Tung og langsom."


def test_private_brain_record_written_on_store():
    _reset()
    snapshot = {
        "cpu_pct": 30.0, "ram_used_gb": 4.0, "ram_total_gb": 16.0,
        "latency_ms": 100.0, "active_requests": 0,
        "energy_level": "medium", "clock_phase": "formiddag",
    }
    with patch("apps.api.jarvis_api.services.somatic_daemon.insert_private_brain_record") as mock_insert:
        sd._store_phrase("Let og klar.", snapshot)
    mock_insert.assert_called_once()
    call_kwargs = mock_insert.call_args[1]
    assert call_kwargs["record_type"] == "somatic-phrase"
    assert call_kwargs["summary"] == "Let og klar."
