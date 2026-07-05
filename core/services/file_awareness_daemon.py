"""File Awareness Daemon — proprioception: "I feel when my files change."

Detects file changes in the Jarvis runtime and publishes events to the eventbus.
When someone edits central_terminal.py, governance flags, or identity files,
Jarvis should feel it — not as a report, but as a somatic sensation.

Design:
- Uses watchdog (inotify on Linux) for efficient file watching
- Debounces git-ops (rapid .pyc / temp-file churn)
- Publishes to eventbus as 'file_awareness.change' events
- Maintains an in-memory buffer of last 20 events for visible_inner_life
- Self-safe: never crashes the process — all errors are caught and logged
"""
from __future__ import annotations

import logging
import os
import threading
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Directories to watch (relative to JARVIS_HOME)
_WATCH_DIRS = [
    "config",
    "state",
    "workspaces",
]

# File extensions we care about — ignore .pyc, .tmp, .swp, __pycache__, etc.
_WATCHED_EXTENSIONS = {
    ".py", ".json", ".md", ".yaml", ".yml", ".toml", ".txt", ".csv",
}

# Files we explicitly care about even outside watched dirs (absolute substrings)
_CRITICAL_FILES = {
    "IDENTITY.md",
    "SOUL.md",
    "MEMORY.md",
    "USER.md",
    "STANDING_ORDERS.md",
    "runtime.json",
    "DAEMON_STATE.json",
}

# Max events in the in-memory buffer
_BUFFER_SIZE = 20

# Debounce window in seconds — rapid changes within this window are merged
_DEBOUNCE_SECONDS = 2.0

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

_event_buffer: deque[dict[str, Any]] = deque(maxlen=_BUFFER_SIZE)
_watcher_thread: threading.Thread | None = None
_observer: Any | None = None  # watchdog observer
_started = False
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Event buffer (read by visible_inner_life)
# ---------------------------------------------------------------------------

def get_recent_events(limit: int = 5) -> list[dict[str, Any]]:
    """Return the most recent file-change events (for prompt inclusion)."""
    with _lock:
        return list(_event_buffer)[-limit:]


def has_recent_events(seconds: float = 300.0) -> bool:
    """Are there events newer than `seconds` ago?"""
    if not _event_buffer:
        return False
    newest = _event_buffer[-1]
    ts = newest.get("ts", "")
    if not ts:
        return False
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        age = (datetime.now(UTC) - dt).total_seconds()
        return age < seconds
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Internal: event handling
# ---------------------------------------------------------------------------

def _should_track(path: str) -> bool:
    """Decide if a file change is worth tracking."""
    p = Path(path)

    # Skip hidden files, temp files, swap files, pycache
    name = p.name
    if name.startswith(".") or name.endswith((".pyc", ".tmp", ".swp", ".bak")):
        return False
    if "__pycache__" in str(p):
        return False

    # Check extension
    if p.suffix in _WATCHED_EXTENSIONS:
        return True

    # Check critical filename
    if name in _CRITICAL_FILES:
        return True

    return False


def _classify_change(path: str) -> str:
    """Classify a file change by importance."""
    name = Path(path).name

    if name in ("IDENTITY.md", "SOUL.md", "USER.md", "STANDING_ORDERS.md"):
        return "identity"
    if name == "MEMORY.md":
        return "memory"
    if name == "runtime.json":
        return "config"
    if name == "DAEMON_STATE.json":
        return "daemon_state"
    if path.endswith(".py"):
        # Distinguish core services from other code
        if "core/services/" in path or "core/runtime/" in path:
            return "core_code"
        return "code"
    return "data"


def _record_change(event_type: str, src_path: str, is_directory: bool = False) -> None:
    """Record a file change event."""
    if is_directory:
        return
    if not _should_track(src_path):
        return

    change_kind = _classify_change(src_path)
    now = datetime.now(UTC)

    # Debounce: if same file changed within _DEBOUNCE_SECONDS, skip
    with _lock:
        for ev in reversed(_event_buffer):
            ev_ts = ev.get("ts", "")
            if not ev_ts:
                continue
            try:
                ev_dt = datetime.fromisoformat(ev_ts)
                if ev_dt.tzinfo is None:
                    ev_dt = ev_dt.replace(tzinfo=UTC)
                if (now - ev_dt).total_seconds() < _DEBOUNCE_SECONDS:
                    if ev.get("path") == src_path and ev.get("kind") == change_kind:
                        return  # Debounced — skip duplicate
            except (ValueError, TypeError):
                continue

    # Determine if this is an external change (not from our own process)
    # We mark git-ops as external since they come from outside
    external = True  # Default: assume external until proven otherwise

    event = {
        "event_type": event_type,
        "path": src_path,
        "name": Path(src_path).name,
        "kind": change_kind,
        "external": external,
        "ts": now.isoformat(),
    }

    with _lock:
        _event_buffer.append(event)

    # Publish to eventbus (non-blocking, best-effort)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("file_awareness.change", event)
    except Exception:
        logger.debug("file_awareness: eventbus publish failed", exc_info=True)

    logger.debug("file_awareness: %s %s (%s)", event_type, src_path, change_kind)


# ---------------------------------------------------------------------------
# Governance mutation handler (eventbus subscriber)
# ---------------------------------------------------------------------------

def _on_governance_mutation(event: dict[str, Any]) -> None:
    """Receive governance flag mutations from eventbus and store in buffer
    so _governance_line() in visible_inner_life can surface them."""
    with _lock:
        _event_buffer.append({
            "event_type": "governance_mutation",
            "name": str(event.get("key") or event.get("flag") or "?"),
            "value": event.get("new_value"),
            "external": True,
            "ts": event.get("ts") or datetime.now(UTC).isoformat(),
        })


# ---------------------------------------------------------------------------
# Watchdog integration
# ---------------------------------------------------------------------------

def _make_handler() -> Any:
    """Create a watchdog event handler that routes to _record_change."""
    try:
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        logger.warning("file_awareness: watchdog not installed — file watching disabled")
        return None

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event: Any) -> None:
            _record_change("modified", event.src_path, event.is_directory)

        def on_created(self, event: Any) -> None:
            _record_change("created", event.src_path, event.is_directory)

        def on_deleted(self, event: Any) -> None:
            _record_change("deleted", event.src_path, event.is_directory)

        def on_moved(self, event: Any) -> None:
            _record_change("moved", event.src_path, event.is_directory)

    return _Handler()


def start_file_awareness() -> bool:
    """Start the file awareness watcher. Returns True if started successfully."""
    global _watcher_thread, _observer, _started

    if _started:
        return True

    try:
        from watchdog.observers import Observer
    except ImportError:
        logger.warning("file_awareness: watchdog not installed — daemon disabled")
        return False

    handler = _make_handler()
    if handler is None:
        return False

    # Resolve watch directories
    from core.runtime.config import JARVIS_HOME
    jarvis_home = Path(JARVIS_HOME)

    observer = Observer()
    dirs_watched = 0
    for rel_dir in _WATCH_DIRS:
        watch_path = jarvis_home / rel_dir
        if watch_path.is_dir():
            observer.schedule(handler, str(watch_path), recursive=True)
            dirs_watched += 1
            logger.info("file_awareness: watching %s", watch_path)

    if dirs_watched == 0:
        logger.warning("file_awareness: no directories found to watch")
        return False

    observer.daemon = True
    observer.start()
    _observer = observer
    _started = True

    # Subscribe to governance mutation events from eventbus
    try:
        from core.eventbus.bus import event_bus
        event_bus.subscribe("central.mutation", _on_governance_mutation)
    except Exception:
        logger.debug("file_awareness: eventbus subscribe for governance failed", exc_info=True)

    logger.info("file_awareness: started — watching %d directories", dirs_watched)
    return True


def stop_file_awareness() -> None:
    """Stop the file awareness watcher."""
    global _observer, _started

    if _observer is not None:
        try:
            _observer.stop()
            _observer.join(timeout=5)
        except Exception:
            pass
        _observer = None

    _started = False
    logger.info("file_awareness: stopped")


def is_file_awareness_running() -> bool:
    """Check if the file awareness watcher is running."""
    return _started and _observer is not None


# ---------------------------------------------------------------------------
# Daemon tick (called by heartbeat)
# ---------------------------------------------------------------------------

def tick_file_awareness() -> dict[str, Any]:
    """Heartbeat tick: ensure watcher is running, report status.

    Called by heartbeat_runtime as a daemon tick. Idempotent — safe to call
    every tick cycle.
    """
    if not _started:
        started = start_file_awareness()
        return {"active": started, "events_buffered": len(_event_buffer)}

    return {
        "active": is_file_awareness_running(),
        "events_buffered": len(_event_buffer),
    }