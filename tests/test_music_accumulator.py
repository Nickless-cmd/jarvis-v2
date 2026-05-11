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
