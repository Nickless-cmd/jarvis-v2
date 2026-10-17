"""Tests for Stream-cluster-sentinel (stream_sentinel).

Verificerer at SSE-lanens livscyklus emitteres til Centralen (observe), at note_stop er
idempotent (ingen dobbelt-emit ved done→finally-fallback), og at stall-backstoppen flagger
en stream der fik start men aldrig stop — alt self-safe (kaster aldrig).
"""
from __future__ import annotations

import time

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
    # tving både start OG sidste aktivitet langt tilbage: stilhed er det vi måler
    with ss._lock:
        ss._live["zombie"]["start"] -= 10_000
        ss._live["zombie"]["last_activity"] -= 10_000
    ss.sweep()
    assert any(e["nerve"] == "stream_stall" for e in captured)
    assert recorded and recorded[0]["nerve"] == "stream_stall"
    assert recorded[0]["severity"] == "error"
    # flagges kun ÉN gang
    captured.clear(); recorded.clear()
    ss.sweep()
    assert not [e for e in captured if e["nerve"] == "stream_stall"]


def test_stall_incident_skelner_stilhed_fra_alder(captured, monkeypatch):
    """Beskeden skal sige HVOR LÆNGE der har været stille — ikke kun hvor gammelt
    runnet er. Det var netop sammenblandingen der gav falske zombier."""
    recorded: list[dict] = []
    import core.runtime.db_central_incidents as inc
    monkeypatch.setattr(inc, "record_central_incident",
                        lambda **kw: recorded.append(kw))
    ss.note_start("gammel", "s1")
    with ss._lock:
        ss._live["gammel"]["start"] -= 1000     # åbnet for ~16 min siden
        ss._live["gammel"]["last_activity"] -= 400  # stille i ~6,5 min
    ss.sweep()
    stall = next(e for e in captured if e["nerve"] == "stream_stall")
    assert stall["silent_s"] == pytest.approx(400, abs=5)
    assert stall["age_s"] == pytest.approx(1000, abs=5)
    assert "livstegn" in recorded[0]["message"]


def test_levende_run_midt_i_provider_ventetid_flagges_ikke(captured, monkeypatch):
    """Kernen i fixet (17/10-2026): alder er ikke det samme som død.

    Incident 14176: et run var åbnet for over 300s, men gav livstegn hele tiden —
    det retryede tre gange hos provideren. Sentinel målte fra ``message_start`` og
    erklærede det zombie 1m43s før det afsluttede RENT med `run-stream terminal`.
    """
    recorded: list[dict] = []
    import core.runtime.db_central_incidents as inc
    monkeypatch.setattr(inc, "record_central_incident",
                        lambda **kw: recorded.append(kw))
    ss.note_start("langtur", "s1")
    with ss._lock:
        ss._live["langtur"]["start"] -= 600          # åbnet for 10 minutter siden
        ss._live["langtur"]["last_activity"] = time.monotonic()  # men lever nu
    ss.sweep()
    assert not [e for e in captured if e["nerve"] == "stream_stall"]
    assert not recorded


def test_loggens_friske_frame_holder_runnet_i_live(captured, monkeypatch):
    """Aktiviteten hentes fra run_event_log, som ser ALLE frames — også pings.

    Sentinel'ens eget spor opdateres kun ved start og edge-cases, så et run der
    pinger hvert 5. sekund ville ellers se stille ud fra sentinel'ens side. Det er
    præcis et provider-ventende run: ingen indholds-frames, men masser af pings.
    """
    from core.services import run_event_log as rel
    recorded: list[dict] = []
    import core.runtime.db_central_incidents as inc
    monkeypatch.setattr(inc, "record_central_incident",
                        lambda **kw: recorded.append(kw))
    rel.create("pinger", "s1")
    try:
        ss.note_start("pinger", "s1")
        with ss._lock:
            ss._live["pinger"]["start"] -= 600
            ss._live["pinger"]["last_activity"] -= 600  # sentinel har intet set i 10 min
        ss.sweep()
        assert not [e for e in captured if e["nerve"] == "stream_stall"]
        assert not recorded
    finally:
        with rel._lock:
            rel._RUNS.pop("pinger", None)


def test_zombie_fanges_stadig_naar_opslaget_gaar_doedt(captured, monkeypatch):
    """Et virkelig dødt run holder OGSÅ op med at pinge — så loggens aktivitet
    stopper med at bevæge sig, og tærsklen nås. Fixet må ikke gøre sentinel blind."""
    from core.services import run_event_log as rel
    recorded: list[dict] = []
    import core.runtime.db_central_incidents as inc
    monkeypatch.setattr(inc, "record_central_incident",
                        lambda **kw: recorded.append(kw))
    rel.create("doedt", "s1")
    try:
        ss.note_start("doedt", "s1")
        with ss._lock:
            ss._live["doedt"]["start"] -= 10_000
            ss._live["doedt"]["last_activity"] -= 10_000
        with rel._lock:
            rel._RUNS["doedt"]["last_append_at"] -= 10_000
        ss.sweep()
        assert [e for e in captured if e["nerve"] == "stream_stall"]
        assert recorded
    finally:
        with rel._lock:
            rel._RUNS.pop("doedt", None)


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
