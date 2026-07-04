"""Tests for central_oneiric_sampler — grounding/falsifying oneiric_loop hypoteser.

Kerne: (1) _evaluate_hypothesis dømmer korrekt pr. retning + edge, (2) tynd data → INTET
(hypotesen rider mod TTL, ingen falsk resolution), (3) run-tick grounder gennem §8 med
verificerbar source+ground_ref, (4) self-safe på ødelagte afhængigheder.
"""
from __future__ import annotations

from types import SimpleNamespace

import core.services.central_oneiric_sampler as s


# ── _evaluate_hypothesis: retning + edge ─────────────────────────────────────────────

def test_supports_when_active_beats_control_down():
    # 'down': aktiv-rate LAVERE end kontrol (0.20 < 0.80) → drømmen slog → supports
    arms = {"active": {"rate": 0.20, "days": 3}, "control": {"rate": 0.80, "days": 3}}
    res = s._evaluate_hypothesis({"predicted_direction": "down"}, arms)
    assert res["supports"] is True and res["falsifies"] is False


def test_falsifies_on_opposite_direction():
    # 'down' forudsagt, men aktiv HØJERE end kontrol → falsificeret
    arms = {"active": {"rate": 0.80, "days": 3}, "control": {"rate": 0.20, "days": 3}}
    res = s._evaluate_hypothesis({"predicted_direction": "down"}, arms)
    assert res["falsifies"] is True and res["supports"] is False


def test_up_direction_supports_when_active_higher():
    arms = {"active": {"rate": 0.70, "days": 2}, "control": {"rate": 0.40, "days": 2}}
    res = s._evaluate_hypothesis({"predicted_direction": "up"}, arms)
    assert res["supports"] is True


def test_none_when_edge_too_small():
    # forskel under _MIN_RATE_EDGE → hverken supports eller falsifies (men stadig et sample)
    arms = {"active": {"rate": 0.50, "days": 3}, "control": {"rate": 0.52, "days": 3}}
    res = s._evaluate_hypothesis({"predicted_direction": "down"}, arms)
    assert res is not None and res["supports"] is False and res["falsifies"] is False


def test_none_when_arm_missing():
    arms = {"active": {"rate": 0.5, "days": 3}, "control": {"rate": None, "days": 0}}
    assert s._evaluate_hypothesis({"predicted_direction": "down"}, arms) is None


def test_none_on_thin_days():
    # begge arme har rate men for FÅ dage → ingen falsk resolution
    arms = {"active": {"rate": 0.2, "days": 1}, "control": {"rate": 0.8, "days": 1}}
    assert s._evaluate_hypothesis({"predicted_direction": "down"}, arms) is None


def test_none_on_bad_direction():
    arms = {"active": {"rate": 0.2, "days": 3}, "control": {"rate": 0.8, "days": 3}}
    assert s._evaluate_hypothesis({"predicted_direction": "sideways"}, arms) is None


# ── compute_arm_rates: partitionering aktiv/kontrol ─────────────────────────────────

def test_compute_arm_rates_partitions_by_control_day(monkeypatch):
    num = {"2026-06-01": 2, "2026-06-02": 8}
    den = {"2026-06-01": 10, "2026-06-02": 10}
    monkeypatch.setattr(s, "_daily_counts",
                        lambda cluster, nerve, **_: num if nerve == "no_progress_finalize" else den)
    import core.services.central_oneiric_loop as loop
    monkeypatch.setattr(loop, "is_control_day", lambda day, **_: day == "2026-06-02")
    arms = s.compute_arm_rates()
    assert arms["active"]["rate"] == 0.2 and arms["active"]["days"] == 1
    assert arms["control"]["rate"] == 0.8 and arms["control"]["days"] == 1


def test_compute_arm_rates_skips_low_run_days(monkeypatch):
    # dag med < _MIN_DAILY_RUNS runs ignoreres (støj)
    monkeypatch.setattr(s, "_daily_counts",
                        lambda cluster, nerve, **_: ({"2026-06-01": 1} if nerve == "no_progress_finalize"
                                                     else {"2026-06-01": 2}))
    import core.services.central_oneiric_loop as loop
    monkeypatch.setattr(loop, "is_control_day", lambda day, **_: False)
    arms = s.compute_arm_rates()
    assert arms["active"]["rate"] is None and arms["active"]["days"] == 0


# ── run tick: grounder gennem §8 ────────────────────────────────────────────────────

def _patch_one_active_hyp(monkeypatch, prov: dict):
    import core.runtime.db as db

    class _Conn:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, *a, **k):
            return SimpleNamespace(fetchall=lambda: [
                {"hyp_id": "hyp_oneiric_1",
                 "provenance_json": __import__("json").dumps(prov)}])
    monkeypatch.setattr(db, "connect", lambda: _Conn())


def test_run_tick_grounds_support(monkeypatch):
    import core.services.central_hypothesis_generator as gen
    monkeypatch.setattr(gen, "ensure_schema", lambda: None)
    monkeypatch.setattr(s, "compute_arm_rates",
                        lambda **_: {"active": {"rate": 0.2, "days": 3},
                                     "control": {"rate": 0.8, "days": 3}, "per_day": {}})
    _patch_one_active_hyp(monkeypatch, {"predicted_direction": "down"})
    rec = {}
    monkeypatch.setattr(gen, "record_governed_sample",
                        lambda hyp_id, **kw: rec.update({"hyp_id": hyp_id, **kw}) or {"status": "ok"})
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda *a, **k: True)
    res = s.run_oneiric_sampler_tick()
    assert res["status"] == "ok" and res["grounded"] == 1 and res["supported"] == 1
    # grounded gennem tilladt verdens-kilde + ikke-tom ground_ref
    assert rec["source"] == "world_consequence" and rec["ground_ref"]
    assert rec["supports"] is True


def test_run_tick_does_nothing_on_thin_data(monkeypatch):
    import core.services.central_hypothesis_generator as gen
    monkeypatch.setattr(gen, "ensure_schema", lambda: None)
    monkeypatch.setattr(s, "compute_arm_rates",
                        lambda **_: {"active": {"rate": None, "days": 0},
                                     "control": {"rate": None, "days": 0}, "per_day": {}})
    _patch_one_active_hyp(monkeypatch, {"predicted_direction": "down"})
    calls = {"n": 0}
    monkeypatch.setattr(gen, "record_governed_sample",
                        lambda *a, **k: calls.__setitem__("n", calls["n"] + 1))
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda *a, **k: True)
    res = s.run_oneiric_sampler_tick()
    assert res["grounded"] == 0 and calls["n"] == 0  # rider mod TTL, ingen falsk resolution


def test_run_tick_self_safe_on_broken_generator(monkeypatch):
    import core.services.central_hypothesis_generator as gen
    def boom():
        raise RuntimeError("db down")
    monkeypatch.setattr(gen, "ensure_schema", boom)
    res = s.run_oneiric_sampler_tick()
    assert res["status"] == "error"  # kaster aldrig
