"""Persistent bash sessions — Jarvis' one-shot bash forced him to restart his
shell mental model with every call. ``cd /repo`` didn't survive, virtualenvs
had to be re-activated, env-vars vanished. This is the single largest UX gap
between Claude Code's harness and Jarvis' own toolset.

Architecture:
- jarvis-api runs 4 uvicorn workers; each worker has its own process memory.
  A bash session opened in worker A is invisible to worker B, so the very
  next turn — load-balanced to a different worker — sees "unknown session_id"
  and Jarvis loses all shell state.
- Fix: a singleton **bash session daemon** owns every session. The daemon
  listens on a Unix socket; any worker (or the runtime, or a CLI) opens the
  socket and proxies the call. The first process to need a session spawns
  the daemon (file-lock guarded so only one ever runs).

Wire protocol: line-delimited JSON over the socket.
- Request: {"op": "open"|"run"|"close"|"list", ...args}
- Response: {"status": "ok"|"error", ...payload}

Containment:
- Subprocess inherits the same env Jarvis runs in (no privilege escalation).
- Output capped per call to keep the model context bounded.
- Hard cap of 8 concurrent sessions to prevent runaway spawn.
- Daemon idle-reaps sessions after 30 minutes of inactivity.
- Daemon itself self-exits if it has had no sessions for 60 minutes.
"""
from __future__ import annotations

import fcntl
import json
import logging
import os
import pty
import select
import signal
import socket
import subprocess
import sys
import termios
import threading
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STATE_DIR = Path.home() / ".jarvis-v2" / "state"
_SOCKET_PATH = _STATE_DIR / "bash_session.sock"
_LOCK_PATH = _STATE_DIR / "bash_session.lock"
_DAEMON_LOG = _STATE_DIR / "bash_session_daemon.log"
_MAX_SESSIONS = 8
_OUTPUT_LIMIT_BYTES = 32 * 1024
_DEFAULT_TIMEOUT = 30
_IDLE_SESSION_TTL = 30 * 60
_IDLE_DAEMON_TTL = 60 * 60
_CLIENT_CONNECT_TIMEOUT = 5.0


# ─────────────────────────────────────────────────────────────────────
#  _Session — owns a single PTY-backed bash subprocess.
#  Lives only inside the daemon process.
# ─────────────────────────────────────────────────────────────────────


class _Session:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.lock = threading.Lock()
        self.last_used = time.time()
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            try:
                os.execvpe(
                    "bash",
                    ["bash", "--noprofile", "--norc", "-i"],
                    dict(os.environ, PS1="", PS2="", TERM="dumb"),
                )
            except Exception:
                os._exit(127)
        try:
            attrs = termios.tcgetattr(self.fd)
            attrs[3] &= ~termios.ECHO
            termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        except Exception:
            pass
        time.sleep(0.2)
        self._drain_pending(timeout=0.4)

    def _drain_pending(self, timeout: float) -> None:
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
    try:
        return buf.decode("utf-8", errors="replace").replace("\r\n", "\n")
    except Exception:
        return repr(buf)


# ─────────────────────────────────────────────────────────────────────
#  Daemon server — runs in a single dedicated process.
# ─────────────────────────────────────────────────────────────────────


def _daemon_main() -> int:
    """Singleton bash-session daemon. Listens on the Unix socket, owns sessions."""
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    log = open(_DAEMON_LOG, "a", buffering=1)
    log.write(f"[{time.time():.0f}] daemon starting pid={os.getpid()}\n")

    try:
        if _SOCKET_PATH.exists():
            _SOCKET_PATH.unlink()
    except OSError:
        pass

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(str(_SOCKET_PATH))
    except OSError as exc:
        log.write(f"bind failed: {exc}\n")
        return 1
    sock.listen(16)
    os.chmod(_SOCKET_PATH, 0o600)

    sessions: dict[str, _Session] = {}
    sess_lock = threading.Lock()
    last_activity = [time.time()]

    def _reaper() -> None:
        while True:
            time.sleep(60)
            now = time.time()
            with sess_lock:
                stale = [
                    sid for sid, s in sessions.items()
                    if (not s.alive()) or (now - s.last_used > _IDLE_SESSION_TTL)
                ]
                for sid in stale:
                    s = sessions.pop(sid, None)
                    if s is not None:
                        s.close()
                        log.write(f"[{now:.0f}] reaped session {sid}\n")
                # Self-exit if no sessions and idle > daemon TTL
                if not sessions and (now - last_activity[0] > _IDLE_DAEMON_TTL):
                    log.write(f"[{now:.0f}] daemon self-exit (idle)\n")
                    os._exit(0)

    threading.Thread(target=_reaper, name="bash-daemon-reaper", daemon=True).start()

    def _handle(client: socket.socket) -> None:
        try:
            client.settimeout(310.0)
            data = b""
            while b"\n" not in data:
                chunk = client.recv(8192)
                if not chunk:
                    return
                data += chunk
                if len(data) > 1_000_000:
                    return
            line = data.split(b"\n", 1)[0]
            try:
                req = json.loads(line.decode("utf-8"))
            except Exception as exc:
                _send(client, {"status": "error", "error": f"bad json: {exc}"})
                return
            last_activity[0] = time.time()
            op = str(req.get("op") or "").strip()

            if op == "open":
                with sess_lock:
                    alive_count = sum(1 for s in sessions.values() if s.alive())
                    if alive_count >= _MAX_SESSIONS:
                        for sid in [sid for sid, s in sessions.items() if not s.alive()]:
                            sessions.pop(sid, None)
                        if sum(1 for s in sessions.values() if s.alive()) >= _MAX_SESSIONS:
                            _send(client, {"status": "error",
                                           "error": f"max {_MAX_SESSIONS} concurrent sessions"})
                            return
                    sid = f"bsh-{uuid.uuid4().hex[:10]}"
                    try:
                        sessions[sid] = _Session(sid)
                    except Exception as exc:
                        _send(client, {"status": "error", "error": f"spawn failed: {exc}"})
                        return
                _send(client, {"status": "ok", "session_id": sid})

            elif op == "run":
                sid = str(req.get("session_id") or "")
                cmd = str(req.get("command") or "")
                timeout = req.get("timeout") or _DEFAULT_TIMEOUT
                with sess_lock:
                    sess = sessions.get(sid)
                if sess is None:
                    _send(client, {"status": "error", "error": f"unknown session_id {sid}"})
                    return
                if not sess.alive():
                    with sess_lock:
                        sessions.pop(sid, None)
                    _send(client, {"status": "error", "error": "session terminated; open a new one"})
                    return
                try:
                    timeout = max(1.0, min(float(timeout), 300.0))
                except Exception:
                    timeout = _DEFAULT_TIMEOUT
                result = sess.run(cmd, timeout=timeout)
                _send(client, result)

            elif op == "close":
                sid = str(req.get("session_id") or "")
                with sess_lock:
                    sess = sessions.pop(sid, None)
                if sess is None:
                    _send(client, {"status": "ok", "note": f"session {sid} was not open"})
                else:
                    sess.close()
                    _send(client, {"status": "ok", "session_id": sid, "closed": True})

            elif op == "list":
                with sess_lock:
                    snapshot = [
                        {"session_id": sid, "alive": s.alive(),
                         "idle_seconds": int(time.time() - s.last_used)}
                        for sid, s in sessions.items()
                    ]
                _send(client, {"status": "ok", "sessions": snapshot, "count": len(snapshot)})

            elif op == "ping":
                _send(client, {"status": "ok", "pong": True})

            else:
                _send(client, {"status": "error", "error": f"unknown op: {op}"})
        except Exception as exc:
            log.write(f"handler error: {exc}\n")
            try:
                _send(client, {"status": "error", "error": f"handler crash: {exc}"})
            except Exception:
                pass
        finally:
            try:
                client.close()
            except Exception:
                pass

    while True:
        try:
            client, _ = sock.accept()
        except Exception as exc:
            log.write(f"accept error: {exc}\n")
            time.sleep(0.5)
            continue
        threading.Thread(target=_handle, args=(client,), daemon=True).start()


def _send(client: socket.socket, payload: dict[str, Any]) -> None:
    try:
        client.sendall((json.dumps(payload) + "\n").encode("utf-8"))
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────
#  Client — every worker uses this. Auto-spawns daemon on demand.
# ─────────────────────────────────────────────────────────────────────


def _ensure_daemon_running() -> bool:
    """Return True if a reachable daemon exists. Spawn one if not."""
    if _ping_daemon():
        return True
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Use a file lock to ensure only one process spawns the daemon.
    lock_fd = os.open(str(_LOCK_PATH), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            got_lock = True
        except BlockingIOError:
            got_lock = False
        if got_lock:
            # We own the lock; spawn the daemon.
            _spawn_daemon()
            # Wait briefly for socket to come up.
            for _ in range(40):
                if _ping_daemon():
                    return True
                time.sleep(0.1)
            return _ping_daemon()
        # Someone else is spawning. Wait for them.
        for _ in range(60):
            if _ping_daemon():
                return True
            time.sleep(0.1)
        return _ping_daemon()
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except Exception:
            pass
        os.close(lock_fd)


def _spawn_daemon() -> None:
    """Fork a detached daemon process running _daemon_main()."""
    args = [sys.executable, "-m", "core.tools.bash_session", "--daemon"]
    try:
        subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except Exception as exc:
        logger.warning("bash_session: spawn daemon failed: %s", exc)


def _ping_daemon() -> bool:
    if not _SOCKET_PATH.exists():
        return False
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect(str(_SOCKET_PATH))
        s.sendall(b'{"op":"ping"}\n')
        data = b""
        while b"\n" not in data:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
        s.close()
        return b'"pong": true' in data or b'"pong":true' in data
    except Exception:
        return False


def _client_call(payload: dict[str, Any], timeout: float = 310.0) -> dict[str, Any]:
    if not _ensure_daemon_running():
        return {"status": "error", "error": "bash session daemon unavailable"}
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(_CLIENT_CONNECT_TIMEOUT)
        s.connect(str(_SOCKET_PATH))
        s.settimeout(timeout)
        s.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        data = b""
        while b"\n" not in data:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
            if len(data) > 4_000_000:
                break
        s.close()
        line = data.split(b"\n", 1)[0]
        if not line:
            return {"status": "error", "error": "empty response from daemon"}
        return json.loads(line.decode("utf-8"))
    except Exception as exc:
        return {"status": "error", "error": f"daemon ipc failed: {exc}"}


# ─────────────────────────────────────────────────────────────────────
#  Tool entrypoints (unchanged signatures — drop-in replacement).
# ─────────────────────────────────────────────────────────────────────


def _exec_bash_session_open(args: dict[str, Any]) -> dict[str, Any]:
    return _client_call({"op": "open"}, timeout=10.0)


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
    return _client_call(
        {"op": "run", "session_id": sid, "command": cmd, "timeout": timeout},
        timeout=timeout + 10.0,
    )


def _exec_bash_session_close(args: dict[str, Any]) -> dict[str, Any]:
    sid = str(args.get("session_id") or "").strip()
    if not sid:
        return {"status": "error", "error": "session_id is required"}
    return _client_call({"op": "close", "session_id": sid}, timeout=10.0)


def _exec_bash_session_list(_args: dict[str, Any]) -> dict[str, Any]:
    return _client_call({"op": "list"}, timeout=5.0)


BASH_SESSION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "bash_session_open",
            "description": (
                "Spawn a persistent bash shell. Returns a session_id you reuse "
                "across calls so cd, env-vars, virtualenvs, sourced files all "
                "persist. Sessions live in a singleton daemon — they survive "
                "across all jarvis-api workers and across worker round-robin. "
                "Idle sessions die after 30 min."
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
                "properties": {"session_id": {"type": "string"}},
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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        sys.exit(_daemon_main())
