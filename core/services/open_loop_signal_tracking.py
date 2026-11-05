from __future__ import annotations

from core.identity.workspace_context import current_workspace_name
from core.services.runtime_surface_cache import (
    get_timed_runtime_surface,
)

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    connect,
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_open_loop_signals,
    list_runtime_private_initiative_tension_signals,
    list_runtime_reflective_critics,
    list_runtime_reflection_signals,
    list_runtime_regulation_homeostasis_signals,
    list_runtime_temporal_recurrence_signals,
    update_runtime_open_loop_signal_status,
    upsert_runtime_open_loop_signal,
)

_STALE_AFTER_DAYS = 5    # 2026-05-16: 14d var for langt — Bjørn fik 16 zombie-loops fra test-runs
_CLOSE_STALE_AFTER_DAYS = 7  # efter stale-mark, auto-close hvis ingen update i yderligere 7 dage
_COUNTED_STATUSES = ("open", "softening", "closed", "stale", "superseded")
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
    auto_closed = 0
    # Listen er nyeste-først og trunkeret. Et fast limit=40 betød derfor at
    # gamle åbne loops aldrig igen blev set, når tabellen voksede over 40.
    # Tæl først populationen og hent hele det lille statuslager; UI-fladen
    # nedenfor er stadig trunkeret separat.
    total = sum(_open_loop_status_counts().values())
    items = list_runtime_open_loop_signals(limit=max(total, 40))
    completed_visible_domains = _completed_visible_domains(items)
    for item in items:
        current_status = str(item.get("status") or "")
        if current_status not in {"open", "softening", "closed", "stale"}:
            continue
        updated_at = _parse_dt(
            str(item.get("updated_at") or item.get("created_at") or "")
        )
        if updated_at is None:
            continue

        # Et visible-run er den operationelle sandhed for de per-run-domæner,
        # som fokuslaget skaber. 41/45 åbne loops på CT105 pegede 5/11-2026
        # på runs der allerede stod completed; closure ventede i stedet på
        # resolved/settled-signaler, som de relevante producenter aldrig skrev.
        # Interrupted er bevidst IKKE terminalt her: dét arbejde kan stadig
        # kræve en fortsættelse.
        domain = _loop_domain(str(item.get("canonical_key") or ""))
        if current_status in {"open", "softening"} and domain in completed_visible_domains:
            closed_item = update_runtime_open_loop_signal_status(
                str(item.get("signal_id") or ""),
                status="closed",
                updated_at=now.isoformat(),
                status_reason="Closed because the source visible run completed successfully.",
            )
            if closed_item is not None:
                auto_closed += 1
                event_bus.publish(
                    "open_loop_signal.closed",
                    {
                        "signal_id": closed_item.get("signal_id"),
                        "signal_type": closed_item.get("signal_type"),
                        "status": closed_item.get("status"),
                        "summary": closed_item.get("summary"),
                        "status_reason": closed_item.get("status_reason"),
                    },
                )
            continue

        # Trin 1: stale → closed efter yderligere _CLOSE_STALE_AFTER_DAYS
        # 2026-05-16 fix: forhindrer at zombie-loops bliver ved med at trigge
        # autonomy_pressure → council → CPU-spinning loop.
        if current_status == "stale" and updated_at < now - timedelta(days=_CLOSE_STALE_AFTER_DAYS):
            closed_item = update_runtime_open_loop_signal_status(
                str(item.get("signal_id") or ""),
                status="closed",
                updated_at=now.isoformat(),
                status_reason="Auto-closed after extended stale inactivity (forhindrer feedback-loop).",
            )
            if closed_item is not None:
                auto_closed += 1
            continue

        # Trin 2: open/softening → stale efter _STALE_AFTER_DAYS
        if current_status in {"open", "softening"}:
            if updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
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
    return {"stale_marked": refreshed, "auto_closed": auto_closed}


def _loop_domain(canonical_key: str) -> str:
    return str(canonical_key or "").rsplit(":", 1)[-1]


def _completed_visible_domains(items: list[dict[str, object]]) -> set[str]:
    domains = {
        _loop_domain(str(item.get("canonical_key") or ""))
        for item in items
        if str(item.get("status") or "") in {"open", "softening"}
    }
    run_ids = sorted(domain for domain in domains if domain.startswith("visible-"))
    if not run_ids:
        return set()
    placeholders = ",".join("?" for _ in run_ids)
    with connect() as conn:
        rows = conn.execute(
            f"SELECT run_id FROM visible_runs WHERE status = 'completed' "
            f"AND run_id IN ({placeholders})",
            run_ids,
        ).fetchall()
    return {str(row["run_id"] or "") for row in rows}


def _open_loop_status_counts() -> dict[str, int]:
    """Tabelsandheden pr. status; aldrig en optælling af en UI-side."""
    counts = {status: 0 for status in _COUNTED_STATUSES}
    # Lagerets offentlige læsevej ejer schema-initialiseringen. På en frisk DB
    # (tests og første boot) findes tabellen ellers endnu ikke.
    list_runtime_open_loop_signals(limit=1)
    with connect() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM runtime_open_loop_signals GROUP BY status"
        ).fetchall()
    for row in rows:
        status = str(row["status"] or "")
        if status in counts:
            counts[status] = int(row["n"] or 0)
    return counts


def build_runtime_open_loop_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return get_timed_runtime_surface(
        ("runtime_open_loop_signal_surface", max(limit, 1)),
        60,
                lambda: _build_runtime_open_loop_signal_surface_uncached(limit=max(limit, 1)),
    )


def _build_runtime_open_loop_signal_surface_uncached(
    *, limit: int = 8
) -> dict[str, object]:
    # Dream bias (Lag 2) — unfinished_business amplifies how many open loops
    # surface. ±40% modulation at intensity=1.0 (limit floor 4, cap 16).
    try:
        from core.services.dream_bias_engine import get_active_dream_bias
        _bias = get_active_dream_bias(workspace_id=current_workspace_name())
        if _bias:
            _modifier = float(_bias["attention_bias"].get("unfinished_business", 0.0))
            _intensity = float(_bias.get("intensity") or 0.0)
            if _modifier != 0.0:
                _shift = _modifier * _intensity * 0.4
                limit = max(4, min(16, int(round(limit * (1.0 + _shift)))))
    except Exception:
        pass
    refresh_runtime_open_loop_signal_statuses()
    counts = _open_loop_status_counts()
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
        "active": bool(counts["open"] or counts["softening"] or counts["closed"]),
        "items": ordered,
        "summary": {
            "open_count": counts["open"],
            "softening_count": counts["softening"],
            "closed_count": counts["closed"],
            "stale_count": counts["stale"],
            "superseded_count": counts["superseded"],
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
    from core.services.private_initiative_tension_signal_tracking import (
        build_runtime_private_initiative_tension_signal_surface,
    )
    from core.services.autonomy_pressure_signal_tracking import (
        build_runtime_autonomy_pressure_signal_surface,
    )
    from core.services.proactive_loop_lifecycle_tracking import (
        build_runtime_proactive_loop_lifecycle_surface,
    )
    from core.services.proactive_question_gate_tracking import (
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
        _bucket(snapshots, focus, _focus_domain_key, "active_focus")

    for critic in list_runtime_reflective_critics(limit=18):
        status = str(critic.get("status") or "")
        if status not in {"active", "resolved"}:
            continue
        _bucket(snapshots, critic, _critic_domain_key,
                "active_critic" if status == "active" else "resolved_critic")

    for goal in list_runtime_goal_signals(limit=18):
        status = str(goal.get("status") or "")
        if status not in {"active", "blocked", "completed"}:
            continue
        _slot = "blocked_goal" if status == "blocked" else ("active_goal" if status == "active" else "completed_goal")
        if status == "active":
            active_goals.append(goal)
        _bucket(snapshots, goal, _goal_domain_key, _slot)

    for reflection in list_runtime_reflection_signals(limit=18):
        status = str(reflection.get("status") or "")
        if status not in {"active", "integrating", "settled"}:
            continue
        _slot = ("active_reflection" if status == "active"
                 else ("integrating_reflection" if status == "integrating" else "settled_reflection"))
        _bucket(snapshots, reflection, _reflection_domain_key, _slot)

    for recurrence in list_runtime_temporal_recurrence_signals(limit=18):
        status = str(recurrence.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        _bucket(snapshots, recurrence, _temporal_domain_key,
                "active_recurrence" if status == "active" else "softening_recurrence")

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
        # Når domænet er en kørsel, er run-id'et ulæseligt som titel. Brug den
        # aktive fokus' egen sætning — den ER retningen i den tur.
        title_suffix = _domain_title(domain_key)
        if active_focus and str(domain_key).startswith(("visible-", "autonomous-", "run_")):
            title_suffix = str(active_focus.get("title") or "").strip() or title_suffix

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
            existing_domain_keys=set(snapshots.keys()),
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

    # Dedup på (signal_type, domæne): et lag registreres nu under BÅDE sin nøgle
    # og sin kørsel, så samme kobling kan dukke op to gange. Uden dette ville
    # ready_count tælle dobbelt (målt: 2 hvor der skulle være 1).
    # Dedup på KILDEPARRET, ikke på domænet: samme lag-kobling kan nu dukke op
    # under både nøgle-aksen og kørsel-aksen, og domænerne er forskellige mens
    # koblingen er den samme. Målt: uden dette blev open_count 2 hvor den skulle
    # være 1. Kilden er kandidatens titel + signal_type — den er stabil fordi
    # den bygges af fokus-titlen, ikke af domænet.
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, object]] = []
    for cand in candidates:
        # Identiteten er KILDERNE, ikke domænet eller titlen: begge bygges af
        # domænet og ændrer sig derfor når samme kobling registreres på to akser.
        # evidence_summary er derimod foldet fra kilderne selv og er stabil.
        sig = (
            str(cand.get("signal_type") or ""),
            str(cand.get("evidence_summary") or ""),
        )
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(cand)
    return unique[:4]


def _materialize_from_creation_readiness(
    readiness: dict[str, object],
    existing_domain_keys: set[str],
) -> dict[str, object] | None:
    aligned_signals = readiness.get("aligned_signals", [])
    if len(aligned_signals) < 3:
        return None

    from core.services.private_initiative_tension_signal_tracking import (
        build_runtime_private_initiative_tension_signal_surface,
    )
    from core.services.autonomy_pressure_signal_tracking import (
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

    total = sum(_open_loop_status_counts().values())
    existing_open_loops = list_runtime_open_loop_signals(limit=max(total, 20))
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


def _topic_key(title: str) -> str:
    """Emnet som identitet ved SKRIVNING — eksakt normaliseret, ikke fuzzy.

    ``canonical_key`` bærer kørslens run_id (``_run_domain``), så opslaget i
    ``_upsert_signal`` aldrig kan matche en tidligere række: samme loop blev
    indsat på ny hver tur (målt 4/11-2026: 8 dublet-familier, 20 rækker).

    Domænet kan ikke erstattes af emnet — det er mødestedet hvor fokus-, critic-,
    goal- og reflection-lagene mødes i samme tur, og ``_with_closure_governance``
    læser det tilbage fra nøglens tredje segment. Emnet bruges derfor kun her.

    Modenheds-præfikset fjernes, så «Open loop: X» og «Softening loop: X» bliver
    SAMME række opdateret i stedet for to. Resten er eksakt: en omformulering er
    et nyt emne, for fuzzy matchning ville kunne smelte to forskellige
    undersøgelser sammen.
    """
    text = " ".join(str(title or "").split()).strip().lower()
    for prefix in ("open loop:", "softening loop:", "closed loop:"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    return text


def _existing_open_loop_keys() -> tuple[dict[str, str], set[str]]:
    """Kort over emne → eksisterende ``canonical_key``, plus alle kendte nøgler.

    Listen er nyeste-først, og vi overskriver undervejs, så den ÆLDSTE række i en
    dublet-familie vinder — den er den oprindelige identitet, ikke en efterfølger.
    """
    topics: dict[str, str] = {}
    keys: set[str] = set()
    for row in list_runtime_open_loop_signals(limit=200):
        if str(row.get("status") or "") not in {"open", "softening", "closed", "stale"}:
            continue
        key = str(row.get("canonical_key") or "")
        if not key:
            continue
        keys.add(key)
        topic = _topic_key(str(row.get("title") or ""))
        if topic:
            topics[topic] = key
    return topics, keys


def _persist_open_loop_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    known_topics, existing_keys = _existing_open_loop_keys()
    for signal in signals:
        canonical_key = str(signal.get("canonical_key") or "")
        topic = _topic_key(str(signal.get("title") or ""))
        # En nøgle der allerede findes er allerede en identitet — fx når
        # closure-maturation genbruger den række den modner. Ellers slår vi
        # emnet op, så samme loop opdateres i stedet for at blive indsat igen.
        if canonical_key not in existing_keys:
            reused_key = known_topics.get(topic) if topic else None
            if reused_key:
                canonical_key = reused_key
            elif topic:
                known_topics[topic] = canonical_key
                existing_keys.add(canonical_key)
        persisted_item = upsert_runtime_open_loop_signal(
            signal_id=f"open-loop-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "open-loop"),
            canonical_key=canonical_key,
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
        # Supersede-kaldet er fjernet (5/11-2026): det sendte kørslens run_id som
        # domain_key, så mønstret ``open-loop:%:{run_id}`` kun kunne matche den
        # række der netop var udelukket. Målt: 0 rækker ramt i hele basens
        # levetid, og ``open_loop_signal.superseded`` havde nul lyttere.
        # Identiteten håndhæves nu ved skrivning via emne-nøglen ovenfor.
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


def _bucket(snapshots: dict, item: dict[str, object], key_fn, slot: str) -> None:
    """Registrér et lag under sit domæne — nøglen først, kørslen som fallback.

    Målt 4/11-2026: nøglen er semantisk (samme EMNE over tid) og er det
    open-loop spørger om. Men fokus-nøglen er en hel sætning og critic-nøglen
    en type, så de mødes aldrig i virkeligheden (fokus ∩ critic = 0). Kørslen
    er den tidslige akse og virker i drift (34 kørsler har både fokus og live
    pressure).

    Nøglen har forrang: giver den et domæne, bruges den — så den semantiske
    kontrakt bevares uændret. Kun når nøglen intet giver (fx en critic af
    typen ``critic:user_correction``) falder vi tilbage til kørslen. Begge
    akser på én gang gav dubletter og brød ready_count, så det er bevidst
    fravalgt her.
    """
    # BEGGE akser registreres (målt 4/11-2026). Nøglen alene gav 0 kandidater i
    # drift, fordi fokus-nøglen altid er en hel sætning: hvert fokus bliver sit
    # eget domæne, og intet andet lag kan dele det. Kørslen alene brød den
    # semantiske kontrakt (to lag om samme emne i forskellige ture skal stadig
    # mødes). Derfor registreres laget under begge — og kandidaterne deduplikeres
    # bagefter på (signal_type, domæne), så ready_count ikke fordobles.
    key_domain = key_fn(str(item.get("canonical_key") or ""))
    run_domain = _run_domain(item)
    # RAEKKEFOELGEN ER FAST (5/11-2026). Et saet her gjorde rækkefølgen vilkaarlig
    # pr. hash-seed: maalt fejlede filens egne tests 1-3 gange i 6 af 6 koersler,
    # fordi run-aksen nogle gange blev itereret foer noegle-aksen og dermed vandt
    # dedup'en nedenfor. Noeglen har forrang (se docstring), saa den registreres
    # foerst — og dermed itereres den foerst.
    for domain_key in (key_domain, run_domain):
        if domain_key:
            snapshots.setdefault(domain_key, {})[slot] = item


def _run_domain(item: dict[str, object]) -> str:
    """Domænet er KØRSLEN når den findes — se ``internal_opposition_signal_tracking``.

    Målt 4/11-2026: open-loop kræver en aktiv fokus OG en live pressure-kilde i
    SAMME domæne. Med nøgle-parsing kunne de aldrig mødes: fokus-nøglen er en
    hel sætning, critic-nøglen er en TYPE (``critic:user_correction``), og
    reflection-nøglen er en besked-slug. Målt: fokus ∩ critic = 0, fokus ∩
    reflection = 0 — uanset hvor mange rækker der blev læst (400-loft gav
    stadig nul kandidater).

    Kørslen er den ene dimension alle lag allerede bærer. Målt i den levende
    base: 34 kørsler har både en aktiv fokus og en live pressure-kilde. Det er
    den ægte kobling — «i denne tur var der både retning og uløst pres».

    Nøgle-parsingen bevares som fallback for rækker uden ``run_id`` (ældre
    data), så kontrakten for dem er uændret.
    """
    run_id = str(item.get("run_id") or "").strip()
    return run_id


def _focus_domain_key(canonical_key: str) -> str:
    # 4/11-2026: krævede præfikset ``development-focus:{kategori}:`` og kasserede
    # derfor alle nyere fokus-nøgler. Målt i den levende base: 3.093 fokus-rækker
    # bærer ``focus:bearing:<sætning>``, kun 905 bærer det gamle format — så 77 %
    # af fokuslaget var usynligt for open-loop. Samme form som
    # ``internal_opposition_signal_tracking._focus_domain_key``.
    #
    # Domænet er det TREDJE segment, ikke det sidste: begge formater har et
    # to-segments præfiks, og det gamle format kan bære en undertype efter
    # domænet (``development-focus:runtime:visible-work:reinforce-retain`` →
    # ``visible-work``). Sidste segment ville give ``reinforce-retain`` og
    # bryde den eksisterende open-loop-kontrakt.
    parts = [part.strip() for part in str(canonical_key or "").split(":") if part.strip()]
    return parts[2] if len(parts) >= 3 else ""


def _critic_domain_key(canonical_key: str) -> str:
    # Producenten skriver ``reflective-critic:mismatch:{fokus-nøgle}``
    # (``reflective_critic_tracking.py:171``); denne funktion forventede et
    # ``development-focus:``-led indskudt som producenten aldrig skriver. Målt:
    # nul af 967 critics har haft det præfiks. Type-nøgler som
    # ``critic:user_correction`` bærer intet domæne og skal fortsat give tomt.
    # Domænet er det FEMTE segment: to for ``reflective-critic:mismatch:`` plus
    # to for fokus-nøglens eget præfiks.
    parts = [part.strip() for part in str(canonical_key or "").split(":") if part.strip()]
    return parts[4] if len(parts) >= 5 else ""


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
