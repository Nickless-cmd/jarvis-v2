from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4


def _insert_focus(db, *, canonical_key: str, status: str = "active", minutes_ago: int = 0, run_id: str = "test-run", title: str = "Development focus: Danish concise calibration") -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_development_focus(
        focus_id=f"focus-{uuid4().hex}",
        focus_type="communication-calibration",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Active focus for Danish concise calibration",
        rationale="Validation focus",
        source_kind="repeated-user-correction",
        confidence="high",
        evidence_summary="focus evidence",
        support_summary="focus support",
        support_count=2,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation focus status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_critic(db, *, canonical_key: str, status: str, minutes_ago: int = 0, run_id: str = "test-run") -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_reflective_critic(
        critic_id=f"critic-{uuid4().hex}",
        critic_type="development-focus-mismatch",
        canonical_key=canonical_key,
        status=status,
        title="Active focus is not landing yet: Danish concise calibration",
        summary="Repeated correction still conflicts with the active focus.",
        rationale="Validation critic",
        source_kind="focus-mismatch",
        confidence="high",
        evidence_summary="critic evidence",
        support_summary="critic support",
        support_count=2,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation critic status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_goal(db, *, canonical_key: str, status: str, minutes_ago: int = 0, run_id: str = "test-run") -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_goal_signal(
        goal_id=f"goal-{uuid4().hex}",
        goal_type="development-direction",
        canonical_key=canonical_key,
        status=status,
        title="Current direction: Danish concise calibration",
        summary="Current direction: Danish concise calibration",
        rationale="Validation goal",
        source_kind="critic-backed" if status == "blocked" else "focus-derived",
        confidence="high",
        evidence_summary="goal evidence",
        support_summary="goal support",
        support_count=2,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation goal status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_temporal_recurrence(db, *, canonical_key: str, status: str, signal_type: str, minutes_ago: int = 0, run_id: str = "test-run") -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    title = (
        "Recurring tension: Danish concise calibration"
        if signal_type == "recurring-tension"
        else "Recurring direction: Danish concise calibration"
    )
    db.upsert_runtime_temporal_recurrence_signal(
        signal_id=f"recurrence-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary=title,
        rationale="Validation temporal recurrence",
        source_kind="multi-signal-runtime-derivation",
        confidence="high",
        evidence_summary="recurrence evidence",
        support_summary="recurrence support",
        support_count=3,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation temporal recurrence status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_open_loop(db, *, status: str, signal_type: str, canonical_key: str, run_id: str = "test-run") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_open_loop_signal(
        signal_id=f"open-loop-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Open loop row: {signal_type}",
        summary=f"Open loop summary: {signal_type}",
        rationale="Validation open loop",
        source_kind="derived-runtime-open-loop",
        confidence="medium",
        evidence_summary="open loop evidence",
        support_summary="open loop support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation open loop status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_self_model(db, *, canonical_key: str, status: str = "active", minutes_ago: int = 0, run_id: str = "test-run", title: str = "Current limitation: Danish concise calibration") -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_self_model_signal(
        signal_id=f"self-model-{uuid4().hex}",
        signal_type="current-limitation" if status == "active" else "improvement-edge",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary=title,
        rationale="Validation self-model",
        source_kind="critic-supported",
        confidence="high",
        evidence_summary="self-model evidence",
        support_summary="self-model support",
        support_count=2,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation self-model status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_world_model(db, *, canonical_key: str, status: str = "uncertain", minutes_ago: int = 0, run_id: str = "test-run") -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_world_model_signal(
        signal_id=f"world-model-{uuid4().hex}",
        signal_type="project-context-assumption",
        canonical_key=canonical_key,
        status=status,
        title="Current project context: building Jarvis together",
        summary="Current project context: building Jarvis together",
        rationale="Validation world-model",
        source_kind="session-evidence",
        confidence="medium",
        evidence_summary="world-model evidence",
        support_summary="world-model support",
        support_count=1,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation world-model status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_internal_opposition(db, *, status: str, signal_type: str, canonical_key: str, run_id: str = "test-run") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_internal_opposition_signal(
        signal_id=f"internal-opposition-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Internal opposition row: {signal_type}",
        summary=f"Internal opposition summary: {signal_type}",
        rationale="Validation internal opposition",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="internal opposition evidence",
        support_summary="internal opposition support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation internal opposition status",
        run_id=run_id,
        session_id="test-session",
    )


def test_internal_opposition_surface_stays_empty_without_relevant_pressure(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.internal_opposition_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=5,
    )

    tracking.track_runtime_internal_opposition_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_internal_opposition_signal_surface(limit=8)

    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["softening_count"] == 0


def test_internal_opposition_surface_forms_challenge_direction_for_open_loop_under_pressure(isolated_runtime) -> None:
    db = isolated_runtime.db
    open_loop_tracking = isolated_runtime.open_loop_tracking
    tracking = isolated_runtime.internal_opposition_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=30,
    )
    _insert_critic(
        db,
        canonical_key="reflective-critic:mismatch:development-focus:communication:danish-concise-calibration",
        status="active",
        minutes_ago=20,
    )
    _insert_goal(
        db,
        canonical_key="goal-signal:danish-concise-calibration",
        status="blocked",
        minutes_ago=15,
    )
    _insert_temporal_recurrence(
        db,
        canonical_key="temporal-recurrence:recurring-tension:danish-concise-calibration",
        status="active",
        signal_type="recurring-tension",
        minutes_ago=10,
    )

    open_loop_tracking.track_runtime_open_loop_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    tracking.track_runtime_internal_opposition_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_internal_opposition_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["current_status"] == "active"
    assert surface["items"][0]["signal_type"] == "challenge-direction"
    assert surface["items"][0]["status"] == "active"
    assert surface["items"][0]["canonical_key"] == "internal-opposition:challenge-direction:test-run"


def test_internal_opposition_surface_forms_challenge_calibration_for_self_model_pressure(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.internal_opposition_tracking

    _insert_goal(
        db,
        canonical_key="goal-signal:danish-concise-calibration",
        status="active",
        minutes_ago=20,
    )
    _insert_self_model(
        db,
        canonical_key="self-model:limitation:danish-concise-calibration",
        status="active",
        minutes_ago=10,
    )
    _insert_open_loop(
        db,
        status="open",
        signal_type="open-loop",
        canonical_key="open-loop:open-loop:danish-concise-calibration",
    )

    tracking.track_runtime_internal_opposition_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_internal_opposition_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 1
    assert surface["items"][0]["signal_type"] == "challenge-calibration"
    assert surface["items"][0]["status"] == "active"
    assert surface["items"][0]["canonical_key"] == "internal-opposition:challenge-calibration:test-run"


def test_begge_lag_naar_frem_til_prompt_linjen_ikke_kun_fokus(isolated_runtime) -> None:
    """Den ægte sidste meter for oppositionens INDHOLD.

    Målt 4/11-2026: ``current_signal`` bygges af ``title`` alene
    (``signal_tracking_framework.py:509``), og prompt-linjen læser
    ``current_signal``. Før rettelsen bar titlen kun fokus-laget, så den linje
    Jarvis læste som «indsigelse» var hans eget fokus gentaget — selvmodellen,
    den sjældne halvdel af betingelsen (36 af 632 kørsler), stod ingen steder.
    """
    db = isolated_runtime.db
    tracking = isolated_runtime.internal_opposition_tracking

    unik_fokus = "UNIKTFOKUS bygger oppositionens anden halvdel"
    unik_selv = "UNIKSELVMODEL tillid til debugging 63 procent"

    _insert_focus(
        db,
        canonical_key="focus:bearing:danish-concise-calibration",
        title=unik_fokus,
    )
    _insert_self_model(
        db,
        canonical_key="self-model:limitation:danish-concise-calibration",
        title=unik_selv,
    )

    tracking.track_runtime_internal_opposition_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_internal_opposition_signal_surface(limit=8)

    assert surface["active"] is True
    item = surface["items"][0]
    assert item["signal_type"] == "challenge-calibration"

    # 1) signalets titel bærer BEGGE lag
    assert unik_fokus in item["title"], "fokus-laget mangler i titlen"
    assert unik_selv in item["title"], (
        "selvmodellen mangler i titlen — og titlen er det ENESTE der når prompten"
    )

    # 2) og dermed også den samlede prompt-linje
    current = surface["summary"]["current_signal"]
    assert unik_fokus in current
    assert unik_selv in current, (
        "prompt-linjen gentager kun fokus — indsigelsen bærer intet andet lag"
    )


def test_internal_opposition_surface_forms_challenge_world_view_for_uncertain_context_with_live_direction(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.internal_opposition_tracking

    _insert_goal(
        db,
        canonical_key="goal-signal:danish-concise-calibration",
        status="blocked",
        minutes_ago=10,
    )
    _insert_world_model(
        db,
        canonical_key="world-model:project-context:building-jarvis-together",
        status="uncertain",
        minutes_ago=5,
    )

    tracking.track_runtime_internal_opposition_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_internal_opposition_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["softening_count"] == 1
    assert surface["items"][0]["signal_type"] == "challenge-world-view"
    assert surface["items"][0]["status"] == "softening"
    assert surface["items"][0]["canonical_key"] == "internal-opposition:challenge-world-view:world:building-jarvis-together"


def test_internal_opposition_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.internal_opposition_tracking
    mission_control = isolated_runtime.mission_control

    _insert_internal_opposition(
        db,
        status="active",
        signal_type="challenge-direction",
        canonical_key="internal-opposition:challenge-direction:danish-concise-calibration",
    )
    _insert_internal_opposition(
        db,
        status="softening",
        signal_type="challenge-calibration",
        canonical_key="internal-opposition:challenge-calibration:workspace-boundary",
    )
    _insert_internal_opposition(
        db,
        status="stale",
        signal_type="challenge-world-view",
        canonical_key="internal-opposition:challenge-world-view:world:building-jarvis-together",
    )
    _insert_internal_opposition(
        db,
        status="superseded",
        signal_type="challenge-direction",
        canonical_key="internal-opposition:challenge-direction:older-thread",
    )

    surface = tracking.build_runtime_internal_opposition_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["internal_opposition_signals"]
    runtime_shape = runtime["runtime_internal_opposition_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
    }.issubset(surface["summary"].keys())
    assert {
        "signal_id",
        "signal_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "confidence",
        "updated_at",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"active", "softening", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"active", "softening", "stale"}


# ── Domænet er KØRSLEN (målt 4/11-2026) ─────────────────────────────────────
# Lagene taler ikke samme sprog: `focus` er en sætning, `goal` en slug,
# `critic` en type. Nøgle-parsing gav `critic ∩ alt = 0`. Kørslen er den ene
# dimension alle lag bærer — og den oppositionen faktisk handler om.


def test_to_lag_i_samme_koersel_danner_opposition(isolated_runtime) -> None:
    """Fokus + selv-model i SAMME kørsel er nok til en kalibrerings-indsigelse."""
    db = isolated_runtime.db
    tracking = isolated_runtime.internal_opposition_tracking

    _insert_focus(
        db,
        canonical_key="focus:bearing:helt-andet-emne",
        status="active",
        minutes_ago=10,
        run_id="samme-koersel",
    )
    _insert_self_model(
        db,
        canonical_key="self-model:domain:fejlhaandtering",
        status="active",
        minutes_ago=5,
        run_id="samme-koersel",
    )

    tracking.track_runtime_internal_opposition_signals_for_visible_turn(
        session_id="test-session",
        run_id="samme-koersel",
    )
    surface = tracking.build_runtime_internal_opposition_signal_surface(limit=8)

    assert surface["active"] is True
    keys = [item["canonical_key"] for item in surface["items"]]
    assert "internal-opposition:challenge-calibration:samme-koersel" in keys


def test_to_lag_i_forskellige_koersler_danner_ikke_opposition(isolated_runtime) -> None:
    """Emnet er underordnet: uden fælles kørsel er der ingen kobling."""
    db = isolated_runtime.db
    tracking = isolated_runtime.internal_opposition_tracking

    _insert_focus(
        db,
        canonical_key="focus:bearing:helt-andet-emne",
        status="active",
        minutes_ago=10,
        run_id="koersel-a",
    )
    _insert_self_model(
        db,
        canonical_key="self-model:domain:fejlhaandtering",
        status="active",
        minutes_ago=5,
        run_id="koersel-b",
    )

    tracking.track_runtime_internal_opposition_signals_for_visible_turn(
        session_id="test-session",
        run_id="tredje-koersel",
    )
    surface = tracking.build_runtime_internal_opposition_signal_surface(limit=8)

    assert surface["active"] is False
