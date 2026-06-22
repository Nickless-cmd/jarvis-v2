"""Tests for API-endpoint forbrugs-statistik (endpoint_usage_store, parallel til tools).

Verificerer DB-backed UPSERT pr. request (template-aggregering), buckets inkl. registrerede-
men-aldrig-kaldte som 'never', og dead_endpoints mod rute-snapshot.
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_env(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    import core.runtime.db as dbmod
    monkeypatch.setattr(dbmod, "connect", lambda: sqlite3.connect(tmp.name))
    # registreret-rute-snapshot via en in-memory shared_cache-stub
    store = {}
    import core.services.shared_cache as scmod
    monkeypatch.setattr(scmod, "set", lambda k, v, **kw: store.__setitem__(k, v))
    monkeypatch.setattr(scmod, "get", lambda k: store.get(k))
    yield
    Path(tmp.name).unlink(missing_ok=True)


def test_record_aggregates_by_template(tmp_env):
    from core.services import endpoint_usage_store as eus
    eus.record_request("GET", "/attachments/{id}", 200)
    eus.record_request("GET", "/attachments/{id}", 200)
    eus.record_request("GET", "/attachments/{id}", 404)
    s = eus.usage_stats()
    assert s["GET /attachments/{id}"]["count"] == 3
    assert s["GET /attachments/{id}"]["errors"] == 1


def test_dead_endpoints_from_registry(tmp_env):
    from core.services import endpoint_usage_store as eus
    eus.store_registered_routes([("GET", "/used"), ("POST", "/dead"), ("GET", "/also_dead")])
    eus.record_request("GET", "/used", 200)
    dead = eus.dead_endpoints()
    assert dead == ["GET /also_dead", "POST /dead"]


def test_buckets_never_includes_registered_uncalled(tmp_env):
    from core.services import endpoint_usage_store as eus
    eus.store_registered_routes([("GET", "/hot"), ("GET", "/cold")])
    for _ in range(6000):
        eus.record_request("GET", "/hot", 200)
    b = eus.usage_buckets()
    assert "GET /hot" in b["most"]
    assert "GET /cold" in b["never"]


def test_observe_stats_self_safe(tmp_env):
    from core.services import endpoint_usage_store as eus
    eus.store_registered_routes([("GET", "/a"), ("GET", "/b")])
    eus.record_request("GET", "/a", 200)
    summary = eus.observe_stats()
    assert summary["registered"] == 2
    assert summary["dead"] == 1  # /b aldrig kaldt


def test_empty_method_or_path_noop(tmp_env):
    from core.services import endpoint_usage_store as eus
    eus.record_request("", "/x", 200)
    eus.record_request("GET", "", 200)
    assert eus.usage_stats() == {}


def test_catalog_has_endpoint_nerves():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    names = [n.name for n in cc.by_cluster("tools")]
    assert "endpoint_usage_stats" in names and "endpoint_call" in names
