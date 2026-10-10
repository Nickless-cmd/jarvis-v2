"""One-shot subprocess execution with best-effort incremental output."""
from __future__ import annotations

import codecs
from contextvars import copy_context
from dataclasses import dataclass
import logging
import subprocess
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StreamingProcessResult:
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    first_output_ms: int | None
    process_ms: int


def run_streaming(
    argv: list[str],
    *,
    cwd: str,
    timeout_s: float,
    on_output: Callable[[str, str], None] | None,
) -> StreamingProcessResult:
    started = time.monotonic()
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    collected: dict[str, list[bytes]] = {"stdout": [], "stderr": []}
    first_output: list[float | None] = [None]
    timing_lock = threading.Lock()

    def read_stream(stream_name: str, pipe) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        while True:
            chunk = pipe.read(4096)
            if not chunk:
                break
            collected[stream_name].append(chunk)
            with timing_lock:
                if first_output[0] is None:
                    first_output[0] = time.monotonic()
            text = decoder.decode(chunk, final=False)
            if text and on_output is not None:
                try:
                    on_output(stream_name, text)
                except Exception as exc:
                    logger.debug("streaming subprocess output callback failed: %s", exc)
        tail = decoder.decode(b"", final=True)
        if tail and on_output is not None:
            try:
                on_output(stream_name, tail)
            except Exception as exc:
                logger.debug("streaming subprocess output callback failed: %s", exc)

    threads = []
    for name, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
        assert pipe is not None
        context = copy_context()
        thread = threading.Thread(
            target=context.run,
            args=(read_stream, name, pipe),
            name=f"streaming-subprocess-{name}",
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    timed_out = False
    try:
        exit_code = process.wait(timeout=max(0.01, float(timeout_s)))
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        exit_code = process.wait()
    for thread in threads:
        thread.join()
    ended = time.monotonic()

    return StreamingProcessResult(
        stdout=b"".join(collected["stdout"]).decode("utf-8", errors="replace"),
        stderr=b"".join(collected["stderr"]).decode("utf-8", errors="replace"),
        exit_code=exit_code,
        timed_out=timed_out,
        first_output_ms=(
            None
            if first_output[0] is None
            else max(0, round((first_output[0] - started) * 1000))
        ),
        process_ms=max(0, round((ended - started) * 1000)),
    )
