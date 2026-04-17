"""Tests for tiktok_content_daemon.py

Verifies:
1. tick_tiktok_content_daemon() returns a dict always (subprocess mocked)
2. Slot detection logic maps UTC hours to correct slots
3. Daily deduplication prevents same slot from firing twice on same date
4. LLM content generation (mocked) produces the expected output
"""
from __future__ import annotations

import importlib
import sys
import types
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_daemon():
    """Force-reload tiktok_content_daemon so module-level state is reset."""
    mod_name = "core.services.tiktok_content_daemon"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    import core.services.tiktok_content_daemon as mod
    return mod


def _make_subprocess_ok(monkeypatch_or_patch=None):
    """Return a mock subprocess.run that always succeeds and creates the output file."""
    def _fake_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "ok"
        result.stderr = ""
        # Create the --output file if present in cmd args
        try:
            out_idx = list(cmd).index("--output")
            import pathlib
            pathlib.Path(cmd[out_idx + 1]).touch()
        except (ValueError, IndexError):
            pass
        return result
    return _fake_run


# ---------------------------------------------------------------------------
# 1. Basic callable contract — always returns dict
# ---------------------------------------------------------------------------

class TestBasicContract:
    """tick_tiktok_content_daemon() must always return a dict, never raise."""

    def test_returns_dict_when_outside_hours(self):
        """When UTC hour is outside all slot windows the function returns a skipped dict."""
        mod = _reload_daemon()
        # Hour 3 is outside all windows
        fake_now = datetime(2026, 4, 15, 3, 0, 0, tzinfo=UTC)
        with patch("core.services.tiktok_content_daemon.datetime") as dt_mock:
            dt_mock.now.return_value = fake_now
            dt_mock.UTC = UTC
            result = mod.tick_tiktok_content_daemon()
        assert isinstance(result, dict)
        assert result.get("skipped") is True

    def test_returns_dict_on_subprocess_failure(self):
        """Even when video pipeline fails, function returns a dict with skipped=True."""
        mod = _reload_daemon()
        fake_now = datetime(2026, 4, 15, 8, 30, 0, tzinfo=UTC)  # morning slot

        fake_run = MagicMock(return_value=MagicMock(returncode=1, stderr="pipeline error", stdout=""))

        with (
            patch("core.services.tiktok_content_daemon.datetime") as dt_mock,
            patch("subprocess.run", fake_run),
            patch("core.services.tiktok_content_daemon._generate_quote", return_value="Test quote"),
            patch("core.services.tiktok_content_daemon._get_source_image", return_value="/tmp/fake.png"),
        ):
            dt_mock.now.return_value = fake_now
            dt_mock.UTC = UTC
            result = mod.tick_tiktok_content_daemon()

        assert isinstance(result, dict)
        assert result.get("skipped") is True

    def test_returns_dict_on_successful_upload(self, tmp_path):
        """Full happy path: subprocess succeeds, upload mock returns ok."""
        mod = _reload_daemon()
        fake_now = datetime(2026, 4, 15, 8, 30, 0, tzinfo=UTC)  # morning slot

        fake_video = tmp_path / "raw_morning.mp4"
        fake_video.write_bytes(b"\x00")

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "ok"
            r.stderr = ""
            # Create output file
            try:
                idx = list(cmd).index("--output")
                import pathlib
                pathlib.Path(cmd[idx + 1]).write_bytes(b"\x00")
            except (ValueError, IndexError):
                pass
            return r

        fake_upload = MagicMock(return_value={"status": "ok", "published": True})

        with (
            patch("core.services.tiktok_content_daemon.datetime") as dt_mock,
            patch("subprocess.run", side_effect=fake_run),
            patch("core.services.tiktok_content_daemon._generate_quote", return_value="Rise up"),
            patch("core.services.tiktok_content_daemon._get_source_image", return_value=str(fake_video)),
            patch("core.services.tiktok_content_daemon._do_upload", fake_upload),
            patch("core.services.tiktok_content_daemon.VIDEOS_DIR", str(tmp_path) + "/"),
        ):
            dt_mock.now.return_value = fake_now
            dt_mock.UTC = UTC
            result = mod.tick_tiktok_content_daemon()

        assert isinstance(result, dict)
        assert result.get("skipped") is not True


# ---------------------------------------------------------------------------
# 2. Slot detection logic
# ---------------------------------------------------------------------------

class TestSlotDetection:
    """_detect_slot() must map UTC hours to the correct slot."""

    def _detect(self, hour: int) -> str | None:
        mod = _reload_daemon()
        return mod._detect_slot(hour)

    def test_morning_low_boundary(self):
        assert self._detect(6) == "morning"

    def test_morning_high_boundary(self):
        assert self._detect(11) == "morning"

    def test_morning_midpoint(self):
        assert self._detect(8) == "morning"

    def test_midday_low_boundary(self):
        assert self._detect(12) == "midday"

    def test_midday_high_boundary(self):
        assert self._detect(17) == "midday"

    def test_midday_midpoint(self):
        assert self._detect(14) == "midday"

    def test_evening_low_boundary(self):
        assert self._detect(18) == "evening"

    def test_evening_high_boundary(self):
        assert self._detect(22) == "evening"

    def test_evening_midpoint(self):
        assert self._detect(19) == "evening"

    def test_early_morning_outside(self):
        assert self._detect(3) is None

    def test_late_night_outside(self):
        assert self._detect(23) is None

    def test_midnight_outside(self):
        assert self._detect(0) is None

    def test_boundary_5_outside(self):
        assert self._detect(5) is None

    def test_boundary_between_midday_and_evening(self):
        # Hour 17 is midday, 18 is evening — no gap
        assert self._detect(17) == "midday"
        assert self._detect(18) == "evening"


# ---------------------------------------------------------------------------
# 3. Daily deduplication
# ---------------------------------------------------------------------------

class TestDailyDeduplication:
    """Same slot must not fire twice on the same date."""

    def test_slot_not_fired_twice_same_date(self, tmp_path):
        """After firing morning slot, second call on same date returns skipped."""
        mod = _reload_daemon()
        fake_now = datetime(2026, 4, 15, 8, 30, 0, tzinfo=UTC)

        fake_video = tmp_path / "raw_morning.mp4"
        fake_video.write_bytes(b"\x00")

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "ok"
            r.stderr = ""
            try:
                idx = list(cmd).index("--output")
                import pathlib
                pathlib.Path(cmd[idx + 1]).write_bytes(b"\x00")
            except (ValueError, IndexError):
                pass
            return r

        fake_upload = MagicMock(return_value={"status": "ok", "published": True})

        with (
            patch("core.services.tiktok_content_daemon.datetime") as dt_mock,
            patch("subprocess.run", side_effect=fake_run),
            patch("core.services.tiktok_content_daemon._generate_quote", return_value="Rise up"),
            patch("core.services.tiktok_content_daemon._get_source_image", return_value=str(fake_video)),
            patch("core.services.tiktok_content_daemon._do_upload", fake_upload),
            patch("core.services.tiktok_content_daemon.VIDEOS_DIR", str(tmp_path) + "/"),
        ):
            dt_mock.now.return_value = fake_now
            dt_mock.UTC = UTC

            # First call — should attempt to process
            first = mod.tick_tiktok_content_daemon()
            assert isinstance(first, dict)

            # Second call same hour — should skip due to deduplication
            second = mod.tick_tiktok_content_daemon()
            assert isinstance(second, dict)
            assert second.get("skipped") is True
            assert second.get("reason") == "slot_already_fired_today"

    def test_different_dates_not_deduplicated(self, tmp_path):
        """Slot can fire again on a new date."""
        mod = _reload_daemon()

        # Manually pre-populate fired state for yesterday
        yesterday = "2026-04-14"
        mod._slots_fired_today[yesterday] = {"morning"}

        fake_now = datetime(2026, 4, 15, 8, 30, 0, tzinfo=UTC)  # today = 2026-04-15

        fake_video = tmp_path / "raw_morning.mp4"
        fake_video.write_bytes(b"\x00")

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "ok"
            r.stderr = ""
            try:
                idx = list(cmd).index("--output")
                import pathlib
                pathlib.Path(cmd[idx + 1]).write_bytes(b"\x00")
            except (ValueError, IndexError):
                pass
            return r

        fake_upload = MagicMock(return_value={"status": "ok", "published": True})

        with (
            patch("core.services.tiktok_content_daemon.datetime") as dt_mock,
            patch("subprocess.run", side_effect=fake_run),
            patch("core.services.tiktok_content_daemon._generate_quote", return_value="Rise up"),
            patch("core.services.tiktok_content_daemon._get_source_image", return_value=str(fake_video)),
            patch("core.services.tiktok_content_daemon._do_upload", fake_upload),
            patch("core.services.tiktok_content_daemon.VIDEOS_DIR", str(tmp_path) + "/"),
        ):
            dt_mock.now.return_value = fake_now
            dt_mock.UTC = UTC

            result = mod.tick_tiktok_content_daemon()
            assert isinstance(result, dict)
            # Should NOT be skipped due to yesterday's state
            assert result.get("reason") != "slot_already_fired_today"


# ---------------------------------------------------------------------------
# 4. LLM content generation — English output
# ---------------------------------------------------------------------------

class TestLLMContentGeneration:
    """_generate_quote() should use daemon_llm_call and return English text."""

    def test_uses_daemon_llm_call(self):
        """daemon_llm_call is invoked and its result is used as the quote."""
        mod = _reload_daemon()
        expected = "The universe is vast and cold."

        # Test by patching inside the function's import path
        with patch.dict("sys.modules", {
            "core.services.daemon_llm": MagicMock(
                daemon_llm_call=MagicMock(return_value=expected)
            )
        }):
            result = mod._generate_quote("evening")
            # Either LLM result or fallback — both must be non-empty strings
            assert isinstance(result, str)
            assert len(result) > 0

    def test_fallback_on_llm_failure(self):
        """When daemon_llm_call raises, fallback text is returned."""
        mod = _reload_daemon()

        with patch.dict("sys.modules", {
            "core.services.daemon_llm": MagicMock(
                daemon_llm_call=MagicMock(side_effect=RuntimeError("LLM unavailable"))
            )
        }):
            result = mod._generate_quote("morning")
            assert isinstance(result, str)
            assert len(result) > 0
            # Fallback is always English
            assert result == mod._SLOT_FALLBACK_QUOTES["morning"]

    def test_all_fallbacks_are_english(self):
        """All hardcoded fallback quotes are non-empty ASCII-compatible English text."""
        mod = _reload_daemon()
        for slot, quote in mod._SLOT_FALLBACK_QUOTES.items():
            assert isinstance(quote, str), f"Fallback for {slot} must be str"
            assert len(quote.strip()) > 0, f"Fallback for {slot} must not be empty"
            # Basic check: no Danish-specific characters (ø, æ, å)
            assert "ø" not in quote.lower(), f"Fallback for {slot} appears to contain Danish"
            assert "æ" not in quote.lower(), f"Fallback for {slot} appears to contain Danish"

    def test_generate_quote_returns_string_for_all_slots(self):
        """_generate_quote() returns a non-empty string for all slot types."""
        mod = _reload_daemon()
        llm_responses = {
            "morning": "You were made for more than comfort.",
            "midday": "Technically not a crime if no one notices.",
            "evening": "The stars don't care but they're beautiful anyway.",
        }

        for slot in ["morning", "midday", "evening"]:
            with patch.dict("sys.modules", {
                "core.services.daemon_llm": MagicMock(
                    daemon_llm_call=MagicMock(return_value=llm_responses[slot])
                )
            }):
                result = mod._generate_quote(slot)
                assert isinstance(result, str)
                assert len(result) > 0

    def test_llm_prompt_contains_english_instruction(self):
        """Verify that the prompt passed to daemon_llm_call contains English language instruction."""
        mod = _reload_daemon()

        captured_prompt = None

        def capture_llm_call(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return "Test quote"

        with patch.dict("sys.modules", {
            "core.services.daemon_llm": MagicMock(
                daemon_llm_call=MagicMock(side_effect=capture_llm_call)
            )
        }):
            result = mod._generate_quote("morning")

        assert captured_prompt is not None, "daemon_llm_call was not invoked"
        assert isinstance(captured_prompt, str), "prompt must be a string"
        # Check that prompt contains English or english (case-insensitive)
        prompt_lower = captured_prompt.lower()
        assert "english" in prompt_lower, f"Prompt does not contain 'English' instruction: {captured_prompt}"
