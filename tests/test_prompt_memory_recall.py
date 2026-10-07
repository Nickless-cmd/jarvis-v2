"""The extracted background recalls still serve cached results without waiting."""
from __future__ import annotations


def test_background_recall_serves_previous_result_without_blocking(monkeypatch):
    from core.services import memory_hierarchy, memory_recall_engine, prompt_memory_recall

    monkeypatch.setattr(memory_hierarchy, "recall_before_act_summary", lambda **kw: "rba-result")
    monkeypatch.setattr(memory_recall_engine, "multi_signal_recall_section", lambda query: "msr-result")

    class ImmediateThread:
        def __init__(self, *, target, **kwargs):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(prompt_memory_recall.threading, "Thread", ImmediateThread)
    session_id = "test-background-recall-cache"
    prompt_memory_recall._RBA_CACHE.pop(session_id, None)
    prompt_memory_recall._MSR_CACHE.pop(session_id, None)
    first, first_inputs = [], []
    prompt_memory_recall.append_background_recall(
        "Hvad aftalte vi sidst?", session_id, first, first_inputs, lambda *args: None,
    )
    assert first == []
    second, second_inputs = [], []
    prompt_memory_recall.append_background_recall(
        "Hvad aftalte vi sidst?", session_id, second, second_inputs, lambda *args: None,
    )
    assert second == ["rba-result", "msr-result"]
    assert "recall-before-act (cached, non-blocking)" in second_inputs
