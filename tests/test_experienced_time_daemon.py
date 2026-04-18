from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
import core.services.experienced_time_daemon as etd


def _reset():
    etd.reset_experienced_time_daemon()


def test_session_starts_on_first_tick():
    """Session start timestamp is set on first tick."""
    _reset()
    assert etd._session_start_at is None
    with patch.object(
        etd,
        "_generate_felt_label",
        side_effect=lambda **kwargs: etd._label(float(kwargs["felt_minutes"])),
    ):
        etd.tick_experienced_time_daemon(5, 1, "medium")
    assert etd._session_start_at is not None


def test_event_count_accumulates():
    """Event and novelty counts accumulate across ticks."""
    _reset()
    with patch.object(
        etd,
        "_generate_felt_label",
        side_effect=lambda **kwargs: etd._label(float(kwargs["felt_minutes"])),
    ):
        etd.tick_experienced_time_daemon(5, 0, "medium")
        etd.tick_experienced_time_daemon(3, 1, "medium")
    assert etd._session_event_count == 8
    assert etd._session_novelty_count == 1


def test_felt_label_new_session():
    """A brand-new session with no elapsed time gets 'meget kort'."""
    _reset()
    with patch.object(
        etd,
        "_generate_felt_label",
        side_effect=lambda **kwargs: etd._label(float(kwargs["felt_minutes"])),
    ):
        result = etd.tick_experienced_time_daemon(0, 0, "medium")
    assert result["felt_label"] == "meget kort"


def test_high_density_amplifies_felt_duration():
    """Many events and high novelty amplify felt duration."""
    _reset()
    etd._session_event_count = 200
    etd._session_novelty_count = 20
    etd._session_start_at = datetime.now(UTC) - timedelta(minutes=30)
    with patch.object(
        etd,
        "_generate_felt_label",
        side_effect=lambda **kwargs: etd._label(float(kwargs["felt_minutes"])),
    ):
        result = etd.tick_experienced_time_daemon(0, 0, "høj")
    # base=30, density=2.0, novelty=1.5, intensity=1.3 → felt=117 → "lang"
    assert result["felt_label"] in ("lang", "meget lang")


def test_build_surface_structure():
    """build_experienced_time_surface returns expected keys."""
    _reset()
    surface = etd.build_experienced_time_surface()
    assert "felt_label" in surface
    assert "session_event_count" in surface
    assert "session_novelty_count" in surface
    assert "base_minutes" in surface
    assert "active" in surface


def test_generate_felt_label_uses_public_safe_llm_path():
    _reset()
    from unittest.mock import patch

    with patch.dict("sys.modules", {
        "core.services.daemon_llm": type(
            "_FakeDaemonLLMModule",
            (),
            {"daemon_public_safe_llm_call": staticmethod(lambda *args, **kwargs: "lang")}
        )()
    }):
        result = etd._generate_felt_label(
            felt_minutes=120.0,
            event_count=40,
            novelty_count=5,
            energy_level="medium",
        )

    assert result == "lang"
