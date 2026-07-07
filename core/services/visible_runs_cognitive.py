"""Per-turn cognitive/candidate tracking-pipeline for visible runs.

Boy Scout-udtrækning (2026-07-07): udskilt fra ``core/services/visible_runs.py``.
Ren KODE-FLYTNING — ingen logik-ændring. Funktionerne re-eksporteres tilbage til
``visible_runs`` i bunden af den fil, så bare kald i ``_stream_visible_run`` +
test-monkeypatches virker.

KRITISK (facade-seam): ``_track_runtime_candidates`` kalder ~61 tracking-funktioner
der er TOP-LEVEL importeret i ``visible_runs``. Tests patcher dem via
``visible_runs.track_xxx``. Derfor refereres de her som ``_vr.track_xxx(...)`` (IKKE
bare navne) så patchen ses på kald-tidspunkt. Lokalt importerede navne
(``observe_hub``, ``extract_prediction_language`` osv.) og ``_track_step_failed``
(bor her) kaldes uændret bart.
"""

from __future__ import annotations

import logging

import core.services.visible_runs as _vr

logger = logging.getLogger(__name__)


def _track_step_failed() -> None:
    """En tracker i _track_runtime_candidates fejlede.

    FØR (kaskade-bug, 2026-06-22): hver tracker-blok afsluttede med `except: return`
    — et `return` forlod HELE funktionen, så ALLE downstream-trackers (self_review-
    kaskaden, memory-promotion, proactive-gates...) blev sprunget over for den tur,
    USYNLIGT. Én fejlende mellem-led dræbte resten.

    NU (Review/Memory/Proactivity fælles fejl-catcher): log med traceback (stakken
    identificerer den fejlende tracker) + central-trace, og FORTSÆT til næste tracker.
    Best-effort: kaster aldrig.
    """
    logger.warning(
        "_track_runtime_candidates: en tracker fejlede — fortsætter med resten",
        exc_info=True,
    )
    try:
        from core.services.central_core import central as _central_track
        _central_track().observe({
            "cluster": "review", "nerve": "candidate_tracker",
            "kind": "tracker_error",
        })
    except Exception:
        pass


def _track_runtime_candidates(run: "_vr.VisibleRun", assistant_text: str) -> None:
    if not run.session_id:
        return
    # LivingNeuron HUB 4: den 106-kald per-tur tracking-pipeline (største enkelt-blindzone) synlig for
    # Centralen egress-frit — ét observe gør hele per-tur-produktions-planet legibelt uden at røre de 106.
    try:
        from core.services.central_private_observe import observe_hub
        observe_hub("visible_turn_tracking", meta={"session": bool(run.session_id)})
    except Exception:
        pass
    try:
        _vr.track_runtime_contract_candidates_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
            assistant_message=assistant_text,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_development_focuses_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_reflective_critics_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_world_model_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        _track_step_failed()
    # World Model loop Phase 1 (2026-05-12): scan Jarvis' OWN response
    # (not the user message) for prediction/resolution language and
    # persist nudges. Jarvis sees them in next session's awareness.
    try:
        from core.services.world_model_signal_tracking import (
            extract_prediction_language,
            extract_resolution_language,
            record_prediction_nudge,
            record_resolution_nudge,
        )
        for m in extract_prediction_language(assistant_text or ""):
            record_prediction_nudge(
                session_id=run.session_id,
                run_id=run.run_id,
                matched_phrase=m["matched_phrase"],
                context_excerpt=m["context_excerpt"],
            )
            # World Model Phase 2 (2026-05-13): also pass to cheap-lane for
            # structured extraction. Records real prediction if cheap-lane
            # confirms it's falsifiable. Rate-limited to 15/day.
            try:
                from core.services.world_model_auto_extraction import (
                    auto_extract_and_record,
                )
                auto_extract_and_record(
                    matched_phrase=m["matched_phrase"],
                    context_excerpt=m["context_excerpt"],
                    session_id=run.session_id,
                )
            except Exception:
                pass
        for m in extract_resolution_language(assistant_text or ""):
            record_resolution_nudge(
                session_id=run.session_id,
                run_id=run.run_id,
                matched_phrase=m["matched_phrase"],
                context_excerpt=m["context_excerpt"],
                candidate_prediction_id="",
            )
    except Exception:
        # Never block downstream candidate tracking on scanner failures.
        pass
    try:
        _vr.track_runtime_self_model_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_goal_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_awareness_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_reflection_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_temporal_recurrence_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_witness_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_internal_opposition_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_self_review_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_self_review_records_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_self_review_runs_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_self_review_outcomes_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_self_review_cadence_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_dream_hypothesis_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_dream_adoption_candidates_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_dream_influence_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_self_authored_prompt_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_user_understanding_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_remembered_fact_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_private_inner_note_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_private_initiative_tension_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_private_inner_interplay_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_private_state_snapshots_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_diary_synthesis_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_private_temporal_curiosity_states_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_executive_contradiction_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_inner_visible_support_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_regulation_homeostasis_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_open_loop_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_relation_state_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_private_temporal_promotion_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_chronicle_consolidation_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_chronicle_consolidation_briefs_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_relation_continuity_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_chronicle_consolidation_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_meaning_significance_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_temperament_tendency_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_self_narrative_continuity_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_metabolism_state_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_release_marker_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_consolidation_target_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_selective_forgetting_candidates_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_attachment_topology_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_loyalty_gradient_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_contract_candidates_from_chronicle_consolidation_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_contract_candidates_from_self_authored_prompt_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_user_md_update_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_memory_md_update_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.auto_apply_safe_memory_md_candidates_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.auto_apply_safe_user_md_candidates_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_selfhood_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_open_loop_closure_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_autonomy_pressure_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_proactive_loop_lifecycle_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
    try:
        _vr.track_runtime_proactive_question_gates_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        _track_step_failed()
