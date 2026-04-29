"""Find a live host Claude Code OAuth token to inject into `claude -p` spawns.

Background (2026-04-29 finding):
The Max-subscription `.credentials.json` token alone returns 401 when used
by `claude -p` from a service context. Headless `claude -p` calls authenticate
via the *session-specific* `CLAUDE_CODE_OAUTH_TOKEN` env var that the desktop
Claude Code app exports for its child processes — that token validates,
where the bare credentials.json one doesn't.

This module finds a running Claude Code host process owned by the same user
and reads its `CLAUDE_CODE_OAUTH_TOKEN` from `/proc/<pid>/environ`. The
dispatch runner injects it into the `claude -p` subprocess env so the
spawn can authenticate using the live host's session.

Limitations:
  * Requires that *some* Claude Code session is open by the same user when
    Jarvis dispatches. If the user has closed all Claude Code instances,
    no token is available and dispatch will fail with a clear error.
  * Token rotates with the host's session; we re-read on every dispatch
    rather than cache, so a host restart is picked up transparently.

This is intentionally read-only and side-effect-free; failures return
None so the caller can surface a precise diagnostic.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


_TOKEN_ENV_KEY = "CLAUDE_CODE_OAUTH_TOKEN"
_HOST_HINT_ENV_KEYS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")


def _process_start_time(pid: str) -> float:
    """Return process start time (seconds since boot) from /proc/<pid>/stat.

    Field 22 of /proc/<pid>/stat is starttime in clock ticks since boot.
    Higher value = newer process. Returns 0.0 on any failure so the
    process sorts to the end of a "newest first" list (de-prioritised).
    """
    try:
        stat_text = (Path("/proc") / pid / "stat").read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, OSError):
        return 0.0
    # The comm field (field 2) can contain spaces/parens, so we have to
    # split after the last ')'.
    rparen = stat_text.rfind(")")
    if rparen < 0:
        return 0.0
    fields = stat_text[rparen + 1:].split()
    # After comm: state(0), ppid(1), pgrp(2), session(3), tty_nr(4),
    # tpgid(5), flags(6), minflt(7), cminflt(8), majflt(9), cmajflt(10),
    # utime(11), stime(12), cutime(13), cstime(14), priority(15), nice(16),
    # num_threads(17), itrealvalue(18), starttime(19) — i.e., index 19
    # into the post-comm split.
    if len(fields) <= 19:
        return 0.0
    try:
        return float(fields[19])
    except (ValueError, IndexError):
        return 0.0


def find_host_oauth_token() -> str | None:
    """Return a live host CLAUDE_CODE_OAUTH_TOKEN, or None if no host is running.

    Strategy:
      1. Walk /proc, gather every Claude Code host process owned by our
         UID that has a non-empty CLAUDE_CODE_OAUTH_TOKEN
      2. Sort by process start time, newest first
      3. Return the token from the most recently started host

    Why "newest first": OAuth tokens rotate when host sessions refresh
    or new sessions start. An older process can hold a stale (expired)
    token while a newer process holds a valid one — picking the newest
    is the cheapest correct heuristic without making a probe API call.
    """
    our_uid = os.getuid()

    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return None

    candidates: list[tuple[float, str, str]] = []  # (starttime, pid, token)

    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = entry.name

        try:
            stat = entry.stat()
        except (FileNotFoundError, PermissionError, OSError):
            continue
        if stat.st_uid != our_uid:
            continue

        environ_path = entry / "environ"
        try:
            raw = environ_path.read_bytes()
        except (FileNotFoundError, PermissionError, OSError):
            continue

        env_pairs: dict[str, str] = {}
        for chunk in raw.split(b"\x00"):
            if not chunk or b"=" not in chunk:
                continue
            try:
                key, value = chunk.decode("utf-8", errors="replace").split("=", 1)
            except ValueError:
                continue
            env_pairs[key] = value

        token = env_pairs.get(_TOKEN_ENV_KEY, "").strip()
        if not token:
            continue

        # Defensive: only accept tokens from processes that actually look
        # like Claude Code hosts. Avoids picking up a stale shell that
        # inherited the var from a long-dead session.
        if not any(env_pairs.get(k) for k in _HOST_HINT_ENV_KEYS):
            continue

        candidates.append((_process_start_time(pid), pid, token))

    if not candidates:
        return None

    # Newest process first — its token is most likely valid.
    candidates.sort(key=lambda x: x[0], reverse=True)
    starttime, pid, token = candidates[0]
    logger.debug(
        "dispatch.host_oauth: selected token from pid=%s starttime=%.0f "
        "(of %d Claude Code host candidates)",
        pid, starttime, len(candidates),
    )
    return token
