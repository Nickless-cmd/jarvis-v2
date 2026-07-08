"""Harness Part 1: model-window-aware compaction threshold."""
from core.context.auto_compact import _compaction_threshold


def test_large_window_compacts_at_70pct(monkeypatch):
    monkeypatch.setattr("core.context.auto_compact.model_context_window", lambda p, m: 1_000_000)
    assert _compaction_threshold(provider="deepseek", model="v4-flash", flat_fallback=192_000) == 700_000


def test_small_window_scales_down(monkeypatch):
    monkeypatch.setattr("core.context.auto_compact.model_context_window", lambda p, m: 128_000)
    assert _compaction_threshold(provider="x", model="y", flat_fallback=192_000) == int(128_000 * 0.70)


def test_unknown_window_falls_back_flat(monkeypatch):
    monkeypatch.setattr("core.context.auto_compact.model_context_window",
                        lambda p, m: (_ for _ in ()).throw(RuntimeError("unknown")))
    assert _compaction_threshold(provider="x", model="y", flat_fallback=192_000) == 192_000


def test_zero_window_falls_back_flat(monkeypatch):
    monkeypatch.setattr("core.context.auto_compact.model_context_window", lambda p, m: 0)
    assert _compaction_threshold(provider="x", model="y", flat_fallback=192_000) == 192_000
