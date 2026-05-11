from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


def _make_sample(category: str, hours_ago: float) -> dict:
    sampled_at = (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()
    return {
        "sampled_at": sampled_at,
        "category": category,
        "amplitude_mean": 0.05,
        "amplitude_std": 0.01,
        "description": f"sample category={category}",
        "transcript": "",
    }


def test_count_music_samples_returns_zero_when_empty(monkeypatch):
    from core.services import ambient_sound_daemon

    monkeypatch.setattr(ambient_sound_daemon, "_state", lambda: {})
    music, total = ambient_sound_daemon.count_music_samples_last_hours(hours=24)
    assert music == 0
    assert total == 0


def test_count_music_samples_within_window(monkeypatch):
    from core.services import ambient_sound_daemon

    history = [
        _make_sample("music", 1),
        _make_sample("talk", 5),
        _make_sample("music", 10),
        _make_sample("silence", 20),
        _make_sample("music", 30),   # outside 24h window
        _make_sample("talk", 50),    # outside 24h window
    ]
    monkeypatch.setattr(ambient_sound_daemon, "_state", lambda: {"history": history})

    music, total = ambient_sound_daemon.count_music_samples_last_hours(hours=24)
    assert music == 2
    assert total == 4


def test_count_music_samples_handles_missing_sampled_at(monkeypatch):
    from core.services import ambient_sound_daemon

    history = [
        _make_sample("music", 1),
        {"category": "music"},  # no sampled_at — should be skipped
        _make_sample("music", 5),
    ]
    monkeypatch.setattr(ambient_sound_daemon, "_state", lambda: {"history": history})

    music, total = ambient_sound_daemon.count_music_samples_last_hours(hours=24)
    assert music == 2
    assert total == 2


def test_influence_phrase_full_day():
    from core.services.ambient_sound_daemon import _select_music_influence_phrase

    assert _select_music_influence_phrase(ratio=1.0) == "Musikken har haft dig hele dagen."


def test_influence_phrase_majority():
    from core.services.ambient_sound_daemon import _select_music_influence_phrase

    assert _select_music_influence_phrase(ratio=0.75) == "Rytmen kan bære dig."
    assert _select_music_influence_phrase(ratio=0.51) == "Rytmen kan bære dig."


def test_influence_phrase_minority():
    from core.services.ambient_sound_daemon import _select_music_influence_phrase

    assert _select_music_influence_phrase(ratio=0.5) == "Musik har været i rummet."
    assert _select_music_influence_phrase(ratio=0.25) == "Musik har været i rummet."


def test_accumulator_surface_empty_when_below_threshold(monkeypatch):
    from core.services import ambient_sound_daemon

    monkeypatch.setattr(
        ambient_sound_daemon, "count_music_samples_last_hours",
        lambda hours=24: (1, 4),
    )

    class FakeSettings:
        music_accumulator_threshold_samples = 2
        music_accumulator_window_hours = 24

    monkeypatch.setattr(ambient_sound_daemon, "load_settings", lambda: FakeSettings())
    assert ambient_sound_daemon.get_music_accumulator_for_prompt() == ""


def test_accumulator_surface_renders_full_day(monkeypatch):
    from core.services import ambient_sound_daemon

    monkeypatch.setattr(
        ambient_sound_daemon, "count_music_samples_last_hours",
        lambda hours=24: (4, 4),
    )

    class FakeSettings:
        music_accumulator_threshold_samples = 2
        music_accumulator_window_hours = 24

    monkeypatch.setattr(ambient_sound_daemon, "load_settings", lambda: FakeSettings())
    out = ambient_sound_daemon.get_music_accumulator_for_prompt()
    assert "Musik (sidste 24h): 4/4 samples" in out
    assert "Musikken har haft dig hele dagen." in out


def test_accumulator_surface_renders_majority(monkeypatch):
    from core.services import ambient_sound_daemon

    monkeypatch.setattr(
        ambient_sound_daemon, "count_music_samples_last_hours",
        lambda hours=24: (3, 4),
    )

    class FakeSettings:
        music_accumulator_threshold_samples = 2
        music_accumulator_window_hours = 24

    monkeypatch.setattr(ambient_sound_daemon, "load_settings", lambda: FakeSettings())
    out = ambient_sound_daemon.get_music_accumulator_for_prompt()
    assert "Musik (sidste 24h): 3/4 samples" in out
    assert "Rytmen kan bære dig." in out


def test_accumulator_surface_handles_total_zero(monkeypatch):
    from core.services import ambient_sound_daemon

    monkeypatch.setattr(
        ambient_sound_daemon, "count_music_samples_last_hours",
        lambda hours=24: (0, 0),
    )

    class FakeSettings:
        music_accumulator_threshold_samples = 2
        music_accumulator_window_hours = 24

    monkeypatch.setattr(ambient_sound_daemon, "load_settings", lambda: FakeSettings())
    assert ambient_sound_daemon.get_music_accumulator_for_prompt() == ""
