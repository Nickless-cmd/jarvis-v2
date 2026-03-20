from __future__ import annotations

import json
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
    controller = register_visible_run(run.run_id)
    event_bus.publish(
        "runtime.visible_run_started",
        {
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": run.provider,
            "model": run.model,
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

        if controller.is_cancelled():
            set_last_visible_run_outcome(
                run,
                status="cancelled",
            )
            for cancelled_chunk in _cancel_visible_run(run):
                yield cancelled_chunk
            return

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
        event_bus.publish(
            "runtime.visible_run_completed",
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
        set_last_visible_run_outcome(
            run,
            status="completed",
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


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _fail_visible_run(run: VisibleRun, error_message: str) -> AsyncIterator[str]:
    event_bus.publish(
        "runtime.visible_run_failed",
        {
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": run.provider,
            "model": run.model,
            "error": error_message,
        },
    )
    yield _sse(
        "failed",
        {
            "type": "failed",
            "run_id": run.run_id,
            "status": "failed",
            "error": error_message,
        },
    )
    yield _sse(
        "done",
        {
            "type": "done",
            "run_id": run.run_id,
            "status": "failed",
            "error": error_message,
        },
    )


def _cancel_visible_run(run: VisibleRun) -> AsyncIterator[str]:
    event_bus.publish(
        "runtime.visible_run_cancelled",
        {
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": run.provider,
            "model": run.model,
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


def register_visible_run(run_id: str) -> VisibleRunController:
    controller = VisibleRunController(run_id=run_id)
    _VISIBLE_RUN_CONTROLLERS[run_id] = controller
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
        "cancelled": controller.is_cancelled(),
    }


def get_last_visible_run_outcome() -> dict[str, str] | None:
    return dict(_LAST_VISIBLE_RUN_OUTCOME) if _LAST_VISIBLE_RUN_OUTCOME else None


def set_last_visible_run_outcome(
    run: VisibleRun,
    *,
    status: str,
    error: str | None = None,
) -> None:
    global _LAST_VISIBLE_RUN_OUTCOME
    outcome = {
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "status": status,
    }
    if error:
        outcome["error"] = error
    _LAST_VISIBLE_RUN_OUTCOME = outcome
