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


# ── operator_screenshot ─────────────────────────────────────────────────


async def operator_screenshot_async(
    *,
    user_id: str,
    display_id: int | None = None,
    save_path: str | None = None,
    format: str = "png",
    jpeg_quality: int = 85,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Capture a screenshot of the operator's desktop.

    Calls the JarvisX bridge which uses Electron's desktopCapturer. The
    bridge returns base64-encoded image bytes; here we decode and write
    them to a Jarvis-side temp file so the LLM can immediately pass the
    path to analyze_image.

    Returns {path, width, height, mime_type, display_id, operator_path?, bytes}.
    """
    import base64
    import tempfile
    import time
    from pathlib import Path

    args: dict[str, Any] = {"format": format, "jpeg_quality": int(jpeg_quality)}
    if display_id is not None:
        args["display_id"] = int(display_id)
    if save_path:
        args["save_path"] = str(save_path)

    raw = await _bridge_call(
        tool="operator_screenshot",
        args=args,
        user_id=user_id,
        timeout_s=timeout_s,
    )
    result = raw or {}
    data_b64 = result.get("data_base64")
    if not data_b64:
        raise RuntimeError("operator_screenshot returned no image data")

    img_bytes = base64.b64decode(data_b64)
    ext = "jpg" if str(result.get("mime_type", "")).endswith("jpeg") else "png"
    tmp = Path(tempfile.gettempdir()) / f"jarvisx-screenshot-{int(time.time() * 1000)}.{ext}"
    tmp.write_bytes(img_bytes)

    return {
        "path": str(tmp),
        "width": result.get("width"),
        "height": result.get("height"),
        "mime_type": result.get("mime_type"),
        "display_id": result.get("display_id"),
        "display_label": result.get("display_label"),
        "operator_path": result.get("operator_path"),
        "bytes": result.get("bytes") or len(img_bytes),
    }


# ── operator_open_url ───────────────────────────────────────────────────


async def operator_open_url_async(
    *,
    url: str,
    user_id: str,
    skip_approval: bool = False,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Open a URL in the operator s default browser. Returns {approved, opened, url}."""
    result = await _bridge_call(
        tool="operator_open_url",
        args={"url": str(url), "skip_approval": bool(skip_approval)},
        user_id=user_id,
        timeout_s=timeout_s + 25.0,
    )
    return result or {}


# ── operator_launch_app ─────────────────────────────────────────────────


async def operator_launch_app_async(
    *,
    path: str,
    user_id: str,
    args: list[str] | None = None,
    cwd: str | None = None,
    skip_approval: bool = False,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Launch an installed app on the operator s machine.

    `path` may be an absolute path (C:/Program Files/.../app.exe), a name
    resolvable on PATH (`notepad`, `code`, `chrome`), or a UWP shell URI
    (`shell:appsFolder\<AppId>` on Windows).

    Returns {approved, started, path, pid?, error?}.
    """
    bridge_args: dict[str, Any] = {
        "path": str(path),
        "skip_approval": bool(skip_approval),
    }
    if args:
        bridge_args["args"] = [str(a) for a in args]
    if cwd:
        bridge_args["cwd"] = str(cwd)
    result = await _bridge_call(
        tool="operator_launch_app",
        args=bridge_args,
        user_id=user_id,
        timeout_s=timeout_s + 25.0,
    )
    return result or {}


# ── operator_mouse_move ─────────────────────────────────────────────────


async def operator_mouse_move_async(
    *,
    x: int,
    y: int,
    user_id: str,
    smooth: bool = False,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Move the operator s mouse cursor to (x, y) screen coordinates."""
    result = await _bridge_call(
        tool="operator_mouse_move",
        args={"x": int(x), "y": int(y), "smooth": bool(smooth)},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_mouse_click ────────────────────────────────────────────────


async def operator_mouse_click_async(
    *,
    user_id: str,
    button: str = "left",
    double: bool = False,
    x: int | None = None,
    y: int | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Click the mouse on the operator s desktop, optionally moving first."""
    args: dict[str, Any] = {"button": str(button), "double": bool(double)}
    if x is not None:
        args["x"] = int(x)
    if y is not None:
        args["y"] = int(y)
    result = await _bridge_call(
        tool="operator_mouse_click",
        args=args,
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_mouse_position ─────────────────────────────────────────────


async def operator_mouse_position_async(
    *,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Get the current mouse cursor position on the operator s desktop."""
    result = await _bridge_call(
        tool="operator_mouse_position",
        args={},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_keyboard_type ──────────────────────────────────────────────


async def operator_keyboard_type_async(
    *,
    text: str,
    user_id: str,
    delay_ms: int | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Type a string into the operator s currently focused window."""
    args: dict[str, Any] = {"text": str(text)}
    if delay_ms is not None:
        args["delay_ms"] = int(delay_ms)
    result = await _bridge_call(
        tool="operator_keyboard_type",
        args=args,
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_keyboard_press ─────────────────────────────────────────────


async def operator_keyboard_press_async(
    *,
    keys: list[str] | str,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Press a single key or a hotkey combination on the operator s keyboard.

    `keys` may be a single string ("Enter", "F5") or a list of modifier+key
    (["Control", "C"] for Ctrl+C, ["Control", "Shift", "T"] for Ctrl+Shift+T).
    """
    args: dict[str, Any] = {
        "keys": [str(k) for k in keys] if isinstance(keys, (list, tuple)) else str(keys)
    }
    result = await _bridge_call(
        tool="operator_keyboard_press",
        args=args,
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_screen_size ────────────────────────────────────────────────


async def operator_screen_size_async(
    *,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Get the operator s primary display size in pixels."""
    result = await _bridge_call(
        tool="operator_screen_size",
        args={},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_browser_* ──────────────────────────────────────────────────


async def operator_browser_open_async(
    *, url: str, user_id: str, wait_until: str = "load",
    timeout_ms: int = 30000, timeout_s: float = 45.0,
) -> dict[str, Any]:
    """Navigate the browser session to URL. First call opens browser."""
    result = await _bridge_call(
        tool="operator_browser_open",
        args={"url": str(url), "wait_until": str(wait_until), "timeout_ms": int(timeout_ms)},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


async def operator_browser_get_text_async(
    *, user_id: str, selector: str | None = None, max_chars: int = 50000,
    timeout_s: float = 20.0,
) -> dict[str, Any]:
    args: dict[str, Any] = {"max_chars": int(max_chars)}
    if selector:
        args["selector"] = str(selector)
    result = await _bridge_call(
        tool="operator_browser_get_text", args=args, user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}


async def operator_browser_get_links_async(
    *, user_id: str, timeout_s: float = 20.0,
) -> dict[str, Any]:
    result = await _bridge_call(
        tool="operator_browser_get_links", args={}, user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}


async def operator_browser_click_async(
    *, selector: str, user_id: str, wait_navigation: bool = False,
    wait_for_selector: bool = True, timeout_ms: int = 5000, timeout_s: float = 25.0,
) -> dict[str, Any]:
    result = await _bridge_call(
        tool="operator_browser_click",
        args={
            "selector": str(selector),
            "wait_navigation": bool(wait_navigation),
            "wait_for_selector": bool(wait_for_selector),
            "timeout_ms": int(timeout_ms),
        },
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


async def operator_browser_type_async(
    *, selector: str, text: str, user_id: str,
    clear_first: bool = False, delay_ms: int = 0, timeout_s: float = 30.0,
) -> dict[str, Any]:
    result = await _bridge_call(
        tool="operator_browser_type",
        args={
            "selector": str(selector),
            "text": str(text),
            "clear_first": bool(clear_first),
            "delay_ms": int(delay_ms),
        },
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


async def operator_browser_screenshot_async(
    *, user_id: str, full_page: bool = False, format: str = "png",
    jpeg_quality: int = 85, timeout_s: float = 30.0,
) -> dict[str, Any]:
    """Screenshot the active browser page. Decoded to a Jarvis-side temp file."""
    import base64, tempfile, time
    from pathlib import Path
    raw = await _bridge_call(
        tool="operator_browser_screenshot",
        args={"full_page": bool(full_page), "format": str(format), "jpeg_quality": int(jpeg_quality)},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    result = raw or {}
    data_b64 = result.get("data_base64")
    if not data_b64:
        raise RuntimeError("operator_browser_screenshot returned no image data")
    img = base64.b64decode(data_b64)
    ext = "jpg" if str(result.get("mime_type", "")).endswith("jpeg") else "png"
    tmp = Path(tempfile.gettempdir()) / f"jarvisx-browser-{int(time.time() * 1000)}.{ext}"
    tmp.write_bytes(img)
    return {
        "path": str(tmp),
        "url": result.get("url"),
        "width": result.get("width"),
        "height": result.get("height"),
        "mime_type": result.get("mime_type"),
        "full_page": result.get("full_page"),
        "bytes": result.get("bytes") or len(img),
    }


async def operator_browser_evaluate_async(
    *, script: str, user_id: str, skip_approval: bool = False,
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    """Run JS in the page context. Requires approval unless skip_approval."""
    result = await _bridge_call(
        tool="operator_browser_evaluate",
        args={"script": str(script), "skip_approval": bool(skip_approval)},
        user_id=user_id,
        timeout_s=timeout_s + 25.0,
    )
    return result or {}


async def operator_browser_status_async(
    *, user_id: str, timeout_s: float = 10.0,
) -> dict[str, Any]:
    result = await _bridge_call(
        tool="operator_browser_status", args={}, user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}


async def operator_browser_close_async(
    *, user_id: str, timeout_s: float = 10.0,
) -> dict[str, Any]:
    result = await _bridge_call(
        tool="operator_browser_close", args={}, user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}
