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
        dream_influence=inputs["dream_influence"],
        self_model_surface=inputs["self_model_surface"],
        inner_voice_state=inputs["inner_voice_state"],
        emergent_surface=inputs["emergent_surface"],
        embodied_state=inputs["embodied_state"],
        loop_runtime=inputs["loop_runtime"],
        adaptive_learning=inputs["adaptive_learning"],
        guided_learning=inputs["guided_learning"],
        adaptive_reasoning=inputs["adaptive_reasoning"],
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
        session_id="heartbeat",
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
        "learning_influence": dict(artifact.get("learning_influence") or {}),
        "dream_influence": dict(artifact.get("dream_influence") or {}),
        "candidate_fragment": str(artifact.get("candidate_fragment") or ""),
        "fragment_grounding": dict(artifact.get("fragment_grounding") or {}),
        "review_light": dict(artifact.get("review_light") or {}),
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
    dream_influence: dict[str, object] | None,
    self_model_surface: dict[str, object] | None,
    inner_voice_state: dict[str, object] | None,
    emergent_surface: dict[str, object] | None,
    embodied_state: dict[str, object] | None,
    loop_runtime: dict[str, object] | None,
    adaptive_learning: dict[str, object] | None,
    guided_learning: dict[str, object] | None,
    adaptive_reasoning: dict[str, object] | None,
    now: datetime | None = None,
) -> dict[str, object]:
    built_at = (now or datetime.now(UTC)).isoformat()
    source_inputs: list[dict[str, str]] = []

    dream = dream_articulation or {}
    dream_influence_surface = dream_influence or {}
    dream_summary = dream.get("summary") or {}
    dream_artifact = dream.get("latest_artifact") or {}
    dream_influence_state = str(dream_influence_surface.get("influence_state") or "quiet")
    if dream_influence_state != "quiet":
        source_inputs.append({
            "source": "dream-influence",
            "signal": (
                f"{dream_influence_state}"
                f" / target={dream_influence_surface.get('influence_target') or 'none'}"
                f" / mode={dream_influence_surface.get('influence_mode') or 'stabilize'}"
                f" / strength={dream_influence_surface.get('influence_strength') or 'none'}"
            )[:120],
        })

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

    learning = adaptive_learning or {}
    learning_mode = str(learning.get("learning_engine_mode") or "")
    if learning_mode:
        source_inputs.append({
            "source": "adaptive-learning",
            "signal": (
                f"{learning_mode}"
                f" / target={learning.get('reinforcement_target') or 'reasoning'}"
                f" / retention={learning.get('retention_bias') or 'light'}"
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
        dream_influence=dream_influence_surface,
        self_model_surface=self_model,
        embodied_state=body,
        loop_runtime=loops,
        adaptive_learning=learning,
    )
    target_asset = _target_asset_from_proposal_type(proposal_type)
    prompt_target = _prompt_target_from_proposal_type(proposal_type)
    anchor = _build_anchor(
        dream_articulation=dream,
        self_model_surface=self_model,
        loop_runtime=loops,
    )
    learning_influence = _build_learning_influence(learning)
    dream_influence_summary = _build_dream_influence_summary(dream_influence_surface)
    guided = guided_learning or {}
    reasoning = adaptive_reasoning or {}
    candidate_fragment = _build_candidate_fragment(
        proposal_type=proposal_type,
        target_asset=target_asset,
        prompt_target=prompt_target,
        adaptive_learning=learning_influence,
        dream_influence=dream_influence_summary,
        guided_learning=guided,
        adaptive_reasoning=reasoning,
        embodied_state=body,
    )
    fragment_co_influence = _build_fragment_co_influence(
        adaptive_learning=learning_influence,
        dream_influence=dream_influence_summary,
    )
    fragment_grounding = _build_fragment_grounding(
        adaptive_learning=learning_influence,
        dream_influence=dream_influence_summary,
        guided_learning=guided,
        adaptive_reasoning=reasoning,
        fragment_co_influence=fragment_co_influence,
    )
    review_light = _build_review_light(
        proposal_type=proposal_type,
        prompt_target=prompt_target,
        adaptive_learning=learning_influence,
        dream_influence=dream_influence_summary,
        guided_learning=guided,
        adaptive_reasoning=reasoning,
        embodied_state=body,
        fragment_co_influence=fragment_co_influence,
    )
    rationale = _build_rationale(
        proposal_type=proposal_type,
        target_asset=target_asset,
        learning_influence=learning_influence,
        dream_influence=dream_influence_summary,
        candidate_fragment=candidate_fragment,
        fragment_co_influence=fragment_co_influence,
    )
    proposal_state = _proposal_state_from_type(proposal_type)
    artifact = {
        "proposal_type": proposal_type,
        "canonical_key": f"runtime-prompt-evolution:{proposal_type}:{anchor}",
        "title": f"Runtime prompt evolution: {target_asset}",
        "summary": (
            f"Bounded {proposal_type} proposal for {target_asset}. "
            f"Prompt target={prompt_target}. "
            f"Adaptive learning={learning_influence.get('learning_engine_mode') or 'none'}"
            f" toward {learning_influence.get('reinforcement_target') or 'none'}. "
            f"Review direction={review_light.get('proposal_direction') or 'none'}. "
            f"Candidate fragment present. "
            f"Proposal-only; not applied."
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
                f"learning_mode={learning_influence.get('learning_engine_mode') or 'none'}",
                f"reinforcement_target={learning_influence.get('reinforcement_target') or 'none'}",
                f"retention_bias={learning_influence.get('retention_bias') or 'light'}",
                f"adaptive_learning={fragment_grounding.get('adaptive_learning') or 'none'}",
                f"dream_influence_state={dream_influence_summary.get('influence_state') or 'quiet'}",
                f"dream_influence_target={dream_influence_summary.get('influence_target') or 'none'}",
                f"dream_influence_mode={dream_influence_summary.get('influence_mode') or 'stabilize'}",
                f"dream_influence_strength={dream_influence_summary.get('influence_strength') or 'none'}",
                f"guided_learning={fragment_grounding.get('guided_learning') or 'none'}",
                f"adaptive_reasoning={fragment_grounding.get('adaptive_reasoning') or 'none'}",
                f"dream_influence={fragment_grounding.get('dream_influence') or 'none'}",
                f"co_influence={fragment_grounding.get('co_influence') or 'none'}",
                f"proposal_direction={review_light.get('proposal_direction') or 'none'}",
                f"proposed_change_kind={review_light.get('proposed_change_kind') or 'none'}",
                f"diff_light_summary={review_light.get('diff_light_summary') or 'none'}",
                f"review_hint={review_light.get('review_hint') or 'none'}",
                f"candidate_fragment={candidate_fragment}",
            ]
        ),
        "support_count": len(source_inputs),
        "status_reason": (
            "Adaptive learning and bounded runtime patterns now warrant a "
            "proposal-only prompt evolution candidate with a self-authored fragment. "
            f"Dream influence={dream_influence_summary.get('influence_state') or 'quiet'}"
            f"/{dream_influence_summary.get('influence_mode') or 'stabilize'}."
        ),
        "target_asset": target_asset,
        "prompt_target": prompt_target,
        "learning_influence": learning_influence,
        "dream_influence": dream_influence_summary,
        "candidate_fragment": candidate_fragment,
        "fragment_grounding": fragment_grounding,
        "fragment_truth": "proposal-only",
        "fragment_visibility": "internal-only",
        "review_light": review_light,
    }

    return {
        "eligible": True,
        "reason": "grounded-runtime-prompt-proposal",
        "proposal_state": proposal_state,
        "source_inputs": source_inputs[:7],
        "artifact": artifact,
        "built_at": built_at,
    }


def build_prompt_evolution_runtime_surface() -> dict[str, object]:
    latest = _latest_prompt_evolution_proposal()
    latest_type = str((latest or {}).get("proposal_type") or "")
    target_asset = _target_asset_from_proposal_type(latest_type) if latest else ""
    prompt_target = _prompt_target_from_proposal_type(latest_type) if latest else ""
    latest_summary_fields = _support_fields_from_latest(latest)
    learning_influence = dict((_last_result or {}).get("learning_influence") or _learning_influence_from_latest(latest))
    dream_influence = dict((_last_result or {}).get("dream_influence") or _dream_influence_from_latest(latest))
    candidate_fragment = str(((_last_result or {}).get("candidate_fragment")) or latest_summary_fields.get("candidate_fragment") or "")
    fragment_grounding = dict((_last_result or {}).get("fragment_grounding") or _fragment_grounding_from_latest(latest))
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
        "learning_influence": learning_influence,
        "dream_influence": dream_influence,
        "candidate_fragment": candidate_fragment,
        "fragment_grounding": fragment_grounding,
        "fragment_truth": "proposal-only",
        "fragment_visibility": "internal-only",
        "review_light": dict((_last_result or {}).get("review_light") or _review_light_from_latest(latest)),
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
            "latest_learning_mode": str(learning_influence.get("learning_engine_mode") or "none"),
            "latest_reinforcement_target": str(learning_influence.get("reinforcement_target") or "none"),
            "latest_retention_bias": str(learning_influence.get("retention_bias") or "light"),
            "latest_dream_influence_state": str(dream_influence.get("influence_state") or "quiet"),
            "latest_dream_influence_target": str(dream_influence.get("influence_target") or "none"),
            "latest_dream_influence_mode": str(dream_influence.get("influence_mode") or "stabilize"),
            "latest_candidate_fragment": candidate_fragment or "none",
            "latest_fragment_co_influence": str(fragment_grounding.get("co_influence") or "none"),
            "proposal_direction": str(((_last_result or {}).get("review_light") or _review_light_from_latest(latest)).get("proposal_direction") or "none"),
            "proposed_change_kind": str(((_last_result or {}).get("review_light") or _review_light_from_latest(latest)).get("proposed_change_kind") or "none"),
            "diff_light_summary": str(((_last_result or {}).get("review_light") or _review_light_from_latest(latest)).get("diff_light_summary") or "none"),
            "fragment_truth": "proposal-only",
            "proposal_truth": "proposal-only",
        },
        "source": "/mc/prompt-evolution",
        "built_at": datetime.now(UTC).isoformat(),
    }


def _load_runtime_inputs() -> dict[str, object]:
    from apps.api.jarvis_api.services.adaptive_learning_runtime import (
        build_adaptive_learning_runtime_surface,
    )
    from apps.api.jarvis_api.services.adaptive_reasoning_runtime import (
        build_adaptive_reasoning_runtime_surface,
    )
    from apps.api.jarvis_api.services.dream_articulation import build_dream_articulation_surface
    from apps.api.jarvis_api.services.dream_influence_runtime import (
        build_dream_influence_runtime_surface,
    )
    from apps.api.jarvis_api.services.embodied_state import build_embodied_state_surface
    from apps.api.jarvis_api.services.emergent_signal_tracking import (
        build_runtime_emergent_signal_surface,
    )
    from apps.api.jarvis_api.services.inner_voice_daemon import get_inner_voice_daemon_state
    from apps.api.jarvis_api.services.loop_runtime import build_loop_runtime_surface
    from apps.api.jarvis_api.services.guided_learning_runtime import (
        build_guided_learning_runtime_surface,
    )
    from apps.api.jarvis_api.services.self_model_signal_tracking import (
        build_runtime_self_model_signal_surface,
    )

    return {
        "dream_articulation": build_dream_articulation_surface(),
        "dream_influence": build_dream_influence_runtime_surface(),
        "self_model_surface": build_runtime_self_model_signal_surface(limit=4),
        "inner_voice_state": get_inner_voice_daemon_state(),
        "emergent_surface": build_runtime_emergent_signal_surface(limit=4),
        "embodied_state": build_embodied_state_surface(),
        "loop_runtime": build_loop_runtime_surface(),
        "adaptive_learning": build_adaptive_learning_runtime_surface(),
        "guided_learning": build_guided_learning_runtime_surface(),
        "adaptive_reasoning": build_adaptive_reasoning_runtime_surface(),
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
    dream_influence: dict[str, object],
    self_model_surface: dict[str, object],
    embodied_state: dict[str, object],
    loop_runtime: dict[str, object],
    adaptive_learning: dict[str, object],
) -> str:
    learning_mode = str(adaptive_learning.get("learning_engine_mode") or "retain")
    reinforcement_target = str(adaptive_learning.get("reinforcement_target") or "reasoning")
    attenuation_bias = str(adaptive_learning.get("attenuation_bias") or "none")
    retention_bias = str(adaptive_learning.get("retention_bias") or "light")
    influence_target = str(dream_influence.get("influence_target") or "none")
    influence_mode = str(dream_influence.get("influence_mode") or "stabilize")
    influence_strength = str(dream_influence.get("influence_strength") or "none")

    if reinforcement_target == "prompt-shape":
        return "focus-nudge"
    if learning_mode in {"rebalance", "attenuate"} or attenuation_bias in {"soften", "release"}:
        return "world-caution-nudge"
    if influence_target == "prompting" and influence_mode == "reinforce":
        return "focus-nudge"
    if influence_mode in {"soften", "caution"} and influence_strength in {"low", "medium"}:
        return "world-caution-nudge"
    if influence_target in {"learning", "reasoning"} and influence_mode == "explore":
        return "communication-nudge"
    if reinforcement_target in {"reasoning", "self-knowledge"} and retention_bias in {"hold", "warm"}:
        return "communication-nudge"

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


def _build_rationale(
    *,
    proposal_type: str,
    target_asset: str,
    learning_influence: dict[str, str],
    dream_influence: dict[str, str],
    candidate_fragment: str,
    fragment_co_influence: str,
) -> str:
    learning_clause = (
        f" Adaptive learning currently points toward "
        f"{learning_influence.get('learning_engine_mode') or 'retain'}"
        f" around {learning_influence.get('reinforcement_target') or 'reasoning'}"
        f" with {learning_influence.get('retention_bias') or 'light'} retention."
    )
    dream_clause = (
        f" Dream influence currently sits at "
        f"{dream_influence.get('influence_state') or 'quiet'}"
        f" toward {dream_influence.get('influence_target') or 'none'}"
        f" via {dream_influence.get('influence_mode') or 'stabilize'}"
        f" ({dream_influence.get('influence_strength') or 'none'})."
        if str(dream_influence.get("influence_state") or "quiet") != "quiet"
        else ""
    )
    co_clause = (
        f" Together they currently shape the fragment as {fragment_co_influence}."
        if fragment_co_influence and fragment_co_influence != "none"
        else ""
    )
    if proposal_type == "communication-nudge":
        return (
            f"Recent runtime material suggests a small communication-framing adjustment "
            f"candidate for {target_asset}, not an applied prompt change."
            f"{learning_clause}{dream_clause}{co_clause} Candidate fragment: {candidate_fragment}"
        )
    if proposal_type == "focus-nudge":
        return (
            f"Recent runtime material suggests a small direction-framing adjustment "
            f"candidate for {target_asset}, not a policy rewrite."
            f"{learning_clause}{dream_clause}{co_clause} Candidate fragment: {candidate_fragment}"
        )
    if proposal_type == "challenge-nudge":
        return (
            f"Recent runtime material suggests a small challenge-posture adjustment "
            f"candidate for {target_asset}, while remaining proposal-only."
            f"{learning_clause}{dream_clause}{co_clause} Candidate fragment: {candidate_fragment}"
        )
    return (
        f"Recent runtime material suggests a small world-caution adjustment "
        f"candidate for {target_asset}, while remaining proposal-only."
        f"{learning_clause}{dream_clause}{co_clause} Candidate fragment: {candidate_fragment}"
    )


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


def _build_learning_influence(adaptive_learning: dict[str, object]) -> dict[str, str]:
    return {
        "learning_engine_mode": str(adaptive_learning.get("learning_engine_mode") or "none"),
        "reinforcement_target": str(adaptive_learning.get("reinforcement_target") or "none"),
        "retention_bias": str(adaptive_learning.get("retention_bias") or "light"),
        "attenuation_bias": str(adaptive_learning.get("attenuation_bias") or "none"),
        "maturation_state": str(adaptive_learning.get("maturation_state") or "early"),
    }


def _build_dream_influence_summary(dream_influence: dict[str, object]) -> dict[str, str]:
    return {
        "influence_state": str(dream_influence.get("influence_state") or "quiet"),
        "influence_target": str(dream_influence.get("influence_target") or "none"),
        "influence_mode": str(dream_influence.get("influence_mode") or "stabilize"),
        "influence_strength": str(dream_influence.get("influence_strength") or "none"),
        "influence_hint": str(dream_influence.get("influence_hint") or "none"),
    }


def _build_fragment_co_influence(
    *,
    adaptive_learning: dict[str, str],
    dream_influence: dict[str, str],
) -> str:
    learning_mode = adaptive_learning.get("learning_engine_mode") or "none"
    reinforcement_target = adaptive_learning.get("reinforcement_target") or "none"
    retention_bias = adaptive_learning.get("retention_bias") or "light"
    dream_state = dream_influence.get("influence_state") or "quiet"
    dream_target = dream_influence.get("influence_target") or "none"
    dream_mode = dream_influence.get("influence_mode") or "stabilize"
    dream_strength = dream_influence.get("influence_strength") or "none"

    if learning_mode == "reinforce" and reinforcement_target == "prompt-shape" and dream_target == "prompting" and dream_mode == "reinforce":
        return "reinforce-thread-visibility"
    if learning_mode in {"rebalance", "attenuate"} and dream_mode in {"soften", "caution"}:
        return "soften-while-rebalancing"
    if learning_mode in {"retain", "consolidate"} and dream_target in {"learning", "reasoning"} and dream_mode == "explore":
        return "hold-open-exploration"
    if retention_bias in {"hold", "warm"} and dream_state != "quiet" and dream_strength in {"low", "medium"}:
        return "keep-thread-warm"
    return "none"


def _build_candidate_fragment(
    *,
    proposal_type: str,
    target_asset: str,
    prompt_target: str,
    adaptive_learning: dict[str, str],
    dream_influence: dict[str, str],
    guided_learning: dict[str, object],
    adaptive_reasoning: dict[str, object],
    embodied_state: dict[str, object],
) -> str:
    learning_mode = adaptive_learning.get("learning_engine_mode") or "retain"
    reinforcement_target = adaptive_learning.get("reinforcement_target") or "reasoning"
    guided_mode = str(guided_learning.get("learning_mode") or "reinforce")
    guided_focus = str(guided_learning.get("learning_focus") or "reasoning")
    reasoning_mode = str(adaptive_reasoning.get("reasoning_mode") or "direct")
    certainty_style = str(adaptive_reasoning.get("certainty_style") or "crisp")
    body_state = str(embodied_state.get("state") or "steady")
    dream_mode = dream_influence.get("influence_mode") or "stabilize"
    dream_target = dream_influence.get("influence_target") or "none"
    dream_strength = dream_influence.get("influence_strength") or "none"
    fragment_co_influence = _build_fragment_co_influence(
        adaptive_learning=adaptive_learning,
        dream_influence=dream_influence,
    )

    if proposal_type == "world-caution-nudge":
        fragment = (
            "When pressure rises, keep caution explicit, narrow the next move, "
            "and prefer bounded wording before expansion."
        )
        if dream_mode in {"soften", "caution"}:
            fragment += " Let the line soften slightly before it hardens into instruction."
        if fragment_co_influence == "soften-while-rebalancing":
            fragment += " Rebalance the tone before the warning settles."
        return _sanitize_fragment(fragment)
    if proposal_type == "communication-nudge":
        fragment = (
            "Keep the inner line plain, grounded in current runtime truth, "
            f"and {certainty_style if certainty_style != 'crisp' else 'measured'} when claims are still forming."
        )
        if dream_mode == "explore" and dream_target in {"learning", "reasoning"}:
            fragment += " Leave a little room for a carried thread to stay legible without becoming decisive."
        if fragment_co_influence == "hold-open-exploration":
            fragment += " Keep that thread warm enough to examine without declaring it settled."
        return _sanitize_fragment(fragment)
    if proposal_type == "challenge-nudge":
        return _sanitize_fragment(
            "Hold a small challenge posture: test the line, keep it bounded, "
            "and do not overstate what has not stabilized."
        )

    fragment = (
        f"Keep the next step plain, bounded, and alive, with {learning_mode} "
        f"around {reinforcement_target}."
    )
    if guided_mode in {"practice", "clarify"}:
        fragment += f" Let {guided_focus} stay close to the next concrete turn."
    if dream_target == "prompting" and dream_mode == "reinforce":
        fragment += " Let the carried thread stay visible in the wording."
    if fragment_co_influence == "reinforce-thread-visibility":
        fragment += " Let warmth guide phrasing, not scope."
    if fragment_co_influence == "keep-thread-warm":
        fragment += " Keep the thread warm, but still bounded by the next trustworthy move."
    if dream_strength == "medium" and dream_mode == "explore":
        fragment += " Keep one edge open for quiet exploration without widening scope."
    if reasoning_mode in {"careful", "constrained"} or body_state in {"strained", "degraded"}:
        fragment += " Keep the move narrow enough to remain trustworthy."
    return _sanitize_fragment(fragment)


def _build_fragment_grounding(
    *,
    adaptive_learning: dict[str, str],
    dream_influence: dict[str, str],
    guided_learning: dict[str, object],
    adaptive_reasoning: dict[str, object],
    fragment_co_influence: str,
) -> dict[str, str]:
    return {
        "adaptive_learning": (
            f"{adaptive_learning.get('learning_engine_mode') or 'retain'}"
            f"/{adaptive_learning.get('reinforcement_target') or 'reasoning'}"
            f"/{adaptive_learning.get('retention_bias') or 'light'}"
        ),
        "guided_learning": (
            f"{guided_learning.get('learning_mode') or 'reinforce'}"
            f"/{guided_learning.get('learning_focus') or 'reasoning'}"
        ),
        "dream_influence": (
            f"{dream_influence.get('influence_state') or 'quiet'}"
            f"/{dream_influence.get('influence_target') or 'none'}"
            f"/{dream_influence.get('influence_mode') or 'stabilize'}"
        ),
        "adaptive_reasoning": (
            f"{adaptive_reasoning.get('reasoning_mode') or 'direct'}"
            f"/{adaptive_reasoning.get('certainty_style') or 'crisp'}"
        ),
        "co_influence": fragment_co_influence or "none",
    }


def _build_review_light(
    *,
    proposal_type: str,
    prompt_target: str,
    adaptive_learning: dict[str, str],
    dream_influence: dict[str, str],
    guided_learning: dict[str, object],
    adaptive_reasoning: dict[str, object],
    embodied_state: dict[str, object],
    fragment_co_influence: str,
) -> dict[str, str]:
    learning_mode = adaptive_learning.get("learning_engine_mode") or "retain"
    reinforcement_target = adaptive_learning.get("reinforcement_target") or "reasoning"
    guided_focus = str(guided_learning.get("learning_focus") or "reasoning")
    reasoning_mode = str(adaptive_reasoning.get("reasoning_mode") or "direct")
    body_state = str(embodied_state.get("state") or "steady")
    dream_mode = dream_influence.get("influence_mode") or "stabilize"
    dream_target = dream_influence.get("influence_target") or "none"

    if proposal_type == "world-caution-nudge":
        return {
            "proposal_direction": "soften-caution" if dream_mode == "soften" else "tighten-caution",
            "proposed_change_kind": "boundary-nudge",
            "diff_light_summary": (
                "Tighten caution framing, but let the tone rebalance before it hardens."
                if fragment_co_influence == "soften-while-rebalancing"
                else "Tighten caution framing and narrow the next move."
            ),
            "review_hint": (
                "Review as a softened caution increase shaped by dream influence, not a policy rewrite."
                if dream_mode == "soften"
                else "Review as a bounded caution increase, not a policy rewrite."
            ),
        }
    if proposal_type == "communication-nudge":
        return {
            "proposal_direction": "follow-dream-thread" if dream_mode == "explore" else "increase-grounding",
            "proposed_change_kind": "communication-calibration",
            "diff_light_summary": (
                "Keep communication grounded while holding the carried thread warm enough to examine."
                if fragment_co_influence == "hold-open-exploration"
                else
                "Let communication keep a quiet carried-thread openness while staying grounded."
                if dream_mode == "explore" and dream_target in {"learning", "reasoning"}
                else "Stabilize communication toward plainer, more grounded wording."
            ),
            "review_hint": (
                "Review as a bounded carried-thread nuance in communication, not a persona change."
                if dream_mode == "explore" and dream_target in {"learning", "reasoning"}
                else "Review as a grounding and tone adjustment, not a persona change."
            ),
        }
    if proposal_type == "challenge-nudge":
        return {
            "proposal_direction": "soften-assertiveness" if body_state in {"strained", "degraded"} else "increase-challenge",
            "proposed_change_kind": "posture-nudge",
            "diff_light_summary": (
                "Soften assertiveness while preserving bounded challenge."
                if body_state in {"strained", "degraded"}
                else "Increase challenge posture without widening scope."
            ),
            "review_hint": "Review as a posture adjustment, not an identity or memory edit.",
        }

    if learning_mode == "reinforce" or reinforcement_target == "prompt-shape":
        return {
            "proposal_direction": (
                "reinforce-dream-framing"
                if dream_target == "prompting" and dream_mode == "reinforce"
                else "follow-dream-thread"
                if dream_mode == "explore" and dream_target in {"learning", "reasoning"}
                else "reinforce-focus-framing"
            ),
            "proposed_change_kind": "framing-nudge",
            "diff_light_summary": (
                "Reinforce focus framing while keeping the carried thread warm and visible."
                if fragment_co_influence == "reinforce-thread-visibility"
                else
                "Reinforce focus framing while letting the carried thread stay visible in the wording."
                if dream_target == "prompting" and dream_mode == "reinforce"
                else "Keep the framing forward while leaving a small carried-thread opening."
                if dream_mode == "explore" and dream_target in {"learning", "reasoning"}
                else "Reinforce focus framing so the next move stays plain and alive."
            ),
            "review_hint": (
                "Review as a dream-shaped framing nudge, not an applied behavioral policy."
                if dream_target == "prompting" and dream_mode == "reinforce"
                else "Review as a bounded carried-thread opening in framing, not an applied behavioral policy."
                if dream_mode == "explore" and dream_target in {"learning", "reasoning"}
                else "Review as a focus-framing nudge, not an applied behavioral policy."
            ),
        }
    if reasoning_mode in {"careful", "constrained"} or guided_focus in {"restraint", "reasoning"}:
        return {
            "proposal_direction": "increase-grounding",
            "proposed_change_kind": "framing-nudge",
            "diff_light_summary": "Increase grounding and keep the next framing more constrained.",
            "review_hint": "Review as a bounded grounding increase, not a full rewrite.",
        }
    return {
        "proposal_direction": "stabilize-communication",
        "proposed_change_kind": "tone-nudge",
        "diff_light_summary": "Stabilize communication so the prompt direction stays readable and bounded.",
        "review_hint": "Review as a small stabilizing nudge, not an applied patch.",
    }


def _sanitize_fragment(text: str) -> str:
    return " ".join(text.replace("|", "/").split())[:220]


def _support_fields_from_latest(latest: dict[str, object] | None) -> dict[str, str]:
    if not latest:
        return {}
    support_summary = str(latest.get("support_summary") or "")
    parsed: dict[str, str] = {}
    for chunk in support_summary.split(" | "):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _learning_influence_from_latest(latest: dict[str, object] | None) -> dict[str, str]:
    parsed = _support_fields_from_latest(latest)
    if not parsed:
        return {}
    return {
        "learning_engine_mode": parsed.get("learning_mode", "none"),
        "reinforcement_target": parsed.get("reinforcement_target", "none"),
        "retention_bias": parsed.get("retention_bias", "light"),
        "attenuation_bias": "none",
        "maturation_state": "early",
    }


def _fragment_grounding_from_latest(latest: dict[str, object] | None) -> dict[str, str]:
    parsed = _support_fields_from_latest(latest)
    if not parsed:
        return {}
    return {
        "adaptive_learning": parsed.get("adaptive_learning", "none"),
        "guided_learning": parsed.get("guided_learning", "none"),
        "dream_influence": parsed.get("dream_influence", "none"),
        "adaptive_reasoning": parsed.get("adaptive_reasoning", "none"),
        "co_influence": parsed.get("co_influence", "none"),
    }


def _dream_influence_from_latest(latest: dict[str, object] | None) -> dict[str, str]:
    parsed = _support_fields_from_latest(latest)
    if not parsed:
        return {}
    return {
        "influence_state": parsed.get("dream_influence_state", "quiet"),
        "influence_target": parsed.get("dream_influence_target", "none"),
        "influence_mode": parsed.get("dream_influence_mode", "stabilize"),
        "influence_strength": parsed.get("dream_influence_strength", "none"),
    }


def _review_light_from_latest(latest: dict[str, object] | None) -> dict[str, str]:
    parsed = _support_fields_from_latest(latest)
    if not parsed:
        return {}
    return {
        "proposal_direction": parsed.get("proposal_direction", "none"),
        "proposed_change_kind": parsed.get("proposed_change_kind", "none"),
        "diff_light_summary": parsed.get("diff_light_summary", "none"),
        "review_hint": parsed.get("review_hint", "none"),
    }


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
