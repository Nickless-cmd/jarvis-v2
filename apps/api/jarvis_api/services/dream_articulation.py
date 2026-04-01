"""Bounded dream articulation light.

Articulates one small internal-only, candidate-only dream hypothesis from
existing runtime material. This is not memory, not identity, and not action.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import list_runtime_dream_hypothesis_signals, upsert_runtime_dream_hypothesis_signal

_DREAM_COOLDOWN_MINUTES = 35
_DREAM_VISIBLE_GRACE_MINUTES = 14
_ADJACENT_PRODUCER_GRACE_MINUTES = 5
_MIN_SOURCE_INPUTS = 3

_last_run_at: str = ""
_last_result: dict[str, object] | None = None


def run_dream_articulation(
    *,
    trigger: str = "heartbeat-idle",
    last_visible_at: str = "",
) -> dict[str, object]:
    """Run one bounded dream-articulation pass."""
    global _last_run_at, _last_result

    now = datetime.now(UTC)
    now_iso = now.isoformat()

    if _last_run_at:
        previous = _parse_dt(_last_run_at)
        if previous and (now - previous) < timedelta(minutes=_DREAM_COOLDOWN_MINUTES):
            result = _blocked(
                reason="cooldown-active",
                cadence_state="cooling-down",
                trigger=trigger,
                now=now,
                reference=previous,
            )
            _last_result = result
            return result

    if last_visible_at:
        visible = _parse_dt(last_visible_at)
        if visible and (now - visible) < timedelta(minutes=_DREAM_VISIBLE_GRACE_MINUTES):
            result = _blocked(
                reason="visible-activity-too-recent",
                cadence_state="visible-grace",
                trigger=trigger,
                now=now,
                reference=visible,
            )
            _last_result = result
            return result

    adjacent = _adjacent_producer_block(now=now, trigger=trigger)
    if adjacent is not None:
        _last_result = adjacent
        return adjacent

    inputs = _load_runtime_inputs()
    plan = build_dream_articulation_from_inputs(
        idle_consolidation=inputs["idle_consolidation"],
        inner_voice_state=inputs["inner_voice_state"],
        emergent_surface=inputs["emergent_surface"],
        witness_surface=inputs["witness_surface"],
        loop_runtime=inputs["loop_runtime"],
        embodied_state=inputs["embodied_state"],
        now=now,
    )

    if not plan["eligible"]:
        result = {
            "producer": "dream_articulation",
            "daemon_ran": True,
            "candidate_created": False,
            "candidate_state": str(plan["candidate_state"] or "insufficient-grounding"),
            "cadence_state": "ran-insufficient-grounding",
            "reason": str(plan["reason"] or "insufficient-grounding"),
            "source_inputs": plan["source_inputs"],
            "output_kind": "runtime-dream-hypothesis",
            "candidate_visibility": "internal-only",
            "candidate_truth": "candidate-only",
            "boundary": "not-memory-not-identity-not-action",
            "trigger": trigger,
            "signal_id": "",
        }
        _last_run_at = now_iso
        _last_result = result
        event_bus.publish(
            "runtime.dream_articulation_skipped",
            {
                "trigger": trigger,
                "reason": result["reason"],
                "candidate_state": result["candidate_state"],
                "source_inputs": result["source_inputs"],
            },
        )
        return result

    artifact = dict(plan["artifact"] or {})
    persisted = upsert_runtime_dream_hypothesis_signal(
        signal_id=f"dream-articulation-{uuid4().hex}",
        signal_type=str(artifact.get("signal_type") or "articulated-dream-fragment"),
        canonical_key=str(artifact.get("canonical_key") or ""),
        status="active",
        title=str(artifact.get("title") or ""),
        summary=str(artifact.get("summary") or ""),
        rationale=str(artifact.get("rationale") or ""),
        source_kind="internal-dream-articulation",
        confidence=str(artifact.get("confidence") or "low"),
        evidence_summary=str(artifact.get("evidence_summary") or ""),
        support_summary=str(artifact.get("support_summary") or ""),
        support_count=int(artifact.get("support_count") or 1),
        session_count=1,
        created_at=now_iso,
        updated_at=now_iso,
        status_reason=str(artifact.get("status_reason") or ""),
        run_id="",
        session_id="",
    )

    result = {
        "producer": "dream_articulation",
        "daemon_ran": True,
        "candidate_created": True,
        "candidate_state": str(plan["candidate_state"] or "articulated"),
        "cadence_state": "ran-produced",
        "reason": "dream-articulated",
        "source_inputs": plan["source_inputs"],
        "output_kind": "runtime-dream-hypothesis",
        "candidate_visibility": "internal-only",
        "candidate_truth": "candidate-only",
        "boundary": "not-memory-not-identity-not-action",
        "trigger": trigger,
        "signal_id": str(persisted.get("signal_id") or ""),
        "signal_summary": str(persisted.get("summary") or ""),
        "signal_type": str(persisted.get("signal_type") or ""),
    }
    _last_run_at = now_iso
    _last_result = result

    event_bus.publish(
        "runtime.dream_articulation_completed",
        {
            "trigger": trigger,
            "signal_id": result["signal_id"],
            "signal_type": result["signal_type"],
            "candidate_state": result["candidate_state"],
            "source_inputs": result["source_inputs"],
            "summary": result["signal_summary"][:200],
            "candidate_truth": "candidate-only",
        },
    )
    return result


def build_dream_articulation_from_inputs(
    *,
    idle_consolidation: dict[str, object] | None,
    inner_voice_state: dict[str, object] | None,
    emergent_surface: dict[str, object] | None,
    witness_surface: dict[str, object] | None,
    loop_runtime: dict[str, object] | None,
    embodied_state: dict[str, object] | None,
    now: datetime | None = None,
) -> dict[str, object]:
    built_at = (now or datetime.now(UTC)).isoformat()
    source_inputs: list[dict[str, str]] = []

    consolidation = idle_consolidation or {}
    consolidation_summary = consolidation.get("summary") or {}
    consolidation_artifact = consolidation.get("latest_artifact") or {}
    if consolidation_summary.get("latest_summary") or consolidation_artifact.get("summary"):
        source_inputs.append({
            "source": "idle-consolidation",
            "signal": str(
                consolidation_artifact.get("summary")
                or consolidation_summary.get("latest_summary")
                or ""
            )[:120],
        })

    voice = inner_voice_state or {}
    voice_result = voice.get("last_result") or {}
    if voice_result.get("inner_voice_created"):
        source_inputs.append({
            "source": "inner-voice",
            "signal": str(voice_result.get("focus") or "inner voice note")[:120],
        })

    emergent = emergent_surface or {}
    emergent_summary = str((emergent.get("summary") or {}).get("current_signal") or "")
    if emergent.get("active") and emergent_summary and emergent_summary != "No active emergent inner signal":
        source_inputs.append({
            "source": "emergent",
            "signal": emergent_summary[:120],
        })

    witness = witness_surface or {}
    witness_summary = str((witness.get("summary") or {}).get("current_signal") or "")
    if witness.get("active") and witness_summary and witness_summary != "No current witness signal":
        source_inputs.append({
            "source": "witness",
            "signal": witness_summary[:120],
        })

    loops = loop_runtime or {}
    loop_summary = loops.get("summary") or {}
    if int(loop_summary.get("loop_count") or 0) > 0:
        source_inputs.append({
            "source": "loop-runtime",
            "signal": (
                f"{loop_summary.get('current_loop') or 'loop'}"
                f" / {loop_summary.get('current_status') or 'none'}"
            )[:120],
        })

    body = embodied_state or {}
    body_state = str(body.get("state") or "unknown")
    if body_state != "unknown":
        source_inputs.append({
            "source": "embodied-state",
            "signal": (
                f"{body_state}"
                f" / strain={body.get('strain_level') or 'unknown'}"
                f" / recovery={body.get('recovery_state') or 'steady'}"
            )[:120],
        })

    if len(source_inputs) < _MIN_SOURCE_INPUTS:
        return {
            "eligible": False,
            "reason": f"insufficient-inner-material:{len(source_inputs)}<{_MIN_SOURCE_INPUTS}",
            "candidate_state": "insufficient-grounding",
            "source_inputs": source_inputs[:5],
            "artifact": None,
            "built_at": built_at,
        }

    candidate_state = _classify_candidate_state(
        idle_consolidation=consolidation,
        emergent_surface=emergent,
        witness_surface=witness,
        loop_runtime=loops,
    )
    anchor = _build_anchor(
        idle_consolidation=consolidation,
        witness_summary=witness_summary,
        emergent_summary=emergent_summary,
        loop_summary=loop_summary,
    )
    signal_type = _build_signal_type(candidate_state=candidate_state, loop_summary=loop_summary)
    title = f"Dream articulation: {_title_suffix(anchor)}"
    summary = _build_summary(
        candidate_state=candidate_state,
        source_inputs=source_inputs,
        body=body,
    )
    rationale = _build_rationale(
        consolidation=consolidation,
        voice_result=voice_result,
        witness_summary=witness_summary,
        emergent_summary=emergent_summary,
    )
    support_summary = _build_support_summary(
        source_inputs=source_inputs,
        candidate_state=candidate_state,
    )

    artifact = {
        "signal_type": signal_type,
        "canonical_key": f"dream-articulation:{signal_type}:{anchor}",
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "confidence": "low" if candidate_state == "tentative" else "medium",
        "evidence_summary": rationale[:200],
        "support_summary": support_summary,
        "support_count": len(source_inputs[:5]),
        "status_reason": (
            "Bounded dream articulation from internal runtime material; candidate-only, internal-only, not action."
        ),
        "built_at": built_at,
        "candidate_state": candidate_state,
    }
    return {
        "eligible": True,
        "reason": "grounding-sufficient",
        "candidate_state": candidate_state,
        "source_inputs": source_inputs[:5],
        "artifact": artifact,
        "built_at": built_at,
    }


def build_dream_articulation_surface() -> dict[str, object]:
    latest = _latest_dream_articulation_signal()
    return {
        "active": bool(latest or _last_result),
        "authority": "authoritative-runtime-observability",
        "visibility": "internal-only",
        "truth": "candidate-only",
        "kind": "dream-articulation-light",
        "boundary": "not-memory-not-identity-not-action",
        "last_run_at": _last_run_at or None,
        "last_result": _last_result,
        "latest_artifact": latest,
        "cadence": {
            "cooldown_minutes": _DREAM_COOLDOWN_MINUTES,
            "visible_grace_minutes": _DREAM_VISIBLE_GRACE_MINUTES,
            "adjacent_producer_grace_minutes": _ADJACENT_PRODUCER_GRACE_MINUTES,
            "min_source_inputs": _MIN_SOURCE_INPUTS,
        },
        "summary": {
            "last_state": str(((_last_result or {}).get("candidate_state")) or "idle"),
            "last_reason": str(((_last_result or {}).get("reason")) or "no-run-yet"),
            "last_output_kind": str(((_last_result or {}).get("output_kind")) or "runtime-dream-hypothesis"),
            "source_input_count": len(((_last_result or {}).get("source_inputs")) or []),
            "latest_signal_id": str((latest or {}).get("signal_id") or ""),
            "latest_summary": str((latest or {}).get("summary") or "No dream articulation candidate recorded yet."),
            "candidate_truth": "candidate-only",
        },
        "source": "/mc/dream-articulation",
        "built_at": datetime.now(UTC).isoformat(),
    }


def _load_runtime_inputs() -> dict[str, object]:
    from apps.api.jarvis_api.services.embodied_state import build_embodied_state_surface
    from apps.api.jarvis_api.services.emergent_signal_tracking import (
        build_runtime_emergent_signal_surface,
    )
    from apps.api.jarvis_api.services.idle_consolidation import build_idle_consolidation_surface
    from apps.api.jarvis_api.services.inner_voice_daemon import get_inner_voice_daemon_state
    from apps.api.jarvis_api.services.loop_runtime import build_loop_runtime_surface
    from apps.api.jarvis_api.services.witness_signal_tracking import (
        build_runtime_witness_signal_surface,
    )

    return {
        "idle_consolidation": build_idle_consolidation_surface(),
        "inner_voice_state": get_inner_voice_daemon_state(),
        "emergent_surface": build_runtime_emergent_signal_surface(limit=4),
        "witness_surface": build_runtime_witness_signal_surface(limit=4),
        "loop_runtime": build_loop_runtime_surface(),
        "embodied_state": build_embodied_state_surface(),
    }


def _adjacent_producer_block(*, now: datetime, trigger: str) -> dict[str, object] | None:
    from apps.api.jarvis_api.services.emergent_signal_tracking import get_emergent_signal_daemon_state
    from apps.api.jarvis_api.services.idle_consolidation import build_idle_consolidation_surface
    from apps.api.jarvis_api.services.inner_voice_daemon import get_inner_voice_daemon_state
    from apps.api.jarvis_api.services.witness_signal_tracking import get_witness_daemon_state

    idle_surface = build_idle_consolidation_surface()
    recent = [
        ("sleep_consolidation", {"last_run_at": idle_surface.get("last_run_at")}),
        ("witness_daemon", get_witness_daemon_state()),
        ("inner_voice_daemon", get_inner_voice_daemon_state()),
        ("emergent_signal_daemon", get_emergent_signal_daemon_state()),
    ]
    for name, state in recent:
        last_run = _parse_dt(state.get("last_run_at"))
        if last_run and (now - last_run) < timedelta(minutes=_ADJACENT_PRODUCER_GRACE_MINUTES):
            return _blocked(
                reason=f"adjacent-producer-too-recent:{name}",
                cadence_state="adjacent-producer-grace",
                trigger=trigger,
                now=now,
                reference=last_run,
            )
    return None


def _latest_dream_articulation_signal() -> dict[str, object] | None:
    for item in list_runtime_dream_hypothesis_signals(limit=20):
        if str(item.get("source_kind") or "") == "internal-dream-articulation":
            return item
    return None


def _classify_candidate_state(
    *,
    idle_consolidation: dict[str, object],
    emergent_surface: dict[str, object],
    witness_surface: dict[str, object],
    loop_runtime: dict[str, object],
) -> str:
    loop_summary = loop_runtime.get("summary") or {}
    loop_status = str(loop_summary.get("current_status") or "none")
    last_state = str((idle_consolidation.get("summary") or {}).get("last_state") or "idle")
    if loop_status in {"resumed", "active"} and emergent_surface.get("active"):
        return "pressing"
    if last_state in {"holding", "settling"} or witness_surface.get("active"):
        return "forming"
    return "tentative"


def _build_anchor(
    *,
    idle_consolidation: dict[str, object],
    witness_summary: str,
    emergent_summary: str,
    loop_summary: dict[str, object],
) -> str:
    raw = (
        str(loop_summary.get("current_loop") or "")
        or witness_summary
        or emergent_summary
        or str((idle_consolidation.get("summary") or {}).get("latest_summary") or "")
        or "dream-fragment"
    )
    normalized = "-".join(raw.lower().split())
    cleaned = "".join(ch for ch in normalized if ch.isalnum() or ch == "-").strip("-")
    return cleaned[:72] or "dream-fragment"


def _build_signal_type(*, candidate_state: str, loop_summary: dict[str, object]) -> str:
    current_kind = str(loop_summary.get("current_kind") or "runtime-thread")
    return f"dream-{candidate_state}-{current_kind}".replace("_", "-")


def _title_suffix(anchor: str) -> str:
    return anchor.replace("-", " ").strip().title() or "Dream Fragment"


def _build_summary(
    *,
    candidate_state: str,
    source_inputs: list[dict[str, str]],
    body: dict[str, object],
) -> str:
    sources = ", ".join(item["source"] for item in source_inputs[:4])
    return (
        f"A bounded dream fragment is {candidate_state} from {sources}. "
        f"It stays candidate-only and internal while body-state={body.get('state') or 'unknown'}."
    )


def _build_rationale(
    *,
    consolidation: dict[str, object],
    voice_result: dict[str, object],
    witness_summary: str,
    emergent_summary: str,
) -> str:
    parts = [
        str(((consolidation.get("summary") or {}).get("latest_summary")) or ""),
        str(voice_result.get("focus") or ""),
        witness_summary,
        emergent_summary,
    ]
    merged = " | ".join(part for part in parts if part)
    return (
        merged[:320]
        or "Existing internal runtime material briefly cohered into a bounded dream-like articulation."
    )


def _build_support_summary(
    *,
    source_inputs: list[dict[str, str]],
    candidate_state: str,
) -> str:
    labels = ", ".join(item["source"] for item in source_inputs[:5])
    return (
        f"Derived only from bounded internal runtime material ({labels}). "
        f"candidate-state={candidate_state} | candidate-only | internal-only | not-memory | not-identity | not-action"
    )


def _blocked(
    *,
    reason: str,
    cadence_state: str,
    trigger: str,
    now: datetime,
    reference: datetime,
) -> dict[str, object]:
    elapsed = max((now - reference).total_seconds() / 60.0, 0.0)
    return {
        "producer": "dream_articulation",
        "daemon_ran": False,
        "candidate_created": False,
        "candidate_state": "blocked",
        "cadence_state": cadence_state,
        "reason": reason,
        "elapsed_minutes": round(elapsed, 2),
        "trigger": trigger,
        "output_kind": "runtime-dream-hypothesis",
        "candidate_visibility": "internal-only",
        "candidate_truth": "candidate-only",
        "boundary": "not-memory-not-identity-not-action",
        "source_inputs": [],
        "signal_id": "",
    }


def _parse_dt(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
