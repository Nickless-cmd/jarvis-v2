from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_witness_signal(db, *, run_id: str, status: str = "carried") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_witness_signal(
        signal_id=f"witness-signal-{uuid4().hex}",
        signal_type="witness",
        canonical_key="witness:settling:test-pattern",
        status=status,
        title="Witness signal for test",
        summary="A pattern appears to be settling around this area.",
        rationale="Validation witness signal",
        source_kind="runtime-observation",
        confidence="medium",
        evidence_summary="test evidence",
        support_summary="Derived from visible work.",
        status_reason="Validation witness",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_chronicle_brief(db, *, run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_brief(
        brief_id=f"chronicle-brief-{uuid4().hex}",
        brief_type="key-moment",
        canonical_key="chronicle-brief:test-pattern",
        status="briefed",
        title="Chronicle brief for test",
        summary="Key moment that shaped direction.",
        rationale="Validation chronicle brief",
        source_kind="runtime-observation",
        confidence="medium",
        evidence_summary="test evidence",
        support_summary="Derived from chronicle consolidation.",
        status_reason="Validation chronicle brief",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_self_narrative_signal(db, *, run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_narrative_continuity_signal(
        signal_id=f"self-narrative-signal-{uuid4().hex}",
        signal_type="self-narrative-continuity",
        canonical_key="self-narrative:continuity:test-pattern",
        status="active",
        title="Self-narrative continuity for test",
        summary="The narrative seems to be shifting toward this area.",
        rationale="Validation self-narrative",
        source_kind="runtime-observation",
        confidence="medium",
        evidence_summary="test evidence",
        support_summary="Derived from self-narrative continuity.",
        status_reason="Validation self-narrative",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_release_marker(
    db, *, run_id: str, release_state: str = "release-leaning"
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_release_marker_signal(
        signal_id=f"release-marker-{uuid4().hex}",
        signal_type="release-marker",
        canonical_key="release-marker:test-pattern",
        status="released",
        title="Release marker for test",
        summary="Something appears to be loosening around this area.",
        rationale="Validation release marker",
        source_kind="runtime-observation",
        confidence="low",
        evidence_summary="test evidence",
        support_summary=f"Derived from metabolism state. | release-state={release_state} | release-direction=loosening",
        status_reason="Validation release marker",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_diary_synthesis_surface_stays_empty_without_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.diary_synthesis_signal_tracking

    result = tracking.track_diary_synthesis_signals_for_visible_turn(
        session_id="test-session",
        run_id="missing-run",
    )
    surface = tracking.build_diary_synthesis_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_diary_synthesis_forms_bounded_reflection_from_witness(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.diary_synthesis_signal_tracking
    db = isolated_runtime.db

    _insert_witness_signal(db, run_id="diary-run-1", status="carried")
    result = tracking.track_diary_synthesis_signals_for_visible_turn(
        session_id="test-session",
        run_id="diary-run-1",
    )
    surface = tracking.build_diary_synthesis_signal_surface(limit=8)

    assert result["created"] == 1
    assert surface["active"] is True
    assert len(surface["items"]) == 1
    item = surface["items"][0]
    assert item["signal_type"] == "diary-synthesis"
    assert item["diary_state"] in {"settling", "emerging", "observing"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["status"] == "active"
    assert (
        "no canonical" in item["status_reason"].lower()
        or "without" in item["status_reason"].lower()
    )
    assert (
        "I notice" in item["support_summary"]
        or "patterns" in item["support_summary"].lower()
    )


def test_diary_synthesis_forms_reflection_from_multiple_sources(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.diary_synthesis_signal_tracking
    db = isolated_runtime.db

    _insert_witness_signal(db, run_id="diary-run-2", status="carried")
    _insert_chronicle_brief(db, run_id="diary-run-2")
    _insert_self_narrative_signal(db, run_id="diary-run-2")

    result = tracking.track_diary_synthesis_signals_for_visible_turn(
        session_id="test-session",
        run_id="diary-run-2",
    )
    surface = tracking.build_diary_synthesis_signal_surface(limit=8)

    assert result["created"] == 1
    assert surface["active"] is True
    item = surface["items"][0]
    assert item["signal_type"] == "diary-synthesis"
    assert (
        "witness" in item["source_anchor"].lower()
        or "chronicle" in item["source_anchor"].lower()
        or "self-narrative" in item["source_anchor"].lower()
    )
    assert item["authority"] == "non-authoritative"
    assert (
        "no" in item["status_reason"].lower()
        or "without" in item["status_reason"].lower()
    )


def test_diary_synthesis_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.diary_synthesis_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_witness_signal(db, run_id="diary-run-3", status="carried")

    tracking.track_diary_synthesis_signals_for_visible_turn(
        session_id="test-session",
        run_id="diary-run-3",
    )
    surface = tracking.build_diary_synthesis_signal_surface(limit=8)

    assert {
        "active_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_state",
        "current_confidence",
        "authority",
        "layer_role",
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
        "diary_state",
        "diary_weight",
        "diary_focus",
        "diary_confidence",
        "source_anchor",
        "authority",
        "layer_role",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["authority"] == "non-authoritative"
    assert surface["summary"]["layer_role"] == "runtime-support"


def test_diary_synthesis_becomes_release_aware_from_release_marker(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.diary_synthesis_signal_tracking
    db = isolated_runtime.db

    _insert_release_marker(
        db, run_id="diary-release-run-1", release_state="release-leaning"
    )

    result = tracking.track_diary_synthesis_signals_for_visible_turn(
        session_id="test-session",
        run_id="diary-release-run-1",
    )
    surface = tracking.build_diary_synthesis_signal_surface(limit=8)

    assert result["created"] == 1
    assert surface["active"] is True
    item = surface["items"][0]
    assert item["signal_type"] == "diary-synthesis"
    assert item["diary_state"] in {"releasing", "loosening"}
    summary_lower = item["summary"].lower()
    assert (
        "loosening" in summary_lower
        or "tightly held" in summary_lower
        or "easing" in summary_lower
        or "release" in summary_lower
    )
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert (
        "no" in item["status_reason"].lower()
        or "without" in item["status_reason"].lower()
        or "deletion" in item["status_reason"].lower()
    )


def test_diary_synthesis_reflective_release_not_deletion(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.diary_synthesis_signal_tracking
    db = isolated_runtime.db

    _insert_release_marker(
        db, run_id="diary-release-run-2", release_state="release-ready"
    )

    result = tracking.track_diary_synthesis_signals_for_visible_turn(
        session_id="test-session",
        run_id="diary-release-run-2",
    )
    surface = tracking.build_diary_synthesis_signal_surface(limit=8)

    item = surface["items"][0]
    summary_lower = item["summary"].lower()
    assert "deleted" not in summary_lower
    assert "forgotten" not in summary_lower
    assert "gone" not in summary_lower
    assert "i am" not in summary_lower
    assert (
        "release" not in summary_lower
        or "appear" in summary_lower
        or "seem" in summary_lower
    )


def test_diary_synthesis_uses_actual_signal_content(
    isolated_runtime,
) -> None:
    from core.services.diary_synthesis_signal_tracking import (
        _diary_summary,
        _extract_release_semantics,
    )
    from datetime import datetime, UTC

    metabolism_with_release = {
        "canonical_key": "metabolism:release:work-pattern",
        "title": "Work pattern release",
        "support_summary": "release-direction=loosening | release-state=release-leaning",
    }
    summary = _diary_summary(
        witness=None,
        chronicle=None,
        self_narrative=None,
        metabolism=metabolism_with_release,
        state="releasing",
    )
    summary_lower = summary.lower()
    assert (
        "work" in summary_lower
        or "pattern" in summary_lower
        or "this area" in summary_lower
    )
    assert "appear" in summary_lower
    assert (
        "easing" in summary_lower
        or "loosen" in summary_lower
        or "release" in summary_lower
    )


def test_diary_synthesis_release_vs_loosening_semantics(
    isolated_runtime,
) -> None:
    from core.services.diary_synthesis_signal_tracking import (
        _diary_summary,
    )

    metabolism_loosening = {
        "canonical_key": "metabolism:test:pattern",
        "title": "Test pattern",
        "support_summary": "release-direction=loosening | release-state=release-leaning",
    }
    summary_releasing = _diary_summary(
        witness=None,
        chronicle=None,
        self_narrative=None,
        metabolism=metabolism_loosening,
        state="releasing",
    )

    metabolism_fading = {
        "canonical_key": "metabolism:test:pattern",
        "title": "Test pattern",
        "support_summary": "release-direction=fading | release-state=release-emerging",
    }
    summary_loosening = _diary_summary(
        witness=None,
        chronicle=None,
        self_narrative=None,
        metabolism=metabolism_fading,
        state="loosening",
    )

    assert summary_releasing != summary_loosening
    assert (
        "easing" in summary_releasing.lower() or "release" in summary_releasing.lower()
    )
    assert (
        "fading" in summary_loosening.lower()
        or "less tightly" in summary_loosening.lower()
    )


def test_diary_synthesis_no_deletion_claims(
    isolated_runtime,
) -> None:
    from core.services.diary_synthesis_signal_tracking import (
        _diary_summary,
    )

    states_to_test = ["releasing", "loosening", "settling", "emerging"]
    for state in states_to_test:
        summary = _diary_summary(
            witness={"canonical_key": "witness:test:pattern"},
            chronicle={"canonical_key": "chronicle:test:pattern"},
            self_narrative={"canonical_key": "self-narrative:test:pattern"},
            metabolism={"canonical_key": "metabolism:test:pattern"},
            state=state,
        )
        summary_lower = summary.lower()
        assert "deleted" not in summary_lower
        assert "forgotten" not in summary_lower
        assert "gone" not in summary_lower
        assert "i deleted" not in summary_lower
        assert "i forgot" not in summary_lower


def test_diary_confidence_boosts_with_release_state(
    isolated_runtime,
) -> None:
    from core.services.diary_synthesis_signal_tracking import (
        _diary_confidence,
    )

    signal_low = {"confidence": "low", "support_summary": ""}
    confidence_low = _diary_confidence(signal_low)
    assert confidence_low == "low"

    signal_release_ready = {
        "confidence": "low",
        "support_summary": "release-state=release-ready",
    }
    confidence_boosted = _diary_confidence(signal_release_ready)
    assert confidence_boosted in {"medium", "high"}

    signal_release_leaning = {
        "confidence": "low",
        "support_summary": "release-state=release-leaning",
    }
    confidence_leaning = _diary_confidence(signal_release_leaning)
    assert confidence_leaning in {"medium", "high"}


def test_diary_weight_considers_release_strength(
    isolated_runtime,
) -> None:
    from core.services.diary_synthesis_signal_tracking import (
        _diary_weight,
    )

    signal_no_release = {"confidence": "low", "support_summary": ""}
    weight_no_release = _diary_weight(signal_no_release)
    assert weight_no_release == "low"

    signal_release_ready = {
        "confidence": "low",
        "support_summary": "release-state=release-ready",
    }
    weight_ready = _diary_weight(signal_release_ready)
    assert weight_ready in {"medium", "high"}


def test_diary_source_anchor_prioritizes_release(
    isolated_runtime,
) -> None:
    from core.services.diary_synthesis_signal_tracking import (
        _source_anchor_from_signals,
    )

    metabolism_release = {
        "support_summary": "release-state=release-ready",
        "status": "active",
    }
    witness = {"status": "carried", "confidence": "medium"}
    chronicle = {"status": "briefed"}

    anchor = _source_anchor_from_signals(
        witness=witness,
        chronicle=chronicle,
        self_narrative=None,
        metabolism=metabolism_release,
    )

    assert "release" in anchor.lower()

    metabolism_no_release = {
        "support_summary": "",
        "status": "active",
    }
    anchor_no_release = _source_anchor_from_signals(
        witness=witness,
        chronicle=chronicle,
        self_narrative=None,
        metabolism=metabolism_no_release,
    )

    assert "release" not in anchor_no_release.lower()
    assert "metabolism" in anchor_no_release.lower()
