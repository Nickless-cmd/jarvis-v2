def test_ollama_failure_falls_to_cheap_pool(monkeypatch):
    from core.services import non_visible_fallback as f
    monkeypatch.setattr(f, "_fallback_enabled", lambda: True)
    monkeypatch.setattr(f, "execute_cheap_lane_via_pool",
                        lambda **k: {"text": "ok", "lane": "cheap", "provider": "groq"})
    def boom(): raise RuntimeError("quota")
    r = f.run_non_visible_with_fallback(message="hej", primary_call=boom, run_is_autonomous=True)
    assert r["lane"] == "cheap"


def test_visible_is_rejected():
    from core.services import non_visible_fallback as f
    import pytest
    with pytest.raises(AssertionError):
        f.run_non_visible_with_fallback(message="x", primary_call=lambda: {}, run_is_autonomous=False)


def test_pool_exhausted_returns_floor(monkeypatch):
    from core.services import non_visible_fallback as f
    monkeypatch.setattr(f, "_fallback_enabled", lambda: True)
    monkeypatch.setattr(f, "execute_cheap_lane_via_pool",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("all failed")))
    monkeypatch.setattr(f, "attempt_floor", lambda **k: {"text": "", "lane": "floor"})
    def boom(): raise RuntimeError("q")
    r = f.run_non_visible_with_fallback(message="x", primary_call=boom, run_is_autonomous=True)
    assert r["lane"] == "floor"


def test_flag_off_reraises(monkeypatch):
    from core.services import non_visible_fallback as f
    monkeypatch.setattr(f, "_fallback_enabled", lambda: False)
    import pytest
    def boom(): raise RuntimeError("q")
    with pytest.raises(RuntimeError):
        f.run_non_visible_with_fallback(message="x", primary_call=boom, run_is_autonomous=True)


def test_primary_success_returns_directly():
    from core.services import non_visible_fallback as f
    r = f.run_non_visible_with_fallback(message="x", primary_call=lambda: {"text": "hi", "lane": "ollama"}, run_is_autonomous=True)
    assert r["lane"] == "ollama"
