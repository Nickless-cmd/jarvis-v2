"""Tests for core/services/central_timeseries.py — per-nerve tidsserie (M0, §24.6)."""
from __future__ import annotations

import pytest

from core.services import central_timeseries as ts


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    # Isolér durabiliteten: ingen test må røre den rigtige runtime-DB (kv i hukommelsen)
    # og baggrunds-persist-tråden slås fra (ellers lækker nerver på tværs af tests).
    _kv: dict = {}
    monkeypatch.setattr(ts, "_kv_get", lambda k, d: _kv.get(k, d))
    monkeypatch.setattr(ts, "_kv_set", lambda k, v: _kv.__setitem__(k, v))
    monkeypatch.setattr(ts, "_maybe_persist", lambda: None)
    ts._reset_for_tests()
    yield
    ts._reset_for_tests()


def test_record_and_recent():
    ts.record("loop", "lifecycle", 1.0, meta={"kind": "runtime.x"})
    ts.record("loop", "lifecycle", 2.0)
    got = ts.recent("loop", "lifecycle")
    assert [s.value for s in got] == [1.0, 2.0]
    assert got[0].meta.get("kind") == "runtime.x"
    assert got[-1].ts  # timestamp populated


def test_per_nerve_isolation_no_cross_eviction():
    # KERNEN i §24.6: ét støjende nerve må IKKE evict'e et andet nerves historik.
    for i in range(1000):
        ts.record("tools", "event", float(i))  # støjende nerve, langt over maxlen
    ts.record("memory", "recall", 42.0)  # stille nerve, ét enkelt sample
    quiet = ts.recent("memory", "recall")
    assert len(quiet) == 1
    assert quiet[0].value == 42.0  # overlevede nabo-støjen


def test_maxlen_cap_per_nerve():
    for i in range(ts._PER_NERVE_MAX + 50):
        ts.record("c", "n", float(i))
    got = ts.recent("c", "n", limit=10_000)
    assert len(got) == ts._PER_NERVE_MAX  # cappet
    assert got[-1].value == float(ts._PER_NERVE_MAX + 49)  # nyeste bevaret


def test_recent_limit():
    for i in range(20):
        ts.record("c", "n", float(i))
    assert len(ts.recent("c", "n", limit=5)) == 5


def test_never_raises_on_bad_input():
    ts.record("", "", None)  # tom nøgle → no-op
    ts.record("c", "n", "not-a-number")  # type: ignore[arg-type]
    assert ts.recent("missing", "nerve") == []


def test_stats_and_nerves():
    ts.record("a", "1", 1.0)
    ts.record("b", "2", 1.0)
    st = ts.stats()
    assert st["nerve_count"] == 2
    assert st["total_samples"] == 2
    assert set(ts.nerves()) == {("a", "1"), ("b", "2")}


def test_snapshot_compact_per_nerve():
    for v in (1.0, 2.0, 3.0):
        ts.record("infra", "reach_pve", v, meta={"up": True})
    ts.record("sensory", "archive", 5.0)
    snap = ts.snapshot(recent=2)
    assert set(snap) == {"infra:reach_pve", "sensory:archive"}
    pve = snap["infra:reach_pve"]
    assert pve["count"] == 3 and pve["latest"] == 3.0
    assert pve["recent"] == [2.0, 3.0]  # seneste 2
    assert pve["meta"] == {"up": True}


def test_snapshot_empty_and_safe():
    assert ts.snapshot() == {}  # ingen data → tom, ingen crash


# ── DURABILITET: nervesystemet overlever genstart (Bjørn 3. jul) ──────────
def test_durable_roundtrip_survives_restart(monkeypatch):
    kv: dict = {}
    monkeypatch.setattr(ts, "_kv_get", lambda k, d: kv.get(k, d))
    monkeypatch.setattr(ts, "_kv_set", lambda k, v: kv.__setitem__(k, v))
    monkeypatch.setattr(ts, "_maybe_persist", lambda: None)  # kun eksplicit persist (undgå tråd-race)
    ts.record("cognition", "inner_salience", 1.0, meta={"would_reuse": True, "mode": "shadow"})
    ts.record("cognition", "inner_salience", 0.0, meta={"would_reuse": False})
    assert ts.persist_snapshot()["status"] == "ok"
    assert _SEP_key(kv)  # blob skrevet til durabel kv
    # simulér GENSTART: frisk proces → in-memory tomt, _restored=False, men kv (DB) består.
    ts._reset_for_tests()
    ts._maybe_restore()  # frisk proces genindlæser durabelt snapshot (hot-hook gated under pytest)
    got = ts.recent("cognition", "inner_salience")
    assert [s.value for s in got] == [1.0, 0.0]         # værdier overlevede genstart
    assert got[0].meta.get("would_reuse") is True        # meta overlevede
    assert got[1].meta.get("would_reuse") is False


def _SEP_key(kv):
    return any(ts._SEP in k for blob in kv.values() if isinstance(blob, dict) for k in blob)


def test_restore_runs_once(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(ts, "_load_durable", lambda: calls.__setitem__("n", calls["n"] + 1))
    ts._restored = False
    ts._maybe_restore()
    ts._maybe_restore()
    assert calls["n"] == 1  # kun første adgang loader


def test_persist_self_safe_on_kv_failure(monkeypatch):
    monkeypatch.setattr(ts, "_kv_set", lambda k, v: (_ for _ in ()).throw(RuntimeError("boom")))
    ts.record("x", "y", 1.0)
    assert ts.persist_snapshot()["status"] == "error"  # fanget, kaster ikke
