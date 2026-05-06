from core.services import tool_router_runtime as trr


def test_compute_threshold_adjustment_high_load_more_increases():
    new_t = trr._adjust_threshold(current=0.55, load_more_rate_7d=0.20)
    assert new_t > 0.55


def test_compute_threshold_adjustment_low_load_more_decreases():
    new_t = trr._adjust_threshold(current=0.55, load_more_rate_7d=0.02)
    assert new_t < 0.55


def test_threshold_bounded_high():
    assert trr._adjust_threshold(current=0.85, load_more_rate_7d=0.50) <= 0.85


def test_threshold_bounded_low():
    assert trr._adjust_threshold(current=0.30, load_more_rate_7d=0.0) >= 0.30


def test_threshold_unchanged_in_neutral_band():
    assert trr._adjust_threshold(current=0.55, load_more_rate_7d=0.10) == 0.55


def test_run_once_returns_summary(monkeypatch):
    monkeypatch.setattr("core.services.tool_embeddings.warmup_all", lambda: 42)
    monkeypatch.setattr(trr, "_read_load_more_rate", lambda: 0.07)
    out = trr.run_once()
    assert out.get("embeddings_warmed") == 42
    assert "threshold_proposed" in out
    assert "started_at" in out
    assert "finished_at" in out
