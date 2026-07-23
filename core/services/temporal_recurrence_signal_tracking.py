"""Temporal-recurrence signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the recurrence-specific cross-layer candidate derivation and domain-key mapping
stay here — that is the part unique to temporal recurrence.

Two knobs are non-standard and stay in this file's own ``_build_candidate``:
the confidence rule adds ``or record_count >= 5`` (passed explicitly to
``make_candidate``), and ``support_summary`` / ``support_count`` fold in the
``record_count`` (overridden on the returned candidate — ``make_candidate`` can
only build them from source items). The display token stays "temporal recurrence"
(a space, not the hyphenated slug) via ``track_summary_fn``.
"""
from __future__ import annotations

from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec, make_candidate
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_reflective_critics,
    list_runtime_reflection_signals,
    list_runtime_temporal_recurrence_signals,
    supersede_runtime_temporal_recurrence_signals_for_domain,
    update_runtime_temporal_recurrence_signal_status,
    upsert_runtime_temporal_recurrence_signal,
)

_STALE_AFTER_DAYS = 14


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_temporal_recurrence_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    return _stf.track_for_visible_turn(_SPEC, session_id=session_id, run_id=run_id)


def refresh_runtime_temporal_recurrence_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_temporal_recurrence_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


# ── recurrence-specific cross-layer candidate derivation (unique ~40%) ─────────
def _extract_recurrence_candidates(*_args, **_kwargs) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for focus in list_runtime_development_focuses(limit=18):
        status = str(focus.get("status") or "")
        if status not in {"active", "stale", "completed"}:
            continue
        domain_key = _focus_domain_key(str(focus.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, _empty_snapshot())
        bucket["focus_records"].append(focus)
        if status == "active":
            bucket["active_focus"] = focus

    for critic in list_runtime_reflective_critics(limit=18):
        status = str(critic.get("status") or "")
        if status not in {"active", "stale", "resolved"}:
            continue
        domain_key = _critic_domain_key(str(critic.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, _empty_snapshot())
        bucket["critic_records"].append(critic)
        if status == "active":
            bucket["active_critic"] = critic

    for goal in list_runtime_goal_signals(limit=18):
        status = str(goal.get("status") or "")
        if status not in {"active", "blocked", "completed", "stale"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, _empty_snapshot())
        bucket["goal_records"].append(goal)
        if status == "blocked":
            bucket["blocked_goal"] = goal
        if status == "active":
            bucket["active_goal"] = goal
        if status == "completed":
            bucket["completed_goal"] = goal

    for reflection in list_runtime_reflection_signals(limit=18):
        status = str(reflection.get("status") or "")
        if status not in {"active", "integrating", "settled", "stale"}:
            continue
        domain_key = _reflection_domain_key(str(reflection.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, _empty_snapshot())
        bucket["reflection_records"].append(reflection)
        if status in {"active", "integrating"}:
            bucket["integrating_reflection"] = reflection
        if status == "settled":
            bucket["settled_reflection"] = reflection

    candidates: list[dict[str, object]] = []
    for domain_key, bucket in snapshots.items():
        record_count = sum(
            len(bucket[name])
            for name in ("focus_records", "critic_records", "goal_records", "reflection_records")
        )
        if record_count < 3:
            continue

        active_focus = bucket["active_focus"]
        active_critic = bucket["active_critic"]
        blocked_goal = bucket["blocked_goal"]
        active_goal = bucket["active_goal"]
        integrating_reflection = bucket["integrating_reflection"]
        settled_reflection = bucket["settled_reflection"]
        completed_goal = bucket["completed_goal"]
        title_suffix = _domain_title(domain_key)

        if active_focus and (active_critic or blocked_goal or integrating_reflection):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="recurring-tension",
                    status="active",
                    title=f"Recurring tension: {title_suffix}",
                    summary=f"The same bounded tension around {title_suffix.lower()} keeps returning over time.",
                    rationale="The same domain keeps reappearing across existing development, critic, goal, or reflection truth rather than showing up as a one-off signal.",
                    status_reason="Repeated domain recurrence still carries live pressure.",
                    source_items=[
                        active_focus,
                        active_critic,
                        blocked_goal,
                        integrating_reflection,
                    ],
                    record_count=record_count,
                )
            )
            continue

        if (active_focus or active_goal) and (settled_reflection or completed_goal):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="recurring-direction",
                    status="softening",
                    title=f"Recurring direction: {title_suffix}",
                    summary=f"The same bounded development direction around {title_suffix.lower()} keeps returning, but the thread looks calmer now.",
                    rationale="The domain is recurring across existing tracked layers, but active pressure has eased enough that the pattern now looks more like a carried direction than live friction.",
                    status_reason="The repeated thread is still present, but it is softening into calmer continuity.",
                    source_items=[
                        active_focus,
                        active_goal,
                        settled_reflection,
                        completed_goal,
                    ],
                    record_count=record_count,
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
    record_count: int,
) -> dict[str, object]:
    # canonical_key = "temporal-recurrence:{signal_type}:{domain_key}"; confidence
    # is high when >=3 source layers OR record_count >= 5 (non-default → passed
    # explicitly). support_summary/support_count fold in record_count, which
    # make_candidate cannot express, so they are overridden on the result.
    items = [item for item in source_items if item]
    confidence = "high" if len(items) >= 3 or record_count >= 5 else "medium"
    candidate = make_candidate(
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
        confidence=confidence,
        group_value=domain_key,
    )
    candidate["support_summary"] = _merge_fragments(
        f"{record_count} bounded signal records across existing runtime layers.",
        *[str(item.get("support_summary") or "") for item in items],
    )
    candidate["support_count"] = max(int(candidate["support_count"]), record_count)
    return candidate


def _temporal_recurrence_track_summary(items: list[dict[str, object]], message: str) -> str:
    return (
        f"Tracked {len(items)} bounded temporal recurrence signals."
        if items
        else "No bounded temporal recurrence signal warranted tracking."
    )


# ── spec: standard S-family knobs + _for_domain supersede ──────────────────────
_SPEC = SignalTrackingSpec(
    name="temporal-recurrence",
    slug="temporal-recurrence",
    signal_id_prefix="recurrence",
    event_prefix="temporal_recurrence_signal",
    default_signal_type="temporal-recurrence",
    list_fn=list_runtime_temporal_recurrence_signals,
    upsert_fn=upsert_runtime_temporal_recurrence_signal,
    update_status_fn=update_runtime_temporal_recurrence_signal_status,
    supersede_fn=supersede_runtime_temporal_recurrence_signals_for_domain,
    supersede_group_field="domain_key",
    supersede_group_kw="domain_key",
    extract_fn=_extract_recurrence_candidates,
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active", "softening"}),
    stale_status_reason="Marked stale after bounded recurrence inactivity window.",
    surface_status_order=("active", "softening", "stale", "superseded"),
    surface_active_statuses=frozenset({"active", "softening"}),
    empty_current_label="No active temporal recurrence signal",
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
    track_summary_fn=_temporal_recurrence_track_summary,
)


# ── recurrence-specific snapshot scaffolding + domain-key mapping (unique) ─────
def _empty_snapshot() -> dict[str, object]:
    return {
        "focus_records": [],
        "critic_records": [],
        "goal_records": [],
        "reflection_records": [],
        "active_focus": None,
        "active_critic": None,
        "blocked_goal": None,
        "active_goal": None,
        "completed_goal": None,
        "integrating_reflection": None,
        "settled_reflection": None,
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
        return text.removeprefix("reflective-critic:mismatch:development-focus:communication:")
    if text.startswith("reflective-critic:mismatch:development-focus:user-directed:"):
        return text.removeprefix("reflective-critic:mismatch:development-focus:user-directed:")
    if text.startswith("reflective-critic:mismatch:development-focus:runtime:"):
        parts = text.removeprefix("reflective-critic:mismatch:development-focus:runtime:").split(":")
        return parts[0] if parts else ""
    return ""


def _goal_domain_key(canonical_key: str) -> str:
    return str(canonical_key or "").removeprefix("goal-signal:")


def _reflection_domain_key(canonical_key: str) -> str:
    parts = str(canonical_key or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Recurring thread"


def _merge_fragments(*values: str) -> str:
    parts: list[str] = []
    for value in values:
        normalized = " ".join(str(value or "").split()).strip()
        if normalized and normalized not in parts:
            parts.append(normalized)
    return " | ".join(parts[:4])
