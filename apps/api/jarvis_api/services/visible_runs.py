from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from urllib import request as urllib_request
from dataclasses import dataclass, field
from typing import AsyncIterator
from uuid import uuid4

from apps.api.jarvis_api.services.orb_phase import set_phase as _set_orb_phase

from apps.api.jarvis_api.services.chat_sessions import (
    append_chat_message,
    recent_chat_tool_messages,
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
    VisibleModelToolCalls,
    _build_visible_input,
    _estimate_tokens,
    execute_visible_model,
    stream_visible_model,
)
from core.runtime.provider_router import resolve_provider_router_target
from core.memory.private_layer_pipeline import write_private_terminal_layers
from core.costing.ledger import record_cost
from core.eventbus.bus import event_bus
from core.runtime.db import (
    connect,
    get_runtime_state_value,
    recent_visible_work_notes,
    recent_visible_work_units,
    set_runtime_state_value,
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
    r'<capability-call\s+(?P<attrs>[^<>]*?)(?<!/)>\s*\n(?P<content>.*?)\n\s*</capability-call>',
    re.DOTALL,
)
CAPABILITY_ATTR_PATTERN = re.compile(
    r'(?P<name>[a-z_]+)="(?P<value>[^"]*)"'
)
CAPABILITY_CALL_PREFIX = '<capability-call id="'
CAPABILITY_CALL_SUFFIX = '" />'
VISIBLE_CAPABILITY_ARG_NAMES = {"command_text", "target_path", "write_content"}

# Pending tool approvals — keyed by approval_id
_PENDING_APPROVALS: dict[str, dict] = {}
_VISIBLE_RUN_CONTROL_PREFIX = "visible_runs.control."
_VISIBLE_RUN_ACTIVE_KEY = "visible_runs.active_run"
_VISIBLE_RUN_APPROVAL_PREFIX = "visible_runs.approval."


@dataclass(slots=True)
class VisibleRun:
    run_id: str
    lane: str
    provider: str
    model: str
    user_message: str
    session_id: str | None = None
    autonomous: bool = False  # True = heartbeat-triggered, no user present


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
    seen_simple_tool_call_signatures: set[str] = field(default_factory=set)

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
        if self.cancelled:
            return True
        return _visible_run_cancelled(self.run_id)


_VISIBLE_RUN_CONTROLLERS: dict[str, VisibleRunController] = {}
_LAST_VISIBLE_RUN_OUTCOME: dict[str, str] | None = None
_LAST_VISIBLE_CAPABILITY_USE: dict[str, object] | None = None
_LAST_VISIBLE_EXECUTION_TRACE: dict[str, object] | None = None


def _visible_run_control_key(run_id: str) -> str:
    return f"{_VISIBLE_RUN_CONTROL_PREFIX}{run_id}"


def _visible_run_approval_key(approval_id: str) -> str:
    return f"{_VISIBLE_RUN_APPROVAL_PREFIX}{approval_id}"


def _set_visible_run_control(run_id: str, payload: dict[str, object]) -> None:
    set_runtime_state_value(_visible_run_control_key(run_id), payload)


def _get_visible_run_control(run_id: str) -> dict[str, object]:
    payload = get_runtime_state_value(_visible_run_control_key(run_id), default={})
    return payload if isinstance(payload, dict) else {}


def _set_active_visible_run(payload: dict[str, object] | None) -> None:
    set_runtime_state_value(_VISIBLE_RUN_ACTIVE_KEY, payload or {})


def _get_active_visible_run_state() -> dict[str, object]:
    payload = get_runtime_state_value(_VISIBLE_RUN_ACTIVE_KEY, default={})
    return payload if isinstance(payload, dict) else {}


def _visible_run_cancelled(run_id: str) -> bool:
    return bool(_get_visible_run_control(run_id).get("cancelled"))


def _mark_visible_run_cancelled(run_id: str, *, cancelled: bool = True) -> None:
    state = _get_visible_run_control(run_id)
    if not state:
        return
    state["cancelled"] = cancelled
    state["updated_at"] = datetime.now(UTC).isoformat()
    _set_visible_run_control(run_id, state)


def _set_visible_approval_state(approval_id: str, payload: dict[str, object]) -> None:
    set_runtime_state_value(_visible_run_approval_key(approval_id), payload)


def _get_visible_approval_state(approval_id: str) -> dict[str, object]:
    payload = get_runtime_state_value(_visible_run_approval_key(approval_id), default={})
    return payload if isinstance(payload, dict) else {}


def _classify_visible_run_interruption(error_message: str) -> dict[str, str]:
    normalized = str(error_message or "").strip().lower()
    if not normalized:
        return {
            "interruption_reason": "unknown",
            "interruption_source": "unknown",
        }
    if "timed out" in normalized or "timeout" in normalized:
        return {
            "interruption_reason": "provider-timeout",
            "interruption_source": "provider-stream",
        }
    if "disconnect" in normalized or "client closed" in normalized:
        return {
            "interruption_reason": "client-disconnect",
            "interruption_source": "client-stream",
        }
    if "cancel" in normalized:
        return {
            "interruption_reason": "cancelled",
            "interruption_source": "runtime-control",
        }
    return {
        "interruption_reason": "runtime-error",
        "interruption_source": "runtime",
    }


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


def start_autonomous_run(message: str, session_id: str | None = None) -> None:
    """Trigger an autonomous (heartbeat-initiated) visible run in a background thread.

    The run executes the visible model with tools available, persists results to
    the given session (or the dedicated autonomous session), and auto-denies any
    tool that requires user approval (no user is present). Fire-and-forget.
    """
    import threading

    from apps.api.jarvis_api.services.chat_sessions import (
        create_chat_session,
        list_chat_sessions,
    )

    def _get_or_create_autonomous_session() -> str:
        for s in list_chat_sessions():
            if s.get("title") == "Autonomous":
                return s["id"]
        return create_chat_session(title="Autonomous")["id"]

    resolved_session = (session_id or "").strip() or _get_or_create_autonomous_session()

    settings = load_settings()
    run = VisibleRun(
        run_id=f"autonomous-{uuid4().hex}",
        lane=settings.primary_model_lane,
        provider=settings.visible_model_provider,
        model=settings.visible_model_name,
        user_message=(message or "").strip() or "Autonomous heartbeat check-in",
        session_id=resolved_session,
        autonomous=True,
    )
    event_bus.publish(
        "runtime.autonomous_run_started",
        {
            "run_id": run.run_id,
            "session_id": resolved_session,
            "provider": run.provider,
            "model": run.model,
            "focus": run.user_message[:200],
        },
    )

    def _in_thread() -> None:
        import asyncio as _asyncio

        loop = _asyncio.new_event_loop()
        consumed_frames = 0
        failed = False
        try:
            async def _consume() -> None:
                nonlocal consumed_frames
                async for _ in _stream_visible_run(run):
                    consumed_frames += 1

            loop.run_until_complete(_consume())
        except Exception as exc:
            failed = True
            event_bus.publish(
                "runtime.autonomous_run_failed",
                {
                    "run_id": run.run_id,
                    "session_id": resolved_session,
                    "provider": run.provider,
                    "model": run.model,
                    "focus": run.user_message[:200],
                    "error": str(exc)[:500],
                    "consumed_frames": consumed_frames,
                },
            )
        finally:
            if not failed:
                event_bus.publish(
                    "runtime.autonomous_run_completed",
                    {
                        "run_id": run.run_id,
                        "session_id": resolved_session,
                        "provider": run.provider,
                        "model": run.model,
                        "focus": run.user_message[:200],
                        "consumed_frames": consumed_frames,
                    },
                )
            loop.close()

    threading.Thread(target=_in_thread, name="jarvis-autonomous-run", daemon=True).start()


def _compact_llm_for_run(prompt: str) -> str:
    """Call the compact LLM for run-level summarisation (monkeypatchable)."""
    from core.context.compact_llm import call_compact_llm
    return call_compact_llm(prompt, max_tokens=400)


def _maybe_compact_agentic_messages(
    messages: list[dict],
    *,
    base_count: int,
    settings,
) -> list[dict]:
    """Compact _agentic_messages if they exceed the run threshold.

    Returns a new (shorter) list, or the original list unchanged if below threshold.
    """
    from core.context.token_estimate import estimate_messages_tokens
    if estimate_messages_tokens(messages) < settings.context_run_compact_threshold_tokens:
        return messages
    from core.context.run_compact import compact_run_messages
    return compact_run_messages(
        messages,
        keep_base=base_count,
        keep_recent_pairs=settings.context_keep_recent_pairs,
        summarise_fn=lambda msgs: _compact_llm_for_run(
            "Komprimér disse tool-operationer til max 300 ord. Bevar resultater, fejl og vigtige fund:\n\n"
            + "\n".join(f"{m.get('role', '')}: {m.get('content', '')[:300]}" for m in msgs)
        ),
    )


def _handle_compact_command(run: "VisibleRun") -> str:
    """Run session compact and return a message for Jarvis to respond to."""
    try:
        from core.context.session_compact import compact_session_history
        from core.context.compact_llm import call_compact_llm
        from core.runtime.settings import load_settings as _ls
        settings = _ls()
        cr = compact_session_history(
            run.session_id or "",
            keep_recent=settings.context_keep_recent,
            summarise_fn=lambda msgs: call_compact_llm(
                "Komprimér denne dialog til max 400 ord. Bevar fakta, beslutninger og kontekst:\n\n"
                + "\n".join(f"{m['role']}: {m.get('content', '')}" for m in msgs),
                max_tokens=500,
            ),
        )
        if cr:
            return (
                f"Jeg har netop komprimeret vores samtalehistorik. "
                f"{cr.freed_tokens} tokens frigjort. Bekræft kort."
            )
        return "Ingen historik at komprimere endnu — samtalen er stadig kort."
    except Exception as exc:
        return f"Komprimering mislykkedes: {exc}"


async def _stream_visible_run(run: VisibleRun) -> AsyncIterator[str]:
    # ── /compact command ──────────────────────────────────────────────────
    if run.user_message.strip().lower() == "/compact":
        run.user_message = _handle_compact_command(run)

    controller = register_visible_run(run)
    trace = _start_visible_execution_trace(run)
    _set_orb_phase("think")
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
    markup_buffer = _CapabilityMarkupBuffer()
    _collected_native_tool_calls: list[dict] = []
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
                    safe_text = markup_buffer.feed(item.delta)
                    if safe_text:
                        _set_orb_phase("speak")
                        yield _sse(
                            "delta",
                            {
                                "type": "delta",
                                "run_id": run.run_id,
                                "delta": safe_text,
                            },
                        )
                    continue
                if isinstance(item, VisibleModelToolCalls):
                    _collected_native_tool_calls = item.tool_calls
                    continue
                if isinstance(item, VisibleModelStreamDone):
                    result = item.result
                    remaining = markup_buffer.flush()
                    if remaining:
                        yield _sse(
                            "delta",
                            {
                                "type": "delta",
                                "run_id": run.run_id,
                                "delta": remaining,
                            },
                        )
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
            _cancel_reason = (
                "user-cancelled" if _visible_run_cancelled(run.run_id)
                else "client-disconnect"
            )
            _update_visible_execution_trace(
                run,
                {
                    "provider_first_pass_status": "cancelled",
                    "provider_error_summary": _cancel_reason,
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

        # ── Native tool_calls: execute directly via simple_tools ──
        if _collected_native_tool_calls:
            simple_results = _execute_simple_tool_calls(
                _collected_native_tool_calls, force=run.autonomous, run_id=run.run_id,
            )

            if simple_results:
                _update_visible_execution_trace(
                    run,
                    {
                        "argument_binding_mode": "native-tool-call",
                        "native_tool_call_count": len(simple_results),
                    },
                )

                # Capture base messages BEFORE any tool results are appended to DB.
                # This gives us the correct conversation up to (but not including)
                # the assistant's tool_calls, which we add manually below.
                # If we called _build_visible_input AFTER appending tool messages,
                # those messages would appear in the wrong order and duplicated.
                from apps.api.jarvis_api.services.ollama_visible_prompt import (
                    serialize_ollama_chat_messages,
                )
                visible_input_pre = _build_visible_input(
                    run.user_message, session_id=run.session_id
                )
                base_messages = serialize_ollama_chat_messages(visible_input_pre)

                # Send tool results as SSE events.
                # For approval_needed, block the run until the user approves/denies.
                # DB appends happen AFTER this loop so base_messages stays clean.
                _resolved_result_texts: dict[int, str] = {}

                for _idx, sr in enumerate(simple_results):
                    if sr["status"] == "approval_needed":
                        if run.autonomous:
                            # No user present — auto-deny approval-needed tools immediately
                            _resolved_result_texts[_idx] = (
                                f"[{sr['tool_name']}]: Autonomous run cannot approve tool calls — skipped."
                            )
                            yield _sse("capability", {"type": "tool_denied", "tool": sr["tool_name"]})
                            continue
                        approval_id = f"approval-{uuid4().hex[:12]}"
                        created_at = datetime.now(UTC).isoformat()
                        _PENDING_APPROVALS[approval_id] = {
                            "tool_name": sr["tool_name"],
                            "arguments": sr["arguments"],
                            "result": sr["result"],
                            "run_id": run.run_id,
                            "session_id": run.session_id,
                            "created_at": created_at,
                        }
                        _set_visible_approval_state(approval_id, {
                            "approval_id": approval_id,
                            "status": "pending",
                            "tool_name": sr["tool_name"],
                            "arguments": sr["arguments"],
                            "result": sr["result"],
                            "run_id": run.run_id,
                            "session_id": run.session_id,
                            "created_at": created_at,
                        })
                        yield _sse("approval_request", {
                            "type": "approval_request",
                            "approval_id": approval_id,
                            "tool": sr["tool_name"],
                            "message": sr["result"].get("message", ""),
                            "detail": (
                                sr["result"].get("path")
                                or sr["result"].get("command", "")
                            ),
                        })
                        # Block the generator until user approves or denies (5 min timeout)
                        _resolved = None
                        _deadline = asyncio.get_running_loop().time() + 300.0
                        while asyncio.get_running_loop().time() < _deadline:
                            _approval_state = _get_visible_approval_state(approval_id)
                            _status = str(_approval_state.get("status") or "")
                            if _status == "approved":
                                _resolved = str(_approval_state.get("result_text") or "")
                                break
                            if _status in {"denied", "expired"}:
                                _resolved = None
                                break
                            await asyncio.sleep(0.25)
                        if _resolved is None:
                            _resolved_result_texts[_idx] = f"[{sr['tool_name']}]: Tool call denied by user."
                            yield _sse("capability", {"type": "tool_denied", "tool": sr["tool_name"]})
                        else:
                            _resolved_result_texts[_idx] = _resolved
                            yield _sse("capability", {"type": "tool_result", "tool": sr["tool_name"], "status": "ok"})
                        continue
                    _resolved_result_texts[_idx] = sr["result_text"]
                    yield _sse("capability", {
                        "type": "tool_result",
                        "tool": sr["tool_name"],
                        "status": sr["status"],
                    })

                # Persist tool results to session DB after all approvals are resolved.
                if run.session_id:
                    for _idx, sr in enumerate(simple_results):
                        result_text = _resolved_result_texts.get(_idx, sr.get("result_text", ""))
                        if result_text and sr.get("status") != "duplicate_suppressed":
                            append_chat_message(
                                session_id=run.session_id,
                                role="tool",
                                content=f"[{sr['tool_name']}]: {result_text[:800]}",
                            )

                # ── Agentic follow-up loop ────────────────────────────────────────────
                # Runs up to _AGENTIC_MAX_ROUNDS LLM passes after the first-pass
                # tool execution. Each pass may call more tools; if it does we
                # execute them and continue. If the model produces text we stream
                # it and stop. This lets Jarvis work through multi-step tasks
                # without the user needing to send a new message for every tool.
                import json as _json
                import logging as _alog
                from core.tools.simple_tools import get_tool_definitions as _get_tool_defs

                _AGENTIC_MAX_ROUNDS = 40
                _TOOL_CALL_MARKER = "__TOOL_CALLS__"
                target = resolve_provider_router_target(lane="visible")
                base_url = str(target.get("base_url") or "").strip() or "http://127.0.0.1:11434"
                _agentic_tools = _get_tool_defs()

                # Seed the conversation for the first agentic pass:
                # user-message format works reliably across local models.
                _first_results_block = "\n\n".join(
                    f"[{sr['tool_name']}]:\n{_resolved_result_texts.get(_idx, sr['result_text'])}"
                    for _idx, sr in enumerate(simple_results)
                )
                _agentic_messages: list[dict] = base_messages + [
                    {
                        "role": "user",
                        "content": (
                            f"Here are the tool results for your previous request:\n\n"
                            f"{_first_results_block}\n\n"
                            f"Please respond based on these results. "
                            f"You may call additional tools if you need more information."
                        ),
                    }
                ]
                _all_followup_parts: list[str] = []

                for _agentic_round in range(_AGENTIC_MAX_ROUNDS):
                    _a_parts: list[str] = []
                    _a_tool_calls: list[dict] = []
                    _a_queue: asyncio.Queue = asyncio.Queue()
                    _a_sentinel = object()
                    _a_failure: dict[str, object] = {}

                    _a_payload: dict[str, object] = {
                        "model": run.model,
                        "messages": _agentic_messages,
                        "stream": True,
                    }
                    if _agentic_tools:
                        _a_payload["tools"] = _agentic_tools

                    _a_req = urllib_request.Request(
                        f"{base_url.rstrip('/')}/api/chat",
                        data=_json.dumps(_a_payload, ensure_ascii=False).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )

                    def _pump_agentic(
                        req=_a_req,
                        q=_a_queue,
                        sentinel=_a_sentinel,
                        rnd=_agentic_round,
                        failure=_a_failure,
                    ) -> None:
                        try:
                            with urllib_request.urlopen(req, timeout=90) as resp:
                                for raw_line in resp:
                                    line = raw_line.decode("utf-8").strip()
                                    if not line:
                                        continue
                                    ev = _json.loads(line)
                                    msg = ev.get("message") or {}
                                    delta = str(msg.get("content") or "")
                                    if delta:
                                        loop.call_soon_threadsafe(q.put_nowait, delta)
                                    tc = msg.get("tool_calls") or []
                                    if tc:
                                        loop.call_soon_threadsafe(
                                            q.put_nowait, (_TOOL_CALL_MARKER, tc)
                                        )
                                    if ev.get("done"):
                                        break
                        except Exception as _ae:
                            _a_summary = f"agentic-round-{rnd + 1}-timeout"
                            if "timed out" not in str(_ae).lower():
                                _a_summary = f"agentic-round-{rnd + 1}-provider-error: {str(_ae) or 'unknown'}"
                            failure.update(
                                {
                                    "round": rnd + 1,
                                    "error": str(_ae) or "unknown",
                                    "summary": _a_summary,
                                }
                            )
                            _alog.getLogger(__name__).error(
                                "agentic round %d failed: %s", rnd, _ae, exc_info=True
                            )
                        finally:
                            loop.call_soon_threadsafe(q.put_nowait, sentinel)

                    loop.run_in_executor(None, _pump_agentic)

                    while True:
                        try:
                            _a_item = await asyncio.wait_for(_a_queue.get(), timeout=100)
                        except asyncio.TimeoutError:
                            if not _a_failure:
                                _a_failure.update(
                                    {
                                        "round": _agentic_round + 1,
                                        "error": "timed out waiting for provider stream item",
                                        "summary": f"agentic-round-{_agentic_round + 1}-timeout",
                                    }
                                )
                            break
                        if _a_item is _a_sentinel:
                            break
                        if isinstance(_a_item, tuple) and _a_item[0] == _TOOL_CALL_MARKER:
                            _a_tool_calls.extend(_a_item[1])
                            continue
                        _a_parts.append(_a_item)
                        _all_followup_parts.append(_a_item)
                        yield _sse("delta", {
                            "type": "delta",
                            "run_id": run.run_id,
                            "delta": _a_item,
                        })

                    if _a_failure:
                        _failure_summary = str(_a_failure.get("summary") or "agentic-round-provider-error")
                        _update_visible_execution_trace(
                            run,
                            {
                                "provider_second_pass_status": "failed",
                                "provider_error_summary": _failure_summary,
                                "provider_call_count": max(
                                    int((get_last_visible_execution_trace() or {}).get("provider_call_count") or 1),
                                    _agentic_round + 2,
                                ),
                            },
                        )
                        event_bus.publish(
                            "runtime.visible_run_interrupted",
                            {
                                "run_id": run.run_id,
                                "lane": run.lane,
                                "provider": run.provider,
                                "model": run.model,
                                "phase": "agentic-round",
                                "round": int(_a_failure.get("round") or (_agentic_round + 1)),
                                **_classify_visible_run_interruption(str(_a_failure.get("error") or _failure_summary)),
                                "error": str(_a_failure.get("error") or ""),
                                "summary": _failure_summary,
                            },
                        )

                    if not _a_tool_calls:
                        # No more tool calls — this round produced the final response.
                        break

                    # ── Execute tools for this agentic round ───────────────────────
                    _a_results = _execute_simple_tool_calls(
                        _a_tool_calls, force=run.autonomous, run_id=run.run_id,
                    )
                    _a_resolved: dict[int, str] = {}

                    for _a_idx, _a_sr in enumerate(_a_results):
                        if _a_sr["status"] == "approval_needed":
                            if run.autonomous:
                                _a_resolved[_a_idx] = (
                                    f"[{_a_sr['tool_name']}]: skipped (autonomous)"
                                )
                                yield _sse("capability", {
                                    "type": "tool_denied", "tool": _a_sr["tool_name"]
                                })
                                continue
                            _a_apid = f"approval-{uuid4().hex[:12]}"
                            _a_created_at = datetime.now(UTC).isoformat()
                            _PENDING_APPROVALS[_a_apid] = {
                                "tool_name": _a_sr["tool_name"],
                                "arguments": _a_sr["arguments"],
                                "result": _a_sr["result"],
                                "run_id": run.run_id,
                                "session_id": run.session_id,
                                "created_at": _a_created_at,
                            }
                            _set_visible_approval_state(_a_apid, {
                                "approval_id": _a_apid,
                                "status": "pending",
                                "tool_name": _a_sr["tool_name"],
                                "arguments": _a_sr["arguments"],
                                "result": _a_sr["result"],
                                "run_id": run.run_id,
                                "session_id": run.session_id,
                                "created_at": _a_created_at,
                            })
                            yield _sse("approval_request", {
                                "type": "approval_request",
                                "approval_id": _a_apid,
                                "tool": _a_sr["tool_name"],
                                "message": _a_sr["result"].get("message", ""),
                                "detail": (
                                    _a_sr["result"].get("path")
                                    or _a_sr["result"].get("command", "")
                                ),
                            })
                            _a_res = None
                            _a_deadline = asyncio.get_running_loop().time() + 300.0
                            while asyncio.get_running_loop().time() < _a_deadline:
                                _a_state = _get_visible_approval_state(_a_apid)
                                _a_status = str(_a_state.get("status") or "")
                                if _a_status == "approved":
                                    _a_res = str(_a_state.get("result_text") or "")
                                    break
                                if _a_status in {"denied", "expired"}:
                                    _a_res = None
                                    break
                                await asyncio.sleep(0.25)
                            if _a_res is None:
                                _a_resolved[_a_idx] = (
                                    f"[{_a_sr['tool_name']}]: Tool call denied by user."
                                )
                                yield _sse("capability", {
                                    "type": "tool_denied", "tool": _a_sr["tool_name"]
                                })
                            else:
                                _a_resolved[_a_idx] = _a_res
                                yield _sse("capability", {
                                    "type": "tool_result",
                                    "tool": _a_sr["tool_name"],
                                    "status": "ok",
                                })
                            continue
                        _a_resolved[_a_idx] = _a_sr["result_text"]
                        yield _sse("capability", {
                            "type": "tool_result",
                            "tool": _a_sr["tool_name"],
                            "status": _a_sr["status"],
                        })

                    # Persist tool results to DB
                    if run.session_id:
                        for _a_idx, _a_sr in enumerate(_a_results):
                            _a_rt = _a_resolved.get(_a_idx, _a_sr.get("result_text", ""))
                            if _a_rt and _a_sr.get("status") != "duplicate_suppressed":
                                append_chat_message(
                                    session_id=run.session_id,
                                    role="tool",
                                    content=f"[{_a_sr['tool_name']}]: {_a_rt[:800]}",
                                )

                    # Append this round's exchange to the conversation for next round
                    _a_results_block = "\n\n".join(
                        f"[{_a_sr['tool_name']}]:\n{_a_resolved.get(_a_idx, _a_sr['result_text'])}"
                        for _a_idx, _a_sr in enumerate(_a_results)
                    )
                    _agentic_messages = _agentic_messages + [
                        {
                            "role": "assistant",
                            "content": "".join(_a_parts) or "",
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Tool results:\n\n{_a_results_block}\n\nContinue."
                            ),
                        },
                    ]

                    # ── Run-level auto-compact ─────────────────────────────────────
                    try:
                        from core.runtime.settings import load_settings as _lcs
                        _run_settings = _lcs()
                        _base_count = len(base_messages) + 1  # base + first tool-results msg
                        _compacted = _maybe_compact_agentic_messages(
                            _agentic_messages,
                            base_count=_base_count,
                            settings=_run_settings,
                        )
                        if _compacted is not _agentic_messages:
                            _agentic_messages = _compacted
                            _agentic_messages.append({
                                "role": "user",
                                "content": (
                                    "Note: Dit arbejdende kontekstvindue er netop komprimeret "
                                    "for at frigøre plads. Nævn kort at du kompakterer "
                                    "(1 sætning) og fortsæt din opgave."
                                ),
                            })
                    except Exception:
                        pass  # Never let compact crash the agentic loop

                # ── End agentic loop ───────────────────────────────────────────────

                # Autonomous runs: only use the final round's text so the
                # persisted message is a clean summary, not all intermediate
                # tool-call reasoning concatenated together.
                # Interactive runs: stream everything (already yielded live).
                if run.autonomous:
                    followup_text = "".join(_a_parts).strip()
                else:
                    followup_text = "".join(_all_followup_parts).strip()
                if not followup_text:
                    # LLM only produced tool calls with no text summary.
                    # Make one final LLM call WITHOUT tools to force a
                    # natural-language response based on the tool results.
                    _summary_payload: dict[str, object] = {
                        "model": run.model,
                        "messages": _agentic_messages + [
                            {
                                "role": "user",
                                "content": (
                                    "Summarise what you just did in 1-2 sentences "
                                    "as a natural reply to the user. "
                                    "Do NOT mention tool names or internal details."
                                ),
                            },
                        ],
                        "stream": True,
                        # No "tools" key — forces text-only response
                    }
                    _summary_req = urllib_request.Request(
                        f"{base_url.rstrip('/')}/api/chat",
                        data=_json.dumps(_summary_payload, ensure_ascii=False).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    _summary_parts: list[str] = []
                    try:
                        _s_queue: asyncio.Queue = asyncio.Queue()
                        _s_sentinel = object()

                        def _pump_summary(
                            req=_summary_req,
                            q=_s_queue,
                            sentinel=_s_sentinel,
                        ) -> None:
                            try:
                                with urllib_request.urlopen(req, timeout=45) as resp:
                                    for raw_line in resp:
                                        line = raw_line.decode("utf-8").strip()
                                        if not line:
                                            continue
                                        ev = _json.loads(line)
                                        delta = str((ev.get("message") or {}).get("content") or "")
                                        if delta:
                                            loop.call_soon_threadsafe(q.put_nowait, delta)
                                        if ev.get("done"):
                                            break
                            except Exception:
                                pass
                            finally:
                                loop.call_soon_threadsafe(q.put_nowait, sentinel)

                        loop.run_in_executor(None, _pump_summary)
                        while True:
                            try:
                                _s_item = await asyncio.wait_for(_s_queue.get(), timeout=50)
                            except asyncio.TimeoutError:
                                break
                            if _s_item is _s_sentinel:
                                break
                            _summary_parts.append(_s_item)
                            yield _sse("delta", {
                                "type": "delta",
                                "run_id": run.run_id,
                                "delta": _s_item,
                            })
                    except Exception:
                        pass
                    followup_text = "".join(_summary_parts).strip()

                if not followup_text:
                    # Absolute fallback — should rarely trigger now.
                    _all_tool_names = []
                    for _sr in simple_results:
                        _all_tool_names.append(str(_sr.get("tool_name") or "tool"))
                    if _all_tool_names:
                        _tool_summary = ", ".join(dict.fromkeys(_all_tool_names))
                        followup_text = f"[Completed: {_tool_summary}]"
                    else:
                        followup_text = "[Completed]"
                    yield _sse("delta", {"type": "delta", "run_id": run.run_id, "delta": followup_text})

                total_input_tokens = result.input_tokens * 2
                total_output_tokens = result.output_tokens + _estimate_tokens(followup_text)

                # Persist the assistant message BEFORE done so loadSession()
                # finds it immediately (avoids "message disappears" race).
                try:
                    _persist_session_assistant_message(run, followup_text)
                except Exception:
                    pass

                _set_orb_phase("idle")
                yield _sse("done", {
                    "type": "done",
                    "run_id": run.run_id,
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                })

                # Background: status update and cost recording only
                _run_ref = run
                _tokens = (total_input_tokens, total_output_tokens)
                _followup_text = followup_text
                _followup_preview = followup_text[:140]
                import threading as _threading

                def _persist_tool_result() -> None:
                    try:
                        set_last_visible_run_outcome(
                            _run_ref, status="completed",
                            text_preview=_followup_preview,
                        )
                        record_cost(
                            provider=_run_ref.provider,
                            model=_run_ref.model,
                            input_tokens=_tokens[0],
                            output_tokens=_tokens[1],
                            cost_usd=0.0,
                            run_id=_run_ref.run_id,
                            lane="visible",
                        )
                        finished_at = datetime.now(UTC).isoformat()
                        event_bus.publish(
                            "runtime.visible_run_completed",
                            {
                                "run_id": _run_ref.run_id,
                                "lane": _run_ref.lane,
                                "provider": _run_ref.provider,
                                "model": _run_ref.model,
                                "status": "completed",
                                "finished_at": finished_at,
                                "input_tokens": _tokens[0],
                                "output_tokens": _tokens[1],
                                "cost_usd": 0.0,
                                "native_tool_path": True,
                            },
                        )
                        _run_memory_postprocess(_run_ref, _followup_text)
                    except Exception:
                        pass

                _threading.Thread(
                    target=_persist_tool_result, daemon=True
                ).start()
                return

        # ── Legacy XML capability-call fallback ──
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
                "native_tool_call_count": len(_collected_native_tool_calls),
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

        all_capabilities = capability_plan.get("all_capabilities") or []
        if all_capabilities:
            for planned_step in _planned_visible_capability_steps(
                run,
                all_capabilities=all_capabilities,
                step_offset=100,
            ):
                yield _sse("working_step", planned_step)
            capability_results, any_executed, capability_events = _execute_visible_capability_entries(
                run,
                all_capabilities=all_capabilities,
            )
            for event in capability_events:
                yield _sse("capability", event)

            _update_visible_execution_trace(
                run,
                {
                    "invoke_status": "executed" if any_executed else "not-executed",
                    "capabilities_executed": sum(
                        1 for r in capability_results if r["status"] == "executed"
                    ),
                    "capabilities_total": len(capability_results),
                },
            )

            # Build visible output from all results
            visible_output_text = "\n\n".join(
                _capability_visible_text(
                    capability_id=str(r["capability_id"]),
                    invocation=r["invocation"],
                )
                for r in capability_results
            )

            yield _sse("trace", _visible_trace_payload(run))

            # --- Second pass grounded in ALL results ---
            if any_executed:
                _update_visible_execution_trace(
                    run, {"provider_second_pass_status": "started"},
                )
                yield _sse(
                    "working_step",
                    {
                        "type": "working_step",
                        "run_id": run.run_id,
                        "action": "thinking",
                        "detail": f"Grounding response from {len(capability_results)} capability results",
                        "step": 1,
                        "status": "running",
                    },
                )
                followup_result = _run_grounded_multi_capability_followup(
                    run,
                    capability_results=capability_results,
                    initial_model_text="",
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
                    second_pass_plan = _extract_capability_plan(followup_result.text)
                    second_pass_caps = second_pass_plan.get("all_capabilities") or []
                    if second_pass_caps:
                        for planned_step in _planned_visible_capability_steps(
                            run,
                            all_capabilities=second_pass_caps,
                            step_offset=200,
                        ):
                            yield _sse("working_step", planned_step)
                        followup_capability_results, followup_any_executed, followup_events = (
                            _execute_visible_capability_entries(
                                run,
                                all_capabilities=second_pass_caps,
                            )
                        )
                        capability_results.extend(followup_capability_results)
                        for event in followup_events:
                            yield _sse("capability", event)
                        if followup_any_executed:
                            yield _sse(
                                "working_step",
                                {
                                    "type": "working_step",
                                    "run_id": run.run_id,
                                    "action": "thinking",
                                    "detail": (
                                        "Continuing autonomously with one extra bounded read-only round "
                                        f"from {len(followup_capability_results)} follow-up capability results"
                                    ),
                                    "step": 2,
                                    "status": "running",
                                },
                            )
                            final_followup = _run_grounded_multi_capability_followup(
                                run,
                                capability_results=capability_results,
                                initial_model_text="",
                            )
                            if final_followup is not None:
                                total_input_tokens += final_followup.input_tokens
                                total_output_tokens += final_followup.output_tokens
                                total_cost_usd += final_followup.cost_usd
                                _update_visible_execution_trace(
                                    run,
                                    {
                                        "provider_call_count": 3,
                                        "third_pass_input_tokens": final_followup.input_tokens,
                                        "third_pass_output_tokens": final_followup.output_tokens,
                                    },
                                )
                                visible_output_text = _finalize_second_pass_visible_text(
                                    final_followup.text,
                                    fallback=visible_output_text,
                                )
                            else:
                                visible_output_text = _finalize_second_pass_visible_text(
                                    followup_result.text,
                                    fallback=visible_output_text,
                                )
                        else:
                            visible_output_text = _finalize_second_pass_visible_text(
                                followup_result.text,
                                fallback=visible_output_text,
                            )
                    else:
                        visible_output_text = _finalize_second_pass_visible_text(
                            followup_result.text,
                            fallback=visible_output_text,
                        )
                else:
                    _update_visible_execution_trace(
                        run,
                        {
                            "provider_second_pass_status": "failed",
                            "provider_call_count": 2,
                        },
                    )
                yield _sse(
                    "delta",
                    {"type": "delta", "run_id": run.run_id, "delta": visible_output_text},
                )
            else:
                _update_visible_execution_trace(
                    run, {"provider_second_pass_status": "skipped"},
                )
                yield _sse(
                    "delta",
                    {"type": "delta", "run_id": run.run_id, "delta": visible_output_text},
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
        # Persist the assistant message BEFORE sending done so that the
        # frontend's loadSession() call immediately after done finds the
        # message in the DB (avoids the "message disappears" race condition).
        if visible_output_text:
            try:
                _persist_session_assistant_message(run, visible_output_text)
            except Exception:
                pass
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
    except Exception as _outer_exc:
        # Catch any unhandled exception from tool execution or second-pass streaming
        # and send a proper failed SSE so the browser gets a clean error instead of
        # an abrupt connection close ("Error in input stream").
        import logging as _outer_log
        _outer_log.getLogger(__name__).error(
            "visible-run unhandled exception: %s", _outer_exc, exc_info=True
        )
        _outer_error = str(_outer_exc) or "unexpected-run-error"
        set_last_visible_run_outcome(run, status="failed", error=_outer_error)
        for _fail_chunk in _fail_visible_run(run, _outer_error):
            yield _fail_chunk
        unregister_visible_run(run.run_id)
        return
    finally:
        # Post-processing in finally: status update, candidate tracking, cleanup.
        # Message persistence now happens synchronously before done (above).
        import threading

        def _post_process() -> None:
            try:
                set_last_visible_run_outcome(
                    run,
                    status="completed",
                    text_preview=_preview_text(visible_output_text),
                )
                _track_runtime_candidates(run, visible_output_text)
                _run_memory_postprocess(run, visible_output_text)
            except Exception:
                pass
            finally:
                unregister_visible_run(run.run_id)

        if visible_output_text:
            threading.Thread(target=_post_process, daemon=True).start()
        else:
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
    message = append_chat_message(session_id=run.session_id, role="assistant", content=normalized)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("channel.chat_message_appended", {
            "session_id": run.session_id,
            "message": message,
            "source": "visible-run",
        })
    except Exception:
        pass


def _recent_internal_tool_context(session_id: str | None, *, limit: int = 6) -> str:
    if not session_id:
        return ""
    try:
        messages = recent_chat_tool_messages(session_id, limit=limit)
    except Exception:
        return ""
    lines: list[str] = []
    for item in messages[-limit:]:
        content = " ".join(str(item.get("content") or "").split()).strip()
        if not content:
            continue
        if len(content) > 300:
            content = content[:299].rstrip() + "…"
        lines.append(f"- {content}")
    if not lines:
        return ""
    return "\n".join(
        [
            "Recent internal tool results from this chat.",
            "These are Jarvis-only observations and are not visible user chat:",
            *lines,
        ]
    )


def _run_memory_postprocess(run: VisibleRun, assistant_text: str) -> None:
    if not run.session_id:
        return
    distillation_result: dict[str, object] | None = None
    consolidation_result: dict[str, object] | None = None
    errors: list[str] = []

    try:
        from apps.api.jarvis_api.services.session_distillation import (
            distill_session_carry,
        )

        distillation_result = distill_session_carry(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception as exc:
        errors.append(f"session_distillation:{type(exc).__name__}:{exc}")
        event_bus.publish(
            "memory.session_distillation_failed",
            {
                "session_id": run.session_id,
                "run_id": run.run_id,
                "error": str(exc) or type(exc).__name__,
            },
        )

    try:
        from apps.api.jarvis_api.services.end_of_run_memory_consolidation import (
            consolidate_run_memory,
        )

        consolidation_result = consolidate_run_memory(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
            assistant_response=assistant_text,
            internal_context=_recent_internal_tool_context(run.session_id),
        )
    except Exception as exc:
        errors.append(f"end_of_run_consolidation:{type(exc).__name__}:{exc}")
        event_bus.publish(
            "memory.end_of_run_consolidation_failed",
            {
                "session_id": run.session_id,
                "run_id": run.run_id,
                "error": str(exc) or type(exc).__name__,
            },
        )

    # Generate session summary for cross-session continuity
    try:
        from apps.api.jarvis_api.services.session_distillation import (
            generate_session_summary,
        )

        generate_session_summary(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
            assistant_response=assistant_text,
        )
    except Exception as exc:
        errors.append(f"session_summary:{type(exc).__name__}:{exc}")

    event_bus.publish(
        "memory.visible_run_postprocess_completed",
        {
            "session_id": run.session_id,
            "run_id": run.run_id,
            "distillation_ran": distillation_result is not None,
            "consolidation_ran": consolidation_result is not None,
            "errors": errors,
            "private_brain_count": (
                distillation_result or {}
            ).get("private_brain_count"),
            "workspace_memory_count": (
                distillation_result or {}
            ).get("workspace_memory_count"),
            "candidate_count": (
                consolidation_result or {}
            ).get("candidate_count"),
            "memory_updated": (
                consolidation_result or {}
            ).get("memory_updated"),
            "user_updated": (
                consolidation_result or {}
            ).get("user_updated"),
            "skipped_reason": (
                consolidation_result or {}
            ).get("skipped_reason"),
        },
    )


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


def _extract_capability_call(text: str) -> str | None:
    parsed = _parse_capability_call_markup((text or "").strip())
    if not parsed:
        return None
    return str(parsed.get("capability_id") or "")


_MAX_CAPABILITIES_PER_TURN = 5


def _native_tool_calls_to_capabilities(tool_calls: list[dict]) -> list[dict]:
    """Convert Ollama native tool_calls to capability-plan entries (legacy compat)."""
    from core.tools.workspace_capabilities import resolve_tool_call_to_capability

    caps: list[dict] = []
    for tc in tool_calls[:_MAX_CAPABILITIES_PER_TURN]:
        fn = tc.get("function") or {}
        name = str(fn.get("name") or "")
        arguments = fn.get("arguments") or {}
        if not name:
            continue
        resolved = resolve_tool_call_to_capability(name, arguments)
        capability_id = resolved.get("capability_id") or ""
        if not capability_id:
            continue
        cap_args: dict[str, str] = {}
        if resolved.get("command_text"):
            cap_args["command_text"] = str(resolved["command_text"])
        if resolved.get("target_path"):
            cap_args["target_path"] = str(resolved["target_path"])
        if resolved.get("write_content"):
            cap_args["write_content"] = str(resolved["write_content"])
        caps.append({
            "capability_id": capability_id,
            "arguments": cap_args,
            "source": "native-tool-call",
            "tool_name": name,
        })
    return caps


def _execute_simple_tool_calls(
    tool_calls: list[dict],
    *,
    force: bool = False,
    run_id: str | None = None,
) -> list[dict[str, object]]:
    """Execute native tool_calls directly via simple_tools. Returns results.

    When *force* is True (autonomous runs), use ``execute_tool_force`` which
    bypasses the approval gate (blocked commands are still blocked).
    """
    from core.tools.simple_tools import execute_tool, execute_tool_force, format_tool_result_for_model

    _exec = execute_tool_force if force else execute_tool

    results: list[dict[str, object]] = []
    controller = get_visible_run_controller(run_id) if run_id else None
    for tc in tool_calls[:_MAX_CAPABILITIES_PER_TURN]:
        fn = tc.get("function") or {}
        name = str(fn.get("name") or "")
        arguments = fn.get("arguments") or {}
        if not name:
            continue
        signature = json.dumps(
            {
                "tool_name": name,
                "arguments": arguments,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        if controller and signature in controller.seen_simple_tool_call_signatures:
            results.append({
                "tool_name": name,
                "arguments": arguments,
                "result": {
                    "status": "duplicate_suppressed",
                    "message": "Skipped duplicate tool call in the same visible run.",
                },
                "result_text": "[Duplicate tool call skipped in same visible run]",
                "status": "duplicate_suppressed",
            })
            continue
        result = _exec(name, arguments)
        result_text = format_tool_result_for_model(name, result)
        if controller and result.get("status") in {"ok", "approval_needed"}:
            controller.seen_simple_tool_call_signatures.add(signature)
        results.append({
            "tool_name": name,
            "arguments": arguments,
            "result": result,
            "result_text": result_text,
            "status": result.get("status", "ok"),
        })
    return results


def resolve_pending_approval(approval_id: str, *, approved: bool) -> dict:
    """Resolve a pending tool approval.

    Resolves a pending approval in shared runtime state so a blocked streaming
    generator can resume even if the approve/deny request lands on another worker.
    """
    from core.tools.simple_tools import execute_tool_force, format_tool_result_for_model

    pending = _PENDING_APPROVALS.pop(approval_id, None)
    shared_pending = _get_visible_approval_state(approval_id)
    if not pending and shared_pending:
        pending = shared_pending
    if not pending:
        return {"error": "Approval not found or expired", "status": "error"}
    if str(pending.get("status") or "pending") not in {"", "pending"}:
        return {"error": "Approval already resolved", "status": "error"}

    if not approved:
        _set_visible_approval_state(
            approval_id,
            {
                **pending,
                "approval_id": approval_id,
                "status": "denied",
                "approved": False,
                "resolved_at": datetime.now(UTC).isoformat(),
            },
        )
        event_bus.publish("tool.approval_resolved", {
            "approval_id": approval_id,
            "tool": pending["tool_name"],
            "approved": False,
            "status": "denied",
        })
        return {"status": "denied", "tool": pending["tool_name"]}

    result = execute_tool_force(pending["tool_name"], pending["arguments"])
    result_text = format_tool_result_for_model(pending["tool_name"], result)

    event_bus.publish("tool.approval_resolved", {
        "approval_id": approval_id,
        "tool": pending["tool_name"],
        "approved": True,
        "status": result.get("status", "ok"),
    })
    _set_visible_approval_state(
        approval_id,
        {
            **pending,
            "approval_id": approval_id,
            "status": "approved",
            "approved": True,
            "resolved_at": datetime.now(UTC).isoformat(),
            "tool_status": result.get("status", "ok"),
            "result_text": result_text,
        },
    )

    return {
        "status": result.get("status", "ok"),
        "tool": pending["tool_name"],
        "result_text": result_text,
    }


def _extract_capability_plan(text: str) -> dict[str, object]:
    raw = str(text or "")
    parsed_matches: list[dict[str, object]] = []

    for match in CAPABILITY_BLOCK_PATTERN.finditer(raw):
        attrs = _parse_capability_attrs(match.group("attrs"))
        capability_id = str(attrs.pop("id", "")).strip()
        if not capability_id or not re.fullmatch(r"[a-z0-9:-]+", capability_id):
            continue
        arguments = dict(attrs)
        block_content = match.group("content").strip()
        if block_content:
            arguments["write_content"] = block_content
        parsed_matches.append(
            {
                "capability_id": capability_id,
                "arguments": arguments,
                "_source_order": match.start(),
                "_binding_mode": "block-content",
            }
        )

    for match in CAPABILITY_CALL_SCAN_PATTERN.finditer(raw):
        parsed = _parse_capability_call_markup(match.group(0))
        if not parsed:
            continue
        parsed_matches.append(
            {
                **parsed,
                "_source_order": match.start(),
                "_binding_mode": "tag-attributes" if parsed.get("arguments") else "id-only",
            }
        )

    parsed_matches.sort(key=lambda item: int(item.get("_source_order") or 0))
    matches = [str(item.get("capability_id") or "") for item in parsed_matches]

    all_capabilities: list[dict[str, object]] = []
    seen: set[str] = set()
    selected_binding_mode = "id-only"
    for item in parsed_matches:
        capability_id = str(item.get("capability_id") or "")
        if _is_known_workspace_capability(capability_id):
            arguments = dict(item.get("arguments") or {})
            dedupe_key = json.dumps(
                {
                    "capability_id": capability_id,
                    "arguments": arguments,
                },
                sort_keys=True,
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            all_capabilities.append({
                "capability_id": capability_id,
                "arguments": arguments,
            })
            if len(all_capabilities) == 1:
                selected_binding_mode = str(item.get("_binding_mode") or "id-only")
            if len(all_capabilities) >= _MAX_CAPABILITIES_PER_TURN:
                break

    # For memory-write self-closing tags without write_content,
    # try to find markdown content after the tag in the LLM response.
    # This handles the common case where the LLM uses self-closing syntax
    # and puts the content below instead of inside a block tag.
    for cap in all_capabilities:
        cap_id = str(cap.get("capability_id") or "")
        cap_args = cap.get("arguments") or {}
        if "write-workspace-memory" in cap_id or "write-user-profile" in cap_id:
            if not cap_args.get("write_content"):
                content_after = _extract_content_after_capability_tag(raw, cap_id)
                if content_after:
                    cap["arguments"] = {**cap_args, "write_content": content_after}

    selected = str(all_capabilities[0]["capability_id"]) if all_capabilities else None
    selected_arguments = dict(all_capabilities[0]["arguments"]) if all_capabilities else {}
    argument_binding_mode = (
        selected_binding_mode if selected else "id-only"
    )
    if selected and argument_binding_mode == "id-only" and selected_arguments:
        argument_binding_mode = "tag-attributes"

    return {
        "selected_capability_id": selected,
        "selected_arguments": selected_arguments,
        "argument_source": argument_binding_mode if selected else "none",
        "argument_binding_mode": argument_binding_mode,
        "capability_ids": matches,
        "all_capabilities": all_capabilities,
        "had_markup": bool(matches),
        "multiple": len(all_capabilities) > 1,
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


def _extract_content_after_capability_tag(raw: str, capability_id: str) -> str | None:
    """Extract markdown/text content after a self-closing capability tag.

    When LLMs use <capability-call id="..." /> (self-closing) and then write
    the intended content below the tag, this function extracts that content.
    Only used for memory-write capabilities where write_content is expected.
    """
    # Find the self-closing tag
    pattern = re.compile(
        rf'<capability-call\s[^>]*id="{re.escape(capability_id)}"[^>]*/>\s*\n',
        re.IGNORECASE,
    )
    match = pattern.search(raw)
    if not match:
        return None

    after = raw[match.end():].strip()
    if not after:
        return None

    # Look for markdown content (starting with # or containing structured text)
    # Stop at the next capability-call tag or end of text
    next_tag = re.search(r'<capability-call\s', after)
    if next_tag:
        after = after[:next_tag.start()].strip()

    # Only accept if it looks like memory content (has a heading or substantial text)
    if len(after) < 20:
        return None
    if after.startswith("#") or after.startswith("- ") or "\n" in after:
        return after

    return None


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


class _CapabilityMarkupBuffer:
    """Buffer that holds back streaming deltas that may be capability-call markup.

    Tokens are fed in via ``feed()``.  The buffer accumulates text while it
    looks like the start of a ``<capability-call …/>`` or block tag.  When
    the accumulated text can no longer be a prefix of a capability tag, the
    buffered content is flushed (returned to the caller for sending).  When
    a complete tag is detected, it is swallowed (not returned).
    """

    _OPEN = "<capability-call"

    def __init__(self) -> None:
        self._buf = ""

    def feed(self, text: str) -> str:
        """Accept new text; return any content safe to send to the client."""
        self._buf += text
        return self._drain()

    def flush(self) -> str:
        """Return any remaining buffered content (call at end-of-stream)."""
        out = self._buf
        self._buf = ""
        return _strip_capability_markup(out)

    # ------------------------------------------------------------------

    def _drain(self) -> str:
        """Return sendable prefix, keeping potential markup buffered."""
        out_parts: list[str] = []
        while self._buf:
            tag_start = self._buf.find("<")
            if tag_start == -1:
                # No '<' at all — everything is safe.
                out_parts.append(self._buf)
                self._buf = ""
                break
            if tag_start > 0:
                # Text before '<' is safe to send.
                out_parts.append(self._buf[:tag_start])
                self._buf = self._buf[tag_start:]
            # self._buf now starts with '<'.
            # Check if it is (or could become) a capability tag.
            if self._is_capability_prefix(self._buf):
                # Could still be a capability tag — check for complete match.
                m = CAPABILITY_CALL_SCAN_PATTERN.match(self._buf)
                if m:
                    # Complete self-closing tag — swallow it.
                    self._buf = self._buf[m.end():]
                    continue
                bm = CAPABILITY_BLOCK_PATTERN.match(self._buf)
                if bm:
                    # Complete block tag — swallow it.
                    self._buf = self._buf[bm.end():]
                    continue
                # Incomplete prefix — keep buffering.
                break
            else:
                # '<' is not part of a capability tag — safe to send.
                out_parts.append(self._buf[0])
                self._buf = self._buf[1:]
        return "".join(out_parts)

    @staticmethod
    def _is_capability_prefix(text: str) -> bool:
        """True if *text* could be the start of a capability-call tag."""
        opening = _CapabilityMarkupBuffer._OPEN
        check_len = min(len(text), len(opening))
        return text[:check_len] == opening[:check_len]


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
        "Every substantive claim must be grounded in the capability result below.",
        "If runtime facts are thin, say what remains uncertain instead of smoothing it over.",
        "If documentation and code or command output conflict, prefer code and command output.",
        "README or file-structure summaries do not outrank direct code/file evidence.",
        "If the user asked for code analysis, do not call this a code analysis unless you have actually read concrete code files.",
        "If more read-only data is clearly needed and the task is still bounded, you may emit more <capability-call ... /> tags instead of asking the user for permission to continue.",
        "Only ask the user to continue when the next step needs approval or the goal is genuinely unclear.",
        f"Original user message: {run.user_message}",
        f"Capability used: {capability_id}",
        f"Capability status: {status}",
        f"Capability execution mode: {execution_mode}",
    ]
    if _is_memory_commit_request(run.user_message):
        parts.append(
            "If the user asked you to remember or save something and the write succeeded, state that it has been saved. Do not talk about syntax unless the runtime result explicitly failed."
        )
    if result_text:
        parts.append("Capability result text:")
        parts.append(result_text)
    elif detail:
        parts.append(f"Capability result detail: {detail}")
    return "\n".join(parts)


def _run_grounded_multi_capability_followup(
    run: VisibleRun,
    *,
    capability_results: list[dict[str, object]],
    initial_model_text: str,
) -> VisibleModelResult | None:
    followup_message = _build_grounded_multi_capability_followup_message(
        run,
        capability_results=capability_results,
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


def _build_grounded_multi_capability_followup_message(
    run: VisibleRun,
    *,
    capability_results: list[dict[str, object]],
    initial_model_text: str,
) -> str:
    n = len(capability_results)
    parts = [
        "Second-pass visible response task.",
        f"You executed {n} capabilit{'y' if n == 1 else 'ies'} this turn. Results are below.",
        "",
        "Respond to the user grounded in these results.",
        "Every substantive claim must be grounded in one or more concrete capability results below.",
        "If runtime facts are thin, stale, or conflicting, say that plainly.",
        "If docs and code disagree, prefer code and direct command/file output.",
        "README, pyproject, or directory names are not enough for a real code analysis by themselves.",
        "If the user asked for code analysis, do not stop at structure or documentation; read concrete code files before claiming analysis.",
        "If more read-only data is clearly needed and the task is still bounded, emit additional <capability-call ... /> tags now and continue autonomously.",
        "Only ask the user to continue when the next step needs approval or the goal is genuinely unclear.",
        "",
        f"Original user message: {run.user_message}",
    ]
    if _is_memory_commit_request(run.user_message):
        parts.append(
            "If the user asked you to remember or save something and the write succeeded, state that it has been saved. Do not describe block syntax or retry mechanics unless the runtime result explicitly failed."
        )
    if _is_code_analysis_request(run.user_message):
        parts.append(
            "Code-analysis mode: prioritize concrete files such as entrypoints, routes, services, core modules, and tests. Do not present README-only or tree-only summaries as code analysis."
        )
    for i, cr in enumerate(capability_results):
        parts.append("")
        parts.append(f"--- Capability {i + 1}: {cr['capability_id']} ---")
        parts.append(f"Status: {cr['status']}")
        parts.append(f"Execution mode: {cr['execution_mode']}")
        result_text = str(cr.get("result_text") or "").strip()
        detail = str(cr.get("detail") or "").strip()
        if result_text:
            parts.append("Result:")
            parts.append(result_text)
        elif detail:
            parts.append(f"Detail: {detail}")
    return "\n".join(parts)


def _is_code_analysis_request(user_message: str) -> bool:
    normalized = str(user_message or "").lower()
    return any(
        token in normalized
        for token in (
            "code analysis",
            "kode analyse",
            "kodeanalyse",
            "codeanalyse",
            "gennemgang",
            "walkthrough",
            "review koden",
            "analyse af koden",
            "analyse main repo",
            "analyser main repo",
        )
    )


def _is_memory_commit_request(user_message: str) -> bool:
    normalized = str(user_message or "").lower()
    return any(
        token in normalized
        for token in (
            "remember this",
            "remember that",
            "husk dette",
            "husk det",
            "gem dette",
            "gem det",
            "this is important",
            "det er vigtigt",
            "do not forget",
            "glem ikke",
        )
    )


def _execute_visible_capability_entries(
    run: VisibleRun,
    *,
    all_capabilities: list[dict[str, object]],
) -> tuple[list[dict[str, object]], bool, list[dict[str, object]]]:
    capability_results: list[dict[str, object]] = []
    capability_events: list[dict[str, object]] = []
    any_executed = False

    for cap_entry in all_capabilities:
        cap_id = str(cap_entry["capability_id"])
        cap_args = dict(cap_entry.get("arguments") or {})

        resolved_target_path, target_source = _resolve_visible_capability_target_path(
            capability_id=cap_id,
            capability_arguments=cap_args,
            user_message=run.user_message,
        )
        resolved_command_text, command_source = _resolve_visible_capability_command_text(
            capability_id=cap_id,
            capability_arguments=cap_args,
            user_message=run.user_message,
        )
        resolved_write_content = cap_args.get("write_content") or None

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
            cap_id,
            run_id=run.run_id,
            target_path=resolved_target_path,
            command_text=resolved_command_text,
            write_content=resolved_write_content,
        )

        cap_status = str(capability_result.get("status") or "")
        cap_exec_mode = str(capability_result.get("execution_mode") or "")
        cap_result_obj = capability_result.get("result") or {}
        cap_result_text = ""
        if isinstance(cap_result_obj, dict):
            cap_result_text = str(cap_result_obj.get("text") or "").strip()
        cap_detail = str(capability_result.get("detail") or "").strip()

        # Surface detailed error context when a capability fails. Jarvis
        # previously only saw the short cap_detail string ("blocked-X"),
        # which made it hard to debug what went wrong. Now error results
        # include exit_code, normalized command, stderr preview, and
        # block reason as part of the result_text the LLM sees.
        if cap_status and cap_status != "executed":
            error_lines: list[str] = [f"TOOL_ERROR status={cap_status}"]
            if isinstance(cap_result_obj, dict):
                exit_code = cap_result_obj.get("exit_code")
                if exit_code is not None:
                    error_lines.append(f"exit_code={exit_code}")
                normalized_cmd = str(cap_result_obj.get("normalized_command_text") or "").strip()
                if normalized_cmd:
                    error_lines.append(f"normalized_command={normalized_cmd[:200]}")
                target_path_field = str(cap_result_obj.get("target_path") or cap_result_obj.get("path") or "").strip()
                if target_path_field:
                    error_lines.append(f"target_path={target_path_field[:200]}")
            if cap_detail:
                error_lines.append(f"detail={cap_detail[:400]}")
            error_header = " | ".join(error_lines)
            if cap_result_text:
                cap_result_text = (
                    f"{error_header}\n--- captured output ---\n{cap_result_text}"
                )
            else:
                cap_result_text = error_header

        # Echo confirmation header for memory/file writes so the LLM gets
        # explicit feedback that the write succeeded — Jarvis previously
        # only saw the merged preview text and could not tell whether the
        # write had actually been persisted.
        if cap_status == "executed" and isinstance(cap_result_obj, dict):
            write_kind = str(cap_result_obj.get("type") or "")
            if write_kind in {"workspace-memory-write", "workspace-file-write"}:
                write_path = str(cap_result_obj.get("path") or "").strip()
                bytes_written = cap_result_obj.get("bytes_written")
                bytes_before = cap_result_obj.get("bytes_before")
                bytes_delta = cap_result_obj.get("bytes_delta")
                fingerprint = str(cap_result_obj.get("content_fingerprint") or "").strip()
                fingerprint_before = str(cap_result_obj.get("content_fingerprint_before") or "").strip()
                readback_match = cap_result_obj.get("readback_match")
                readback_fp = str(cap_result_obj.get("readback_fingerprint") or "").strip()
                line_count: int | None = None
                if cap_result_text:
                    line_count = cap_result_text.count("\n") + 1
                header_parts: list[str] = [
                    f"WRITE_CONFIRMED path={write_path or 'unknown'}",
                    f"bytes={int(bytes_written) if isinstance(bytes_written, (int, float)) else 'unknown'}",
                ]
                if isinstance(bytes_before, (int, float)):
                    header_parts.append(f"bytes_before={int(bytes_before)}")
                if isinstance(bytes_delta, (int, float)):
                    header_parts.append(f"bytes_delta={int(bytes_delta):+d}")
                if line_count is not None:
                    header_parts.append(f"preview_lines={line_count}")
                if fingerprint:
                    header_parts.append(f"fingerprint={fingerprint[:16]}")
                if fingerprint_before and fingerprint_before != fingerprint:
                    header_parts.append(f"fingerprint_before={fingerprint_before[:16]}")
                # Readback verification — Jarvis can see disk truth, not
                # just a write-side claim. If readback failed, this
                # surfaces the mismatch loudly.
                if readback_match is True:
                    header_parts.append("readback=verified")
                elif readback_match is False:
                    header_parts.append("readback=MISMATCH")
                    if readback_fp:
                        header_parts.append(f"readback_fingerprint={readback_fp[:16]}")
                header_parts.append(
                    "status=persisted" if readback_match is not False else "status=persisted-but-mismatched"
                )
                confirmation_header = " | ".join(header_parts)
                cap_result_text = (
                    f"{confirmation_header}\n--- preview ---\n{cap_result_text}"
                    if cap_result_text
                    else confirmation_header
                )

        _update_visible_execution_trace(
            run,
            {
                "invoke_status": cap_status,
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

        capability_results.append({
            "capability_id": cap_id,
            "status": cap_status,
            "execution_mode": cap_exec_mode,
            "result_text": cap_result_text,
            "detail": cap_detail,
            "invocation": capability_result,
        })

        if cap_status == "executed":
            any_executed = True

        set_last_visible_capability_use(
            run,
            capability_id=cap_id,
            invocation=capability_result,
            capability_arguments=cap_args,
            argument_source=_merge_argument_sources(target_source, command_source),
        )

        event_bus.publish(
            "runtime.visible_run_capability_used",
            {
                "run_id": run.run_id,
                "lane": run.lane,
                "provider": run.provider,
                "model": run.model,
                "capability_id": cap_id,
                "status": cap_status,
                "execution_mode": cap_exec_mode,
            },
        )

        capability_events.append(
            {
                "type": "capability",
                "run_id": run.run_id,
                "capability_id": cap_id,
                "status": cap_status,
                "execution_mode": cap_exec_mode,
                "target_path": resolved_target_path or None,
                "command_text": resolved_command_text or None,
                "capability_name": (
                    (capability_result.get("capability") or {}).get("name")
                    or cap_id
                ),
            }
        )

    return capability_results, any_executed, capability_events


def _planned_visible_capability_steps(
    run: VisibleRun,
    *,
    all_capabilities: list[dict[str, object]],
    step_offset: int,
) -> list[dict[str, object]]:
    planned_steps: list[dict[str, object]] = []

    for index, cap_entry in enumerate(all_capabilities, start=1):
        cap_id = str(cap_entry.get("capability_id") or "")
        cap_args = dict(cap_entry.get("arguments") or {})
        resolved_target_path, _target_source = _resolve_visible_capability_target_path(
            capability_id=cap_id,
            capability_arguments=cap_args,
            user_message=run.user_message,
        )
        resolved_command_text, _command_source = _resolve_visible_capability_command_text(
            capability_id=cap_id,
            capability_arguments=cap_args,
            user_message=run.user_message,
        )
        action, detail = _visible_capability_step_description(
            capability_id=cap_id,
            target_path=resolved_target_path,
            command_text=resolved_command_text,
        )
        planned_steps.append(
            {
                "type": "working_step",
                "run_id": run.run_id,
                "action": action,
                "detail": detail,
                "step": step_offset + index,
                "status": "running",
            }
        )

    return planned_steps


def _visible_capability_step_description(
    *,
    capability_id: str,
    target_path: str | None,
    command_text: str | None,
) -> tuple[str, str]:
    normalized_id = capability_id.lower()
    normalized_command = str(command_text or "").strip()
    normalized_target = str(target_path or "").strip()

    if normalized_target and any(token in normalized_id for token in ("write", "edit", "patch", "memory")):
        return "editing", f"Editing {normalized_target}"
    if normalized_target and any(token in normalized_id for token in ("list", "dir", "folder")):
        return "browsing", f"Browsing {normalized_target}"
    if normalized_target:
        return "reading", f"Reading {normalized_target}"
    if normalized_command:
        return "running", f"Running {normalized_command}"
    return "tool", f"Using {capability_id}"


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
    if str(capability.get("execution_mode") or "") not in {"external-file-read", "external-dir-list"}:
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
    interruption = _classify_visible_run_interruption(
        (
            (get_last_visible_execution_trace() or {}).get("provider_error_summary")
            or bounded_error
        )
    )
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
    _set_orb_phase("idle")
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
            **interruption,
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
    shared = _get_visible_run_control(run.run_id)
    finished_at = datetime.now(UTC).isoformat()
    interruption = _classify_visible_run_interruption(
        str(
            (get_last_visible_execution_trace() or {}).get("provider_error_summary")
            or "cancelled"
        )
    )
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
    _set_orb_phase("idle")
    yield _sse("trace", _visible_trace_payload(run))
    event_bus.publish(
        "runtime.visible_run_cancelled",
        {
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": run.provider,
            "model": run.model,
            "status": "cancelled",
            "started_at": controller.started_at if controller else shared.get("started_at"),
            "finished_at": finished_at,
            **interruption,
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
    started_at = datetime.now(UTC).isoformat()
    controller = VisibleRunController(
        run_id=run.run_id,
        lane=run.lane,
        provider=run.provider,
        model=run.model,
        started_at=started_at,
        user_message_preview=_preview_text(run.user_message),
    )
    _VISIBLE_RUN_CONTROLLERS[run.run_id] = controller
    state = {
        "active": True,
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "started_at": started_at,
        "current_user_message_preview": controller.user_message_preview,
        "capability_id": None,
        "cancelled": False,
        "updated_at": started_at,
    }
    _set_visible_run_control(run.run_id, state)
    _set_active_visible_run(state)
    return controller


def get_visible_run_controller(run_id: str) -> VisibleRunController | None:
    return _VISIBLE_RUN_CONTROLLERS.get(run_id)


def cancel_visible_run(run_id: str) -> bool:
    controller = get_visible_run_controller(run_id)
    shared = _get_visible_run_control(run_id)
    if controller is None and not shared:
        return False
    _mark_visible_run_cancelled(run_id)
    if controller is not None:
        controller.cancel()
    return True


def unregister_visible_run(run_id: str) -> None:
    controller = _VISIBLE_RUN_CONTROLLERS.pop(run_id, None)
    state = _get_visible_run_control(run_id)
    if state:
        state["active"] = False
        state["updated_at"] = datetime.now(UTC).isoformat()
        _set_visible_run_control(run_id, state)
    active = _get_active_visible_run_state()
    if str(active.get("run_id") or "") == run_id:
        _set_active_visible_run({})
    if controller is not None:
        controller.clear_stream()


def get_active_visible_run() -> dict[str, str] | None:
    active = _get_active_visible_run_state()
    if not active:
        return None
    if not bool(active.get("active", True)):
        return None
    return {
        "active": True,
        "run_id": str(active.get("run_id") or ""),
        "lane": str(active.get("lane") or ""),
        "provider": str(active.get("provider") or ""),
        "model": str(active.get("model") or ""),
        "started_at": str(active.get("started_at") or ""),
        "current_user_message_preview": str(active.get("current_user_message_preview") or ""),
        "capability_id": active.get("capability_id"),
        "cancelled": bool(active.get("cancelled")),
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
    state = _get_visible_run_control(run.run_id)
    if state:
        state["capability_id"] = capability_id
        state["updated_at"] = datetime.now(UTC).isoformat()
        _set_visible_run_control(run.run_id, state)
        active = _get_active_visible_run_state()
        if str(active.get("run_id") or "") == run.run_id:
            _set_active_visible_run({**active, "capability_id": capability_id, "updated_at": state["updated_at"]})
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
    shared = _get_visible_run_control(run.run_id)
    started_at = controller.started_at if controller else shared.get("started_at")
    capability_id = controller.last_capability_id if controller else shared.get("capability_id")
    user_message_preview = controller.user_message_preview if controller else shared.get("current_user_message_preview")
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

    # --- Cognitive Architecture: fire-and-forget post-run updates ---
    _update_cognitive_systems_async(
        run_id=run.run_id,
        user_message=user_message_preview or "",
        assistant_response=work_preview or "",
        outcome_status=status,
    )


def _update_cognitive_systems_async(
    *,
    run_id: str,
    user_message: str,
    assistant_response: str,
    outcome_status: str,
) -> None:
    """Fire-and-forget updates to all cognitive accumulation systems."""
    import threading

    def _run() -> None:
        try:
            from apps.api.jarvis_api.services.personality_vector import (
                update_personality_vector_async,
            )
            update_personality_vector_async(
                run_id=run_id,
                user_message=user_message,
                assistant_response=assistant_response,
                outcome_status=outcome_status,
            )
        except Exception:
            pass

        try:
            from apps.api.jarvis_api.services.taste_profile import update_taste_async
            # Detect correction: user message contains correction markers
            msg_lower = user_message.lower()
            was_corrected = any(
                m in msg_lower
                for m in ("nej", "forkert", "ikke det", "det er stadig", "prøv igen")
            )
            update_taste_async(
                run_id=run_id,
                user_message=user_message,
                was_corrected=was_corrected,
                outcome_status=outcome_status,
            )
        except Exception:
            pass

        try:
            from apps.api.jarvis_api.services.relationship_texture import (
                update_relationship_async,
            )
            update_relationship_async(
                run_id=run_id,
                user_message=user_message,
                assistant_response=assistant_response,
                outcome_status=outcome_status,
            )
        except Exception:
            pass

        try:
            from apps.api.jarvis_api.services.habit_tracker import track_habit_from_run
            # Use first 50 chars of user message as task signature
            sig = user_message[:50].strip() if user_message else ""
            if sig:
                track_habit_from_run(
                    run_id=run_id,
                    task_signature=sig,
                    outcome_status=outcome_status,
                )
        except Exception:
            pass

        try:
            from apps.api.jarvis_api.services.shared_language import scan_for_shared_terms
            scan_for_shared_terms(
                user_message=user_message,
                assistant_response=assistant_response,
                run_id=run_id,
            )
        except Exception:
            pass

        try:
            from apps.api.jarvis_api.services.rhythm_engine import update_rhythm_state
            update_rhythm_state()
        except Exception:
            pass

        # --- User emotional resonance ---
        detected_mood = "neutral"
        try:
            from apps.api.jarvis_api.services.user_emotional_resonance import detect_user_mood
            mood_result = detect_user_mood(
                user_message=user_message,
                run_id=run_id,
            )
            detected_mood = mood_result.get("detected_mood", "neutral")
        except Exception:
            pass

        # --- Experiential memory ---
        try:
            from apps.api.jarvis_api.services.experiential_memory import (
                create_experiential_memory_async,
            )
            create_experiential_memory_async(
                run_id=run_id,
                user_message=user_message,
                assistant_response=assistant_response,
                outcome_status=outcome_status,
                user_mood=detected_mood,
            )
        except Exception:
            pass

        # --- Auto-seed planting from conversation ---
        try:
            from apps.api.jarvis_api.services.seed_system import auto_plant_seeds_from_conversation
            auto_plant_seeds_from_conversation(user_message=user_message)
        except Exception:
            pass

        # --- Self-surprise detection ---
        try:
            from apps.api.jarvis_api.services.self_surprise_detection import detect_self_surprise
            detect_self_surprise(
                expected_confidence=0.6,  # baseline expectation
                actual_outcome=outcome_status,
                domain=user_message[:30],
                run_id=run_id,
            )
        except Exception:
            pass

        # --- Gratitude tracking ---
        try:
            from apps.api.jarvis_api.services.gratitude_tracker import detect_gratitude_from_interaction
            msg_lower = user_message.lower()
            was_corrected = any(m in msg_lower for m in ("nej", "forkert", "ikke det"))
            detect_gratitude_from_interaction(
                user_mood=detected_mood,
                outcome_status=outcome_status,
                was_corrected=was_corrected,
            )
        except Exception:
            pass

        # --- Value formation ---
        try:
            from apps.api.jarvis_api.services.value_formation import detect_value_from_outcome
            detect_value_from_outcome(
                action_type="visible_run",
                outcome_status=outcome_status,
                user_mood=detected_mood,
            )
        except Exception:
            pass

        # --- Flow state update ---
        try:
            from apps.api.jarvis_api.services.flow_state_detection import update_flow_detection
            msg_lower = user_message.lower()
            corrections = sum(1 for m in ("nej", "forkert", "prøv igen") if m in msg_lower)
            update_flow_detection(
                recent_outcomes=[outcome_status],
                correction_count=corrections,
            )
        except Exception:
            pass

        # --- HJERTESLAG: Cadence producers (vække døde signaler) ---
        try:
            from apps.api.jarvis_api.services.cadence_producers import (
                produce_signals_from_run,
                detect_decision_in_message,
            )
            produce_signals_from_run(
                run_id=run_id,
                session_id=None,  # session_id not in scope here
                user_message=user_message,
                assistant_response=assistant_response,
                outcome_status=outcome_status,
                user_mood=detected_mood,
            )
            detect_decision_in_message(
                user_message=user_message,
                assistant_response=assistant_response,
                run_id=run_id,
            )
        except Exception:
            pass

        # --- Counterfactual auto-generation (bredere triggers) ---
        try:
            from apps.api.jarvis_api.services.counterfactual_engine import generate_counterfactual
            msg_lower = user_message.lower()
            was_corrected_local = any(m in msg_lower for m in ("nej", "forkert", "ikke det"))
            if outcome_status in ("failed", "error"):
                generate_counterfactual(
                    trigger_type="failed_run",
                    anchor=user_message[:80],
                    confidence=0.6,
                )
            elif was_corrected_local:
                generate_counterfactual(
                    trigger_type="correction",
                    anchor=user_message[:80],
                    confidence=0.5,
                )
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


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
