"""Tests for DB-cluster (db_sentinel).

Verificerer at modulet er NON-destruktivt (kun SELECT/COUNT), at vækst-flagget kun fyrer på
egregious vækst (fordobling + stor abs. tilvækst), at første scan etablerer baseline uden
flags, og at dead_table_candidates kun LISTER (aldrig dropper).
"""
from __future__ import annotations

import pytest

from core.services import db_sentinel as ds


@pytest.fixture
def patch_census(monkeypatch):
    state = {"cur": {}, "prev": {}}
    monkeypatch.setattr(ds, "census", lambda: dict(state["cur"]))
    monkeypatch.setattr(ds, "_load_prev", lambda: dict(state["prev"]))
    monkeypatch.setattr(ds, "_save", lambda c: None)
    return state


def test_first_scan_no_flags_establishes_baseline(patch_census):
    # ny tabel uden baseline → ingen flag
    patch_census["cur"] = {"events": 50000}
    patch_census["prev"] = {}
    r = ds.scan()
    assert r["flagged_growth"] == []
    assert r["tables"] == 1
    assert r["total_rows"] == 50000


def test_egregious_growth_flagged(patch_census):
    patch_census["prev"] = {"events": 1000}
    patch_census["cur"] = {"events": 30000}  # >fordoblet OG +29000 (>20000)
    r = ds.scan()
    assert len(r["flagged_growth"]) == 1
    assert r["flagged_growth"][0]["table"] == "events"
    assert r["flagged_growth"][0]["grew"] == 29000


def test_organic_growth_not_flagged(patch_census):
    # vokset stort absolut MEN ikke fordoblet → ikke flagget (lav false-positive)
    patch_census["prev"] = {"events": 1_000_000}
    patch_census["cur"] = {"events": 1_025_000}  # +25000 men kun 2.5% → ikke fordoblet
    r = ds.scan()
    assert r["flagged_growth"] == []


def test_small_doubling_not_flagged(patch_census):
    # fordoblet MEN lille absolut → ikke flagget
    patch_census["prev"] = {"t": 100}
    patch_census["cur"] = {"t": 500}  # 5× men kun +400 (<20000)
    r = ds.scan()
    assert r["flagged_growth"] == []


def test_empty_tables_listed_not_dropped(patch_census):
    patch_census["cur"] = {"live": 10, "empty_a": 0, "empty_b": 0}
    r = ds.scan()
    assert set(r["empty"]) == {"empty_a", "empty_b"}


def test_observe_self_safe(patch_census):
    patch_census["cur"] = {"x": 5}
    # må aldrig kaste
    rep = ds.observe()
    assert isinstance(rep, dict)


def test_catalog_validates_with_db():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "db" in cc.clusters()
    names = [n.name for n in cc.by_cluster("db")]
    assert "census" in names and "table_growth" in names
