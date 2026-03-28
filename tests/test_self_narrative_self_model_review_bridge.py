from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


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


def _insert_self_model_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_model_signal(
        signal_id=f"self-model-signal-{uuid4().hex}",
        signal_type="current-limitation",
        canonical_key="self-model:limitation:over-eager-execution",
        status=status,
        title="Current limitation: over-eager execution",
        summary="Jarvis is carrying a bounded self-assessment that over-eager execution remains a current limitation.",
        rationale="Validation self-model runtime support",
        source_kind="critic-supported",
        confidence="medium",
        evidence_summary="self model evidence",
        support_summary="Validation self-model support summary",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation self-model support status",
        run_id=run_id,
        session_id="test-session",
    )


def test_self_narrative_review_bridge_stays_empty_without_narrative_substrate(isolated_runtime) -> None:
    bridge = isolated_runtime.self_narrative_self_model_review_bridge
    db = isolated_runtime.db

    _insert_self_model_signal(db, run_id="visible-run-1")

    surface = bridge.build_runtime_self_narrative_self_model_review_bridge_surface(limit=8)
    runtime = isolated_runtime.mission_control.mc_runtime()

    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["patterns"] == []
    assert surface["summary"]["active_count"] == 0
    assert runtime["runtime_self_narrative_self_model_review_bridge"]["items"] == []


def test_self_narrative_review_bridge_forms_read_only_bridge_from_narrative_and_self_model(isolated_runtime) -> None:
    bridge = isolated_runtime.self_narrative_self_model_review_bridge
    db = isolated_runtime.db

    _insert_self_narrative_signal(
        db,
        status="active",
        canonical_key="self-narrative-continuity:becoming-steady:workspace-search",
        title="Self-narrative support: workspace search",
    )
    _insert_self_model_signal(db, run_id="test-run", status="active")

    surface = bridge.build_runtime_self_narrative_self_model_review_bridge_surface(limit=8)
    item = surface["items"][0]

    assert surface["active"] is True
    assert item["bridge_state"] in {"self-model-reviewable", "narrative-only-reviewable"}
    assert item["bridge_direction"] in {"steadying", "deepening", "guarding", "opening", "firming"}
    assert item["bridge_weight"] in {"low", "medium", "high"}
    assert item["bridge_confidence"] in {"low", "medium", "high"}
    assert item["pattern_type"] in {
        "steady-becoming-pattern",
        "watchful-becoming-pattern",
        "firming-pattern",
        "opening-pattern",
        "deepening-pattern",
        "coherent-review-pattern",
    }
    assert item["pattern_direction"] in {"steadying", "deepening", "guarding", "opening", "firming"}
    assert item["pattern_weight"] in {"low", "medium", "high"}
    assert item["pattern_confidence"] in {"low", "medium", "high"}
    assert item["review_state"] in {"narrative-and-self-model-visible", "narrative-awaiting-self-model-context"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["review_mode"] == "read-only-review-support"
    assert item["proposal_state"] == "not-selfhood-proposal"
    assert item["canonical_identity_state"] == "not-canonical-identity-truth"
    assert "read-only" in item["status_reason"].lower()
    assert "not a selfhood proposal" in item["status_reason"].lower()


def test_self_narrative_review_bridge_surfaces_in_mc_without_proposal_side_effects(isolated_runtime) -> None:
    bridge = isolated_runtime.self_narrative_self_model_review_bridge
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    _insert_self_narrative_signal(
        db,
        status="active",
        canonical_key="self-narrative-continuity:becoming-watchful:workspace-search",
        title="Self-narrative support: workspace search",
    )

    surface = bridge.build_runtime_self_narrative_self_model_review_bridge_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()

    assert {
        "active_count",
        "softening_count",
        "pattern_count",
        "current_bridge",
        "current_pattern",
        "current_status",
        "current_state",
        "current_direction",
        "current_weight",
        "current_review_state",
        "current_confidence",
        "authority",
        "layer_role",
        "review_mode",
        "proposal_state",
        "canonical_identity_state",
    }.issubset(surface["summary"].keys())
    assert {
        "bridge_id",
        "signal_id",
        "status",
        "title",
        "bridge_state",
        "bridge_direction",
        "bridge_weight",
        "bridge_summary",
        "bridge_confidence",
        "pattern_type",
        "pattern_direction",
        "pattern_weight",
        "pattern_summary",
        "pattern_confidence",
        "source_anchor",
        "review_state",
        "authority",
        "layer_role",
        "review_mode",
        "proposal_state",
        "canonical_identity_state",
    }.issubset(surface["items"][0].keys())
    assert surface["patterns"][0]["pattern_summary"]
    assert jarvis["development"]["self_narrative_self_model_review_bridge"]["summary"]["proposal_state"] == "not-selfhood-proposal"
    assert runtime["runtime_self_narrative_self_model_review_bridge"]["summary"]["review_mode"] == "read-only-review-support"
    assert jarvis["development"]["selfhood_proposals"]["summary"]["active_count"] == 0
