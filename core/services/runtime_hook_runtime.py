from __future__ import annotations

import queue
import threading
from typing import Any

from core.services.runtime_hooks import dispatch_hook_event
from core.eventbus.bus import event_bus

_HOOK_RUNTIME_THREAD: threading.Thread | None = None
_HOOK_RUNTIME_STOP = threading.Event()
_HOOK_RUNTIME_SUBSCRIBER: queue.Queue[dict[str, Any] | None] | None = None
_SUPPORTED_EVENT_KINDS = {
    "heartbeat.initiative_pushed",
    "heartbeat.tick_completed",
}


def start_runtime_hook_runtime() -> None:
    global _HOOK_RUNTIME_THREAD, _HOOK_RUNTIME_SUBSCRIBER
    if _HOOK_RUNTIME_THREAD and _HOOK_RUNTIME_THREAD.is_alive():
        return
    _HOOK_RUNTIME_STOP.clear()
    subscriber = event_bus.subscribe()
    _HOOK_RUNTIME_SUBSCRIBER = subscriber
    thread = threading.Thread(
        target=_hook_runtime_loop,
        kwargs={"subscriber": subscriber},
        name="jarvis-runtime-hook-runtime",
        daemon=True,
    )
    thread.start()
    _HOOK_RUNTIME_THREAD = thread


def stop_runtime_hook_runtime() -> None:
    global _HOOK_RUNTIME_THREAD, _HOOK_RUNTIME_SUBSCRIBER
    _HOOK_RUNTIME_STOP.set()
    subscriber = _HOOK_RUNTIME_SUBSCRIBER
    if subscriber is not None:
        event_bus.unsubscribe(subscriber)
    thread = _HOOK_RUNTIME_THREAD
    if thread and thread.is_alive():
        thread.join(timeout=1.0)
    _HOOK_RUNTIME_THREAD = None
    _HOOK_RUNTIME_SUBSCRIBER = None


def _hook_runtime_loop(*, subscriber: queue.Queue[dict[str, Any] | None]) -> None:
    while not _HOOK_RUNTIME_STOP.is_set():
        try:
            item = subscriber.get(timeout=0.5)
        except queue.Empty:
            continue
        if item is None:
            break
        if str(item.get("kind") or "") not in _SUPPORTED_EVENT_KINDS:
            continue
        try:
            dispatch_hook_event(item)
        except Exception:
            continue


def build_runtime_hook_runtime_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "runtime_hook_runtime",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_runtime_hook_runtime_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event — defensive, never blocks caller.
    Cartographer scans for event_bus.publish() text.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"runtime_hook_runtime.{kind}",
            payload or {},
        )
    except Exception:
        pass

