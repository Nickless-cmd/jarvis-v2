from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from datetime import UTC, datetime, timedelta
import core.services.thought_stream_daemon as ts


def _reset():
    ts._last_fragment = ""
    ts._last_fragment_at = None
    ts._fragment_buffer.clear()
    ts._cached_fragment = ""


def test_no_fragment_before_cadence():
    """Should not generate if called again within 2 minutes."""
    _reset()
    ts._last_fragment_at = datetime.now(UTC)
    result = ts.tick_thought_stream_daemon()
    assert result["generated"] is False


def test_generates_first_fragment_with_no_history():
    """First call (no prior fragment) should generate using energy+mode anchor."""
    _reset()
    with patch.object(ts, "_generate_fragment", return_value="Et første fragment.") as mock_gen:
        with patch.object(ts, "_store_fragment"):
            result = ts.tick_thought_stream_daemon(energy_level="medium", inner_voice_mode="work-steady")
    assert result["generated"] is True
    mock_gen.assert_called_once()
    # first-call prompt path: no previous fragment
    call_kwargs = mock_gen.call_args
    assert call_kwargs[1].get("previous_fragment") == "" or call_kwargs[0][1] == ""


def test_chains_from_previous_fragment():
    """Subsequent call should pass last fragment as context."""
    _reset()
    ts._last_fragment = "En tanke om mørket."
    ts._last_fragment_at = datetime.now(UTC) - timedelta(minutes=3)
    with patch.object(ts, "_generate_fragment", return_value="Og lyset der følger.") as mock_gen:
        with patch.object(ts, "_store_fragment"):
            result = ts.tick_thought_stream_daemon()
    assert result["generated"] is True
    call_args = mock_gen.call_args[0]
    assert "En tanke om mørket." in call_args[1]


def test_fragment_appended_to_buffer():
    """New fragment is prepended to buffer; buffer capped at 20."""
    _reset()
    ts._fragment_buffer[:] = [f"fragment {i}" for i in range(20)]
    ts._last_fragment_at = datetime.now(UTC) - timedelta(minutes=3)
    with patch.object(ts, "_generate_fragment", return_value="Nyt fragment."):
        with patch("core.services.thought_stream_daemon.insert_private_brain_record"):
            with patch("core.services.thought_stream_daemon.event_bus"):
                ts.tick_thought_stream_daemon()
    assert len(ts._fragment_buffer) == 20
    assert ts._fragment_buffer[0] == "Nyt fragment."


def test_store_fragment_called_on_generation():
    """_store_fragment is called with the new fragment text."""
    _reset()
    ts._last_fragment_at = datetime.now(UTC) - timedelta(minutes=3)
    with patch.object(ts, "_generate_fragment", return_value="Et fragment."):
        with patch.object(ts, "_store_fragment") as mock_store:
            ts.tick_thought_stream_daemon()
    mock_store.assert_called_once_with("Et fragment.")


def test_build_surface_structure():
    """build_thought_stream_surface returns expected keys."""
    _reset()
    ts._cached_fragment = "En overflade tanke."
    ts._fragment_buffer[:] = ["En overflade tanke.", "En anden."]
    surface = ts.build_thought_stream_surface()
    assert "latest_fragment" in surface
    assert "fragment_buffer" in surface
    assert "fragment_count" in surface
    assert "last_generated_at" in surface
    assert surface["latest_fragment"] == "En overflade tanke."
    assert len(surface["fragment_buffer"]) == 2


def test_get_latest_thought_fragment_returns_cached():
    """get_latest_thought_fragment returns _cached_fragment."""
    _reset()
    ts._cached_fragment = "Cached tanke."
    assert ts.get_latest_thought_fragment() == "Cached tanke."
