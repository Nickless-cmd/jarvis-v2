from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from datetime import UTC, datetime, timedelta
import apps.api.jarvis_api.services.development_narrative_daemon as dnd


def _reset():
    dnd._last_narrative_at = None
    dnd._cached_narrative = ""


def test_no_narrative_before_cadence():
    """Should not generate within 24-hour cadence."""
    _reset()
    dnd._last_narrative_at = datetime.now(UTC)
    result = dnd.tick_development_narrative_daemon()
    assert result["generated"] is False


def test_generates_on_first_call():
    """First call (no prior narrative) should generate."""
    _reset()
    with patch.object(dnd, "_generate_narrative", return_value="De seneste dage har jeg udviklet mig.") as mock_gen:
        with patch.object(dnd, "_store_narrative"):
            result = dnd.tick_development_narrative_daemon()
    assert result["generated"] is True
    mock_gen.assert_called_once()


def test_store_called_on_generation():
    """_store_narrative is called with the generated text."""
    _reset()
    with patch.object(dnd, "_generate_narrative", return_value="En narrativ."):
        with patch.object(dnd, "_store_narrative") as mock_store:
            dnd.tick_development_narrative_daemon()
    mock_store.assert_called_once_with("En narrativ.")


def test_no_narrative_when_generate_returns_empty():
    """When _generate_narrative returns empty string, result is not-generated."""
    _reset()
    with patch.object(dnd, "_generate_narrative", return_value=""):
        result = dnd.tick_development_narrative_daemon()
    assert result["generated"] is False


def test_build_surface_structure():
    """build_development_narrative_surface returns expected keys."""
    _reset()
    dnd._cached_narrative = "Test."
    surface = dnd.build_development_narrative_surface()
    assert "latest_narrative" in surface
    assert "last_generated_at" in surface
    assert surface["latest_narrative"] == "Test."
