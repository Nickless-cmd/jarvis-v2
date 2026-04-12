from __future__ import annotations

import math
import re
from datetime import UTC, datetime
from typing import Any

from apps.api.jarvis_api.services.executive_contradiction_signal_tracking import (
    build_runtime_executive_contradiction_signal_surface,
)
from apps.api.jarvis_api.services.initiative_queue import get_pending_initiatives
from apps.api.jarvis_api.services.loop_runtime import build_loop_runtime_surface
from apps.api.jarvis_api.services.private_initiative_tension_signal_tracking import (
    build_runtime_private_initiative_tension_signal_surface,
)
from core.runtime.db import (
    recent_runtime_learning_signals,
    recent_runtime_action_outcomes,
    recent_visible_runs,
    recent_visible_work_notes,
    recent_visible_work_units,
    visible_session_continuity,
)


def build_operational_memory_snapshot(*, limit: int = 12) -> dict[str, Any]:
    loops = recent_open_loops(limit=min(limit, 6))
    outcomes = recent_visible_outcomes(limit=min(limit, 6))
    tensions = active_internal_pressures(limit=min(limit, 4))
    contradictions = active_executive_contradictions(limit=min(limit, 4))
    initiatives = queued_initiatives(limit=min(limit, 4))
    executive_feedback = recent_executive_feedback(limit=min(limit, 6))
    executive_feedback_summary = summarize_executive_feedback(executive_feedback)
    runtime_learning = recent_persisted_learning(limit=min(limit * 4, 32))
    runtime_learning_summary = summarize_runtime_learning_signals(runtime_learning)
    semantic_feedback_summary = summarize_semantic_feedback(executive_feedback)
    continuity = visible_session_continuity()
    user_facts = remembered_user_facts(limit=min(limit, 3))
    work_context = active_work_context(limit=min(limit, 5))
    recent_notes = recent_visible_work_notes(limit=min(limit, 6))
    note_loop_synergies = summarize_note_loop_synergies(loops=loops, notes=recent_notes)

    return {
        "open_loops": loops,
        "recent_outcomes": outcomes,
        "user_facts": user_facts,
        "internal_pressures": tensions,
        "executive_contradictions": contradictions,
        "queued_initiatives": initiatives,
        "executive_feedback": executive_feedback,
        "executive_feedback_summary": executive_feedback_summary,
        "runtime_learning": runtime_learning,
        "runtime_learning_summary": runtime_learning_summary,
        "semantic_feedback_summary": semantic_feedback_summary,
        "work_context": work_context,
        "note_loop_synergies": note_loop_synergies,
        "visible_continuity": continuity,
        "summary": {
            "open_loop_count": len(loops),
            "recent_outcome_count": len(outcomes),
            "executive_outcome_count": len(executive_feedback),
            "initiative_count": len(initiatives),
            "pressure_count": len(tensions),
            "contradiction_count": len(contradictions),
            "note_loop_synergy_count": len(note_loop_synergies),
            "memory_context_stale": (
                len(outcomes) == 0
                and len(executive_feedback) == 0
                and len(work_context) <= 1
            ),
            "continuity_summary": str(continuity.get("summary") or ""),
            "latest_executive_action": executive_feedback_summary["latest_action"],
            "latest_executive_status": executive_feedback_summary["latest_status"],
            "repeat_action_detected": executive_feedback_summary["repeat_action_detected"],
            "blocked_action_detected": executive_feedback_summary["blocked_action_detected"],
            "semantic_signal_count": int(semantic_feedback_summary.get("signal_count") or 0),
            "persistent_learning_signal_count": int(runtime_learning_summary.get("signal_count") or 0),
        },
    }


def recent_open_loops(*, limit: int = 5) -> list[dict[str, Any]]:
    runtime = build_loop_runtime_surface()
    items = list(runtime.get("items") or [])
    live_items = [
        item
        for item in items
        if str(item.get("runtime_status") or "") in {"active", "resumed", "standby"}
    ]
    return live_items[: max(limit, 1)]


def recent_visible_outcomes(*, limit: int = 5) -> list[dict[str, Any]]:
    notes = recent_visible_work_notes(limit=max(limit, 1))
    if notes:
        return notes[: max(limit, 1)]
    units = recent_visible_work_units(limit=max(limit, 1))
    if units:
        return units[: max(limit, 1)]
    return recent_visible_runs(limit=max(limit, 1))


def active_internal_pressures(*, limit: int = 5) -> list[dict[str, Any]]:
    surface = build_runtime_private_initiative_tension_signal_surface(limit=max(limit, 1))
    items = list(surface.get("items") or [])
    return [
        item
        for item in items
        if str(item.get("status") or "") == "active"
    ][: max(limit, 1)]


def active_executive_contradictions(*, limit: int = 5) -> list[dict[str, Any]]:
    surface = build_runtime_executive_contradiction_signal_surface(limit=max(limit, 1))
    items = list(surface.get("items") or [])
    return [
        item
        for item in items
        if str(item.get("status") or "") in {"active", "softening"}
    ][: max(limit, 1)]


def remembered_user_facts(*, limit: int = 5) -> list[dict[str, Any]]:
    continuity = visible_session_continuity()
    notes = list(continuity.get("recent_notes") or [])
    facts: list[dict[str, Any]] = []
    for item in notes[: max(limit, 1)]:
        preview = str(item.get("user_message_preview") or "").strip()
        if not preview:
            continue
        facts.append(
            {
                "source": "visible-note",
                "summary": preview[:200],
                "created_at": str(item.get("created_at") or ""),
            }
        )
    return facts


def active_work_context(*, limit: int = 5) -> list[dict[str, Any]]:
    items = recent_visible_work_units(limit=max(limit, 1))
    context: list[dict[str, Any]] = []
    for item in items:
        context.append(
            {
                "source": "visible-work-unit",
                "work_id": str(item.get("work_id") or ""),
                "summary": str(item.get("work_preview") or item.get("user_message_preview") or "")[:200],
                "status": str(item.get("status") or ""),
                "updated_at": str(item.get("finished_at") or item.get("started_at") or ""),
            }
        )
    return context[: max(limit, 1)]


def queued_initiatives(*, limit: int = 5) -> list[dict[str, Any]]:
    return get_pending_initiatives()[: max(limit, 1)]


def recent_executive_feedback(*, limit: int = 6) -> list[dict[str, Any]]:
    return recent_runtime_action_outcomes(limit=max(limit, 1))[: max(limit, 1)]


def recent_persisted_learning(*, limit: int = 24) -> list[dict[str, Any]]:
    return recent_runtime_learning_signals(limit=max(limit, 1))[: max(limit, 1)]


def summarize_executive_feedback(
    items: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    normalized = list(items or [])
    latest = normalized[0] if normalized else {}
    now = datetime.now(UTC)
    action_stats: dict[str, dict[str, Any]] = {}
    for item in normalized:
        action_id = str(item.get("action_id") or "").strip()
        if not action_id:
            continue
        status = str(item.get("result_status") or "unknown").strip() or "unknown"
        recorded_at = str(item.get("recorded_at") or "")
        recency_weight = _feedback_recency_weight(recorded_at, now=now)
        no_change_detected = _outcome_looks_like_no_change(item)
        bucket = action_stats.setdefault(
            action_id,
            {
                "count": 0,
                "latest_status": status,
                "latest_recorded_at": recorded_at,
                "latest_age_seconds": _feedback_age_seconds(recorded_at, now=now),
                "success_count": 0,
                "blocked_count": 0,
                "failed_count": 0,
                "no_change_count": 0,
                "executed_count": 0,
                "proposed_count": 0,
                "success_weight": 0.0,
                "blocked_weight": 0.0,
                "failed_weight": 0.0,
                "no_change_weight": 0.0,
            },
        )
        bucket["count"] += 1
        bucket["latest_status"] = bucket.get("latest_status") or status
        if not bucket.get("latest_recorded_at"):
            bucket["latest_recorded_at"] = recorded_at
        if bucket.get("latest_age_seconds") is None:
            bucket["latest_age_seconds"] = _feedback_age_seconds(recorded_at, now=now)
        if status in {"executed", "recorded", "sent"}:
            bucket["success_count"] += 1
            bucket["success_weight"] += recency_weight
        if status == "blocked":
            bucket["blocked_count"] += 1
            bucket["blocked_weight"] += recency_weight
        if status == "failed":
            bucket["failed_count"] += 1
            bucket["failed_weight"] += recency_weight
        if status == "executed":
            bucket["executed_count"] += 1
        if status == "proposed":
            bucket["proposed_count"] += 1
        if no_change_detected:
            bucket["no_change_count"] += 1
            bucket["no_change_weight"] += recency_weight
    repeat_action_detected = False
    blocked_action_detected = False
    if len(normalized) >= 2:
        first = str(normalized[0].get("action_id") or "")
        second = str(normalized[1].get("action_id") or "")
        repeat_action_detected = bool(first and first == second)
    if normalized:
        blocked_action_detected = any(
            str(item.get("result_status") or "") in {"blocked", "failed"}
            for item in normalized[:2]
        )
    return {
        "latest_action": str(latest.get("action_id") or "none"),
        "latest_status": str(latest.get("result_status") or "none"),
        "repeat_action_detected": repeat_action_detected,
        "blocked_action_detected": blocked_action_detected,
        "action_stats": action_stats,
    }


def summarize_note_loop_synergies(
    *,
    loops: list[dict[str, Any]] | None,
    notes: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    loop_items = list(loops or [])
    note_items = list(notes or [])
    if not loop_items or not note_items:
        return []

    now = datetime.now(UTC)
    synergies: list[dict[str, Any]] = []
    for loop in loop_items:
        loop_id = str(loop.get("loop_id") or "").strip()
        canonical_key = str(loop.get("canonical_key") or "").strip()
        title = str(loop.get("title") or loop.get("summary") or "").strip()
        domain_key = _domain_key(loop_id=loop_id, canonical_key=canonical_key)
        loop_tokens = _signal_tokens(" ".join(part for part in (canonical_key, title) if part))
        if domain_key:
            loop_tokens.add(domain_key.lower())
        best_match: dict[str, Any] | None = None
        for note in note_items:
            preview = str(note.get("work_preview") or "").strip()
            if not preview:
                continue
            note_tokens = _signal_tokens(preview)
            overlap = sorted(loop_tokens & note_tokens)
            if domain_key and domain_key.lower() in preview.lower():
                overlap.append(domain_key.lower())
            overlap = list(dict.fromkeys(overlap))
            if not overlap:
                continue
            age_seconds = _feedback_age_seconds(
                str(note.get("finished_at") or note.get("created_at") or ""),
                now=now,
            )
            recency_weight = _feedback_recency_weight(
                str(note.get("finished_at") or note.get("created_at") or ""),
                now=now,
            )
            match_score = min(0.3, 0.08 * len(overlap)) * recency_weight
            if match_score <= 0.02:
                continue
            candidate = {
                "loop_id": loop_id,
                "canonical_key": canonical_key,
                "title": title[:200],
                "note_id": str(note.get("note_id") or ""),
                "note_preview": preview[:220],
                "projection_source": str(note.get("projection_source") or ""),
                "matched_terms": overlap[:6],
                "match_score": round(match_score, 4),
                "age_seconds": age_seconds,
            }
            if best_match is None or float(candidate["match_score"]) > float(best_match["match_score"]):
                best_match = candidate
        if best_match is not None:
            synergies.append(best_match)
    synergies.sort(key=lambda item: float(item.get("match_score") or 0.0), reverse=True)
    return synergies


def summarize_runtime_learning_signals(
    items: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    normalized = list(items or [])
    signal_stats: dict[str, dict[str, Any]] = {}
    family_signal_stats: dict[str, dict[str, dict[str, Any]]] = {}
    action_signal_stats: dict[str, dict[str, dict[str, Any]]] = {}
    for item in normalized:
        signal_key = str(item.get("signal_key") or "").strip()
        if not signal_key:
            continue
        signal_weight = float(item.get("signal_weight") or 0.0)
        signal_count = int(item.get("signal_count") or 1)
        _accumulate_signal_bucket(signal_stats, signal_key, signal_weight, signal_count)

        target_family = str(item.get("target_family") or "").strip()
        if target_family:
            family_bucket = family_signal_stats.setdefault(target_family, {})
            _accumulate_signal_bucket(family_bucket, signal_key, signal_weight, signal_count)

        target_action_id = str(item.get("target_action_id") or "").strip()
        if target_action_id:
            action_bucket = action_signal_stats.setdefault(target_action_id, {})
            _accumulate_signal_bucket(action_bucket, signal_key, signal_weight, signal_count)

    return {
        "signal_count": len(normalized),
        "signal_stats": signal_stats,
        "family_signal_stats": family_signal_stats,
        "action_signal_stats": action_signal_stats,
    }


def summarize_semantic_feedback(
    items: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    normalized = list(items or [])
    now = datetime.now(UTC)
    signal_stats: dict[str, dict[str, Any]] = {}
    for item in normalized:
        recorded_at = str(item.get("recorded_at") or "")
        recency_weight = _feedback_recency_weight(recorded_at, now=now)
        action_id = str(item.get("action_id") or "").strip()
        for signal in _extract_semantic_signals(item):
            bucket = signal_stats.setdefault(
                signal,
                {
                    "count": 0,
                    "weight": 0.0,
                    "latest_action": action_id,
                    "latest_recorded_at": recorded_at,
                },
            )
            bucket["count"] += 1
            bucket["weight"] += recency_weight
            if not bucket.get("latest_action"):
                bucket["latest_action"] = action_id
            if not bucket.get("latest_recorded_at"):
                bucket["latest_recorded_at"] = recorded_at
    return {
        "signal_count": len(signal_stats),
        "signal_stats": signal_stats,
    }


def _feedback_recency_weight(recorded_at: str, *, now: datetime) -> float:
    age_seconds = _feedback_age_seconds(recorded_at, now=now)
    half_life_seconds = 6 * 60 * 60
    if age_seconds <= 0:
        return 1.0
    return max(0.05, math.exp(-math.log(2) * (age_seconds / half_life_seconds)))


def _feedback_age_seconds(recorded_at: str, *, now: datetime) -> float:
    timestamp = _parse_iso_datetime(recorded_at)
    if timestamp is None:
        return 0.0
    return max((now - timestamp).total_seconds(), 0.0)


def _parse_iso_datetime(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _outcome_looks_like_no_change(item: dict[str, Any]) -> bool:
    summary = str(item.get("result_summary") or "")
    result = item.get("result_json") or item.get("result") or {}
    payload = item.get("payload_json") or item.get("payload") or {}
    haystack = " ".join(
        str(part)
        for part in (
            summary,
            result,
            payload,
        )
    ).lower()
    return any(
        token in haystack
        for token in (
            "intet nyt",
            "nothing new",
            "no change",
            "no changes",
            "no new",
            "clean working tree",
            "upstream=in-sync",
            "in-sync",
        )
    )


def _extract_semantic_signals(item: dict[str, Any]) -> list[str]:
    result = item.get("result_json") or item.get("result") or {}
    details = result.get("details") if isinstance(result, dict) else {}
    side_effects = result.get("side_effects") if isinstance(result, dict) else []
    summary = str(item.get("result_summary") or "")
    haystack = " ".join(
        str(part)
        for part in (
            summary,
            result,
            details,
            side_effects,
        )
    ).lower()

    signals: list[str] = []
    side_effect_list = [str(effect or "").strip() for effect in list(side_effects or [])]
    if "runtime-task-created" in side_effect_list:
        signals.append("task_created")
    if "visible-work-note-persisted" in side_effect_list or "internal-work-note" in side_effect_list:
        signals.append("note_persisted")
    if "repo-context-inspected" in side_effect_list:
        signals.append("repo_context_inspected")
    if "workspace-capability-blocked" in side_effect_list:
        signals.append("repo_capability_blocked")
    if "visible-proposal" in side_effect_list or "initiative-promoted" in side_effect_list:
        signals.append("visible_proposal_made")
    if "repo-context-inspected" in side_effect_list and _outcome_looks_like_no_change(item):
        signals.append("repo_no_change")
    if "repo-context-inspected" in side_effect_list and any(
        token in haystack
        for token in (
            "modified",
            "untracked",
            "dirty",
            "ahead",
            "behind",
            "diverged",
            "anomaly",
            "changes=",
            " m ",
            " ?? ",
        )
    ):
        signals.append("repo_actionable_change")
    return list(dict.fromkeys(signals))


def _accumulate_signal_bucket(
    buckets: dict[str, dict[str, Any]],
    signal_key: str,
    signal_weight: float,
    signal_count: int,
) -> None:
    bucket = buckets.setdefault(
        signal_key,
        {
            "count": 0,
            "weight": 0.0,
        },
    )
    bucket["count"] += int(signal_count or 1)
    bucket["weight"] += float(signal_weight or 0.0)


def _domain_key(*, loop_id: str, canonical_key: str) -> str:
    raw = canonical_key.strip() or loop_id.strip()
    if not raw:
        return ""
    parts = raw.split(":")
    return parts[-1].strip()


def _signal_tokens(value: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]{3,}", value.lower())
        if token not in _STOP_TOKENS
    }
    return tokens


_STOP_TOKENS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "runtime",
    "executive",
    "note",
    "mode",
    "carrying",
    "before",
    "next",
    "step",
    "loop",
    "open",
}
