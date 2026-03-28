from __future__ import annotations

from datetime import UTC, datetime


def test_private_lane_decontamination_stops_visible_reply_text_from_carrying_forward(
    isolated_runtime,
) -> None:
    from core.memory.private_layer_pipeline import write_private_terminal_layers

    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control
    visible_text = (
        "I investigated the endpoint failure, mapped the stack trace, and prepared "
        "a visible assistant reply with next steps."
    )
    finished_at = datetime.now(UTC).isoformat()

    write_private_terminal_layers(
        run_id="visible-run-private-lane",
        work_id="visible-work-private-lane",
        status="completed",
        started_at=finished_at,
        finished_at=finished_at,
        user_message_preview="Please inspect the failing endpoint and explain the issue.",
        work_preview=visible_text,
        capability_id="workspace-search",
    )

    growth_note = db.recent_private_growth_notes(limit=1)[0]
    reflective_selection = db.recent_private_reflective_selections(limit=1)[0]
    promotion_signal = db.get_private_temporal_promotion_signal()
    promotion_decision = db.get_private_promotion_decision()
    retained_record = db.get_private_retained_memory_record()
    jarvis = mission_control.mc_jarvis()

    assert visible_text not in str(growth_note.get("helpful_signal") or "")
    assert visible_text not in str(growth_note.get("lesson") or "")
    assert visible_text not in str(reflective_selection.get("reinforce") or "")
    assert visible_text not in str(promotion_signal.get("promotion_target") or "")
    assert visible_text not in str(promotion_decision.get("promotion_target") or "")
    assert visible_text not in str(retained_record.get("retained_value") or "")

    assert "workspace search" in str(growth_note.get("helpful_signal") or "").lower()
    assert "private-runtime-grounded" in str(growth_note.get("source") or "")
    assert "private-runtime-grounded" in str(reflective_selection.get("source") or "")
    assert "private-runtime-grounded" in str(promotion_signal.get("source") or "")
    assert "private-runtime-grounded" in str(promotion_decision.get("source") or "")
    assert "private-runtime-grounded" in str(retained_record.get("source") or "")

    reflective_surface = jarvis["development"]["reflective_selection"]
    promotion_surface = jarvis["continuity"]["promotion_signal"]
    decision_surface = jarvis["continuity"]["promotion_decision"]
    retained_projection = jarvis["memory"]["retained_projection"]
    retained_record_surface = jarvis["memory"]["retained_record"]

    assert (
        reflective_surface["summary"]["current_source_state"]
        == "private-runtime-grounded"
    )
    assert (
        promotion_surface["summary"]["current_contamination_state"]
        == "decontaminated-from-visible-reply"
    )
    assert (
        decision_surface["summary"]["current_source_state"]
        == "private-runtime-grounded"
    )
    assert (
        retained_projection["private_lane_source_state"]
        == "private-runtime-grounded"
    )
    assert (
        retained_projection["contamination_state"]
        == "decontaminated-from-visible-reply"
    )
    assert (
        retained_record_surface["summary"]["current_contamination_state"]
        == "decontaminated-from-visible-reply"
    )
