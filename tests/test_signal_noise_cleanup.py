from __future__ import annotations

import importlib
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.services.signal_noise_guard import (
    build_bounded_hypothesis_text,
    is_noisy_signal_text,
    stable_signal_slug,
)


def test_signal_noise_guard_flags_generic_noise() -> None:
    assert is_noisy_signal_text(
        "Current goal: make stabilize det var fanme godt formuleret! jeg er helt enig land visibly"
    )
    assert is_noisy_signal_text(
        "What if så mangle rjeg bar resten could be approached differently?"
    )
    assert not is_noisy_signal_text("fix council summary role prefixes in agent runtime")
    assert stable_signal_slug("fix council summary role prefixes in agent runtime")
    assert "mere afgr" in build_bounded_hypothesis_text("council summary role prefixes").lower()


def test_cadence_producers_skip_noisy_runtime_signals(
    isolated_runtime,
    monkeypatch,
) -> None:
    cadence = importlib.import_module("core.services.cadence_producers")
    cadence = importlib.reload(cadence)

    monkeypatch.setattr(
        importlib.import_module("core.services.living_heartbeat_cycle"),
        "determine_life_phase",
        lambda: {"phase": "dreaming"},
    )

    cadence.produce_signals_from_run(
        run_id="visible-noise-run",
        session_id="test-session",
        user_message="så mangle rjeg bar resten 😛 du har jo fri idag 😉",
        assistant_response="ok",
        outcome_status="completed",
        user_mood="neutral",
    )

    assert isolated_runtime.db.list_runtime_witness_signals(limit=8) == []
    assert isolated_runtime.db.list_runtime_reflection_signals(limit=8) == []
    assert isolated_runtime.db.list_runtime_dream_hypothesis_signals(limit=8) == []


def test_cleanup_archives_noisy_signal_rows(isolated_runtime) -> None:
    db = isolated_runtime.db
    now = datetime.now(UTC).isoformat()

    db.upsert_runtime_development_focus(
        focus_id=f"focus-{uuid4().hex}",
        focus_type="runtime-development-thread",
        canonical_key="development-focus:runtime:det-var-fanme-godt-formuleret:reinforce-retain",
        status="active",
        title="Stabilize Det var fanme godt formuleret! Jeg er helt enig",
        summary="Development state is pushing toward reinforce:retain around Det virker værd at holde fast i det, der hjalp omkring Det var fanme godt formuleret! Jeg er helt enig.",
        rationale="Validation noise",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="noise",
        support_summary="noise",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="noise",
        run_id="test-run",
        session_id="test-session",
    )
    db.upsert_runtime_goal_signal(
        goal_id=f"goal-{uuid4().hex}",
        goal_type="development-direction",
        canonical_key="goal-signal:runtime-det-var-fanme-godt-formuleret-reinforce-retain",
        status="active",
        title="Current goal: make stabilize det var fanme godt formuleret! jeg er helt enig land visibly",
        summary="Current goal: make stabilize det var fanme godt formuleret! jeg er helt enig land visibly",
        rationale="noise",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="noise",
        support_summary="noise",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="noise",
        run_id="test-run",
        session_id="test-session",
    )
    db.upsert_runtime_reflection_signal(
        signal_id=f"reflection-{uuid4().hex}",
        signal_type="post_run_reflection",
        canonical_key="reflection:visible-noise",
        status="active",
        title="Reflected on: så mangle rjeg bar resten 😛 du har jo fri idag 😉",
        summary="Outcome=completed, mood=neutral",
        rationale="noise",
        source_kind="cadence_producer",
        confidence="medium",
        evidence_summary="noise",
        support_summary="noise",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="noise",
        run_id="test-run",
        session_id="test-session",
    )
    db.upsert_runtime_dream_hypothesis_signal(
        signal_id=f"dream-{uuid4().hex}",
        signal_type="post_run_hypothesis",
        canonical_key="dream:visible-noise",
        status="active",
        title="Hypothesis from så mangle rjeg bar resten 😛",
        summary="What if så mangle rjeg bar resten 😛 could be approached differently?",
        rationale="noise",
        source_kind="visible_run",
        confidence="low",
        evidence_summary="noise",
        support_summary="noise",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="noise",
        run_id="test-run",
        session_id="test-session",
    )
    db.upsert_runtime_witness_signal(
        signal_id=f"witness-{uuid4().hex}",
        signal_type="visible_run_observed",
        canonical_key="witness:run:visible-noise",
        status="fresh",
        title="Visible run observed (completed)",
        summary="Observed: så mangle rjeg bar resten 😛 du har jo fri idag 😉 → completed",
        rationale="noise",
        source_kind="visible_run",
        confidence="medium",
        evidence_summary="noise",
        support_summary="noise",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="noise",
        run_id="test-run",
        session_id="test-session",
    )

    cleanup = importlib.import_module("scripts.signal_noise_cleanup")
    result = cleanup.cleanup_signal_noise(
        db_path=Path(isolated_runtime.config.STATE_DIR) / "jarvis.db"
    )

    assert result["archived"]["runtime_development_focuses"] == 1
    assert result["archived"]["runtime_goal_signals"] == 1
    assert result["archived"]["runtime_reflection_signals"] == 1
    assert result["archived"]["runtime_dream_hypothesis_signals"] == 1
    assert result["archived"]["runtime_witness_signals"] == 1

    conn = sqlite3.connect(Path(isolated_runtime.config.STATE_DIR) / "jarvis.db")
    archived = conn.execute("SELECT COUNT(*) FROM signal_archive").fetchone()[0]
    assert archived >= 5


def test_runtime_development_focus_ignores_noisy_private_state(isolated_runtime) -> None:
    db = isolated_runtime.db
    now = datetime.now(UTC).isoformat()
    db.record_private_development_state(
        state_id=f"state-{uuid4().hex}",
        source="test",
        retained_pattern="Det virker værd at holde fast i det, der hjalp omkring det var fanme godt formuleret! jeg er helt enig.",
        preferred_direction="reinforce-retain",
        recurring_tension="",
        identity_thread="det var fanme godt formuleret! jeg er helt enig",
        confidence="high",
        created_at=now,
        updated_at=now,
    )

    tracking = importlib.import_module("core.services.development_focus_tracking")
    tracking = importlib.reload(tracking)

    result = tracking.track_runtime_development_focuses_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
        user_message="hej",
    )

    assert result["created"] == 0
