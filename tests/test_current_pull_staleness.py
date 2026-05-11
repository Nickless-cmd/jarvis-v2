from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


def test_compute_landscape_returns_none_when_thin(monkeypatch):
    from core.services import current_pull

    monkeypatch.setattr(current_pull, "_collect_appetite_texts", lambda *, days_back: [])
    monkeypatch.setattr(current_pull, "_collect_chronicle_texts", lambda *, days_back: [])
    monkeypatch.setattr(current_pull, "_collect_journal_texts", lambda *, days_back: [])

    assert current_pull._compute_landscape_embedding() is None


def test_compute_landscape_returns_none_when_only_one_item(monkeypatch):
    from core.services import current_pull

    monkeypatch.setattr(current_pull, "_collect_appetite_texts", lambda *, days_back: ["én appetit"])
    monkeypatch.setattr(current_pull, "_collect_chronicle_texts", lambda *, days_back: [])
    monkeypatch.setattr(current_pull, "_collect_journal_texts", lambda *, days_back: [])

    assert current_pull._compute_landscape_embedding() is None


def test_compute_landscape_returns_mean_when_enough_items(monkeypatch):
    from core.services import current_pull

    monkeypatch.setattr(current_pull, "_collect_appetite_texts",
                        lambda *, days_back: ["lyst til lyd under vand"])
    monkeypatch.setattr(current_pull, "_collect_chronicle_texts",
                        lambda *, days_back: ["uge med fokus på lyd og resonans"])
    monkeypatch.setattr(current_pull, "_collect_journal_texts", lambda *, days_back: [])

    # Use a fake embedder to keep the test deterministic and avoid torch/CUDA
    # env brittleness. Production verifies real embedder via smoke test.
    class FakeEmbedder:
        def encode(self, texts, normalize_embeddings=True):
            import numpy as np
            # Deterministic: each text maps to a fixed-length vector based on length
            return np.array([[float((len(t) + i) % 7) / 10.0 for i in range(8)] for t in texts])

    monkeypatch.setattr(
        "core.services.experience_substrate._get_embedder",
        lambda: FakeEmbedder(),
    )

    landscape = current_pull._compute_landscape_embedding()
    assert landscape is not None
    assert isinstance(landscape, list)
    assert len(landscape) == 8
    assert all(isinstance(x, float) for x in landscape)


def test_collect_appetite_texts_filters_low_intensity(monkeypatch):
    from core.services import current_pull

    fake_appetites = [
        {"type": "craft-appetite", "label": "lyst A", "intensity": 0.8},
        {"type": "curiosity-appetite", "label": "lyst B", "intensity": 0.1},  # below 0.2
        {"type": "connection-appetite", "label": "", "intensity": 0.9},        # empty label
        {"type": "craft-appetite", "label": "lyst C", "intensity": 0.5},
    ]
    monkeypatch.setattr(
        "core.services.desire_daemon.get_active_appetites",
        lambda: fake_appetites,
    )
    texts = current_pull._collect_appetite_texts(days_back=3)
    assert "lyst A" in texts
    assert "lyst C" in texts
    assert "lyst B" not in texts
    assert "" not in texts


def test_pull_is_stale_returns_false_when_landscape_thin(monkeypatch):
    from core.services import current_pull

    monkeypatch.setattr(current_pull, "_compute_landscape_embedding", lambda: None)
    is_stale, score = current_pull._pull_is_stale("min pull tekst")
    assert is_stale is False
    assert score == 0.0


def test_pull_is_stale_true_when_cos_below_threshold(monkeypatch):
    from core.services import current_pull

    monkeypatch.setattr(current_pull, "_compute_landscape_embedding",
                        lambda: [1.0, 0.0, 0.0, 0.0])

    class FakeEmbedder:
        def encode(self, text, normalize_embeddings=True):
            import numpy as np
            return np.array([0.0, 1.0, 0.0, 0.0])  # orthogonal → cos = 0

    monkeypatch.setattr(
        "core.services.experience_substrate._get_embedder",
        lambda: FakeEmbedder(),
    )

    class FakeSettings:
        current_pull_staleness_threshold = 0.45

    monkeypatch.setattr(current_pull, "load_settings", lambda: FakeSettings())

    is_stale, score = current_pull._pull_is_stale("min pull tekst")
    assert is_stale is True
    assert score < 0.45


def test_pull_is_stale_false_when_cos_above_threshold(monkeypatch):
    from core.services import current_pull

    monkeypatch.setattr(current_pull, "_compute_landscape_embedding",
                        lambda: [1.0, 0.0, 0.0, 0.0])

    class FakeEmbedder:
        def encode(self, text, normalize_embeddings=True):
            import numpy as np
            return np.array([1.0, 0.0, 0.0, 0.0])  # identical → cos = 1.0

    monkeypatch.setattr(
        "core.services.experience_substrate._get_embedder",
        lambda: FakeEmbedder(),
    )

    class FakeSettings:
        current_pull_staleness_threshold = 0.45

    monkeypatch.setattr(current_pull, "load_settings", lambda: FakeSettings())

    is_stale, score = current_pull._pull_is_stale("min pull tekst")
    assert is_stale is False
    assert score > 0.9


def test_archive_refresh_event_appends_and_caps_at_5():
    from core.services import current_pull

    state: dict = {}
    for i in range(7):
        current_pull._archive_refresh_event(
            state=state,
            refreshed_at=f"2026-05-{11+i:02d}T19:00:00+00:00",
            reason="stale",
            stale_score=0.30 + i * 0.01,
            previous_pull=f"pull {i}",
        )

    history = state["refresh_history"]
    assert len(history) == 5
    assert history[0]["previous_pull"] == "pull 2"
    assert history[-1]["previous_pull"] == "pull 6"


def test_should_run_staleness_check_first_time():
    from core.services import current_pull

    state = {}
    assert current_pull._should_run_staleness_check(state, interval_hours=12) is True


def test_should_run_staleness_check_within_window():
    from core.services import current_pull

    state = {
        "last_staleness_checked_at": (
            datetime.now(UTC) - timedelta(hours=3)
        ).isoformat()
    }
    assert current_pull._should_run_staleness_check(state, interval_hours=12) is False


def test_should_run_staleness_check_after_window():
    from core.services import current_pull

    state = {
        "last_staleness_checked_at": (
            datetime.now(UTC) - timedelta(hours=13)
        ).isoformat()
    }
    assert current_pull._should_run_staleness_check(state, interval_hours=12) is True
