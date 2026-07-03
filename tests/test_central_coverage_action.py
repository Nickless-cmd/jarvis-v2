"""Tests for core/services/central_coverage_action.py — §11 #5 handlings-udløser (shadow-først).

Hermetisk: monkeypatcher connectivity-kortet + event-bus + KV-flag + hypotese-registrering, så INTET
rører filsystem, DB eller eventbus for alvor. Verificerer: flag default off = 0 arbejde; shadow =
beregn men opret intet; on = registrér via den EKSISTERENDE governed-hypotese-mekanisme; self-safe.
"""
from __future__ import annotations

import pytest

from core.services import central_coverage as cov
from core.services import central_coverage_action as act
from core.services import central_timeseries


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    cov._reset_matrix_cache_for_tests()
    yield
    central_timeseries._reset_for_tests()
    cov._reset_matrix_cache_for_tests()


# ── Fælles fikstur: et lille syntetisk connectivity-kort med lav dækning + en dark-family ──
def _bind_matrix(monkeypatch, *, total=100, connected=30, dark=40, llm=5,
                 dark_family="somefamily", dark_files=4):
    matrix = {
        "total": total,
        "counts": {"KOBLET": connected, "FRAKOBLET+DARK": dark,
                   "FRAKOBLET+LLM": llm, "FRAKOBLET-STILLE": total - connected - dark - llm},
        "rows": [
            {"quadrant": "FRAKOBLET+DARK", "dark_families": [dark_family]}
            for _ in range(dark_files)
        ],
    }
    monkeypatch.setattr(cov, "_matrix_cache", matrix)


def _bind_events(monkeypatch, events):
    import core.eventbus.bus as bus

    class _Bus:
        def recent(self, limit=2000):
            return [{"kind": k} for k in events][:limit]
    monkeypatch.setattr(bus, "event_bus", _Bus())


def _bind_mode(monkeypatch, mode):
    monkeypatch.setattr(act, "get_mode", lambda: mode)


# ── Del 1: strukturel dækning gøres runtime-kendt ─────────────────────────────────────
def test_structural_coverage_scalars(monkeypatch):
    _bind_matrix(monkeypatch, total=100, connected=30, dark=40, llm=5)
    sc = cov.structural_coverage()
    assert sc["available"] is True
    assert sc["total"] == 100 and sc["connected"] == 30 and sc["dark"] == 40
    assert sc["structural_ratio"] == 0.3
    assert sc["dark_ratio"] == 0.4
    assert sc["top_dark_families"][0]["family"] == "somefamily"


def test_structural_coverage_missing_matrix(monkeypatch):
    monkeypatch.setattr(cov, "load_connectivity_matrix", lambda: None)
    assert cov.structural_coverage() == {"available": False}


def test_record_coverage_observes_structural(monkeypatch):
    _bind_matrix(monkeypatch)
    _bind_events(monkeypatch, ["impulse.tick"])
    cov.record_coverage(window=50)
    # structural_coverage observeret egress-frit på cluster=system/nerve=structural_coverage
    assert central_timeseries.recent("system", "structural_coverage")


# ── Del 2: handlings-udløser, flag-gated ──────────────────────────────────────────────
def test_mode_off_does_nothing(monkeypatch):
    _bind_matrix(monkeypatch)
    _bind_events(monkeypatch, [])
    _bind_mode(monkeypatch, "off")
    # skulle den kalde compute → fejl; men off returnerer FØR beregning
    monkeypatch.setattr(act, "compute_candidates", lambda **k: (_ for _ in ()).throw(AssertionError("off må ikke beregne")))
    res = act.run_coverage_action_tick()
    assert res["mode"] == "off"
    assert res["candidates"] == 0 and res["registered"] == 0


def test_low_coverage_yields_structural_candidate(monkeypatch):
    # dækning 0.30 < 0.35 → strukturel-blindhed-hypotese formuleres
    _bind_matrix(monkeypatch, total=100, connected=30, dark=40)
    _bind_events(monkeypatch, [])
    cands = act.compute_candidates(window=100)
    assert any(c["source"] == "structural_coverage" for c in cands)


def test_hot_dark_family_yields_candidate(monkeypatch):
    # høj dækning (ingen strukturel-hypotese) men dark-family bærer meget live-signal
    _bind_matrix(monkeypatch, total=100, connected=80, dark=10, dark_family="hotfam")
    _bind_events(monkeypatch, ["hotfam.a"] * 7 + ["known.b"])
    cands = act.compute_candidates(window=100)
    srcs = [c["source"] for c in cands]
    assert "dark_family_signal" in srcs
    assert "structural_coverage" not in srcs  # dækning 0.80 er ikke lav


def test_shadow_computes_but_creates_nothing(monkeypatch):
    _bind_matrix(monkeypatch, total=100, connected=30, dark=40)
    _bind_events(monkeypatch, [])
    _bind_mode(monkeypatch, "shadow")
    # hvis on-stien blev kaldt ville register_governed_hypothesis fyre → gør den til en fælde
    import core.services.central_hypothesis_generator as hg
    monkeypatch.setattr(hg, "register_governed_hypothesis",
                        lambda hyp: (_ for _ in ()).throw(AssertionError("shadow må IKKE oprette")))
    res = act.run_coverage_action_tick()
    assert res["mode"] == "shadow"
    assert res["candidates"] >= 1
    assert res["registered"] == 0
    assert res["would_register"] == res["candidates"]


def test_on_registers_via_governed_mechanism(monkeypatch):
    _bind_matrix(monkeypatch, total=100, connected=30, dark=40)
    _bind_events(monkeypatch, [])
    _bind_mode(monkeypatch, "on")
    seen = []
    import core.services.central_hypothesis_generator as hg

    def _fake_register(hyp):
        seen.append(hyp)
        # verificér at kandidaten ER fuldt pre-registreret (governance-invarianten)
        for f in ("statement", "prediction", "null_hypothesis", "success_criterion",
                  "sample_size", "ttl_seconds", "provenance"):
            assert f in hyp, f"kandidat mangler {f} → ville ikke overleve validate_preregistration"
        return {"status": "registered", "hyp_id": "clh-fake"}
    monkeypatch.setattr(hg, "register_governed_hypothesis", _fake_register)
    res = act.run_coverage_action_tick()
    assert res["mode"] == "on"
    assert res["registered"] == len(seen) >= 1


def test_candidates_are_governance_valid(monkeypatch):
    """Kandidaterne skal overleve DEN RIGTIGE validate_preregistration (ægte governance, ikke mock)."""
    from core.services import central_hypothesis_governance as gov
    _bind_matrix(monkeypatch, total=100, connected=30, dark=40, dark_family="hotfam")
    _bind_events(monkeypatch, ["hotfam.a"] * 7)
    for c in act.compute_candidates(window=100):
        ok, missing = gov.validate_preregistration(c)
        assert ok, f"kandidat ikke pre-registreret: mangler {missing}"


def test_tick_self_safe_on_broken_matrix(monkeypatch):
    monkeypatch.setattr(cov, "load_connectivity_matrix",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    _bind_mode(monkeypatch, "on")
    res = act.run_coverage_action_tick()  # må ikke kaste
    assert res["status"] == "ok"
    assert res["candidates"] == 0


def test_surface_is_read_only(monkeypatch):
    _bind_matrix(monkeypatch, total=100, connected=30, dark=40)
    _bind_events(monkeypatch, [])
    _bind_mode(monkeypatch, "shadow")
    surf = act.build_central_coverage_action_surface()
    assert surf["active"] is True and surf["mode"] == "shadow"
    assert surf["candidate_count"] >= 1
    assert isinstance(surf["candidates"], list)
