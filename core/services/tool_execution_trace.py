"""Process-local timing and bounded live-output state for visible tool calls.

The final tool result remains authoritative.  This module only measures its
journey to the UI and carries a lossy, ephemeral output projection while the
call is running.
"""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
import logging
import threading
import time
from typing import Any, Iterator


@dataclass(frozen=True, slots=True)
class OutputDelta:
    tool_use_id: str
    stream: str
    seq: int
    chunk: str
    truncated: bool = False


class BoundedOutputBuffer:
    """Thread-safe non-blocking queue that drops oldest output under pressure."""

    def __init__(self, max_frames: int = 128, max_pending_chars: int = 64 * 1024):
        if max_frames < 1 or max_pending_chars < 1:
            raise ValueError("output buffer limits must be positive")
        self._max_frames = int(max_frames)
        self._max_pending_chars = int(max_pending_chars)
        self._frames: deque[OutputDelta] = deque()
        self._pending_chars = 0
        self._lock = threading.Lock()

    def put(self, delta: OutputDelta) -> None:
        chunk = str(delta.chunk)
        truncated = bool(delta.truncated)
        if len(chunk) > self._max_pending_chars:
            chunk = chunk[-self._max_pending_chars :]
            truncated = True
        item = replace(delta, chunk=chunk, truncated=truncated)
        with self._lock:
            dropped = False
            while self._frames and (
                len(self._frames) >= self._max_frames
                or self._pending_chars + len(item.chunk) > self._max_pending_chars
            ):
                old = self._frames.popleft()
                self._pending_chars -= len(old.chunk)
                dropped = True
            if dropped and not item.truncated:
                item = replace(item, truncated=True)
            self._frames.append(item)
            self._pending_chars += len(item.chunk)

    def drain(self) -> list[OutputDelta]:
        with self._lock:
            items = list(self._frames)
            self._frames.clear()
            self._pending_chars = 0
        return items


@dataclass(slots=True)
class _ExecutionBinding:
    tool_use_id: str
    output_buffer: BoundedOutputBuffer | None
    next_seq: int = 1
    lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass(slots=True)
class _CallTrace:
    tool_use_id: str
    tool: str
    run_id: str
    announced_at: float
    dispatched_at: float | None = None
    execution_completed_at: float | None = None
    approval_wait_started_at: float | None = None
    approved_dispatched_at: float | None = None
    executor_timing: dict[str, Any] = field(default_factory=dict)


_CURRENT_EXECUTION: ContextVar[_ExecutionBinding | None] = ContextVar(
    "tool_execution_binding", default=None
)
_TRACES: dict[str, _CallTrace] = {}
_TRACES_LOCK = threading.Lock()
logger = logging.getLogger(__name__)


def _timing_enabled() -> bool:
    from core.runtime.settings import load_settings

    try:
        enabled = load_settings().tool_execution_timing_enabled
    except Exception as exc:
        logger.warning("tool timing settings unavailable; keeping timing on: %s", exc)
        return True
    return bool(enabled)


def _milliseconds(start: float | None, end: float | None) -> int | None:
    if start is None or end is None:
        return None
    return max(0, round((end - start) * 1000))


def start_call(
    tool_use_id: str,
    *,
    tool: str,
    run_id: str,
    announced_at: float | None = None,
) -> None:
    if not tool_use_id or not _timing_enabled():
        return
    item = _CallTrace(
        tool_use_id=str(tool_use_id),
        tool=str(tool),
        run_id=str(run_id),
        announced_at=time.monotonic() if announced_at is None else announced_at,
    )
    with _TRACES_LOCK:
        _TRACES[item.tool_use_id] = item


def mark_dispatch(tool_use_id: str, *, now: float | None = None) -> None:
    with _TRACES_LOCK:
        item = _TRACES.get(str(tool_use_id))
        if item is not None and item.dispatched_at is None:
            item.dispatched_at = time.monotonic() if now is None else now


def mark_execution_complete(tool_use_id: str, *, now: float | None = None) -> None:
    with _TRACES_LOCK:
        item = _TRACES.get(str(tool_use_id))
        if item is not None and item.execution_completed_at is None:
            item.execution_completed_at = time.monotonic() if now is None else now


def mark_approval_wait(tool_use_id: str, *, now: float | None = None) -> None:
    with _TRACES_LOCK:
        item = _TRACES.get(str(tool_use_id))
        if item is not None and item.approval_wait_started_at is None:
            item.approval_wait_started_at = time.monotonic() if now is None else now


def mark_approved_dispatch(tool_use_id: str, *, now: float | None = None) -> None:
    with _TRACES_LOCK:
        item = _TRACES.get(str(tool_use_id))
        if item is not None and item.approved_dispatched_at is None:
            item.approved_dispatched_at = time.monotonic() if now is None else now


def note_executor_timing(tool_use_id: str, timing: dict[str, Any] | None) -> None:
    if not timing:
        return
    allowed = {
        "route",
        "dispatch_to_lock_ms",
        "dispatch_to_spawn_ms",
        "first_output_ms",
        "process_ms",
        "had_output",
    }
    with _TRACES_LOCK:
        item = _TRACES.get(str(tool_use_id))
        if item is not None:
            item.executor_timing.update({key: timing[key] for key in allowed if key in timing})


def _finish(
    tool_use_id: str,
    *,
    status: str,
    exit_code: int | None,
    now: float | None,
) -> None:
    ended_at = time.monotonic() if now is None else now
    with _TRACES_LOCK:
        item = _TRACES.pop(str(tool_use_id), None)
    if item is None:
        return
    measured = item.executor_timing
    payload = {
        "tool": item.tool,
        "run_id": item.run_id,
        "tool_use_id": item.tool_use_id,
        "route": measured.get("route"),
        "status": str(status),
        "exit_code": exit_code,
        "had_output": measured.get("had_output"),
        "announced_to_dispatch_ms": _milliseconds(item.announced_at, item.dispatched_at),
        "dispatch_to_lock_ms": measured.get("dispatch_to_lock_ms"),
        "dispatch_to_spawn_ms": measured.get("dispatch_to_spawn_ms"),
        "first_output_ms": measured.get("first_output_ms"),
        "process_ms": measured.get("process_ms"),
        "process_exit_to_result_emit_ms": _milliseconds(item.execution_completed_at, ended_at),
        "approval_wait_ms": _milliseconds(
            item.approval_wait_started_at, item.approved_dispatched_at
        ),
        "approved_dispatch_to_result_ms": _milliseconds(
            item.approved_dispatched_at, ended_at
        ),
        "total_visible_ms": _milliseconds(item.announced_at, ended_at),
    }
    from core.tools.tool_call_telemetry import udgiv_execution_timing

    udgiv_execution_timing(payload)


def surface_result(
    tool_use_id: str,
    *,
    status: str,
    exit_code: int | None = None,
    now: float | None = None,
) -> None:
    _finish(tool_use_id, status=status, exit_code=exit_code, now=now)


def cancel_call(tool_use_id: str, *, now: float | None = None) -> None:
    _finish(tool_use_id, status="cancelled", exit_code=None, now=now)


@contextmanager
def bind_execution(
    tool_use_id: str, output_buffer: BoundedOutputBuffer | None
) -> Iterator[None]:
    token = _CURRENT_EXECUTION.set(_ExecutionBinding(str(tool_use_id), output_buffer))
    try:
        yield
    finally:
        _CURRENT_EXECUTION.reset(token)


def emit_current_output(
    stream: str,
    chunk: str,
    seq: int | None = None,
    truncated: bool = False,
) -> None:
    binding = _CURRENT_EXECUTION.get()
    if binding is None or binding.output_buffer is None or not chunk:
        return
    with binding.lock:
        actual_seq = binding.next_seq if seq is None else int(seq)
        if seq is None:
            binding.next_seq += 1
        else:
            binding.next_seq = max(binding.next_seq, actual_seq + 1)
    binding.output_buffer.put(
        OutputDelta(
            binding.tool_use_id, str(stream), actual_seq, str(chunk), bool(truncated)
        )
    )
