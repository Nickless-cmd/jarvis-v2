"""Stream the existing tool-free final synthesis without buffering its deltas.

The visible run is async, while provider adapters expose a synchronous iterator.
The small queue is the boundary: the worker sends every provider delta as it
arrives and the run can immediately forward it as SSE. The final text remains
the same answer used for persistence.
"""

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator

from core.services import visible_followup, visible_text_scrub


@dataclass(frozen=True)
class SynthesisDelta:
    text: str


@dataclass(frozen=True)
class SynthesisDone:
    text: str


async def stream_final_synthesis(
    *,
    provider: str,
    model: str,
    base_messages: list[dict],
    exchanges: list[visible_followup.ToolExchange],
    min_chars: int = 1,
) -> AsyncIterator[SynthesisDelta | SynthesisDone]:
    """Yield clean text deltas, then the exact text the caller should persist.

    ``min_chars`` holds short candidates until they become worth showing. The
    post-tool answer guard uses the same threshold as its replacement check;
    an empty or one-word candidate therefore never leaks to the chat.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

    def enqueue(kind: str, text: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, (kind, text))

    def worker() -> None:
        try:
            result = visible_followup.synthesize_final_answer(
                provider=provider,
                model=model,
                base_messages=base_messages,
                exchanges=exchanges,
                on_delta=lambda delta: enqueue("delta", delta),
            )
        except Exception:
            result = ""
        enqueue("done", result)

    task = asyncio.create_task(asyncio.to_thread(worker))
    scrubber = visible_text_scrub.StroemSkrubber()
    emitted = ""
    held = ""
    released = False
    try:
        while True:
            kind, value = await queue.get()
            if kind == "delta":
                held += scrubber.foed(value)
                if len((emitted + held).strip()) >= min_chars:
                    chunk = held.lstrip() if not released else held
                    held = ""
                    released = True
                    if chunk:
                        emitted += chunk
                        yield SynthesisDelta(chunk)
                continue

            held += scrubber.skyl()
            streamed = (emitted + held).strip()
            completed = visible_text_scrub.fjern_interne_markoerer(value).strip()
            # The provider's Done normally repeats the deltas. If it adds a
            # suffix, forward that too; if it disagrees, keep the bytes the
            # user actually saw as the persisted answer.
            candidate = completed if completed and completed.startswith(streamed) else streamed
            if len(candidate.strip()) >= min_chars:
                remainder = candidate[len(emitted):]
                if remainder:
                    yield SynthesisDelta(remainder)
                yield SynthesisDone(candidate)
            else:
                yield SynthesisDone("")
            break
    finally:
        if task.done():
            await task
