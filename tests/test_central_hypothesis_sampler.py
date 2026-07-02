"""Tests for core/services/central_hypothesis_sampler.py — Lag 3 loop-lukning (test mod virkelighed)."""
from __future__ import annotations

import pytest

from core.services import central_hypothesis_sampler as smp
from core.services import central_hypothesis_generator as gen


def _bind_events(monkeypatch, seq):
    """seq: list of (id, kind, iso_ts) — bindes som event_bus.recent()."""
    import core.eventbus.bus as bus

    class _Bus:
        def recent(self, limit=3000):
            return [{"id": i, "kind": k, "created_at": t} for i, k, t in seq][:limit]
    monkeypatch.setattr(bus, "event_bus", _Bus())


def _ts(sec):
    # simple monotone timestamps
    return f"2026-07-02T00:00:{sec:02d}+00:00"


def test_supports_when_y_follows_x(monkeypatch):
    # X altid tæt fulgt af Y → betinget rate høj vs baseline → supports
    seq = []
    eid = 1
    for base in range(0, 60, 2):
        seq.append((eid, "memory.recall_fail", _ts(base))); eid += 1
        seq.append((eid, "somatic.stress", _ts(base + 1))); eid += 1
    _bind_events(monkeypatch, seq)
    res = smp.test_causal_hypothesis("memory", "somatic")
    assert res is not None and res["supports"] is True and res["falsifies"] is False


def test_falsifies_when_no_lift(monkeypatch):
    # Y forekommer aldrig efter X (spredt/uafhængigt) → ingen lift → falsifies
    seq = []
    eid = 1
    for base in range(0, 60, 2):
        seq.append((eid, "memory.recall_fail", _ts(base))); eid += 1
        seq.append((eid, "tool.completed", _ts(base + 1))); eid += 1
    _bind_events(monkeypatch, seq)
    res = smp.test_causal_hypothesis("memory", "somatic")   # somatic forekommer slet ikke
    assert res is not None and res["supports"] is False and res["falsifies"] is True


def test_too_little_data_returns_none(monkeypatch):
    _bind_events(monkeypatch, [(1, "a.x", _ts(0)), (2, "b.y", _ts(1))])
    assert smp.test_causal_hypothesis("a", "b") is None


def test_sampler_tick_records_grounded_samples(isolated_runtime, monkeypatch):
    # registrér en causal-hypotese memory->somatic
    gen.ensure_schema()
    gen.register_governed_hypothesis(gen.formulate_correlation_hypothesis(
        {"parent_family": "memory", "child_family": "somatic", "count": 4, "cursor": 10}))
    # event-strøm hvor somatic altid følger memory → supports
    seq = []
    eid = 1
    for base in range(0, 60, 2):
        seq.append((eid, "memory.recall_fail", _ts(base))); eid += 1
        seq.append((eid, "somatic.stress", _ts(base + 1))); eid += 1
    _bind_events(monkeypatch, seq)
    res = smp.run_hypothesis_sampler_tick()
    assert res["status"] == "ok" and res["tested"] == 1 and res["supported"] == 1
    # hypotesen har nu 1 grounded sample
    active = gen.list_active_hypotheses()
    assert active and active[0]["grounded_samples"] == 1


def test_five_supporting_samples_resolve(isolated_runtime, monkeypatch):
    gen.ensure_schema()
    gen.register_governed_hypothesis(gen.formulate_correlation_hypothesis(
        {"parent_family": "memory", "child_family": "somatic", "count": 4, "cursor": 10}))
    seq = []
    eid = 1
    for base in range(0, 60, 2):
        seq.append((eid, "memory.recall_fail", _ts(base))); eid += 1
        seq.append((eid, "somatic.stress", _ts(base + 1))); eid += 1
    _bind_events(monkeypatch, seq)
    # 5 ticks (hver = ét grounded sample) → sample_size=5 nået → resolve supported
    for _ in range(5):
        smp.run_hypothesis_sampler_tick()
    from core.runtime.db import connect
    with connect() as c:
        row = c.execute("SELECT status, outcome FROM central_hypotheses").fetchone()
    assert row["status"] == "resolved" and row["outcome"] == "supported"
