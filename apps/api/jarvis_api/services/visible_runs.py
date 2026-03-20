from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator
from uuid import uuid4

from apps.api.jarvis_api.services.visible_model import execute_visible_model
from core.costing.ledger import record_cost
from core.eventbus.bus import event_bus
from core.runtime.settings import load_settings


VISIBLE_PROVIDER = "phase1-runtime"
VISIBLE_MODEL = "visible-placeholder"


@dataclass(slots=True)
class VisibleRun:
    run_id: str
    lane: str
    provider: str
    model: str
    user_message: str


def start_visible_run(message: str) -> AsyncIterator[str]:
    settings = load_settings()
    run = VisibleRun(
        run_id=f"visible-{uuid4().hex}",
        lane=settings.primary_model_lane,
        provider=VISIBLE_PROVIDER,
        model=VISIBLE_MODEL,
        user_message=(message or "").strip() or "Tom synlig forespoergsel",
    )
    return _stream_visible_run(run)


async def _stream_visible_run(run: VisibleRun) -> AsyncIterator[str]:
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

    result = execute_visible_model(
        message=run.user_message,
        provider=run.provider,
        model=run.model,
    )
    for chunk in _chunk_text(result.text):
        yield _sse(
            "delta",
            {
                "type": "delta",
                "run_id": run.run_id,
                "delta": chunk,
            },
        )
        await asyncio.sleep(0.05)

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
    yield _sse(
        "done",
        {
            "type": "done",
            "run_id": run.run_id,
            "status": "completed",
        },
    )


def _chunk_text(text: str, size: int = 48) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
