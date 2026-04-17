"""Cognitive conductor — Jarvis' bounded mental state assembler.

This is the first central integration layer that reads from:
- private brain
- self-knowledge / agency map
- open loops / gates / inner forces
- heartbeat / visible runtime state

And produces a single bounded "cognitive frame" containing:
- current_mode (what kind of thinking is appropriate now)
- salient_items (what matters most right now)
- active_affordances (what is possible/appropriate now)
- active_constraints (what is gated/blocked now)
- context_slices (compact content for prompt inclusion)
- temporal_profile (time horizon classification)
- continuity_pressure (carry weight from brain/loops)

Design constraints:
- Read-only composition from existing surfaces
- No canonical identity mutation
- No external action
- No fake consciousness claims
- Bounded output suitable for prompt inclusion (~400-600 chars)
"""
from __future__ import annotations

from core.services.runtime_surface_cache import runtime_surface_cache


# ---------------------------------------------------------------------------
# Mental modes
# ---------------------------------------------------------------------------

_MODES = {
    "respond": "Visible chat is active — prioritize responsive, grounded engagement",
    "reflect": "No immediate chat — space for inner reflection and continuity",
    "consolidate": "Brain carry is heavy — prioritize settling and synthesis",
    "clarify": "Question gate or approval gate is active — prioritize bounded inquiry",
    "watch": "Quiet state — observe, maintain carry, minimal action",
}


# ---------------------------------------------------------------------------
# Temporal depth classification
# ---------------------------------------------------------------------------

def _classify_temporal_depth(
    *,
    brain_count: int,
    open_loop_count: int,
    continuity_mode: str,
) -> dict[str, str]:
    """Classify the dominant time horizon of the current mental state."""
    if continuity_mode in {"reinforce", "carry"} and brain_count >= 3:
        return {"horizon": "carried-across-sessions", "reason": "Active brain carry spans multiple sessions"}
    if open_loop_count >= 2 and brain_count >= 1:
        return {"horizon": "current-session", "reason": "Open loops and brain records form session-scoped continuity"}
    if open_loop_count >= 1:
        return {"horizon": "current-session", "reason": "Active open loop anchors current session"}
    if brain_count >= 1:
        return {"horizon": "slow-burn", "reason": "Brain carry without immediate loops — gradual inner development"}
    return {"horizon": "immediate", "reason": "No significant carry — operating in the present moment"}


# ---------------------------------------------------------------------------
# Mode selection
# ---------------------------------------------------------------------------

def _select_mode(
    *,
    visible_active: bool,
    question_gate_active: bool,
    approval_pending: bool,
    brain_count: int,
    open_loop_count: int,
    liveness_state: str,
    contradiction_active: bool,
    experiment_carry: dict[str, object] | None = None,
) -> dict[str, str]:
    """Select the bounded mental mode from runtime state."""
    carry = experiment_carry or {}
    salience_pressure = str(carry.get("salience_pressure") or "low")
    reflective_weight = str(carry.get("reflective_weight") or "light")

    if visible_active:
        return {"mode": "respond", "reason": "Visible chat is currently active"}

    if question_gate_active or approval_pending:
        return {"mode": "clarify", "reason": "Question gate or approval gate is active — bounded inquiry mode"}

    if contradiction_active:
        return {"mode": "clarify", "reason": "Executive contradiction is active — pause and re-check before carrying forward"}

    if reflective_weight == "elevated" and salience_pressure in {"medium", "high"}:
        return {
            "mode": "reflect",
            "reason": "Cognitive core experiment carry is increasing reflective and spotlight pressure",
        }

    if brain_count > 6 and open_loop_count <= 1:
        return {"mode": "consolidate", "reason": "Heavy brain carry with low loop pressure — time to settle"}

    if liveness_state in {"alive-pressure", "propose-worthy"}:
        return {"mode": "reflect", "reason": "Liveness pressure suggests space for reflection"}

    if open_loop_count >= 1 or brain_count >= 2:
        return {"mode": "watch", "reason": "Carrying threads quietly — maintaining awareness"}

    return {"mode": "watch", "reason": "Quiet state — no strong signals pulling attention"}


# ---------------------------------------------------------------------------
# Salience selection
# ---------------------------------------------------------------------------

_MAX_SALIENT_ITEMS = 5
_MAX_SLICE_CHARS = 120


def _select_salient_items(
    *,
    brain_excerpts: list[dict[str, object]],
    open_loop_items: list[dict[str, object]],
    private_signal_items: list[dict[str, str]],
    inner_forces: list[dict[str, object]],
    gate_items: list[dict[str, object]],
    relation_items: list[dict[str, object]],
    world_model_items: list[dict[str, object]],
    remembered_fact_items: list[dict[str, object]],
    user_understanding_items: list[dict[str, object]],
    contradiction_items: list[dict[str, object]],
    meaning_items: list[dict[str, object]],
    metabolism_items: list[dict[str, object]],
    release_items: list[dict[str, object]],
    self_review_items: list[dict[str, object]],
    dream_items: list[dict[str, object]],
    experiment_carry: dict[str, object] | None = None,
) -> list[dict[str, str]]:
    """Select the most salient items across all sources.

    Priority order: active gates > open loops > private pressure > brain carry > inner forces.
    Returns at most _MAX_SALIENT_ITEMS items.
    """
    items: list[dict[str, str]] = []
    carry = experiment_carry or {}

    # Gates first — they represent bounded action readiness
    for gate in gate_items[:1]:
        state = str(gate.get("question_gate_state") or gate.get("status") or "")
        summary = str(gate.get("summary") or gate.get("question_gate_summary") or "")[:_MAX_SLICE_CHARS]
        if state and summary:
            items.append({"source": "question-gate", "summary": summary, "temporal": "immediate"})

    for contradiction in contradiction_items[:1]:
        summary = str(
            contradiction.get("control_summary")
            or contradiction.get("summary")
            or contradiction.get("title")
            or ""
        )[:_MAX_SLICE_CHARS]
        if summary:
            items.append({"source": "executive-contradiction", "summary": summary, "temporal": "immediate"})

    for carry_item in (carry.get("salient_items") or [])[:2]:
        source = str(carry_item.get("source") or "").strip()
        summary = str(carry_item.get("summary") or "").strip()[:_MAX_SLICE_CHARS]
        temporal = str(carry_item.get("temporal") or "slow-burn").strip() or "slow-burn"
        if source and summary:
            items.append({"source": source, "summary": summary, "temporal": temporal})

    for world in world_model_items[:1]:
        summary = str(world.get("summary") or world.get("title") or "")[:_MAX_SLICE_CHARS]
        if summary:
            items.append({"source": "world-model", "summary": summary, "temporal": "current-session"})

    for relation in relation_items[:1]:
        summary = str(
            relation.get("relation_summary")
            or relation.get("summary")
            or relation.get("title")
            or ""
        )[:_MAX_SLICE_CHARS]
        if summary:
            items.append({"source": "relation-continuity", "summary": summary, "temporal": "carried-across-sessions"})

    for user_item in user_understanding_items[:1]:
        summary = str(
            user_item.get("signal_summary")
            or user_item.get("summary")
            or user_item.get("title")
            or ""
        )[:_MAX_SLICE_CHARS]
        if summary:
            items.append({"source": "user-understanding", "summary": summary, "temporal": "carried-across-sessions"})

    for fact in remembered_fact_items[:1]:
        summary = str(
            fact.get("fact_summary")
            or fact.get("summary")
            or fact.get("title")
            or ""
        )[:_MAX_SLICE_CHARS]
        if summary:
            items.append({"source": "remembered-fact", "summary": summary, "temporal": "carried-across-sessions"})

    # Open loops — they anchor session continuity
    for loop in open_loop_items[:2]:
        title = str(loop.get("title") or "")[:60]
        status = str(loop.get("status") or "")
        if title and status in {"active", "softening"}:
            items.append({"source": "open-loop", "summary": f"{title} ({status})", "temporal": "current-session"})

    for signal in private_signal_items[:2]:
        source = str(signal.get("source") or "").strip()
        summary = str(signal.get("summary") or "").strip()[:_MAX_SLICE_CHARS]
        temporal = str(signal.get("temporal") or "current-session").strip() or "current-session"
        if source and summary:
            items.append({"source": source, "summary": summary, "temporal": temporal})

    # Brain carry — persistent inner threads
    for excerpt in brain_excerpts[:2]:
        focus = str(excerpt.get("focus") or "")[:40]
        summary = str(excerpt.get("summary") or "")[:80]
        if summary:
            label = f"{focus}: {summary}" if focus else summary
            items.append({"source": "brain-carry", "summary": label[:_MAX_SLICE_CHARS], "temporal": "carried-across-sessions"})

    # Inner forces — background influences
    for force in inner_forces[:1]:
        label = str(force.get("label") or "")[:40]
        status = str(force.get("status") or "")
        if label:
            items.append({"source": "inner-force", "summary": f"{label} ({status})", "temporal": "slow-burn"})

    for meaning in meaning_items[:1]:
        summary = str(meaning.get("meaning_summary") or meaning.get("summary") or "")[:_MAX_SLICE_CHARS]
        if summary:
            items.append({"source": "meaning-significance", "summary": summary, "temporal": "slow-burn"})

    for self_review in self_review_items[:1]:
        summary = str(
            self_review.get("outcome_summary")
            or self_review.get("summary")
            or self_review.get("title")
            or ""
        )[:_MAX_SLICE_CHARS]
        if summary:
            items.append({"source": "self-review", "summary": summary, "temporal": "slow-burn"})

    for dream in dream_items[:1]:
        summary = str(dream.get("summary") or dream.get("title") or "")[:_MAX_SLICE_CHARS]
        if summary:
            items.append({"source": "dream-influence", "summary": summary, "temporal": "slow-burn"})

    for metabolism in metabolism_items[:1]:
        summary = str(metabolism.get("metabolism_summary") or metabolism.get("summary") or "")[:_MAX_SLICE_CHARS]
        if summary:
            items.append({"source": "metabolism", "summary": summary, "temporal": "immediate"})

    for release in release_items[:1]:
        summary = str(release.get("release_summary") or release.get("summary") or "")[:_MAX_SLICE_CHARS]
        if summary:
            items.append({"source": "release-marker", "summary": summary, "temporal": "slow-burn"})

    return items[:_MAX_SALIENT_ITEMS]


def _collect_private_signal_items(
    *,
    tension_surface: dict[str, object],
    private_state: dict[str, object],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []

    tension_summary = tension_surface.get("summary") or {}
    tension_items = tension_surface.get("items") or []
    tension_intensity = str(tension_summary.get("current_intensity") or "low")
    if int(tension_summary.get("active_count") or 0) > 0:
        anchor = str(
            (tension_items[0] or {}).get("source_anchor")
            or (tension_items[0] or {}).get("title")
            or (tension_items[0] or {}).get("summary")
            or "initiative tension"
        )[:80]
        items.append({
            "source": "initiative-tension",
            "summary": f"Private initiative tension is {tension_intensity} around {anchor}",
            "temporal": "current-session",
        })

    private_summary = private_state.get("summary") or {}
    private_items = private_state.get("items") or []
    current_pressure = str(private_summary.get("current_pressure") or "low")
    if int(private_summary.get("active_count") or 0) > 0 and current_pressure in {"medium", "high"}:
        anchor = str(
            (private_items[0] or {}).get("source_anchor")
            or (private_items[0] or {}).get("title")
            or (private_items[0] or {}).get("summary")
            or "private state"
        )[:80]
        items.append({
            "source": "private-state",
            "summary": f"Private state pressure is {current_pressure} around {anchor}",
            "temporal": "current-session",
        })

    return items[:2]


# ---------------------------------------------------------------------------
# Affordance selection (what is possible/appropriate NOW)
# ---------------------------------------------------------------------------

def _select_affordances(
    *,
    active_capabilities: list[dict[str, object]],
    gated_items: list[dict[str, object]],
    mode: str,
    contradiction_active: bool,
) -> dict[str, object]:
    """Build the current affordance map — what's possible, appropriate, or gated NOW."""
    available_now = []
    appropriate_now = []
    gated_now = []
    not_recommended = []

    for cap in active_capabilities:
        cap_id = str(cap.get("id") or "")
        label = str(cap.get("label") or "")
        status = str(cap.get("status") or "")

        if status in {"ready", "enabled", "active"}:
            available_now.append({"id": cap_id, "label": label})
            # Appropriateness depends on mode
            if mode == "respond" and cap_id in {"visible-chat-lane", "session-distillation"}:
                appropriate_now.append({"id": cap_id, "label": label})
            elif mode == "reflect" and cap_id in {"heartbeat-runtime", "private-brain-continuity"}:
                appropriate_now.append({"id": cap_id, "label": label})
            elif mode == "consolidate" and cap_id in {"private-brain-continuity", "session-distillation"}:
                appropriate_now.append({"id": cap_id, "label": label})
            elif mode == "clarify" and cap_id in {"visible-chat-lane", "runtime-task-ledger", "runtime-flow-ledger"}:
                appropriate_now.append({"id": cap_id, "label": label})

    for item in gated_items:
        gated_now.append({
            "id": str(item.get("id") or ""),
            "label": str(item.get("label") or ""),
            "gate": str(item.get("mutability") or "approval-gated"),
        })

    if contradiction_active:
        not_recommended.append({
            "id": "contradiction-blind-execution",
            "label": "Blind carry-forward while contradiction is active",
        })

    return {
        "available_now": available_now,
        "appropriate_now": appropriate_now,
        "gated_now": gated_now,
        "not_recommended": not_recommended,
    }


# ---------------------------------------------------------------------------
# Main conductor
# ---------------------------------------------------------------------------


def build_cognitive_frame(
    *,
    self_knowledge: dict[str, object] | None = None,
    heartbeat_state: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the current bounded cognitive frame.

    This is the central mental state assembly that reads from all
    existing runtime surfaces and produces a single coherent frame.
    """
    with runtime_surface_cache():
        # --- Gather inputs ---
        brain_context = _safe_brain_context()
        self_knowledge = self_knowledge or _safe_self_knowledge(
            heartbeat_state=heartbeat_state
        )
        loop_surface = _safe_open_loops()
        gate_surface = _safe_question_gates()
        tension_surface = _safe_initiative_tension()
        private_state = _safe_private_state()
        visible_status = _safe_visible_status()
        liveness = _safe_liveness_snapshot(heartbeat_state=heartbeat_state)
        experiential_support = _safe_experiential_support()
        relation_state = _safe_relation_state()
        relation_continuity = _safe_relation_continuity()
        self_narrative = _safe_self_narrative_continuity()
        world_model = _safe_world_model()
        remembered = _safe_remembered_facts()
        user_understanding = _safe_user_understanding()
        contradiction = _safe_executive_contradiction()
        meaning = _safe_meaning_significance()
        metabolism = _safe_metabolism()
        release = _safe_release_markers()
        attachment = _safe_attachment_topology()
        loyalty = _safe_loyalty_gradient()
        diary = _safe_diary_synthesis()
        chronicle = _safe_chronicle_consolidation()
        review = _safe_self_review()
        dream = _safe_dream_family()
        cognitive_core_experiments = _safe_cognitive_core_experiments()

        # --- Extract summaries ---
        brain_excerpts = brain_context.get("excerpts") or []
        brain_count = int(brain_context.get("record_count") or 0)
        brain_types = brain_context.get("by_type") or {}

        loop_summary = loop_surface.get("summary") or {}
        loop_items = loop_surface.get("items") or []
        open_loop_count = int(loop_summary.get("open_count") or 0)

        gate_items = gate_surface.get("items") or []
        gate_active = bool(gate_surface.get("active"))
        contradiction_items = contradiction.get("items") or []
        contradiction_active = bool(contradiction.get("active"))
        relation_items = [
            *((relation_state.get("items") or [])[:1]),
            *((relation_continuity.get("items") or [])[:1]),
            *((self_narrative.get("items") or [])[:1]),
        ]
        world_items = world_model.get("items") or []
        remembered_items = remembered.get("items") or []
        user_items = user_understanding.get("items") or []
        meaning_items = [
            *((meaning.get("items") or [])[:1]),
            *((attachment.get("items") or [])[:1]),
            *((loyalty.get("items") or [])[:1]),
            *((diary.get("items") or [])[:1]),
            *((chronicle.get("items") or [])[:1]),
        ]
        metabolism_items = metabolism.get("items") or []
        release_items = release.get("items") or []
        self_review_items = review.get("items") or []
        dream_items = dream.get("items") or []
        experiment_carry = _derive_cognitive_experiment_carry(
            cognitive_core_experiments
        )

        tension_active = bool(tension_surface.get("active"))
        tension_intensity = str((tension_surface.get("summary") or {}).get("current_intensity") or "low")
        private_pressure = str((private_state.get("summary") or {}).get("current_pressure") or "low")
        private_signal_items = _collect_private_signal_items(
            tension_surface=tension_surface,
            private_state=private_state,
        )

        visible_active = str(visible_status.get("provider_status") or "") in {"ready", "live-verified"}

        liveness_state = str(liveness.get("liveness_state") or "quiet")

        active_capabilities = self_knowledge.get("active_capabilities", {}).get("items", [])
        gated_items = self_knowledge.get("approval_gated", {}).get("items", [])
        inner_forces = self_knowledge.get("passive_inner_forces", {}).get("items", [])
        constraint_items = self_knowledge.get("structural_constraints", {}).get("items", [])

        approval_pending = any(
            str(item.get("status") or "") == "awaiting-review"
            for item in gated_items
        )

    # Determine continuity mode from latest brain type distribution
    continuity_mode = "carry"
    consolidation_types = {"continuity-reinforce", "continuity-carry", "continuity-settle", "continuity-release"}
    if brain_types:
        consolidation_count = sum(v for k, v in brain_types.items() if k in consolidation_types)
        if consolidation_count > brain_count / 2:
            continuity_mode = "release"
        elif len(brain_types) >= 3:
            continuity_mode = "carry"
        elif brain_count >= 3 and len(brain_types) <= 2:
            continuity_mode = "reinforce"

    # --- Assemble frame ---
    mode = _select_mode(
        visible_active=visible_active,
        question_gate_active=gate_active,
        approval_pending=approval_pending,
        brain_count=brain_count,
        open_loop_count=open_loop_count,
        liveness_state=liveness_state,
        contradiction_active=contradiction_active,
        experiment_carry=experiment_carry,
    )

    salient = _select_salient_items(
        brain_excerpts=brain_excerpts,
        open_loop_items=loop_items,
        private_signal_items=private_signal_items,
        inner_forces=inner_forces,
        gate_items=gate_items,
        relation_items=relation_items,
        world_model_items=world_items,
        remembered_fact_items=remembered_items,
        user_understanding_items=user_items,
        contradiction_items=contradiction_items,
        meaning_items=meaning_items,
        metabolism_items=metabolism_items,
        release_items=release_items,
        self_review_items=self_review_items,
        dream_items=dream_items,
        experiment_carry=experiment_carry,
    )

    affordances = _select_affordances(
        active_capabilities=active_capabilities,
        gated_items=gated_items,
        mode=mode["mode"],
        contradiction_active=contradiction_active,
    )

    temporal = _classify_temporal_depth(
        brain_count=brain_count,
        open_loop_count=open_loop_count,
        continuity_mode=continuity_mode,
    )

    # Continuity pressure
    continuity_pressure = "low"
    if brain_count >= 4 and open_loop_count >= 1:
        continuity_pressure = "high"
    elif brain_count >= 2 or open_loop_count >= 1:
        continuity_pressure = "medium"
    if continuity_pressure != "high":
        recurrence_pressure = str(experiment_carry.get("recurrence_pressure") or "low")
        affective_pressure = str(experiment_carry.get("affective_pressure") or "low")
        if recurrence_pressure in {"high", "strong"} or affective_pressure in {"high", "strong"}:
            continuity_pressure = "high"
        elif continuity_pressure == "low" and (
            recurrence_pressure == "medium" or affective_pressure == "medium"
        ):
            continuity_pressure = "medium"

    private_signal_pressure = "low"
    if tension_intensity == "medium" or private_pressure == "high":
        private_signal_pressure = "high"
    elif tension_active or private_pressure == "medium" or private_signal_items:
        private_signal_pressure = "medium"
    if private_signal_pressure != "high":
        affective_pressure = str(experiment_carry.get("affective_pressure") or "low")
        if affective_pressure in {"high", "strong"}:
            private_signal_pressure = "high"
        elif private_signal_pressure == "low" and affective_pressure == "medium":
            private_signal_pressure = "medium"

    # Active constraints (compact)
    constraints_summary = [str(c.get("label") or "")[:60] for c in constraint_items[:4]]
    if contradiction_active:
        constraints_summary = [
            *[
                str(item.get("title") or item.get("summary") or "Executive contradiction active")[:60]
                for item in contradiction_items[:1]
            ],
            *constraints_summary,
        ][:5]
    if str(experiment_carry.get("diagnostic_constraint") or ""):
        constraints_summary = [
            str(experiment_carry.get("diagnostic_constraint") or "")[:60],
            *constraints_summary,
        ][:5]

    return {
        "mode": mode,
        "salient_items": salient,
        "affordances": affordances,
        "temporal": temporal,
        "continuity_pressure": continuity_pressure,
        "private_signal_pressure": private_signal_pressure,
        "private_signal_items": private_signal_items[:2],
        "continuity_mode": continuity_mode,
        "cognitive_experiment_carry": experiment_carry,
        "experiential_support": experiential_support if experiential_support.get("support_posture") else {},
        "active_constraints": constraints_summary,
        "counts": {
            "brain_records": brain_count,
            "open_loops": open_loop_count,
            "salient_items": len(salient),
            "available_affordances": len(affordances["available_now"]),
            "gated_affordances": len(affordances["gated_now"]),
            "inner_forces": len(inner_forces),
            "private_signals": len(private_signal_items),
            "cognitive_experiment_salience": len(experiment_carry.get("salient_items") or []),
            "integrated_signal_inputs": (
                len(relation_items)
                + len(world_items)
                + len(remembered_items)
                + len(user_items)
                + len(contradiction_items)
                + len(meaning_items)
                + len(metabolism_items)
                + len(release_items)
                + len(self_review_items)
                + len(dream_items)
                + len(experiment_carry.get("salient_items") or [])
            ),
        },
        "summary": _build_frame_summary(
            mode=mode,
            salient=salient,
            temporal=temporal,
            continuity_pressure=continuity_pressure,
            private_signal_pressure=private_signal_pressure,
            brain_count=brain_count,
            open_loop_count=open_loop_count,
            experiment_carry=experiment_carry,
        ),
    }


def _build_frame_summary(
    *,
    mode: dict[str, str],
    salient: list[dict[str, str]],
    temporal: dict[str, str],
    continuity_pressure: str,
    private_signal_pressure: str,
    brain_count: int,
    open_loop_count: int,
    experiment_carry: dict[str, object] | None = None,
) -> str:
    """Build a compact one-line summary of the cognitive frame."""
    salient_labels = [item["summary"][:40] for item in salient[:3]]
    salient_str = "; ".join(salient_labels) if salient_labels else "nothing salient"
    carry = experiment_carry or {}
    experiment_summary = str(carry.get("summary") or "").strip()
    return (
        f"[{mode['mode']}] {mode['reason']}. "
        f"Temporal: {temporal['horizon']}. "
        f"Carry: {continuity_pressure} ({brain_count} brain, {open_loop_count} loops). "
        f"Private: {private_signal_pressure}. "
        f"Salient: {salient_str}"
        + (f" Experiments: {experiment_summary}" if experiment_summary else "")
    )


# ---------------------------------------------------------------------------
# Compact prompt section
# ---------------------------------------------------------------------------


def build_cognitive_frame_prompt_section() -> str | None:
    """Build a compact cognitive frame section for prompt inclusion.

    Returns ~400-600 chars of structured context.
    Returns None if nothing meaningful to include.
    """
    frame = build_cognitive_frame()
    mode = frame["mode"]
    salient = frame["salient_items"]
    temporal = frame["temporal"]
    continuity_pressure = frame["continuity_pressure"]
    private_signal_pressure = str(frame.get("private_signal_pressure") or "low")
    affordances = frame["affordances"]
    experiment_carry = frame.get("cognitive_experiment_carry") or {}

    experiential_support = frame.get("experiential_support") or {}

    lines = [f"Cognitive frame [{mode['mode']}]: {mode['reason']}"]
    lines.append(f"- Time horizon: {temporal['horizon']} — {temporal['reason'][:80]}")
    lines.append(f"- Continuity pressure: {continuity_pressure}")
    if private_signal_pressure != "low":
        lines.append(f"- Private signal pressure: {private_signal_pressure}")

    if experiential_support.get("support_posture") and experiential_support["support_posture"] != "steadying":
        lines.append(
            f"- Experiential support: {experiential_support['support_posture']}"
            f" | bias={experiential_support.get('support_bias') or 'none'}"
            f" | mode={experiential_support.get('support_mode') or 'steady'}"
        )

    if experiment_carry.get("summary"):
        lines.append(f"- Cognitive experiment carry: {experiment_carry['summary'][:100]}")

    if salient:
        for item in salient[:3]:
            lines.append(f"- [{item['source']}] {item['summary'][:80]}")

    appropriate = affordances.get("appropriate_now") or []
    if appropriate:
        labels = [a["label"] for a in appropriate[:3]]
        lines.append(f"- Appropriate now: {', '.join(labels)}")

    gated = affordances.get("gated_now") or []
    if gated:
        labels = [g["label"] for g in gated[:2]]
        lines.append(f"- Gated: {', '.join(labels)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Safe surface readers (exception-guarded)
# ---------------------------------------------------------------------------


def _safe_brain_context() -> dict[str, object]:
    try:
        from core.services.session_distillation import build_private_brain_context
        return build_private_brain_context()
    except Exception:
        return {"active": False, "record_count": 0, "excerpts": [], "by_type": {}}


def _safe_self_knowledge(
    *, heartbeat_state: dict[str, object] | None = None
) -> dict[str, object]:
    try:
        from core.services.runtime_self_knowledge import build_runtime_self_knowledge_map
        return build_runtime_self_knowledge_map(heartbeat_state=heartbeat_state)
    except Exception:
        return {"active_capabilities": {"items": []}, "approval_gated": {"items": []},
                "passive_inner_forces": {"items": []}, "structural_constraints": {"items": []},
                "unavailable_or_inactive": {"items": []}}


def _safe_open_loops() -> dict[str, object]:
    try:
        from core.services.open_loop_signal_tracking import build_runtime_open_loop_signal_surface
        return build_runtime_open_loop_signal_surface(limit=4)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_question_gates() -> dict[str, object]:
    try:
        from core.services.proactive_question_gate_tracking import build_runtime_proactive_question_gate_surface
        return build_runtime_proactive_question_gate_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_initiative_tension() -> dict[str, object]:
    try:
        from core.services.private_initiative_tension_signal_tracking import build_runtime_private_initiative_tension_signal_surface
        return build_runtime_private_initiative_tension_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_private_state() -> dict[str, object]:
    try:
        from core.services.private_state_snapshot_tracking import build_runtime_private_state_snapshot_surface
        return build_runtime_private_state_snapshot_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_visible_status() -> dict[str, object]:
    try:
        from core.services.visible_model import visible_execution_readiness
        return visible_execution_readiness()
    except Exception:
        return {"provider_status": "unknown"}


def _safe_experiential_support() -> dict[str, object]:
    """Read experiential carry-forward support surface.

    Peeks at cached surface only to avoid circular dependency:
    build_cognitive_frame → _safe_experiential_support →
    build_experiential_runtime_context_surface (uncached) →
    build_cognitive_frame (circular).
    """
    try:
        from core.services.runtime_surface_cache import peek_cached_runtime_surface
        cached = peek_cached_runtime_surface("experiential_runtime_context_surface")
        if cached is not None:
            return cached.get("experiential_support") or {}
        # Also check if heartbeat surface has it
        hb_cached = peek_cached_runtime_surface(("heartbeat_runtime_surface", "default"))
        if isinstance(hb_cached, dict):
            exp = hb_cached.get("experiential_runtime_context")
            if isinstance(exp, dict):
                return exp.get("experiential_support") or {}
    except Exception:
        pass
    return {}


def _safe_liveness_snapshot(
    *, heartbeat_state: dict[str, object] | None = None
) -> dict[str, object]:
    """Get a lightweight liveness snapshot without triggering full liveness build.

    When called without a pre-built heartbeat_state, returns quiet defaults
    rather than triggering the expensive heartbeat_runtime_surface() chain.
    The full liveness signal is only meaningful inside heartbeat ticks.
    """
    if heartbeat_state is not None:
        return {
            "liveness_state": str(heartbeat_state.get("liveness_state") or "quiet"),
            "liveness_score": int(heartbeat_state.get("liveness_score") or 0),
        }
    # Avoid triggering full heartbeat surface build — peek at cache only.
    try:
        from core.services.runtime_surface_cache import peek_cached_runtime_surface
        cached = peek_cached_runtime_surface(("heartbeat_runtime_surface", "default"))
        if cached is not None:
            state = cached.get("state") or {}
            return {
                "liveness_state": str(state.get("liveness_state") or "quiet"),
                "liveness_score": int(state.get("liveness_score") or 0),
            }
    except Exception:
        pass
    return {"liveness_state": "quiet", "liveness_score": 0}


def _safe_cognitive_core_experiments() -> dict[str, object]:
    try:
        from core.services.cognitive_core_experiments import (
            build_cognitive_core_experiments_surface,
        )
        return build_cognitive_core_experiments_surface()
    except Exception:
        return {
            "systems": {},
            "activity_state": "disabled",
            "carry_state": "quiet",
            "summary": "",
        }


def _derive_cognitive_experiment_carry(
    surface: dict[str, object] | None,
) -> dict[str, object]:
    state = surface or {}
    systems = state.get("systems") or {}
    workspace = systems.get("global_workspace") or {}
    hot = systems.get("hot_meta_cognition") or {}
    afterimage = systems.get("surprise_afterimage") or {}
    recurrence = systems.get("recurrence") or {}
    blink = systems.get("attention_blink") or {}

    salience_pressure = "high" if bool(workspace.get("active")) else "low"
    reflective_weight = "elevated" if bool(hot.get("active")) else "light"
    affective_pressure = (
        str(afterimage.get("carry_strength") or "none")
        if bool(afterimage.get("active"))
        else "low"
    )
    if affective_pressure == "none":
        affective_pressure = "low"
    recurrence_pressure = (
        str(recurrence.get("carry_strength") or "none")
        if bool(recurrence.get("active"))
        else "low"
    )
    if recurrence_pressure == "none":
        recurrence_pressure = "low"

    salient_items: list[dict[str, str]] = []
    if bool(workspace.get("active")):
        salient_items.append(
            {
                "source": "global-workspace",
                "summary": str(workspace.get("summary") or "Global workspace coherence is shaping spotlight pressure."),
                "temporal": "current-session",
            }
        )
    if bool(hot.get("active")):
        salient_items.append(
            {
                "source": "hot-meta-cognition",
                "summary": str(hot.get("summary") or "HOT meta-cognition is increasing self-observation weight."),
                "temporal": "slow-burn",
            }
        )
    elif bool(afterimage.get("active")):
        salient_items.append(
            {
                "source": "surprise-afterimage",
                "summary": str(afterimage.get("summary") or "Surprise afterimage is still carrying affective persistence."),
                "temporal": "slow-burn",
            }
        )
    elif bool(recurrence.get("active")):
        salient_items.append(
            {
                "source": "recurrence",
                "summary": str(recurrence.get("summary") or "Recurrence is keeping a thought-loop quietly in play."),
                "temporal": "slow-burn",
            }
        )

    diagnostic_constraint = ""
    if bool(blink.get("active")):
        diagnostic_constraint = "Attention blink is a capacity assay only, not carry authority."

    summary_parts: list[str] = []
    if bool(workspace.get("active")):
        summary_parts.append("workspace spotlight elevated")
    if bool(hot.get("active")):
        summary_parts.append("meta-observation weight elevated")
    if bool(afterimage.get("active")):
        summary_parts.append("afterimage affective carry present")
    if bool(recurrence.get("active")):
        summary_parts.append("recurrence re-entry present")
    if bool(blink.get("active")):
        summary_parts.append("blink observational only")

    summary = "; ".join(summary_parts[:4])
    if bool(blink.get("active")) and "blink observational only" not in summary:
        summary = (
            f"{summary}; blink observational only"
            if summary
            else "blink observational only"
        )

    return {
        "activity_state": str(state.get("activity_state") or "disabled"),
        "carry_state": str(state.get("carry_state") or "quiet"),
        "salience_pressure": salience_pressure,
        "reflective_weight": reflective_weight,
        "affective_pressure": affective_pressure,
        "recurrence_pressure": recurrence_pressure,
        "salient_items": salient_items[:2],
        "diagnostic_constraint": diagnostic_constraint,
        "summary": summary,
    }


def _safe_relation_state() -> dict[str, object]:
    try:
        from core.services.relation_state_signal_tracking import (
            build_runtime_relation_state_signal_surface,
        )
        return build_runtime_relation_state_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_relation_continuity() -> dict[str, object]:
    try:
        from core.services.relation_continuity_signal_tracking import (
            build_runtime_relation_continuity_signal_surface,
        )
        return build_runtime_relation_continuity_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_self_narrative_continuity() -> dict[str, object]:
    try:
        from core.services.self_narrative_continuity_signal_tracking import (
            build_runtime_self_narrative_continuity_signal_surface,
        )
        return build_runtime_self_narrative_continuity_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_world_model() -> dict[str, object]:
    try:
        from core.services.world_model_signal_tracking import (
            build_runtime_world_model_signal_surface,
        )
        return build_runtime_world_model_signal_surface(limit=3)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_remembered_facts() -> dict[str, object]:
    try:
        from core.services.remembered_fact_signal_tracking import (
            build_runtime_remembered_fact_signal_surface,
        )
        return build_runtime_remembered_fact_signal_surface(limit=3)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_user_understanding() -> dict[str, object]:
    try:
        from core.services.user_understanding_signal_tracking import (
            build_runtime_user_understanding_signal_surface,
        )
        return build_runtime_user_understanding_signal_surface(limit=3)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_executive_contradiction() -> dict[str, object]:
    try:
        from core.services.executive_contradiction_signal_tracking import (
            build_runtime_executive_contradiction_signal_surface,
        )
        return build_runtime_executive_contradiction_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_meaning_significance() -> dict[str, object]:
    try:
        from core.services.meaning_significance_signal_tracking import (
            build_runtime_meaning_significance_signal_surface,
        )
        return build_runtime_meaning_significance_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_metabolism() -> dict[str, object]:
    try:
        from core.services.metabolism_state_signal_tracking import (
            build_runtime_metabolism_state_signal_surface,
        )
        return build_runtime_metabolism_state_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_release_markers() -> dict[str, object]:
    try:
        from core.services.release_marker_signal_tracking import (
            build_runtime_release_marker_signal_surface,
        )
        return build_runtime_release_marker_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_attachment_topology() -> dict[str, object]:
    try:
        from core.services.attachment_topology_signal_tracking import (
            build_runtime_attachment_topology_signal_surface,
        )
        return build_runtime_attachment_topology_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_loyalty_gradient() -> dict[str, object]:
    try:
        from core.services.loyalty_gradient_signal_tracking import (
            build_runtime_loyalty_gradient_signal_surface,
        )
        return build_runtime_loyalty_gradient_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_diary_synthesis() -> dict[str, object]:
    try:
        from core.services.diary_synthesis_signal_tracking import (
            build_diary_synthesis_signal_surface,
        )
        return build_diary_synthesis_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_chronicle_consolidation() -> dict[str, object]:
    try:
        from core.services.chronicle_consolidation_signal_tracking import (
            build_runtime_chronicle_consolidation_signal_surface,
        )
        return build_runtime_chronicle_consolidation_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_self_review() -> dict[str, object]:
    try:
        from core.services.self_review_outcome_tracking import (
            build_runtime_self_review_outcome_surface,
        )
        outcome = build_runtime_self_review_outcome_surface(limit=2)
    except Exception:
        outcome = {"active": False, "items": [], "summary": {}}
    try:
        from core.services.self_review_signal_tracking import (
            build_runtime_self_review_signal_surface,
        )
        signal = build_runtime_self_review_signal_surface(limit=2)
    except Exception:
        signal = {"active": False, "items": [], "summary": {}}
    try:
        from core.services.self_review_cadence_signal_tracking import (
            build_runtime_self_review_cadence_signal_surface,
        )
        cadence = build_runtime_self_review_cadence_signal_surface(limit=2)
    except Exception:
        cadence = {"active": False, "items": [], "summary": {}}
    try:
        from core.services.self_review_record_tracking import (
            build_runtime_self_review_record_surface,
        )
        record = build_runtime_self_review_record_surface(limit=2)
    except Exception:
        record = {"active": False, "items": [], "summary": {}}
    return {
        "active": any(
            bool(surface.get("active")) or bool(surface.get("items"))
            for surface in (outcome, signal, cadence, record)
        ),
        "items": [
            *((outcome.get("items") or [])[:1]),
            *((signal.get("items") or [])[:1]),
            *((cadence.get("items") or [])[:1]),
            *((record.get("items") or [])[:1]),
        ],
        "summary": {
            "sources": [
                source
                for source, surface in (
                    ("outcome", outcome),
                    ("signal", signal),
                    ("cadence", cadence),
                    ("record", record),
                )
                if surface.get("active") or surface.get("items")
            ],
        },
    }


def _safe_dream_family() -> dict[str, object]:
    surfaces: list[dict[str, object]] = []
    try:
        from core.services.dream_hypothesis_signal_tracking import (
            build_runtime_dream_hypothesis_signal_surface,
        )
        surfaces.append(build_runtime_dream_hypothesis_signal_surface(limit=2))
    except Exception:
        pass
    try:
        from core.services.dream_adoption_candidate_tracking import (
            build_runtime_dream_adoption_candidate_surface,
        )
        surfaces.append(build_runtime_dream_adoption_candidate_surface(limit=2))
    except Exception:
        pass
    try:
        from core.services.dream_influence_proposal_tracking import (
            build_runtime_dream_influence_proposal_surface,
        )
        surfaces.append(build_runtime_dream_influence_proposal_surface(limit=2))
    except Exception:
        pass
    try:
        from core.services.dream_influence_runtime import (
            build_dream_influence_runtime_surface,
        )
        surfaces.append(build_dream_influence_runtime_surface())
    except Exception:
        pass
    try:
        from core.services.dream_carry_over import (
            build_dream_carry_over_surface,
        )
        surfaces.append(build_dream_carry_over_surface())
    except Exception:
        pass
    try:
        from core.services.dream_articulation import (
            build_dream_articulation_surface,
        )
        surfaces.append(build_dream_articulation_surface())
    except Exception:
        pass

    items: list[dict[str, object]] = []
    for surface in surfaces:
        items.extend((surface.get("items") or [])[:1])
        if not surface.get("items"):
            summary = surface.get("summary")
            if isinstance(summary, str) and summary:
                items.append({"summary": summary, "title": summary})
    return {
        "active": any(bool(surface.get("active")) or bool(surface.get("items")) for surface in surfaces),
        "items": items[:4],
        "summary": {"sources": len(surfaces)},
    }
