"""Tests for core/services/cheap_lane_floor.py — aldrig-tør-bund."""
from __future__ import annotations
import core.services.cheap_lane_floor as floor


def test_floor_result_is_typed_and_never_empty_shape():
    r = floor.floor_result(lane="cheap", reason="no-healthy-provider")
    assert r["status"] == "degraded"
    assert r["provider"] == "floor"
    assert r["lane"] == "cheap"
    assert r["floor_reason"] == "no-healthy-provider"
    assert "text" in r  # nøglen findes altid (tom er ok)


def test_attempt_floor_returns_ok_when_a_floor_target_answers(monkeypatch):
    calls = []

    def fake_exec(*, provider, model, message, lane):
        calls.append((provider, model))
        return {"status": "ok", "provider": provider, "model": model, "lane": lane,
                "text": "OK", "input_tokens": 1, "output_tokens": 1, "is_floor": True}

    monkeypatch.setattr(floor, "_execute_floor_target", fake_exec)
    monkeypatch.setattr(floor, "floor_targets", lambda: [("deepseek", "deepseek-chat")])
    r = floor.attempt_floor(message="hej", lane="cheap", reason="no-healthy-provider")
    assert r["status"] == "ok"
    assert r["text"] == "OK"
    assert calls == [("deepseek", "deepseek-chat")]


def test_attempt_floor_degrades_and_never_raises_when_all_fail(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("floor target down")

    monkeypatch.setattr(floor, "_execute_floor_target", boom)
    monkeypatch.setattr(floor, "floor_targets",
                        lambda: [("deepseek", "deepseek-chat"), ("ollama", "x")])
    r = floor.attempt_floor(message="hej", lane="cheap", reason="exhausted")
    assert r["status"] == "degraded"   # aldrig raise
    assert r["provider"] == "floor"
    assert r["text"] == ""
