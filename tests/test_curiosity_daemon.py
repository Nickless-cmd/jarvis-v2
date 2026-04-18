from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from datetime import UTC, datetime, timedelta
import core.services.curiosity_daemon as cd


def _reset():
    cd._last_tick_at = None
    cd._cached_curiosity = ""
    cd._open_questions.clear()


def test_no_curiosity_before_cadence():
    """Should not generate if within 5-minute cadence."""
    _reset()
    cd._last_tick_at = datetime.now(UTC)
    result = cd.tick_curiosity_daemon(["Hvad sker der egentlig?"])
    assert result["generated"] is False


def test_no_curiosity_without_gap():
    """Fragments with no gap patterns produce no curiosity signal."""
    _reset()
    result = cd.tick_curiosity_daemon(["Alt er fint. Arbejder videre."])
    assert result["generated"] is False
    assert cd._cached_curiosity == ""


def test_question_mark_gap_detected():
    """Fragment with '?' triggers curiosity generation."""
    _reset()
    with patch.object(cd, "_generate_curiosity_signal", return_value="Jeg undrer mig over det."):
        with patch.object(cd, "_store_curiosity"):
            result = cd.tick_curiosity_daemon(["Hvad sker der egentlig?"])
    assert result["generated"] is True
    assert result["gap_type"] == "question"


def test_ved_ikke_gap_detected():
    """Fragment with 'ved ikke' triggers curiosity generation."""
    _reset()
    with patch.object(cd, "_generate_curiosity_signal", return_value="Jeg ved ikke nok."):
        with patch.object(cd, "_store_curiosity"):
            result = cd.tick_curiosity_daemon(["Jeg ved ikke om det er rigtigt."])
    assert result["generated"] is True
    assert result["gap_type"] == "open"


def test_open_question_added_to_buffer():
    """Generated curiosity signal is prepended to open_questions buffer."""
    _reset()
    with patch.object(cd, "_generate_curiosity_signal", return_value="Jeg ved ikke nok."):
        with patch("core.services.curiosity_daemon.insert_private_brain_record"):
            with patch("core.services.curiosity_daemon.event_bus"):
                cd.tick_curiosity_daemon(["Hvad sker der?"])
    assert len(cd._open_questions) == 1
    assert cd._open_questions[0] == "Jeg ved ikke nok."


def test_open_questions_capped_at_5():
    """Open questions buffer is capped at 5 entries."""
    _reset()
    cd._open_questions[:] = [f"question {i}" for i in range(5)]
    cd._last_tick_at = datetime.now(UTC) - timedelta(minutes=6)
    with patch.object(cd, "_generate_curiosity_signal", return_value="Ny nysgerrighed."):
        with patch("core.services.curiosity_daemon.insert_private_brain_record"):
            with patch("core.services.curiosity_daemon.event_bus"):
                cd.tick_curiosity_daemon(["Hvad er dette?"])
    assert len(cd._open_questions) == 5
    assert cd._open_questions[0] == "Ny nysgerrighed."


def test_build_surface_structure():
    """build_curiosity_surface returns expected keys."""
    _reset()
    surface = cd.build_curiosity_surface()
    assert "latest_curiosity" in surface
    assert "open_questions" in surface
    assert "curiosity_count" in surface
    assert "last_generated_at" in surface


def test_generate_curiosity_signal_uses_public_safe_llm_path():
    _reset()
    with patch.dict("sys.modules", {
        "core.services.daemon_llm": type(
            "_FakeDaemonLLMModule",
            (),
            {"daemon_public_safe_llm_call": staticmethod(lambda *args, **kwargs: "Et åbent spørgsmål står tilbage.")}
        )()
    }):
        result = cd._generate_curiosity_signal("Hvad sker der egentlig?", "question")

    assert result == "Et åbent spørgsmål står tilbage."
