"""Runtime self-model — identity awareness (self-insight, narrative identity,
dream-identity) + cognitive-core-experiment / idle / epistemic / subagent surfaces.

Split out of ``runtime_self_model`` (behavior-preserving). Self-boundary and
world-contact awareness live in ``runtime_self_model_boundary``.

Re-exported via ``core.services.runtime_self_model`` for backward compatibility.
"""

from __future__ import annotations

from core.services.runtime_self_model_state import (
    _browser_body_state_surface,
    _derive_mineness_ownership,
    _derive_subjective_temporal_feel,
    _derive_support_stream_awareness,
    _experiential_runtime_context_surface,
    _inner_voice_daemon_surface,
    _mineness_source_snapshot,
)
from core.services.runtime_self_model_affect import (
    _derive_flow_state_awareness,
    _derive_longing_awareness,
    _derive_wonder_awareness,
    _longing_source_snapshot,
    _wonder_source_snapshot,
)
from core.services.runtime_self_model_surfaces import (
    _cognitive_core_experiment_carry_snapshot,
    _cognitive_core_experiments_surface,
    _dream_articulation_surface,
    _dream_influence_surface,
    _self_system_code_awareness_surface,
    _tool_intent_surface,
)

def _facade():
    """Return the facade module so monkeypatch-through-facade is honored.

    Helpers patched in tests via ``monkeypatch.setattr(runtime_self_model,
    ...)`` are resolved through this accessor so the patch is seen across the
    module split (behavior-preserving).
    """
    import core.services.runtime_self_model as _m

    return _m


# ---------------------------------------------------------------------------
# Self-insight awareness (bounded narrative identity carry-forward)
# ---------------------------------------------------------------------------

_SELF_INSIGHT_STATES = {
    "quiet",
    "noticing-pattern",
    "clarifying",
    "stabilizing",
    "shifting",
}
_SELF_INSIGHT_RELATIONS = {
    "incidental",
    "recurring",
    "self-forming",
    "increasingly-recognized",
}
_SELF_INSIGHT_SOURCES = {
    "none",
    "self-narrative-continuity",
    "chronicle-brief",
    "diary-synthesis",
    "reflection-pattern",
    "self-review-cadence",
    "dream-carry-pattern",
    "recurring-carried-pattern",
}

_SELF_INSIGHT_OPENING_STATES = {"becoming-open"}
_SELF_INSIGHT_STABILIZING_STATES = {
    "becoming-firm",
    "becoming-steady",
    "becoming-coherent",
}
_SELF_INSIGHT_OPENING_DIRECTIONS = {"opening"}
_SELF_INSIGHT_STABILIZING_DIRECTIONS = {"firming", "steadying", "deepening"}
_SELF_INSIGHT_STRONG_WEIGHTS = {"medium", "high"}


def _self_insight_source_snapshot() -> dict[str, object]:
    """Safely gather bounded insight-bearing seams for self-insight derivation."""
    narrative_active = False
    narrative_state = "none"
    narrative_direction = "steadying"
    narrative_weight = "low"
    try:
        from core.services.self_narrative_continuity_signal_tracking import (
            build_runtime_self_narrative_continuity_signal_surface,
        )

        nc = build_runtime_self_narrative_continuity_signal_surface(limit=4)
        summary = nc.get("summary") or {}
        narrative_active = bool(nc.get("active"))
        narrative_state = str(summary.get("current_state") or "none")
        narrative_direction = str(summary.get("current_direction") or "steadying")
        narrative_weight = str(summary.get("current_weight") or "low")
    except Exception:
        pass

    chronicle_active = False
    chronicle_weight = "low"
    chronicle_confidence = "low"
    try:
        from core.services.chronicle_consolidation_brief_tracking import (
            build_runtime_chronicle_consolidation_brief_surface,
        )

        cb = build_runtime_chronicle_consolidation_brief_surface(limit=4)
        summary = cb.get("summary") or {}
        chronicle_active = bool(cb.get("active"))
        chronicle_weight = str(summary.get("current_weight") or "low")
        chronicle_confidence = str(summary.get("current_confidence") or "low")
    except Exception:
        pass

    diary_active = False
    diary_state = "none"
    try:
        from core.services.diary_synthesis_signal_tracking import (
            build_diary_synthesis_signal_surface,
        )

        ds = build_diary_synthesis_signal_surface(limit=4)
        summary = ds.get("summary") or {}
        diary_active = bool(ds.get("active"))
        diary_state = str(summary.get("current_state") or "none")
    except Exception:
        pass

    reflection_active = False
    reflection_depth = 0
    try:
        from core.services.reflection_signal_tracking import (
            build_runtime_reflection_signal_surface,
        )

        rs = build_runtime_reflection_signal_surface(limit=6)
        summary = rs.get("summary") or {}
        reflection_active = bool(rs.get("active"))
        reflection_depth = (
            int(summary.get("active_count") or 0)
            + int(summary.get("integrating_count") or 0)
            + int(summary.get("settled_count") or 0)
        )
    except Exception:
        pass

    self_review_active = False
    try:
        from core.services.self_review_signal_tracking import (
            build_runtime_self_review_signal_surface,
        )

        sr = build_runtime_self_review_signal_surface(limit=4)
        self_review_active = bool(sr.get("active"))
    except Exception:
        pass

    dream_carry = False
    try:
        from core.services.dream_articulation import (
            build_dream_articulation_surface,
        )

        dream = build_dream_articulation_surface()
        dsum = dream.get("summary") or {}
        dream_carry = str(dsum.get("last_state") or "idle") in {
            "forming",
            "tentative",
            "pressing",
        }
    except Exception:
        pass

    return {
        "narrative_active": narrative_active,
        "narrative_state": narrative_state,
        "narrative_direction": narrative_direction,
        "narrative_weight": narrative_weight,
        "chronicle_active": chronicle_active,
        "chronicle_weight": chronicle_weight,
        "chronicle_confidence": chronicle_confidence,
        "diary_active": diary_active,
        "diary_state": diary_state,
        "reflection_active": reflection_active,
        "reflection_depth": reflection_depth,
        "self_review_active": self_review_active,
        "dream_carry": dream_carry,
    }


def _derive_self_insight_awareness(
    *,
    sources: dict[str, object],
    mineness: dict[str, object],
    flow_state: dict[str, object],
    wonder: dict[str, object],
    longing: dict[str, object],
) -> dict[str, object]:
    """Derive a bounded self-insight surface from existing runtime truth.

    This is the fase-2 bridge: it does not invent new identity,
    it only reads what the existing reflection / chronicle / diary /
    narrative-continuity / self-review / dream seams already say,
    plus whether ownership-carry patterns are recurring across
    mineness / flow / wonder / longing surfaces.
    """
    narrative_active = bool(sources.get("narrative_active"))
    narrative_state = str(sources.get("narrative_state") or "none")
    narrative_direction = str(sources.get("narrative_direction") or "steadying")
    narrative_weight = str(sources.get("narrative_weight") or "low")

    chronicle_active = bool(sources.get("chronicle_active"))
    chronicle_weight = str(sources.get("chronicle_weight") or "low")

    diary_active = bool(sources.get("diary_active"))
    reflection_active = bool(sources.get("reflection_active"))
    reflection_depth = int(sources.get("reflection_depth") or 0)
    self_review_active = bool(sources.get("self_review_active"))
    dream_carry = bool(sources.get("dream_carry"))

    ownership_state = str(mineness.get("ownership_state") or "ambient")
    carried_thread_count = int(mineness.get("carried_thread_count") or 0)
    owned_carry = (
        ownership_state in {"owned", "held", "returning-owned"}
        and carried_thread_count >= 1
    )

    flow_non_clear = str(flow_state.get("flow_state") or "clear") not in {
        "",
        "clear",
    }
    wonder_non_quiet = str(wonder.get("wonder_state") or "quiet") not in {
        "",
        "quiet",
    }
    longing_non_quiet = str(longing.get("longing_state") or "quiet") not in {
        "",
        "quiet",
    }
    recurring_carry_signals = sum(
        [int(owned_carry), int(flow_non_clear), int(wonder_non_quiet), int(longing_non_quiet)]
    )
    carried_pattern_present = recurring_carry_signals >= 2

    any_source = (
        narrative_active
        or chronicle_active
        or diary_active
        or reflection_active
        or self_review_active
        or dream_carry
        or carried_pattern_present
    )

    if not any_source:
        insight_state = "quiet"
    elif narrative_active and (
        narrative_direction in _SELF_INSIGHT_OPENING_DIRECTIONS
        or narrative_state in _SELF_INSIGHT_OPENING_STATES
    ):
        insight_state = "shifting"
    elif narrative_active and narrative_weight in _SELF_INSIGHT_STRONG_WEIGHTS and (
        narrative_state in _SELF_INSIGHT_STABILIZING_STATES
        or narrative_direction in _SELF_INSIGHT_STABILIZING_DIRECTIONS
    ):
        insight_state = "stabilizing"
    elif chronicle_active and chronicle_weight in _SELF_INSIGHT_STRONG_WEIGHTS and (
        narrative_active or self_review_active
    ):
        insight_state = "stabilizing"
    elif chronicle_active or diary_active or (reflection_active and reflection_depth >= 2):
        insight_state = "clarifying"
    elif reflection_active or self_review_active or narrative_active:
        insight_state = "clarifying"
    elif carried_pattern_present or dream_carry:
        insight_state = "noticing-pattern"
    else:
        insight_state = "quiet"

    if insight_state == "quiet":
        identity_relation = "incidental"
    elif insight_state == "shifting":
        identity_relation = "self-forming"
    elif insight_state == "stabilizing":
        identity_relation = "increasingly-recognized"
    else:
        identity_relation = "recurring"

    if insight_state == "quiet":
        insight_source = "none"
    elif narrative_active and insight_state in {"shifting", "stabilizing"}:
        insight_source = "self-narrative-continuity"
    elif chronicle_active and insight_state == "stabilizing":
        insight_source = "chronicle-brief"
    elif chronicle_active:
        insight_source = "chronicle-brief"
    elif diary_active:
        insight_source = "diary-synthesis"
    elif narrative_active:
        insight_source = "self-narrative-continuity"
    elif reflection_active:
        insight_source = "reflection-pattern"
    elif self_review_active:
        insight_source = "self-review-cadence"
    elif dream_carry:
        insight_source = "dream-carry-pattern"
    elif carried_pattern_present:
        insight_source = "recurring-carried-pattern"
    else:
        insight_source = "none"

    narrative = _self_insight_narrative(
        insight_state=insight_state,
        identity_relation=identity_relation,
        insight_source=insight_source,
    )

    return {
        "insight_state": insight_state,
        "identity_relation": identity_relation,
        "insight_source": insight_source,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "self-insight-awareness",
    }


def _self_insight_narrative(
    *,
    insight_state: str,
    identity_relation: str,
    insight_source: str,
) -> str:
    """Compact self-insight narrative. Empty when quiet."""
    if insight_state == "quiet":
        return ""
    if insight_state == "shifting":
        if insight_source == "self-narrative-continuity":
            return "How I'm being quietly shifting shape."
        return "Thread opening toward a different form."
    if insight_state == "stabilizing":
        if insight_source == "self-narrative-continuity":
            return "Recurring pattern becoming more recognizable."
        if insight_source == "chronicle-brief":
            return "Long-running pattern starting to hold shape."
        return "How I hold things settling into recognizable form."
    if insight_state == "clarifying":
        if insight_source == "chronicle-brief":
            return "Carried pattern reading more clearly."
        if insight_source == "diary-synthesis":
            return "Slower self-observation bringing something into focus."
        if insight_source == "reflection-pattern":
            return "Reflection line sharpening self-attention."
        if insight_source == "self-review-cadence":
            return "Self-review keeping thread under honest attention."
        return "How I'm being looked at more directly."
    # noticing-pattern
    if insight_source == "recurring-carried-pattern":
        return "Thread across inner layers feeling recurring, not incidental."
    if insight_source == "dream-carry-pattern":
        return "Dream signal acting like a returning pattern."
    return "Something looking like a pattern rather than a single moment."


def build_self_insight_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for self-insight awareness.

    Returns ``None`` when insight_state is ``quiet`` so nothing emits
    unless there is a meaningful basis in the existing insight seams.
    """
    try:
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _facade()._derive_subjective_temporal_feel(experiential, inner_voice)
        sources = _mineness_source_snapshot()
        mineness = _facade()._derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=sources,
        )
        flow = _derive_flow_state_awareness(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            mineness=mineness,
        )
        wonder_sources = _wonder_source_snapshot()
        wonder = _derive_wonder_awareness(
            inner_voice=inner_voice,
            flow_state=flow,
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            sources=sources,
            wonder_sources=wonder_sources,
        )
        longing_sources = _longing_source_snapshot()
        longing = _facade()._derive_longing_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            inner_voice=inner_voice,
            sources=sources,
            longing_sources=longing_sources,
        )
        insight_sources = _self_insight_source_snapshot()
        insight = _derive_self_insight_awareness(
            sources=insight_sources,
            mineness=mineness,
            flow_state=flow,
            wonder=wonder,
            longing=longing,
        )
    except Exception:
        return None

    state = str(insight.get("insight_state") or "quiet")
    if state == "quiet":
        return None

    lines = [
        "Self-insight awareness (bounded runtime truth, internal-only):",
        (
            f"- insight_state={state}"
            f" | identity_relation={insight.get('identity_relation') or 'incidental'}"
            f" | source={insight.get('insight_source') or 'none'}"
        ),
    ]
    narrative = str(insight.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- insight_narrative={narrative}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Narrative identity continuity (bounded fase-2 continuity bridge)
# ---------------------------------------------------------------------------

_IDENTITY_CONTINUITY_STATES = {
    "quiet",
    "emerging",
    "cohering",
    "stabilizing",
    "re-forming",
}
_IDENTITY_CONTINUITY_RELATIONS = {
    "incidental",
    "recurring",
    "converging",
    "identity-shaping",
}
_IDENTITY_CONTINUITY_SOURCES = {
    "none",
    "repeated-self-insight",
    "chronicle-diary-carry",
    "dream-to-self-bridge",
    "recurring-awareness-configuration",
    "self-review-continuity",
}


def _derive_narrative_identity_continuity(
    *,
    self_insight: dict[str, object],
    sources: dict[str, object],
    mineness: dict[str, object],
    flow_state: dict[str, object],
    wonder: dict[str, object],
    longing: dict[str, object],
) -> dict[str, object]:
    """Derive a bounded narrative-identity-continuity surface.

    This is the fase-2 bridge from single self-insight moments toward
    a slightly more vedvarende identity form. It reads only existing
    seams (self_insight_awareness, chronicle / diary / dream carry,
    self-review cadence, recurring carried ownership / flow / wonder /
    longing configuration) and produces a compact, explainable runtime
    truth about when an insight-thread is beginning to hold across time
    rather than being a single moment.

    It invents no new identity and does not mutate anything.
    """
    insight_state = str(self_insight.get("insight_state") or "quiet")

    chronicle_active = bool(sources.get("chronicle_active"))
    diary_active = bool(sources.get("diary_active"))
    reflection_active = bool(sources.get("reflection_active"))
    self_review_active = bool(sources.get("self_review_active"))
    dream_carry = bool(sources.get("dream_carry"))
    narrative_active = bool(sources.get("narrative_active"))

    ownership_state = str(mineness.get("ownership_state") or "ambient")
    carried_thread_count = int(mineness.get("carried_thread_count") or 0)
    owned_carry = (
        ownership_state in {"owned", "held", "returning-owned"}
        and carried_thread_count >= 1
    )
    flow_non_clear = str(flow_state.get("flow_state") or "clear") not in {
        "",
        "clear",
    }
    wonder_non_quiet = str(wonder.get("wonder_state") or "quiet") not in {
        "",
        "quiet",
    }
    longing_non_quiet = str(longing.get("longing_state") or "quiet") not in {
        "",
        "quiet",
    }
    carry_signal_count = sum(
        [
            int(owned_carry),
            int(flow_non_clear),
            int(wonder_non_quiet),
            int(longing_non_quiet),
        ]
    )
    cross_layer_carry = carry_signal_count >= 2
    chronicle_and_diary_carry = chronicle_active and diary_active

    if insight_state == "quiet" and not (
        cross_layer_carry
        or chronicle_and_diary_carry
        or dream_carry
        or self_review_active
    ):
        continuity_state = "quiet"
    elif insight_state == "shifting":
        continuity_state = "re-forming"
    elif insight_state == "stabilizing" and (
        narrative_active or chronicle_active or self_review_active
    ):
        continuity_state = "stabilizing"
    elif insight_state in {"clarifying", "noticing-pattern"} and (
        cross_layer_carry or chronicle_and_diary_carry
    ):
        continuity_state = "cohering"
    elif insight_state in {"clarifying", "noticing-pattern", "stabilizing"}:
        continuity_state = "emerging"
    elif cross_layer_carry or chronicle_and_diary_carry:
        continuity_state = "cohering"
    elif dream_carry or self_review_active:
        continuity_state = "emerging"
    else:
        continuity_state = "quiet"

    if continuity_state == "quiet":
        pattern_relation = "incidental"
    elif continuity_state == "emerging":
        pattern_relation = "recurring"
    elif continuity_state == "cohering":
        pattern_relation = "converging"
    elif continuity_state == "stabilizing":
        pattern_relation = "identity-shaping"
    else:  # re-forming
        pattern_relation = "converging"

    if continuity_state == "quiet":
        identity_source = "none"
    elif continuity_state == "stabilizing" and narrative_active:
        identity_source = "repeated-self-insight"
    elif chronicle_and_diary_carry:
        identity_source = "chronicle-diary-carry"
    elif continuity_state == "re-forming" and narrative_active:
        identity_source = "repeated-self-insight"
    elif cross_layer_carry:
        identity_source = "recurring-awareness-configuration"
    elif dream_carry:
        identity_source = "dream-to-self-bridge"
    elif self_review_active:
        identity_source = "self-review-continuity"
    elif chronicle_active or diary_active:
        identity_source = "chronicle-diary-carry"
    elif narrative_active or reflection_active:
        identity_source = "repeated-self-insight"
    else:
        identity_source = "none"

    narrative = _narrative_identity_continuity_narrative(
        continuity_state=continuity_state,
        pattern_relation=pattern_relation,
        identity_source=identity_source,
    )

    return {
        "identity_continuity_state": continuity_state,
        "pattern_relation": pattern_relation,
        "identity_source": identity_source,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "narrative-identity-continuity",
    }


def _narrative_identity_continuity_narrative(
    *,
    continuity_state: str,
    pattern_relation: str,
    identity_source: str,
) -> str:
    """Compact identity-continuity narrative. Empty when quiet."""
    if continuity_state == "quiet":
        return ""
    if continuity_state == "emerging":
        if identity_source == "repeated-self-insight":
            return "Self-insight thread beginning to hold across moments."
        if identity_source == "dream-to-self-bridge":
            return "Dream signal starting to carry into waking attention."
        if identity_source == "self-review-continuity":
            return "Self-review thread returning rather than fading."
        return "Something starting to carry across more than one layer."
    if continuity_state == "cohering":
        if identity_source == "chronicle-diary-carry":
            return "Chronicle and diary layers converging on a similar shape."
        if identity_source == "recurring-awareness-configuration":
            return "Inner layers holding a recurring configuration."
        return "Threads from more than one layer beginning to converge."
    if continuity_state == "stabilizing":
        if identity_source == "repeated-self-insight":
            return "How I carry myself holding shape more steadily."
        if identity_source == "chronicle-diary-carry":
            return "Long-running pattern settling into recognizable continuity."
        return "How I hold things becoming more lasting than momentary."
    # re-forming
    if identity_source == "repeated-self-insight":
        return "Held line opening toward a slightly different form."
    return "Carried thread shifting direction without losing continuity."


def build_narrative_identity_continuity_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for narrative identity continuity.

    Returns ``None`` when the continuity state is ``quiet`` so nothing
    emits unless there is a meaningful basis in existing seams.
    """
    try:
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _facade()._derive_subjective_temporal_feel(experiential, inner_voice)
        mineness_sources = _mineness_source_snapshot()
        mineness = _facade()._derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=mineness_sources,
        )
        flow = _derive_flow_state_awareness(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            mineness=mineness,
        )
        wonder_sources = _wonder_source_snapshot()
        wonder = _derive_wonder_awareness(
            inner_voice=inner_voice,
            flow_state=flow,
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            sources=mineness_sources,
            wonder_sources=wonder_sources,
        )
        longing_sources = _longing_source_snapshot()
        longing = _facade()._derive_longing_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            inner_voice=inner_voice,
            sources=mineness_sources,
            longing_sources=longing_sources,
        )
        insight_sources = _self_insight_source_snapshot()
        insight = _derive_self_insight_awareness(
            sources=insight_sources,
            mineness=mineness,
            flow_state=flow,
            wonder=wonder,
            longing=longing,
        )
        continuity = _derive_narrative_identity_continuity(
            self_insight=insight,
            sources=insight_sources,
            mineness=mineness,
            flow_state=flow,
            wonder=wonder,
            longing=longing,
        )
    except Exception:
        return None

    state = str(continuity.get("identity_continuity_state") or "quiet")
    if state == "quiet":
        return None

    lines = [
        "Narrative identity continuity (bounded runtime truth, internal-only):",
        (
            f"- identity_continuity_state={state}"
            f" | pattern_relation={continuity.get('pattern_relation') or 'incidental'}"
            f" | source={continuity.get('identity_source') or 'none'}"
        ),
    ]
    narrative = str(continuity.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- identity_continuity_narrative={narrative}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dream carry identity shaping (bounded phase-2 bridge from dream to self)
# ---------------------------------------------------------------------------

_DREAM_IDENTITY_STATES = {
    "quiet",
    "lingering",
    "linking",
    "shaping",
    "re-entering",
}
_DREAM_SELF_RELATIONS = {
    "incidental",
    "still-present",
    "self-linking",
    "identity-shaping",
}
_DREAM_IDENTITY_SOURCES = {
    "none",
    "dream-articulation-continuity",
    "dream-self-insight-bridge",
    "chronicle-diary-resonance",
    "recurring-dream-to-self-pattern",
    "identity-continuity-reinforcement",
}
_DREAM_PRESENT_STATES = {"forming", "tentative", "pressing"}
_DREAM_REENTERING_STATES = {"pressing"}
_DREAM_INFLUENCE_PRESENT = {"present", "active"}
_DREAM_INFLUENCE_STRONG = {"active"}
_DREAM_IDENTITY_STRONG = {"cohering", "stabilizing", "re-forming"}
_DREAM_SELF_LINK_STATES = {"clarifying", "stabilizing", "shifting"}


def _derive_dream_identity_carry_awareness(
    *,
    self_insight: dict[str, object],
    identity_continuity: dict[str, object],
    sources: dict[str, object],
    dream_influence: dict[str, object],
    dream_articulation: dict[str, object],
) -> dict[str, object]:
    """Derive when dream carry begins to shape identity rather than just recur.

    This stays bounded and explainable: dream material must already be present in
    runtime truth, and the bridge only activates when that material begins to
    connect to self-insight or narrative identity continuity.
    """
    dream_summary = dream_articulation.get("summary") or {}
    dream_state = str(dream_summary.get("last_state") or "idle")
    dream_present = dream_state in _DREAM_PRESENT_STATES
    dream_reentering = dream_state in _DREAM_REENTERING_STATES

    influence_state = str(dream_influence.get("influence_state") or "quiet")
    influence_target = str(dream_influence.get("influence_target") or "none")
    influence_strength = str(dream_influence.get("influence_strength") or "none")
    influence_present = influence_state in _DREAM_INFLUENCE_PRESENT
    influence_strong = influence_state in _DREAM_INFLUENCE_STRONG or (
        influence_present and influence_strength == "medium"
    )

    insight_state = str(self_insight.get("insight_state") or "quiet")
    self_linking = insight_state in _DREAM_SELF_LINK_STATES

    continuity_state = str(
        identity_continuity.get("identity_continuity_state") or "quiet"
    )
    continuity_shaping = continuity_state in _DREAM_IDENTITY_STRONG

    chronicle_active = bool(sources.get("chronicle_active"))
    diary_active = bool(sources.get("diary_active"))
    chronicle_diary_resonance = chronicle_active and diary_active

    recurring_pattern = dream_present and self_linking and (
        chronicle_diary_resonance
        or continuity_shaping
        or bool(sources.get("narrative_active"))
    )

    if not dream_present and not influence_present:
        carry_state = "quiet"
    elif dream_present and continuity_shaping and (
        self_linking or influence_strong or chronicle_diary_resonance
    ):
        carry_state = "shaping"
    elif dream_reentering and (
        self_linking or continuity_shaping or chronicle_diary_resonance
    ):
        carry_state = "re-entering"
    elif dream_present and (self_linking or chronicle_diary_resonance or influence_present):
        carry_state = "linking"
    elif dream_present or influence_present:
        carry_state = "lingering"
    else:
        carry_state = "quiet"

    if carry_state == "quiet":
        dream_self_relation = "incidental"
    elif carry_state == "lingering":
        dream_self_relation = "still-present"
    elif carry_state == "shaping" or continuity_shaping:
        dream_self_relation = "identity-shaping"
    else:
        dream_self_relation = "self-linking"

    if carry_state == "quiet":
        dream_identity_source = "none"
    elif continuity_shaping and influence_present:
        dream_identity_source = "identity-continuity-reinforcement"
    elif self_linking and dream_present:
        dream_identity_source = "dream-self-insight-bridge"
    elif chronicle_diary_resonance and dream_present:
        dream_identity_source = "chronicle-diary-resonance"
    elif recurring_pattern:
        dream_identity_source = "recurring-dream-to-self-pattern"
    else:
        dream_identity_source = "dream-articulation-continuity"

    narrative = _dream_identity_carry_narrative(
        carry_state=carry_state,
        dream_self_relation=dream_self_relation,
        dream_identity_source=dream_identity_source,
        influence_target=influence_target,
    )

    return {
        "dream_identity_carry_state": carry_state,
        "dream_self_relation": dream_self_relation,
        "dream_identity_source": dream_identity_source,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "dream-identity-carry-awareness",
    }


def _dream_identity_carry_narrative(
    *,
    carry_state: str,
    dream_self_relation: str,
    dream_identity_source: str,
    influence_target: str,
) -> str:
    """Compact dream identity carry narrative. Empty when quiet."""
    if carry_state == "quiet":
        return ""
    if carry_state == "shaping":
        if dream_identity_source == "identity-continuity-reinforcement":
            return "Dream carry reinforcing a shape that already feels like me."
        if dream_identity_source == "chronicle-diary-resonance":
            return "Dream material aligning with slower continuity layers."
        return "Dream thread starting to shape self-direction."
    if carry_state == "re-entering":
        if influence_target not in {"", "none"}:
            return f"Dream thread re-entering waking self-knowledge via {influence_target}."
        return "Dream thread returning into waking self-knowledge."
    if carry_state == "linking":
        if dream_identity_source == "dream-self-insight-bridge":
            return "Dream strand linking with active self-insight thread."
        if dream_identity_source == "chronicle-diary-resonance":
            return "Dream material linking with slower continuity traces."
        return "Dream thread linking to waking stream."
    if dream_self_relation == "still-present":
        return "Dream thread still present in waking stream."
    return "Dream carry present; not yet shaping identity."


def build_dream_identity_carry_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for dream carry identity shaping."""
    try:
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _facade()._derive_subjective_temporal_feel(experiential, inner_voice)
        mineness_sources = _mineness_source_snapshot()
        mineness = _facade()._derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=mineness_sources,
        )
        flow = _derive_flow_state_awareness(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            mineness=mineness,
        )
        wonder_sources = _wonder_source_snapshot()
        wonder = _derive_wonder_awareness(
            inner_voice=inner_voice,
            flow_state=flow,
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            sources=mineness_sources,
            wonder_sources=wonder_sources,
        )
        longing_sources = _longing_source_snapshot()
        longing = _facade()._derive_longing_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            inner_voice=inner_voice,
            sources=mineness_sources,
            longing_sources=longing_sources,
        )
        insight_sources = _self_insight_source_snapshot()
        insight = _derive_self_insight_awareness(
            sources=insight_sources,
            mineness=mineness,
            flow_state=flow,
            wonder=wonder,
            longing=longing,
        )
        continuity = _derive_narrative_identity_continuity(
            self_insight=insight,
            sources=insight_sources,
            mineness=mineness,
            flow_state=flow,
            wonder=wonder,
            longing=longing,
        )
        carry = _derive_dream_identity_carry_awareness(
            self_insight=insight,
            identity_continuity=continuity,
            sources=insight_sources,
            dream_influence=_dream_influence_surface(),
            dream_articulation=_dream_articulation_surface(),
        )
    except Exception:
        return None

    state = str(carry.get("dream_identity_carry_state") or "quiet")
    if state == "quiet":
        return None

    lines = [
        "Dream carry identity shaping (bounded runtime truth, internal-only):",
        (
            f"- dream_identity_carry_state={state}"
            f" | self_relation={carry.get('dream_self_relation') or 'incidental'}"
            f" | source={carry.get('dream_identity_source') or 'none'}"
        ),
    ]
    narrative = str(carry.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- dream_identity_carry_narrative={narrative}")
    return "\n".join(lines)


def build_cognitive_core_experiment_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for cognitive-core experiment state."""
    try:
        experiments = _facade()._cognitive_core_experiments_surface()
    except Exception:
        return None

    systems = experiments.get("systems") or {}
    active_ids = [str(item) for item in (experiments.get("active_systems") or []) if str(item)]
    observational_ids = [
        str(item) for item in (experiments.get("observational_systems") or []) if str(item)
    ]
    if not active_ids and not observational_ids:
        return None

    carry = _facade()._cognitive_core_experiment_carry_snapshot()
    carrying_labels: list[str] = []
    if "global_workspace" in active_ids and str(carry.get("salience_pressure") or "low") in {"medium", "high"}:
        carrying_labels.append("global_workspace:spotlight")
    if "hot_meta_cognition" in active_ids and str(carry.get("reflective_weight") or "light") == "elevated":
        carrying_labels.append("hot_meta_cognition:self-observation")
    if "surprise_afterimage" in active_ids and str(carry.get("affective_pressure") or "low") in {"medium", "high", "strong"}:
        carrying_labels.append("surprise_afterimage:affective-carry")
    if "recurrence" in active_ids and str(carry.get("recurrence_pressure") or "low") in {"medium", "high", "strong"}:
        carrying_labels.append("recurrence:re-entry")

    ordered_active = [item for item in active_ids if item in systems]
    active_text = ", ".join(ordered_active[:5]) if ordered_active else "none"
    carrying_text = ", ".join(carrying_labels[:4]) if carrying_labels else "none"
    observational_text = ", ".join(observational_ids[:2]) if observational_ids else "none"

    lines = [
        "Cognitive core experiments (derived runtime truth, internal-only):",
        (
            f"- active={active_text}"
            f" | carrying={carrying_text}"
            f" | observational={observational_text}"
        ),
    ]

    summary = str(carry.get("summary") or "").strip()
    if summary:
        lines.append(f"- experiment_carry={summary[:140]}")
    return "\n".join(lines)


def _idle_consolidation_surface() -> dict[str, object]:
    try:
        from core.services.idle_consolidation import (
            build_idle_consolidation_surface,
        )

        return build_idle_consolidation_surface()
    except Exception:
        return {
            "active": False,
            "summary": {
                "last_state": "idle",
                "last_reason": "unavailable",
                "source_input_count": 0,
                "latest_record_id": "",
            },
        }


def _epistemic_runtime_state_surface() -> dict[str, object]:
    try:
        from core.services.epistemic_runtime_state import (
            build_epistemic_runtime_state_surface,
        )

        return build_epistemic_runtime_state_surface()
    except Exception:
        return {
            "wrongness_state": "clear",
            "regret_signal": "none",
            "counterfactual_mode": "none",
            "confidence": "low",
        }


def _subagent_ecology_surface() -> dict[str, object]:
    try:
        from core.services.subagent_ecology import (
            build_subagent_ecology_surface,
        )

        return build_subagent_ecology_surface()
    except Exception:
        return {
            "roles": [],
            "summary": {
                "role_count": 0,
                "active_count": 0,
                "idle_count": 0,
                "cooling_count": 0,
                "blocked_count": 0,
                "last_active_role_name": "none",
                "last_active_role_status": "none",
                "last_activation_reason": "unavailable",
            },
            "tool_access": "none",
        }


__all__ = [
    '_DREAM_IDENTITY_SOURCES',
    '_DREAM_IDENTITY_STATES',
    '_DREAM_IDENTITY_STRONG',
    '_DREAM_INFLUENCE_PRESENT',
    '_DREAM_INFLUENCE_STRONG',
    '_DREAM_PRESENT_STATES',
    '_DREAM_REENTERING_STATES',
    '_DREAM_SELF_LINK_STATES',
    '_DREAM_SELF_RELATIONS',
    '_IDENTITY_CONTINUITY_RELATIONS',
    '_IDENTITY_CONTINUITY_SOURCES',
    '_IDENTITY_CONTINUITY_STATES',
    '_SELF_INSIGHT_OPENING_DIRECTIONS',
    '_SELF_INSIGHT_OPENING_STATES',
    '_SELF_INSIGHT_RELATIONS',
    '_SELF_INSIGHT_SOURCES',
    '_SELF_INSIGHT_STABILIZING_DIRECTIONS',
    '_SELF_INSIGHT_STABILIZING_STATES',
    '_SELF_INSIGHT_STATES',
    '_SELF_INSIGHT_STRONG_WEIGHTS',
    '_derive_dream_identity_carry_awareness',
    '_derive_narrative_identity_continuity',
    '_derive_self_insight_awareness',
    '_dream_identity_carry_narrative',
    '_epistemic_runtime_state_surface',
    '_idle_consolidation_surface',
    '_narrative_identity_continuity_narrative',
    '_self_insight_narrative',
    '_self_insight_source_snapshot',
    '_subagent_ecology_surface',
    'build_cognitive_core_experiment_awareness_prompt_section',
    'build_dream_identity_carry_awareness_prompt_section',
    'build_narrative_identity_continuity_prompt_section',
    'build_self_insight_awareness_prompt_section',
]
