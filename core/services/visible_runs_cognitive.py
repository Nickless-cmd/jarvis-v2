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


def _run_visible_cadence_updates(
    *,
    run_id: str,
    session_id: str | None,
    user_message: str,
    assistant_response: str,
    outcome_status: str,
    user_mood: str,
) -> None:
    """Run post-turn cadence producers without letting them block finalization."""
    try:
        from core.services.cadence_producers import (
            detect_decision_in_message,
            produce_signals_from_run,
        )

        produce_signals_from_run(
            run_id=run_id,
            session_id=session_id,
            user_message=user_message,
            assistant_response=assistant_response,
            outcome_status=outcome_status,
            user_mood=user_mood,
        )
        detect_decision_in_message(
            user_message=user_message,
            assistant_response=assistant_response,
            run_id=run_id,
        )
    except Exception:
        pass


def _legacy_regex_detectors_enabled() -> bool:
    """Er de gamle ordmønster-detektorer stadig tændt? (default: nej)

    Slukket 2026-09-04 (lærings-sløjfe, blok B). De skrev hver tur og lærte
    intet: 1.756 forkastede USER.md-kandidater mod 9 anvendte, og 19.145
    forkastede MEMORY.md-kandidater med Bjørns egen besked ordret som titel.
    Fail-safe: enhver fejl i opslaget → slukket (den nye sløjfe kører alligevel).
    """
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "legacy_regex_learning_detectors_enabled", False))
    except Exception:
        return False


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
    # ── KRYDS-LAG-FAMILIEN: STRUKTURELT DØD (målt 4/11-2026) ─────────────────
    # De fire trackers nedenfor — temporal_recurrence, internal_opposition,
    # executive_contradiction og open_loop — kaldes hver tur og skriver ALDRIG
    # noget. Målt i den levende base: alle fire _extract_*-funktioner returnerer
    # 0 kandidater, og tabellerne har 0 rækker nogensinde (internal_opposition
    # har 1 række fra 15. maj, superseded).
    #
    # ÅRSAGEN ER IKKE EN FEJL DER KAN RETTES. De kræver alle et domæne der deles
    # på tværs af lag, og hvert lag taler sit eget nøgle-format:
    #   focus   → focus:bearing:<hel sætning>      (hvert fokus sit eget domæne)
    #   goal    → goal-signal:<slug>
    #   critic  → critic:<type>                    (en TYPE, ikke et emne)
    #   self    → self-model:domain:<emne>         (det eneste ægte domæne)
    #   loop    → findes ikke (0 rækker)
    # Ingen af dem kan mødes. Målt: focus∩goal = 2 domæner ud af 3.118, og
    # critic deler nul domæner med noget lag.
    #
    # FRISTELSE DER IKKE VIRKER: at matche fokus-nøglens ord mod beskeden
    # generisk. Målt på 400 historiske correction-critics gav det 41 "matches"
    # — alle på funktionsord som «skal», «ikke», «hvordan». Det er falske
    # domæner, og et falsk domæne er værre end et tomt.
    #
    # HVAD DER SKAL BYGGES FØR DE KAN FYRE: en fælles domæne-dimension — en
    # kolonne, et vokabular eller en mapping — der siger hvad «samme emne»
    # betyder på tværs af de fem lag. Det er en designbeslutning om hvad et
    # domæne ER i systemet, ikke en konfigurationsrettelse. Indtil den findes,
    # er tomme signaler den korrekte adfærd — men de skal stå her som tomme
    # med vilje, ikke som en mekanisme nogen tror virker.
    #
    # Læserne (11 for executive_contradiction alene) tåler tomme data og gør
    # det allerede. Der er derfor intet at rette i læse-fladen.
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
    # 14/11-2026: en kørsel der aldrig nåede modellen har intet at selv-reviewe.
    # Self-review- og indre-note-trackerne skrev alligevel «Review needed for
    # run …» for en kørsel hvis tekst var 0 tegn.
    from core.services.visible_run_trace import run_never_reached_model
    _no_model_call = run_never_reached_model(run.run_id, assistant_text)
    if not _no_model_call:
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
    # ── REGEX-DETEKTORER (slukket 2026-09-04, lærings-sløjfe blok B) ────────
    # Målt over 30 dage: user_md-forslagene gav 1.756 forkastede kandidater og
    # 9 anvendte ("User appears to prefer plain, grounded replies" ni gange);
    # memory_md-forslagene gav 19.145 forkastede, med Bjørns egen besked ordret
    # som titel ("MEMORY.md update proposal: Kan Du Ikk Lige Finde Ud Af Hvilke
    # Ip Vores"). Fire faste ordmønstre kan ikke lære nogen at kende. Sløjfen i
    # end_of_run_memory_consolidation gør arbejdet nu. Tænd igen med
    # settings.legacy_regex_learning_detectors_enabled = true.
    if _legacy_regex_detectors_enabled():
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
    if not _no_model_call:
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
    if _legacy_regex_detectors_enabled():
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
    if _legacy_regex_detectors_enabled():
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
