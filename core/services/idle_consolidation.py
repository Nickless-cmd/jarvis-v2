"""Bounded sleep / idle consolidation light.

Produces one small internal-only consolidation artifact from existing runtime
material when cadence is quiet enough. This is not workspace memory, not
identity, and not visible output.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record, list_private_brain_records

_CONSOLIDATION_COOLDOWN_MINUTES = 12
_CONSOLIDATION_VISIBLE_GRACE_MINUTES = 6
_ADJACENT_PRODUCER_GRACE_MINUTES = 1
_MIN_SOURCE_INPUTS = 2
_DUPLICATE_WINDOW = 8

_last_run_at: str = ""
_last_result: dict[str, object] | None = None


def run_idle_consolidation(
    *,
    trigger: str = "heartbeat-idle",
    last_visible_at: str = "",
) -> dict[str, object]:
    """Run one bounded idle consolidation pass."""
    global _last_run_at, _last_result

    now = datetime.now(UTC)
    now_iso = now.isoformat()

    if _last_run_at:
        last_run = _parse_dt(_last_run_at)
        if last_run and (now - last_run) < timedelta(minutes=_CONSOLIDATION_COOLDOWN_MINUTES):
            result = _blocked(
                reason="cooldown-active",
                cadence_state="cooling-down",
                trigger=trigger,
                now=now,
                reference=last_run,
            )
            _last_result = result
            return result

    if last_visible_at:
        visible_at = _parse_dt(last_visible_at)
        if visible_at and (now - visible_at) < timedelta(minutes=_CONSOLIDATION_VISIBLE_GRACE_MINUTES):
            result = _blocked(
                reason="visible-activity-too-recent",
                cadence_state="visible-grace",
                trigger=trigger,
                now=now,
                reference=visible_at,
            )
            _last_result = result
            return result

    adjacent_block = _adjacent_producer_block(now=now, trigger=trigger)
    if adjacent_block is not None:
        _last_result = adjacent_block
        return adjacent_block

    inputs = _load_runtime_inputs()
    plan = build_idle_consolidation_from_inputs(
        private_brain_context=inputs["private_brain_context"],
        witness_surface=inputs["witness_surface"],
        emergent_surface=inputs["emergent_surface"],
        embodied_state=inputs["embodied_state"],
        loop_runtime=inputs["loop_runtime"],
        inner_voice_state=inputs["inner_voice_state"],
        now=now,
    )

    if not plan["eligible"]:
        result = {
            "producer": "sleep_consolidation",
            "daemon_ran": True,
            "consolidation_created": False,
            "consolidation_state": str(plan["consolidation_state"] or "insufficient-grounding"),
            "cadence_state": "ran-insufficient-grounding",
            "reason": str(plan["reason"] or "insufficient-grounding"),
            "source_inputs": plan["source_inputs"],
            "output_kind": "private-brain-sleep-consolidation",
            "trigger": trigger,
            "record_id": "",
            "boundary": "not-memory-not-identity-not-action",
        }
        _last_run_at = now_iso
        _last_result = result
        event_bus.publish(
            "runtime.idle_consolidation_skipped",
            {
                "trigger": trigger,
                "reason": result["reason"],
                "consolidation_state": result["consolidation_state"],
                "source_inputs": result["source_inputs"],
            },
        )
        return result

    artifact = dict(plan["artifact"] or {})
    recent = [
        item
        for item in list_private_brain_records(limit=_DUPLICATE_WINDOW)
        if str(item.get("record_type") or "") == "sleep-consolidation"
    ]
    if _is_near_duplicate(str(artifact.get("summary") or ""), recent):
        result = {
            "producer": "sleep_consolidation",
            "daemon_ran": True,
            "consolidation_created": False,
            "consolidation_state": str(plan["consolidation_state"] or "duplicate"),
            "cadence_state": "ran-duplicate-suppressed",
            "reason": "near-duplicate-consolidation",
            "source_inputs": plan["source_inputs"],
            "output_kind": "private-brain-sleep-consolidation",
            "trigger": trigger,
            "record_id": "",
            "boundary": "not-memory-not-identity-not-action",
        }
        _last_run_at = now_iso
        _last_result = result
        event_bus.publish(
            "runtime.idle_consolidation_skipped",
            {
                "trigger": trigger,
                "reason": result["reason"],
                "consolidation_state": result["consolidation_state"],
                "source_inputs": result["source_inputs"],
            },
        )
        return result

    record = insert_private_brain_record(
        record_id=f"pb-sleep-{uuid4().hex[:12]}",
        record_type="sleep-consolidation",
        layer="private_brain",
        session_id="heartbeat",
        run_id="",
        focus=str(artifact.get("focus") or "")[:200],
        summary=str(artifact.get("summary") or "")[:400],
        detail=str(artifact.get("detail") or "")[:400],
        source_signals=str(artifact.get("source_signals") or ""),
        confidence=str(artifact.get("confidence") or "medium"),
        created_at=now_iso,
    )

    result = {
        "producer": "sleep_consolidation",
        "daemon_ran": True,
        "consolidation_created": True,
        "consolidation_state": str(plan["consolidation_state"] or "holding"),
        "cadence_state": "ran-produced",
        "reason": "consolidated",
        "source_inputs": plan["source_inputs"],
        "output_kind": "private-brain-sleep-consolidation",
        "trigger": trigger,
        "record_id": str(record.get("record_id") or ""),
        "record_summary": str(record.get("summary") or ""),
        "boundary": "not-memory-not-identity-not-action",
    }
    _last_run_at = now_iso
    _last_result = result

    event_bus.publish(
        "runtime.idle_consolidation_completed",
        {
            "trigger": trigger,
            "record_id": result["record_id"],
            "consolidation_state": result["consolidation_state"],
            "source_inputs": result["source_inputs"],
            "summary": result["record_summary"][:200],
            "output_kind": result["output_kind"],
        },
    )
    return result


def build_idle_consolidation_from_inputs(
    *,
    private_brain_context: dict[str, object] | None,
    witness_surface: dict[str, object] | None,
    emergent_surface: dict[str, object] | None,
    embodied_state: dict[str, object] | None,
    loop_runtime: dict[str, object] | None,
    inner_voice_state: dict[str, object] | None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Build a bounded consolidation plan from runtime truth inputs."""
    built_at = (now or datetime.now(UTC)).isoformat()
    source_inputs: list[dict[str, str]] = []

    brain = private_brain_context or {}
    witness = witness_surface or {}
    emergent = emergent_surface or {}
    embodied = embodied_state or {}
    loops = loop_runtime or {}
    voice = inner_voice_state or {}

    brain_summary = str(brain.get("continuity_summary") or "")
    brain_count = int(brain.get("record_count") or 0)
    if brain.get("active") and brain_count > 0:
        source_inputs.append({
            "source": "private-brain",
            "signal": brain_summary[:120],
        })

    witness_summary = str((witness.get("summary") or {}).get("current_signal") or "")
    if witness.get("active") and witness_summary and witness_summary != "No current witness signal":
        source_inputs.append({
            "source": "witness",
            "signal": witness_summary[:120],
        })

    emergent_summary = str((emergent.get("summary") or {}).get("current_signal") or "")
    if emergent.get("active") and emergent_summary and emergent_summary != "No active emergent inner signal":
        source_inputs.append({
            "source": "emergent",
            "signal": emergent_summary[:120],
        })

    voice_result = voice.get("last_result") or {}
    if voice_result.get("inner_voice_created"):
        source_inputs.append({
            "source": "inner-voice",
            "signal": str(voice_result.get("focus") or "inner voice note")[:120],
        })

    embodied_state_name = str(embodied.get("state") or "unknown")
    if embodied_state_name != "unknown":
        source_inputs.append({
            "source": "embodied-state",
            "signal": (
                f"{embodied_state_name}"
                f" / strain={embodied.get('strain_level') or 'unknown'}"
                f" / recovery={embodied.get('recovery_state') or 'steady'}"
            )[:120],
        })

    loop_summary = loops.get("summary") or {}
    loop_count = int(loop_summary.get("loop_count") or 0)
    if loop_count > 0:
        source_inputs.append({
            "source": "loop-runtime",
            "signal": (
                f"{loop_summary.get('current_loop') or 'loop'}"
                f" / status={loop_summary.get('current_status') or 'none'}"
            )[:120],
        })

    if len(source_inputs) < _MIN_SOURCE_INPUTS:
        return {
            "eligible": False,
            "reason": f"insufficient-inner-material:{len(source_inputs)}<{_MIN_SOURCE_INPUTS}",
            "consolidation_state": "insufficient-grounding",
            "source_inputs": source_inputs[:4],
            "artifact": None,
            "built_at": built_at,
        }

    consolidation_state = _classify_consolidation_state(
        witness_surface=witness,
        emergent_surface=emergent,
        embodied_state=embodied,
        loop_runtime=loops,
    )
    focus = _choose_focus(
        witness_summary=witness_summary,
        emergent_summary=emergent_summary,
        loop_summary=loop_summary,
        embodied_state=embodied_state_name,
    )
    summary = _build_summary(
        consolidation_state=consolidation_state,
        source_inputs=source_inputs,
        loop_summary=loop_summary,
        embodied_state=embodied,
    )
    detail = _build_detail(
        brain_summary=brain_summary,
        source_inputs=source_inputs,
        loop_summary=loop_summary,
        embodied_state=embodied,
    )

    artifact = {
        "kind": "private-brain-sleep-consolidation",
        "focus": focus,
        "summary": summary,
        "detail": detail,
        "confidence": "medium",
        "source_signals": ",".join(item["source"] for item in source_inputs[:5]),
        "boundary": "not-memory-not-identity-not-action",
        "visibility": "internal-only",
        "consolidation_state": consolidation_state,
        "built_at": built_at,
    }
    return {
        "eligible": True,
        "reason": "grounding-sufficient",
        "consolidation_state": consolidation_state,
        "source_inputs": source_inputs[:5],
        "artifact": artifact,
        "built_at": built_at,
    }


def build_idle_consolidation_surface() -> dict[str, object]:
    latest_artifact = _latest_sleep_consolidation_record()
    return {
        "active": bool(latest_artifact or _last_result),
        "authority": "authoritative",
        "visibility": "internal-only",
        "kind": "sleep-consolidation-light",
        "boundary": "not-memory-not-identity-not-action",
        "last_run_at": _last_run_at or None,
        "last_result": _last_result,
        "latest_artifact": latest_artifact,
        "cadence": {
            "cooldown_minutes": _CONSOLIDATION_COOLDOWN_MINUTES,
            "visible_grace_minutes": _CONSOLIDATION_VISIBLE_GRACE_MINUTES,
            "adjacent_producer_grace_minutes": _ADJACENT_PRODUCER_GRACE_MINUTES,
            "min_source_inputs": _MIN_SOURCE_INPUTS,
        },
        "summary": {
            "last_state": str(((_last_result or {}).get("consolidation_state")) or "idle"),
            "last_reason": str(((_last_result or {}).get("reason")) or "no-run-yet"),
            "last_output_kind": str(((_last_result or {}).get("output_kind")) or "private-brain-sleep-consolidation"),
            "source_input_count": len(((_last_result or {}).get("source_inputs")) or []),
            "latest_record_id": str((latest_artifact or {}).get("record_id") or ""),
            "latest_summary": str((latest_artifact or {}).get("summary") or "No idle consolidation artifact recorded yet."),
        },
        "source": "/mc/idle-consolidation",
        "built_at": datetime.now(UTC).isoformat(),
    }


def _load_runtime_inputs() -> dict[str, object]:
    from core.services.embodied_state import build_embodied_state_surface
    from core.services.emergent_signal_tracking import (
        build_runtime_emergent_signal_surface,
    )
    from core.services.emergent_signal_tracking import (
        get_emergent_signal_daemon_state,
    )
    from core.services.inner_voice_daemon import get_inner_voice_daemon_state
    from core.services.loop_runtime import build_loop_runtime_surface
    from core.services.session_distillation import build_private_brain_context
    from core.services.witness_signal_tracking import (
        build_runtime_witness_signal_surface,
    )

    return {
        "private_brain_context": build_private_brain_context(limit=5),
        "witness_surface": build_runtime_witness_signal_surface(limit=4),
        "emergent_surface": build_runtime_emergent_signal_surface(limit=4),
        "embodied_state": build_embodied_state_surface(),
        "loop_runtime": build_loop_runtime_surface(),
        "inner_voice_state": get_inner_voice_daemon_state(),
        "emergent_daemon_state": get_emergent_signal_daemon_state(),
    }


def _adjacent_producer_block(*, now: datetime, trigger: str) -> dict[str, object] | None:
    from core.services.emergent_signal_tracking import (
        get_emergent_signal_daemon_state,
    )
    from core.services.inner_voice_daemon import get_inner_voice_daemon_state
    from core.services.witness_signal_tracking import get_witness_daemon_state

    recent_producers = [
        ("witness_daemon", get_witness_daemon_state()),
        ("inner_voice_daemon", get_inner_voice_daemon_state()),
        ("emergent_signal_daemon", get_emergent_signal_daemon_state()),
    ]
    for name, state in recent_producers:
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


def _latest_sleep_consolidation_record() -> dict[str, object] | None:
    for item in list_private_brain_records(limit=12):
        if str(item.get("record_type") or "") == "sleep-consolidation":
            return item
    return None


def _classify_consolidation_state(
    *,
    witness_surface: dict[str, object],
    emergent_surface: dict[str, object],
    embodied_state: dict[str, object],
    loop_runtime: dict[str, object],
) -> str:
    loop_summary = loop_runtime.get("summary") or {}
    current_status = str(loop_summary.get("current_status") or "none")
    strain = str(embodied_state.get("strain_level") or "unknown")
    recovery = str(embodied_state.get("recovery_state") or "steady")

    if current_status in {"active", "resumed"} or strain in {"loaded", "strained", "degraded"}:
        return "holding"
    if witness_surface.get("active") or emergent_surface.get("active") or recovery == "recovering":
        return "settling"
    return "released-lite"


def _choose_focus(
    *,
    witness_summary: str,
    emergent_summary: str,
    loop_summary: dict[str, object],
    embodied_state: str,
) -> str:
    if loop_summary.get("current_loop"):
        return str(loop_summary.get("current_loop") or "")[:120]
    if witness_summary:
        return witness_summary[:120]
    if emergent_summary:
        return emergent_summary[:120]
    return f"idle consolidation around {embodied_state or 'runtime'}"


def _build_summary(
    *,
    consolidation_state: str,
    source_inputs: list[dict[str, str]],
    loop_summary: dict[str, object],
    embodied_state: dict[str, object],
) -> str:
    sources = ", ".join(item["source"] for item in source_inputs[:4])
    return (
        f"Idle consolidation settled bounded internal material into a {consolidation_state} carry "
        f"using {sources}. "
        f"Loop={loop_summary.get('current_status') or 'none'}; "
        f"body={embodied_state.get('state') or 'unknown'}."
    )


def _build_detail(
    *,
    brain_summary: str,
    source_inputs: list[dict[str, str]],
    loop_summary: dict[str, object],
    embodied_state: dict[str, object],
) -> str:
    source_lines = "; ".join(
        f"{item['source']}={item['signal']}"
        for item in source_inputs[:4]
    )
    return (
        f"{brain_summary[:140]} | "
        f"{source_lines[:180]} | "
        f"loop_kind={loop_summary.get('current_kind') or 'none'} | "
        f"loop_reason={loop_summary.get('current_reason') or 'none'} | "
        f"recovery={embodied_state.get('recovery_state') or 'steady'}"
    )


def _is_near_duplicate(summary: str, recent_records: list[dict[str, object]]) -> bool:
    normalized = " ".join(summary.lower().split())
    if not normalized:
        return False
    words = set(normalized.split())
    for record in recent_records:
        existing = " ".join(str(record.get("summary") or "").lower().split())
        existing_words = set(existing.split())
        if not existing_words:
            continue
        union = words | existing_words
        if union and (len(words & existing_words) / len(union)) > 0.72:
            return True
    return False


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
        "producer": "sleep_consolidation",
        "daemon_ran": False,
        "consolidation_created": False,
        "consolidation_state": "blocked",
        "cadence_state": cadence_state,
        "reason": reason,
        "elapsed_minutes": round(elapsed, 2),
        "trigger": trigger,
        "output_kind": "private-brain-sleep-consolidation",
        "source_inputs": [],
        "record_id": "",
        "boundary": "not-memory-not-identity-not-action",
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
