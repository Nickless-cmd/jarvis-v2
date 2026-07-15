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


# ── operator_clipboard_read ─────────────────────────────────────────────


async def operator_clipboard_read_async(
    *,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Return current clipboard text from the operator's desktop."""
    result = await _bridge_call(
        tool="operator_clipboard_read",
        args={},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_clipboard_write ────────────────────────────────────────────


async def operator_clipboard_write_async(
    *,
    text: str,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Replace the operator's clipboard with the given text."""
    result = await _bridge_call(
        tool="operator_clipboard_write",
        args={"text": str(text)},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_list_windows ───────────────────────────────────────────────


async def operator_list_windows_async(
    *,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """List open windows on the operator's desktop. Returns {windows: [{title, id}]}."""
    result = await _bridge_call(
        tool="operator_list_windows",
        args={},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_focus_window ───────────────────────────────────────────────


async def operator_focus_window_async(
    *,
    user_id: str,
    title_substring: str | None = None,
    handle: int | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Bring a window to the foreground by title substring or handle/id."""
    args: dict[str, Any] = {}
    if title_substring is not None:
        args["title_substring"] = str(title_substring)
    if handle is not None:
        args["handle"] = int(handle)
    result = await _bridge_call(
        tool="operator_focus_window",
        args=args,
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_mouse_scroll ───────────────────────────────────────────────


async def operator_mouse_scroll_async(
    *,
    direction: str,
    user_id: str,
    amount: int = 3,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Scroll the mouse wheel in the given direction."""
    result = await _bridge_call(
        tool="operator_mouse_scroll",
        args={"direction": str(direction), "amount": int(amount)},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_mouse_drag ─────────────────────────────────────────────────


async def operator_mouse_drag_async(
    *,
    from_x: int,
    from_y: int,
    to_x: int,
    to_y: int,
    user_id: str,
    button: str = "left",
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Drag the mouse from (from_x, from_y) to (to_x, to_y)."""
    result = await _bridge_call(
        tool="operator_mouse_drag",
        args={
            "from_x": int(from_x),
            "from_y": int(from_y),
            "to_x": int(to_x),
            "to_y": int(to_y),
            "button": str(button),
        },
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_list_processes ─────────────────────────────────────────────


async def operator_list_processes_async(
    *,
    user_id: str,
    filter: str | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """List running processes on the operator's machine. Returns {processes: [{pid, name, cpu, memMB}]}."""
    args: dict[str, Any] = {}
    if filter is not None:
        args["filter"] = str(filter)
    result = await _bridge_call(
        tool="operator_list_processes",
        args=args,
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_kill_process ───────────────────────────────────────────────


async def operator_kill_process_async(
    *,
    pid: int,
    user_id: str,
    skip_approval: bool = False,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Kill a process by PID. Requires operator approval unless skip_approval=True."""
    result = await _bridge_call(
        tool="operator_kill_process",
        args={"pid": int(pid), "skip_approval": bool(skip_approval)},
        user_id=user_id,
        timeout_s=timeout_s + 25.0,
    )
    return result or {}


# ── operator_speak ──────────────────────────────────────────────────────


async def operator_speak_async(
    *,
    text: str,
    user_id: str,
    voice: str | None = None,
    rate: int = 5,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Say text aloud on the operator's machine via TTS (espeak-ng / SAPI)."""
    args: dict[str, Any] = {"text": str(text), "rate": int(rate)}
    if voice is not None:
        args["voice"] = str(voice)
    result = await _bridge_call(
        tool="operator_speak",
        args=args,
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_screenshot_window ──────────────────────────────────────────


async def operator_screenshot_window_async(
    *,
    user_id: str,
    title_substring: str | None = None,
    handle: str | None = None,
    save_path: str | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Capture a specific window on the operator's desktop. Returns base64 PNG or saves to path."""
    args: dict[str, Any] = {}
    if title_substring is not None:
        args["title_substring"] = str(title_substring)
    if handle is not None:
        args["handle"] = str(handle)
    if save_path is not None:
        args["save_path"] = str(save_path)
    result = await _bridge_call(
        tool="operator_screenshot_window",
        args=args,
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_find_image ─────────────────────────────────────────────────


async def operator_find_image_async(
    *,
    template_path: str,
    user_id: str,
    confidence: float = 0.85,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Template-match a small image inside the current screen. Returns {found, x, y, confidence}."""
    result = await _bridge_call(
        tool="operator_find_image",
        args={"template_path": str(template_path), "confidence": float(confidence)},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_ocr_region ─────────────────────────────────────────────────


async def operator_ocr_region_async(
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    user_id: str,
    lang: str = "eng",
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Extract text from a screen region using Tesseract OCR."""
    result = await _bridge_call(
        tool="operator_ocr_region",
        args={
            "x": int(x),
            "y": int(y),
            "width": int(width),
            "height": int(height),
            "lang": str(lang),
        },
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_notify ─────────────────────────────────────────────────────


async def operator_notify_async(
    *,
    title: str,
    body: str,
    user_id: str,
    icon: str | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Show an OS notification toast on the operator's machine via Electron Notification."""
    args: dict[str, Any] = {"title": str(title), "body": str(body)}
    if icon is not None:
        args["icon"] = str(icon)
    result = await _bridge_call(
        tool="operator_notify",
        args=args,
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_watch_folder ───────────────────────────────────────────────


async def operator_watch_folder_async(
    *,
    path: str,
    user_id: str,
    recursive: bool = False,
    debounce_ms: int = 500,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Start watching a folder for changes on the operator's machine. Returns {watcher_id}."""
    result = await _bridge_call(
        tool="operator_watch_folder",
        args={"path": str(path), "recursive": bool(recursive), "debounce_ms": int(debounce_ms)},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


async def operator_unwatch_folder_async(
    *,
    watcher_id: str,
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Stop a folder watcher by watcher_id. Returns {stopped: true}."""
    result = await _bridge_call(
        tool="operator_unwatch_folder",
        args={"watcher_id": str(watcher_id)},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


async def operator_watch_events_async(
    *,
    watcher_id: str,
    user_id: str,
    max: int = 100,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Poll buffered filesystem events for a watcher. Returns {events: [...]} and clears buffer."""
    result = await _bridge_call(
        tool="operator_watch_events",
        args={"watcher_id": str(watcher_id), "max": int(max)},
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}


# ── operator_record_audio ───────────────────────────────────────────────


async def operator_record_audio_async(
    *,
    duration_s: int,
    user_id: str,
    output_path: str | None = None,
    device: str | None = None,
    skip_approval: bool = False,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Record N seconds of microphone audio on the operator's machine. Requires approval."""
    args: dict[str, Any] = {
        "duration_s": int(duration_s),
        "skip_approval": bool(skip_approval),
    }
    if output_path is not None:
        args["output_path"] = str(output_path)
    if device is not None:
        args["device"] = str(device)
    result = await _bridge_call(
        tool="operator_record_audio",
        args=args,
        user_id=user_id,
        timeout_s=timeout_s,
    )
    return result or {}



# ── operator_reminder / operator_wakeup / operator_scheduled_* ─────────


async def operator_reminder_async(
    *, when: str, message: str, title: str | None = None,
    user_id: str, timeout_s: float = 15.0,
) -> dict[str, Any]:
    args: dict[str, Any] = {"when": str(when), "message": str(message)}
    if title:
        args["title"] = str(title)
    result = await _bridge_call(
        tool="operator_reminder", args=args, user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}


async def operator_wakeup_async(
    *, when: str, message: str | None = None, title: str | None = None,
    user_id: str, timeout_s: float = 15.0,
) -> dict[str, Any]:
    args: dict[str, Any] = {"when": str(when)}
    if message:
        args["message"] = str(message)
    if title:
        args["title"] = str(title)
    result = await _bridge_call(
        tool="operator_wakeup", args=args, user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}


async def operator_scheduled_list_async(
    *, user_id: str, kind: str | None = None, include_fired: bool = False,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    args: dict[str, Any] = {"include_fired": bool(include_fired)}
    if kind:
        args["kind"] = str(kind)
    result = await _bridge_call(
        tool="operator_scheduled_list", args=args, user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}


async def operator_scheduled_cancel_async(
    *, id: str, user_id: str, timeout_s: float = 15.0,
) -> dict[str, Any]:
    result = await _bridge_call(
        tool="operator_scheduled_cancel", args={"id": str(id)},
        user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}


# ── operator_process_spawn / _status / _output / _kill / _list ────────


async def operator_process_spawn_async(
    *, cmd: str, user_id: str, cwd: str | None = None, label: str | None = None,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    args: dict[str, Any] = {"cmd": str(cmd)}
    if cwd:
        args["cwd"] = str(cwd)
    if label:
        args["label"] = str(label)
    result = await _bridge_call(
        tool="operator_process_spawn", args=args, user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}


async def operator_process_status_async(
    *, id: str, user_id: str, timeout_s: float = 10.0,
) -> dict[str, Any]:
    result = await _bridge_call(
        tool="operator_process_status", args={"id": str(id)},
        user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}


async def operator_process_output_async(
    *, id: str, user_id: str, since_offset: int = 0, max_bytes: int = 64_000,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    result = await _bridge_call(
        tool="operator_process_output",
        args={"id": str(id), "since_offset": int(since_offset), "max_bytes": int(max_bytes)},
        user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}


async def operator_process_kill_async(
    *, id: str, user_id: str, signal: str = "SIGTERM", timeout_s: float = 10.0,
) -> dict[str, Any]:
    result = await _bridge_call(
        tool="operator_process_kill", args={"id": str(id), "signal": str(signal)},
        user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}


async def operator_process_list_async(
    *, user_id: str, include_finished: bool = True, timeout_s: float = 10.0,
) -> dict[str, Any]:
    result = await _bridge_call(
        tool="operator_process_list", args={"include_finished": bool(include_finished)},
        user_id=user_id, timeout_s=timeout_s,
    )
    return result or {}


# ── operator_session_* — owner-gated backup channel for jarvis-code ─────────
#
# A persistent operator session that jarvis-code's client-side `bash` reroutes
# through when a command targets a path OUTSIDE the client bwrap sandbox (e.g.
# /media/projects). Dispatches via the bridge with skip_approval=True so there
# is NO per-reroute approval dialog — the owner opts in ONCE on the client
# (operator_channel(open=True)); every subsequent reroute is dialog-free.
#
# STEP-0 FINDING: the bridge protocol ALREADY carries a skip_approval flag
# (operator_bash_async → bridge_registry.dispatch args["skip_approval"]), so NO
# dedicated bridge route is needed — these tools reuse the existing path via
# simple_tools_operator._exec_operator_bash (which passes skip_approval=True).
#
# Owner-only: a real non-owner role is refused server-side too (defense in
# depth on top of the client owner-gate).
#
# Spec: docs/superpowers/specs/2026-07-14-operator-channel-design.md

import threading as _threading
import time as _time
import uuid as _uuid

_OPERATOR_SESSIONS: dict[str, dict[str, Any]] = {}
_OP_SESS_LOCK = _threading.Lock()
_OP_SESS_IDLE_TTL = 1800.0  # 30 min, matching operator_bash_session


def _op_sess_now() -> float:
    return _time.time()


def _op_sess_reap() -> None:
    cutoff = _op_sess_now() - _OP_SESS_IDLE_TTL
    with _OP_SESS_LOCK:
        for sid in [s for s, v in _OPERATOR_SESSIONS.items()
                    if v.get("last", 0.0) < cutoff]:
            _OPERATOR_SESSIONS.pop(sid, None)


def _op_sess_owner_denied() -> str | None:
    """Denial reason if the caller is a real non-owner role, else None.

    Owner and unbound ("" — trusted internal/daemon callers) pass. This is a
    server-side backstop; the client already owner-gates operator_channel.
    """
    try:
        from core.identity.workspace_context import effective_role
        role = str(effective_role() or "")
    except Exception:
        role = ""
    if role and role != "owner":
        return f"access denied: operator_session is owner-only (role={role})"
    return None


def _op_sess_user_id(args: dict[str, Any]) -> str:
    from core.tools.simple_tools_operator import _operator_user_id
    return _operator_user_id(args)


def _op_dispatch_bash(command: str, *, user_id: str, cwd: str | None,
                      timeout_s: float) -> dict[str, Any]:
    """Dispatch a command via the bridge with skip_approval=True (reuses the
    existing operator_bash path). Returns simple_tools_operator's
    {status, result|error} envelope."""
    from core.tools.simple_tools import _exec_operator_bash
    op_args: dict[str, Any] = {
        "command": command, "_user_id": user_id, "timeout_s": timeout_s,
    }
    if cwd:
        op_args["cwd"] = cwd
    return _exec_operator_bash(op_args)


def _exec_operator_session_open(args: dict[str, Any]) -> dict[str, Any]:
    """Open a persistent operator session. Owner-only. Probes the bridge with a
    no-op so an unavailable companion app fails fast (edge case 9)."""
    denied = _op_sess_owner_denied()
    if denied:
        return {"status": "error", "error": denied}
    _op_sess_reap()
    uid = _op_sess_user_id(args)
    # Liveness probe: a no-op bash over the bridge proves the companion app is
    # reachable BEFORE we hand back a session (edge case 9).
    probe = _op_dispatch_bash("true", user_id=uid, cwd=None, timeout_s=10.0)
    if str((probe or {}).get("status")) == "error":
        return {"status": "error",
                "error": str(probe.get("error") or "bridge_not_connected")}
    sid = "opchan-" + _uuid.uuid4().hex[:12]
    with _OP_SESS_LOCK:
        _OPERATOR_SESSIONS[sid] = {"user_id": uid, "last": _op_sess_now()}
    return {"status": "ok", "session_id": sid}


def _exec_operator_session_run(args: dict[str, Any]) -> dict[str, Any]:
    """Run a command in an operator session via the bridge WITHOUT an approval
    dialog (skip_approval=True). Owner-only. Flattens the bridge result so the
    client sees stdout/stderr/exit_code at the top level."""
    denied = _op_sess_owner_denied()
    if denied:
        return {"status": "error", "error": denied}
    sid = str(args.get("session_id") or "").strip()
    cmd = str(args.get("command") or "")
    if not cmd:
        return {"status": "error", "error": "command is required"}
    with _OP_SESS_LOCK:
        sess = _OPERATOR_SESSIONS.get(sid)
    if sid and sess is None:
        return {"status": "error",
                "error": "unknown session_id (udløbet?) — kald operator_session_open"}
    uid = (sess or {}).get("user_id") or _op_sess_user_id(args)
    try:
        timeout_s = max(1.0, min(float(args.get("timeout") or args.get("timeout_s") or 30.0), 300.0))
    except Exception:
        timeout_s = 30.0
    res = _op_dispatch_bash(cmd, user_id=uid, cwd=args.get("cwd"), timeout_s=timeout_s)
    if sess is not None:
        with _OP_SESS_LOCK:
            if sid in _OPERATOR_SESSIONS:
                _OPERATOR_SESSIONS[sid]["last"] = _op_sess_now()
    if isinstance(res, dict) and str(res.get("status")) == "error":
        return {"status": "error",
                "error": str(res.get("error") or "operator_bash failed"),
                "session_id": sid or None}
    inner = res.get("result") if isinstance(res, dict) else None
    out: dict[str, Any] = {"status": "ok", "session_id": sid or None}
    if isinstance(inner, dict):
        for k in ("stdout", "stderr", "exit_code", "timed_out", "approved"):
            if k in inner:
                out[k] = inner[k]
    else:
        out["result"] = inner
    return out


def _exec_operator_session_close(args: dict[str, Any]) -> dict[str, Any]:
    """Close an operator session (owner-only)."""
    denied = _op_sess_owner_denied()
    if denied:
        return {"status": "error", "error": denied}
    sid = str(args.get("session_id") or "").strip()
    with _OP_SESS_LOCK:
        sess = _OPERATOR_SESSIONS.pop(sid, None)
    return {"status": "ok", "closed": bool(sess)}


OPERATOR_SESSION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "operator_session_open",
        "description": (
            "Owner-only. Åbn en vedvarende operator-session (backup-kanal for "
            "jarvis-code). Kald bruges af klientens operator_channel — reroute af "
            "bash til stier udenfor klient-sandboxen, uden approval-dialog. Fejler "
            "hvis JarvisX companion-appen ikke kører."),
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "operator_session_run",
        "description": (
            "Owner-only. Kør en kommando på operatorens maskine via broen UDEN "
            "approval-dialog (skip_approval). Bruges af klientens bash-reroute."),
        "parameters": {"type": "object", "properties": {
            "session_id": {"type": "string",
                           "description": "Returneret af operator_session_open."},
            "command": {"type": "string", "description": "Shell-kommando."},
            "cwd": {"type": "string", "description": "Arbejdsmappe (valgfri)."},
            "timeout": {"type": "number",
                        "description": "Sekunder før timeout (default 30, max 300)."}},
            "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "operator_session_close",
        "description": "Owner-only. Luk en operator-session.",
        "parameters": {"type": "object", "properties": {
            "session_id": {"type": "string"}}, "required": ["session_id"]}}},
]
