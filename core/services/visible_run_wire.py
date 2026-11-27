"""Legacy visible-run SSE encoding, extracted from visible_runs.py.

Keep serialization and presentation protocol at the wire boundary rather
than duplicating marker stripping in individual channel consumers.
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def explicit_answer_stream(function):
    """Turn the model's marker into one boundary event for every channel.

    The source accumulator retains the declaration for canonical persistence;
    consumers receive only clean prose and the explicit event. No length test.
    """
    from functools import wraps
    from core.services.code_answer_boundary import strip_answer_markers
    from core.services.answer_declaration import AnswerDeclarationStream

    @wraps(function)
    async def wrapped(*args, **kwargs):
        scanner = AnswerDeclarationStream()
        source = function(*args, **kwargs)
        run_id = str(getattr(args[0], "run_id", "") if args else "")
        def encode(parts, payload):
            for kind, value in parts:
                if kind == "answer_start":
                    yield _sse("answer_start", {"type": "answer_start", "run_id": run_id})
                else:
                    yield _sse("delta", {**payload, "delta": value})

        try:
            async for chunk in source:
                lines = chunk.splitlines()
                event = next((line[7:] for line in lines if line.startswith("event: ")), "")
                raw = next((line[6:] for line in lines if line.startswith("data: ")), "")
                if event == "delta":
                    payload = json.loads(raw)
                    run_id = str(payload.get("run_id") or run_id)
                    before = scanner.rejected
                    for part in encode(scanner.feed(str(payload.get("delta") or "")), payload):
                        yield part
                    if scanner.rejected > before:
                        logger.info("answer-declaration-rejected: work_opening run=%s", run_id)
                    continue
                if event == "done":
                    for part in encode(scanner.flush(), {"type": "delta", "run_id": run_id}):
                        yield part
                    payload = json.loads(raw)
                    for key in ("text", "content", "response"):
                        if isinstance(payload.get(key), str):
                            payload[key] = strip_answer_markers(payload[key])
                    yield _sse(event, payload)
                    continue
                # A new model round starts a new prose line even when the
                # previous synthesis had no trailing newline. Never carry a
                # half marker or a code-fence context across tool boundaries.
                if event == "working_step":
                    payload = json.loads(raw)
                    if payload.get("action") == "thinking" and not payload.get("tool_id"):
                        for part in encode(scanner.flush(), {"type": "delta", "run_id": run_id}):
                            yield part
                        scanner.reset_round()
                yield chunk
        finally:
            await source.aclose()

    return wrapped
