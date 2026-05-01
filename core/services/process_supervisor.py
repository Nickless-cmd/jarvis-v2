"""Process supervisor — track long-running background processes Jarvis spawns.

Today Jarvis runs `nohup foo &` via bash and immediately loses the pid.
Logs scatter, leaks accumulate, "is the toku-poller still running?" is
hard to answer. This module gives him a managed primitive:

  process_spawn(name="toku-poller", command="node poller.mjs", cwd=...)
  process_list()                — pid, status (running/exited/lost), uptime
  process_tail("toku-poller")   — last N log lines
  process_stop("toku-poller")   — SIGTERM, then SIGKILL after grace

Each spawn writes stdout+stderr to a per-process log under
  ~/.jarvis-v2/state/processes/<name>.log
and the registry of {name → pid, command, cwd, started_at, log_path}
persists to ~/.jarvis-v2/state/processes/registry.json so survival across
runtime restarts is detectable: if a stored pid no longer exists, status
becomes 'lost' and Jarvis can decide what to do.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.config import STATE_DIR

logger = logging.getLogger(__name__)

_PROC_DIR = Path(STATE_DIR) / "processes"
_REGISTRY = _PROC_DIR / "registry.json"
_LOCK = threading.Lock()
_GRACE_SECONDS = 5
_TAIL_DEFAULT_LINES = 40
_TAIL_MAX_LINES = 500


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_dirs() -> None:
    _PROC_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(name: str) -> str:
    """Sanitize a process name for use in filenames."""
    s = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in (name or "").strip())
    return s[:64] or "proc"


def _load_registry() -> dict[str, dict[str, Any]]:
    if not _REGISTRY.is_file():
        return {}
    try:
        with _REGISTRY.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("process_supervisor: registry load failed: %s", exc)
        return {}


def _save_registry(reg: dict[str, dict[str, Any]]) -> None:
    _ensure_dirs()
    tmp = _REGISTRY.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(reg, fh, indent=2, ensure_ascii=False)
    tmp.replace(_REGISTRY)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)  # signal 0 = check existence + permissions
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal (different uid) — treat as alive
        return True
    except Exception:
        return False


def _read_status(entry: dict[str, Any]) -> dict[str, Any]:
    """Snapshot of a registry entry's live status."""
    pid = int(entry.get("pid") or 0)
    alive = _pid_alive(pid)
    status = "running" if alive else (
        "exited" if entry.get("exit_code") is not None else "lost"
    )
    started_at = entry.get("started_at") or ""
    uptime_s: float | None = None
    if alive and started_at:
        try:
            t0 = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            uptime_s = (datetime.now(UTC) - t0).total_seconds()
        except Exception:
            uptime_s = None
    return {
        "name": entry.get("name"),
        "pid": pid,
        "status": status,
        "command": entry.get("command"),
        "cwd": entry.get("cwd"),
        "started_at": started_at,
        "uptime_seconds": uptime_s,
        "exit_code": entry.get("exit_code"),
        "stopped_at": entry.get("stopped_at"),
        "log_path": entry.get("log_path"),
    }


# ── Public API ────────────────────────────────────────────────────


def spawn_process(
    *,
    name: str,
    command: str,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    replace_if_running: bool = False,
) -> dict[str, Any]:
    """Spawn a detached background process under supervision.

    The command runs in a new session (so a Ctrl-C in our parent shell
    doesn't take it down), with stdout+stderr redirected to a per-name
    log file. Returns the registry entry on success.

    If a process with `name` is already alive and replace_if_running
    is False, returns an error rather than spawning a duplicate.
    """
    name = _safe_name(name)
    if not command.strip():
        return {"status": "error", "error": "command required"}

    _ensure_dirs()
    with _LOCK:
        reg = _load_registry()
        existing = reg.get(name)
        if existing:
            status = _read_status(existing)
            if status["status"] == "running":
                if not replace_if_running:
                    return {
                        "status": "error",
                        "error": f"process '{name}' already running (pid={status['pid']}). "
                                 f"Pass replace_if_running=true to terminate and respawn.",
                        "current": status,
                    }
                # Stop the existing one first
                _stop_locked(reg, name, grace=_GRACE_SECONDS)

        log_path = _PROC_DIR / f"{name}.log"
        # Truncate previous log so each spawn starts fresh
        log_fh = log_path.open("w", encoding="utf-8", buffering=1)
        log_fh.write(f"# JarvisX spawn {_now_iso()}\n# cmd: {command}\n# cwd: {cwd or '(default)'}\n\n")

        full_env = os.environ.copy()
        if env:
            full_env.update({str(k): str(v) for k, v in env.items()})

        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                cwd=cwd or None,
                env=full_env,
                start_new_session=True,
                close_fds=True,
            )
        except Exception as exc:
            log_fh.close()
            return {"status": "error", "error": f"spawn failed: {exc}"}

        entry = {
            "name": name,
            "pid": proc.pid,
            "command": command,
            "cwd": cwd or os.getcwd(),
            "started_at": _now_iso(),
            "log_path": str(log_path),
            "exit_code": None,
            "stopped_at": None,
        }
        reg[name] = entry
        _save_registry(reg)

    # Background reaper to record exit code if it dies on its own
    def _reap(pid: int, name: str) -> None:
        try:
            # subprocess.Popen.wait would close fds; use os.waitpid
            _, status_code = os.waitpid(pid, 0)
            exit_code = os.waitstatus_to_exitcode(status_code)
        except Exception:
            exit_code = None
        with _LOCK:
            reg2 = _load_registry()
            if name in reg2 and int(reg2[name].get("pid") or 0) == pid:
                reg2[name]["exit_code"] = exit_code
                reg2[name]["stopped_at"] = _now_iso()
                _save_registry(reg2)
    threading.Thread(target=_reap, args=(proc.pid, name), daemon=True, name=f"proc-reap-{name}").start()

    return {"status": "ok", "process": _read_status(entry)}


def list_processes(*, include_stopped: bool = True) -> dict[str, Any]:
    with _LOCK:
        reg = _load_registry()
    items = [_read_status(e) for e in reg.values()]
    if not include_stopped:
        items = [i for i in items if i["status"] == "running"]
    items.sort(key=lambda x: (x["status"] != "running", x.get("name") or ""))
    return {"count": len(items), "processes": items}


def _stop_locked(reg: dict[str, dict[str, Any]], name: str, grace: int) -> dict[str, Any]:
    """Caller must hold _LOCK. Stops the named process gracefully."""
    entry = reg.get(name)
    if not entry:
        return {"status": "error", "error": f"unknown process '{name}'"}
    pid = int(entry.get("pid") or 0)
    if not _pid_alive(pid):
        return {"status": "ok", "message": "already stopped", "process": _read_status(entry)}
    # SIGTERM, wait grace seconds, SIGKILL if still alive.
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except Exception as exc:
        logger.debug("process_supervisor: SIGTERM %s failed: %s", pid, exc)
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
    deadline = time.time() + max(0, grace)
    while time.time() < deadline:
        if not _pid_alive(pid):
            break
        time.sleep(0.2)
    if _pid_alive(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
    entry["stopped_at"] = _now_iso()
    _save_registry(reg)
    return {"status": "ok", "process": _read_status(entry)}


def stop_process(name: str, *, grace: int = _GRACE_SECONDS) -> dict[str, Any]:
    name = _safe_name(name)
    with _LOCK:
        reg = _load_registry()
        return _stop_locked(reg, name, grace)


def tail_process_log(name: str, *, lines: int = _TAIL_DEFAULT_LINES) -> dict[str, Any]:
    name = _safe_name(name)
    lines = max(1, min(int(lines or _TAIL_DEFAULT_LINES), _TAIL_MAX_LINES))
    log_path = _PROC_DIR / f"{name}.log"
    if not log_path.is_file():
        return {"status": "error", "error": f"no log for '{name}'"}
    try:
        # Read the tail efficiently by chunks from end
        with log_path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            file_size = fh.tell()
            block = 8192
            buf = b""
            pos = file_size
            while pos > 0 and buf.count(b"\n") <= lines:
                read_size = min(block, pos)
                pos -= read_size
                fh.seek(pos)
                buf = fh.read(read_size) + buf
        text = buf.decode("utf-8", errors="replace")
        tail = "\n".join(text.splitlines()[-lines:])
    except Exception as exc:
        return {"status": "error", "error": f"read failed: {exc}"}
    return {
        "status": "ok",
        "name": name,
        "log_path": str(log_path),
        "lines": tail,
        "byte_size": file_size,
    }


def remove_process(name: str) -> dict[str, Any]:
    """Remove an entry from the registry. Refuses if still alive."""
    name = _safe_name(name)
    with _LOCK:
        reg = _load_registry()
        entry = reg.get(name)
        if not entry:
            return {"status": "error", "error": "not found"}
        if _pid_alive(int(entry.get("pid") or 0)):
            return {"status": "error", "error": "still running — stop_process first"}
        reg.pop(name, None)
        _save_registry(reg)
    return {"status": "ok"}
