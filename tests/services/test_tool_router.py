import pytest
from core.services import tool_router as tr


def test_clarity_signal_short_affirmation_low():
    assert tr._clarity_signal("ja") < 0.3
    assert tr._clarity_signal("ok") < 0.3


def test_clarity_signal_question_high():
    assert tr._clarity_signal("hvor mange tokens bruger vi nu?") > 0.6


def test_clarity_signal_empty_zero():
    assert tr._clarity_signal("") == 0.0


def test_score_monotonic_in_top_sim():
    a = tr._score("læs filen visible_runs.py", top_sim=0.3, load_more_rate_7d=0.05)
    b = tr._score("læs filen visible_runs.py", top_sim=0.7, load_more_rate_7d=0.05)
    assert b > a


def test_score_lowered_by_high_load_more_rate():
    a = tr._score("læs filen", top_sim=0.5, load_more_rate_7d=0.0)
    b = tr._score("læs filen", top_sim=0.5, load_more_rate_7d=0.20)
    assert b < a


def test_killswitch_returns_full_list(monkeypatch):
    class _FakeSettings:
        tool_router_enabled = False
        tool_router_threshold = 0.55
        tool_router_always_core_size = 70
        tool_router_k_embeddings = 30
    monkeypatch.setattr(tr, "RuntimeSettings", lambda: _FakeSettings())
    sel = tr.select_tools(user_message="hvad sker der?", session_id=None, lane="visible")
    assert sel.fallback_used
    assert sel.fallback_reason == "killswitch-off"


def test_low_confidence_falls_back(monkeypatch):
    monkeypatch.setattr(tr, "_load_more_rate_7d", lambda: 0.0)
    monkeypatch.setattr(
        "core.services.tool_embeddings.top_k_similar",
        lambda query, k=30: [],
    )
    sel = tr.select_tools(user_message="ok", session_id=None, lane="visible")
    assert sel.fallback_used
    assert sel.fallback_reason == "confidence-below-threshold"


def test_selection_returns_subset_when_confident(monkeypatch):
    monkeypatch.setattr(tr, "_load_more_rate_7d", lambda: 0.0)
    monkeypatch.setattr(
        "core.services.tool_embeddings.top_k_similar",
        lambda query, k=30: [("read_file", 0.85), ("grep", 0.8)],
    )
    monkeypatch.setattr(tr, "_always_core_set", lambda limit: ["bash", "pause_and_ask"])
    sel = tr.select_tools(
        user_message="hvad er der i visible_runs.py? kan du læse den?",
        session_id=None, lane="visible",
    )
    if not sel.fallback_used:
        assert "bash" in sel.selected_names
        assert "read_file" in sel.selected_names


def test_always_core_falls_back_to_bootstrap(monkeypatch):
    """When call-log is empty AND pinned set is empty, use bootstrap."""
    monkeypatch.setattr("core.services.tool_tagger.get_pinned_set", lambda: set())
    # Patch DB query to return nothing
    monkeypatch.setattr(tr, "connect", lambda: _FakeEmptyDB())
    out = tr._always_core_set(70)
    assert out == tr._BOOTSTRAP_FALLBACK_CORE


class _FakeEmptyDB:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def execute(self, *a, **k):
        class _R:
            def fetchall(self): return []
            def fetchone(self): return [0]
        return _R()
