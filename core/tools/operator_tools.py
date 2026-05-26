"""Operator-side tools — execute on operator's desktop via JarvisX bridge.

These tools route via `core.services.jarvisx_bridge` to the JarvisX
Electron-app running on the operator's local machine. They fail with
`bridge_not_connected` if the app is not running.

Phase 2 adds the filesystem-complete set: write_file, edit_file, glob,
grep, list_dir. Each is a thin async wrapper around bridge_registry.dispatch.

Spec: docs/superpowers/specs/2026-05-26-jarvisx-tool-bridge.md
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_S = 30.0


async def _bridge_call(
    *,
    tool: str,
    args: dict[str, Any],
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> Any:
    """Common dispatch helper. Raises RuntimeError on bridge failure."""
    from core.services.jarvisx_bridge import bridge_registry

    result = await bridge_registry.dispatch(
        user_id=user_id, tool=tool, args=args, timeout_s=timeout_s,
    )
    if result.get("status") != "ok":
        err = str(result.get("error") or "unknown")
        raise RuntimeError(f"{tool} failed: {err}")
    return result.get("result")


# ── operator_read_file ──────────────────────────────────────────────────


async def operator_read_file_async(
    *, path: str, user_id: str, timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> str:
    """Read a file from the operator's desktop."""
    result = await _bridge_call(
        tool="operator_read_file",
        args={"path": str(path)},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return str(result or "")


def operator_read_file(*, path: str, user_id: str, timeout_s: float = _DEFAULT_TIMEOUT_S) -> str:
    return asyncio.run(operator_read_file_async(path=path, user_id=user_id, timeout_s=timeout_s))


# ── operator_write_file ─────────────────────────────────────────────────


async def operator_write_file_async(
    *,
    path: str,
    content: str,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Write content to a file on the operator's desktop. Creates parents
    as needed. Returns {bytes_written, path}.
    """
    result = await _bridge_call(
        tool="operator_write_file",
        args={"path": str(path), "content": str(content)},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_edit_file ──────────────────────────────────────────────────


async def operator_edit_file_async(
    *,
    path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Find/replace in a file on the operator's desktop. Returns
    {replacements: int, path}. Errors if old_string not found, or if
    replace_all=False and old_string appears more than once.
    """
    result = await _bridge_call(
        tool="operator_edit_file",
        args={
            "path": str(path),
            "old_string": str(old_string),
            "new_string": str(new_string),
            "replace_all": bool(replace_all),
        },
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_glob ───────────────────────────────────────────────────────


async def operator_glob_async(
    *,
    pattern: str,
    cwd: str | None = None,
    max_results: int = 200,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> list[str]:
    """Find files matching a glob pattern on the operator's desktop.
    pattern like '**/*.py'. cwd defaults to operator's home directory.
    """
    result = await _bridge_call(
        tool="operator_glob",
        args={
            "pattern": str(pattern),
            "cwd": str(cwd) if cwd else None,
            "max_results": int(max_results),
        },
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return list(result or [])


# ── operator_grep ───────────────────────────────────────────────────────


async def operator_grep_async(
    *,
    pattern: str,
    path: str | None = None,
    glob: str | None = None,
    case_insensitive: bool = False,
    max_results: int = 200,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> list[dict[str, Any]]:
    """Search for regex pattern in files on the operator's desktop.
    Returns list of {file, line, text} matches.
    """
    result = await _bridge_call(
        tool="operator_grep",
        args={
            "pattern": str(pattern),
            "path": str(path) if path else None,
            "glob": str(glob) if glob else None,
            "case_insensitive": bool(case_insensitive),
            "max_results": int(max_results),
        },
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return list(result or [])


# ── operator_list_dir ───────────────────────────────────────────────────


async def operator_list_dir_async(
    *,
    path: str,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> list[dict[str, Any]]:
    """List directory contents on the operator's desktop.
    Returns list of {name, type: file|dir|symlink, size}.
    """
    result = await _bridge_call(
        tool="operator_list_dir",
        args={"path": str(path)},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return list(result or [])


# ── operator_webfetch ───────────────────────────────────────────────────


async def operator_webfetch_async(
    *,
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: str | None = None,
    timeout_s: float = 30.0,
    user_id: str,
) -> dict[str, Any]:
    """Fetch a URL from the operator's local network via the bridge.

    Useful for reaching private services on the operator's LAN that
    Jarvis (in his LXC) can't reach directly — e.g. router admin
    pages, local Docker services, intranet sites.

    Returns {status, headers, body, content_type}. Body is truncated
    at ~100KB; binary content returned as base64.
    """
    result = await _bridge_call(
        tool="operator_webfetch",
        args={
            "url": str(url),
            "method": str(method).upper(),
            "headers": dict(headers) if headers else None,
            "body": str(body) if body else None,
            "timeout_s": float(timeout_s),
        },
        user_id=user_id,
        timeout_s=timeout_s + 30.0,
    )
    return result or {}


# ── operator_bash ───────────────────────────────────────────────────────


async def operator_bash_async(
    *,
    command: str,
    cwd: str | None = None,
    timeout_s: float = 30.0,
    user_id: str,
    skip_approval: bool = False,
) -> dict[str, Any]:
    """Run a shell command on the operator's desktop.

    By default the JarvisX-app shows the operator a dialog with the full
    command before running. When skip_approval=True (e.g. operator opted
    into "Trust All" in composer, or autonomous run), the bridge runs the
    command directly without prompting.

    Returns {stdout, stderr, exit_code, timed_out, approved}.
    """
    # Cap at 5 min to prevent ridiculous timeouts
    timeout_s = min(max(timeout_s, 1.0), 300.0)
    # Bridge-call timeout: command timeout + 25s (20s dialog auto-reject + 5s slack).
    # If operator doesn't respond to the approval dialog within 20s, bridge
    # auto-rejects so Jarvis' agentic loop isn't blocked for minutes.
    # When skip_approval=True, the 25s buffer is overkill but harmless.
    result = await _bridge_call(
        tool="operator_bash",
        args={
            "command": str(command),
            "cwd": str(cwd) if cwd else None,
            "timeout_s": float(timeout_s),
            "skip_approval": bool(skip_approval),
        },
        user_id=user_id,
        timeout_s=timeout_s + 25.0,
    )
    return result or {}
