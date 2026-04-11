from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from datetime import UTC, datetime, timedelta
import apps.api.jarvis_api.services.meta_reflection_daemon as mrd


def _reset():
    mrd._last_meta_at = None
    mrd._cached_meta_insight = ""
    mrd._meta_buffer.clear()


def test_no_meta_before_cadence():
    """Should not generate within 30-minute cadence."""
    _reset()
    mrd._last_meta_at = datetime.now(UTC)
    result = mrd.tick_meta_reflection_daemon({"latest_fragment": "Noget."})
    assert result["generated"] is False


def test_no_meta_without_active_signals():
    """Empty snapshot (no active signals) produces no meta-insight."""
    _reset()
    result = mrd.tick_meta_reflection_daemon({})
    assert result["generated"] is False


def test_generates_meta_insight_with_signals():
    """Non-empty snapshot with active signals generates a meta-insight."""
    _reset()
    with patch.object(mrd, "_generate_meta_insight", return_value="Et klart mønster.") as mock_gen:
        with patch.object(mrd, "_store_meta_insight"):
            result = mrd.tick_meta_reflection_daemon({
                "latest_fragment": "Noget.",
                "last_surprise": "En overraskelse.",
            })
    assert result["generated"] is True
    mock_gen.assert_called_once()


def test_store_called_on_generation():
    """_store_meta_insight is called with the generated text."""
    _reset()
    with patch.object(mrd, "_generate_meta_insight", return_value="Indsigt."):
        with patch.object(mrd, "_store_meta_insight") as mock_store:
            mrd.tick_meta_reflection_daemon({"latest_fragment": "Tanke."})
    mock_store.assert_called_once_with("Indsigt.")


def test_insight_added_to_buffer():
    """Generated insight is prepended to meta_buffer."""
    _reset()
    with patch.object(mrd, "_generate_meta_insight", return_value="Ny indsigt."):
        with patch("apps.api.jarvis_api.services.meta_reflection_daemon.insert_private_brain_record"):
            with patch("apps.api.jarvis_api.services.meta_reflection_daemon.event_bus"):
                mrd.tick_meta_reflection_daemon({"last_conflict": "Konflikt."})
    assert len(mrd._meta_buffer) == 1
    assert mrd._meta_buffer[0] == "Ny indsigt."


def test_build_surface_structure():
    """build_meta_reflection_surface returns expected keys."""
    _reset()
    mrd._cached_meta_insight = "Et mønster."
    surface = mrd.build_meta_reflection_surface()
    assert "latest_insight" in surface
    assert "insight_buffer" in surface
    assert "insight_count" in surface
    assert "last_generated_at" in surface
    assert surface["latest_insight"] == "Et mønster."
