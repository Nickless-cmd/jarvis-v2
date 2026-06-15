"""Tests for generalized-learning capture-wiring (backlog #159, plan A: direkte
capture med dedup). De 4 ikke-wirede kilder kalder nu capture_conclusion."""
from __future__ import annotations


def _rows(source: str | None = None) -> int:
    from core.services.reasoning_store import recall_reasoning
    rows = recall_reasoning(limit=100)
    if source:
        rows = [r for r in rows if r.get("source") == source]
    return len(rows)


# ── dedup_key-primitiv ──

def test_capture_dedup_key_is_idempotent(isolated_runtime) -> None:
    from core.services.reasoning_store import capture_conclusion
    a = capture_conclusion(source="deep_analyze", conclusion_text="x", dedup_key="k1")
    b = capture_conclusion(source="deep_analyze", conclusion_text="x igen", dedup_key="k1")
    assert a == b  # samme deterministiske cid
    assert _rows("deep_analyze") == 1  # kun én række trods to kald


def test_capture_without_dedup_key_allows_duplicates(isolated_runtime) -> None:
    from core.services.reasoning_store import capture_conclusion
    capture_conclusion(source="manual", conclusion_text="a")
    capture_conclusion(source="manual", conclusion_text="b")
    assert _rows("manual") == 2


# ── Kilde 1: deep_analyze ──

def test_deep_analyze_captures_conclusion(isolated_runtime, monkeypatch) -> None:
    from core.tools import simple_tools
    monkeypatch.setattr("core.services.deep_analyzer.run_deep_analysis",
                        lambda **kw: {"summary": "fandt 3 risici i auth", "findings": []})
    r = simple_tools._exec_deep_analyze({"goal": "audit auth", "scope": "repo"})
    assert r["status"] == "ok"
    assert _rows("deep_analyze") == 1


# ── Kilde 2: reasoning_classify ──

def test_reasoning_classify_captures_conclusion(isolated_runtime, monkeypatch) -> None:
    from core.services import reasoning_classifier
    monkeypatch.setattr(reasoning_classifier, "classify_reasoning_tier",
                        lambda message, **kw: {"tier": "deep", "score": 8, "reason": "kompleks"})
    reasoning_classifier._exec_reasoning_classify({"message": "design en distribueret kø"})
    assert _rows("reasoning_classify") == 1


# ── Kilde 3: agent_self_evaluation ──

def test_self_evaluation_captures_conclusion(isolated_runtime, monkeypatch) -> None:
    from core.services import agent_self_evaluation as ase
    monkeypatch.setattr(ase, "tick_quality_summary",
                        lambda **kw: {"status": "ok", "count": 10, "avg_score": 0.42, "trend": "faldende"})
    ase.self_evaluation_section()
    assert _rows("self_evaluation") == 1


# ── Kilde 4: counterfactual_self_simulation ──

def test_counterfactual_captures_conclusion(isolated_runtime, monkeypatch) -> None:
    from core.services import counterfactual_self_simulation as cf
    monkeypatch.setattr(cf, "_feed_learning", lambda sim: None)  # isolér tung downstream
    episode = {"run_id": "r1", "policy": "deepseek", "outcome": "ok"}
    cf.simulate_from_episode(episode)
    assert _rows("counterfactual") >= 1
