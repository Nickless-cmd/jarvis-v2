from __future__ import annotations

from apps.api.jarvis_api.services.runtime_surface_cache import (
    get_cached_runtime_surface,
)

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_open_loop_signals,
    list_runtime_private_initiative_tension_signals,
    list_runtime_reflective_critics,
    list_runtime_reflection_signals,
    list_runtime_regulation_homeostasis_signals,
    list_runtime_temporal_recurrence_signals,
    supersede_runtime_open_loop_signals_for_domain,
    update_runtime_open_loop_signal_status,
    upsert_runtime_open_loop_signal,
)

_STALE_AFTER_DAYS = 14
_THREAD_TOKEN_STOPWORDS = {
    "active",
    "around",
    "bounded",
    "current",
    "development",
    "direction",
    "focus",
    "goal",
    "homeostasis",
    "initiative",
    "loop",
    "loops",
    "open",
    "pressure",
    "private",
    "regulation",
    "retain",
    "runtime",
    "signal",
    "signals",
    "stabilize",
    "state",
    "steady",
    "support",
    "thread",
    "tension",
    "visible",
}


def track_runtime_open_loop_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    items = _persist_open_loop_signals(
        signals=_extract_open_loop_candidates(),
        session_id=str(session_id or "").strip(),
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded open-loop signals."
            if items
            else "No bounded open-loop signal warranted tracking."
        ),
    }


def refresh_runtime_open_loop_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_open_loop_signals(limit=40):
        if str(item.get("status") or "") not in {"open", "softening", "closed"}:
            continue
        updated_at = _parse_dt(
            str(item.get("updated_at") or item.get("created_at") or "")
        )
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_open_loop_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded open-loop inactivity window.",
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        event_bus.publish(
            "open_loop_signal.stale",
            {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
                "status_reason": refreshed_item.get("status_reason"),
            },
        )
    return {"stale_marked": refreshed}


def build_runtime_open_loop_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return get_cached_runtime_surface(
        ("runtime_open_loop_signal_surface", max(limit, 1)),
        lambda: _build_runtime_open_loop_signal_surface_uncached(limit=max(limit, 1)),
    )


def _build_runtime_open_loop_signal_surface_uncached(
    *, limit: int = 8
) -> dict[str, object]:
    refresh_runtime_open_loop_signal_statuses()
    items = list_runtime_open_loop_signals(limit=limit)
    snapshots = _build_governance_snapshots()
    enriched_items = [
        _with_closure_governance(item, snapshots=snapshots) for item in items
    ]
    open_items = [
        item for item in enriched_items if str(item.get("status") or "") == "open"
    ]
    softening = [
        item for item in enriched_items if str(item.get("status") or "") == "softening"
    ]
    closed = [
        item for item in enriched_items if str(item.get("status") or "") == "closed"
    ]
    stale = [
        item for item in enriched_items if str(item.get("status") or "") == "stale"
    ]
    superseded = [
        item for item in enriched_items if str(item.get("status") or "") == "superseded"
    ]
    ordered = [*open_items, *softening, *closed, *stale, *superseded]
    latest = next(iter(open_items or softening or closed or stale or superseded), None)
    creation_readiness = get_open_loop_creation_readiness()
    return {
        "active": bool(open_items or softening or closed),
        "items": ordered,
        "summary": {
            "open_count": len(open_items),
            "softening_count": len(softening),
            "closed_count": len(closed),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "ready_count": len(
                [
                    item
                    for item in ordered
                    if str(item.get("closure_confidence") or "") == "high"
                ]
            ),
            "current_signal": str((latest or {}).get("title") or "No active open loop"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_closure_confidence": str(
                (latest or {}).get("closure_confidence") or "low"
            ),
            "creation_readiness": creation_readiness,
        },
    }


def get_open_loop_creation_readiness() -> dict[str, object]:
    from apps.api.jarvis_api.services.private_initiative_tension_signal_tracking import (
        build_runtime_private_initiative_tension_signal_surface,
    )
    from apps.api.jarvis_api.services.autonomy_pressure_signal_tracking import (
        build_runtime_autonomy_pressure_signal_surface,
    )
    from apps.api.jarvis_api.services.proactive_loop_lifecycle_tracking import (
        build_runtime_proactive_loop_lifecycle_surface,
    )
    from apps.api.jarvis_api.services.proactive_question_gate_tracking import (
        build_runtime_proactive_question_gate_surface,
    )

    tension = build_runtime_private_initiative_tension_signal_surface(limit=8)
    autonomy = build_runtime_autonomy_pressure_signal_surface(limit=8)
    loops = build_runtime_proactive_loop_lifecycle_surface(limit=8)
    question_gate = build_runtime_proactive_question_gate_surface(limit=8)

    aligned_signals = []

    active_tensions = [
        item
        for item in tension.get("items", [])
        if str(item.get("status") or "") == "active"
    ]
    if active_tensions:
        aligned_signals.append("initiative-tension")

    autonomy_pressures = [
        item
        for item in autonomy.get("items", [])
        if str(item.get("status") or "") == "active"
    ]
    if autonomy_pressures:
        aligned_signals.append("autonomy-pressure")

    active_loops = [
        item
        for item in loops.get("items", [])
        if str(item.get("status") or "") == "active"
    ]
    if active_loops:
        aligned_signals.append("proactive-loop")

    question_gates = [
        item
        for item in question_gate.get("items", [])
        if str(item.get("gate_state") or "") == "question-gated-candidate"
    ]
    if question_gates:
        aligned_signals.append("question-gate")

    alignment_count = len(aligned_signals)

    if alignment_count >= 3:
        readiness = "ready"
        confidence = "high"
    elif alignment_count == 2:
        readiness = "partial"
        confidence = "medium"
    elif alignment_count == 1:
        readiness = "emerging"
        confidence = "low"
    else:
        readiness = "none"
        confidence = "none"

    return {
        "readiness": readiness,
        "confidence": confidence,
        "aligned_signals": aligned_signals,
        "alignment_count": alignment_count,
        "threshold": 2,
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
    }


def _extract_open_loop_candidates() -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}
    active_goals: list[dict[str, object]] = []
    active_tensions: list[dict[str, object]] = []
    active_regulation: list[dict[str, object]] = []

    for focus in list_runtime_development_focuses(limit=18):
        if str(focus.get("status") or "") != "active":
            continue
        domain_key = _focus_domain_key(str(focus.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["active_focus"] = focus

    for critic in list_runtime_reflective_critics(limit=18):
        status = str(critic.get("status") or "")
        if status not in {"active", "resolved"}:
            continue
        domain_key = _critic_domain_key(str(critic.get("canonical_key") or ""))
        if domain_key:
            bucket = snapshots.setdefault(domain_key, {})
            if status == "active":
                bucket["active_critic"] = critic
            else:
                bucket["resolved_critic"] = critic

    for goal in list_runtime_goal_signals(limit=18):
        status = str(goal.get("status") or "")
        if status not in {"active", "blocked", "completed"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if domain_key:
            bucket = snapshots.setdefault(domain_key, {})
            if status == "blocked":
                bucket["blocked_goal"] = goal
            elif status == "active":
                active_goals.append(goal)
                bucket["active_goal"] = goal
            else:
                bucket["completed_goal"] = goal

    for reflection in list_runtime_reflection_signals(limit=18):
        status = str(reflection.get("status") or "")
        if status not in {"active", "integrating", "settled"}:
            continue
        domain_key = _reflection_domain_key(str(reflection.get("canonical_key") or ""))
        if domain_key:
            bucket = snapshots.setdefault(domain_key, {})
            if status == "active":
                bucket["active_reflection"] = reflection
            elif status == "integrating":
                bucket["integrating_reflection"] = reflection
            else:
                bucket["settled_reflection"] = reflection

    for recurrence in list_runtime_temporal_recurrence_signals(limit=18):
        status = str(recurrence.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _temporal_domain_key(str(recurrence.get("canonical_key") or ""))
        if domain_key:
            bucket = snapshots.setdefault(domain_key, {})
            if status == "active":
                bucket["active_recurrence"] = recurrence
            else:
                bucket["softening_recurrence"] = recurrence

    for tension in list_runtime_private_initiative_tension_signals(limit=18):
        if str(tension.get("status") or "") != "active":
            continue
        active_tensions.append(tension)

    for regulation in list_runtime_regulation_homeostasis_signals(limit=18):
        if str(regulation.get("status") or "") != "active":
            continue
        active_regulation.append(regulation)

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        active_focus = snapshot.get("active_focus")
        active_critic = snapshot.get("active_critic")
        resolved_critic = snapshot.get("resolved_critic")
        blocked_goal = snapshot.get("blocked_goal")
        active_goal = snapshot.get("active_goal")
        completed_goal = snapshot.get("completed_goal")
        active_reflection = snapshot.get("active_reflection")
        integrating_reflection = snapshot.get("integrating_reflection")
        settled_reflection = snapshot.get("settled_reflection")
        active_recurrence = snapshot.get("active_recurrence")
        softening_recurrence = snapshot.get("softening_recurrence")
        title_suffix = _domain_title(domain_key)

        live_pressure = [
            item
            for item in [
                active_critic,
                blocked_goal,
                active_reflection,
                active_recurrence,
            ]
            if item
        ]
        if active_focus and live_pressure:
            signal_type = (
                "persistent-open-loop"
                if active_recurrence or (active_critic and blocked_goal)
                else "open-loop"
            )
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type=signal_type,
                    status="open",
                    title=f"Open loop: {title_suffix}",
                    summary=f"A bounded loop around {title_suffix.lower()} is still unresolved and carrying live pressure.",
                    rationale="Existing development, critic, goal, reflection, or recurrence truth still shows unresolved bounded pressure in the same domain.",
                    status_reason="The bounded thread is still visibly unresolved.",
                    source_items=[
                        active_focus,
                        active_critic,
                        blocked_goal,
                        active_reflection,
                        active_recurrence,
                    ],
                )
            )
            continue

        live_pressure_goal = _match_live_pressure_item(
            anchors=[active_focus],
            candidates=active_goals,
            minimum_overlap=2,
        )
        live_pressure_tension = _match_live_pressure_item(
            anchors=[active_focus, live_pressure_goal],
            candidates=active_tensions,
            minimum_overlap=2,
        )
        live_pressure_regulation = _match_live_pressure_item(
            anchors=[active_focus, live_pressure_goal],
            candidates=active_regulation,
            minimum_overlap=1,
        )
        if (
            active_focus
            and live_pressure_goal
            and live_pressure_tension
            and live_pressure_regulation
        ):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="open-loop",
                    status="open",
                    title=f"Open loop: {title_suffix}",
                    summary=(
                        f"A bounded loop around {title_suffix.lower()} is still carrying live pressure through active focus, "
                        "active goal carry, initiative tension, and regulation support."
                    ),
                    rationale=(
                        "Existing focus and goal carry may materialize a bounded live loop only when initiative tension and "
                        "regulation support are concurrently aligned in the same thread, without becoming planner authority "
                        "or treating all active goals as loops."
                    ),
                    status_reason=(
                        "The bounded thread is still visibly unresolved through aligned focus, goal, initiative-tension, "
                        "and regulation carry."
                    ),
                    source_items=[
                        active_focus,
                        live_pressure_goal,
                        live_pressure_tension,
                        live_pressure_regulation,
                    ],
                )
            )
            continue

        if (
            active_focus
            and (integrating_reflection or softening_recurrence)
            and not active_critic
            and not blocked_goal
        ):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="softening-loop",
                    status="softening",
                    title=f"Softening loop: {title_suffix}",
                    summary=f"A bounded loop around {title_suffix.lower()} is still present, but the pressure is easing.",
                    rationale="The thread remains live through existing focus and integration/recurrence truth, but acute critic or blocked-goal pressure is no longer present.",
                    status_reason="The loop is still present, but it is softening rather than pressing.",
                    source_items=[
                        active_focus,
                        active_goal,
                        integrating_reflection,
                        softening_recurrence,
                    ],
                )
            )
            continue

        if (
            (active_focus or active_goal or completed_goal)
            and settled_reflection
            and (softening_recurrence or resolved_critic or completed_goal)
            and not active_critic
            and not blocked_goal
        ):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="softening-loop",
                    status="closed",
                    title=f"Closed loop: {title_suffix}",
                    summary=f"A bounded loop around {title_suffix.lower()} now appears closed by visible runtime evidence.",
                    rationale="The same domain now reads as settled or completed across existing layers without matching active critic or blocked-goal pressure.",
                    status_reason="The bounded loop appears closed by calmer reflection and cleared pressure, not by autonomous task execution.",
                    source_items=[
                        active_focus,
                        active_goal,
                        completed_goal,
                        settled_reflection,
                        softening_recurrence,
                        resolved_critic,
                    ],
                )
            )

    readiness = get_open_loop_creation_readiness()
    if readiness.get("readiness") == "ready":
        readiness_candidate = _materialize_from_creation_readiness(
            readiness=readiness,
            existing_domain_keys={snapshots.keys()},
        )
        if readiness_candidate:
            candidates.append(readiness_candidate)

    maturation_candidates = _extract_closure_maturation_candidates(
        snapshots=snapshots,
        existing_domain_keys=set(snapshots.keys()),
    )
    for mat_candidate in maturation_candidates:
        if mat_candidate not in candidates:
            candidates.append(mat_candidate)

    return candidates[:4]


def _materialize_from_creation_readiness(
    readiness: dict[str, object],
    existing_domain_keys: set[str],
) -> dict[str, object] | None:
    aligned_signals = readiness.get("aligned_signals", [])
    if len(aligned_signals) < 3:
        return None

    from apps.api.jarvis_api.services.private_initiative_tension_signal_tracking import (
        build_runtime_private_initiative_tension_signal_surface,
    )
    from apps.api.jarvis_api.services.autonomy_pressure_signal_tracking import (
        build_runtime_autonomy_pressure_signal_surface,
    )

    tension = build_runtime_private_initiative_tension_signal_surface(limit=8)
    autonomy = build_runtime_autonomy_pressure_signal_surface(limit=8)

    focus_title = "aligned runtime threads"
    source_items = []

    active_tensions = [
        item
        for item in tension.get("items", [])
        if str(item.get("status") or "") == "active"
    ]
    if active_tensions:
        source_items.append(active_tensions[0])
        tension_title = str(active_tensions[0].get("title") or "")
        if tension_title:
            focus_title = tension_title.replace(
                "Private initiative tension: ", ""
            ).strip()

    active_pressures = [
        item
        for item in autonomy.get("items", [])
        if str(item.get("status") or "") == "active"
    ]
    if active_pressures:
        source_items.append(active_pressures[0])

    domain_key = f"creation-readiness:{focus_title.replace(' ', '-').lower()[:32]}"
    if domain_key in existing_domain_keys:
        return None

    existing_loops = list_runtime_open_loop_signals(limit=20)
    for loop in existing_loops:
        if str(loop.get("status") or "") not in {"open", "softening"}:
            continue
        loop_title = str(loop.get("title") or "").lower()
        if focus_title.lower() in loop_title or domain_key in str(
            loop.get("canonical_key") or ""
        ):
            return None

    return _build_candidate(
        domain_key=domain_key,
        signal_type="open-loop",
        status="open",
        title=f"Open loop: {focus_title}",
        summary=f"A bounded loop around {focus_title.lower()} emerged from aligned initiative tension and autonomy pressure.",
        rationale="Bounded open loop may materialize only when at least three aligned signals (initiative-tension, autonomy-pressure, proactive-loop, question-gate) point in the same direction, without becoming planner authority or task execution.",
        status_reason="The bounded thread emerged from strong aligned runtime signals, not from autonomous task creation.",
        source_items=source_items,
    )


def _extract_closure_maturation_candidates(
    snapshots: dict[str, dict[str, object]],
    existing_domain_keys: set[str],
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []

    existing_open_loops = list_runtime_open_loop_signals(limit=20)
    open_loops = [
        loop for loop in existing_open_loops if str(loop.get("status") or "") == "open"
    ]

    for loop in open_loops:
        loop_domain_key = str(loop.get("canonical_key") or "")
        if not loop_domain_key:
            continue

        parts = loop_domain_key.split(":")
        domain_key_part = parts[-1] if parts else loop_domain_key

        current_snapshot = snapshots.get(domain_key_part, {})

        active_critic = current_snapshot.get("active_critic")
        resolved_critic = current_snapshot.get("resolved_critic")
        blocked_goal = current_snapshot.get("blocked_goal")
        integrating_reflection = current_snapshot.get("integrating_reflection")
        softening_recurrence = current_snapshot.get("softening_recurrence")
        settled_reflection = current_snapshot.get("settled_reflection")

        has_active_critic = active_critic is not None
        has_blocked_goal = blocked_goal is not None
        has_integrating = integrating_reflection is not None
        has_softening_recurrence = softening_recurrence is not None
        has_settled = settled_reflection is not None
        has_resolved_critic = resolved_critic is not None

        loop_title = str(loop.get("title") or "").replace("Open loop: ", "").strip()

        if has_integrating or has_softening_recurrence:
            if not has_active_critic and not has_blocked_goal:
                candidates.append(
                    _build_candidate(
                        domain_key=loop_domain_key,
                        signal_type="softening-loop",
                        status="softening",
                        title=f"Softening loop: {loop_title}",
                        summary=f"A bounded loop around {loop_title.lower()} appears to be easing - acute pressure has reduced.",
                        rationale="Bounded loop softening may occur when acute critic/blocked-goal pressure clears while integration or recurrence signals remain.",
                        status_reason="The loop is softening based on reduced acute pressure in the runtime evidence.",
                        source_items=[
                            integrating_reflection,
                            softening_recurrence,
                            resolved_critic,
                        ],
                    )
                )
                continue

        if has_settled and (has_softening_recurrence or has_resolved_critic):
            if not has_active_critic and not has_blocked_goal:
                candidates.append(
                    _build_candidate(
                        domain_key=loop_domain_key,
                        signal_type="softening-loop",
                        status="closed",
                        title=f"Closed loop: {loop_title}",
                        summary=f"A bounded loop around {loop_title.lower()} now appears closed by calmer runtime evidence.",
                        rationale="Bounded loop closure may occur when settled reflection and resolved pressure clearly indicate completion without active opposition.",
                        status_reason="The loop appears closed based on settled evidence and resolved pressure, not autonomous execution.",
                        source_items=[
                            settled_reflection,
                            softening_recurrence,
                            resolved_critic,
                        ],
                    )
                )

    return candidates


def _build_governance_snapshots() -> dict[str, dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for critic in list_runtime_reflective_critics(limit=18):
        status = str(critic.get("status") or "")
        if status not in {"active", "resolved"}:
            continue
        domain_key = _critic_domain_key(str(critic.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_critic"] = critic
        else:
            bucket["resolved_critic"] = critic

    for goal in list_runtime_goal_signals(limit=18):
        status = str(goal.get("status") or "")
        if status not in {"blocked", "completed"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "blocked":
            bucket["blocked_goal"] = goal
        else:
            bucket["completed_goal"] = goal

    for reflection in list_runtime_reflection_signals(limit=18):
        status = str(reflection.get("status") or "")
        if status not in {"integrating", "settled"}:
            continue
        domain_key = _reflection_domain_key(str(reflection.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "integrating":
            bucket["integrating_reflection"] = reflection
        else:
            bucket["settled_reflection"] = reflection

    for recurrence in list_runtime_temporal_recurrence_signals(limit=18):
        status = str(recurrence.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _temporal_domain_key(str(recurrence.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_recurrence"] = recurrence
        else:
            bucket["softening_recurrence"] = recurrence

    return snapshots


def _with_closure_governance(
    item: dict[str, object],
    *,
    snapshots: dict[str, dict[str, object]],
) -> dict[str, object]:
    enriched = dict(item)
    domain_key = _open_loop_domain_key(str(item.get("canonical_key") or ""))
    snapshot = snapshots.get(domain_key, {}) if domain_key else {}
    active_critic = snapshot.get("active_critic")
    blocked_goal = snapshot.get("blocked_goal")
    completed_goal = snapshot.get("completed_goal")
    integrating_reflection = snapshot.get("integrating_reflection")
    settled_reflection = snapshot.get("settled_reflection")
    active_recurrence = snapshot.get("active_recurrence")
    softening_recurrence = snapshot.get("softening_recurrence")
    status = str(item.get("status") or "")

    closure_confidence = "low"
    closure_reason = (
        "No current closure evidence is strong enough to treat this loop as ready."
    )

    if status == "closed":
        closure_confidence = "high"
        closure_reason = "This loop already reads as conservatively closed by existing runtime truth."
    elif active_critic or blocked_goal:
        if settled_reflection or softening_recurrence or completed_goal:
            closure_confidence = "medium"
            closure_reason = "Some calming evidence exists, but active critic or blocked-goal pressure still keeps closure readiness bounded."
        else:
            closure_confidence = "low"
            closure_reason = "Active critic or blocked-goal pressure is still present, so the loop is not close to closure."
    elif settled_reflection and (softening_recurrence or completed_goal):
        closure_confidence = "high"
        closure_reason = "Settled reflection and calmer completion signals now point toward likely closure readiness."
    elif integrating_reflection or softening_recurrence:
        closure_confidence = "medium"
        closure_reason = "The loop is easing through integration or softening, but closure evidence is not yet strong."
    elif active_recurrence:
        closure_confidence = "low"
        closure_reason = (
            "The loop still shows active recurrence, so closure readiness remains low."
        )

    enriched["closure_readiness"] = closure_confidence
    enriched["closure_confidence"] = closure_confidence
    enriched["closure_reason"] = closure_reason
    return enriched


def _persist_open_loop_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_open_loop_signal(
            signal_id=f"open-loop-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "open-loop"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "open"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or "runtime-derived-support"),
            confidence=str(signal.get("confidence") or "low"),
            evidence_summary=str(signal.get("evidence_summary") or ""),
            support_summary=str(signal.get("support_summary") or ""),
            support_count=int(signal.get("support_count") or 1),
            session_count=int(signal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(signal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
        )
        superseded_count = supersede_runtime_open_loop_signals_for_domain(
            domain_key=str(signal.get("domain_key") or ""),
            exclude_signal_id=str(persisted_item.get("signal_id") or ""),
            updated_at=now,
            status_reason="Superseded by a newer open-loop reading for the same bounded domain.",
        )
        if superseded_count > 0:
            event_bus.publish(
                "open_loop_signal.superseded",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "superseded_count": superseded_count,
                    "summary": persisted_item.get("summary"),
                },
            )
        if persisted_item.get("was_created"):
            event_bus.publish(
                "open_loop_signal.created"
                if persisted_item.get("status") != "closed"
                else "open_loop_signal.closed",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "open_loop_signal.updated"
                if persisted_item.get("status") != "closed"
                else "open_loop_signal.closed",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(persisted_item)
    return persisted


def _build_candidate(
    *,
    domain_key: str,
    signal_type: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    status_reason: str,
    source_items: list[dict[str, object] | None],
) -> dict[str, object]:
    items = [item for item in source_items if item]
    support_count = max(
        [int(item.get("support_count") or 1) for item in items], default=1
    )
    session_count = max(
        [int(item.get("session_count") or 1) for item in items], default=1
    )
    confidence = "high" if len(items) >= 3 else "medium"
    return {
        "signal_type": signal_type,
        "canonical_key": f"open-loop:{signal_type}:{domain_key}",
        "domain_key": domain_key,
        "status": status,
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_kind": "derived-runtime-open-loop",
        "confidence": confidence,
        "evidence_summary": _merge_fragments(
            *[str(item.get("evidence_summary") or "") for item in items]
        ),
        "support_summary": _merge_fragments(
            *[str(item.get("support_summary") or "") for item in items]
        ),
        "support_count": support_count,
        "session_count": session_count,
        "status_reason": status_reason,
    }


def _focus_domain_key(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if text.startswith("development-focus:communication:"):
        return text.removeprefix("development-focus:communication:")
    if text.startswith("development-focus:user-directed:"):
        return text.removeprefix("development-focus:user-directed:")
    if text.startswith("development-focus:runtime:"):
        parts = text.removeprefix("development-focus:runtime:").split(":")
        return parts[0] if parts else ""
    return ""


def _critic_domain_key(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if text.startswith("reflective-critic:mismatch:development-focus:communication:"):
        return text.removeprefix(
            "reflective-critic:mismatch:development-focus:communication:"
        )
    if text.startswith("reflective-critic:mismatch:development-focus:user-directed:"):
        return text.removeprefix(
            "reflective-critic:mismatch:development-focus:user-directed:"
        )
    if text.startswith("reflective-critic:mismatch:development-focus:runtime:"):
        parts = text.removeprefix(
            "reflective-critic:mismatch:development-focus:runtime:"
        ).split(":")
        return parts[0] if parts else ""
    return ""


def _goal_domain_key(canonical_key: str) -> str:
    return str(canonical_key or "").removeprefix("goal-signal:")


def _reflection_domain_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def _temporal_domain_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def _open_loop_domain_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Open loop"


def _merge_fragments(*values: str) -> str:
    parts: list[str] = []
    for value in values:
        normalized = " ".join(str(value or "").split()).strip()
        if normalized and normalized not in parts:
            parts.append(normalized)
    return " | ".join(parts[:4])


def _match_live_pressure_item(
    *,
    anchors: list[dict[str, object] | None],
    candidates: list[dict[str, object] | None],
    minimum_overlap: int,
) -> dict[str, object] | None:
    valid_anchors = [item for item in anchors if item]
    if not valid_anchors:
        return None
    best_item: dict[str, object] | None = None
    best_score = 0
    for candidate in candidates:
        if not candidate:
            continue
        score = 0
        for anchor in valid_anchors:
            score = max(score, _thread_overlap(anchor, candidate))
        if score < minimum_overlap or score <= best_score:
            continue
        best_item = candidate
        best_score = score
    return best_item


def _thread_overlap(left: dict[str, object], right: dict[str, object]) -> int:
    return len(_thread_tokens(left) & _thread_tokens(right))


def _thread_tokens(item: dict[str, object]) -> set[str]:
    fragments = [
        str(item.get("canonical_key") or ""),
        str(item.get("title") or ""),
        str(item.get("summary") or ""),
        str(item.get("support_summary") or ""),
        str(item.get("status_reason") or ""),
    ]
    tokens: set[str] = set()
    for fragment in fragments:
        normalized = str(fragment or "").lower()
        for raw_token in (
            normalized.replace(":", " ")
            .replace("|", " ")
            .replace("[", " ")
            .replace("]", " ")
            .split()
        ):
            token = "".join(ch for ch in raw_token if ch.isalnum() or ch == "-").strip(
                "-"
            )
            if len(token) < 4:
                continue
            if token in _THREAD_TOKEN_STOPWORDS:
                continue
            tokens.add(token)
            tokens.update(
                part
                for part in token.split("-")
                if len(part) >= 4 and part not in _THREAD_TOKEN_STOPWORDS
            )
    return tokens


def _parse_dt(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
