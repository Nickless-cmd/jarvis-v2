"""Unit tests for context_window_manager."""
from __future__ import annotations

from unittest.mock import patch

from core.services.context_window_manager import (
    apply_sliding,
    estimate_pressure,
    degradation_signal,
    adaptive_pick_strategy,
    context_window_section,
    _is_anchor,
)


def _msg(content: str, role: str = "user"):
    return {"role": role, "content": content}


def test_anchor_detection():
    assert _is_anchor(_msg("Vi besluttede at gå med option B"))
    assert _is_anchor(_msg("VIGTIGT: husk at backup'e først"))
    assert _is_anchor(_msg("error: filen findes ikke"))
    assert not _is_anchor(_msg("ok"))
    assert not _is_anchor(_msg("forstået"))


def test_sliding_keeps_recent():
    msgs = [_msg(f"msg {i}") for i in range(50)]
    result = apply_sliding(msgs, keep_recent=10, preserve_anchors=False)
    assert result["kept"] == 10
    assert result["dropped"] == 40
    assert result["messages"][-1]["content"] == "msg 49"


def test_sliding_preserves_anchors():
    msgs = [_msg(f"msg {i}") for i in range(50)]
    msgs[5]["content"] = "Vi besluttede at gå videre"
    msgs[15]["content"] = "VIGTIGT: backup nu"
    result = apply_sliding(msgs, keep_recent=10, preserve_anchors=True)
    assert result["anchors_preserved"] == 2
    contents = [m["content"] for m in result["messages"]]
    assert any("besluttede" in c for c in contents)
    assert any("backup" in c for c in contents)


def test_sliding_short_history_no_op():
    msgs = [_msg(f"m{i}") for i in range(5)]
    result = apply_sliding(msgs, keep_recent=10)
    assert result["kept"] == 5
    assert result["dropped"] == 0


def test_pressure_levels():
    with patch("core.services.context_window_manager._estimate_session_tokens", return_value=2000):
        assert estimate_pressure()["level"] == "comfortable"
    with patch("core.services.context_window_manager._estimate_session_tokens", return_value=10000):
        assert estimate_pressure()["level"] == "elevated"
    with patch("core.services.context_window_manager._estimate_session_tokens", return_value=20000):
        assert estimate_pressure()["level"] == "high"
    with patch("core.services.context_window_manager._estimate_session_tokens", return_value=30000):
        assert estimate_pressure()["level"] == "critical"


def test_degradation_zero_when_no_signals():
    with patch("core.services.context_window_manager._estimate_session_tokens", return_value=2000):
        from core.eventbus.bus import event_bus
        with patch.object(event_bus, "recent", return_value=[]):
            d = degradation_signal()
        assert d["score"] == 0
        assert d["advice"] == "ok"


def test_degradation_detects_errors_and_loops():
    fake_events = [
        {"kind": "tool.completed", "payload": {"tool": "x", "status": "error"}},
        {"kind": "tool.completed", "payload": {"tool": "x", "status": "error"}},
        {"kind": "tool.completed", "payload": {"tool": "x", "status": "error"}},
        {"kind": "tool.completed", "payload": {"tool": "x", "status": "error"}},
        {"kind": "tool.completed", "payload": {"tool": "x", "status": "error"}},
    ]
    from core.eventbus.bus import event_bus
    with patch.object(event_bus, "recent", return_value=fake_events), \
         patch("core.services.context_window_manager._estimate_session_tokens", return_value=5000):
        d = degradation_signal()
    assert d["score"] >= 30
    assert any("error" in s for s in d["signals"])


def test_adaptive_picks_none_when_comfortable():
    with patch("core.services.context_window_manager.degradation_signal",
               return_value={"advice": "ok", "score": 0}):
        assert adaptive_pick_strategy() == "none"


def test_adaptive_picks_smart_compact_for_smart_advice():
    with patch("core.services.context_window_manager.degradation_signal",
               return_value={"advice": "compact_smart", "score": 40}):
        assert adaptive_pick_strategy() == "smart_compact"


def test_adaptive_picks_aggressive_for_high_degradation():
    with patch("core.services.context_window_manager.degradation_signal",
               return_value={"advice": "compact_now_aggressive", "score": 75}):
        assert adaptive_pick_strategy() == "sliding_with_anchors"


def test_section_returns_none_when_ok():
    with patch("core.services.context_window_manager.degradation_signal",
               return_value={"advice": "ok", "score": 0, "signals": [], "pressure": {}}):
        assert context_window_section() is None


def test_section_warns_when_degraded():
    with patch("core.services.context_window_manager.degradation_signal",
               return_value={"advice": "compact_smart", "score": 50, "signals": ["x"], "pressure": {}}):
        section = context_window_section()
    assert section is not None
    assert "compact_smart" in section
