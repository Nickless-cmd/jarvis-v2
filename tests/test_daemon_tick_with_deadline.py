"""Tests for _daemon_tick_with_deadline helper.

Bug 2026-05-17: en daemon der hænger på et LLM-kald forbi heartbeat-tick's
deadline holdt currently_ticking-låsen i timevis. Senere daemons i kæden
fyrede aldrig. Fix: wrap alle inline-daemons med per-call deadline så
ÉN langsom daemon ikke blokerer 20+ andre.

Disse tests verificerer at:
1. Hurtig daemon returnerer normalt (happy-path)
2. Daemon der hænger forbi deadline orphan'es og returnerer None
3. Orphan publisher heartbeat.daemon_tick_deadline_exceeded event
4. Exception i daemon swallow'es (returnerer None) — heartbeat fortsætter
"""
from __future__ import annotations

import time

from core.services import heartbeat_runtime as hb


def test_daemon_tick_with_deadline_returns_result_when_fast() -> None:
    """Happy-path: hurtig daemon returnerer result normalt."""
    def _fast_daemon() -> dict[str, str]:
        return {"status": "ok"}

    result = hb._daemon_tick_with_deadline(
        "test-fast", _fast_daemon, deadline_seconds=2.0,
    )
    assert result == {"status": "ok"}


def test_daemon_tick_with_deadline_orphans_on_timeout(monkeypatch) -> None:
    """Daemon der hænger forbi deadline orphan'es — returnerer None."""
    def _slow_daemon() -> dict[str, str]:
        time.sleep(5.0)  # langsommere end deadline
        return {"status": "should-not-reach"}

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        hb.event_bus, "publish",
        lambda name, payload: events.append((name, payload)),
    )

    t0 = time.perf_counter()
    result = hb._daemon_tick_with_deadline(
        "test-slow", _slow_daemon, deadline_seconds=0.5,
    )
    elapsed = time.perf_counter() - t0

    assert result is None, "orphaned daemon skal returnere None"
    assert elapsed < 2.0, f"deadline-tick må ikke vente fuld 5s, faktisk {elapsed:.1f}s"
    deadline_events = [e for e in events if e[0] == "heartbeat.daemon_tick_deadline_exceeded"]
    assert deadline_events, "forventede heartbeat.daemon_tick_deadline_exceeded event"
    assert deadline_events[0][1]["daemon"] == "test-slow"


def test_daemon_tick_with_deadline_swallows_exception() -> None:
    """Exception i daemon må ikke bryde heartbeat-tick — returnerer None."""
    def _crashing_daemon() -> dict:
        raise RuntimeError("simuleret daemon-crash")

    result = hb._daemon_tick_with_deadline(
        "test-crash", _crashing_daemon, deadline_seconds=2.0,
    )
    assert result is None


def test_daemon_pool_genbruger_traaden_i_stedet_for_at_foede_per_kald() -> None:
    """Poolen skal genbruge traaden — foer kostede hvert kald foe+doed.

    Maalt 13/10-2026: en raa traad per kald kostede 52 us CPU mod 14 us for at
    genbruge en traad der allerede findes. Der er 61 kaldesteder, saa forskellen
    loeber op. Testen pinner at kald nr. 2..N ikke foeder nye traade.
    """
    def _fast() -> dict[str, str]:
        return {"status": "ok"}

    # Varm puljen op, saa vi maaler genbrug og ikke den foerste spawn.
    assert hb._daemon_tick_with_deadline(
        "pool-warm", _fast, deadline_seconds=2.0,
    ) == {"status": "ok"}
    before = dict(hb._DAEMON_POOL_STATS)
    for i in range(10):
        assert hb._daemon_tick_with_deadline(
            f"pool-{i}", _fast, deadline_seconds=2.0,
        ) == {"status": "ok"}
    after = dict(hb._DAEMON_POOL_STATS)

    assert after["spawned"] == before["spawned"], (
        f"kaldene foe/dte nye traade i stedet for at genbruge: {before} -> {after}"
    )
    assert after["reused"] == before["reused"] + 10


def test_daemon_pool_traade_er_daemon_og_blokerer_ikke() -> None:
    """Puljens traade skal vaere daemon-traade — og en haengende daemon maa ikke
    blokere det naeste kald.

    Daemon-flaget er ikke kosmetik: ThreadPoolExecutor bruger NON-daemon-workers
    og joiner dem ved interpreter-exit, saa en haengende daemon ville kunne
    blokere en genstart. De raa traade i dag er daemon=True — det skal bevares.
    """
    import threading as _th

    def _hang() -> None:
        time.sleep(30.0)

    assert hb._daemon_tick_with_deadline(
        "pool-hang", _hang, deadline_seconds=0.5,
    ) is None

    t0 = time.perf_counter()
    assert hb._daemon_tick_with_deadline(
        "pool-efter", lambda: {"ok": True}, deadline_seconds=2.0,
    ) == {"ok": True}
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0, f"kaldet efter en haengende daemon blev blokeret ({elapsed:.2f}s)"

    pool_threads = [t for t in _th.enumerate() if t.name == "daemon-tick-pool"]
    assert pool_threads, "forventede mindst én traad i puljen"
    assert all(t.daemon for t in pool_threads), "puljens traade SKAL vaere daemon-traade"
