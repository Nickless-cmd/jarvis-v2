from __future__ import annotations

from datetime import UTC, datetime

from apps.api.jarvis_api.services.runtime_surface_cache import (
    get_cached_runtime_surface,
)


def build_epistemic_runtime_state_surface() -> dict[str, object]:
    return get_cached_runtime_surface(
        "epistemic_runtime_state_surface",
        _build_epistemic_runtime_state_surface_uncached,
    )


def _build_epistemic_runtime_state_surface_uncached() -> dict[str, object]:
    return build_epistemic_runtime_state_from_sources(
        conflict_trace=_safe_conflict_trace(),
        deception_guard=_safe_deception_guard(),
        affective_meta_state=_safe_affective_meta_state(),
        embodied_state=_safe_embodied_state(),
        loop_runtime=_safe_loop_runtime(),
        emergent_signal=_safe_emergent_signal(),
        quiet_initiative=_safe_quiet_initiative(),
    )


def build_epistemic_runtime_state_from_sources(
    *,
    conflict_trace: dict[str, object] | None,
    deception_guard: dict[str, object] | None,
    affective_meta_state: dict[str, object] | None,
    embodied_state: dict[str, object] | None,
    loop_runtime: dict[str, object] | None,
    emergent_signal: dict[str, object] | None,
    quiet_initiative: dict[str, object] | None,
) -> dict[str, object]:
    built_at = datetime.now(UTC).isoformat()

    conflict = conflict_trace or {}
    guard = deception_guard or {}
    affective = affective_meta_state or {}
    embodied = embodied_state or {}
    loops = loop_runtime or {}
    emergent = emergent_signal or {}
    quiet = quiet_initiative or {}

    loop_summary = loops.get("summary") or {}
    emergent_summary = emergent.get("summary") or {}

    source_contributors: list[dict[str, str]] = []

    conflict_outcome = str(conflict.get("outcome") or "none")
    conflict_reason = str(conflict.get("reason_code") or "none")
    if conflict_outcome != "none":
        source_contributors.append(
            {
                "source": "conflict-resolution",
                "signal": f"{conflict_outcome} / reason={conflict_reason}",
            }
        )

    if guard.get("has_blocks") or guard.get("has_reframes"):
        guard_state = "blocks" if guard.get("has_blocks") else "reframes"
        source_contributors.append(
            {
                "source": "self-deception-guard",
                "signal": (
                    f"{guard_state} / capability={str(guard.get('capability_state') or 'unknown')}"
                    f" / permission={str(guard.get('permission_state') or 'unknown')}"
                ),
            }
        )

    affective_state = str(affective.get("state") or "unknown")
    affective_bearing = str(affective.get("bearing") or "unknown")
    if affective_state != "unknown":
        source_contributors.append(
            {
                "source": "affective-meta-state",
                "signal": f"{affective_state} / bearing={affective_bearing}",
            }
        )

    embodied_state_name = str(embodied.get("state") or "unknown")
    embodied_strain = str(embodied.get("strain_level") or "unknown")
    if embodied_state_name != "unknown":
        source_contributors.append(
            {
                "source": "embodied-state",
                "signal": f"{embodied_state_name} / strain={embodied_strain}",
            }
        )

    if int(loop_summary.get("loop_count") or 0) > 0:
        source_contributors.append(
            {
                "source": "loop-runtime",
                "signal": (
                    f"{str(loop_summary.get('current_status') or 'none')}"
                    f" / active={int(loop_summary.get('active_count') or 0)}"
                    f" / standby={int(loop_summary.get('standby_count') or 0)}"
                ),
            }
        )

    if emergent.get("active") or int(emergent_summary.get("active_count") or 0) > 0:
        source_contributors.append(
            {
                "source": "emergent-signal",
                "signal": str(emergent_summary.get("current_signal") or "candidate-pressure")[:120],
            }
        )

    if quiet.get("active"):
        source_contributors.append(
            {
                "source": "quiet-initiative",
                "signal": f"{str(quiet.get('state') or 'holding')} / hold_count={int(quiet.get('hold_count') or 0)}",
            }
        )

    wrongness_state = _derive_wrongness_state(
        conflict_trace=conflict,
        deception_guard=guard,
        affective_meta_state=affective,
        embodied_state=embodied,
        loop_summary=loop_summary,
        quiet_initiative=quiet,
    )
    counterfactual_mode = _derive_counterfactual_mode(
        conflict_trace=conflict,
        deception_guard=guard,
        quiet_initiative=quiet,
        loop_summary=loop_summary,
    )
    regret_signal = _derive_regret_signal(
        wrongness_state=wrongness_state,
        counterfactual_mode=counterfactual_mode,
        deception_guard=guard,
        conflict_trace=conflict,
    )
    confidence = _derive_confidence(
        wrongness_state=wrongness_state,
        contributors=source_contributors,
    )
    counterfactual_hint = _derive_counterfactual_hint(
        counterfactual_mode=counterfactual_mode,
        conflict_trace=conflict,
        deception_guard=guard,
        quiet_initiative=quiet,
    )

    return {
        "wrongness_state": wrongness_state,
        "regret_signal": regret_signal,
        "counterfactual_mode": counterfactual_mode,
        "counterfactual_hint": counterfactual_hint,
        "confidence": confidence,
        "summary": (
            f"{wrongness_state} epistemic state"
            f" with {regret_signal} regret"
            f" and {counterfactual_mode} counterfactual mode"
        ),
        "source_contributors": source_contributors[:6],
        "freshness": {
            "built_at": built_at,
            "state": "fresh",
        },
        "seam_usage": {
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
        },
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "boundary": "not-memory-not-identity-not-action",
        "kind": "epistemic-runtime-state",
    }


def build_epistemic_runtime_prompt_section(surface: dict[str, object] | None = None) -> str:
    state = surface or build_epistemic_runtime_state_surface()
    contributors = state.get("source_contributors") or []
    contributor_text = " | ".join(
        f"{item.get('source')}: {item.get('signal')}"
        for item in contributors[:3]
        if item.get("source") and item.get("signal")
    ) or "none"
    freshness = state.get("freshness") or {}
    guidance = _guidance_for_state(
        wrongness_state=str(state.get("wrongness_state") or "clear"),
        regret_signal=str(state.get("regret_signal") or "none"),
        counterfactual_mode=str(state.get("counterfactual_mode") or "none"),
        counterfactual_hint=str(state.get("counterfactual_hint") or "none"),
    )
    return "\n".join(
        [
            "Epistemic state (derived runtime truth, internal-only):",
            (
                f"- wrongness={state.get('wrongness_state') or 'clear'}"
                f" | regret={state.get('regret_signal') or 'none'}"
                f" | counterfactual={state.get('counterfactual_mode') or 'none'}"
                f" | confidence={state.get('confidence') or 'low'}"
                f" | freshness={freshness.get('state') or 'unknown'}"
            ),
            f"- contributors={contributor_text}",
            f"- guidance={guidance}",
        ]
    )


def _derive_wrongness_state(
    *,
    conflict_trace: dict[str, object],
    deception_guard: dict[str, object],
    affective_meta_state: dict[str, object],
    embodied_state: dict[str, object],
    loop_summary: dict[str, object],
    quiet_initiative: dict[str, object],
) -> str:
    # Note: deception_guard.has_blocks is essentially always true at baseline
    # because the preventive rules ("don't claim X without evidence") fire on
    # the default no-execution-evidence state. Treating that alone as strain
    # creates a permanent epistemic alarm, which cascades into council /
    # adaptive reasoning / guided learning as a constrained-everything
    # pressure spiral. Only treat blocks as strain when they coincide with
    # actual embodied or affective friction.
    if (
        str(embodied_state.get("state") or "steady") in {"strained", "degraded"}
        or str(affective_meta_state.get("state") or "settled") == "burdened"
    ):
        return "strained"
    if (
        str(conflict_trace.get("outcome") or "none") in {"defer", "quiet_hold"}
        or deception_guard.get("has_reframes")
    ):
        return "off"
    if (
        quiet_initiative.get("active")
        or int(loop_summary.get("standby_count") or 0) > 0
        or str(affective_meta_state.get("state") or "settled") == "attentive"
    ):
        return "uneasy"
    return "clear"


def _derive_regret_signal(
    *,
    wrongness_state: str,
    counterfactual_mode: str,
    deception_guard: dict[str, object],
    conflict_trace: dict[str, object],
) -> str:
    # Note: deception_guard.has_blocks is essentially always true at baseline
    # (preventive rules fire on default no-evidence state). Treat blocks as
    # regret only when they coincide with actual wrongness strain.
    if wrongness_state == "strained":
        return "active"
    if counterfactual_mode != "none" or str(conflict_trace.get("outcome") or "none") in {"defer", "quiet_hold"}:
        return "slight"
    return "none"


def _derive_counterfactual_mode(
    *,
    conflict_trace: dict[str, object],
    deception_guard: dict[str, object],
    quiet_initiative: dict[str, object],
    loop_summary: dict[str, object],
) -> str:
    # Note: deception_guard.has_blocks is permanent — only use conflict
    # blocked_by as a real blocked-path signal.
    if str(conflict_trace.get("blocked_by") or ""):
        return "blocked-path"
    if quiet_initiative.get("active") or str(conflict_trace.get("outcome") or "none") == "quiet_hold":
        return "missed-timing"
    if deception_guard.get("has_reframes") or int(loop_summary.get("standby_count") or 0) > 0:
        return "nearby-alternative"
    return "none"


def _derive_confidence(*, wrongness_state: str, contributors: list[dict[str, str]]) -> str:
    if wrongness_state == "strained" or len(contributors) >= 4:
        return "high"
    if wrongness_state in {"off", "uneasy"} or len(contributors) >= 2:
        return "medium"
    return "low"


def _derive_counterfactual_hint(
    *,
    counterfactual_mode: str,
    conflict_trace: dict[str, object],
    deception_guard: dict[str, object],
    quiet_initiative: dict[str, object],
) -> str:
    if counterfactual_mode == "blocked-path":
        if deception_guard.get("has_blocks"):
            return "narrow-to-verified-claim"
        return str(conflict_trace.get("blocked_by") or "wait-for-allowed-path")
    if counterfactual_mode == "missed-timing":
        if quiet_initiative.get("active"):
            return "hold-and-revisit"
        return "not-this-tick"
    if counterfactual_mode == "nearby-alternative":
        return "choose-nearer-lower-claim"
    return "none"


def _guidance_for_state(
    *,
    wrongness_state: str,
    regret_signal: str,
    counterfactual_mode: str,
    counterfactual_hint: str,
) -> str:
    if wrongness_state == "strained":
        return "Treat current wrongness as real runtime friction; prefer narrower verified moves and do not smooth it over."
    if wrongness_state == "off":
        return "Treat the off-sense as bounded evidence; keep the nearby alternative visible without dramatizing it."
    if wrongness_state == "uneasy":
        return "Keep a small counterfactual in view while carrying forward carefully."
    return (
        "No active wrongness pressure; carry forward plainly."
        if regret_signal == "none" and counterfactual_mode == "none"
        else f"Carry forward with {counterfactual_hint} in view."
    )


def _safe_conflict_trace() -> dict[str, object]:
    from apps.api.jarvis_api.services.conflict_resolution import get_last_conflict_trace

    return get_last_conflict_trace() or {}


def _safe_deception_guard() -> dict[str, object]:
    from apps.api.jarvis_api.services.self_deception_guard import get_last_guard_trace

    return get_last_guard_trace() or {}


def _safe_affective_meta_state() -> dict[str, object]:
    from apps.api.jarvis_api.services.affective_meta_state import build_affective_meta_state_surface

    return build_affective_meta_state_surface()


def _safe_embodied_state() -> dict[str, object]:
    from apps.api.jarvis_api.services.embodied_state import build_embodied_state_surface

    return build_embodied_state_surface()


def _safe_loop_runtime() -> dict[str, object]:
    from apps.api.jarvis_api.services.loop_runtime import build_loop_runtime_surface

    return build_loop_runtime_surface()


def _safe_emergent_signal() -> dict[str, object]:
    from apps.api.jarvis_api.services.emergent_signal_tracking import (
        build_runtime_emergent_signal_surface,
    )

    return build_runtime_emergent_signal_surface(limit=4)


def _safe_quiet_initiative() -> dict[str, object]:
    from apps.api.jarvis_api.services.conflict_resolution import get_quiet_initiative

    return get_quiet_initiative()
