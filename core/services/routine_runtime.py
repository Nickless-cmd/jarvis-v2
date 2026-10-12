"""Bounded worker and reconciler threads for Routines."""
from __future__ import annotations

import logging
import threading
from typing import Any

from core.services.routine_reconciler import RoutineReconciler
from core.services.routine_runner import RoutineRunner


logger = logging.getLogger(__name__)


class RoutineRuntime:
    def __init__(
        self, *, runner: Any | None = None, reconciler: Any | None = None,
        poll_seconds: float = 1.0, reconcile_seconds: float = 30.0,
    ):
        self.runner = runner or RoutineRunner()
        self.reconciler = reconciler or RoutineReconciler(repository=self.runner.repository)
        self.poll_seconds = max(0.001, float(poll_seconds))
        self.reconcile_seconds = max(0.001, float(reconcile_seconds))
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None
        self._reconciler: threading.Thread | None = None
        self._claims_after_stop = 0

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.runner.run_next()
            except Exception as exc:
                logger.warning("routine worker failed: %s", type(exc).__name__)
            self._stop.wait(self.poll_seconds)

    def _reconciler_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.reconciler.reconcile_once()
            except Exception as exc:
                logger.warning("routine reconciliation failed: %s", type(exc).__name__)
            try:
                self.reconciler.sweep_retention()
            except Exception as exc:
                logger.warning("routine retention sweep failed: %s", type(exc).__name__)
            self._stop.wait(self.reconcile_seconds)

    def start(self) -> None:
        if self.worker_is_alive() or self.reconciler_is_alive():
            return
        self._stop.clear()
        self._worker = threading.Thread(
            target=self._worker_loop, name="routine-worker", daemon=True,
        )
        self._reconciler = threading.Thread(
            target=self._reconciler_loop, name="routine-reconciler", daemon=True,
        )
        self._worker.start()
        self._reconciler.start()

    def stop(self, *, timeout_seconds: float = 5.0) -> None:
        self._stop.set()
        for thread in (self._worker, self._reconciler):
            if thread is not None:
                thread.join(timeout=max(0.0, timeout_seconds))

    def worker_is_alive(self) -> bool:
        return bool(self._worker and self._worker.is_alive())

    def reconciler_is_alive(self) -> bool:
        return bool(self._reconciler and self._reconciler.is_alive())

    def claim_count_after_stop(self) -> int:
        return self._claims_after_stop


_runtime: RoutineRuntime | None = None
_lock = threading.Lock()


def start_routine_runtime() -> RoutineRuntime:
    global _runtime
    with _lock:
        if _runtime is None:
            _runtime = RoutineRuntime()
        _runtime.start()
        return _runtime


def stop_routine_runtime(*, timeout_seconds: float = 5.0) -> None:
    global _runtime
    with _lock:
        runtime = _runtime
        _runtime = None
    if runtime is not None:
        runtime.stop(timeout_seconds=timeout_seconds)
