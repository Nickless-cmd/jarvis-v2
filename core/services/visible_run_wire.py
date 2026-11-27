"""Legacy visible-run SSE encoding, extracted from visible_runs.py.

Keep serialization and presentation protocol at the wire boundary rather
than duplicating marker stripping in individual channel consumers.
"""
from __future__ import annotations

import json


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def explicit_answer_stream(function):
    """Turn the model's marker into one boundary event for every channel.

    The source accumulator retains the declaration for canonical persistence;
    consumers receive only clean prose and the explicit event. No length test.
    """
    from functools import wraps
    from core.services.code_answer_boundary import AnswerMarkerStream, strip_answer_markers

    @wraps(function)
    async def wrapped(*args, **kwargs):
        scanner = AnswerMarkerStream()
        source = function(*args, **kwargs)
        run_id = str(getattr(args[0], "run_id", "") if args else "")
        try:
            async for chunk in source:
                lines = chunk.splitlines()
                event = next((line[7:] for line in lines if line.startswith("event: ")), "")
                raw = next((line[6:] for line in lines if line.startswith("data: ")), "")
                if event == "delta":
                    payload = json.loads(raw)
                    run_id = str(payload.get("run_id") or run_id)
                    for kind, value in scanner.feed(str(payload.get("delta") or "")):
                        if kind == "answer_start":
                            yield _sse("answer_start", {"type": "answer_start", "run_id": run_id})
                        else:
                            yield _sse("delta", {**payload, "delta": value})
                    continue
                if event == "done":
                    for kind, value in scanner.flush():
                        yield _sse("delta", {"type": "delta", "run_id": run_id, "delta": value})
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
                        for kind, value in scanner.flush():
                            yield _sse("delta", {"type": "delta", "run_id": run_id, "delta": value})
                        scanner.line_start = True
                        scanner.line_prefix = ""
                        scanner.fence = ""
                yield chunk
        finally:
            await source.aclose()

    return wrapped
