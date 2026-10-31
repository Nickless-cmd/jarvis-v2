"""De tre tavse fald i `connections` — målt 31/10-2026.

Filen havde INGEN logger: alle tre fald var tavse per konstruktion. De sidder
alle i Centralens synlighedslag, hvor "kunne ikke registrere" og "intet at
registrere" er den samme værdi — og derfor den samme konklusion.

Hver vagt beviser TO ting: at fejlen efterlader et spor, OG at retningen er
uændret. Self-safe (kaster aldrig) er en politik, ikke en fejl.
"""
from __future__ import annotations

import logging

from core.services import connections as C


def _kaster(exc: Exception):
    def _f(*a, **k):
        raise exc
    return _f


# ── 1. _observe: Centralen kunne ikke registrere forbindelsen ──
def test_observe_fejl_logger_og_kaster_ikke(monkeypatch, caplog):
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", _kaster(RuntimeError("central nede")))
    with caplog.at_level(logging.WARNING):
        C.note_presence("u1", "desk-1", "linux")  # må ikke kaste
    assert "central nede" in caplog.text
    assert "device_presence" in caplog.text


# ── 2. session_activity: tool_observer kunne ikke læses ──
def test_session_activity_tool_observer_fejl_logger(monkeypatch, caplog):
    import core.services.tool_observer as to
    monkeypatch.setattr(to, "recent_tool_calls", _kaster(RuntimeError("observer nede")))
    with caplog.at_level(logging.WARNING):
        out = C.session_activity("s1")
    # retningen: strukturen er intakt, så kalderen ikke kollapser
    assert out["session_id"] == "s1" and out["failed_tools"] == []
    assert "observer nede" in caplog.text


# ── 3. session_activity: central_trace kunne ikke læses ──
def test_session_activity_trace_fejl_logger(monkeypatch, caplog):
    import core.services.central_trace as ct
    monkeypatch.setattr(ct, "sink", _kaster(RuntimeError("trace nede")))
    with caplog.at_level(logging.WARNING):
        out = C.session_activity("s2")
    assert out["unauthorized"] == [] and out["connection_errors"] == []
    assert "trace nede" in caplog.text


# ── 4. støj-vagt: normal drift må ikke skrive én eneste advarsel ──
def test_normal_drift_stoejer_ikke(caplog):
    with caplog.at_level(logging.WARNING):
        C.note_presence("u1", "desk-1", "linux")
        C.note_ws("connected", "host:1234")
        C.session_activity("s3")
        C.active_summary()
    advarsler = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert not advarsler, f"normal drift støjede: {[r.message for r in advarsler]}"


# ── 5. RETNINGEN: en ægte uautoriseret adgang registreres stadig ──
def test_uauthoriseret_registreres_stadig(monkeypatch):
    """Rapporteringen må ikke gøre forbindelses-laget tandløst."""
    kaldt = []
    import core.runtime.db_central_incidents as inc
    monkeypatch.setattr(inc, "record_central_incident",
                        lambda **kw: kaldt.append(kw))
    C.note_unauthorized("u1", "s1", "exec_command", "identity_spoof")
    assert kaldt and kaldt[0]["severity"] == "severe"
