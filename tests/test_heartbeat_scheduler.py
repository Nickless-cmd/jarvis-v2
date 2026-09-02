"""Planlægger-dæmonen — udskilt fra heartbeat_runtime 2026-09-02.

Baggrund: en stilstand hvor runtimen selv meldte `due: true` i over ti minutter
uden at slå, og hvor kun en genstart hjalp. Vi kunne ikke afgøre det enkleste
spørgsmål — TÆLLER LØKKEN VIDERE? — fordi iterations-loggen stod på debug og
aldrig kom ud. Derfor tælleren, og derfor disse tests.
"""
from __future__ import annotations

import threading
import time

import pytest

from core.services import heartbeat_scheduler as sched


@pytest.fixture(autouse=True)
def _rene_globaler():
    sched._STOP.set()
    if sched._THREAD and sched._THREAD.is_alive():
        sched._THREAD.join(timeout=1.0)
    sched._THREAD = None
    sched._ITERATION = 0
    sched._STOP.clear()
    yield
    sched._STOP.set()
    sched._THREAD = None


def test_taelleren_starter_paa_nul():
    assert sched.iterations() == 0


def test_loekken_taeller_hvert_gennemloeb(monkeypatch):
    """Uden dette tal kan en tavs tråd ikke skelnes fra en tråd der kører uden
    at udrette noget — og den forskel afgør hvor man skal lede."""
    calls: list[str] = []

    class _FakeHb:
        event_bus = type("B", (), {"publish": staticmethod(lambda *a, **k: None)})()

        @staticmethod
        def _poll_heartbeat_schedule_with_trigger(**kw):
            return {}

        @staticmethod
        def poll_heartbeat_schedule(*, name):
            calls.append(name)

    # `from core.services import heartbeat_runtime` henter ATTRIBUTTEN på
    # pakken — ikke sys.modules — når modulet allerede er importeret. Derfor
    # skal attrappen sættes dér.
    import core.services as pkg
    monkeypatch.setattr(pkg, "heartbeat_runtime", _FakeHb)
    monkeypatch.setattr(sched, "INTERVAL_SECONDS", 0.01)

    t = threading.Thread(
        target=sched._loop,
        kwargs={"name": "test", "startup_recovery_requested": False},
        daemon=True,
    )
    t.start()
    time.sleep(0.2)
    sched._STOP.set()
    t.join(timeout=1.0)

    assert sched.iterations() >= 2
    assert calls, "pollet blev aldrig kaldt"


def test_en_fejl_i_et_gennemloeb_draeber_ikke_loekken(monkeypatch):
    """En dårlig runde må ikke stoppe hjertet — den skal logges og fortsætte."""
    seen: list[int] = []

    class _FakeHb:
        event_bus = type("B", (), {"publish": staticmethod(lambda *a, **k: None)})()

        @staticmethod
        def _poll_heartbeat_schedule_with_trigger(**kw):
            return {}

        @staticmethod
        def poll_heartbeat_schedule(*, name):
            seen.append(1)
            raise RuntimeError("noget gik galt")

    # `from core.services import heartbeat_runtime` henter ATTRIBUTTEN på
    # pakken — ikke sys.modules — når modulet allerede er importeret. Derfor
    # skal attrappen sættes dér.
    import core.services as pkg
    monkeypatch.setattr(pkg, "heartbeat_runtime", _FakeHb)
    monkeypatch.setattr(sched, "INTERVAL_SECONDS", 0.01)

    t = threading.Thread(
        target=sched._loop,
        kwargs={"name": "test", "startup_recovery_requested": False},
        daemon=True,
    )
    t.start()
    time.sleep(0.2)
    sched._STOP.set()
    t.join(timeout=1.0)

    assert len(seen) >= 2, "løkken stoppede ved første fejl"


def test_is_running_er_falsk_uden_traad():
    assert sched.is_running() is False


def test_de_gamle_navne_virker_stadig():
    """Udskillelsen må ikke kunne mærkes fra kaldestedet (apps/api importerer
    start_heartbeat_scheduler direkte)."""
    from core.services.heartbeat_runtime import (
        _heartbeat_scheduler_running,
        start_heartbeat_scheduler,
        stop_heartbeat_scheduler,
    )
    assert callable(start_heartbeat_scheduler)
    assert callable(stop_heartbeat_scheduler)
    assert _heartbeat_scheduler_running() is False
