"""Tests for daemon_llm cache-effektivitets-instrumentering (Bølge 0, observe-only)."""
from __future__ import annotations

import pytest

from core.services import central_timeseries
from core.services import daemon_llm as dl


@pytest.fixture(autouse=True)
def _clean():
    with dl._llm_lock:
        dl._llm_stats.clear()
    central_timeseries._reset_for_tests()
    yield
    with dl._llm_lock:
        dl._llm_stats.clear()
    central_timeseries._reset_for_tests()


def test_note_call_tracks_hit_rate():
    dl._note_call("somatic", hit=False)
    dl._note_call("somatic", hit=True)
    dl._note_call("somatic", hit=True)
    snap = dl.daemon_llm_cache_snapshot()
    assert snap["somatic"] == {"calls": 3, "hits": 2, "hit_rate": round(2 / 3, 3)}
    # seneste sample i tidsserien = løbende hit-rate
    last = central_timeseries.recent("daemon_llm", "somatic", limit=1)[-1]
    assert last.value == round(2 / 3, 3)


def test_snapshot_sorted_by_calls():
    for _ in range(5):
        dl._note_call("dream", hit=False)
    dl._note_call("mood", hit=True)
    keys = list(dl.daemon_llm_cache_snapshot().keys())
    assert keys[0] == "dream"  # flest kald først


def test_note_call_self_safe():
    try:
        dl._note_call(None, hit=True)  # type: ignore[arg-type]
    except Exception as e:  # pragma: no cover
        pytest.fail(f"_note_call kastede: {e}")


# ── Fail-open synlighed: begge LLM-lanes tørre → observe daemon_llm_dry ──────
def test_both_lanes_dry_observes_central(monkeypatch):
    """Når BÅDE cheap- og heartbeat-lane fejler → returner fallback (uændret adfærd)
    MEN observe et 'daemon_llm_dry'-signal så drift-monitoren fanger korrelerede fald."""
    # Ingen cache-sti: form-judge/cache må ikke kortslutte kaldet.
    monkeypatch.setattr(dl, "_get_cache_ttl", lambda name: 0)

    # public_safe=True → cheap-lane går via execute_public_safe_cheap_lane; lad den kaste.
    def _cheap_boom(*a, **k):
        raise RuntimeError("provider outage")

    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.execute_public_safe_cheap_lane",
        _cheap_boom)
    # Heartbeat-fallback: lad target-valget kaste, så text forbliver tomt.
    monkeypatch.setattr(
        "core.services.heartbeat_runtime._select_heartbeat_target",
        lambda: (_ for _ in ()).throw(RuntimeError("heartbeat nede")))

    observed: list[dict] = []

    class _FakeCentral:
        def observe(self, event):
            observed.append(event)

    monkeypatch.setattr("core.services.central_core.central", lambda: _FakeCentral())

    out = dl._daemon_llm_call_impl(
        "prompt", max_len=100, fallback="FALLBACK",
        daemon_name="somatic", public_safe=True)

    assert out == "FALLBACK"  # adfærd uændret: fallback returneres
    # Filtrér til dry-signalet: cache-miss fyrer nu OGSÅ et cost/llm_egress-observe
    # (samlet egress-billede), så tæl kun daemon_llm_dry-nerven.
    dry = [e for e in observed if e.get("nerve") == "daemon_llm_dry"]
    assert len(dry) == 1
    ev = dry[0]
    assert ev["cluster"] == "stream"
    assert ev["nerve"] == "daemon_llm_dry"
    assert ev["kind"] == "error"
    assert ev["daemon"] == "somatic"


def test_dry_observe_is_self_safe(monkeypatch):
    """Self-safe: kaster central().observe påvirkes fallback-returen IKKE."""
    monkeypatch.setattr(dl, "_get_cache_ttl", lambda name: 0)
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.execute_public_safe_cheap_lane",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("outage")))
    monkeypatch.setattr(
        "core.services.heartbeat_runtime._select_heartbeat_target",
        lambda: (_ for _ in ()).throw(RuntimeError("down")))

    class _BoomCentral:
        def observe(self, event):
            raise RuntimeError("observe nede")

    monkeypatch.setattr("core.services.central_core.central", lambda: _BoomCentral())

    out = dl._daemon_llm_call_impl(
        "prompt", max_len=100, fallback="FALLBACK",
        daemon_name="somatic", public_safe=True)
    assert out == "FALLBACK"  # fail-safe holder trods observe-fejl


def test_lane_success_does_not_observe_dry(monkeypatch):
    """Regression: når en lane leverer tekst må dry-signalet IKKE fyre."""
    monkeypatch.setattr(dl, "_get_cache_ttl", lambda name: 0)
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.execute_public_safe_cheap_lane",
        lambda *a, **k: {"text": "ægte svar", "provider": "public-safe"})

    observed: list[dict] = []

    class _FakeCentral:
        def observe(self, event):
            observed.append(event)

    monkeypatch.setattr("core.services.central_core.central", lambda: _FakeCentral())

    out = dl._daemon_llm_call_impl(
        "prompt", max_len=100, fallback="FALLBACK",
        daemon_name="somatic", public_safe=True)
    assert out == "ægte svar"
    assert not any(e.get("nerve") == "daemon_llm_dry" for e in observed)


def test_note_call_miss_reports_egress(monkeypatch):
    """SAMLET EGRESS: cache-MISS er ægte udgående kald → egress-observeren fyrer med lane=daemon."""
    seen: list[dict] = []

    def _fake_observe(**kw):
        seen.append(kw)

    monkeypatch.setattr("core.services.central_llm_egress.observe", _fake_observe)
    dl._note_call("thought_stream", hit=False)

    assert len(seen) == 1
    assert seen[0]["lane"] == "daemon"
    assert seen[0]["autonomous"] is True
    assert seen[0]["source"] == "daemon:thought_stream"


def test_note_call_hit_does_not_report_egress(monkeypatch):
    """Cache-HIT / form-genbrug forlader ikke maskinen → INGEN egress-rapport."""
    seen: list[dict] = []
    monkeypatch.setattr("core.services.central_llm_egress.observe", lambda **kw: seen.append(kw))
    dl._note_call("thought_stream", hit=True)
    assert seen == []
