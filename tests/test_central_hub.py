"""Tests for central_hub — Jarvis Mind-projektions-hub (ét ground truth)."""
from __future__ import annotations

from core.services import central_hub as h


def test_index_lists_all_sections():
    idx = h.mind_index()
    keys = [s["section"] for s in idx]
    assert "overview" in keys and "mind" in keys and "observability" in keys
    assert len(idx) == 10
    # ready-flag matcher byggerne
    ready = {s["section"] for s in idx if s["ready"]}
    assert ready == {"overview", "mind", "observability"}


def test_pending_section_is_marked_not_error():
    r = h.mind_section("council")
    assert r["pending"] is True and r["active"] is False
    assert "error" not in r


def test_unknown_section_is_error():
    r = h.mind_section("frobnicate")
    assert r.get("error") and r["active"] is False


def test_section_is_self_safe_on_builder_crash(monkeypatch):
    # en byggers fejl må aldrig vælte hub'en — sektionen returnerer {error}
    monkeypatch.setitem(h._BUILDERS, "mind",
                        lambda: (_ for _ in ()).throw(RuntimeError("surface nede")))
    r = h.mind_section("mind")
    assert "surface nede" in r["error"] and r["active"] is False
    assert r["section"] == "mind"


def test_snapshot_default_is_index_only():
    snap = h.mind_snapshot()
    assert "index" in snap and snap["sections"] == {}
    snap2 = h.mind_snapshot(sections=["overview"])
    assert "overview" in snap2["sections"]


def test_overview_reads_central_pulse(monkeypatch):
    import core.services.central_realtime as cr
    monkeypatch.setattr(cr, "realtime_snapshot",
                        lambda **k: {"status": "green", "coverage": {"nerves": 5},
                                     "diagnose": {}, "processes": [], "clusters": []})
    r = h.mind_section("overview")
    assert r["status"] == "green" and r["coverage"]["nerves"] == 5 and r["active"] is True
