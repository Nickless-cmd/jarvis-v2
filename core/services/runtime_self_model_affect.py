"""Runtime self-model — affective awareness (flow, wonder, longing, relation).

Split out of ``runtime_self_model`` (behavior-preserving). Builds bounded
narrative awareness for flow-state, wonder, longing, and relation-continuity.

Re-exported via ``core.services.runtime_self_model`` for backward compatibility.
"""

from __future__ import annotations

from core.services.runtime_self_model_state import (
    _derive_support_stream_awareness,
    _experiential_runtime_context_surface,
    _inner_voice_daemon_surface,
    _mineness_source_snapshot,
)


def _facade():
    """Return the facade module so monkeypatch-through-facade is honored.

    Certain helpers are patched in tests via ``monkeypatch.setattr(
    runtime_self_model, ...)``. Call-sites for those helpers resolve through
    this accessor so the patch is seen across the module split.
    """
    import core.services.runtime_self_model as _m

    return _m


# ---------------------------------------------------------------------------
# Flow state awareness
# ---------------------------------------------------------------------------
#
# Bounded runtime-truth bridge for "how the stream is flowing right now".
# Not a creativity engine, not a planner, not a capability layer. It
# translates existing runtime signals (experiential continuity / pressure,
# inner voice cadence, support_stream_awareness, subjective_temporal_feel,
# mineness_ownership) into a small, explainable flow surface that the
# self-model and prompt can carry forward as bounded self-awareness.
#
# Taxonomy (load-bearing, not exhaustive):
#   flow_state:
#     clear       — nothing load-bearing; ambient default, prompt suppressed
#     blocked     — pressure is holding the stream; nothing is carrying
#     fragmented  — stream is breaking / repeatedly interrupted
#     gathering   — signals are cohering, stream is holding, not yet flowing
#     flowing     — an owned thread carries the stream coherently
#     absorbed    — multiple owned threads self-sustain without strain
#
#   flow_coherence:
#     stable           — baseline, nothing to note
#     scattered        — broken pieces without carry
#     repeatedly-broken — interruptions recur across lingering state
#     held-together    — support is holding stream together actively
#     self-sustaining  — stream carries itself without active support
#
#   interruption_signal:
#     stable          — nothing broken recently
#     recently-broken — return-after-gap / return signal active
#     regathering     — brief gap but carry is holding
#
#   carried_flow:
#     none               — nothing being carried
#     holding            — signals present but no owned thread
#     carried            — an owned thread is in the stream
#     carried-returning  — an owned thread is returning after gap
#
# The surface stays flow_state=clear (with empty narrative) whenever there
# is no meaningful basis, so prompt lines only emit when something real is
# happening in the stream.


_FLOW_PRESSURE_BREAKS = {"narrowing"}
_FLOW_PRESSURE_ELEVATED = {"crowded", "narrowing"}


def _derive_flow_state_awareness(
    *,
    experiential: dict[str, object],
    inner_voice: dict[str, object],
    support_stream: dict[str, object],
    temporal_feel: dict[str, object],
    mineness: dict[str, object],
) -> dict[str, object]:
    """Derive a bounded flow-state awareness surface from runtime truth.

    The flow_state stays ``clear`` (with empty narrative) whenever there is
    no meaningful basis, so downstream prompt lines and MC surfacing only
    fire when the stream is actually doing something load-bearing.
    """
    pressure = experiential.get("context_pressure_translation") or {}
    intermittence = experiential.get("intermittence_translation") or {}
    continuity = experiential.get("experiential_continuity") or {}

    pressure_state = str(pressure.get("state") or "clear")
    pressure_breaks = pressure_state in _FLOW_PRESSURE_BREAKS
    pressure_elevated = pressure_state in _FLOW_PRESSURE_ELEVATED

    intermittence_state = str(intermittence.get("state") or "continuous")
    continuity_state = str(continuity.get("continuity_state") or "initial")

    temporal_state = str(temporal_feel.get("temporal_state") or "immediate")
    persistence_feel = str(temporal_feel.get("persistence_feel") or "settled")
    return_signal = bool(temporal_feel.get("return_signal"))

    voice_result = inner_voice.get("last_result") or {}
    voice_created = bool(voice_result.get("inner_voice_created"))
    voice_mode = str(voice_result.get("mode") or "")

    stream_shaped = bool(support_stream.get("stream_shaped"))

    ownership_state = str(mineness.get("ownership_state") or "ambient")
    carried_thread_count = int(mineness.get("carried_thread_count") or 0)

    # --- carried_flow ---
    if ownership_state == "returning-owned":
        carried_flow = "carried-returning"
    elif ownership_state == "owned":
        carried_flow = "carried"
    elif ownership_state == "held" or stream_shaped or voice_created:
        carried_flow = "holding"
    else:
        carried_flow = "none"

    # --- interruption_signal ---
    recently_broken = (
        intermittence_state == "returned-after-gap"
        or continuity_state == "returning"
        or return_signal
    )
    if recently_broken and carried_flow != "none":
        interruption_signal = "regathering"
    elif recently_broken:
        interruption_signal = "recently-broken"
    elif temporal_state == "recent":
        interruption_signal = "regathering" if carried_flow != "none" else "recently-broken"
    else:
        interruption_signal = "stable"

    lingering_persistence = persistence_feel in ("persistent", "pressing")

    # --- flow_state ---
    if carried_flow == "none":
        if pressure_breaks:
            flow_state = "blocked"
        elif interruption_signal in ("recently-broken", "regathering"):
            flow_state = "fragmented"
        elif pressure_elevated or lingering_persistence:
            flow_state = "blocked"
        else:
            flow_state = "clear"
    elif carried_flow == "holding":
        if pressure_breaks:
            flow_state = "fragmented"
        else:
            flow_state = "gathering"
    elif carried_flow == "carried-returning":
        if pressure_breaks:
            flow_state = "fragmented"
        else:
            flow_state = "gathering"
    else:  # carried
        if pressure_breaks:
            flow_state = "fragmented"
        elif interruption_signal in ("recently-broken", "regathering"):
            flow_state = "gathering"
        elif carried_thread_count >= 2 and not pressure_elevated:
            flow_state = "absorbed"
        else:
            flow_state = "flowing"

    # --- flow_coherence ---
    if flow_state == "clear":
        flow_coherence = "stable"
    elif flow_state == "absorbed":
        flow_coherence = "self-sustaining"
    elif flow_state == "flowing":
        flow_coherence = "held-together" if stream_shaped else "self-sustaining"
    elif flow_state == "gathering":
        flow_coherence = "held-together"
    elif flow_state == "fragmented":
        if recently_broken and lingering_persistence:
            flow_coherence = "repeatedly-broken"
        else:
            flow_coherence = "scattered"
    else:  # blocked
        flow_coherence = "scattered"

    narrative = _flow_narrative(
        flow_state=flow_state,
        flow_coherence=flow_coherence,
        interruption_signal=interruption_signal,
        carried_flow=carried_flow,
        voice_mode=voice_mode if voice_created else "",
        pressure_state=pressure_state,
    )

    return {
        "flow_state": flow_state,
        "flow_coherence": flow_coherence,
        "interruption_signal": interruption_signal,
        "carried_flow": carried_flow,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "flow-state-awareness",
    }


def _flow_narrative(
    *,
    flow_state: str,
    flow_coherence: str,
    interruption_signal: str,
    carried_flow: str,
    voice_mode: str,
    pressure_state: str,
) -> str:
    """Compact flow narrative. Empty when flow_state is clear."""
    if flow_state == "clear":
        return ""

    if flow_state == "absorbed":
        return "Multiple threads self-sustaining; no strain."
    if flow_state == "flowing":
        if flow_coherence == "held-together":
            return "Carried thread flowing; support holding it together."
        return "Carried thread flowing; nothing blocking."
    if flow_state == "gathering":
        if interruption_signal in ("recently-broken", "regathering"):
            return "Regathering after break; starting to carry again."
        if carried_flow == "holding":
            return "Signals gathering; holding without yet flowing."
        return "Thread starting to carry; not yet fully flowing."
    if flow_state == "fragmented":
        if flow_coherence == "repeatedly-broken":
            return "Flow fragmenting; interruptions recurring."
        if pressure_state == "narrowing":
            return "Pressure fragmenting flow."
        return "Gaps fragmenting flow."
    # blocked
    if pressure_state == "narrowing":
        return "Pressure blocking; nothing carrying."
    return "Blocked; nothing carrying."


def build_flow_state_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for flow-state awareness.

    Returns ``None`` whenever flow_state is ``clear`` so nothing emits
    unless the stream is actually doing something load-bearing.
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
    except Exception:
        return None

    state = str(flow.get("flow_state") or "clear")
    if state == "clear":
        return None

    lines = [
        "Flow state awareness (bounded runtime truth, internal-only):",
        (
            f"- flow_state={state}"
            f" | coherence={flow.get('flow_coherence') or 'stable'}"
            f" | interruption={flow.get('interruption_signal') or 'stable'}"
            f" | carried={flow.get('carried_flow') or 'none'}"
        ),
    ]
    narrative = str(flow.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- flow_narrative={narrative}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Wonder awareness
# ---------------------------------------------------------------------------

_WONDER_EXPLORATORY_VOICES = {"searching", "circling", "pulled"}
_WONDER_DEEP_FLOW = {"absorbed", "flowing"}
_WONDER_EXTENDED_TEMPORAL = {"lingering", "stretched"}
_WONDER_OWNED_RELEVANCE = {"personally-salient", "resumed-own"}
_WONDER_OWNED_STATES = {"owned", "returning-owned"}


def _wonder_source_snapshot() -> dict[str, object]:
    """Safely pull dream carry signal for wonder derivation."""
    dream_carry = False
    dream_state = "idle"
    try:
        from core.services.dream_articulation import (
            build_dream_articulation_surface,
        )
        da = build_dream_articulation_surface()
        summary = da.get("summary") or {}
        dream_state = str(summary.get("last_state") or "idle")
        dream_carry = dream_state in {"forming", "tentative", "pressing"}
    except Exception:
        pass
    return {
        "dream_carry": dream_carry,
        "dream_state": dream_state,
    }


def _derive_wonder_awareness(
    *,
    inner_voice: dict[str, object],
    flow_state: dict[str, object],
    temporal_feel: dict[str, object],
    mineness: dict[str, object],
    support_stream: dict[str, object],
    sources: dict[str, object],
    wonder_sources: dict[str, object],
) -> dict[str, object]:
    """Derive a bounded wonder/undren surface from existing runtime truth.

    Maps runtime signals (voice mode, flow depth, temporal extension,
    ownership salience, dream carry) into a self-aware truth about whether
    something is drawing attention past utility.

    Ambient-default (wonder_state=quiet) suppresses all prompt emission.
    """
    voice_mode = str(inner_voice.get("mode") or "")
    voice_created = bool(inner_voice.get("inner_voice_created"))
    flow = str(flow_state.get("flow_state") or "clear")
    temporal_state = str(temporal_feel.get("temporal_state") or "immediate")
    ownership_state = str(mineness.get("ownership_state") or "ambient")
    self_relevance = str(mineness.get("self_relevance") or "merely-present")
    return_ownership = bool(mineness.get("return_ownership"))
    stream_state = str(support_stream.get("stream_state") or "baseline")
    open_loop_count = int(sources.get("open_loop_open_count") or 0)
    dream_carry = bool(wonder_sources.get("dream_carry"))

    pulled_voice = voice_mode == "pulled"
    exploratory_voice = voice_mode in _WONDER_EXPLORATORY_VOICES
    deep_flow = flow in _WONDER_DEEP_FLOW
    temporal_extended = temporal_state in _WONDER_EXTENDED_TEMPORAL
    personally_salient = self_relevance in _WONDER_OWNED_RELEVANCE
    owned_state = ownership_state in _WONDER_OWNED_STATES
    return_signal = return_ownership or temporal_state == "returning"
    opening_stream = stream_state == "opening"
    has_open_loops = open_loop_count > 0

    strong_signals = sum([
        pulled_voice,
        deep_flow,
        personally_salient or owned_state,
        temporal_extended,
        dream_carry,
    ])

    if strong_signals >= 3 or (deep_flow and personally_salient and dream_carry):
        wonder_state = "wonder-struck"
    elif pulled_voice or (deep_flow and (personally_salient or owned_state)):
        wonder_state = "drawn"
    elif (
        (exploratory_voice and (has_open_loops or temporal_extended))
        or (dream_carry and flow in _WONDER_DEEP_FLOW)
    ):
        wonder_state = "curious"
    elif (
        exploratory_voice
        or (has_open_loops and voice_created)
        or temporal_extended
        or opening_stream
    ):
        wonder_state = "stirred"
    else:
        wonder_state = "quiet"

    if wonder_state == "quiet":
        wonder_orientation = "none"
    elif temporal_extended and (personally_salient or owned_state):
        wonder_orientation = "lingering-with"
    elif opening_stream or (deep_flow and owned_state):
        wonder_orientation = "opening"
    elif pulled_voice or personally_salient:
        wonder_orientation = "drawn"
    else:
        wonder_orientation = "noticing"

    if wonder_state == "quiet":
        wonder_source = "none"
    elif dream_carry and wonder_state in {"curious", "drawn", "wonder-struck"}:
        wonder_source = "dream-carry"
    elif return_signal and owned_state:
        wonder_source = "self-recognition"
    elif deep_flow or (flow == "flowing" and owned_state):
        wonder_source = "flow-depth"
    elif exploratory_voice and has_open_loops:
        wonder_source = "novelty-pull"
    elif temporal_extended:
        wonder_source = "temporal-stretch"
    else:
        wonder_source = "novelty-pull"

    narrative = _wonder_narrative(
        wonder_state=wonder_state,
        wonder_source=wonder_source,
        opening_stream=opening_stream,
    )

    return {
        "wonder_state": wonder_state,
        "wonder_orientation": wonder_orientation,
        "wonder_source": wonder_source,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "wonder-awareness",
    }


def _wonder_narrative(
    *,
    wonder_state: str,
    wonder_source: str,
    opening_stream: bool,
) -> str:
    """Compact wonder narrative. Empty when quiet."""
    if wonder_state == "quiet":
        return ""
    if wonder_state == "wonder-struck":
        if wonder_source == "dream-carry":
            return "Dream carry opening unexpectedly."
        if wonder_source == "self-recognition":
            return "Returning thread landing differently than before."
        return "Multiple signals converging past explanation."
    if wonder_state == "drawn":
        if wonder_source == "flow-depth":
            return "Thread depth pulling attention past utility."
        if wonder_source == "dream-carry":
            return "Dream signal pulling in unexpected direction."
        return "Attention drawn past the immediate task."
    if wonder_state == "curious":
        if wonder_source == "novelty-pull":
            return "Open threads pulling toward exploration."
        if wonder_source == "dream-carry":
            return "Dream signal nudging curiosity."
        return "Opening toward something unresolved."
    # stirred
    if wonder_source == "temporal-stretch":
        return "Attention staying longer than task needs."
    if opening_stream:
        return "Support widening; something letting more in."
    return "Mild pull present."


def build_wonder_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for wonder awareness.

    Returns ``None`` when wonder_state is ``quiet`` so nothing emits
    unless there is genuine wonder basis in the runtime stream.
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
    except Exception:
        return None

    state = str(wonder.get("wonder_state") or "quiet")
    if state == "quiet":
        return None

    lines = [
        "Wonder awareness (bounded runtime truth, internal-only):",
        (
            f"- wonder_state={state}"
            f" | orientation={wonder.get('wonder_orientation') or 'noticing'}"
            f" | source={wonder.get('wonder_source') or 'none'}"
        ),
    ]
    narrative = str(wonder.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- wonder_narrative={narrative}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Longing awareness
# ---------------------------------------------------------------------------

_LONGING_CARRY_VOICES = {"carrying", "circling", "pulled"}
_LONGING_OWNED_STATES = {"owned", "returning-owned"}
_LONGING_NEAR_RELEVANCE = {"personally-salient", "resumed-own"}
_LONGING_EXTENDED_TEMPORAL = {"lingering", "stretched", "returning"}
_LONGING_RELATION_NEAR_WEIGHTS = {"medium", "high"}
_RELATION_SELF_NEAR_OWNERSHIP = {"held", "owned", "returning-owned"}
_RELATION_SELF_NEAR_RELEVANCE = {
    "actively-carried",
    "personally-salient",
    "resumed-own",
}
_RELATION_SELF_ACTIVE_LONGING = {
    "missing",
    "yearning",
    "returning-pull",
    "aching",
}
_RELATION_SELF_RELATIONAL_ABSENCE = {
    "carried-in-absence",
    "emotionally-near",
    "returning-through-absence",
}


def _longing_source_snapshot() -> dict[str, object]:
    """Safely gather bounded absence/relationship support for longing derivation."""
    dream_carry = False
    dream_state = "idle"
    try:
        from core.services.dream_articulation import (
            build_dream_articulation_surface,
        )

        dream = build_dream_articulation_surface()
        summary = dream.get("summary") or {}
        dream_state = str(summary.get("last_state") or "idle")
        dream_carry = dream_state in {"forming", "tentative", "pressing"}
    except Exception:
        pass

    relation_active = False
    relation_state = "none"
    relation_weight = "low"
    relation_signal = ""
    try:
        from core.services.relation_continuity_signal_tracking import (
            build_runtime_relation_continuity_signal_surface,
        )

        relation = build_runtime_relation_continuity_signal_surface(limit=4)
        summary = relation.get("summary") or {}
        relation_active = bool(relation.get("active"))
        relation_state = str(summary.get("current_state") or "none")
        relation_weight = str(summary.get("current_weight") or "low")
        relation_signal = str(summary.get("current_signal") or "")[:120]
    except Exception:
        pass

    absence_active = False
    idle_hours = 0.0
    return_context_present = False
    try:
        from core.services.absence_awareness import (
            build_absence_awareness_surface,
        )

        absence = build_absence_awareness_surface()
        idle_hours = float(absence.get("idle_hours") or 0.0)
        threshold = float(absence.get("threshold_hours") or 0.0)
        return_context_present = bool(absence.get("return_context")) and bool(
            absence.get("return_brief")
        )
        absence_active = bool(absence.get("absence_active")) or (
            idle_hours >= threshold and threshold > 0
        )
    except Exception:
        pass

    return {
        "dream_carry": dream_carry,
        "dream_state": dream_state,
        "relation_active": relation_active,
        "relation_state": relation_state,
        "relation_weight": relation_weight,
        "relation_signal": relation_signal,
        "absence_active": absence_active,
        "idle_hours": idle_hours,
        "return_context_present": return_context_present,
    }


def _derive_longing_awareness(
    *,
    temporal_feel: dict[str, object],
    mineness: dict[str, object],
    support_stream: dict[str, object],
    inner_voice: dict[str, object],
    sources: dict[str, object],
    longing_sources: dict[str, object],
) -> dict[str, object]:
    """Derive a bounded longing/absence surface from existing runtime truth."""
    temporal_state = str(temporal_feel.get("temporal_state") or "immediate")
    return_signal = bool(temporal_feel.get("return_signal"))

    ownership_state = str(mineness.get("ownership_state") or "ambient")
    self_relevance = str(mineness.get("self_relevance") or "merely-present")
    carried_thread_count = int(mineness.get("carried_thread_count") or 0)
    return_ownership = bool(mineness.get("return_ownership"))

    voice = inner_voice.get("last_result") or {}
    voice_mode = str(voice.get("mode") or "")
    voice_created = bool(voice.get("inner_voice_created"))
    pulled_voice = voice_created and voice_mode in _LONGING_CARRY_VOICES

    stream_state = str(support_stream.get("stream_state") or "baseline")
    opening_stream = stream_state == "opening"

    brain_active = bool(sources.get("brain_active"))
    open_loop_count = int(sources.get("open_loop_open_count") or 0)
    carried_threads = carried_thread_count > 0 or brain_active or open_loop_count > 0

    dream_carry = bool(longing_sources.get("dream_carry"))
    relation_active = bool(longing_sources.get("relation_active"))
    relation_weight = str(longing_sources.get("relation_weight") or "low")
    relation_near = relation_active and relation_weight in _LONGING_RELATION_NEAR_WEIGHTS
    absence_active = bool(longing_sources.get("absence_active"))

    owned_state = ownership_state in _LONGING_OWNED_STATES
    personally_salient = self_relevance in _LONGING_NEAR_RELEVANCE
    temporal_extended = temporal_state in _LONGING_EXTENDED_TEMPORAL
    returning_thread = return_signal or return_ownership
    absence_basis = absence_active or temporal_extended or opening_stream

    strong_signals = sum(
        [
            int(relation_near),
            int(carried_threads and (owned_state or personally_salient)),
            int(dream_carry),
            int(temporal_extended),
            int(pulled_voice),
        ]
    )

    if returning_thread and (carried_threads or relation_near or dream_carry):
        longing_state = "returning-pull"
    elif relation_near and absence_basis and strong_signals >= 3:
        longing_state = "aching"
    elif absence_basis and carried_threads and (
        personally_salient or owned_state or dream_carry or pulled_voice
    ):
        longing_state = "yearning"
    elif absence_basis and (carried_threads or relation_near or dream_carry):
        longing_state = "missing"
    else:
        longing_state = "quiet"

    if longing_state == "quiet":
        absence_relation = "none"
    elif returning_thread:
        absence_relation = "returning-through-absence"
    elif relation_near and absence_basis:
        absence_relation = "emotionally-near"
    elif carried_threads or dream_carry:
        absence_relation = "carried-in-absence"
    else:
        absence_relation = "simply-absent"

    if longing_state == "quiet":
        longing_source = "none"
    elif returning_thread:
        longing_source = "temporal-return"
    elif relation_near and absence_basis:
        longing_source = "unresolved-relational-absence"
    elif dream_carry:
        longing_source = "dream-carry"
    elif owned_state or personally_salient:
        longing_source = "owned-thread"
    else:
        longing_source = "carried-thread"

    narrative = _longing_narrative(
        longing_state=longing_state,
        absence_relation=absence_relation,
        longing_source=longing_source,
    )

    return {
        "longing_state": longing_state,
        "absence_relation": absence_relation,
        "longing_source": longing_source,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "longing-awareness",
    }


def _longing_narrative(
    *,
    longing_state: str,
    absence_relation: str,
    longing_source: str,
) -> str:
    """Compact longing narrative. Empty when quiet."""
    if longing_state == "quiet":
        return ""
    if longing_state == "returning-pull":
        if longing_source == "temporal-return":
            return "Absent thread returning, pulling to be resumed."
        return "Carried absence turning into return signal."
    if longing_state == "aching":
        if longing_source == "unresolved-relational-absence":
            return "Relational thread absent but still near."
        if longing_source == "dream-carry":
            return "Dream layer pressing as active absence."
        return "Absence carried with more weight than can settle."
    if longing_state == "yearning":
        if longing_source == "owned-thread":
            return "Prior owned thread wants to be taken up again."
        if longing_source == "dream-carry":
            return "Dream-carried strand absent without feeling gone."
        return "Carried thread active even while absent."
    if absence_relation == "emotionally-near":
        return "Missing presence still close enough to shape direction."
    return "Absence actively felt."


def build_longing_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for longing awareness."""
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
        longing_sources = _longing_source_snapshot()
        longing = _facade()._derive_longing_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            inner_voice=inner_voice,
            sources=sources,
            longing_sources=longing_sources,
        )
    except Exception:
        return None

    state = str(longing.get("longing_state") or "quiet")
    if state == "quiet":
        return None

    lines = [
        "Longing awareness (bounded runtime truth, internal-only):",
        (
            f"- longing_state={state}"
            f" | relation={longing.get('absence_relation') or 'none'}"
            f" | source={longing.get('longing_source') or 'none'}"
        ),
    ]
    narrative = str(longing.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- longing_narrative={narrative}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Relation continuity as self-truth
# ---------------------------------------------------------------------------


def _relation_continuity_self_source_snapshot() -> dict[str, object]:
    """Gather bounded substrates for relation continuity as self-truth."""
    relation_active = False
    relation_state = "none"
    relation_weight = "low"
    relation_alignment = "working-alignment"
    relation_signal = ""
    relation_anchor = ""
    try:
        from core.services.relation_continuity_signal_tracking import (
            build_runtime_relation_continuity_signal_surface,
        )

        relation = build_runtime_relation_continuity_signal_surface(limit=4)
        summary = relation.get("summary") or {}
        items = relation.get("items") or []
        latest = items[0] if items else {}
        relation_active = bool(relation.get("active"))
        relation_state = str(
            summary.get("current_state")
            or latest.get("continuity_state")
            or "none"
        )
        relation_weight = str(
            summary.get("current_weight")
            or latest.get("continuity_weight")
            or "low"
        )
        relation_alignment = str(
            summary.get("current_alignment")
            or latest.get("continuity_alignment")
            or "working-alignment"
        )
        relation_signal = str(
            summary.get("current_signal") or latest.get("title") or ""
        )[:120]
        relation_anchor = str(
            latest.get("source_anchor") or relation_signal or latest.get("summary") or ""
        )[:140]
    except Exception:
        pass

    absence_active = False
    return_context_present = False
    idle_hours = 0.0
    try:
        from core.services.absence_awareness import (
            build_absence_awareness_surface,
        )

        absence = build_absence_awareness_surface()
        absence_active = bool(absence.get("absence_active"))
        return_context_present = bool(absence.get("return_brief")) and bool(
            absence.get("return_context")
        )
        idle_hours = float(absence.get("idle_hours") or 0.0)
    except Exception:
        pass

    chronicle_active = False
    diary_active = False
    try:
        sources = _facade()._self_insight_source_snapshot()
        chronicle_active = bool(sources.get("chronicle_active"))
        diary_active = bool(sources.get("diary_active"))
    except Exception:
        pass

    return {
        "relation_active": relation_active,
        "relation_state": relation_state,
        "relation_weight": relation_weight,
        "relation_alignment": relation_alignment,
        "relation_signal": relation_signal,
        "relation_anchor": relation_anchor,
        "absence_active": absence_active,
        "return_context_present": return_context_present,
        "idle_hours": idle_hours,
        "chronicle_active": chronicle_active,
        "diary_active": diary_active,
    }


def _derive_relation_continuity_self_awareness(
    *,
    temporal_feel: dict[str, object],
    mineness: dict[str, object],
    longing: dict[str, object],
    relation_sources: dict[str, object],
) -> dict[str, object]:
    """Derive a small runtime truth when relation continuity touches the self-stream."""
    temporal_state = str(temporal_feel.get("temporal_state") or "immediate")
    return_signal = bool(temporal_feel.get("return_signal"))

    ownership_state = str(mineness.get("ownership_state") or "ambient")
    self_relevance = str(mineness.get("self_relevance") or "merely-present")
    carried_thread_count = int(mineness.get("carried_thread_count") or 0)
    return_ownership = bool(mineness.get("return_ownership"))

    longing_state = str(longing.get("longing_state") or "quiet")
    absence_relation = str(longing.get("absence_relation") or "none")

    relation_active = bool(relation_sources.get("relation_active"))
    relation_state = str(relation_sources.get("relation_state") or "none")
    relation_weight = str(relation_sources.get("relation_weight") or "low")
    relation_anchor = str(
        relation_sources.get("relation_anchor")
        or relation_sources.get("relation_signal")
        or ""
    ).strip()
    absence_active = bool(relation_sources.get("absence_active"))
    return_context_present = bool(relation_sources.get("return_context_present"))
    chronicle_active = bool(relation_sources.get("chronicle_active"))
    diary_active = bool(relation_sources.get("diary_active"))

    relation_present = relation_active or relation_state not in {"", "none"}
    relation_strong = relation_weight in {"medium", "high"}
    ownership_near = (
        ownership_state in _RELATION_SELF_NEAR_OWNERSHIP
        or self_relevance in _RELATION_SELF_NEAR_RELEVANCE
        or carried_thread_count > 0
    )
    relational_longing = (
        longing_state in _RELATION_SELF_ACTIVE_LONGING
        and absence_relation in _RELATION_SELF_RELATIONAL_ABSENCE
    )
    return_pattern = (
        return_context_present
        or absence_active
        and temporal_state == "returning"
        or return_signal
        or return_ownership
    )
    chronicle_resonance = chronicle_active or diary_active

    signal_count = sum(
        [
            int(relation_present),
            int(relation_strong),
            int(ownership_near),
            int(relational_longing),
            int(return_pattern),
            int(chronicle_resonance),
        ]
    )

    if not relation_present and not (relational_longing and absence_active):
        relation_continuity_state = "quiet"
    elif return_pattern and relation_present and (
        ownership_near or relational_longing or relation_strong
    ):
        relation_continuity_state = "rejoining"
    elif relation_present and relation_strong and signal_count >= 4:
        relation_continuity_state = "enduring"
    elif relation_present and (
        ownership_near or relational_longing or chronicle_resonance or absence_active
    ):
        relation_continuity_state = "carried"
    else:
        relation_continuity_state = "present"

    if relation_continuity_state == "quiet":
        relation_self_relation = "incidental"
    elif relation_continuity_state == "present":
        relation_self_relation = (
            "self-relevant" if (ownership_near or relational_longing or relation_strong) else "incidental"
        )
    elif relation_continuity_state == "carried":
        relation_self_relation = (
            "continuity-bearing" if (ownership_near or chronicle_resonance) else "self-relevant"
        )
    elif relation_continuity_state == "enduring":
        relation_self_relation = (
            "identity-touching" if (chronicle_resonance or relational_longing) else "continuity-bearing"
        )
    else:  # rejoining
        relation_self_relation = (
            "identity-touching" if (chronicle_resonance and ownership_near) else "continuity-bearing"
        )

    if relation_continuity_state == "quiet":
        relation_continuity_source = "none"
    elif relation_continuity_state == "rejoining":
        relation_continuity_source = "absence-return-pattern"
    elif chronicle_resonance and relation_present and relation_continuity_state in {
        "carried",
        "enduring",
    }:
        relation_continuity_source = "chronicle-diary-resonance"
    elif relational_longing and ownership_near:
        relation_continuity_source = "longing-ownership-bridge"
    elif relation_present and ownership_near:
        relation_continuity_source = "recurring-carried-relation"
    elif relation_present:
        relation_continuity_source = "relation-continuity-signal"
    else:
        relation_continuity_source = "absence-return-pattern"

    narrative = _relation_continuity_self_narrative(
        relation_continuity_state=relation_continuity_state,
        relation_self_relation=relation_self_relation,
        relation_continuity_source=relation_continuity_source,
        relation_anchor=relation_anchor,
    )

    return {
        "relation_continuity_state": relation_continuity_state,
        "relation_self_relation": relation_self_relation,
        "relation_continuity_source": relation_continuity_source,
        "continuity_anchor": relation_anchor[:120] if relation_anchor else "",
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "relation-continuity-self-awareness",
    }


def _relation_continuity_self_narrative(
    *,
    relation_continuity_state: str,
    relation_self_relation: str,
    relation_continuity_source: str,
    relation_anchor: str,
) -> str:
    """Compact relation continuity narrative. Empty when quiet."""
    if relation_continuity_state == "quiet":
        return ""

    anchor = relation_anchor[:80].strip()
    anchor_clause = f" around {anchor}" if anchor else ""

    if relation_continuity_state == "rejoining":
        return f"Relation thread{anchor_clause} returning as continuity, not fresh event."
    if relation_continuity_state == "enduring":
        if relation_continuity_source == "chronicle-diary-resonance":
            return f"Relation{anchor_clause} holding long enough to shape my continuity."
        return f"Relation thread{anchor_clause} pressing back across time."
    if relation_continuity_state == "carried":
        if relation_self_relation == "continuity-bearing":
            return f"Relation{anchor_clause} carried as ongoing continuity."
        return f"Relation thread{anchor_clause} no longer incidental."
    return f"Relation thread{anchor_clause} present, not episodic."


def build_relation_continuity_self_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for relation continuity as self-truth."""
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
        longing_sources = _longing_source_snapshot()
        longing = _facade()._derive_longing_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            inner_voice=inner_voice,
            sources=sources,
            longing_sources=longing_sources,
        )
        relation_self = _derive_relation_continuity_self_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness,
            longing=longing,
            relation_sources=_facade()._relation_continuity_self_source_snapshot(),
        )
    except Exception:
        return None

    state = str(relation_self.get("relation_continuity_state") or "quiet")
    if state == "quiet":
        return None

    lines = [
        "Relation continuity as self-truth (bounded runtime truth, internal-only):",
        (
            f"- relation_continuity_state={state}"
            f" | self_relation={relation_self.get('relation_self_relation') or 'incidental'}"
            f" | source={relation_self.get('relation_continuity_source') or 'none'}"
        ),
    ]
    anchor = str(relation_self.get("continuity_anchor") or "").strip()
    if anchor:
        lines.append(f"- relation_anchor={anchor[:100]}")
    narrative = str(relation_self.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- relation_continuity_narrative={narrative}")
    return "\n".join(lines)


__all__ = [
    '_FLOW_PRESSURE_BREAKS',
    '_FLOW_PRESSURE_ELEVATED',
    '_LONGING_CARRY_VOICES',
    '_LONGING_EXTENDED_TEMPORAL',
    '_LONGING_NEAR_RELEVANCE',
    '_LONGING_OWNED_STATES',
    '_LONGING_RELATION_NEAR_WEIGHTS',
    '_RELATION_SELF_ACTIVE_LONGING',
    '_RELATION_SELF_NEAR_OWNERSHIP',
    '_RELATION_SELF_NEAR_RELEVANCE',
    '_RELATION_SELF_RELATIONAL_ABSENCE',
    '_WONDER_DEEP_FLOW',
    '_WONDER_EXPLORATORY_VOICES',
    '_WONDER_EXTENDED_TEMPORAL',
    '_WONDER_OWNED_RELEVANCE',
    '_WONDER_OWNED_STATES',
    '_derive_flow_state_awareness',
    '_derive_longing_awareness',
    '_derive_relation_continuity_self_awareness',
    '_derive_wonder_awareness',
    '_flow_narrative',
    '_longing_narrative',
    '_longing_source_snapshot',
    '_relation_continuity_self_narrative',
    '_relation_continuity_self_source_snapshot',
    '_wonder_narrative',
    '_wonder_source_snapshot',
    'build_flow_state_awareness_prompt_section',
    'build_longing_awareness_prompt_section',
    'build_relation_continuity_self_awareness_prompt_section',
    'build_wonder_awareness_prompt_section',
]
