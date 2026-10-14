"""Real subprocess fixture for cross-process run-stream integration tests."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from apps.api.jarvis_api.routes.internal_run_stream import router
from core.services import in_flight_runs, run_event_log


def build_app(args: argparse.Namespace) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    @app.on_event("startup")
    async def _start_producer() -> None:
        Path(args.counter).write_text("1\n", encoding="utf-8")
        in_flight_runs.mark_started(
            run_id=args.run_id,
            session_id=args.session_id,
            user_message="cross-process stream fixture",
            kind="autonomous",
        )
        run_event_log.create(args.run_id, args.session_id)

        async def _produce() -> None:
            await asyncio.sleep(0.8)
            run_event_log.append(
                args.run_id,
                'event: message_start\ndata: {"type":"message_start"}\n\n',
            )
            run_event_log.append(
                args.run_id,
                'event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"text":"alpha"}}\n\n',
            )
            Path(args.phase_one).write_text("ready\n", encoding="utf-8")
            for _ in range(200):
                if Path(args.proceed).exists():
                    break
                await asyncio.sleep(0.05)
            run_event_log.append(
                args.run_id,
                'event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"text":"beta"}}\n\n',
            )
            await asyncio.sleep(0.1)
            run_event_log.append(
                args.run_id,
                'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            )
            run_event_log.mark_done(args.run_id)
            in_flight_runs.settle_terminal(
                args.run_id,
                status="completed",
                reason="fixture-complete",
            )

        asyncio.create_task(_produce())

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--counter", required=True)
    parser.add_argument("--phase-one", required=True)
    parser.add_argument("--proceed", required=True)
    args = parser.parse_args()
    uvicorn.run(build_app(args), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
