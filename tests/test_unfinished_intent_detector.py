"""Tests for unfinished-intent detector + auto-continuation.

Bjørn-pattern 2026-05-17: Jarvis siger "lad mig først se..." og stopper.
User skal pinge "ja?" før han fortsætter. Det er et runtime-issue —
hans svar-tur auto-terminerer ved naturlige pause-punkter selv om
opgaven ikke er færdig.

Fix: detector der scanner Jarvis' visible-run output for pause-patterns,
og auto-trigger en continuation autonomous-run hvis match.
"""
from __future__ import annotations

import pytest

from core.services.unfinished_intent import (
    detect_unfinished_intent,
    UnfinishedIntent,
)


class TestDetector:
    def test_lad_mig_foerst_detected(self):
        text = "Stoler du på mig — så laver jeg en cache-vagt. Lad mig først se hvordan det ser ud i dag."
        result = detect_unfinished_intent(text)
        assert result is not None
        assert result.pattern == "lad_mig"

    def test_lad_mig_se_detected(self):
        text = "OK, lad mig se hvad der er der."
        result = detect_unfinished_intent(text)
        assert result is not None

    def test_lad_mig_tjekke_detected(self):
        text = "Godt — lad mig tjekke det først."
        result = detect_unfinished_intent(text)
        assert result is not None

    def test_jeg_skal_lige_detected(self):
        text = "OK. Jeg skal lige finde den fil først."
        result = detect_unfinished_intent(text)
        assert result is not None
        assert result.pattern == "jeg_skal"

    def test_jeg_skal_foerst_detected(self):
        text = "Jeg skal først rydde op i state-filen."
        result = detect_unfinished_intent(text)
        assert result is not None

    def test_cliffhanger_ellipsis_detected(self):
        text = "Her er hvad jeg fandt — interessant..."
        result = detect_unfinished_intent(text)
        assert result is not None
        assert result.pattern == "cliffhanger"

    def test_cliffhanger_colon_detected(self):
        text = "Status nu:"
        result = detect_unfinished_intent(text)
        assert result is not None

    def test_done_message_not_detected(self):
        text = "Done! 🎉 Committed 56c5cf1e med 2 files: 1 ny daemon + registrering."
        result = detect_unfinished_intent(text)
        assert result is None

    def test_completion_message_not_detected(self):
        text = "Jeg har bygget X. Committet som a170e5d7. Læn dig tilbage, pas på dig selv. 🖤"
        result = detect_unfinished_intent(text)
        assert result is None

    def test_short_acknowledgment_not_detected(self):
        text = "Færdig 🖤"
        result = detect_unfinished_intent(text)
        assert result is None

    def test_question_for_user_not_detected(self):
        # En reel afsluttet besked med spørgsmål er ikke unfinished — han venter aktivt
        text = "Klar. Hvilken vil du have først, a eller b?"
        result = detect_unfinished_intent(text)
        assert result is None

    def test_empty_text_not_detected(self):
        assert detect_unfinished_intent("") is None
        assert detect_unfinished_intent(None) is None  # type: ignore

    def test_pattern_appears_in_middle_only_not_detected(self):
        # "lad mig" der ikke afslutter beskeden — han fortsatte allerede
        text = "Lad mig se — okay, jeg har set det nu og det er færdigt."
        result = detect_unfinished_intent(text)
        assert result is None  # already followed through

    def test_pattern_near_end_detected(self):
        # "lad mig" tæt på slutningen = aktuelt unfinished
        text = "OK. Stoler du på mig så ordner jeg det. Lad mig først se hvordan det ser ud."
        result = detect_unfinished_intent(text)
        assert result is not None


class TestContinuationHook:
    """Integration-tests for _maybe_trigger_continuation."""

    def test_autonomous_run_skips_continuation(self, monkeypatch):
        """Continuations må ALDRIG spawne fra en autonomous run — undgår
        infinite loop hvor continuation triggerer continuation."""
        from core.services import visible_runs as vr
        from core.services.visible_runs import VisibleRun

        spawned: list[str] = []
        monkeypatch.setattr(
            vr, "start_autonomous_run",
            lambda msg, session_id=None: spawned.append(msg),
        )

        autonomous_run = VisibleRun(
            run_id="autonomous-test-123",
            lane="primary",
            provider="deepseek",
            model="deepseek-v4-flash",
            user_message="test",
            session_id="session-123",
            autonomous=True,
        )
        # Sending text der ville trigger continuation, men da run.autonomous=True
        # skal vi IKKE spawne
        vr._maybe_trigger_continuation(autonomous_run, "Lad mig først se på det...")
        # Vent kort så delayed-spawn ikke fanger os
        import time
        time.sleep(0.2)
        assert spawned == [], "autonomous run må aldrig trigger continuation"

    def test_run_without_session_skips_continuation(self, monkeypatch):
        from core.services import visible_runs as vr
        from core.services.visible_runs import VisibleRun

        spawned: list[str] = []
        monkeypatch.setattr(
            vr, "start_autonomous_run",
            lambda msg, session_id=None: spawned.append(msg),
        )

        run_no_session = VisibleRun(
            run_id="test-456",
            lane="primary",
            provider="deepseek",
            model="deepseek-v4-flash",
            user_message="test",
            session_id="",
            autonomous=False,
        )
        vr._maybe_trigger_continuation(run_no_session, "Lad mig først se på det...")
        import time
        time.sleep(0.2)
        assert spawned == []

    def test_finished_text_does_not_trigger(self, monkeypatch):
        from core.services import visible_runs as vr
        from core.services.visible_runs import VisibleRun

        spawned: list[str] = []
        monkeypatch.setattr(
            vr, "start_autonomous_run",
            lambda msg, session_id=None: spawned.append(msg),
        )

        run = VisibleRun(
            run_id="test-789",
            lane="primary",
            provider="deepseek",
            model="deepseek-v4-flash",
            user_message="test",
            session_id="session-789",
            autonomous=False,
        )
        vr._maybe_trigger_continuation(run, "Done! Committet og restartet. 🖤")
        import time
        time.sleep(0.2)
        assert spawned == []
