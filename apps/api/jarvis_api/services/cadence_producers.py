"""Cadence Producers — central orchestration for waking up dead MC fields.

The problem: many tracker services have track_*_for_visible_turn() functions
that depend on chains of pre-existing signals. If the chain has no head,
nothing fires. This module bypasses the chain and produces baseline data
directly from accumulated cognitive state.

Run after each visible run + on heartbeat ticks.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    upsert_runtime_self_model_signal,
    upsert_runtime_reflective_critic,
    upsert_runtime_reflection_signal,
    upsert_runtime_self_review_record,
    upsert_runtime_self_review_run,
    upsert_runtime_self_review_outcome,
    upsert_runtime_self_review_signal,
    upsert_runtime_witness_signal,
    upsert_runtime_development_focus,
    upsert_runtime_world_model_signal,
    upsert_runtime_self_narrative_continuity_signal,
    upsert_runtime_metabolism_state_signal,
    upsert_runtime_release_marker_signal,
    upsert_runtime_chronicle_consolidation_brief,
    upsert_runtime_dream_hypothesis_signal,
    get_latest_cognitive_personality_vector,
    get_latest_cognitive_user_emotional_state,
    get_latest_cognitive_relationship_texture,
    list_cognitive_experiential_memories,
    list_cognitive_user_emotional_states,
    list_cognitive_habit_patterns,
    list_cognitive_friction_signals,
    recent_visible_runs,
)

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def produce_signals_from_run(
    *,
    run_id: str,
    session_id: str | None,
    user_message: str,
    assistant_response: str,
    outcome_status: str,
    user_mood: str = "neutral",
) -> dict[str, int]:
    """Fire all relevant signals after a visible run, bypassing chain dependencies."""
    counts = {
        "self_model": 0, "reflective_critic": 0, "reflection": 0,
        "self_review_record": 0, "self_review_run": 0, "witness": 0,
        "development_focus": 0, "self_review_outcome": 0,
        "world_model": 0, "self_review_signal": 0, "conversation_rhythm": 0,
    }

    msg_lower = user_message.lower()
    was_corrected = any(m in msg_lower for m in (
        "nej", "forkert", "ikke det", "stadig samme", "prøv igen", "hold nu"
    ))

    # 1. Witness signal — always fire after visible run
    try:
        upsert_runtime_witness_signal(
            signal_id=f"wit-{uuid4().hex[:10]}",
            signal_type="visible_run_observed",
            canonical_key=f"witness:run:{run_id}",
            status="fresh",
            title=user_message[:80] or "visible run",
            summary=f"Observed: {user_message[:60]} → {outcome_status}",
            rationale="Observation of completed visible run for witness lifecycle",
            source_kind="visible_run",
            confidence="medium",
            evidence_summary=user_message[:200],
            support_summary=f"outcome={outcome_status}",
            support_count=1,
            session_count=1,
            run_id=run_id,
            session_id=str(session_id or ""),
            created_at=_now(),
            updated_at=_now(),
        )
        counts["witness"] += 1
    except Exception as exc:
        logger.debug("witness signal failed: %s", exc)

    # 2. Self-review record — always fire after run
    try:
        score = 0.7 if outcome_status in ("completed", "success") else 0.3
        upsert_runtime_self_review_record(
            record_id=f"srr-{uuid4().hex[:10]}",
            record_type="visible_run_review",
            canonical_key=f"self-review:record:{run_id}",
            status="active",
            title=f"Review of run {run_id[:12]}",
            summary=f"Run outcome: {outcome_status}, mood: {user_mood}",
            rationale="Post-run automated self-assessment",
            source_kind="visible_run",
            confidence="medium",
            evidence_summary=user_message[:200],
            support_summary=f"score={score}",
            support_count=1,
            session_count=1,
            run_id=run_id,
            session_id=str(session_id or ""),
            created_at=_now(),
            updated_at=_now(),
        )
        counts["self_review_record"] += 1
    except Exception as exc:
        logger.debug("self review record failed: %s", exc)

    # 3. Self-review run — track the review itself
    try:
        srrun_id = f"srrun-{uuid4().hex[:10]}"
        upsert_runtime_self_review_run(
            run_id=srrun_id,
            run_type="auto_post_run",
            canonical_key=f"self-review:run:{run_id}",
            status="completed",
            title=f"Auto self-review of {run_id[:12]}",
            summary=f"Outcome={outcome_status}",
            rationale="Auto-fired after visible run",
            source_kind="cadence_producer",
            confidence="medium",
            evidence_summary=f"mood={user_mood}",
            support_summary=outcome_status,
            support_count=1,
            session_count=1,
            record_run_id=run_id,
            session_id=str(session_id or ""),
            created_at=_now(),
            updated_at=_now(),
        )
        counts["self_review_run"] += 1
    except Exception as exc:
        logger.debug("self review run failed: %s", exc)

    # 4. Self-review outcome
    try:
        upsert_runtime_self_review_outcome(
            outcome_id=f"sro-{uuid4().hex[:10]}",
            outcome_type="post_run_outcome",
            canonical_key=f"self-review:outcome:{run_id}",
            status="active",
            title=f"Outcome: {outcome_status}",
            summary=f"Run {run_id[:12]} completed with {outcome_status}",
            rationale="Tracking outcome for self-review lifecycle",
            source_kind="visible_run",
            confidence="high",
            evidence_summary=user_message[:200],
            support_summary=f"mood={user_mood}",
            support_count=1,
            session_count=1,
            review_run_id=run_id,
            session_id=str(session_id or ""),
            created_at=_now(),
            updated_at=_now(),
        )
        counts["self_review_outcome"] += 1
    except Exception as exc:
        logger.debug("self review outcome failed: %s", exc)

    # 5. Reflective critic — fire on failure or correction
    if was_corrected or outcome_status in ("failed", "error"):
        try:
            critic_type = "user_correction" if was_corrected else "outcome_failure"
            upsert_runtime_reflective_critic(
                critic_id=f"crit-{uuid4().hex[:10]}",
                critic_type=critic_type,
                canonical_key=f"critic:{critic_type}:{run_id}",
                status="active",
                title=f"Critic: {critic_type}",
                summary=f"Should have verified before responding to: {user_message[:60]}",
                rationale="Auto-fired after correction or failure",
                source_kind="cadence_producer",
                confidence="medium",
                evidence_summary=user_message[:200],
                support_summary=f"outcome={outcome_status}, corrected={was_corrected}",
                support_count=1,
                session_count=1,
                run_id=run_id,
                session_id=str(session_id or ""),
                created_at=_now(),
                updated_at=_now(),
            )
            counts["reflective_critic"] += 1
        except Exception as exc:
            logger.debug("reflective critic failed: %s", exc)

    # 6. Reflection signal — meaningful runs
    if len(user_message) > 30:
        try:
            upsert_runtime_reflection_signal(
                signal_id=f"refl-{uuid4().hex[:10]}",
                signal_type="post_run_reflection",
                canonical_key=f"reflection:{run_id}",
                status="active",
                title=f"Reflected on: {user_message[:50]}",
                summary=f"Outcome={outcome_status}, mood={user_mood}",
                rationale="Meta-cognitive reflection after visible run",
                source_kind="cadence_producer",
                confidence="medium",
                evidence_summary=user_message[:200],
                support_summary=f"length={len(user_message)}",
                support_count=1,
                session_count=1,
                run_id=run_id,
                session_id=str(session_id or ""),
                created_at=_now(),
                updated_at=_now(),
            )
            counts["reflection"] += 1
        except Exception as exc:
            logger.debug("reflection signal failed: %s", exc)

    # 7. Self-model signal — fire from personality_vector confidence
    try:
        pv = get_latest_cognitive_personality_vector()
        if pv:
            confidence_by_domain = json.loads(str(pv.get("confidence_by_domain") or "{}"))
            # Pick lowest confidence domain as a "limitation" signal
            if confidence_by_domain:
                weak_domain = min(confidence_by_domain, key=confidence_by_domain.get)
                weak_conf = confidence_by_domain[weak_domain]
                upsert_runtime_self_model_signal(
                    signal_id=f"sm-{uuid4().hex[:10]}",
                    signal_type="confidence_baseline",
                    canonical_key=f"self-model:domain:{weak_domain}",
                    status="active",
                    title=f"Confidence in {weak_domain}: {weak_conf:.0%}",
                    summary=f"Personality vector v{pv.get('version', 0)} tracks confidence in {weak_domain}",
                    rationale="Auto-tracked from personality vector",
                    source_kind="personality_vector",
                    confidence="high",
                    evidence_summary=f"v{pv.get('version', 0)}",
                    support_summary=f"score={weak_conf:.2f}",
                    support_count=int(pv.get("version", 1)),
                    session_count=1,
                    run_id=run_id,
                    session_id=str(session_id or ""),
                    created_at=_now(),
                    updated_at=_now(),
                )
                counts["self_model"] += 1
    except Exception as exc:
        logger.debug("self model signal failed: %s", exc)

    # 8. Development focus — derive from current bearing
    try:
        pv = get_latest_cognitive_personality_vector()
        if pv:
            bearing = str(pv.get("current_bearing") or "")
            if bearing:
                upsert_runtime_development_focus(
                    focus_id=f"foc-{uuid4().hex[:10]}",
                    focus_type="current_bearing",
                    canonical_key=f"focus:bearing:{bearing[:30]}",
                    status="active",
                    title=bearing[:80],
                    summary=f"Current strategic focus: {bearing[:120]}",
                    rationale="Derived from personality vector bearing",
                    source_kind="personality_vector",
                    confidence="high",
                    evidence_summary=bearing[:200],
                    support_summary=f"v{pv.get('version', 0)}",
                    support_count=1,
                    session_count=1,
                    run_id=run_id,
                    session_id=str(session_id or ""),
                    created_at=_now(),
                    updated_at=_now(),
                )
                counts["development_focus"] += 1
    except Exception as exc:
        logger.debug("development focus failed: %s", exc)

    # 9. World model signal — derive from message context
    try:
        upsert_runtime_world_model_signal(
            signal_id=f"wm-{uuid4().hex[:10]}",
            signal_type="conversational_context",
            canonical_key=f"world-model:run:{run_id}",
            status="active",
            title=user_message[:80],
            summary=f"Context: {user_message[:120]}",
            rationale="Bounded situational context from visible turn",
            source_kind="visible_run",
            confidence="medium",
            evidence_summary=user_message[:200],
            support_summary=f"outcome={outcome_status}",
            support_count=1,
            session_count=1,
            run_id=run_id,
            session_id=str(session_id or ""),
            created_at=_now(),
            updated_at=_now(),
        )
        counts["world_model"] += 1
    except Exception as exc:
        logger.debug("world model signal failed: %s", exc)

    # 10. Self-review need signal (different from records — these are trigger signals)
    try:
        upsert_runtime_self_review_signal(
            signal_id=f"srs-{uuid4().hex[:10]}",
            signal_type="post_run_review_need",
            canonical_key=f"self-review-need:{run_id}",
            status="active",
            title=f"Review needed for run {run_id[:12]}",
            summary=f"Outcome: {outcome_status}, mood: {user_mood}",
            rationale="Auto-fired post-run for review tracking",
            source_kind="cadence_producer",
            confidence="medium",
            evidence_summary=user_message[:200],
            support_summary=f"outcome={outcome_status}",
            support_count=1,
            session_count=1,
            run_id=run_id,
            session_id=str(session_id or ""),
            created_at=_now(),
            updated_at=_now(),
        )
        counts["self_review_signal"] += 1
    except Exception as exc:
        logger.debug("self review signal failed: %s", exc)

    # 11. Conversation rhythm tracking
    try:
        from apps.api.jarvis_api.services.conversation_rhythm import track_conversation_rhythm
        was_corrected = any(m in msg_lower for m in (
            "nej", "forkert", "ikke det", "stadig samme", "prøv igen", "hold nu"
        ))
        track_conversation_rhythm(
            run_id=run_id,
            session_id=str(session_id or ""),
            turn_count=1,
            correction_count=1 if was_corrected else 0,
            avg_message_length=len(user_message),
            duration_minutes=1.0,
            outcome_status=outcome_status,
        )
        counts["conversation_rhythm"] += 1
    except Exception as exc:
        logger.debug("conversation rhythm failed: %s", exc)

    # 12. Update relationship texture (humor + trust + corrections)
    try:
        from apps.api.jarvis_api.services.relationship_texture import update_relationship_from_run
        update_relationship_from_run(
            run_id=run_id,
            user_message=user_message,
            assistant_response=assistant_response,
            outcome_status=outcome_status,
            turn_count=1,
        )
    except Exception as exc:
        logger.debug("relationship texture update failed: %s", exc)

    # 13a. Self-narrative continuity signal
    try:
        upsert_runtime_self_narrative_continuity_signal(
            signal_id=f"snc-{uuid4().hex[:10]}",
            signal_type="post_run_continuity",
            canonical_key=f"narrative-continuity:{run_id}",
            status="active",
            title=f"Continuity from run {run_id[:12]}",
            summary=f"Narrative thread continues with mood={user_mood}",
            rationale="Bounded narrative continuity tracking from visible turn",
            source_kind="visible_run",
            confidence="medium",
            evidence_summary=user_message[:200],
            support_summary=f"outcome={outcome_status}",
            support_count=1,
            session_count=1,
            run_id=run_id,
            session_id=str(session_id or ""),
            created_at=_now(),
            updated_at=_now(),
        )
    except Exception as exc:
        logger.debug("self narrative continuity failed: %s", exc)

    # 13b. Metabolism state signal
    try:
        upsert_runtime_metabolism_state_signal(
            signal_id=f"met-{uuid4().hex[:10]}",
            signal_type="post_run_metabolism",
            canonical_key=f"metabolism:{run_id}",
            status="active",
            title=f"Metabolism after run {run_id[:12]}",
            summary=f"Processing {outcome_status} outcome",
            rationale="Bounded metabolism tracking",
            source_kind="visible_run",
            confidence="medium",
            evidence_summary=f"mood={user_mood}",
            support_summary=outcome_status,
            support_count=1,
            session_count=1,
            run_id=run_id,
            session_id=str(session_id or ""),
            created_at=_now(),
            updated_at=_now(),
        )
    except Exception as exc:
        logger.debug("metabolism failed: %s", exc)

    # 13c. Release marker (only on completion)
    if outcome_status in ("completed", "success"):
        try:
            upsert_runtime_release_marker_signal(
                signal_id=f"rel-{uuid4().hex[:10]}",
                signal_type="completion_release",
                canonical_key=f"release:{run_id}",
                status="active",
                title=f"Release after {run_id[:12]}",
                summary=f"Completed: {user_message[:60]}",
                rationale="Release marker on successful completion",
                source_kind="visible_run",
                confidence="medium",
                evidence_summary=user_message[:200],
                support_summary="completed",
                support_count=1,
                session_count=1,
                run_id=run_id,
                session_id=str(session_id or ""),
                created_at=_now(),
                updated_at=_now(),
            )
        except Exception as exc:
            logger.debug("release marker failed: %s", exc)

    # 13d. Chronicle consolidation brief (periodic)
    try:
        upsert_runtime_chronicle_consolidation_brief(
            brief_id=f"brief-{uuid4().hex[:10]}",
            brief_type="post_run_brief",
            canonical_key=f"chronicle-brief:{run_id}",
            status="briefed",
            title=f"Brief: {user_message[:60]}",
            summary=f"Run brief: {outcome_status}, mood={user_mood}",
            rationale="Bounded chronicle consolidation brief from visible turn",
            source_kind="visible_run",
            confidence="medium",
            evidence_summary=user_message[:200],
            support_summary=f"outcome={outcome_status}",
            support_count=1,
            session_count=1,
            run_id=run_id,
            session_id=str(session_id or ""),
            created_at=_now(),
            updated_at=_now(),
        )
    except Exception as exc:
        logger.debug("chronicle brief failed: %s", exc)

    # 13e. Dream hypothesis (during dreaming/reflection phases or randomly)
    try:
        from apps.api.jarvis_api.services.living_heartbeat_cycle import determine_life_phase
        phase = determine_life_phase()
        if phase.get("phase") in ("dreaming", "reflection") or (run_id.endswith("0") or run_id.endswith("5")):
            upsert_runtime_dream_hypothesis_signal(
                signal_id=f"dh-{uuid4().hex[:10]}",
                signal_type="post_run_hypothesis",
                canonical_key=f"dream:{run_id}",
                status="active",
                title=f"Hypothesis from {user_message[:40]}",
                summary=f"What if {user_message[:80]} could be approached differently?",
                rationale="Bounded dream hypothesis from runtime support",
                source_kind="visible_run",
                confidence="low",
                evidence_summary=user_message[:200],
                support_summary=f"phase={phase.get('phase', '?')}",
                support_count=1,
                session_count=1,
                run_id=run_id,
                session_id=str(session_id or ""),
                created_at=_now(),
                updated_at=_now(),
            )
    except Exception as exc:
        logger.debug("dream hypothesis failed: %s", exc)

    # 13f. Diary synthesis (now that prerequisites exist)
    try:
        from apps.api.jarvis_api.services.diary_synthesis_signal_tracking import (
            track_diary_synthesis_signals_for_visible_turn,
        )
        track_diary_synthesis_signals_for_visible_turn(
            session_id=str(session_id or ""),
            run_id=run_id,
        )
    except Exception as exc:
        logger.debug("diary synthesis failed: %s", exc)

    # 14. Counterfactual auto-generation (broader triggers)
    try:
        from apps.api.jarvis_api.services.counterfactual_engine import generate_counterfactual
        if outcome_status in ("failed", "error"):
            generate_counterfactual(
                trigger_type="failed_run",
                anchor=user_message[:80],
                source="auto",
                confidence=0.5,
            )
        elif was_corrected:
            generate_counterfactual(
                trigger_type="correction",
                anchor=user_message[:80],
                source="auto",
                confidence=0.4,
            )
        elif outcome_status in ("completed", "success") and len(user_message) > 100:
            # Even successful long messages: speculate about alternatives
            generate_counterfactual(
                trigger_type="decision",
                anchor=user_message[:80],
                source="auto",
                confidence=0.3,
            )
    except Exception as exc:
        logger.debug("counterfactual failed: %s", exc)

    event_bus.publish("cognitive_state.cadence_producers_fired",
                     {"run_id": run_id, "counts": counts})
    return counts


def produce_emergent_signals_from_history() -> dict[str, int]:
    """Run the emergent signal daemon to scan timeline for patterns."""
    counts = {"emergent": 0, "candidates": 0}
    try:
        from apps.api.jarvis_api.services.emergent_signal_tracking import run_emergent_signal_daemon
        result = run_emergent_signal_daemon(trigger="cadence_producer")
        counts["emergent"] = int(result.get("active_count", 0))
        counts["candidates"] = int(result.get("created", 0)) + int(result.get("strengthened", 0))
        if counts["emergent"]:
            event_bus.publish("cognitive_state.emergent_signals_produced", counts)
    except Exception as exc:
        logger.debug("emergent signal daemon failed: %s", exc)
    return counts


def detect_decision_in_message(
    *, user_message: str, assistant_response: str, run_id: str,
) -> dict[str, object] | None:
    """Detect decisions in conversation and log them."""
    msg_lower = user_message.lower()
    decision_markers = [
        "vi vælger", "lad os bruge", "beslutningen er", "vi går med",
        "vi tager", "lad os", "skal vi", "i stedet for", "frem for",
        "vi bør", "decided", "let's use", "going with",
    ]
    if not any(m in msg_lower for m in decision_markers):
        return None
    try:
        from apps.api.jarvis_api.services.decision_log import record_decision
        # Find which marker triggered
        marker_found = next((m for m in decision_markers if m in msg_lower), "")
        idx = msg_lower.find(marker_found)
        context = user_message[max(0, idx - 30):idx + 100].strip()
        return record_decision(
            title=context[:80],
            context=user_message[:200],
            decision=context[:100],
            why=f"Detected via marker '{marker_found}' in conversation",
            options=[],
            refs=[run_id],
        )
    except Exception:
        return None


def run_adoption_pipelines() -> dict[str, int]:
    """Move things from candidate → adopted state."""
    counts = {"dreams_adopted": 0, "values_strengthened": 0, "memories_reinforced": 0}

    # 1. Dreams: confirmed dreams with high confidence → adoption
    try:
        from apps.api.jarvis_api.services.dream_carry_over import (
            _ACTIVE_DREAMS,
            promote_confirmed_dream_to_identity,
        )
        for dream in _ACTIVE_DREAMS:
            if dream.get("confirmed") and float(dream.get("confidence", 0)) > 0.7:
                result = promote_confirmed_dream_to_identity(dream["dream_id"])
                if result:
                    counts["dreams_adopted"] += 1
    except Exception as exc:
        logger.debug("dream adoption failed: %s", exc)

    # 2. Auto-apply safe contract candidates
    try:
        from core.identity.candidate_workflow import (
            auto_apply_safe_user_md_candidates,
            auto_apply_safe_memory_md_candidates,
        )
        user_result = auto_apply_safe_user_md_candidates()
        memory_result = auto_apply_safe_memory_md_candidates()
        counts["values_strengthened"] = (
            int(user_result.get("applied", 0)) + int(memory_result.get("applied", 0))
        )
    except Exception as exc:
        logger.debug("contract auto-apply failed: %s", exc)

    if counts["dreams_adopted"] or counts["values_strengthened"]:
        event_bus.publish("cognitive_state.adoption_pipelines_fired", counts)
    return counts


def sync_personality_to_self_model() -> dict[str, int]:
    """Bridge: sync personality_vector changes to self_model_signal."""
    counts = {"signals_created": 0}
    try:
        pv = get_latest_cognitive_personality_vector()
        if not pv:
            return counts
        confidence_by_domain = json.loads(str(pv.get("confidence_by_domain") or "{}"))
        strengths = json.loads(str(pv.get("strengths_discovered") or "[]"))
        mistakes = json.loads(str(pv.get("recurring_mistakes") or "[]"))

        # Fire one signal per strong area
        for strength in strengths[:3]:
            try:
                upsert_runtime_self_model_signal(
                    signal_id=f"sm-{uuid4().hex[:10]}",
                    signal_type="recognized_strength",
                    canonical_key=f"self-model:strength:{strength[:30]}",
                    status="active",
                    title=f"Strength: {strength[:60]}",
                    summary=str(strength)[:200],
                    rationale="From personality_vector strengths_discovered",
                    source_kind="personality_vector",
                    confidence="high",
                    evidence_summary=f"v{pv.get('version', 0)}",
                    support_summary="Discovered through experience",
                    support_count=int(pv.get("version", 1)),
                    session_count=1,
                    run_id="",
                    session_id="",
                    created_at=_now(),
                    updated_at=_now(),
                )
                counts["signals_created"] += 1
            except Exception:
                pass

        # And one per recurring mistake (as limitation)
        for mistake in mistakes[:3]:
            try:
                upsert_runtime_self_model_signal(
                    signal_id=f"sm-{uuid4().hex[:10]}",
                    signal_type="known_limitation",
                    canonical_key=f"self-model:limitation:{mistake[:30]}",
                    status="active",
                    title=f"Known limitation: {mistake[:60]}",
                    summary=str(mistake)[:200],
                    rationale="From personality_vector recurring_mistakes",
                    source_kind="personality_vector",
                    confidence="medium",
                    evidence_summary=f"v{pv.get('version', 0)}",
                    support_summary="Pattern observed across sessions",
                    support_count=int(pv.get("version", 1)),
                    session_count=1,
                    run_id="",
                    session_id="",
                    created_at=_now(),
                    updated_at=_now(),
                )
                counts["signals_created"] += 1
            except Exception:
                pass
    except Exception as exc:
        logger.debug("self_model bridge failed: %s", exc)
    return counts


def progress_signal_lifecycles() -> dict[str, int]:
    """Move signals through lifecycle stages: active → carried → fading → released."""
    counts = {"carried": 0, "fading": 0, "released": 0, "stale": 0}
    try:
        # Refresh witness signal statuses
        from apps.api.jarvis_api.services.witness_signal_tracking import refresh_runtime_witness_signal_statuses
        result = refresh_runtime_witness_signal_statuses()
        counts["stale"] += int(result.get("stale_marked", 0))
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.reflective_critic_tracking import refresh_runtime_reflective_critic_statuses
        result = refresh_runtime_reflective_critic_statuses()
        counts["stale"] += int(result.get("stale_marked", 0))
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.self_model_signal_tracking import refresh_runtime_self_model_signal_statuses
        result = refresh_runtime_self_model_signal_statuses()
        counts["stale"] += int(result.get("stale_marked", 0))
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.development_focus_tracking import refresh_runtime_development_focus_statuses
        result = refresh_runtime_development_focus_statuses()
        counts["stale"] += int(result.get("stale_marked", 0))
    except Exception:
        pass

    return counts


def build_cadence_producers_surface() -> dict[str, object]:
    """MC surface for cadence producer status."""
    return {
        "active": True,
        "summary": "Cadence producers fire signals after visible runs and heartbeat ticks",
        "producers": [
            "witness_signal", "self_review_record", "self_review_run", "self_review_outcome",
            "reflective_critic", "reflection_signal", "self_model_signal", "development_focus",
            "emergent_signal", "decision_log", "lifecycle_progression",
        ],
    }
