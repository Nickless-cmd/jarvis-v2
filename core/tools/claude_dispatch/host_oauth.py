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


def find_host_oauth_token() -> str | None:
    """Return a live host CLAUDE_CODE_OAUTH_TOKEN, or None if no host is running.

    Strategy:
      1. Walk /proc looking for processes owned by our UID
      2. Read each one's environ
      3. Return the first non-empty CLAUDE_CODE_OAUTH_TOKEN found that is
         accompanied by a Claude Code host hint (CLAUDECODE=1 or
         CLAUDE_CODE_ENTRYPOINT set), so we don't pick up some unrelated
         process that happens to have the var set.
    """
    our_uid = os.getuid()

    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return None

    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = entry.name

        # Cheap UID gate — skip other users' processes early
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

        logger.debug(
            "dispatch.host_oauth: found token via pid=%s (entrypoint=%s)",
            pid, env_pairs.get("CLAUDE_CODE_ENTRYPOINT", "?"),
        )
        return token

    return None
