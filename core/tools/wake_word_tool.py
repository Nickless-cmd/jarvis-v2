"""Wake-word tool — Jarvis listens for 'Hey Jarvis' in the background.

Wraps core.skills.voice.wake_word.listen() as a start/stop/status tool
Jarvis can control. Runs the continuous listener in a daemon thread so
other work continues. On detection, emits wake_word.detected event and
optionally triggers an active mic_listen for the follow-up utterance.

The existing wake_word.listen() uses:
  parec → webrtcvad → ElevenLabs STT → phrase match

So it needs an ElevenLabs API key in runtime.json. We check and fail
clean if it's missing.
"""
from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Singleton background state — only one wake-word listener at a time
_listener_thread: threading.Thread | None = None
_interrupt_event: threading.Event | None = None
_last_detection_ts: datetime | None = None
_detection_count: int = 0
_start_ts: datetime | None = None
_auto_listen_after_wake: bool = False
_auto_listen_duration: float = 6.0


def _on_wake(phrase: str) -> None:
    """Callback fired when wake word detected."""
    global _last_detection_ts, _detection_count
    _last_detection_ts = datetime.now(UTC)
    _detection_count += 1
    logger.info("wake_word: detected '%s' (#%d)", phrase, _detection_count)

    # Emit bus event
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "wake_word.detected",
            "payload": {
                "phrase": phrase,
                "at": _last_detection_ts.isoformat(),
                "detection_count": _detection_count,
            },
        })
    except Exception:
        pass

    # Optional: auto-capture the follow-up utterance via mic_listen
    if _auto_listen_after_wake:
        try:
            from core.tools.mic_listen_tool import listen_and_transcribe
            result = listen_and_transcribe(
                duration=_auto_listen_duration,
                backend="hf",
                save_recording=False,
            )
            if result.get("status") == "ok":
                logger.info(
                    "wake_word auto-listen: captured %d chars (trigger=%s)",
                    len(result.get("text") or ""),
                    result.get("trigger"),
                )
                try:
                    from core.eventbus.bus import event_bus
                    event_bus.publish({
                        "kind": "wake_word.follow_up_transcribed",
                        "payload": {
                            "text": str(result.get("text") or "")[:500],
                            "trigger": result.get("trigger"),
                            "trigger_result": result.get("trigger_result"),
                        },
                    })
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("wake_word auto-listen failed: %s", exc)


def _run_listener() -> None:
    """Entry for the background listener thread."""
    try:
        from core.skills.voice.wake_word import listen
        listen(callback=_on_wake, interrupt_event=_interrupt_event)
    except Exception as exc:
        logger.warning("wake_word listener crashed: %s", exc)


def start_wake_word(
    *,
    auto_listen: bool = False,
    auto_listen_duration: float = 6.0,
) -> dict[str, Any]:
    """Start the background wake-word listener. Idempotent."""
    global _listener_thread, _interrupt_event, _start_ts
    global _auto_listen_after_wake, _auto_listen_duration

    if _listener_thread is not None and _listener_thread.is_alive():
        return {
            "status": "ok",
            "text": "wake-word listener already running",
            "started_at": _start_ts.isoformat() if _start_ts else None,
            "detections": _detection_count,
        }

    # Check prerequisites
    try:
        from core.runtime.secrets import read_runtime_key
        if not read_runtime_key("elevenlabs_api_key"):
            return {
                "status": "error",
                "text": "elevenlabs_api_key missing from runtime.json — wake word needs ElevenLabs STT",
            }
    except Exception as exc:
        return {"status": "error", "text": f"could not verify ElevenLabs key: {exc}"}

    _auto_listen_after_wake = bool(auto_listen)
    _auto_listen_duration = max(2.0, min(30.0, float(auto_listen_duration)))
    _interrupt_event = threading.Event()
    _start_ts = datetime.now(UTC)
    _listener_thread = threading.Thread(
        target=_run_listener,
        name="wake-word-listener",
        daemon=True,
    )
    _listener_thread.start()

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "wake_word.started",
            "payload": {
                "at": _start_ts.isoformat(),
                "auto_listen": _auto_listen_after_wake,
                "auto_listen_duration": _auto_listen_duration,
            },
        })
    except Exception:
        pass

    return {
        "status": "ok",
        "text": (
            f"wake-word listener started "
            f"(auto_listen={_auto_listen_after_wake}, duration={_auto_listen_duration}s)"
        ),
        "started_at": _start_ts.isoformat(),
    }


def stop_wake_word() -> dict[str, Any]:
    """Stop the background wake-word listener."""
    global _listener_thread, _interrupt_event, _start_ts
    if _listener_thread is None or not _listener_thread.is_alive():
        return {
            "status": "ok",
            "text": "wake-word listener was not running",
        }

    if _interrupt_event is not None:
        _interrupt_event.set()
    # Give it a few seconds to exit cleanly
    _listener_thread.join(timeout=5.0)
    was_alive = _listener_thread.is_alive()
    _listener_thread = None
    _interrupt_event = None

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "wake_word.stopped",
            "payload": {
                "at": datetime.now(UTC).isoformat(),
                "clean_shutdown": not was_alive,
                "detections_during_session": _detection_count,
            },
        })
    except Exception:
        pass

    return {
        "status": "ok",
        "text": f"wake-word listener stopped (clean={not was_alive})",
        "clean_shutdown": not was_alive,
    }


def wake_word_status() -> dict[str, Any]:
    running = _listener_thread is not None and _listener_thread.is_alive()
    return {
        "status": "ok",
        "running": running,
        "started_at": _start_ts.isoformat() if _start_ts else None,
        "last_detection_at": _last_detection_ts.isoformat() if _last_detection_ts else None,
        "detection_count": _detection_count,
        "auto_listen": _auto_listen_after_wake,
        "auto_listen_duration": _auto_listen_duration,
    }


def _exec_wake_word(args: dict[str, Any]) -> dict[str, Any]:
    command = str(args.get("command") or "status").lower().strip()
    if command == "start":
        auto = bool(args.get("auto_listen", False))
        duration = float(args.get("auto_listen_duration") or 6.0)
        result = start_wake_word(auto_listen=auto, auto_listen_duration=duration)
    elif command == "stop":
        result = stop_wake_word()
    elif command == "status":
        result = wake_word_status()
        result["text"] = (
            f"wake-word {'running' if result['running'] else 'stopped'}, "
            f"{result['detection_count']} detection(s) since "
            f"{result['started_at'][:16] if result['started_at'] else 'never'}"
        )
    else:
        return {
            "status": "error",
            "text": f"unknown command '{command}'. Use start | stop | status.",
        }
    return result


WAKE_WORD_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "wake_word",
            "description": (
                "Control the 'Hey Jarvis' wake-word listener. Uses webrtcvad + "
                "ElevenLabs STT (requires elevenlabs_api_key in runtime.json). "
                "Runs in a background daemon thread. On detection emits "
                "wake_word.detected; if auto_listen=true, also captures the "
                "follow-up utterance via mic_listen and emits "
                "wake_word.follow_up_transcribed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "start | stop | status (default)",
                    },
                    "auto_listen": {
                        "type": "boolean",
                        "description": (
                            "Only for 'start': automatically record follow-up "
                            "after wake detection. Default false."
                        ),
                    },
                    "auto_listen_duration": {
                        "type": "number",
                        "description": "Only for 'start' + auto_listen: seconds. Default 6.",
                    },
                },
                "required": [],
            },
        },
    },
]
