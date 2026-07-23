"""Reflection signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below now delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the reflection-specific candidate derivation, domain-key mapping, and history
labelling stay here — that is the part unique to reflection.

Reflection is one of the *richest* variants (its ``.settled`` event, early-retire
window, and ``{active,integrating,settled}`` status set are atypical); every one
of those is expressed as an explicit field on the spec below so nothing leaks and
nothing is lost.
"""
from __future__ import annotations

from core.services.signal_noise_guard import is_noisy_signal_text
from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec, make_candidate
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_reflective_critics,
    list_runtime_reflection_signals,
    list_runtime_self_model_signals,
    supersede_runtime_reflection_signals_for_domain,
    update_runtime_reflection_signal_status,
    upsert_runtime_reflection_signal,
)

_STALE_AFTER_DAYS = 14
_EARLY_RETIRE_DAYS = 2
_REFRESH_SCAN_LIMIT = 3000


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_reflection_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
    user_message: str,
) -> dict[str, object]:
    return _stf.track_for_visible_turn(
        _SPEC, session_id=session_id, run_id=run_id, user_message=user_message
    )


def refresh_runtime_reflection_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_reflection_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


# ── reflection-specific candidate derivation (unique ~40%) ────────────────────
def _extract_reflection_candidates(*_args, **_kwargs) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for focus in list_runtime_development_focuses(limit=12):
        if str(focus.get("status") or "") != "active":
            continue
        domain_key = _domain_key_from_focus(str(focus.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["focus"] = focus

    for critic in list_runtime_reflective_critics(limit=12):
        if str(critic.get("status") or "") != "active":
            continue
        domain_key = _domain_key_from_critic(str(critic.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["critic"] = critic

    for signal in list_runtime_self_model_signals(limit=16):
        status = str(signal.get("status") or "")
        if status not in {"active", "uncertain"}:
            continue
        domain_key = _domain_key_from_self_model(str(signal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        signal_type = str(signal.get("signal_type") or "")
        if signal_type == "current-limitation" and status == "active":
            bucket["self_limitation"] = signal
        if signal_type == "improvement-edge":
            bucket["improvement_edge"] = signal

    for goal in list_runtime_goal_signals(limit=16):
        status = str(goal.get("status") or "")
        if status not in {"active", "blocked"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "blocked":
            bucket["blocked_goal"] = goal
        else:
            bucket["goal"] = goal

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        focus = snapshot.get("focus")
        critic = snapshot.get("critic")
        self_limitation = snapshot.get("self_limitation")
        improvement_edge = snapshot.get("improvement_edge")
        blocked_goal = snapshot.get("blocked_goal")
        goal = snapshot.get("goal")
        title_suffix = _domain_title(domain_key)

        if focus and critic and self_limitation:
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="persistent-tension",
                    status="active",
                    title=f"Persistent reflection tension: {title_suffix}",
                    summary=f"Jarvis is still carrying unresolved reflective pressure around {title_suffix.lower()}.",
                    rationale="Development focus, reflective critic, and self-model limitation all still point at the same bounded problem domain.",
                    status_reason="Multiple bounded layers still agree that this tension is live.",
                    source_items=[focus, critic, self_limitation, blocked_goal],
                )
            )
            continue

        if focus and improvement_edge and not critic and not blocked_goal:
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="settled-thread",
                    status="settled",
                    title=f"Settled reflection thread: {title_suffix}",
                    summary=f"A previously tense reflective thread around {title_suffix.lower()} now appears calmer.",
                    rationale="A prior weak area now has explicit better-now style feedback without matching active critic pressure or blocked-goal pressure.",
                    status_reason="The bounded thread appears meaningfully calmer and is now being retained as settled rather than live tension.",
                    source_items=[focus, goal, improvement_edge],
                )
            )
            continue

        if focus and (goal or blocked_goal) and (self_limitation or improvement_edge) and not critic:
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="slow-integration",
                    status="integrating",
                    title=f"Slow integration thread: {title_suffix}",
                    summary=f"Jarvis is carrying a slow integration thread around {title_suffix.lower()}.",
                    rationale="Multiple bounded layers still point at the same improvement domain, but active reflective mismatch pressure has eased enough that the thread should be treated as integration rather than raw tension.",
                    status_reason="Cross-layer support remains live, but the domain is moving from pressure into integration.",
                    source_items=[focus, goal, blocked_goal, self_limitation, improvement_edge],
                )
            )

    return candidates[:4]


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
    # canonical_key = "reflection-signal:{signal_type}:{domain_key}"; confidence
    # high when >=3 source layers else medium — matches the original exactly.
    return make_candidate(
        _SPEC,
        signal_type=signal_type,
        discriminator=signal_type,
        key=domain_key,
        status=status,
        title=title,
        summary=summary,
        rationale=rationale,
        status_reason=status_reason,
        source_items=source_items,
        group_value=domain_key,
    )


# ── reflection-specific surface + refresh hooks ───────────────────────────────
def _history_item_from_signal(item: dict[str, object]) -> dict[str, object]:
    status = str(item.get("status") or "unknown")
    return {
        "signal_id": item.get("signal_id"),
        "signal_type": item.get("signal_type"),
        "title": item.get("title"),
        "status": status,
        "transition": _history_transition_label(
            signal_type=str(item.get("signal_type") or ""),
            status=status,
        ),
        "confidence": item.get("confidence"),
        "summary": item.get("summary"),
        "status_reason": item.get("status_reason"),
        "updated_at": item.get("updated_at"),
        "created_at": item.get("created_at"),
    }


def _reflection_early_retire(item: dict[str, object]) -> bool:
    return (
        str(item.get("confidence") or "") == "low"
        or int(item.get("support_count") or 0) <= 1
        or is_noisy_signal_text(str(item.get("title") or "") + " " + str(item.get("summary") or ""))
    )


def _reflection_track_summary(items: list[dict[str, object]], message: str) -> str:
    if items:
        return f"Tracked {len(items)} bounded reflection signals."
    if message:
        return f"No bounded reflection signal warranted tracking for '{message[:80]}'."
    return "No bounded reflection signal warranted tracking."


# ── spec: every reflection-specific knob made explicit ────────────────────────
_SPEC = SignalTrackingSpec(
    name="reflection",
    slug="reflection-signal",
    signal_id_prefix="reflection",
    event_prefix="reflection_signal",
    default_signal_type="reflection-signal",
    list_fn=list_runtime_reflection_signals,
    upsert_fn=upsert_runtime_reflection_signal,
    update_status_fn=update_runtime_reflection_signal_status,
    supersede_fn=supersede_runtime_reflection_signals_for_domain,
    supersede_group_field="domain_key",
    supersede_group_kw="domain_key",
    extract_fn=_extract_reflection_candidates,
    stale_after_days=_STALE_AFTER_DAYS,
    early_retire_days=_EARLY_RETIRE_DAYS,
    early_retire_predicate=_reflection_early_retire,
    refresh_scan_limit=_REFRESH_SCAN_LIMIT,
    refreshable_statuses=frozenset({"active", "integrating", "settled"}),
    stale_status_reason="Marked stale after bounded reflection inactivity window.",
    surface_status_order=("active", "integrating", "settled", "stale", "superseded"),
    surface_active_statuses=frozenset({"active", "integrating", "settled"}),
    surface_history_cap=6,
    history_item_fn=_history_item_from_signal,
    empty_current_label="No active reflection signal",
    extra_status_events={"settled": "reflection_signal.settled"},
    stale_payload_extra=("status_reason",),
    superseded_payload_extra=("canonical_key",),
    track_summary_fn=_reflection_track_summary,
)


# ── reflection-specific domain-key mapping + labels (unique) ───────────────────
def _domain_key_from_focus(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if "danish-concise-calibration" in text:
        return "danish-concise-calibration"
    if "avoid-repetitive-openers" in text:
        return "avoid-repetitive-openers"
    if text.startswith("development-focus:"):
        return text.removeprefix("development-focus:").replace(":", "-")
    return ""


def _domain_key_from_critic(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if "danish-concise-calibration" in text:
        return "danish-concise-calibration"
    if "avoid-repetitive-openers" in text:
        return "avoid-repetitive-openers"
    prefix = "reflective-critic:mismatch:development-focus:"
    if text.startswith(prefix):
        return text.removeprefix(prefix).replace(":", "-")
    return ""


def _domain_key_from_self_model(canonical_key: str) -> str:
    text = str(canonical_key or "")
    if text.startswith("self-model:limitation:"):
        return text.removeprefix("self-model:limitation:")
    if text.startswith("self-model:improving:"):
        return text.removeprefix("self-model:improving:")
    return ""


def _goal_domain_key(canonical_key: str) -> str:
    return str(canonical_key or "").removeprefix("goal-signal:")


def _domain_title(domain_key: str) -> str:
    if domain_key == "danish-concise-calibration":
        return "Danish concise calibration"
    if domain_key == "avoid-repetitive-openers":
        return "opener calibration"
    return domain_key.replace("-", " ") or "current bounded thread"


def _history_transition_label(*, signal_type: str, status: str) -> str:
    normalized_status = str(status or "").strip()
    if normalized_status == "active":
        return "active tension"
    if normalized_status == "integrating":
        return "slow integration"
    if normalized_status == "settled":
        return "recent settling"
    if normalized_status == "stale":
        return "went stale"
    if normalized_status == "superseded":
        return "superseded"
    normalized_type = str(signal_type or "").strip()
    if normalized_type == "persistent-tension":
        return "persistent tension"
    if normalized_type == "slow-integration":
        return "slow integration"
    if normalized_type == "settled-thread":
        return "recent settling"
    return "reflection update"
