"""Reboot Awareness Daemon — proprioception: "I feel when I restart".

Jarvis' plan #2 (PLAN_PROPRIOCEPTION.md, 2026-04-20): detect restart
events — both graceful (SIGTERM) and unclean (OOM, kill -9, crash).

Mechanism:
- On every tick: write `last_seen_at` timestamp + pid to markers file
- On startup: read previous markers. If gap > threshold → emit event
  with direction (graceful | unclean) based on last shutdown marker.
- On SIGTERM/SIGINT: register handler that writes a graceful-shutdown
  marker before exit.

The detection runs once per process lifetime (idempotent via flag).
"""
from __future__ import annotations

import json
import logging
import os
import signal
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/reboot_markers.json"
_UNCLEAN_GAP_MINUTES = 30  # if last_seen older than 30 min → assume crashed
_DETECTION_RUN = False
_EVENT_RESULT: dict[str, Any] | None = None


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        logger.warning("reboot_awareness: load failed: %s", exc)
    return {}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("reboot_awareness: save failed: %s", exc)


def _update_last_seen(pid: int) -> None:
    data = _load()
    data["last_seen_at"] = datetime.now(UTC).isoformat()
    data["last_seen_pid"] = int(pid)
    _save(data)


def _graceful_shutdown_marker() -> None:
    """Called via signal handler. Writes a clean shutdown marker."""
    try:
        data = _load()
        data["last_shutdown_at"] = datetime.now(UTC).isoformat()
        data["last_shutdown_type"] = "graceful"
        data["last_shutdown_pid"] = os.getpid()
        _save(data)
    except Exception:
        pass


def _signal_handler(signum: int, _frame: Any) -> None:
    """Write graceful-shutdown marker then re-raise to default handler."""
    _graceful_shutdown_marker()
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "reboot.imminent",
            "payload": {
                "signal": signum,
                "graceful": True,
                "at": datetime.now(UTC).isoformat(),
            },
        })
    except Exception:
        pass
    # Re-raise default for the signal (exit cleanly)
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


def _install_signal_handlers() -> None:
    try:
        signal.signal(signal.SIGTERM, _signal_handler)
    except Exception:
        pass
    try:
        signal.signal(signal.SIGINT, _signal_handler)
    except Exception:
        pass


def detect_reboot() -> dict[str, Any] | None:
    """Compare previous last_seen to now; emit an event if this is a fresh boot.

    Runs once per process via _DETECTION_RUN flag. Subsequent calls no-op.
    """
    global _DETECTION_RUN, _EVENT_RESULT
    if _DETECTION_RUN:
        return _EVENT_RESULT
    _DETECTION_RUN = True

    data = _load()
    now = datetime.now(UTC)
    prev_seen_str = data.get("last_seen_at")
    prev_shutdown_type = str(data.get("last_shutdown_type") or "")
    prev_pid = data.get("last_seen_pid")
    current_pid = os.getpid()

    if not prev_seen_str:
        # First ever boot — no prior marker
        result = {
            "kind": "reboot.first_boot",
            "current_pid": current_pid,
            "at": now.isoformat(),
        }
    else:
        try:
            prev_seen = datetime.fromisoformat(str(prev_seen_str).replace("Z", "+00:00"))
            gap_seconds = max(0, int((now - prev_seen).total_seconds()))
        except Exception:
            prev_seen = None
            gap_seconds = 0

        if prev_pid == current_pid:
            # Same process — not actually a reboot, just startup hook called mid-process
            _EVENT_RESULT = None
            return None

        direction: str
        if prev_shutdown_type == "graceful":
            direction = "completed"
            graceful = True
        elif gap_seconds > _UNCLEAN_GAP_MINUTES * 60:
            direction = "unexpected"
            graceful = False
        else:
            # Recent but no graceful marker → probably quick restart without SIGTERM
            direction = "unexpected"
            graceful = False

        result = {
            "kind": f"reboot.{direction}",
            "downtime_seconds": gap_seconds,
            "graceful": graceful,
            "prev_pid": prev_pid,
            "current_pid": current_pid,
            "at": now.isoformat(),
        }

    _EVENT_RESULT = dict(result)

    # Clear the shutdown_type marker (start of new process)
    data["last_shutdown_type"] = None
    data["last_seen_at"] = now.isoformat()
    data["last_seen_pid"] = current_pid
    data["last_boot_at"] = now.isoformat()
    data["last_boot_event"] = result
    _save(data)

    # Publish event
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({"kind": result["kind"], "payload": result})
    except Exception:
        pass

    # Install signal handlers for graceful shutdown detection
    _install_signal_handlers()

    return result


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Heartbeat hook: first call triggers detect_reboot(), thereafter
    updates last_seen timestamp."""
    if not _DETECTION_RUN:
        detect_reboot()
    _update_last_seen(os.getpid())
    return {"ok": True}


def get_last_boot_event() -> dict[str, Any] | None:
    return _load().get("last_boot_event")


def build_reboot_awareness_surface() -> dict[str, Any]:
    data = _load()
    last_event = data.get("last_boot_event") or {}
    last_seen = data.get("last_seen_at")
    now = datetime.now(UTC)
    uptime_seconds: int | None = None
    boot_at = data.get("last_boot_at")
    if boot_at:
        try:
            boot_dt = datetime.fromisoformat(str(boot_at).replace("Z", "+00:00"))
            uptime_seconds = max(0, int((now - boot_dt).total_seconds()))
        except Exception:
            pass
    return {
        "active": _DETECTION_RUN,
        "last_boot_event": last_event,
        "uptime_seconds": uptime_seconds,
        "last_seen_at": last_seen,
        "current_pid": os.getpid(),
        "summary": _surface_summary(last_event, uptime_seconds),
    }


def _surface_summary(event: dict[str, Any], uptime: int | None) -> str:
    if not event:
        return "Ingen reboot-data endnu"
    kind = str(event.get("kind") or "")
    uptime_str = ""
    if uptime is not None:
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        if hours > 0:
            uptime_str = f" (oppe {hours}h{minutes}m)"
        else:
            uptime_str = f" (oppe {minutes}m)"
    if kind == "reboot.first_boot":
        return f"Første boot{uptime_str}"
    if kind == "reboot.completed":
        downtime = int(event.get("downtime_seconds") or 0)
        return f"Genstartet rent efter {downtime}s nede{uptime_str}"
    if kind == "reboot.unexpected":
        downtime = int(event.get("downtime_seconds") or 0)
        return f"Genstartet uventet efter {downtime}s nede{uptime_str}"
    return f"{kind}{uptime_str}"


def build_reboot_awareness_prompt_section() -> str | None:
    """Announce recent reboot once; stays silent after first ~10 min."""
    data = _load()
    last_event = data.get("last_boot_event") or {}
    if not last_event:
        return None
    boot_at = data.get("last_boot_at")
    if not boot_at:
        return None
    try:
        boot_dt = datetime.fromisoformat(str(boot_at).replace("Z", "+00:00"))
    except Exception:
        return None
    if (datetime.now(UTC) - boot_dt) > timedelta(minutes=15):
        return None
    kind = str(last_event.get("kind") or "")
    if kind == "reboot.first_boot":
        return "Jeg er nystartet — første boot."
    if kind == "reboot.completed":
        downtime = int(last_event.get("downtime_seconds") or 0)
        return f"Jeg er vågnet igen efter rent shutdown ({downtime}s nede)."
    if kind == "reboot.unexpected":
        downtime = int(last_event.get("downtime_seconds") or 0)
        return f"Jeg er genstartet uventet efter {downtime}s nede — noget afbrød mig."
    return None
