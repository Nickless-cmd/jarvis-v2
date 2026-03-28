from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_chronicle_brief(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_brief(
        brief_id=f"chronicle-consolidation-brief-{uuid4().hex}",
        brief_type="consolidation-brief",
        canonical_key="chronicle-consolidation-brief:consolidation-brief:workspace-search",
        status=status,
        title="Chronicle brief: workspace search",
        summary="Bounded chronicle brief is holding workspace search as a small longer-horizon continuity candidate.",
        rationale="Validation chronicle brief runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="chronicle brief evidence",
        support_summary="Derived primarily from an existing bounded chronicle/consolidation signal. | chronicle brief anchor",
        status_reason="Validation bounded chronicle brief support.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_chronicle_proposal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_proposal(
        proposal_id=f"chronicle-consolidation-proposal-{uuid4().hex}",
        proposal_type="consolidation-proposal",
        canonical_key="chronicle-consolidation-proposal:consolidation-proposal:workspace-search",
        status=status,
        title="Chronicle proposal: workspace search",
        summary="Bounded chronicle proposal is holding workspace search as a small carry-forward proposal.",
        rationale="Validation chronicle proposal runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="chronicle proposal evidence",
        support_summary="Derived from bounded chronicle brief support. | chronicle proposal anchor",
        status_reason="Validation bounded chronicle proposal support.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_meaning_significance_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_meaning_significance_signal(
        signal_id=f"meaning-significance-signal-{uuid4().hex}",
        signal_type="meaning-significance",
        canonical_key="meaning-significance:development-significance:workspace-search",
        status=status,
        title="Meaning significance support: workspace search",
        summary="Bounded meaning/significance runtime support is holding a small significance-weight.",
        rationale="Validation meaning/significance runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="meaning significance evidence",
        support_summary="Derived only from bounded chronicle continuity support, relation continuity support, and small promotion/contradiction/regulation sharpening. | grounding-mode=relation-continuity+chronicle-brief+chronicle-proposal | meaning significance anchor",
        status_reason="Validation bounded meaning/significance support and not canonical value or moral truth.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_relation_continuity_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_relation_continuity_signal(
        signal_id=f"relation-continuity-signal-{uuid4().hex}",
        signal_type="relation-continuity",
        canonical_key="relation-continuity:trustful-continuity:workspace-search",
        status=status,
        title="Relation continuity support: workspace search",
        summary="Bounded relation continuity runtime support is holding a small working-relationship continuity thread.",
        rationale="Validation relation continuity runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="relation continuity evidence",
        support_summary="Derived only from bounded relation-state support and chronicle continuity support. | relation continuity anchor",
        status_reason="Validation bounded relation continuity support and not canonical relationship truth.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_temperament_tendency_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_temperament_tendency_signal(
        signal_id=f"temperament-tendency-signal-{uuid4().hex}",
        signal_type="temperament-tendency",
        canonical_key="temperament-tendency:steadiness:workspace-search",
        status=status,
        title="Temperament support: workspace search",
        summary="Bounded temperament runtime support is holding a small character-tilt.",
        rationale="Validation temperament runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="temperament evidence",
        support_summary="Derived only from bounded meaning/significance support, relation continuity support, regulation or private-state substrate, and small contradiction or temporal-promotion sharpening. | grounding-mode=meaning-significance+relation-continuity+regulation | temperament anchor",
        status_reason="Validation bounded temperament support and not canonical personality truth.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_self_narrative_signal(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_narrative_continuity_signal(
        signal_id=f"self-narrative-continuity-signal-{uuid4().hex}",
        signal_type="self-narrative-continuity",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded self-narrative runtime support is holding a small becoming-line.",
        rationale="Validation self-narrative runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="self narrative evidence",
        support_summary="Derived only from bounded chronicle continuity support, meaning/significance support, temperament support, and relation continuity support. | grounding-mode=meaning-significance+temperament-tendency+relation-continuity+chronicle-brief+chronicle-proposal | narrative-direction=deepening | narrative-weight=high | self narrative anchor",
        status_reason="Validation bounded self-narrative continuity support and not canonical identity truth.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_self_narrative_continuity_stays_empty_without_relevant_grounding(isolated_runtime) -> None:
    tracking = isolated_runtime.self_narrative_continuity_signal_tracking
    db = isolated_runtime.db

    _insert_meaning_significance_signal(db, run_id="visible-run-1")

    result = tracking.track_runtime_self_narrative_continuity_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_self_narrative_continuity_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_self_narrative_continuity_forms_bounded_runtime_support_from_existing_substrate(isolated_runtime) -> None:
    tracking = isolated_runtime.self_narrative_continuity_signal_tracking
    db = isolated_runtime.db

    _insert_chronicle_brief(db, run_id="visible-run-2")
    _insert_chronicle_proposal(db, run_id="visible-run-2")
    _insert_meaning_significance_signal(db, run_id="visible-run-2")
    _insert_relation_continuity_signal(db, run_id="visible-run-2")
    _insert_temperament_tendency_signal(db, run_id="visible-run-2")

    result = tracking.track_runtime_self_narrative_continuity_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_self_narrative_continuity_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["signal_type"] == "self-narrative-continuity"
    assert item["narrative_state"] in {
        "becoming-steady",
        "becoming-watchful",
        "becoming-firm",
        "becoming-open",
        "becoming-coherent",
    }
    assert item["narrative_direction"] in {"steadying", "deepening", "guarding", "opening", "firming"}
    assert item["narrative_weight"] in {"low", "medium", "high"}
    assert item["narrative_confidence"] in {"low", "medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["canonical_identity_state"] == "not-canonical-identity-truth"
    assert "not canonical identity truth" in item["status_reason"].lower()
    assert "meaning-significance" in item["grounding_mode"]
    assert item["source_anchor"]


def test_self_narrative_continuity_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_narrative_continuity_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_self_narrative_signal(
        db,
        status="active",
        canonical_key="self-narrative-continuity:becoming-steady:workspace-search",
        title="Self-narrative support: workspace search",
    )
    _insert_self_narrative_signal(
        db,
        status="softening",
        canonical_key="self-narrative-continuity:becoming-watchful:visible-work",
        title="Self-narrative support: visible work",
    )
    _insert_self_narrative_signal(
        db,
        status="superseded",
        canonical_key="self-narrative-continuity:becoming-coherent:archive-focus",
        title="Self-narrative support: archive focus",
    )

    surface = tracking.build_runtime_self_narrative_continuity_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["self_narrative_continuity_signals"]
    runtime_shape = runtime["runtime_self_narrative_continuity_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_state",
        "current_direction",
        "current_weight",
        "current_confidence",
        "authority",
        "layer_role",
        "canonical_identity_state",
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
        "narrative_state",
        "narrative_direction",
        "narrative_weight",
        "narrative_summary",
        "narrative_confidence",
        "source_anchor",
        "authority",
        "layer_role",
        "canonical_identity_state",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["canonical_identity_state"] == "not-canonical-identity-truth"
