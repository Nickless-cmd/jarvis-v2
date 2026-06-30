"""Cognitive-state cache — state-aware invalidation (2026-06-30).

Cachen holdt før KUN på TTL; invalidation_snapshot blev gemt men aldrig
sammenlignet. Nu sammenligner _get_cached_state snapshotten ved hvert hit →
stale ved ÆGTE indre-tilstands-ændring (mood/bearing/chronicle/rhythm) uanset TTL.
"""
from __future__ import annotations

from core.services import cognitive_state_assembly as cs


class _FakeCache:
    """Minimal shared_cache-stand-in (in-memory, ingen TTL-udløb i testen)."""

    def __init__(self):
        self.store: dict[str, dict] = {}

    def set(self, key, value, ttl_seconds=0):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def invalidate_prefix(self, prefix):
        for k in [k for k in self.store if k.startswith(prefix)]:
            del self.store[k]


def _patch(monkeypatch, snapshot):
    fake = _FakeCache()
    import core.services.shared_cache as real_sc
    monkeypatch.setattr(real_sc, "set", fake.set, raising=False)
    monkeypatch.setattr(real_sc, "get", fake.get, raising=False)
    monkeypatch.setattr(real_sc, "invalidate_prefix", fake.invalidate_prefix, raising=False)
    monkeypatch.setattr(cs, "_build_invalidation_snapshot", lambda: dict(snapshot))
    monkeypatch.setattr(cs, "_cache_enabled", lambda: True)
    return fake


def test_default_ttl_raised_to_600(monkeypatch):
    # Standard-TTL er hævet (sikkert pga. tilstands-bevidst invalidering).
    assert cs._cache_ttl_seconds() >= 600


def test_hit_when_state_unchanged(monkeypatch):
    snap = {"pv_version": 5, "pv_bearing": "rolig", "rhythm_phase": "wake"}
    _patch(monkeypatch, snap)
    cs._set_cached_state("visible_full", "indre tilstand A", ["self"])
    assert cs._get_cached_state("visible_full") == "indre tilstand A"


def test_stale_when_state_changed(monkeypatch):
    snap = {"pv_version": 5, "pv_bearing": "rolig", "rhythm_phase": "wake"}
    _patch(monkeypatch, snap)
    cs._set_cached_state("visible_full", "indre tilstand A", ["self"])
    # Skift tilstanden (ny mood/version) → snapshotten matcher ikke længere
    snap["pv_version"] = 6
    snap["pv_bearing"] = "frustreret"
    assert cs._get_cached_state("visible_full") is None  # stale → rebuild


def test_snapshot_stored_fresh_at_write(monkeypatch):
    snap = {"pv_version": 1}
    fake = _patch(monkeypatch, snap)
    cs._set_cached_state("visible_full", "x", [])
    entry = fake.get("cognitive_state:visible_full")
    assert entry["invalidation_snapshot"] == {"pv_version": 1}


def test_invalidate_clears(monkeypatch):
    snap = {"pv_version": 1}
    _patch(monkeypatch, snap)
    cs._set_cached_state("visible_full", "x", [])
    cs.invalidate_cognitive_state_cache()
    assert cs._get_cached_state("visible_full") is None
