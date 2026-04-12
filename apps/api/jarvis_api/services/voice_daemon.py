"""Voice daemon — runs the Hey Jarvis voice loop as a background thread.

Starts automatically with the API if voice is enabled in config.
Uses /opt/conda/envs/ai/bin/python3 to access voice dependencies.
"""
from __future__ import annotations

import logging
import subprocess
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_PYTHON = "/opt/conda/envs/ai/bin/python3"
_SCRIPT = str(Path(__file__).resolve().parents[4] / "core" / "skills" / "voice" / "voice_daemon_worker.py")

_thread: threading.Thread | None = None
_proc: subprocess.Popen | None = None
_stop_event = threading.Event()


def _is_voice_enabled() -> bool:
    """Check if voice is enabled via config or env."""
    import os
    return os.environ.get("JARVIS_VOICE_ENABLED", "").lower() in ("1", "true", "yes")


def _run_loop():
    """Supervisor thread: start worker, restart on crash until stopped."""
    global _proc
    while not _stop_event.is_set():
        logger.info("voice_daemon: starting worker process")
        try:
            _proc = subprocess.Popen(
                [_PYTHON, "-u", _SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            # Stream worker output to logger
            for line in _proc.stdout:
                line = line.rstrip()
                if line:
                    logger.info("voice_worker: %s", line)
                if _stop_event.is_set():
                    break
            _proc.wait()
            if _stop_event.is_set():
                break
            logger.warning("voice_daemon: worker exited (code=%s), restarting in 5s", _proc.returncode)
            time.sleep(5)
        except Exception as exc:
            logger.error("voice_daemon: worker error: %s", exc)
            time.sleep(10)
    logger.info("voice_daemon: supervisor stopped")


def start_voice_daemon():
    global _thread
    if not _is_voice_enabled():
        logger.info("voice_daemon: JARVIS_VOICE_ENABLED not set — skipping")
        return
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_run_loop, daemon=True, name="voice-daemon")
    _thread.start()
    logger.info("voice_daemon: started")


def stop_voice_daemon():
    global _proc
    _stop_event.set()
    if _proc:
        try:
            _proc.terminate()
        except Exception:
            pass
    logger.info("voice_daemon: stopping")
