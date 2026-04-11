from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
import apps.api.jarvis_api.services.aesthetic_taste_daemon as atd


def _reset():
    atd._choice_log.clear()
    atd._insight_history.clear()
    atd._latest_insight = ""
    atd._choices_since_insight = 0


def test_no_insight_before_threshold():
    _reset()
    for _ in range(14):
        atd.record_choice("work-steady", ["short", "direct"])
    result = atd.tick_taste_daemon()
    assert result["generated"] is False


def test_insight_after_threshold():
    _reset()
    for _ in range(15):
        atd.record_choice("work-steady", ["short", "direct"])
    with patch.object(atd, "_generate_insight", return_value="Jeg foretrækker det korte og direkte."):
        with patch.object(atd, "_store_insight"):
            result = atd.tick_taste_daemon()
    assert result["generated"] is True
    assert result["insight"] == "Jeg foretrækker det korte og direkte."


def test_choice_log_bounded_to_50():
    _reset()
    for _ in range(60):
        atd.record_choice("searching", ["long"])
    assert len(atd._choice_log) == 50


def test_dominant_modes_in_surface():
    _reset()
    for _ in range(10):
        atd.record_choice("work-steady", [])
    for _ in range(5):
        atd.record_choice("searching", [])
    surface = atd.build_taste_surface()
    assert surface["dominant_modes"][0] == "work-steady"
    assert surface["choice_count"] == 15


def test_private_brain_record_written_on_store():
    _reset()
    atd._choice_log[:] = [
        {"mode": "searching", "style": ["short"], "ts": "2026-01-01T00:00:00Z"}
    ] * 15
    with patch("apps.api.jarvis_api.services.aesthetic_taste_daemon.insert_private_brain_record") as mock_insert:
        atd._store_insight("Jeg vælger det kompakte.")
    mock_insert.assert_called_once()
    kwargs = mock_insert.call_args[1]
    assert kwargs["record_type"] == "taste-insight"
    assert kwargs["summary"] == "Jeg vælger det kompakte."
