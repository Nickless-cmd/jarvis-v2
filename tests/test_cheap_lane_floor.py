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


def test_default_floor_uses_v4_flash_not_dying_chat_alias():
    """WS4 (spec 2026-07-13): default-bunden må IKKE bruge den døende
    ``deepseek-chat``-alias (udfases 24. juli 2026) — den skal være
    ``deepseek-v4-flash``."""
    assert floor._DEFAULT_FLOOR == [("deepseek", "deepseek-v4-flash")]
    # floor_targets() falder tilbage til default når config er tom
    import core.runtime.settings as settings_mod

    class _S:
        cheap_lane_floor_targets = None

    orig = settings_mod.load_settings
    try:
        settings_mod.load_settings = lambda: _S()  # type: ignore[assignment]
        assert floor.floor_targets() == [("deepseek", "deepseek-v4-flash")]
    finally:
        settings_mod.load_settings = orig  # type: ignore[assignment]


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
