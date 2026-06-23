"""Test: self-model render dropper log/event-navne (Jarvis-spec 2026-06-23 #2)."""
from __future__ import annotations

from core.services import self_model_signal_tracking as sm


def test_machine_id_title_is_dropped(monkeypatch):
    def _fake_surface(limit=5):
        return {
            "summary": {"active_count": 2},
            "items": [
                {"status": "active", "confidence": "high",
                 "title": "Strength: plugin_container_process_kill_load_reduction_success"},
                {"status": "active", "confidence": "high",
                 "title": "Strength: tålmodig og grundig fejlsøgning"},
            ],
        }
    monkeypatch.setattr(sm, "build_runtime_self_model_signal_surface", _fake_surface, raising=False)
    out = sm.build_self_model_signal_prompt_section(limit=5) or ""
    assert "plugin_container_process_kill" not in out      # maskin-id droppet
    assert "tålmodig" in out                               # menneskelæsbar beholdt
