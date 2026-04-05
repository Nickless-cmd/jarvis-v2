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

from apps.api.jarvis_api.services.runtime_surface_cache import runtime_surface_cache


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
) -> dict[str, str]:
    """Select the bounded mental mode from runtime state."""
    if visible_active:
        return {"mode": "respond", "reason": "Visible chat is currently active"}

    if question_gate_active or approval_pending:
        return {"mode": "clarify", "reason": "Question gate or approval gate is active — bounded inquiry mode"}

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
    inner_forces: list[dict[str, object]],
    gate_items: list[dict[str, object]],
) -> list[dict[str, str]]:
    """Select the most salient items across all sources.

    Priority order: active gates > open loops > brain carry > inner forces.
    Returns at most _MAX_SALIENT_ITEMS items.
    """
    items: list[dict[str, str]] = []

    # Gates first — they represent bounded action readiness
    for gate in gate_items[:1]:
        state = str(gate.get("question_gate_state") or gate.get("status") or "")
        summary = str(gate.get("summary") or gate.get("question_gate_summary") or "")[:_MAX_SLICE_CHARS]
        if state and summary:
            items.append({"source": "question-gate", "summary": summary, "temporal": "immediate"})

    # Open loops — they anchor session continuity
    for loop in open_loop_items[:2]:
        title = str(loop.get("title") or "")[:60]
        status = str(loop.get("status") or "")
        if title and status in {"active", "softening"}:
            items.append({"source": "open-loop", "summary": f"{title} ({status})", "temporal": "current-session"})

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

    return items[:_MAX_SALIENT_ITEMS]


# ---------------------------------------------------------------------------
# Affordance selection (what is possible/appropriate NOW)
# ---------------------------------------------------------------------------

def _select_affordances(
    *,
    active_capabilities: list[dict[str, object]],
    gated_items: list[dict[str, object]],
    mode: str,
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

    for item in gated_items:
        gated_now.append({
            "id": str(item.get("id") or ""),
            "label": str(item.get("label") or ""),
            "gate": str(item.get("mutability") or "approval-gated"),
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
        visible_status = _safe_visible_status()
        liveness = _safe_liveness_snapshot(heartbeat_state=heartbeat_state)
        experiential_support = _safe_experiential_support()

        # --- Extract summaries ---
        brain_excerpts = brain_context.get("excerpts") or []
        brain_count = int(brain_context.get("record_count") or 0)
        brain_types = brain_context.get("by_type") or {}

        loop_summary = loop_surface.get("summary") or {}
        loop_items = loop_surface.get("items") or []
        open_loop_count = int(loop_summary.get("open_count") or 0)

        gate_items = gate_surface.get("items") or []
        gate_active = bool(gate_surface.get("active"))

        tension_active = bool(tension_surface.get("active"))
        tension_intensity = str((tension_surface.get("summary") or {}).get("current_intensity") or "low")

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
    )

    salient = _select_salient_items(
        brain_excerpts=brain_excerpts,
        open_loop_items=loop_items,
        inner_forces=inner_forces,
        gate_items=gate_items,
    )

    affordances = _select_affordances(
        active_capabilities=active_capabilities,
        gated_items=gated_items,
        mode=mode["mode"],
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

    # Active constraints (compact)
    constraints_summary = [str(c.get("label") or "")[:60] for c in constraint_items[:4]]

    return {
        "mode": mode,
        "salient_items": salient,
        "affordances": affordances,
        "temporal": temporal,
        "continuity_pressure": continuity_pressure,
        "continuity_mode": continuity_mode,
        "experiential_support": experiential_support if experiential_support.get("support_posture") else {},
        "active_constraints": constraints_summary,
        "counts": {
            "brain_records": brain_count,
            "open_loops": open_loop_count,
            "salient_items": len(salient),
            "available_affordances": len(affordances["available_now"]),
            "gated_affordances": len(affordances["gated_now"]),
            "inner_forces": len(inner_forces),
        },
        "summary": _build_frame_summary(
            mode=mode,
            salient=salient,
            temporal=temporal,
            continuity_pressure=continuity_pressure,
            brain_count=brain_count,
            open_loop_count=open_loop_count,
        ),
    }


def _build_frame_summary(
    *,
    mode: dict[str, str],
    salient: list[dict[str, str]],
    temporal: dict[str, str],
    continuity_pressure: str,
    brain_count: int,
    open_loop_count: int,
) -> str:
    """Build a compact one-line summary of the cognitive frame."""
    salient_labels = [item["summary"][:40] for item in salient[:3]]
    salient_str = "; ".join(salient_labels) if salient_labels else "nothing salient"
    return (
        f"[{mode['mode']}] {mode['reason']}. "
        f"Temporal: {temporal['horizon']}. "
        f"Carry: {continuity_pressure} ({brain_count} brain, {open_loop_count} loops). "
        f"Salient: {salient_str}"
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
    affordances = frame["affordances"]

    experiential_support = frame.get("experiential_support") or {}

    lines = [f"Cognitive frame [{mode['mode']}]: {mode['reason']}"]
    lines.append(f"- Time horizon: {temporal['horizon']} — {temporal['reason'][:80]}")
    lines.append(f"- Continuity pressure: {continuity_pressure}")

    if experiential_support.get("support_posture") and experiential_support["support_posture"] != "steadying":
        lines.append(
            f"- Experiential support: {experiential_support['support_posture']}"
            f" | bias={experiential_support.get('support_bias') or 'none'}"
            f" | mode={experiential_support.get('support_mode') or 'steady'}"
        )

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
        from apps.api.jarvis_api.services.session_distillation import build_private_brain_context
        return build_private_brain_context()
    except Exception:
        return {"active": False, "record_count": 0, "excerpts": [], "by_type": {}}


def _safe_self_knowledge(
    *, heartbeat_state: dict[str, object] | None = None
) -> dict[str, object]:
    try:
        from apps.api.jarvis_api.services.runtime_self_knowledge import build_runtime_self_knowledge_map
        return build_runtime_self_knowledge_map(heartbeat_state=heartbeat_state)
    except Exception:
        return {"active_capabilities": {"items": []}, "approval_gated": {"items": []},
                "passive_inner_forces": {"items": []}, "structural_constraints": {"items": []},
                "unavailable_or_inactive": {"items": []}}


def _safe_open_loops() -> dict[str, object]:
    try:
        from apps.api.jarvis_api.services.open_loop_signal_tracking import build_runtime_open_loop_signal_surface
        return build_runtime_open_loop_signal_surface(limit=4)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_question_gates() -> dict[str, object]:
    try:
        from apps.api.jarvis_api.services.proactive_question_gate_tracking import build_runtime_proactive_question_gate_surface
        return build_runtime_proactive_question_gate_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_initiative_tension() -> dict[str, object]:
    try:
        from apps.api.jarvis_api.services.private_initiative_tension_signal_tracking import build_runtime_private_initiative_tension_signal_surface
        return build_runtime_private_initiative_tension_signal_surface(limit=2)
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_visible_status() -> dict[str, object]:
    try:
        from apps.api.jarvis_api.services.visible_model import visible_execution_readiness
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
        from apps.api.jarvis_api.services.runtime_surface_cache import peek_cached_runtime_surface
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
        from apps.api.jarvis_api.services.runtime_surface_cache import peek_cached_runtime_surface
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
