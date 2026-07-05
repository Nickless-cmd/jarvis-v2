"""Tests for file_awareness_daemon — somatic awareness of file changes.

Fase 1 of somatic awareness spec: Jarvis should FEEL when someone touches
his files, not just read about it later.
"""
from __future__ import annotations

import importlib
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fam():
    """Import the module fresh for each test (resets global state)."""
    import core.services.file_awareness_daemon as _fam
    importlib.reload(_fam)
    _fam._event_buffer.clear()
    return _fam


# ---------------------------------------------------------------------------
# 1. Change classification
# ---------------------------------------------------------------------------

class TestChangeClassification:
    def test_classifies_py_as_code(self, fam):
        assert fam._classify_change("test.py") == "code"

    def test_classifies_json_as_data(self, fam):
        assert fam._classify_change("config.json") == "data"

    def test_classifies_md_as_data(self, fam):
        assert fam._classify_change("README.md") == "data"

    def test_classifies_yaml_as_data(self, fam):
        assert fam._classify_change("settings.yaml") == "data"

    def test_classifies_toml_as_data(self, fam):
        assert fam._classify_change("pyproject.toml") == "data"

    def test_classifies_unknown_as_data(self, fam):
        assert fam._classify_change("data.csv") == "data"


# ---------------------------------------------------------------------------
# 2. Should-track filtering
# ---------------------------------------------------------------------------

class TestShouldTrack:
    def test_tracks_py(self, fam):
        assert fam._should_track("module.py") is True

    def test_tracks_json(self, fam):
        assert fam._should_track("config.json") is True

    def test_tracks_md(self, fam):
        assert fam._should_track("README.md") is True

    def test_ignores_pyc(self, fam):
        assert fam._should_track("module.pyc") is False

    def test_ignores_swp(self, fam):
        assert fam._should_track(".file.swp") is False

    def test_ignores_git_dir(self, fam):
        assert fam._should_track(".git/HEAD") is False

    def test_ignores_pycache(self, fam):
        assert fam._should_track("__pycache__/module.cpython-311.pyc") is False

    def test_ignores_tmp(self, fam):
        assert fam._should_track("temp.tmp") is False

    def test_ignores_log(self, fam):
        assert fam._should_track("app.log") is False


# ---------------------------------------------------------------------------
# 3. Change recording
# ---------------------------------------------------------------------------

class TestChangeRecording:
    def test_record_change_adds_to_buffer(self, fam):
        initial = len(fam._event_buffer)
        fam._record_change("modified", "/tmp/test.py", is_directory=False)
        assert len(fam._event_buffer) == initial + 1

    def test_record_change_classifies(self, fam):
        fam._record_change("created", "/tmp/test.py", is_directory=False)
        event = fam._event_buffer[-1]
        assert event["kind"] == "code"

    def test_record_change_publishes_eventbus(self, fam):
        with patch("core.eventbus.bus.event_bus") as mock_bus:
            fam._record_change("modified", "/tmp/test.py", is_directory=False)
            assert mock_bus.publish.called

    def test_record_change_skips_directories(self, fam):
        initial = len(fam._event_buffer)
        fam._record_change("modified", "/tmp/__pycache__", is_directory=True)
        assert len(fam._event_buffer) == initial

    def test_record_change_has_timestamp(self, fam):
        fam._record_change("modified", "/tmp/test.py", is_directory=False)
        event = fam._event_buffer[-1]
        assert "ts" in event

    def test_record_change_has_path(self, fam):
        fam._record_change("modified", "/tmp/test.py", is_directory=False)
        event = fam._event_buffer[-1]
        assert event["path"] == "/tmp/test.py"

    def test_record_change_has_external_flag(self, fam):
        fam._record_change("modified", "/tmp/test.py", is_directory=False)
        event = fam._event_buffer[-1]
        assert "external" in event


# ---------------------------------------------------------------------------
# 4. get_recent_events
# ---------------------------------------------------------------------------

class TestGetRecentEvents:
    def test_returns_list(self, fam):
        result = fam.get_recent_events()
        assert isinstance(result, list)

    def test_returns_recorded_events(self, fam):
        fam._record_change("modified", "/tmp/test.py", is_directory=False)
        events = fam.get_recent_events(limit=10)
        assert len(events) >= 1
        assert events[-1]["kind"] == "code"

    def test_respects_limit(self, fam):
        for i in range(30):
            fam._record_change("modified", f"/tmp/file{i}.py", is_directory=False)
        events = fam.get_recent_events(limit=5)
        assert len(events) <= 5


# ---------------------------------------------------------------------------
# 5. has_recent_events
# ---------------------------------------------------------------------------

class TestHasRecentEvents:
    def test_false_when_empty(self, fam):
        assert fam.has_recent_events(seconds=300) is False

    def test_true_after_change(self, fam):
        fam._record_change("modified", "/tmp/test.py", is_directory=False)
        assert fam.has_recent_events(seconds=300) is True


# ---------------------------------------------------------------------------
# 6. tick_file_awareness (daemon entry point)
# ---------------------------------------------------------------------------

class TestTickFunction:
    def test_tick_returns_dict(self, fam):
        """tick_file_awareness should return a result dict."""
        result = fam.tick_file_awareness()
        assert isinstance(result, dict)
        assert "active" in result
        assert "events_buffered" in result

    def test_tick_reports_events(self, fam):
        """Tick should report number of buffered events."""
        fam._record_change("modified", "/tmp/test.py", is_directory=False)
        result = fam.tick_file_awareness()
        assert result.get("events_buffered", 0) >= 1

    def test_tick_reports_clean_when_no_events(self, fam):
        """Tick with no events should report zero buffered."""
        result = fam.tick_file_awareness()
        assert result.get("events_buffered", 0) == 0


# ---------------------------------------------------------------------------
# 7. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_buffer_is_bounded(self, fam):
        """Buffer should not grow beyond _BUFFER_SIZE."""
        for i in range(200):
            fam._record_change("modified", f"/tmp/file{i}.py", is_directory=False)
        assert len(fam._event_buffer) <= 20  # _BUFFER_SIZE = 20

    def test_external_detection_default(self, fam):
        """Changes should be marked external by default (no git process)."""
        fam._record_change("modified", "/tmp/test.py", is_directory=False)
        event = fam._event_buffer[-1]
        assert event["external"] is True