from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from dataclasses import dataclass
from typing import AsyncIterator
from uuid import uuid4

from apps.api.jarvis_api.services.visible_model import (
    VisibleModelDelta,
    VisibleModelStreamCancelled,
    VisibleModelStreamDone,
    stream_visible_model,
)
from core.costing.ledger import record_cost
from core.eventbus.bus import event_bus
from core.runtime.settings import load_settings
from core.tools.workspace_capabilities import (
    invoke_workspace_capability,
    load_workspace_capabilities,
)

CAPABILITY_CALL_PATTERN = re.compile(
    r'^<capability-call id="(?P<capability_id>[a-z0-9:-]+)"\s*/>$'
)
CAPABILITY_CALL_PREFIX = '<capability-call id="'
CAPABILITY_CALL_SUFFIX = '" />'


@dataclass(slots=True)
class VisibleRun:
    run_id: str
    lane: str
    provider: str
    model: str
    user_message: str


@dataclass(slots=True)
class VisibleRunController:
    run_id: str
    lane: str
    provider: str
    model: str
    started_at: str
    cancelled: bool = False
    active_stream: object | None = None

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


def start_visible_run(message: str) -> AsyncIterator[str]:
    settings = load_settings()
    run = VisibleRun(
        run_id=f"visible-{uuid4().hex}",
        lane=settings.primary_model_lane,
        provider=settings.visible_model_provider,
        model=settings.visible_model_name,
        user_message=(message or "").strip() or "Tom synlig forespoergsel",
    )
    return _stream_visible_run(run)


async def _stream_visible_run(run: VisibleRun) -> AsyncIterator[str]:
    controller = register_visible_run(run)
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

    result = None
    visible_output_text = ""
    buffered_capability_text = ""
    buffering_capability_marker = False
    try:
        try:
            for item in stream_visible_model(
                message=run.user_message,
                provider=run.provider,
                model=run.model,
                controller=controller,
            ):
                if controller.is_cancelled():
                    for cancelled_chunk in _cancel_visible_run(run):
                        yield cancelled_chunk
                    return
                if isinstance(item, VisibleModelDelta):
                    candidate = (
                        f"{buffered_capability_text}{item.delta}"
                        if buffering_capability_marker
                        else item.delta
                    )
                    marker_state = _capability_call_state(candidate)
                    if buffering_capability_marker or marker_state != "invalid":
                        if marker_state == "invalid":
                            yield _sse(
                                "delta",
                                {
                                    "type": "delta",
                                    "run_id": run.run_id,
                                    "delta": candidate,
                                },
                            )
                            buffered_capability_text = ""
                            buffering_capability_marker = False
                            continue
                        buffered_capability_text = candidate
                        buffering_capability_marker = True
                        continue
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
                    break
        except VisibleModelStreamCancelled:
            set_last_visible_run_outcome(
                run,
                status="cancelled",
            )
            for cancelled_chunk in _cancel_visible_run(run):
                yield cancelled_chunk
            return
        except Exception as exc:
            set_last_visible_run_outcome(
                run,
                status="failed",
                error=str(exc) or "visible-run-failed",
            )
            for failure_chunk in _fail_visible_run(run, str(exc) or "visible-run-failed"):
                yield failure_chunk
            return

        if result is None:
            set_last_visible_run_outcome(
                run,
                status="failed",
                error="Visible model stream completed without final result",
            )
            for failure_chunk in _fail_visible_run(
                run, "Visible model stream completed without final result"
            ):
                yield failure_chunk
            return

        capability_call = _extract_capability_call(result.text)
        if buffering_capability_marker and not capability_call and buffered_capability_text:
            yield _sse(
                "delta",
                {
                    "type": "delta",
                    "run_id": run.run_id,
                    "delta": buffered_capability_text,
                },
            )
        buffered_capability_text = ""
        buffering_capability_marker = False

        if controller.is_cancelled():
            set_last_visible_run_outcome(
                run,
                status="cancelled",
            )
            for cancelled_chunk in _cancel_visible_run(run):
                yield cancelled_chunk
            return

        if capability_call and _is_runnable_workspace_capability(capability_call):
            capability_result = invoke_workspace_capability(capability_call)
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
            yield _sse(
                "delta",
                {
                    "type": "delta",
                    "run_id": run.run_id,
                    "delta": visible_output_text,
                },
            )
        else:
            visible_output_text = result.text

        record_cost(
            lane=run.lane,
            provider=run.provider,
            model=run.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=result.cost_usd,
        )
        event_bus.publish(
            "cost.recorded",
            {
                "run_id": run.run_id,
                "lane": run.lane,
                "provider": run.provider,
                "model": run.model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": result.cost_usd,
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
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": result.cost_usd,
            },
        )
        set_last_visible_run_outcome(
            run,
            status="completed",
            text_preview=_preview_text(visible_output_text),
        )
        yield _sse(
            "done",
            {
                "type": "done",
                "run_id": run.run_id,
                "status": "completed",
            },
        )
    finally:
        unregister_visible_run(run.run_id)


def _preview_text(text: str, limit: int = 120) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _extract_capability_call(text: str) -> str | None:
    match = CAPABILITY_CALL_PATTERN.fullmatch((text or "").strip())
    if not match:
        return None
    return match.group("capability_id")


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


def _is_runnable_workspace_capability(capability_id: str) -> bool:
    declared = load_workspace_capabilities().get("declared_capabilities", [])
    for capability in declared:
        if capability.get("capability_id") != capability_id:
            continue
        return bool(capability.get("runnable"))
    return False


def _capability_visible_text(*, capability_id: str, invocation: dict) -> str:
    status = str(invocation.get("status") or "unknown")
    execution_mode = str(invocation.get("execution_mode") or "unknown")
    result = invocation.get("result") or {}
    detail = str(invocation.get("detail") or "").strip()
    text = ""
    if isinstance(result, dict):
        text = str(result.get("text") or "").strip()

    if text:
        return (
            f"[Capability {capability_id} via {execution_mode}]\n"
            f"{text}"
        )
    if detail:
        return (
            f"[Capability {capability_id} via {execution_mode}]\n"
            f"{detail}"
        )
    return f"[Capability {capability_id} via {execution_mode}] {status}"


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
        "cancelled": controller.is_cancelled(),
    }


def get_last_visible_run_outcome() -> dict[str, str] | None:
    return dict(_LAST_VISIBLE_RUN_OUTCOME) if _LAST_VISIBLE_RUN_OUTCOME else None


def set_last_visible_run_outcome(
    run: VisibleRun,
    *,
    status: str,
    error: str | None = None,
    text_preview: str | None = None,
) -> None:
    global _LAST_VISIBLE_RUN_OUTCOME
    outcome = {
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "status": status,
        "finished_at": datetime.now(UTC).isoformat(),
    }
    if error:
        outcome["error"] = error
    if text_preview:
        outcome["text_preview"] = text_preview
    _LAST_VISIBLE_RUN_OUTCOME = outcome
