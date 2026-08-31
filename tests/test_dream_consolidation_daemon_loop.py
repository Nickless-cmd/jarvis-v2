"""Tests for drømme-konsolideringens egen kadence.

MÅLT 2026-08-30: konsolideringen blev kun vurderet når heartbeat tikkede.
På 30 dage faldt **0 af 237** heartbeat-ticks i et vindue med >= 30 min
stilhed — selvom der var **440** sådanne vinduer. Gaten krævede stilhed;
observatøren var der aldrig når der var stille. Derfor stod den stille fra
4. juni, selvom hver eneste anden gate var grøn.

Tråden her er rettelsen: den tikker på sin egen kadence og logger udfaldet,
så næste stilstand kan ses i journalen frem for at skulle måles frem.
"""

from __future__ import annotations

import logging
import threading

import pytest

import core.services.dream_consolidation_daemon as d


class TestLoopCadence:
    def test_loop_calls_tick_and_stops_on_event(self, monkeypatch) -> None:
        calls: list[float] = []
        stop = threading.Event()

        def fake_tick(seconds: float = 0.0):
            calls.append(seconds)
            stop.set()                      # stop efter første runde
            return {"skipped": True, "reason": "not-idle-1m"}

        monkeypatch.setattr(d, "tick", fake_tick)
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0)
        d.consolidation_loop(stop)
        assert calls == [0]

    def test_loop_survives_a_raising_tick(self, monkeypatch, caplog) -> None:
        """Heartbeat-kaldet lå i `except: pass` — en fejl forsvandt lydløst."""
        stop = threading.Event()
        seen = {"n": 0}

        def boom(seconds: float = 0.0):
            seen["n"] += 1
            stop.set()
            raise RuntimeError("syntese fejlede")

        monkeypatch.setattr(d, "tick", boom)
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0)
        with caplog.at_level(logging.ERROR):
            d.consolidation_loop(stop)      # må ikke kaste videre
        assert seen["n"] == 1
        assert "tick fejlede" in caplog.text

    def test_successful_run_is_logged_at_info(self, monkeypatch, caplog) -> None:
        """En drøm skal kunne ses i journalen, ikke kun i state-filen."""
        stop = threading.Event()

        def ran(seconds: float = 0.0):
            stop.set()
            return {"consolidation_id": "dream-abc123"}

        monkeypatch.setattr(d, "tick", ran)
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0)
        with caplog.at_level(logging.INFO):
            d.consolidation_loop(stop)
        assert "dream-abc123" in caplog.text
        assert "KØRTE" in caplog.text

    def test_skips_are_not_logged_at_info(self, monkeypatch, caplog) -> None:
        """En sprunget-over-runde hvert 5. minut må ikke fylde journalen."""
        stop = threading.Event()

        def skip(seconds: float = 0.0):
            stop.set()
            return {"skipped": True, "reason": "cooldown-2.0h"}

        monkeypatch.setattr(d, "tick", skip)
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0)
        with caplog.at_level(logging.INFO):
            d.consolidation_loop(stop)
        assert "cooldown" not in caplog.text

    def test_none_result_is_handled(self, monkeypatch) -> None:
        stop = threading.Event()
        monkeypatch.setattr(d, "tick", lambda s=0.0: (stop.set(), None)[1])
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0)
        d.consolidation_loop(stop)          # må ikke kaste


class TestStartStop:
    def teardown_method(self) -> None:
        d.stop_dream_consolidation_daemon()

    def test_start_spawns_a_named_daemon_thread(self, monkeypatch) -> None:
        monkeypatch.setattr(d, "tick", lambda s=0.0: {"skipped": True})
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0.05)
        d._DAEMON_STOP_EVENT = None
        d.start_dream_consolidation_daemon()
        assert d._DAEMON_THREAD is not None
        assert d._DAEMON_THREAD.daemon is True
        assert d._DAEMON_THREAD.name == "jarvis-dream-consolidation"

    def test_start_is_idempotent(self, monkeypatch) -> None:
        monkeypatch.setattr(d, "tick", lambda s=0.0: {"skipped": True})
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0.05)
        d._DAEMON_STOP_EVENT = None
        d.start_dream_consolidation_daemon()
        first = d._DAEMON_THREAD
        d.start_dream_consolidation_daemon()
        assert d._DAEMON_THREAD is first

    def test_stop_is_safe_when_never_started(self) -> None:
        d._DAEMON_STOP_EVENT = None
        d.stop_dream_consolidation_daemon()


class TestCadenceChoice:
    def test_interval_is_shorter_than_the_idle_window(self) -> None:
        """Vinduet skal opdages mens det stadig er der.

        Gaten kræver >= 30 min stilhed. Tikker vi sjældnere end det, kan et
        modent vindue nå at lukke igen uden at nogen så det — netop den fejl
        vi retter.
        """
        assert d._LOOP_INTERVAL_SECONDS < d._TRIGGER_IDLE_MINUTES * 60

    def test_interval_is_not_so_short_it_hammers(self) -> None:
        assert d._LOOP_INTERVAL_SECONDS >= 60
