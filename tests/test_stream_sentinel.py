"""Tests for Stream-cluster-sentinel (stream_sentinel).

Verificerer at SSE-lanens livscyklus emitteres til Centralen (observe), at note_stop er
idempotent (ingen dobbelt-emit ved done→finally-fallback), og at stall-backstoppen flagger
en stream der fik start men aldrig stop — alt self-safe (kaster aldrig).
"""
from __future__ import annotations

import pytest

from core.services import stream_sentinel as ss


@pytest.fixture(autouse=True)
def _clean_state():
    with ss._lock:
        ss._live.clear()
    yield
    with ss._lock:
        ss._live.clear()


@pytest.fixture
def captured(monkeypatch):
    events: list[dict] = []
    monkeypatch.setattr(ss, "_observe",
                        lambda nerve, run_id, session_id, **d: events.append(
                            {"nerve": nerve, "run_id": run_id, "session_id": session_id, **d}))
    return events


# ── livscyklus ───────────────────────────────────────────────────────────
def test_start_registers_and_observes(captured):
    ss.note_start("r1", "s1", model="glm")
    assert ss.live_count() == 1
    assert any(e["nerve"] == "stream_start" and e["run_id"] == "r1" for e in captured)


def test_stop_observes_and_clears(captured):
    ss.note_start("r1", "s1")
    ss.note_stop("r1", reason="done")
    assert ss.live_count() == 0
    stops = [e for e in captured if e["nerve"] == "stream_stop"]
    assert len(stops) == 1
    assert stops[0]["reason"] == "done"
    assert "duration_ms" in stops[0]


def test_stop_is_idempotent_no_double_emit(captured):
    # done-stop efterfulgt af finally-fallback-stop → kun ÉT stream_stop-event
    ss.note_start("r1", "s1")
    ss.note_stop("r1", reason="done")
    ss.note_stop("r1", reason="fallback")  # finally — run allerede poppet
    stops = [e for e in captured if e["nerve"] == "stream_stop"]
    assert len(stops) == 1
    assert stops[0]["reason"] == "done"


def test_stop_unknown_run_no_emit(captured):
    ss.note_stop("never-started", reason="fallback")
    assert not [e for e in captured if e["nerve"] == "stream_stop"]


def test_note_event_observes(captured):
    ss.note_event("r1", "zombie_slot", "s1", age_s=12)
    assert any(e["nerve"] == "stream_zombie_slot" and e.get("age_s") == 12 for e in captured)


def test_empty_run_id_is_noop(captured):
    ss.note_start("", "s1")
    assert ss.live_count() == 0
    assert not captured


# ── stall-backstop ─────────────────────────────────────────────────────
def test_sweep_flags_stalled_stream(captured, monkeypatch):
    recorded: list[dict] = []
    import core.runtime.db_central_incidents as inc
    monkeypatch.setattr(inc, "record_central_incident",
                        lambda **kw: recorded.append(kw))
    ss.note_start("zombie", "s9")
    # tving start-tid langt tilbage så den overskrider tærsklen
    with ss._lock:
        ss._live["zombie"]["start"] -= 10_000
    ss.sweep()
    assert any(e["nerve"] == "stream_stall" for e in captured)
    assert recorded and recorded[0]["nerve"] == "stream_stall"
    assert recorded[0]["severity"] == "error"
    # flagges kun ÉN gang
    captured.clear(); recorded.clear()
    ss.sweep()
    assert not [e for e in captured if e["nerve"] == "stream_stall"]


def test_active_stream_not_flagged(captured, monkeypatch):
    import core.runtime.db_central_incidents as inc
    monkeypatch.setattr(inc, "record_central_incident", lambda **kw: None)
    ss.note_start("fresh", "s1")
    ss.sweep()
    assert not [e for e in captured if e["nerve"] == "stream_stall"]


# ── katalog ────────────────────────────────────────────────────────────
def test_catalog_validates_with_stream():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "stream" in cc.clusters()
