"""Tests for inner_voice_shadow.py — pilot for llm_driven_inner_pipeline.

Shadow recorder must NEVER affect production return values, must be
fail-tolerant (LLM down/timeout shouldn't impact heartbeat), and must
store both template and LLM outputs side-by-side for later comparison.
"""
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    import core.services.inner_voice_shadow as mod
    monkeypatch.setattr(mod, "DB_PATH", path)
    yield path
    # Drain any in-flight shadow threads so they don't write to the
    # production DB after the patch is reverted.
    _wait_for_shadow_thread()
    path.unlink(missing_ok=True)


def _wait_for_shadow_thread():
    """Shadow runs in a daemon thread; give it a moment to finish."""
    # Find inner-voice-shadow threads and wait for them
    for t in threading.enumerate():
        if t.name == "inner-voice-shadow" and t.is_alive():
            t.join(timeout=15)


# ── Production contract: LLM-primary, template fallback ─────────────────


def test_helpful_signal_falls_back_to_template_on_llm_failure(tmp_db, monkeypatch):
    """When LLM call fails (error/timeout/empty), _helpful_signal must
    fall back to the template output — heartbeat must never break."""
    import core.services.inner_voice_shadow as shadow_mod

    def _failing_llm(prompt):
        return {"output": None, "provider": None, "model": None,
                "latency_ms": 0, "error": "stub failure"}

    monkeypatch.setattr(shadow_mod, "_call_llm", _failing_llm)

    from core.memory.private_growth_note import _helpful_signal
    out = _helpful_signal(
        status="completed", focus="cache-fix", work_signal="completed:cache",
    )
    # Falls back to template
    assert "holde fast" in out
    assert len(out) <= 140


def test_helpful_signal_returns_llm_output_when_succeeds(tmp_db, monkeypatch):
    """2026-05-25 rollout: LLM output IS what _helpful_signal returns now
    (was template-only before). Template becomes fallback path."""
    import core.services.inner_voice_shadow as shadow_mod
    monkeypatch.setattr(
        shadow_mod, "_call_llm",
        lambda _: {"output": "LLM-skrevet kort note.", "provider": "p",
                   "model": "m", "latency_ms": 100, "error": None},
    )
    from core.memory.private_growth_note import _helpful_signal

    completed = _helpful_signal(status="completed", focus="f", work_signal="")
    failed = _helpful_signal(status="failed", focus="f", work_signal="")
    observe = _helpful_signal(status="observe", focus="f", work_signal="")
    unknown = _helpful_signal(status="weird", focus="f", work_signal="")

    # All four paths return the LLM output (LLM succeeded for each)
    assert completed == "LLM-skrevet kort note."
    assert failed == "LLM-skrevet kort note."
    assert observe == "LLM-skrevet kort note."
    assert unknown == "LLM-skrevet kort note."


# ── Shadow recording ────────────────────────────────────────────────────


def test_shadow_records_template_and_llm(tmp_db, monkeypatch):
    """When LLM succeeds, both outputs are stored side-by-side."""
    import core.services.inner_voice_shadow as shadow_mod
    monkeypatch.setattr(
        shadow_mod, "_call_llm",
        lambda _: {"output": "LLM siger noget kort.", "provider": "deepseek",
                   "model": "v4-flash", "latency_ms": 800, "error": None},
    )
    from core.memory.private_growth_note import _helpful_signal
    _helpful_signal(status="completed", focus="cache", work_signal="")
    _wait_for_shadow_thread()

    with sqlite3.connect(str(tmp_db)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM inner_voice_shadow ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    assert row["function_name"] == "_helpful_signal"
    assert "holde fast" in row["template_output"]
    assert row["llm_output"] == "LLM siger noget kort."
    assert row["llm_provider"] == "deepseek"
    assert row["llm_model"] == "v4-flash"
    assert row["llm_latency_ms"] == 800
    assert row["llm_error"] is None


def test_shadow_records_llm_failure(tmp_db, monkeypatch):
    """When LLM fails, the error is stored — template_output still present."""
    import core.services.inner_voice_shadow as shadow_mod
    monkeypatch.setattr(
        shadow_mod, "_call_llm",
        lambda _: {"output": None, "provider": None, "model": None,
                   "latency_ms": 100, "error": "rate-limited"},
    )
    from core.memory.private_growth_note import _helpful_signal
    _helpful_signal(status="failed", focus="x", work_signal="")
    _wait_for_shadow_thread()

    with sqlite3.connect(str(tmp_db)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM inner_voice_shadow ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    assert row["llm_output"] is None
    assert row["llm_error"] == "rate-limited"
    assert "varsom" in row["template_output"]


def test_stats_aggregation(tmp_db, monkeypatch):
    """shadow_stats summarizes total / success / latency / sizes."""
    import core.services.inner_voice_shadow as shadow_mod

    call_count = [0]

    def _mixed_llm(_):
        call_count[0] += 1
        if call_count[0] % 2 == 0:
            return {"output": None, "provider": None, "model": None,
                    "latency_ms": 100, "error": "fail"}
        return {"output": "noget output", "provider": "p", "model": "m",
                "latency_ms": 500, "error": None}

    monkeypatch.setattr(shadow_mod, "_call_llm", _mixed_llm)

    from core.memory.private_growth_note import _helpful_signal
    for _ in range(4):
        _helpful_signal(status="completed", focus="f", work_signal="")
        _wait_for_shadow_thread()

    from core.services.inner_voice_shadow import shadow_stats
    stats = shadow_stats()
    assert stats["total_shadows"] == 4
    assert stats["successful_llm_calls"] == 2
    assert stats["success_rate"] == 0.5
    assert stats["avg_llm_latency_ms"] == 500
