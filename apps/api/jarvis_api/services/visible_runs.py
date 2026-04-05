from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from dataclasses import dataclass
from typing import AsyncIterator
from uuid import uuid4

from apps.api.jarvis_api.services.chat_sessions import (
    append_chat_message,
)
from apps.api.jarvis_api.services.candidate_tracking import (
    auto_apply_safe_memory_md_candidates_for_visible_turn,
    auto_apply_safe_user_md_candidates_for_visible_turn,
    track_runtime_contract_candidates_from_chronicle_consolidation_proposals_for_visible_turn,
    track_runtime_contract_candidates_for_visible_turn,
    track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn,
    track_runtime_contract_candidates_from_self_authored_prompt_proposals_for_visible_turn,
    track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn,
    track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn,
)
from apps.api.jarvis_api.services.development_focus_tracking import (
    track_runtime_development_focuses_for_visible_turn,
)
from apps.api.jarvis_api.services.reflective_critic_tracking import (
    track_runtime_reflective_critics_for_visible_turn,
)
from apps.api.jarvis_api.services.goal_signal_tracking import (
    track_runtime_goal_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.self_model_signal_tracking import (
    track_runtime_self_model_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.world_model_signal_tracking import (
    track_runtime_world_model_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.runtime_awareness_signal_tracking import (
    track_runtime_awareness_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.reflection_signal_tracking import (
    track_runtime_reflection_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.temporal_recurrence_signal_tracking import (
    track_runtime_temporal_recurrence_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.witness_signal_tracking import (
    track_runtime_witness_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.open_loop_signal_tracking import (
    track_runtime_open_loop_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.internal_opposition_signal_tracking import (
    track_runtime_internal_opposition_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.self_review_signal_tracking import (
    track_runtime_self_review_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.self_review_record_tracking import (
    track_runtime_self_review_records_for_visible_turn,
)
from apps.api.jarvis_api.services.self_review_run_tracking import (
    track_runtime_self_review_runs_for_visible_turn,
)
from apps.api.jarvis_api.services.self_review_outcome_tracking import (
    track_runtime_self_review_outcomes_for_visible_turn,
)
from apps.api.jarvis_api.services.self_review_cadence_signal_tracking import (
    track_runtime_self_review_cadence_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.dream_hypothesis_signal_tracking import (
    track_runtime_dream_hypothesis_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.dream_adoption_candidate_tracking import (
    track_runtime_dream_adoption_candidates_for_visible_turn,
)
from apps.api.jarvis_api.services.dream_influence_proposal_tracking import (
    track_runtime_dream_influence_proposals_for_visible_turn,
)
from apps.api.jarvis_api.services.self_authored_prompt_proposal_tracking import (
    track_runtime_self_authored_prompt_proposals_for_visible_turn,
)
from apps.api.jarvis_api.services.user_understanding_signal_tracking import (
    track_runtime_user_understanding_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.remembered_fact_signal_tracking import (
    track_runtime_remembered_fact_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.private_inner_note_signal_tracking import (
    track_runtime_private_inner_note_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.private_initiative_tension_signal_tracking import (
    track_runtime_private_initiative_tension_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.private_inner_interplay_signal_tracking import (
    track_runtime_private_inner_interplay_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.private_state_snapshot_tracking import (
    track_runtime_private_state_snapshots_for_visible_turn,
)
from apps.api.jarvis_api.services.diary_synthesis_signal_tracking import (
    track_diary_synthesis_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.private_temporal_curiosity_state_tracking import (
    track_runtime_private_temporal_curiosity_states_for_visible_turn,
)
from apps.api.jarvis_api.services.inner_visible_support_signal_tracking import (
    track_runtime_inner_visible_support_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.regulation_homeostasis_signal_tracking import (
    track_runtime_regulation_homeostasis_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.relation_state_signal_tracking import (
    track_runtime_relation_state_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.relation_continuity_signal_tracking import (
    track_runtime_relation_continuity_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.meaning_significance_signal_tracking import (
    track_runtime_meaning_significance_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.temperament_tendency_signal_tracking import (
    track_runtime_temperament_tendency_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.self_narrative_continuity_signal_tracking import (
    track_runtime_self_narrative_continuity_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.metabolism_state_signal_tracking import (
    track_runtime_metabolism_state_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.release_marker_signal_tracking import (
    track_runtime_release_marker_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.consolidation_target_signal_tracking import (
    track_runtime_consolidation_target_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.selective_forgetting_candidate_tracking import (
    track_runtime_selective_forgetting_candidates_for_visible_turn,
)
from apps.api.jarvis_api.services.attachment_topology_signal_tracking import (
    track_runtime_attachment_topology_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.loyalty_gradient_signal_tracking import (
    track_runtime_loyalty_gradient_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.autonomy_pressure_signal_tracking import (
    track_runtime_autonomy_pressure_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.proactive_loop_lifecycle_tracking import (
    track_runtime_proactive_loop_lifecycle_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.proactive_question_gate_tracking import (
    track_runtime_proactive_question_gates_for_visible_turn,
)
from apps.api.jarvis_api.services.executive_contradiction_signal_tracking import (
    track_runtime_executive_contradiction_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.private_temporal_promotion_signal_tracking import (
    track_runtime_private_temporal_promotion_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.chronicle_consolidation_signal_tracking import (
    track_runtime_chronicle_consolidation_signals_for_visible_turn,
)
from apps.api.jarvis_api.services.chronicle_consolidation_brief_tracking import (
    track_runtime_chronicle_consolidation_briefs_for_visible_turn,
)
from apps.api.jarvis_api.services.chronicle_consolidation_proposal_tracking import (
    track_runtime_chronicle_consolidation_proposals_for_visible_turn,
)
from apps.api.jarvis_api.services.user_md_update_proposal_tracking import (
    track_runtime_user_md_update_proposals_for_visible_turn,
)
from apps.api.jarvis_api.services.memory_md_update_proposal_tracking import (
    track_runtime_memory_md_update_proposals_for_visible_turn,
)
from apps.api.jarvis_api.services.open_loop_closure_proposal_tracking import (
    track_runtime_open_loop_closure_proposals_for_visible_turn,
)
from apps.api.jarvis_api.services.selfhood_proposal_tracking import (
    track_runtime_selfhood_proposals_for_visible_turn,
)
from apps.api.jarvis_api.services.visible_model import (
    VisibleModelDelta,
    VisibleModelRateLimited,
    VisibleModelResult,
    VisibleModelStreamCancelled,
    VisibleModelStreamDone,
    execute_visible_model,
    stream_visible_model,
)
from core.memory.private_layer_pipeline import write_private_terminal_layers
from core.costing.ledger import record_cost
from core.eventbus.bus import event_bus
from core.runtime.db import (
    connect,
    recent_visible_work_notes,
    recent_visible_work_units,
)
from core.runtime.settings import load_settings
from core.tools.workspace_capabilities import (
    invoke_workspace_capability,
    load_workspace_capabilities,
)

CAPABILITY_CALL_PATTERN = re.compile(
    r"^<capability-call\s+(?P<attrs>[^<>]*?)\s*/>$"
)
CAPABILITY_CALL_SCAN_PATTERN = re.compile(
    r"<capability-call\s+(?P<attrs>[^<>]*?)\s*/>"
)
CAPABILITY_BLOCK_PATTERN = re.compile(
    r'<capability-call\s+(?P<attrs>[^>]*?)>\s*\n(?P<content>.*?)\n\s*</capability-call>',
    re.DOTALL,
)
CAPABILITY_ATTR_PATTERN = re.compile(
    r'(?P<name>[a-z_]+)="(?P<value>[^"]*)"'
)
CAPABILITY_CALL_PREFIX = '<capability-call id="'
CAPABILITY_CALL_SUFFIX = '" />'
VISIBLE_CAPABILITY_ARG_NAMES = {"command_text", "target_path", "write_content"}


@dataclass(slots=True)
class VisibleRun:
    run_id: str
    lane: str
    provider: str
    model: str
    user_message: str
    session_id: str | None = None


@dataclass(slots=True)
class VisibleRunController:
    run_id: str
    lane: str
    provider: str
    model: str
    started_at: str
    user_message_preview: str
    cancelled: bool = False
    active_stream: object | None = None
    last_capability_id: str | None = None

    def attach_stream(self, stream: object) -> None:
        self.active_stream = stream

    def clear_stream(self) -> None:
        self.active_stream = None

    def cancel(self) -> None:
        self.cancelled = True
        stream = self.active_stream
        close = getattr(stream, "close", None)
        if callable(close):
            close()

    def is_cancelled(self) -> bool:
        return self.cancelled


_VISIBLE_RUN_CONTROLLERS: dict[str, VisibleRunController] = {}
_LAST_VISIBLE_RUN_OUTCOME: dict[str, str] | None = None
_LAST_VISIBLE_CAPABILITY_USE: dict[str, object] | None = None
_LAST_VISIBLE_EXECUTION_TRACE: dict[str, object] | None = None


def start_visible_run(
    message: str, session_id: str | None = None
) -> AsyncIterator[str]:
    settings = load_settings()
    run = VisibleRun(
        run_id=f"visible-{uuid4().hex}",
        lane=settings.primary_model_lane,
        provider=settings.visible_model_provider,
        model=settings.visible_model_name,
        user_message=(message or "").strip() or "Tom synlig forespoergsel",
        session_id=(session_id or "").strip() or None,
    )
    return _stream_visible_run(run)


async def _stream_visible_run(run: VisibleRun) -> AsyncIterator[str]:
    controller = register_visible_run(run)
    trace = _start_visible_execution_trace(run)
    event_bus.publish(
        "runtime.visible_run_started",
        {
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": run.provider,
            "model": run.model,
            "status": "started",
            "started_at": controller.started_at,
        },
    )
    yield _sse(
        "run",
        {
            "type": "run",
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": run.provider,
            "model": run.model,
            "status": "started",
        },
    )
    yield _sse(
        "working_step",
        {
            "type": "working_step",
            "run_id": run.run_id,
            "action": "thinking",
            "detail": f"Preparing response via {run.provider}/{run.model}",
            "step": 0,
            "status": "running",
        },
    )

    result = None
    visible_output_text = ""
    try:
        try:
            # Run the synchronous model stream in a thread so SSE
            # frames are flushed to the client as each token arrives.
            _sentinel = object()
            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()

            def _pump_model_stream() -> None:
                try:
                    for item in stream_visible_model(
                        message=run.user_message,
                        provider=run.provider,
                        model=run.model,
                        session_id=run.session_id,
                        controller=controller,
                    ):
                        loop.call_soon_threadsafe(queue.put_nowait, item)
                except Exception as exc:
                    loop.call_soon_threadsafe(queue.put_nowait, exc)
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, _sentinel)

            thread_future = loop.run_in_executor(None, _pump_model_stream)

            while True:
                item = await queue.get()
                if item is _sentinel:
                    break
                if isinstance(item, Exception):
                    raise item
                if controller.is_cancelled():
                    for cancelled_chunk in _cancel_visible_run(run):
                        yield cancelled_chunk
                    await thread_future
                    return
                if isinstance(item, VisibleModelDelta):
                    yield _sse(
                        "delta",
                        {
                            "type": "delta",
                            "run_id": run.run_id,
                            "delta": item.delta,
                        },
                    )
                    continue
                if isinstance(item, VisibleModelStreamDone):
                    result = item.result
                    _update_visible_execution_trace(
                        run,
                        {
                            "provider_first_pass_status": "completed",
                            "provider_call_count": 1,
                            "first_pass_input_tokens": item.result.input_tokens,
                            "first_pass_output_tokens": item.result.output_tokens,
                        },
                    )
                    break

            await thread_future
        except VisibleModelStreamCancelled:
            _update_visible_execution_trace(
                run,
                {
                    "provider_first_pass_status": "cancelled",
                    "provider_error_summary": "visible-run-cancelled",
                },
            )
            _persist_session_assistant_message(run, "Generation cancelled.")
            set_last_visible_run_outcome(
                run,
                status="cancelled",
            )
            for cancelled_chunk in _cancel_visible_run(run):
                yield cancelled_chunk
            return
        except VisibleModelRateLimited as exc:
            bounded_message = (
                str(exc) or "Backend is temporarily unavailable. Please try again."
            )
            stage_error = f"first-pass-provider-error: {bounded_message}"
            _update_visible_execution_trace(
                run,
                {
                    "provider_first_pass_status": "failed",
                    "provider_error_summary": bounded_message,
                    "provider_call_count": 1,
                },
            )
            _persist_session_assistant_message(run, bounded_message)
            set_last_visible_run_outcome(
                run,
                status="failed",
                error=stage_error,
            )
            for failure_chunk in _fail_visible_run(run, stage_error):
                yield failure_chunk
            return
        except Exception as exc:
            bounded_message = str(exc) or "visible-run-failed"
            stage_error = f"first-pass-provider-error: {bounded_message}"
            _update_visible_execution_trace(
                run,
                {
                    "provider_first_pass_status": "failed",
                    "provider_error_summary": bounded_message,
                    "provider_call_count": 1,
                },
            )
            _persist_session_assistant_message(run, bounded_message)
            set_last_visible_run_outcome(
                run,
                status="failed",
                error=stage_error,
            )
            for failure_chunk in _fail_visible_run(run, stage_error):
                yield failure_chunk
            return

        if result is None:
            stage_error = "first-pass-provider-error: Visible model stream completed without final result"
            _update_visible_execution_trace(
                run,
                {
                    "provider_first_pass_status": "failed",
                    "provider_error_summary": "Visible model stream completed without final result",
                    "provider_call_count": 1,
                },
            )
            set_last_visible_run_outcome(
                run,
                status="failed",
                error=stage_error,
            )
            for failure_chunk in _fail_visible_run(run, stage_error):
                yield failure_chunk
            return

        capability_plan = _extract_capability_plan(result.text)
        _update_visible_execution_trace(
            run,
            {
                "selected_capability_id": capability_plan.get("selected_capability_id"),
                "parsed_command_text": (capability_plan.get("selected_arguments") or {}).get("command_text"),
                "parsed_target_path": (capability_plan.get("selected_arguments") or {}).get("target_path"),
                "argument_source": capability_plan.get("argument_source") or "none",
                "argument_binding_mode": capability_plan.get("argument_binding_mode") or "id-only",
                "capability_markup_count": len(capability_plan.get("capability_ids") or []),
                "multiple_capability_tags": bool(capability_plan.get("multiple")),
            },
        )

        if controller.is_cancelled():
            set_last_visible_run_outcome(
                run,
                status="cancelled",
            )
            for cancelled_chunk in _cancel_visible_run(run):
                yield cancelled_chunk
            return

        total_input_tokens = result.input_tokens
        total_output_tokens = result.output_tokens
        total_cost_usd = result.cost_usd

        if capability_plan["selected_capability_id"]:
            capability_call = str(capability_plan["selected_capability_id"])
            resolved_target_path, target_source = _resolve_visible_capability_target_path(
                capability_id=capability_call,
                capability_arguments=capability_plan.get("selected_arguments") or {},
                user_message=run.user_message,
            )
            resolved_command_text, command_source = _resolve_visible_capability_command_text(
                capability_id=capability_call,
                capability_arguments=capability_plan.get("selected_arguments") or {},
                user_message=run.user_message,
            )
            resolved_write_content = (
                (capability_plan.get("selected_arguments") or {}).get("write_content")
                or None
            )
            _update_visible_execution_trace(
                run,
                {
                    "parsed_target_path": resolved_target_path,
                    "parsed_command_text": resolved_command_text,
                    "argument_source": _merge_argument_sources(target_source, command_source),
                    "invoke_status": "started",
                },
            )
            capability_result = invoke_workspace_capability(
                capability_call,
                run_id=run.run_id,
                target_path=resolved_target_path,
                command_text=resolved_command_text,
                write_content=resolved_write_content,
            )
            set_last_visible_capability_use(
                run,
                capability_id=capability_call,
                invocation=capability_result,
                capability_arguments=capability_plan.get("selected_arguments") or {},
                argument_source=_merge_argument_sources(target_source, command_source),
            )
            _update_visible_execution_trace(
                run,
                {
                    "invoke_status": capability_result.get("status"),
                    "blocked_reason": capability_result.get("detail"),
                    "argument_source": _merge_argument_sources(target_source, command_source),
                    "normalized_command_text": (
                        ((capability_result.get("result") or {}).get("normalized_command_text"))
                        or None
                    ),
                    "path_normalization_applied": bool(
                        (capability_result.get("result") or {}).get("path_normalization_applied", False)
                    ),
                    "normalization_source": (
                        ((capability_result.get("result") or {}).get("normalization_source"))
                        or "none"
                    ),
                },
            )
            visible_output_text = _capability_visible_text(
                capability_id=capability_call,
                invocation=capability_result,
            )
            event_bus.publish(
                "runtime.visible_run_capability_used",
                {
                    "run_id": run.run_id,
                    "lane": run.lane,
                    "provider": run.provider,
                    "model": run.model,
                    "capability_id": capability_call,
                    "status": capability_result.get("status"),
                    "execution_mode": capability_result.get("execution_mode"),
                },
            )
            yield _sse("trace", _visible_trace_payload(run))
            yield _sse(
                "capability",
                {
                    "type": "capability",
                    "run_id": run.run_id,
                    "capability_id": capability_call,
                    "status": capability_result.get("status"),
                    "execution_mode": capability_result.get("execution_mode"),
                },
            )
            if str(capability_result.get("status") or "") == "executed":
                _update_visible_execution_trace(
                    run,
                    {
                        "provider_second_pass_status": "started",
                    },
                )
                yield _sse(
                    "working_step",
                    {
                        "type": "working_step",
                        "run_id": run.run_id,
                        "action": "thinking",
                        "detail": "Grounding final response from capability result",
                        "step": 1,
                        "status": "running",
                    },
                )
                followup_result = _run_grounded_capability_followup(
                    run,
                    capability_id=capability_call,
                    invocation=capability_result,
                    initial_model_text=_visible_text_without_capability_markup(
                        result.text,
                        had_markup=bool(capability_plan["had_markup"]),
                    ),
                )
                if followup_result is not None:
                    total_input_tokens += followup_result.input_tokens
                    total_output_tokens += followup_result.output_tokens
                    total_cost_usd += followup_result.cost_usd
                    _update_visible_execution_trace(
                        run,
                        {
                            "provider_second_pass_status": "completed",
                            "provider_call_count": 2,
                            "second_pass_input_tokens": followup_result.input_tokens,
                            "second_pass_output_tokens": followup_result.output_tokens,
                        },
                    )
                    visible_output_text = _finalize_second_pass_visible_text(
                        followup_result.text,
                        fallback=visible_output_text,
                    )
                else:
                    _update_visible_execution_trace(
                        run,
                        {
                            "provider_second_pass_status": "failed",
                            "provider_error_summary": (
                                get_last_visible_execution_trace() or {}
                            ).get("provider_error_summary")
                            or "second-pass-provider-error",
                            "provider_call_count": 2,
                        },
                    )
                yield _sse(
                    "delta",
                    {
                        "type": "delta",
                        "run_id": run.run_id,
                        "delta": visible_output_text,
                    },
                )
            else:
                _update_visible_execution_trace(
                    run,
                    {
                        "provider_second_pass_status": "skipped",
                    },
                )
                yield _sse(
                    "delta",
                    {
                        "type": "delta",
                        "run_id": run.run_id,
                        "delta": visible_output_text,
                    },
                )
        else:
            _update_visible_execution_trace(
                run,
                {
                    "invoke_status": "not-invoked",
                    "provider_second_pass_status": "skipped",
                },
            )
            visible_output_text = _visible_text_without_capability_markup(
                result.text,
                had_markup=bool(capability_plan["had_markup"]),
            )
            # Deltas already streamed live — no need to re-send the full text.

        record_cost(
            lane=run.lane,
            provider=run.provider,
            model=run.model,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            cost_usd=total_cost_usd,
        )
        event_bus.publish(
            "cost.recorded",
            {
                "run_id": run.run_id,
                "lane": run.lane,
                "provider": run.provider,
                "model": run.model,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cost_usd": total_cost_usd,
            },
        )
        finished_at = datetime.now(UTC).isoformat()
        event_bus.publish(
            "runtime.visible_run_completed",
            {
                "run_id": run.run_id,
                "lane": run.lane,
                "provider": run.provider,
                "model": run.model,
                "status": "completed",
                "started_at": controller.started_at,
                "finished_at": finished_at,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cost_usd": total_cost_usd,
            },
        )
        _update_visible_execution_trace(
            run,
            {
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "final_status": "completed",
            },
        )
        yield _sse("trace", _visible_trace_payload(run))
        set_last_visible_run_outcome(
            run,
            status="completed",
            text_preview=_preview_text(visible_output_text),
        )
        _persist_session_assistant_message(run, visible_output_text)
        _track_runtime_candidates(run, visible_output_text)
        yield _sse(
            "working_step",
            {
                "type": "working_step",
                "run_id": run.run_id,
                "action": "thinking",
                "detail": "Generation complete",
                "step": 0,
                "status": "done",
            },
        )
        yield _sse(
            "done",
            {
                "type": "done",
                "run_id": run.run_id,
                "status": "completed",
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
            },
        )
    finally:
        unregister_visible_run(run.run_id)


def _preview_text(text: str, limit: int = 120) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _persist_session_assistant_message(run: VisibleRun, text: str) -> None:
    if not run.session_id:
        return
    normalized = str(text or "").strip()
    if not normalized:
        return
    append_chat_message(session_id=run.session_id, role="assistant", content=normalized)


def _track_runtime_candidates(run: VisibleRun, assistant_text: str) -> None:
    if not run.session_id:
        return
    try:
        track_runtime_contract_candidates_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
            assistant_message=assistant_text,
        )
    except Exception:
        return
    try:
        track_runtime_development_focuses_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        return
    try:
        track_runtime_reflective_critics_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        return
    try:
        track_runtime_world_model_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        return
    try:
        track_runtime_self_model_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        return
    try:
        track_runtime_goal_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        return
    try:
        track_runtime_awareness_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_reflection_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        return
    try:
        track_runtime_temporal_recurrence_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_witness_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_internal_opposition_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_self_review_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_self_review_records_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_self_review_runs_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_self_review_outcomes_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_self_review_cadence_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_dream_hypothesis_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_dream_adoption_candidates_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_dream_influence_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_self_authored_prompt_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_user_understanding_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        return
    try:
        track_runtime_remembered_fact_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        return
    try:
        track_runtime_private_inner_note_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_private_initiative_tension_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_private_inner_interplay_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_private_state_snapshots_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_diary_synthesis_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_private_temporal_curiosity_states_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_executive_contradiction_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_inner_visible_support_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_regulation_homeostasis_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_open_loop_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_relation_state_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_private_temporal_promotion_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_chronicle_consolidation_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_chronicle_consolidation_briefs_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_relation_continuity_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_chronicle_consolidation_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_meaning_significance_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_temperament_tendency_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_self_narrative_continuity_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_metabolism_state_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_release_marker_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_consolidation_target_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_selective_forgetting_candidates_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_attachment_topology_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_loyalty_gradient_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_contract_candidates_from_chronicle_consolidation_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_contract_candidates_from_self_authored_prompt_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_user_md_update_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_memory_md_update_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        auto_apply_safe_memory_md_candidates_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        auto_apply_safe_user_md_candidates_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_selfhood_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_open_loop_closure_proposals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_autonomy_pressure_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_proactive_loop_lifecycle_signals_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        track_runtime_proactive_question_gates_for_visible_turn(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        return
    try:
        from apps.api.jarvis_api.services.session_distillation import (
            distill_session_carry,
        )
        distill_session_carry(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.end_of_run_memory_consolidation import (
            consolidate_run_memory,
        )
        consolidate_run_memory(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
            assistant_response=assistant_text,
        )
    except Exception:
        pass


def _extract_capability_call(text: str) -> str | None:
    parsed = _parse_capability_call_markup((text or "").strip())
    if not parsed:
        return None
    return str(parsed.get("capability_id") or "")


def _extract_capability_plan(text: str) -> dict[str, object]:
    raw = str(text or "")

    # First try block-style: <capability-call id="...">content</capability-call>
    block_match = CAPABILITY_BLOCK_PATTERN.search(raw)
    if block_match:
        attrs = _parse_capability_attrs(block_match.group("attrs"))
        capability_id = str(attrs.pop("id", "")).strip()
        block_content = block_match.group("content").strip()
        if capability_id and re.fullmatch(r"[a-z0-9:-]+", capability_id):
            arguments = dict(attrs)
            if block_content:
                arguments["write_content"] = block_content
            return {
                "selected_capability_id": capability_id,
                "selected_arguments": arguments,
                "argument_source": "block-content",
                "argument_binding_mode": "block-content",
                "capability_ids": [capability_id],
                "had_markup": True,
                "multiple": False,
            }

    # Fall back to self-closing: <capability-call id="..." />
    parsed_matches = [
        parsed
        for match in CAPABILITY_CALL_SCAN_PATTERN.finditer(raw)
        if (parsed := _parse_capability_call_markup(match.group(0)))
    ]
    matches = [str(item.get("capability_id") or "") for item in parsed_matches]
    selected: str | None = None
    selected_arguments: dict[str, str] = {}
    argument_binding_mode = "id-only"
    seen: set[str] = set()
    for item in parsed_matches:
        capability_id = str(item.get("capability_id") or "")
        if capability_id in seen:
            continue
        seen.add(capability_id)
        if _is_known_workspace_capability(capability_id):
            selected = capability_id
            selected_arguments = dict(item.get("arguments") or {})
            if selected_arguments:
                argument_binding_mode = "tag-attributes"
            break
    return {
        "selected_capability_id": selected,
        "selected_arguments": selected_arguments,
        "argument_source": "tag-attributes" if selected_arguments else "none",
        "argument_binding_mode": argument_binding_mode,
        "capability_ids": matches,
        "had_markup": bool(matches),
        "multiple": len(matches) > 1,
    }


def _parse_capability_call_markup(text: str) -> dict[str, object] | None:
    match = CAPABILITY_CALL_PATTERN.fullmatch(str(text or "").strip())
    if not match:
        return None
    attrs = _parse_capability_attrs(match.group("attrs"))
    capability_id = str(attrs.pop("id", "")).strip()
    if not capability_id or not re.fullmatch(r"[a-z0-9:-]+", capability_id):
        return None
    arguments = {
        key: value
        for key, value in attrs.items()
        if key in VISIBLE_CAPABILITY_ARG_NAMES and str(value).strip()
    }
    return {
        "capability_id": capability_id,
        "arguments": arguments,
    }


def _parse_capability_attrs(attrs_text: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in CAPABILITY_ATTR_PATTERN.finditer(str(attrs_text or "")):
        attrs[str(match.group("name") or "")] = str(match.group("value") or "")
    return attrs


def _capability_call_state(text: str) -> str:
    candidate = (text or "").strip()
    if not candidate:
        return "invalid"
    if len(candidate) <= len(CAPABILITY_CALL_PREFIX):
        return "prefix" if CAPABILITY_CALL_PREFIX.startswith(candidate) else "invalid"
    if not candidate.startswith(CAPABILITY_CALL_PREFIX):
        return "invalid"

    remainder = candidate[len(CAPABILITY_CALL_PREFIX) :]
    capability_id = ""
    index = 0
    while index < len(remainder) and re.fullmatch(r"[a-z0-9:-]", remainder[index]):
        capability_id += remainder[index]
        index += 1

    tail = remainder[index:]
    if not tail:
        return "prefix"
    if not capability_id:
        return "invalid"
    if CAPABILITY_CALL_SUFFIX.startswith(tail):
        return "exact" if tail == CAPABILITY_CALL_SUFFIX else "prefix"
    return "invalid"


def _strip_capability_markup(text: str) -> str:
    return CAPABILITY_CALL_SCAN_PATTERN.sub("", str(text or ""))


def _visible_text_without_capability_markup(text: str, *, had_markup: bool) -> str:
    stripped = _strip_capability_markup(text)
    # Collapse runs of 3+ newlines into 2 (preserve paragraph breaks) and
    # normalise horizontal whitespace per line, but keep markdown structure.
    lines = stripped.split("\n")
    lines = [" ".join(line.split()) for line in lines]
    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if cleaned:
        return cleaned
    if had_markup:
        return "Capability request was consumed by the visible lane."
    return ""


def _run_grounded_capability_followup(
    run: VisibleRun,
    *,
    capability_id: str,
    invocation: dict[str, object],
    initial_model_text: str,
) -> VisibleModelResult | None:
    followup_message = _build_grounded_capability_followup_message(
        run,
        capability_id=capability_id,
        invocation=invocation,
        initial_model_text=initial_model_text,
    )
    try:
        return execute_visible_model(
            message=followup_message,
            provider=run.provider,
            model=run.model,
            session_id=run.session_id,
        )
    except Exception as exc:
        _update_visible_execution_trace(
            run,
            {
                "provider_second_pass_status": "failed",
                "provider_error_summary": str(exc) or "second-pass-provider-error",
            },
        )
        return None


def _build_grounded_capability_followup_message(
    run: VisibleRun,
    *,
    capability_id: str,
    invocation: dict[str, object],
    initial_model_text: str,
) -> str:
    execution_mode = str(invocation.get("execution_mode") or "unknown")
    status = str(invocation.get("status") or "unknown")
    result = invocation.get("result") or {}
    detail = str(invocation.get("detail") or "").strip()
    result_text = ""
    if isinstance(result, dict):
        result_text = str(result.get("text") or "").strip()
    parts = [
        "Second-pass visible response task.",
        "You have already completed one bounded capability invocation for the current user turn.",
        "Respond to the user in ordinary prose only.",
        "Do not emit any <capability-call ... /> tags.",
        "Do not invoke another capability.",
        "Do not describe hidden orchestration; just answer grounded in the result below.",
        f"Original user message: {run.user_message}",
        f"Capability used: {capability_id}",
        f"Capability status: {status}",
        f"Capability execution mode: {execution_mode}",
    ]
    if initial_model_text:
        parts.append(f"First-pass draft without capability markup: {initial_model_text}")
    if result_text:
        parts.append("Capability result text:")
        parts.append(result_text)
    elif detail:
        parts.append(f"Capability result detail: {detail}")
    return "\n".join(parts)


def _finalize_second_pass_visible_text(text: str, *, fallback: str) -> str:
    plan = _extract_capability_plan(text)
    cleaned = _visible_text_without_capability_markup(
        text,
        had_markup=bool(plan["had_markup"]),
    )
    if cleaned:
        return cleaned
    return fallback


def _is_known_workspace_capability(capability_id: str) -> bool:
    runtime_capabilities = load_workspace_capabilities().get("runtime_capabilities", [])
    for capability in runtime_capabilities:
        if capability.get("capability_id") != capability_id:
            continue
        return True
    return False


def _resolve_visible_capability_target_path(
    *, capability_id: str, capability_arguments: dict[str, str], user_message: str
) -> tuple[str | None, str]:
    runtime_capabilities = load_workspace_capabilities().get("runtime_capabilities", [])
    capability = next(
        (
            item
            for item in runtime_capabilities
            if item.get("capability_id") == capability_id
        ),
        None,
    )
    if capability is None:
        return None, "none"
    if str(capability.get("execution_mode") or "") != "external-file-read":
        return None, "none"
    if str(capability_arguments.get("target_path") or "").strip():
        return str(capability_arguments.get("target_path") or "").strip(), "tag-attributes"
    if str(capability.get("target_path_source") or "") != "invocation-argument":
        return None, "none"
    fallback = _extract_external_target_path_from_user_message(user_message)
    if fallback:
        return fallback, "user-message-fallback"
    return None, "none"


def _extract_external_target_path_from_user_message(user_message: str) -> str | None:
    for match in re.finditer(r"(?P<path>(?:~|/)[^\s<>'\"]+)", str(user_message or "")):
        candidate = str(match.group("path") or "").strip()
        candidate = candidate.rstrip(".,:;!?)]}")
        if candidate:
            return candidate
    return None


def _resolve_visible_capability_command_text(
    *, capability_id: str, capability_arguments: dict[str, str], user_message: str
) -> tuple[str | None, str]:
    runtime_capabilities = load_workspace_capabilities().get("runtime_capabilities", [])
    capability = next(
        (
            item
            for item in runtime_capabilities
            if item.get("capability_id") == capability_id
        ),
        None,
    )
    if capability is None:
        return None, "none"
    if str(capability.get("execution_mode") or "") != "non-destructive-exec":
        return None, "none"
    if str(capability_arguments.get("command_text") or "").strip():
        return str(capability_arguments.get("command_text") or "").strip(), "tag-attributes"
    if str(capability.get("command_source") or "") != "invocation-argument":
        return None, "none"
    fallback = _extract_exec_command_from_user_message(user_message)
    if fallback:
        return fallback, "user-message-fallback"
    return None, "none"


def _merge_argument_sources(*sources: str) -> str:
    meaningful = [str(source or "").strip() for source in sources if str(source or "").strip() and str(source or "").strip() != "none"]
    if not meaningful:
        return "none"
    unique = []
    for item in meaningful:
        if item not in unique:
            unique.append(item)
    return "+".join(unique)


def _extract_exec_command_from_user_message(user_message: str) -> str | None:
    fenced = re.search(r"`(?P<command>[^`\n]+)`", str(user_message or ""))
    if fenced:
        command = str(fenced.group("command") or "").strip()
        if command:
            return command
    for raw_line in str(user_message or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith("command:") or lowered.startswith("kommando:"):
            command = line.split(":", 1)[1].strip()
            if command:
                return command
    return None


def _capability_visible_text(*, capability_id: str, invocation: dict) -> str:
    status = str(invocation.get("status") or "unknown")
    execution_mode = str(invocation.get("execution_mode") or "unknown")
    result = invocation.get("result") or {}
    detail = str(invocation.get("detail") or "").strip()
    text = ""
    if isinstance(result, dict):
        text = str(result.get("text") or "").strip()
        if result.get("type") == "workspace-search-read":
            return _workspace_search_visible_text(
                capability_id=capability_id,
                execution_mode=execution_mode,
                result=result,
            )

    if text:
        return f"[Capability {capability_id} via {execution_mode}]\n{text}"
    if detail:
        return f"[Capability {capability_id} via {execution_mode}]\n{detail}"
    return f"[Capability {capability_id} via {execution_mode}] {status}"


def _workspace_search_visible_text(
    *, capability_id: str, execution_mode: str, result: dict
) -> str:
    path = str(result.get("path") or "ukendt")
    query = str(result.get("query") or "ukendt")
    matches = result.get("matches") or []
    lines = [
        f"[Capability {capability_id} via {execution_mode}]",
        f"File: {path}",
        f"Query: {query}",
    ]
    if isinstance(matches, list) and matches:
        for match in matches:
            if not isinstance(match, dict):
                continue
            line_number = match.get("line")
            excerpt = str(match.get("excerpt") or "").strip()
            if not excerpt:
                continue
            lines.append(f"L{line_number}: {excerpt}")
    else:
        lines.append("No matches found.")
    return "\n".join(lines)


def _bounded_error(error_message: str, limit: int = 160) -> str:
    normalized = " ".join((error_message or "").split()) or "visible-run-failed"
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _fail_visible_run(run: VisibleRun, error_message: str) -> AsyncIterator[str]:
    controller = get_visible_run_controller(run.run_id)
    finished_at = datetime.now(UTC).isoformat()
    bounded_error = _bounded_error(error_message)
    _update_visible_execution_trace(
        run,
        {
            "final_status": "failed",
            "provider_error_summary": (
                get_last_visible_execution_trace() or {}
            ).get("provider_error_summary")
            or bounded_error,
        },
    )
    yield _sse("trace", _visible_trace_payload(run))
    event_bus.publish(
        "runtime.visible_run_failed",
        {
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": run.provider,
            "model": run.model,
            "status": "failed",
            "started_at": controller.started_at if controller else None,
            "finished_at": finished_at,
            "error": bounded_error,
        },
    )
    yield _sse(
        "failed",
        {
            "type": "failed",
            "run_id": run.run_id,
            "status": "failed",
            "error": bounded_error,
        },
    )
    yield _sse(
        "done",
        {
            "type": "done",
            "run_id": run.run_id,
            "status": "failed",
            "error": bounded_error,
        },
    )


def _cancel_visible_run(run: VisibleRun) -> AsyncIterator[str]:
    controller = get_visible_run_controller(run.run_id)
    finished_at = datetime.now(UTC).isoformat()
    _update_visible_execution_trace(
        run,
        {
            "final_status": "cancelled",
            "provider_first_pass_status": (
                get_last_visible_execution_trace() or {}
            ).get("provider_first_pass_status")
            or "cancelled",
        },
    )
    yield _sse("trace", _visible_trace_payload(run))
    event_bus.publish(
        "runtime.visible_run_cancelled",
        {
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": run.provider,
            "model": run.model,
            "status": "cancelled",
            "started_at": controller.started_at if controller else None,
            "finished_at": finished_at,
        },
    )
    yield _sse(
        "cancelled",
        {
            "type": "cancelled",
            "run_id": run.run_id,
            "status": "cancelled",
        },
    )
    yield _sse(
        "done",
        {
            "type": "done",
            "run_id": run.run_id,
            "status": "cancelled",
        },
    )


def register_visible_run(run: VisibleRun) -> VisibleRunController:
    controller = VisibleRunController(
        run_id=run.run_id,
        lane=run.lane,
        provider=run.provider,
        model=run.model,
        started_at=datetime.now(UTC).isoformat(),
        user_message_preview=_preview_text(run.user_message),
    )
    _VISIBLE_RUN_CONTROLLERS[run.run_id] = controller
    return controller


def get_visible_run_controller(run_id: str) -> VisibleRunController | None:
    return _VISIBLE_RUN_CONTROLLERS.get(run_id)


def cancel_visible_run(run_id: str) -> bool:
    controller = get_visible_run_controller(run_id)
    if controller is None:
        return False
    controller.cancel()
    return True


def unregister_visible_run(run_id: str) -> None:
    _VISIBLE_RUN_CONTROLLERS.pop(run_id, None)


def get_active_visible_run() -> dict[str, str] | None:
    if not _VISIBLE_RUN_CONTROLLERS:
        return None
    run_id = next(reversed(_VISIBLE_RUN_CONTROLLERS))
    controller = _VISIBLE_RUN_CONTROLLERS[run_id]
    return {
        "active": True,
        "run_id": controller.run_id,
        "lane": controller.lane,
        "provider": controller.provider,
        "model": controller.model,
        "started_at": controller.started_at,
        "current_user_message_preview": controller.user_message_preview,
        "capability_id": controller.last_capability_id,
        "cancelled": controller.is_cancelled(),
    }


def get_visible_work() -> dict[str, object]:
    active_run = get_active_visible_run()
    if active_run:
        return {
            "active": True,
            "run_id": active_run.get("run_id"),
            "status": "running",
            "lane": active_run.get("lane"),
            "provider": active_run.get("provider"),
            "model": active_run.get("model"),
            "started_at": active_run.get("started_at"),
            "current_user_message_preview": active_run.get(
                "current_user_message_preview"
            ),
            "capability_id": active_run.get("capability_id"),
        }

    last_outcome = get_last_visible_run_outcome() or {}
    last_capability_use = get_last_visible_capability_use() or {}
    return {
        "active": False,
        "run_id": last_outcome.get("run_id"),
        "status": last_outcome.get("status") or "idle",
        "lane": last_outcome.get("lane"),
        "provider": last_outcome.get("provider"),
        "model": last_outcome.get("model"),
        "started_at": None,
        "current_user_message_preview": last_outcome.get("text_preview"),
        "capability_id": last_capability_use.get("capability_id"),
    }


def get_visible_work_surface() -> dict[str, object]:
    visible_work = get_visible_work()
    recent_units = recent_visible_work_units(limit=5)
    current_unit = recent_units[0] if recent_units else {}
    return {
        "active": bool(visible_work.get("active")),
        "current_work_id": current_unit.get("work_id"),
        "current_run_id": visible_work.get("run_id") or current_unit.get("run_id"),
        "status": visible_work.get("status") or current_unit.get("status"),
        "lane": visible_work.get("lane") or current_unit.get("lane"),
        "provider": visible_work.get("provider") or current_unit.get("provider"),
        "model": visible_work.get("model") or current_unit.get("model"),
        "started_at": visible_work.get("started_at") or current_unit.get("started_at"),
        "finished_at": current_unit.get("finished_at"),
        "current_user_message_preview": visible_work.get("current_user_message_preview")
        or current_unit.get("user_message_preview"),
        "capability_id": visible_work.get("capability_id")
        or current_unit.get("capability_id"),
        "recent_work_ids": [
            str(item.get("work_id") or "").strip()
            for item in recent_units
            if str(item.get("work_id") or "").strip()
        ],
        "latest_work_preview": current_unit.get("work_preview"),
    }


def get_visible_selected_work_surface() -> dict[str, object]:
    visible_work_surface = get_visible_work_surface()
    recent_units = recent_visible_work_units(limit=5)
    selected_unit = recent_units[0] if recent_units else {}
    return {
        "active": bool(visible_work_surface.get("active")),
        "selected_work_id": visible_work_surface.get("current_work_id")
        or selected_unit.get("work_id"),
        "selected_run_id": visible_work_surface.get("current_run_id")
        or selected_unit.get("run_id"),
        "status": visible_work_surface.get("status") or selected_unit.get("status"),
        "lane": visible_work_surface.get("lane") or selected_unit.get("lane"),
        "provider": visible_work_surface.get("provider")
        or selected_unit.get("provider"),
        "model": visible_work_surface.get("model") or selected_unit.get("model"),
        "selected_user_message_preview": visible_work_surface.get(
            "current_user_message_preview"
        )
        or selected_unit.get("user_message_preview"),
        "selected_capability_id": visible_work_surface.get("capability_id")
        or selected_unit.get("capability_id"),
        "selected_work_preview": visible_work_surface.get("latest_work_preview")
        or selected_unit.get("work_preview"),
        "recent_work_ids": [
            str(item.get("work_id") or "").strip()
            for item in recent_units
            if str(item.get("work_id") or "").strip()
        ],
    }


def get_visible_selected_work_item() -> dict[str, object]:
    visible_work = get_visible_work()
    visible_work_surface = get_visible_work_surface()
    visible_selected_work_surface = get_visible_selected_work_surface()
    recent_units = recent_visible_work_units(limit=5)
    selected_unit = recent_units[0] if recent_units else {}
    return {
        "active": bool(visible_selected_work_surface.get("active")),
        "selected_work_id": visible_selected_work_surface.get("selected_work_id")
        or visible_work_surface.get("current_work_id")
        or selected_unit.get("work_id"),
        "selected_run_id": visible_selected_work_surface.get("selected_run_id")
        or visible_work_surface.get("current_run_id")
        or visible_work.get("run_id")
        or selected_unit.get("run_id"),
        "selected_status": visible_selected_work_surface.get("status")
        or visible_work_surface.get("status")
        or selected_unit.get("status"),
        "selected_lane": visible_selected_work_surface.get("lane")
        or visible_work_surface.get("lane")
        or selected_unit.get("lane"),
        "selected_provider": visible_selected_work_surface.get("provider")
        or visible_work_surface.get("provider")
        or selected_unit.get("provider"),
        "selected_model": visible_selected_work_surface.get("model")
        or visible_work_surface.get("model")
        or selected_unit.get("model"),
        "selected_user_message_preview": visible_selected_work_surface.get(
            "selected_user_message_preview"
        )
        or visible_work_surface.get("current_user_message_preview")
        or selected_unit.get("user_message_preview"),
        "selected_capability_id": visible_selected_work_surface.get(
            "selected_capability_id"
        )
        or visible_work_surface.get("capability_id")
        or selected_unit.get("capability_id"),
        "selected_work_preview": visible_selected_work_surface.get(
            "selected_work_preview"
        )
        or visible_work_surface.get("latest_work_preview")
        or selected_unit.get("work_preview"),
        "recent_work_ids": list(
            visible_selected_work_surface.get("recent_work_ids") or []
        ),
        "selection_source": "active-visible-work"
        if visible_selected_work_surface.get("active")
        else "persisted-visible-work-unit",
        "recent_count": len(recent_units),
    }


def get_visible_selected_work_note() -> dict[str, object]:
    selected_work_item = get_visible_selected_work_item()
    recent_notes = recent_visible_work_notes(limit=5)
    selected_note = recent_notes[0] if recent_notes else {}
    return {
        "active": bool(selected_note),
        "note_id": selected_note.get("note_id"),
        "work_id": selected_note.get("work_id")
        or selected_work_item.get("selected_work_id"),
        "run_id": selected_note.get("run_id")
        or selected_work_item.get("selected_run_id"),
        "status": selected_note.get("status")
        or selected_work_item.get("selected_status"),
        "lane": selected_note.get("lane") or selected_work_item.get("selected_lane"),
        "provider": selected_note.get("provider")
        or selected_work_item.get("selected_provider"),
        "model": selected_note.get("model") or selected_work_item.get("selected_model"),
        "user_message_preview": selected_note.get("user_message_preview")
        or selected_work_item.get("selected_user_message_preview"),
        "capability_id": selected_note.get("capability_id")
        or selected_work_item.get("selected_capability_id"),
        "work_preview": selected_note.get("work_preview")
        or selected_work_item.get("selected_work_preview"),
        "selection_source": selected_note.get("projection_source")
        or selected_work_item.get("selection_source"),
        "created_at": selected_note.get("created_at"),
        "finished_at": selected_note.get("finished_at"),
        "recent_note_ids": [
            str(item.get("note_id") or "").strip()
            for item in recent_notes
            if str(item.get("note_id") or "").strip()
        ],
    }


def get_last_visible_run_outcome() -> dict[str, str] | None:
    return dict(_LAST_VISIBLE_RUN_OUTCOME) if _LAST_VISIBLE_RUN_OUTCOME else None


def get_last_visible_capability_use() -> dict[str, object] | None:
    if not _LAST_VISIBLE_CAPABILITY_USE:
        return None
    return {
        **dict(_LAST_VISIBLE_CAPABILITY_USE),
        "trace": get_last_visible_execution_trace(),
    }


def get_last_visible_execution_trace() -> dict[str, object] | None:
    return dict(_LAST_VISIBLE_EXECUTION_TRACE) if _LAST_VISIBLE_EXECUTION_TRACE else None


def set_last_visible_run_outcome(
    run: VisibleRun,
    *,
    status: str,
    error: str | None = None,
    text_preview: str | None = None,
) -> None:
    global _LAST_VISIBLE_RUN_OUTCOME
    finished_at = datetime.now(UTC).isoformat()
    outcome = {
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "status": status,
        "finished_at": finished_at,
    }
    if error:
        outcome["error"] = error
    if text_preview:
        outcome["text_preview"] = text_preview
    _LAST_VISIBLE_RUN_OUTCOME = outcome
    _persist_visible_run_outcome(
        run,
        status=status,
        finished_at=finished_at,
        text_preview=text_preview,
        error=error,
    )


def set_last_visible_capability_use(
    run: VisibleRun,
    *,
    capability_id: str,
    invocation: dict[str, object],
    capability_arguments: dict[str, str] | None = None,
    argument_source: str = "none",
) -> None:
    global _LAST_VISIBLE_CAPABILITY_USE
    controller = get_visible_run_controller(run.run_id)
    if controller is not None:
        controller.last_capability_id = capability_id
    capability = invocation.get("capability")
    result = invocation.get("result") or {}
    result_preview = None
    if isinstance(result, dict):
        text = str(result.get("text", "")).strip()
        if text:
            result_preview = _preview_text(text)
        elif isinstance(result.get("matches"), list) and result["matches"]:
            excerpt = str((result["matches"][0] or {}).get("excerpt", "")).strip()
            if excerpt:
                result_preview = _preview_text(excerpt)

    _LAST_VISIBLE_CAPABILITY_USE = {
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "capability_id": capability_id,
        "capability": capability,
        "status": invocation.get("status"),
        "execution_mode": invocation.get("execution_mode"),
        "used_at": datetime.now(UTC).isoformat(),
        "result_preview": result_preview,
        "detail": invocation.get("detail"),
        "parsed_arguments": dict(capability_arguments or {}),
        "argument_source": argument_source,
        "trace": get_last_visible_execution_trace(),
    }


def _persist_visible_run_outcome(
    run: VisibleRun,
    *,
    status: str,
    finished_at: str,
    text_preview: str | None = None,
    error: str | None = None,
) -> None:
    controller = get_visible_run_controller(run.run_id)
    started_at = controller.started_at if controller else None
    capability_id = controller.last_capability_id if controller else None
    user_message_preview = controller.user_message_preview if controller else None
    bounded_error = _bounded_error(error) if error else None
    work_preview = text_preview or bounded_error
    work_id = f"visible-work:{run.run_id}"
    note_id = f"visible-work-note:{run.run_id}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO visible_runs (
                run_id, lane, provider, model, status,
                started_at, finished_at, text_preview, error, capability_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                lane=excluded.lane,
                provider=excluded.provider,
                model=excluded.model,
                status=excluded.status,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at,
                text_preview=excluded.text_preview,
                error=excluded.error,
                capability_id=excluded.capability_id
            """,
            (
                run.run_id,
                run.lane,
                run.provider,
                run.model,
                status,
                started_at,
                finished_at,
                text_preview,
                bounded_error,
                capability_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO visible_work_units (
                work_id, run_id, status, lane, provider, model,
                started_at, finished_at, user_message_preview, capability_id, work_preview
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                work_id=excluded.work_id,
                status=excluded.status,
                lane=excluded.lane,
                provider=excluded.provider,
                model=excluded.model,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at,
                user_message_preview=excluded.user_message_preview,
                capability_id=excluded.capability_id,
                work_preview=excluded.work_preview
            """,
            (
                work_id,
                run.run_id,
                status,
                run.lane,
                run.provider,
                run.model,
                started_at,
                finished_at,
                user_message_preview,
                capability_id,
                work_preview,
            ),
        )
        conn.execute(
            """
            INSERT INTO visible_work_notes (
                note_id, work_id, run_id, status, lane, provider, model,
                user_message_preview, capability_id, work_preview,
                projection_source, created_at, finished_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                note_id=excluded.note_id,
                work_id=excluded.work_id,
                status=excluded.status,
                lane=excluded.lane,
                provider=excluded.provider,
                model=excluded.model,
                user_message_preview=excluded.user_message_preview,
                capability_id=excluded.capability_id,
                work_preview=excluded.work_preview,
                projection_source=excluded.projection_source,
                created_at=excluded.created_at,
                finished_at=excluded.finished_at
            """,
            (
                note_id,
                work_id,
                run.run_id,
                status,
                run.lane,
                run.provider,
                run.model,
                user_message_preview,
                capability_id,
                work_preview,
                "visible-selected-work-item",
                started_at or finished_at,
                finished_at,
            ),
        )
        conn.commit()
    write_private_terminal_layers(
        run_id=run.run_id,
        work_id=work_id,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        user_message_preview=user_message_preview,
        work_preview=work_preview,
        capability_id=capability_id,
    )


def _start_visible_execution_trace(run: VisibleRun) -> dict[str, object]:
    trace = {
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "selected_capability_id": None,
        "parsed_target_path": None,
        "parsed_command_text": None,
        "normalized_command_text": None,
        "path_normalization_applied": False,
        "normalization_source": "none",
        "argument_source": "none",
        "argument_binding_mode": "id-only",
        "invoke_status": "not-invoked",
        "blocked_reason": None,
        "provider_first_pass_status": "started",
        "provider_second_pass_status": "not-started",
        "provider_error_summary": None,
        "provider_call_count": 0,
        "capability_markup_count": 0,
        "multiple_capability_tags": False,
        "first_pass_input_tokens": 0,
        "first_pass_output_tokens": 0,
        "second_pass_input_tokens": 0,
        "second_pass_output_tokens": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "final_status": "running",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _set_last_visible_execution_trace(trace)
    return trace


def _update_visible_execution_trace(run: VisibleRun, updates: dict[str, object]) -> None:
    trace = get_last_visible_execution_trace() or {}
    merged = {
        **trace,
        **updates,
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _set_last_visible_execution_trace(merged)


def _set_last_visible_execution_trace(trace: dict[str, object]) -> None:
    global _LAST_VISIBLE_EXECUTION_TRACE
    _LAST_VISIBLE_EXECUTION_TRACE = dict(trace)
    event_bus.publish(
        "runtime.visible_run_execution_trace",
        dict(trace),
    )


def _visible_trace_payload(run: VisibleRun) -> dict[str, object]:
    trace = get_last_visible_execution_trace() or {}
    return {
        "type": "trace",
        "run_id": run.run_id,
        **trace,
    }
