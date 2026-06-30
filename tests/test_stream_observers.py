"""Stream-observabilitets-nerver (visible_runs_sections.stream_observers).

Boy Scout-udtrækning fra visible_runs.py (2026-06-30). Nerverne SKAL være
self-safe: de gør tavse stream-/persist-hændelser synlige i Centralen, men må
ALDRIG kaste tilbage ind i stream-stien. observe_streamed_text_recovered er
den nye dag-ét-divergens-måler (streamede bytes reddet når result.text svigtede).
"""
from __future__ import annotations

from types import SimpleNamespace

from core.services.visible_runs_sections import stream_observers as so


class _CapturingCentral:
    def __init__(self):
        self.events: list[dict] = []

    def observe(self, payload):
        self.events.append(payload)


def _run():
    return SimpleNamespace(
        run_id="visible-abc123", session_id="sess-1",
        provider="deepseek", model="deepseek-v4-flash",
    )


def _patch_central(monkeypatch, central_obj):
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: central_obj, raising=False)


def test_persist_failed_observes_with_stream_cluster(monkeypatch):
    cap = _CapturingCentral()
    _patch_central(monkeypatch, cap)
    so.observe_persist_failed(_run(), RuntimeError("db locked"))
    assert len(cap.events) == 1
    ev = cap.events[0]
    assert ev["cluster"] == "stream"
    assert ev["nerve"] == "persist_failed"
    assert ev["run_id"] == "visible-abc123"
    assert "db locked" in ev["error"]


def test_streamed_text_recovered_observes_chars_and_source(monkeypatch):
    cap = _CapturingCentral()
    _patch_central(monkeypatch, cap)
    so.observe_streamed_text_recovered(_run(), chars=412, source="first_pass_stream")
    assert len(cap.events) == 1
    ev = cap.events[0]
    assert ev["cluster"] == "stream"
    assert ev["nerve"] == "streamed_text_recovered"
    assert ev["chars"] == 412
    assert ev["source"] == "first_pass_stream"
    assert ev["provider"] == "deepseek"
    assert ev["model"] == "deepseek-v4-flash"


def test_observers_are_self_safe_when_central_raises(monkeypatch):
    # Hvis Centralen selv kaster, må nerven ALDRIG boble op i stream-stien.
    def _boom():
        raise RuntimeError("central down")
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", _boom, raising=False)
    # Ingen af dem må kaste:
    so.observe_persist_failed(_run(), ValueError("x"))
    so.observe_streamed_text_recovered(_run(), chars=1, source="agentic_first_pass_stream")


def test_observers_tolerate_partial_run_object(monkeypatch):
    cap = _CapturingCentral()
    _patch_central(monkeypatch, cap)
    # Run uden alle felter (getattr-defaults skal holde):
    bare = SimpleNamespace(run_id="r1")
    so.observe_streamed_text_recovered(bare, chars=5, source="first_pass_stream")
    assert cap.events[0]["session_id"] == ""
    assert cap.events[0]["provider"] == ""
