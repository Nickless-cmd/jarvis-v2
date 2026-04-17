"""Smoke test for core.services.temporal_context.

Temporal context should classify the day phase and peak-focus window from the
current UTC timestamp.
"""

from datetime import UTC, datetime

from core.services import temporal_context


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 4, 13, 10, 0, tzinfo=UTC)


def test_build_temporal_context_for_weekday_focus_window(monkeypatch) -> None:
    monkeypatch.setattr(temporal_context, "datetime", _FixedDateTime)

    context = temporal_context.build_temporal_context()
    surface = temporal_context.build_temporal_context_surface()

    assert context["day_phase"] == "late_morning"
    assert context["is_peak_focus"] is True
    assert "Monday 10:00" in surface["summary"]
