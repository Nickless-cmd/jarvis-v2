"""Tests for core/services/central_private_observe.py — Fase 2 inner-life liveness (§24.4).

Den vigtigste test her er NO-EGRESS: inner-life må ALDRIG nå eventbus (→ Discord/eksternt).
"""
from __future__ import annotations

import pytest

from core.services import central_private_observe as cpo
from core.services import central_timeseries


class _FakeSink:
    def __init__(self):
        self.records = []

    def record(self, rec):
        self.records.append(rec)


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


@pytest.fixture
def sink(monkeypatch):
    s = _FakeSink()
    monkeypatch.setattr(cpo.central_trace, "sink", lambda: s)
    return s


# ── NO-EGRESS (kernen i §24.4) ──

def test_no_egress_eventbus_never_touched(sink, monkeypatch):
    calls = []
    import core.eventbus.bus as bus
    monkeypatch.setattr(bus.event_bus, "publish", lambda *a, **k: calls.append((a, k)))
    cpo.observe_liveness("inner_voice_daemon", ok=True, status="ran", produced=2)
    # gik til den lokale sink...
    assert len(sink.records) == 1
    # ...men ALDRIG til eventbus (ingen _emit/publish → ingen egress)
    assert calls == []


def test_records_to_inner_cluster(sink):
    cpo.observe_liveness("dream_articulation", ok=True, status="ran", produced=1, empty=False)
    assert len(sink.records) == 1
    r = sink.records[0]
    assert r.cluster == "inner"
    assert r.nerve == "dream_articulation"
    assert r.kind == "observe"


def test_payload_only_aggregated_no_content(sink):
    cpo.observe_liveness("witness_daemon", ok=True, status="ran", produced=3, empty=False)
    payload = sink.records[0].payload
    assert set(payload) <= {"ok", "status", "produced", "empty"}
    # ingen tekst-værdier ud over den korte status-etiket
    assert payload["ok"] is True
    assert payload["produced"] == 3


# ── liveness-udtræk ──

def test_liveness_from_result_scalars_only():
    ok, produced, empty = cpo._liveness_from_result("ran", {"produced": 5, "text": "hemmeligt indhold"})
    assert ok is True
    assert produced == 5
    assert empty is False
    # "text" (indhold) blev IKKE udtrukket — kun skalar-tælling


def test_liveness_from_result_empty_status():
    ok, produced, empty = cpo._liveness_from_result("ran", {"status": "skipped"})
    assert ok is True
    assert empty is True


def test_liveness_error_status():
    ok, produced, empty = cpo._liveness_from_result("error", None)
    assert ok is False


# ── cadence-hook: kun inner-life ──

def test_cadence_hook_routes_inner_egressfree_operational_normal(sink, monkeypatch):
    # inner-life producer → EGRESS-FRI (direkte til lokal sink, cluster=inner)
    cpo.observe_cadence_liveness("self_critique_runtime", "ran", {"produced": 1})
    assert len(sink.records) == 1
    assert sink.records[0].cluster == "inner"
    # operationel producer → NORMAL observe (cluster=system), IKKE via den egress-frie sink
    observed = []
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central",
                        lambda: type("C", (), {"observe": lambda s, e: observed.append(dict(e))})())
    cpo.observe_cadence_liveness("db_health_scan", "ran", {})
    assert len(sink.records) == 1  # egress-fri sink uændret
    assert observed and observed[0]["cluster"] == "system" and observed[0]["nerve"] == "db_health_scan"


def test_timeseries_recorded_under_inner(sink):
    cpo.observe_cadence_liveness("inner_voice_daemon", "ran", {"produced": 0})
    assert len(central_timeseries.recent("inner", "inner_voice_daemon")) == 1


def test_never_raises(sink, monkeypatch):
    monkeypatch.setattr(cpo.central_trace, "sink",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    cpo.observe_liveness("x", ok=True)  # må ikke kaste
    cpo.observe_cadence_liveness("inner_voice_daemon", "ran", {})  # må ikke kaste


def test_inner_life_set_excludes_infra():
    # sanity: rene infra-daemons må IKKE være i inner-life-sættet (de er ikke private)
    for infra in ("eventbus_central_bridge", "central_self_observe", "db_health_scan",
                  "provider_health_check", "config_drift_check", "shared_cache_cleanup"):
        assert infra not in cpo.INNER_LIFE_PRODUCERS


def test_observe_hub_egress_free(isolated_runtime):
    # HUB-observe skriver til trace, ALDRIG central().observe (egress-fri)
    from core.services import central_private_observe as cpo, central_trace
    cpo.observe_hub("signal_surface_router", meta={"surfaces": 35, "errors": 0})
    recs = [r for r in central_trace.sink().recent(limit=30) if r.nerve == "signal_surface_router"]
    assert recs and recs[-1].payload.get("surfaces") == 35
