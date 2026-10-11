"""Incremental adapters from canonical background jobs to live job events."""
from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Awaitable, Callable

from core.services import live_job_events


SnapshotReader = Callable[[], dict[str, Any]]
OperatorReader = Callable[..., Awaitable[dict[str, Any]]]


def _run(coro: Awaitable[dict[str, Any]]) -> dict[str, Any]:
    """Run one bridge coroutine from the pump's synchronous worker context."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:  # ingen aktiv loop: asyncio.run er den direkte vej
        return asyncio.run(coro)
    result: list[dict[str, Any]] = []
    failure: list[BaseException] = []

    def worker() -> None:
        try:
            result.append(asyncio.run(coro))
        except BaseException as exc:  # propagated to the caller below
            failure.append(exc)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join()
    if failure:
        raise failure[0]
    return result[0]


class LiveJobSourcePump:
    """Sample server/operator logs while a live Desk subscriber exists."""

    def __init__(
        self,
        *,
        snapshot_reader: SnapshotReader,
        user_id: str,
        operator_reader: OperatorReader | None = None,
    ) -> None:
        if operator_reader is None:
            from core.tools.operator_background import read_many_async

            operator_reader = read_many_async
        self._snapshot_reader = snapshot_reader
        self._operator_reader = operator_reader
        self._user_id = str(user_id or "")
        self._jobs: dict[tuple[str, str], dict[str, Any]] = {}
        self._offsets: dict[tuple[str, str], int] = {}
        self._finished: set[tuple[str, str]] = set()
        self._operator_healthy: bool | None = None
        self._subscribers = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _publish(self, event_type: str, source: str, job: dict[str, Any],
                 payload: dict[str, Any]) -> None:
        live_job_events.publish(
            event_type,
            job_key=str(job.get("id") or ""),
            session_id=str(job.get("session_id") or ""),
            source=source,
            payload=payload,
        )

    def _reconcile(self) -> None:
        snapshot = self._snapshot_reader()
        bridge_ok = bool(snapshot.get("bridge_ok", True))
        if not bridge_ok and self._operator_healthy is not False:
            live_job_events.publish(
                "source_status", job_key="operator", session_id="",
                source="operator",
                payload={"healthy": False, "error": "operator bridge unavailable"},
            )
            self._operator_healthy = False
        seen: set[tuple[str, str]] = set()
        for job in snapshot.get("jobs") or []:
            source = str(job.get("kilde") or "")
            if source not in {"supervisor", "operator"}:
                continue
            key = (source, str(job.get("id") or ""))
            if not key[1]:
                continue
            seen.add(key)
            if key in self._finished and not self._terminal(job):
                self._finished.discard(key)
            if key not in self._jobs:
                self._jobs[key] = dict(job)
                self._offsets[key] = 0
                if key not in self._finished:
                    self._publish("job_started", source, job, {"job": dict(job)})
            else:
                self._jobs[key] = dict(job)
        for key in set(self._jobs) - seen:
            if key in self._finished:
                self._jobs.pop(key, None)
                self._offsets.pop(key, None)
                self._finished.discard(key)

    @staticmethod
    def _terminal(job: dict[str, Any], *, running: bool | None = None) -> bool:
        if running is not None:
            return not running
        return str(job.get("status") or "") not in {"running", "paused", "active"}

    def _finish(self, key: tuple[str, str], job: dict[str, Any],
                exit_code: int | None) -> None:
        if key in self._finished:
            return
        self._finished.add(key)
        self._publish("job_finished", key[0], job, {
            "job": {k: v for k, v in job.items() if not k.startswith("_")},
            "status": str(job.get("status") or "exited"),
            "exit_code": exit_code,
        })

    def _sample_server(self) -> None:
        from core.services.process_supervisor import read_process_log_since

        for key, job in list(self._jobs.items()):
            if key[0] != "supervisor" or key in self._finished:
                continue
            result = read_process_log_since(key[1], self._offsets.get(key, 0))
            if result.get("status") == "ok":
                self._offsets[key] = int(result.get("offset") or 0)
                output = str(result.get("output") or "")
                if output:
                    self._publish("job_output", "supervisor", job, {
                        "stream": "combined", "chunk": output,
                        "offset": self._offsets[key],
                        "truncated": bool(result.get("truncated")),
                    })
            if self._terminal(job):
                self._finish(key, job, job.get("exit_code"))

    def _sample_operator(self) -> None:
        active = {
            key[1]: self._offsets.get(key, 0)
            for key, job in self._jobs.items()
            if key[0] == "operator" and key not in self._finished
        }
        if not active:
            return
        try:
            result = _run(self._operator_reader(
                offsets=active, user_id=self._user_id, max_bytes_per_job=32768,
            ))
        except Exception as exc:
            if self._operator_healthy is not False:
                live_job_events.publish(
                    "source_status", job_key="operator", session_id="",
                    source="operator",
                    payload={"healthy": False, "error": str(exc)},
                )
            self._operator_healthy = False
            return
        if self._operator_healthy is False:
            live_job_events.publish(
                "source_status", job_key="operator", session_id="",
                source="operator", payload={"healthy": True},
            )
        self._operator_healthy = True
        for job_id, item in (result.get("jobs") or {}).items():
            key = ("operator", str(job_id))
            job = self._jobs.get(key)
            if job is None:
                continue
            self._offsets[key] = int(item.get("offset") or self._offsets.get(key, 0))
            output = str(item.get("output") or "")
            if output:
                self._publish("job_output", "operator", job, {
                    "stream": "combined", "chunk": output,
                    "offset": self._offsets[key],
                    "truncated": bool(item.get("truncated")),
                })
            if self._terminal(job, running=bool(item.get("running"))):
                self._finish(key, job, item.get("exit_code"))

    def sample_once(self) -> None:
        """Force one reconciliation and one sample of both machine sources."""
        self._reconcile()
        self._sample_server()
        self._sample_operator()

    def add_subscriber(self) -> None:
        with self._lock:
            self._subscribers += 1
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop, daemon=True, name="live-job-sources",
            )
            self._thread.start()

    def remove_subscriber(self) -> None:
        with self._lock:
            self._subscribers = max(0, self._subscribers - 1)
            if self._subscribers == 0:
                self._stop.set()

    def _loop(self) -> None:
        next_reconcile = 0.0
        next_server = 0.0
        next_operator = 0.0
        while not self._stop.wait(0.05):
            now = time.monotonic()
            try:
                if now >= next_reconcile:
                    self._reconcile()
                    next_reconcile = now + 30.0
                if now >= next_server:
                    self._sample_server()
                    next_server = now + 0.25
                if now >= next_operator:
                    self._sample_operator()
                    next_operator = now + 0.75
            except Exception:
                # A transient source failure must not kill the shared pump.
                continue
