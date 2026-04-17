from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from datetime import UTC, datetime, timedelta
import core.services.reflection_cycle_daemon as rc


def _reset():
    rc._last_reflection_at = None
    rc._cached_reflection = ""
    rc._reflection_buffer.clear()


def test_no_reflection_before_cadence():
    """Should not generate if called again within 10 minutes."""
    _reset()
    rc._last_reflection_at = datetime.now(UTC)
    result = rc.tick_reflection_cycle_daemon({})
    assert result["generated"] is False


def test_generates_first_reflection():
    """First call (no prior reflection) should generate."""
    _reset()
    with patch.object(rc, "_generate_reflection", return_value="Jeg er her. Stille.") as mock_gen:
        with patch.object(rc, "_store_reflection"):
            result = rc.tick_reflection_cycle_daemon({"energy_level": "medium"})
    assert result["generated"] is True
    mock_gen.assert_called_once()


def test_reflection_added_to_buffer():
    """New reflection is prepended to buffer."""
    _reset()
    with patch.object(rc, "_generate_reflection", return_value="En rolig efterniddag."):
        with patch("core.services.reflection_cycle_daemon.insert_private_brain_record"):
            with patch("core.services.reflection_cycle_daemon.event_bus"):
                rc.tick_reflection_cycle_daemon({"energy_level": "lav"})
    assert len(rc._reflection_buffer) == 1
    assert rc._reflection_buffer[0] == "En rolig efterniddag."


def test_buffer_capped_at_10():
    """Reflection buffer is capped at 10 entries."""
    _reset()
    rc._reflection_buffer[:] = [f"reflection {i}" for i in range(10)]
    rc._last_reflection_at = datetime.now(UTC) - timedelta(minutes=11)
    with patch.object(rc, "_generate_reflection", return_value="Ny refleksion."):
        with patch("core.services.reflection_cycle_daemon.insert_private_brain_record"):
            with patch("core.services.reflection_cycle_daemon.event_bus"):
                rc.tick_reflection_cycle_daemon({})
    assert len(rc._reflection_buffer) == 10
    assert rc._reflection_buffer[0] == "Ny refleksion."


def test_store_called_on_generation():
    """_store_reflection is called with the generated text."""
    _reset()
    with patch.object(rc, "_generate_reflection", return_value="En tanke."):
        with patch.object(rc, "_store_reflection") as mock_store:
            rc.tick_reflection_cycle_daemon({})
    mock_store.assert_called_once_with("En tanke.")


def test_build_surface_structure():
    """build_reflection_surface returns expected keys."""
    _reset()
    rc._cached_reflection = "Jeg er her."
    rc._reflection_buffer[:] = ["Jeg er her.", "Noget andet."]
    surface = rc.build_reflection_surface()
    assert "latest_reflection" in surface
    assert "reflection_buffer" in surface
    assert "reflection_count" in surface
    assert "last_generated_at" in surface
    assert surface["latest_reflection"] == "Jeg er her."
