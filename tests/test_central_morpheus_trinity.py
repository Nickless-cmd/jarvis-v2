from __future__ import annotations

import core.services.central_morpheus as m
import core.services.central_trinity as t


# ── Morpheus ──────────────────────────────────────────────────────────────
def test_morpheus_aggregates_sources(monkeypatch):
    monkeypatch.setattr(m, "_brewing", lambda: [{"source": "emergence", "title": "Drift",
                                                 "distance_to_ready": 0.1, "trajectory": "strengthening",
                                                 "felt": "x"}])
    monkeypatch.setattr(m, "_oracle_approaching", lambda: [])
    monkeypatch.setattr(m, "_near_mature_hypotheses", lambda: [])
    monkeypatch.setattr(m, "_gates_near_key", lambda: [])
    monkeypatch.setattr(m, "_skill_formation", lambda: [{"source": "skill_formation", "title": "grep",
                                                        "distance_to_ready": None, "trajectory": "forming",
                                                        "felt": "y"}])
    pots = m.scan_potentials()
    assert {p["source"] for p in pots} == {"emergence", "skill_formation"}
    surf = m.build_morpheus_surface()
    assert surf["active"] is True and surf["summary"]["count"] == 2


def test_morpheus_empty_is_calm(monkeypatch):
    for fn in ("_brewing", "_oracle_approaching", "_near_mature_hypotheses",
               "_gates_near_key", "_skill_formation"):
        monkeypatch.setattr(m, fn, lambda: [])
    surf = m.build_morpheus_surface()
    assert surf["active"] is False
    assert "holder øje" in surf["summary"]["felt"]


def test_morpheus_self_safe_on_source_error(monkeypatch):
    def boom():
        raise RuntimeError("db down")
    monkeypatch.setattr(m, "_brewing", boom)
    monkeypatch.setattr(m, "_oracle_approaching", lambda: [])
    monkeypatch.setattr(m, "_near_mature_hypotheses", lambda: [])
    monkeypatch.setattr(m, "_gates_near_key", lambda: [])
    monkeypatch.setattr(m, "_skill_formation", lambda: [])
    assert m.scan_potentials() == []  # én kilde-fejl dræber ikke resten


# ── Trinity ───────────────────────────────────────────────────────────────
def test_trinity_default_shadow():
    # Uden eksplicit flip → shadow (default OFF, modsat gate-default)
    assert t._is_enforced() is False


def test_trinity_threshold_is_conservative():
    assert t._KEY_THRESHOLD == 150  # > Keymakers 100


def test_trinity_shadow_never_earns(monkeypatch):
    # I shadow: selv en streak ≥ threshold optjener INGEN nøgle (earned=0)
    monkeypatch.setattr(t, "assess_affirmations",
                        lambda: [{"pattern_key": "hyp:x", "title": "T", "convergence": 0.9,
                                  "track_record": {}, "progress_to_key": "150/150", "felt": "f"}])
    monkeypatch.setattr(t, "_bump", lambda k, title, now: 150)
    monkeypatch.setattr(t, "_is_enforced", lambda: False)
    r = t.record_trinity()
    assert r["would_earn"] == 1 and r["earned"] == 0  # ville optjene, men shadow → intet


def test_trinity_enforce_respects_merovingian_veto(monkeypatch):
    monkeypatch.setattr(t, "assess_affirmations",
                        lambda: [{"pattern_key": "hyp:x", "title": "T", "convergence": 0.9,
                                  "track_record": {}, "progress_to_key": "150/150", "felt": "f"}])
    monkeypatch.setattr(t, "_bump", lambda k, title, now: 150)
    monkeypatch.setattr(t, "_is_enforced", lambda: True)
    monkeypatch.setattr(t, "_merovingian_blocks", lambda k: True)  # veto
    r = t.record_trinity()
    assert r["would_earn"] == 1 and r["earned"] == 0  # Merovingian blokerede optjeningen
