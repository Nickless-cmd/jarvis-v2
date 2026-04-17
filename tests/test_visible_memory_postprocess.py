from __future__ import annotations

import importlib

from core.eventbus.bus import event_bus


def test_visible_memory_postprocess_consolidates_even_when_distillation_fails(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    session_distillation = importlib.import_module(
        "core.services.session_distillation"
    )
    end_consolidation = importlib.import_module(
        "core.services.end_of_run_memory_consolidation"
    )

    calls: list[dict[str, object]] = []

    def _boom(**kwargs):
        raise RuntimeError("distillation broke")

    def _consolidate(**kwargs):
        calls.append(kwargs)
        return {
            "candidate_count": 0,
            "memory_updated": False,
            "user_updated": False,
            "skipped_reason": "no-new-memory-items",
        }

    monkeypatch.setattr(session_distillation, "distill_session_carry", _boom)
    monkeypatch.setattr(end_consolidation, "consolidate_run_memory", _consolidate)
    monkeypatch.setattr(
        visible_runs,
        "_recent_internal_tool_context",
        lambda session_id: "[bash]: internal tool result",
    )

    run = visible_runs.VisibleRun(
        run_id="visible-memory-postprocess-test",
        lane="visible",
        provider="ollama",
        model="qwen3.5:9b",
        user_message="Husk tool resultatet.",
        session_id="postprocess-session",
    )

    visible_runs._run_memory_postprocess(run, "Jeg har undersøgt det.")

    assert calls
    assert calls[0]["internal_context"] == "[bash]: internal tool result"
    recent = event_bus.recent(limit=4)
    kinds = [item["kind"] for item in recent]
    assert "memory.session_distillation_failed" in kinds
    assert "memory.visible_run_postprocess_completed" in kinds
