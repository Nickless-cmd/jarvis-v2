"""Persistent bash sessions — Jarvis' one-shot bash forced him to restart his
shell mental model with every call. ``cd /repo`` didn't survive, virtualenvs
had to be re-activated, env-vars vanished. This is the single largest UX gap
between Claude Code's harness and Jarvis' own toolset.

Design:
- ``bash_session_open()`` spawns a long-lived ``bash -i`` over a real PTY
  and returns a session_id. State (cwd, env, exported vars, sourced files,
  shell aliases) survives across calls. PTY is required because bash
  block-buffers stdout when it isn't on a TTY — over a pipe the marker
  line never reaches us until the shell exits.
- ``bash_session_run(session_id, command, timeout=30)`` writes the command
  followed by an ``echo MARKER $?`` sentinel and reads PTY output until
  the marker line shows up. Returns stdout/stderr/exit_code. Concurrent
  runs against one session are serialized via a lock.
- ``bash_session_close(session_id)`` terminates the subprocess and clears
  state.
- Idle reaper thread closes any session with no activity for >30 min.
- Session metadata is persisted to ~/.jarvis-v2/state/bash_sessions.json
  so a process restart leaves no zombie sessions referenced by the model.

Containment:
- Subprocess inherits the same env Jarvis runs in (no privilege escalation).
- Output capped per call to keep the model context bounded.
- Hard cap of 8 concurrent sessions to prevent runaway spawn.
"""
from __future__ import annotations

import logging
import os
import pty
import select
import signal
import termios
import threading
import time
import uuid
from typing import Any

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "bash_sessions"
_MAX_SESSIONS = 8
_OUTPUT_LIMIT_BYTES = 32 * 1024
_DEFAULT_TIMEOUT = 30
_IDLE_TTL_SECONDS = 30 * 60


class _Session:
    """A single persistent bash subprocess on a PTY, serialized command access."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.lock = threading.Lock()
        self.last_used = time.time()
        # pty.fork() gives the child a controlling terminal so bash will
        # line-buffer stdout. Without this, output is block-buffered and
        # our marker line never arrives until the shell exits.
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            # Child — replace ourselves with bash. ``--noprofile --norc``
            # avoids loading user dotfiles that might emit prompts; ``-i``
            # is still needed so aliases/jobs work as expected.
            try:
                os.execvpe(
                    "bash",
                    ["bash", "--noprofile", "--norc", "-i"],
                    dict(os.environ, PS1="", PS2="", TERM="dumb"),
                )
            except Exception:
                os._exit(127)
        # Parent — disable terminal echo so the commands we write don't
        # come back as output. Wait briefly for bash to settle, then
        # drain any startup banner.
        try:
            attrs = termios.tcgetattr(self.fd)
            attrs[3] &= ~termios.ECHO
            termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        except Exception:
            pass
        time.sleep(0.2)
        self._drain_pending(timeout=0.4)

    def _drain_pending(self, timeout: float) -> None:
        """Read whatever's currently buffered on the PTY and discard it."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if not r:
                return
            try:
                os.read(self.fd, 4096)
            except OSError:
                return

    def alive(self) -> bool:
        try:
            pid, _ = os.waitpid(self.pid, os.WNOHANG)
            return pid == 0
        except ChildProcessError:
            return False

    def run(self, command: str, timeout: float = _DEFAULT_TIMEOUT) -> dict[str, Any]:
        if not self.alive():
            return {"status": "error", "error": "session terminated"}

        with self.lock:
            self.last_used = time.time()
            marker = f"__JARVIS_END_{uuid.uuid4().hex}__"
            # Group the user command in { ... ; } so its exit-status flows
            # to $? after the close-brace; then the marker line carries it.
            payload = (
                f"{{ {command}\n"
                f"}} ; echo \"{marker} $?\"\n"
            ).encode()
            try:
                os.write(self.fd, payload)
            except OSError as exc:
                return {"status": "error", "error": f"write failed: {exc}"}

            buf = b""
            exit_code: int | None = None
            deadline = time.time() + max(1.0, float(timeout))
            marker_b = marker.encode()

            while time.time() < deadline:
                r, _, _ = select.select([self.fd], [], [], 0.2)
                if not r:
                    if not self.alive():
                        break
                    continue
                try:
                    chunk = os.read(self.fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                buf += chunk
                if marker_b in buf:
                    pre, _, post = buf.partition(marker_b)
                    tail = post.split(b"\n", 1)[0].strip()
                    try:
                        exit_code = int(tail.decode().split()[0])
                    except Exception:
                        exit_code = None
                    buf = pre
                    break
                if len(buf) > _OUTPUT_LIMIT_BYTES * 2:
                    buf = buf[-_OUTPUT_LIMIT_BYTES * 2:]
            else:
                return {
                    "status": "timeout",
                    "session_id": self.session_id,
                    "command": command[:160],
                    "timeout_seconds": timeout,
                    "output": _decode(buf)[-_OUTPUT_LIMIT_BYTES:],
                    "note": "Command did not finish within timeout. "
                    "Session is still alive but the command may still be running.",
                }

            return {
                "status": "ok",
                "session_id": self.session_id,
                "command": command[:160],
                "exit_code": exit_code,
                "output": _decode(buf)[-_OUTPUT_LIMIT_BYTES:],
            }

    def close(self) -> None:
        with self.lock:
            try:
                if self.alive():
                    os.kill(self.pid, signal.SIGTERM)
                    for _ in range(10):
                        if not self.alive():
                            break
                        time.sleep(0.1)
                    if self.alive():
                        os.kill(self.pid, signal.SIGKILL)
            except Exception as exc:
                logger.debug("bash_session %s close failed: %s", self.session_id, exc)
            try:
                os.close(self.fd)
            except OSError:
                pass


def _decode(buf: bytes) -> str:
    """PTY read can give partial UTF-8 — replace bad bytes rather than crash."""
    try:
        return buf.decode("utf-8", errors="replace").replace("\r\n", "\n")
    except Exception:
        return repr(buf)


_sessions: dict[str, _Session] = {}
_registry_lock = threading.Lock()
_reaper_started = False


def _persist_metadata() -> None:
    meta = {
        sid: {"alive": s.alive(), "last_used": s.last_used}
        for sid, s in _sessions.items()
    }
    save_json(_STATE_KEY, meta)


def _start_reaper() -> None:
    global _reaper_started
    if _reaper_started:
        return
    _reaper_started = True

    def _loop() -> None:
        while True:
            time.sleep(60)
            now = time.time()
            with _registry_lock:
                stale = [
                    sid for sid, s in _sessions.items()
                    if (not s.alive()) or (now - s.last_used > _IDLE_TTL_SECONDS)
                ]
                for sid in stale:
                    s = _sessions.pop(sid, None)
                    if s is not None:
                        s.close()
                if stale:
                    _persist_metadata()

    threading.Thread(target=_loop, name="bash-session-reaper", daemon=True).start()


def _exec_bash_session_open(args: dict[str, Any]) -> dict[str, Any]:
    _start_reaper()
    with _registry_lock:
        if len(_sessions) >= _MAX_SESSIONS:
            stale = [sid for sid, s in _sessions.items() if not s.alive()]
            for sid in stale:
                _sessions.pop(sid, None)
        if len(_sessions) >= _MAX_SESSIONS:
            return {
                "status": "error",
                "error": f"max {_MAX_SESSIONS} concurrent bash sessions; close one first",
            }
        sid = f"bsh-{uuid.uuid4().hex[:10]}"
        try:
            _sessions[sid] = _Session(sid)
        except Exception as exc:
            return {"status": "error", "error": f"failed to spawn shell: {exc}"}
        _persist_metadata()
        return {"status": "ok", "session_id": sid}


def _exec_bash_session_run(args: dict[str, Any]) -> dict[str, Any]:
    sid = str(args.get("session_id") or "").strip()
    cmd = str(args.get("command") or "")
    timeout = args.get("timeout") or _DEFAULT_TIMEOUT
    if not sid:
        return {"status": "error", "error": "session_id is required"}
    if not cmd:
        return {"status": "error", "error": "command is required"}
    try:
        timeout = max(1.0, min(float(timeout), 300.0))
    except Exception:
        timeout = _DEFAULT_TIMEOUT
    with _registry_lock:
        sess = _sessions.get(sid)
    if sess is None:
        return {"status": "error", "error": f"unknown session_id {sid}"}
    if not sess.alive():
        with _registry_lock:
            _sessions.pop(sid, None)
        return {"status": "error", "error": "session terminated; open a new one"}
    result = sess.run(cmd, timeout=timeout)
    _persist_metadata()
    return result


def _exec_bash_session_close(args: dict[str, Any]) -> dict[str, Any]:
    sid = str(args.get("session_id") or "").strip()
    if not sid:
        return {"status": "error", "error": "session_id is required"}
    with _registry_lock:
        sess = _sessions.pop(sid, None)
    if sess is None:
        return {"status": "ok", "note": f"session {sid} was not open"}
    sess.close()
    _persist_metadata()
    return {"status": "ok", "session_id": sid, "closed": True}


def _exec_bash_session_list(_args: dict[str, Any]) -> dict[str, Any]:
    with _registry_lock:
        snapshot = [
            {
                "session_id": sid,
                "alive": s.alive(),
                "idle_seconds": int(time.time() - s.last_used),
            }
            for sid, s in _sessions.items()
        ]
    return {"status": "ok", "sessions": snapshot, "count": len(snapshot)}


BASH_SESSION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "bash_session_open",
            "description": (
                "Spawn a persistent bash shell. Returns a session_id you reuse "
                "across calls so cd, env-vars, virtualenvs, sourced files all "
                "persist. Use this instead of one-shot bash whenever you'll run "
                "more than one related command. Idle sessions die after 30 min."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash_session_run",
            "description": (
                "Run a command in an open bash session. Same shell state as "
                "previous calls (cd, env, aliases). Returns exit_code, output. "
                "Output capped at 32 KB. Default timeout 30s, max 300s."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Returned by bash_session_open."},
                    "command": {"type": "string", "description": "Shell command to run."},
                    "timeout": {"type": "number", "description": "Seconds before timing out (default 30, max 300)."},
                },
                "required": ["session_id", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash_session_close",
            "description": "Terminate a bash session and free its slot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
                "required": ["session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash_session_list",
            "description": "List currently open bash sessions and their idle time.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
