"""Bounded runtime prompt evolution / self-authored prompt proposals light.

Produces one small internal-only, proposal-only prompt proposal from existing
runtime material. This does not apply prompts, write workspace assets, or
mutate identity.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_self_authored_prompt_proposals,
    upsert_runtime_self_authored_prompt_proposal,
)

_PROMPT_EVOLUTION_COOLDOWN_MINUTES = 45
_PROMPT_EVOLUTION_VISIBLE_GRACE_MINUTES = 16
_ADJACENT_PRODUCER_GRACE_MINUTES = 6
_MIN_SOURCE_INPUTS = 3
_SOURCE_KIND = "internal-runtime-prompt-evolution"

_last_run_at: str = ""
_last_result: dict[str, object] | None = None


def run_prompt_evolution_runtime(
    *,
    trigger: str = "heartbeat-idle",
    last_visible_at: str = "",
) -> dict[str, object]:
    """Run one bounded prompt-evolution proposal pass."""
    global _last_run_at, _last_result

    now = datetime.now(UTC)
    now_iso = now.isoformat()

    if _last_run_at:
        previous = _parse_dt(_last_run_at)
        if previous and (now - previous) < timedelta(minutes=_PROMPT_EVOLUTION_COOLDOWN_MINUTES):
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
        if visible and (now - visible) < timedelta(minutes=_PROMPT_EVOLUTION_VISIBLE_GRACE_MINUTES):
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
    plan = build_prompt_evolution_from_inputs(
        dream_articulation=inputs["dream_articulation"],
        self_model_surface=inputs["self_model_surface"],
        inner_voice_state=inputs["inner_voice_state"],
        emergent_surface=inputs["emergent_surface"],
        embodied_state=inputs["embodied_state"],
        loop_runtime=inputs["loop_runtime"],
        now=now,
    )

    if not plan["eligible"]:
        result = {
            "producer": "prompt_evolution_runtime",
            "daemon_ran": True,
            "proposal_created": False,
            "proposal_state": str(plan["proposal_state"] or "insufficient-grounding"),
            "cadence_state": "ran-insufficient-grounding",
            "reason": str(plan["reason"] or "insufficient-grounding"),
            "source_inputs": plan["source_inputs"],
            "output_kind": "self-authored-prompt-proposal",
            "trigger": trigger,
            "proposal_id": "",
            "proposal_type": "",
            "target_asset": "",
            "proposal_visibility": "internal-only",
            "proposal_truth": "proposal-only",
            "boundary": "not-memory-not-identity-not-action-not-applied-prompt",
        }
        _last_run_at = now_iso
        _last_result = result
        event_bus.publish(
            "runtime.prompt_evolution_skipped",
            {
                "trigger": trigger,
                "reason": result["reason"],
                "proposal_state": result["proposal_state"],
                "source_inputs": result["source_inputs"],
            },
        )
        return result

    artifact = dict(plan["artifact"] or {})
    persisted = upsert_runtime_self_authored_prompt_proposal(
        proposal_id=f"runtime-prompt-evolution-{uuid4().hex}",
        proposal_type=str(artifact.get("proposal_type") or "focus-nudge"),
        canonical_key=str(artifact.get("canonical_key") or ""),
        status="fresh",
        title=str(artifact.get("title") or ""),
        summary=str(artifact.get("summary") or ""),
        rationale=str(artifact.get("rationale") or ""),
        source_kind=_SOURCE_KIND,
        confidence=str(artifact.get("confidence") or "medium"),
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
        "producer": "prompt_evolution_runtime",
        "daemon_ran": True,
        "proposal_created": True,
        "proposal_state": str(plan["proposal_state"] or "candidate"),
        "cadence_state": "ran-produced",
        "reason": "prompt-proposal-articulated",
        "source_inputs": plan["source_inputs"],
        "output_kind": "self-authored-prompt-proposal",
        "trigger": trigger,
        "proposal_id": str(persisted.get("proposal_id") or ""),
        "proposal_type": str(persisted.get("proposal_type") or ""),
        "proposal_summary": str(persisted.get("summary") or ""),
        "target_asset": str(artifact.get("target_asset") or ""),
        "proposal_visibility": "internal-only",
        "proposal_truth": "proposal-only",
        "boundary": "not-memory-not-identity-not-action-not-applied-prompt",
    }
    _last_run_at = now_iso
    _last_result = result

    event_bus.publish(
        "runtime.prompt_evolution_completed",
        {
            "trigger": trigger,
            "proposal_id": result["proposal_id"],
            "proposal_type": result["proposal_type"],
            "target_asset": result["target_asset"],
            "summary": result["proposal_summary"][:200],
            "proposal_truth": "proposal-only",
            "source_inputs": result["source_inputs"],
        },
    )
    return result


def build_prompt_evolution_from_inputs(
    *,
    dream_articulation: dict[str, object] | None,
    self_model_surface: dict[str, object] | None,
    inner_voice_state: dict[str, object] | None,
    emergent_surface: dict[str, object] | None,
    embodied_state: dict[str, object] | None,
    loop_runtime: dict[str, object] | None,
    now: datetime | None = None,
) -> dict[str, object]:
    built_at = (now or datetime.now(UTC)).isoformat()
    source_inputs: list[dict[str, str]] = []

    dream = dream_articulation or {}
    dream_summary = dream.get("summary") or {}
    dream_artifact = dream.get("latest_artifact") or {}
    if dream_summary.get("latest_summary") or dream_artifact.get("summary"):
        source_inputs.append({
            "source": "dream-articulation",
            "signal": str(
                dream_artifact.get("summary")
                or dream_summary.get("latest_summary")
                or ""
            )[:120],
        })

    self_model = self_model_surface or {}
    self_model_summary = self_model.get("summary") or {}
    self_model_items = self_model.get("items") or []
    if self_model_items or int(self_model_summary.get("active_count") or 0) > 0:
        source_inputs.append({
            "source": "self-model",
            "signal": str(self_model_summary.get("current_signal") or "runtime self-model signal")[:120],
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

    if len(source_inputs) < _MIN_SOURCE_INPUTS:
        return {
            "eligible": False,
            "reason": f"insufficient-grounding:{len(source_inputs)}<{_MIN_SOURCE_INPUTS}",
            "proposal_state": "insufficient-grounding",
            "source_inputs": source_inputs[:5],
            "artifact": None,
            "built_at": built_at,
        }

    proposal_type = _choose_proposal_type(
        dream_articulation=dream,
        self_model_surface=self_model,
        embodied_state=body,
        loop_runtime=loops,
    )
    target_asset = _target_asset_from_proposal_type(proposal_type)
    prompt_target = _prompt_target_from_proposal_type(proposal_type)
    anchor = _build_anchor(
        dream_articulation=dream,
        self_model_surface=self_model,
        loop_runtime=loops,
    )
    rationale = _build_rationale(proposal_type=proposal_type, target_asset=target_asset)
    proposal_state = _proposal_state_from_type(proposal_type)
    artifact = {
        "proposal_type": proposal_type,
        "canonical_key": f"runtime-prompt-evolution:{proposal_type}:{anchor}",
        "title": f"Runtime prompt evolution: {target_asset}",
        "summary": (
            f"Bounded {proposal_type} proposal for {target_asset}. "
            f"Prompt target={prompt_target}. Proposal-only; not applied."
        ),
        "rationale": rationale,
        "confidence": _confidence_from_inputs(
            proposal_type=proposal_type,
            source_input_count=len(source_inputs),
            self_model_surface=self_model,
        ),
        "evidence_summary": " | ".join(item["signal"] for item in source_inputs[:3]),
        "support_summary": " | ".join(
            [
                f"target_asset={target_asset}",
                f"prompt_target={prompt_target}",
                f"proposal_state={proposal_state}",
                f"source_inputs={len(source_inputs)}",
            ]
        ),
        "support_count": len(source_inputs),
        "status_reason": "A bounded runtime pattern now warrants a proposal-only prompt evolution candidate.",
        "target_asset": target_asset,
        "prompt_target": prompt_target,
    }

    return {
        "eligible": True,
        "reason": "grounded-runtime-prompt-proposal",
        "proposal_state": proposal_state,
        "source_inputs": source_inputs[:6],
        "artifact": artifact,
        "built_at": built_at,
    }


def build_prompt_evolution_runtime_surface() -> dict[str, object]:
    latest = _latest_prompt_evolution_proposal()
    latest_type = str((latest or {}).get("proposal_type") or "")
    target_asset = _target_asset_from_proposal_type(latest_type) if latest else ""
    prompt_target = _prompt_target_from_proposal_type(latest_type) if latest else ""
    return {
        "active": bool(latest or _last_result),
        "authority": "authoritative-runtime-observability",
        "visibility": "internal-only",
        "truth": "candidate-only",
        "proposal_mode": "proposal-only",
        "kind": "runtime-prompt-evolution-light",
        "boundary": "not-memory-not-identity-not-action-not-applied-prompt",
        "last_run_at": _last_run_at or None,
        "last_result": _last_result,
        "latest_proposal": latest,
        "cadence": {
            "cooldown_minutes": _PROMPT_EVOLUTION_COOLDOWN_MINUTES,
            "visible_grace_minutes": _PROMPT_EVOLUTION_VISIBLE_GRACE_MINUTES,
            "adjacent_producer_grace_minutes": _ADJACENT_PRODUCER_GRACE_MINUTES,
            "min_source_inputs": _MIN_SOURCE_INPUTS,
        },
        "summary": {
            "last_state": str(((_last_result or {}).get("proposal_state")) or "idle"),
            "last_reason": str(((_last_result or {}).get("reason")) or "no-run-yet"),
            "last_output_kind": str(((_last_result or {}).get("output_kind")) or "self-authored-prompt-proposal"),
            "source_input_count": len(((_last_result or {}).get("source_inputs")) or []),
            "latest_proposal_id": str((latest or {}).get("proposal_id") or ""),
            "latest_summary": str((latest or {}).get("summary") or "No runtime prompt proposal recorded yet."),
            "latest_target_asset": target_asset or "none",
            "latest_prompt_target": prompt_target or "none",
            "proposal_truth": "proposal-only",
        },
        "source": "/mc/prompt-evolution",
        "built_at": datetime.now(UTC).isoformat(),
    }


def _load_runtime_inputs() -> dict[str, object]:
    from apps.api.jarvis_api.services.dream_articulation import build_dream_articulation_surface
    from apps.api.jarvis_api.services.embodied_state import build_embodied_state_surface
    from apps.api.jarvis_api.services.emergent_signal_tracking import (
        build_runtime_emergent_signal_surface,
    )
    from apps.api.jarvis_api.services.inner_voice_daemon import get_inner_voice_daemon_state
    from apps.api.jarvis_api.services.loop_runtime import build_loop_runtime_surface
    from apps.api.jarvis_api.services.self_model_signal_tracking import (
        build_runtime_self_model_signal_surface,
    )

    return {
        "dream_articulation": build_dream_articulation_surface(),
        "self_model_surface": build_runtime_self_model_signal_surface(limit=4),
        "inner_voice_state": get_inner_voice_daemon_state(),
        "emergent_surface": build_runtime_emergent_signal_surface(limit=4),
        "embodied_state": build_embodied_state_surface(),
        "loop_runtime": build_loop_runtime_surface(),
    }


def _adjacent_producer_block(*, now: datetime, trigger: str) -> dict[str, object] | None:
    from apps.api.jarvis_api.services.dream_articulation import build_dream_articulation_surface
    from apps.api.jarvis_api.services.emergent_signal_tracking import get_emergent_signal_daemon_state
    from apps.api.jarvis_api.services.inner_voice_daemon import get_inner_voice_daemon_state

    dream_surface = build_dream_articulation_surface()
    recent = [
        ("dream_articulation", {"last_run_at": dream_surface.get("last_run_at")}),
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


def _latest_prompt_evolution_proposal() -> dict[str, object] | None:
    for item in list_runtime_self_authored_prompt_proposals(limit=20):
        if str(item.get("source_kind") or "") == _SOURCE_KIND:
            return item
    return None


def _choose_proposal_type(
    *,
    dream_articulation: dict[str, object],
    self_model_surface: dict[str, object],
    embodied_state: dict[str, object],
    loop_runtime: dict[str, object],
) -> str:
    latest_dream = dream_articulation.get("latest_artifact") or {}
    latest_dream_type = str(latest_dream.get("signal_type") or "").lower()
    if "tension" in latest_dream_type or str(embodied_state.get("state") or "") in {"strained", "degraded"}:
        return "world-caution-nudge"

    loop_summary = loop_runtime.get("summary") or {}
    if str(loop_summary.get("current_status") or "") in {"active", "resumed"}:
        return "focus-nudge"

    self_model_summary = self_model_surface.get("summary") or {}
    if int(self_model_summary.get("uncertain_count") or 0) > 0:
        return "communication-nudge"

    return "challenge-nudge"


def _target_asset_from_proposal_type(proposal_type: str) -> str:
    mapping = {
        "communication-nudge": "INNER_VOICE.md",
        "focus-nudge": "HEARTBEAT.md",
        "challenge-nudge": "INNER_VOICE.md",
        "world-caution-nudge": "HEARTBEAT.md",
    }
    return mapping.get(proposal_type, "HEARTBEAT.md")


def _prompt_target_from_proposal_type(proposal_type: str) -> str:
    mapping = {
        "communication-nudge": "communication-style",
        "focus-nudge": "direction-framing",
        "challenge-nudge": "challenge-posture",
        "world-caution-nudge": "world-caution",
    }
    return mapping.get(proposal_type, "direction-framing")


def _build_anchor(
    *,
    dream_articulation: dict[str, object],
    self_model_surface: dict[str, object],
    loop_runtime: dict[str, object],
) -> str:
    latest = dream_articulation.get("latest_artifact") or {}
    canonical_key = str(latest.get("canonical_key") or "")
    if canonical_key:
        parts = canonical_key.split(":")
        if len(parts) >= 3 and parts[-1]:
            return parts[-1]

    loop_summary = loop_runtime.get("summary") or {}
    current_loop = str(loop_summary.get("current_loop") or "").strip()
    if current_loop:
        normalized = "-".join(current_loop.lower().split())
        cleaned = "".join(ch for ch in normalized if ch.isalnum() or ch == "-").strip("-")
        if cleaned:
            return cleaned

    current_signal = str((self_model_surface.get("summary") or {}).get("current_signal") or "").strip()
    if current_signal:
        normalized = "-".join(current_signal.lower().split())
        cleaned = "".join(ch for ch in normalized if ch.isalnum() or ch == "-").strip("-")
        if cleaned:
            return cleaned[:48]
    return "runtime-thread"


def _build_rationale(*, proposal_type: str, target_asset: str) -> str:
    if proposal_type == "communication-nudge":
        return f"Recent runtime material suggests a small communication-framing adjustment candidate for {target_asset}, not an applied prompt change."
    if proposal_type == "focus-nudge":
        return f"Recent runtime material suggests a small direction-framing adjustment candidate for {target_asset}, not a policy rewrite."
    if proposal_type == "challenge-nudge":
        return f"Recent runtime material suggests a small challenge-posture adjustment candidate for {target_asset}, while remaining proposal-only."
    return f"Recent runtime material suggests a small world-caution adjustment candidate for {target_asset}, while remaining proposal-only."


def _proposal_state_from_type(proposal_type: str) -> str:
    if proposal_type in {"focus-nudge", "world-caution-nudge"}:
        return "pressing"
    if proposal_type == "communication-nudge":
        return "forming"
    return "tentative"


def _confidence_from_inputs(
    *,
    proposal_type: str,
    source_input_count: int,
    self_model_surface: dict[str, object],
) -> str:
    if proposal_type == "world-caution-nudge":
        return "high"
    if int((self_model_surface.get("summary") or {}).get("uncertain_count") or 0) > 0:
        return "medium"
    if source_input_count >= 5:
        return "medium"
    return "low"


def _blocked(
    *,
    reason: str,
    cadence_state: str,
    trigger: str,
    now: datetime,
    reference: datetime,
) -> dict[str, object]:
    elapsed_minutes = max(int((now - reference).total_seconds() // 60), 0)
    return {
        "producer": "prompt_evolution_runtime",
        "daemon_ran": False,
        "proposal_created": False,
        "proposal_state": "idle",
        "cadence_state": cadence_state,
        "reason": reason,
        "source_inputs": [],
        "output_kind": "self-authored-prompt-proposal",
        "trigger": trigger,
        "proposal_id": "",
        "proposal_type": "",
        "target_asset": "",
        "proposal_visibility": "internal-only",
        "proposal_truth": "proposal-only",
        "boundary": "not-memory-not-identity-not-action-not-applied-prompt",
        "elapsed_minutes": elapsed_minutes,
    }


def _parse_dt(raw: object) -> datetime | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
