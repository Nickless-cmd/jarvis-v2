"""Tests for Tools-cluster Phase 2 forbrugs-statistik (tool_usage_store).

Verificerer DB-backed UPSERT-tælling, buckets (most/often/sometimes/rare/never inkl.
aldrig-brugte registrerede tools), katalog-rækkefølge (mest-først, døde-sidst) og dead_tools.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    import core.runtime.db as dbmod
    # tool_usage_store bruger core.runtime.db.connect — peg den på en frisk temp-DB.
    import sqlite3

    def _connect():
        c = sqlite3.connect(tmp.name)
        return c

    monkeypatch.setattr(dbmod, "connect", _connect)
    yield tmp.name
    Path(tmp.name).unlink(missing_ok=True)


def test_record_and_count(tmp_db):
    from core.services import tool_usage_store as tus
    tus.record_use("read_file", kind="native", ok=True)
    tus.record_use("read_file", kind="native", ok=True)
    tus.record_use("read_file", kind="native", ok=False)
    stats = tus.usage_stats()
    assert stats["read_file"]["count"] == 3
    assert stats["read_file"]["errors"] == 1


def test_operator_kind_recorded(tmp_db):
    from core.services import tool_usage_store as tus
    tus.record_use("operator_bash", kind="operator", ok=True)
    assert tus.usage_stats()["operator_bash"]["kind"] == "operator"


def test_buckets_include_never_for_registered(tmp_db):
    from core.services import tool_usage_store as tus
    for _ in range(600):
        tus.record_use("hot_tool")
    b = tus.usage_buckets(registered=["hot_tool", "never_used_tool"])
    assert "hot_tool" in b["most"]
    assert "never_used_tool" in b["never"]


def test_tool_order_most_first_dead_last(tmp_db):
    from core.services import tool_usage_store as tus
    for _ in range(10):
        tus.record_use("used")
    order = tus.tool_order(["dead", "used", "also_dead"])
    assert order[0] == "used"          # mest-brugt først
    assert set(order[1:]) == {"also_dead", "dead"}  # døde sidst (alfabetisk)


def test_dead_tools(tmp_db):
    from core.services import tool_usage_store as tus
    tus.record_use("alive")
    dead = tus.dead_tools(["alive", "ghost1", "ghost2"])
    assert dead == ["ghost1", "ghost2"]


def test_observe_stats_self_safe(tmp_db):
    from core.services import tool_usage_store as tus
    tus.record_use("x")
    summary = tus.observe_stats(registered=["x", "y"])
    assert summary["tracked"] == 1
    assert summary["never"] == 1  # 'y' aldrig brugt


def test_catalog_validates_with_usage_nerves():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    names = [n.name for n in cc.by_cluster("tools")]
    assert "tool_usage_stats" in names
