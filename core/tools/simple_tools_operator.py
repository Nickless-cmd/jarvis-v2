"""Operator-bridge tool executors for Jarvis (desktop operator lane).

Udskilt fra ``simple_tools.py`` (Boy Scout, 2026-07): alle ``_exec_operator_*``
handlers + deres delte hjælpere (``_operator_user_id``, ``_run_operator_async``,
``_record_active_file``, ``_operator_file_exists``) flyttet hertil. INGEN
logik-ændring — kun flyt. Disse tools eksekverer på brugerens EGEN maskine via
JarvisX-broen; de fleste delegerer til ``core.tools.operator_tools`` async-
dispatcheren gennem ``_run_operator_async``.

``simple_tools`` re-importerer alle disse navne, så ``_TOOL_HANDLERS`` og
eksisterende ``from core.tools.simple_tools import _exec_operator_bash`` (m.fl.)
er uændret. ``_operator_user_id`` bruges også af google/note-connector-handlers
i ``simple_tools`` — derfor re-eksporteret.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _st():
    """Lazy accessor til simple_tools-modulet (facade-søm, §4 monkeypatch).

    ``_operator_user_id`` og ``_run_operator_async`` er de to hjælpere som
    tests monkeypatcher PÅ ``core.tools.simple_tools`` (read-before-write-
    guard-testen m.fl.). Efter Boy-Scout-splittet bor selve implementeringen
    her, men de kanoniske, patch-bare navne eksponeres af ``simple_tools``.
    De interne kald i denne fil går derfor gennem ``_st()`` så en patch på
    ``simple_tools._operator_user_id`` / ``._run_operator_async`` stadig
    rammer. Lazy import → ingen cirkulær import ved modul-load."""
    import core.tools.simple_tools as _m
    return _m


def _operator_user_id(args: dict[str, Any]) -> str:
    """Facade → simple_tools._operator_user_id (honorér test-patch-søm)."""
    return _st()._operator_user_id(args)


def _run_operator_async(coro_fn, *, tool_name: str, timeout_s: float = 35.0) -> dict[str, Any]:
    """Facade → simple_tools._run_operator_async (honorér test-patch-søm)."""
    return _st()._run_operator_async(coro_fn, tool_name=tool_name, timeout_s=timeout_s)


def _operator_user_id_impl(args: dict[str, Any]) -> str:
    """Resolve operator's user_id for bridge routing.

    Resolution order (Phase 5 multi-user-ready):
      1. Explicit _runtime_user_id / _user_id in args (set by caller)
      2. Latest user-stamped message in the session (Mikkel/Bjørn etc.)
      3. owner_user_id from runtime.json
      4. Hardcoded Bjørn discord_id (final fallback)

    For multi-user deployments (Bjørn + Mikkel), step 2 is what makes
    each operator route to THEIR OWN bridge: their JarvisX-app stamps
    messages with their user_id, and tool-calls inherit it.
    """
    user_id = str(
        args.get("_runtime_user_id")
        or args.get("_user_id")
        or ""
    ).strip()
    if user_id:
        return user_id

    # Try to derive from session participants
    session_id = str(args.get("_runtime_session_id") or "").strip()
    if session_id:
        try:
            import sqlite3
            from pathlib import Path
            import os
            db_path = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2" / "state" / "jarvis.db"
            with sqlite3.connect(str(db_path)) as conn:
                row = conn.execute(
                    "SELECT user_id FROM message_user_attribution "
                    "WHERE session_id=? AND user_id IS NOT NULL AND user_id != '' "
                    "ORDER BY rowid DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
                if row and row[0]:
                    return str(row[0])
        except Exception:
            pass

    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        return str(settings.extra.get("owner_user_id") or "1246415163603816499")
    except Exception:
        return "1246415163603816499"


def _record_active_file(path: str, op: str, args: dict[str, Any]) -> None:
    """Live-highlight: notér at Jarvis (i brugerens kontekst) rører `path` på sin
    egen maskine, så desk-fil-træet kan markere den live. Fail-open."""
    try:
        from core.services.active_file_store import set_active_file
        set_active_file(_operator_user_id(args), str(path), op)
    except Exception:
        pass


def _run_operator_async_impl(coro_fn, *, tool_name: str, timeout_s: float = 35.0) -> dict[str, Any]:
    """Bridge sync tool-handler → async dispatcher.

    The bridge's WebSocket lives on uvicorn's main asyncio loop. Submitting
    the dispatch coroutine to that SAME loop (via run_coroutine_threadsafe)
    avoids cross-loop races where ws.send_json from a worker thread's loop
    would silently fail to deliver / wake up. Falls back to a dedicated
    worker-loop only if no main loop has been registered (e.g. CLI scripts
    importing the tool outside the API process).
    """
    import asyncio
    from core.services.jarvisx_bridge import get_main_loop

    main_loop = get_main_loop()
    if main_loop is not None and main_loop.is_running():
        # Preferred path: submit to the loop that owns the bridge's WS.
        try:
            logger.debug(
                "[bridge-dispatch] WORKER-START tool=%s timeout=%.1fs threads=%d",
                tool_name, timeout_s, threading.active_count(),
            )
            t0 = time.monotonic()
            cf_fut = asyncio.run_coroutine_threadsafe(coro_fn(), main_loop)
            logger.info("[bridge-dispatch] WORKER-SUBMITTED tool=%s", tool_name)
            result = cf_fut.result(timeout=timeout_s)
            dt = time.monotonic() - t0
            logger.debug(
                "[bridge-dispatch] WORKER-RECV tool=%s dt=%.3fs result_status=%s",
                tool_name, dt, result.get("status") if isinstance(result, dict) else "?",
            )
            return {"status": "ok", "result": result}
        except TimeoutError:
            # Cancel the future on the main loop so the coroutine doesn't
            # keep running and potentially block subsequent dispatches.
            cf_fut.cancel()
            logger.error(
                "[bridge-dispatch] WORKER-TIMEOUT tool=%s after %.1fs (cancelled)",
                tool_name, timeout_s,
            )
            return {
                "error": f"{tool_name}: dispatcher did not return in {timeout_s}s",
                "status": "error",
            }
        except RuntimeError as exc:
            msg = str(exc)
            # Forventede MILJØ-udfald er ikke runtime-bugs → WARNING (ellers fanger anomaly-
            # catcheren dem som falske anomalier): desk ikke forbundet, operator i forkert mode,
            # fil findes ikke, bro-timeout. Kun UVENTEDE fejl skal være ERROR.
            _expected = ("bridge_not_connected", "mode_not_local", "bridge_timeout",
                         "ENOENT", "no such file")
            _log = logger.warning if any(k in msg for k in _expected) else logger.error
            _log("[bridge-dispatch] WORKER-RUNTIME-ERR tool=%s err=%s", tool_name, exc)
            return {"error": msg, "status": "error"}
        except Exception as exc:
            logger.error("[bridge-dispatch] WORKER-EXC tool=%s err=%s", tool_name, exc)
            return {"error": f"{tool_name} failed: {exc!s}"[:240], "status": "error"}

    # Fallback: standalone loop in a thread. Only used when main loop is
    # unavailable (CLI scripts, tests outside the API process). Has the
    # cross-loop ws.send_json hazard but is the only option here.
    # threading is already imported at module top (line 18).
    holder: dict[str, Any] = {}

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        try:
            holder["result"] = loop.run_until_complete(coro_fn())
        except RuntimeError as exc:
            holder["error"] = str(exc)
        except Exception as exc:
            holder["error"] = f"{tool_name} failed: {exc!s}"[:240]
        finally:
            loop.close()

    t = threading.Thread(target=_runner, daemon=True, name=f"operator-{tool_name}")
    t.start()
    t.join(timeout=timeout_s)
    if t.is_alive():
        return {"error": f"{tool_name}: dispatcher thread did not return in {timeout_s}s", "status": "error"}
    if "error" in holder:
        return {"error": holder["error"], "status": "error"}
    return {"status": "ok", "result": holder.get("result")}


def _exec_operator_read_file(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    if not path:
        return {"error": "path is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_read_file_async
    out = _run_operator_async(
        lambda: operator_read_file_async(path=path, user_id=user_id, timeout_s=30.0),
        tool_name="operator_read_file",
    )
    if out.get("status") == "ok":
        # Phase 1 read-before-write enforcement: record the read so a
        # later operator_write_file / operator_edit_file on the same
        # path passes the guard. Best-effort; failure is non-fatal.
        try:
            from core.services.read_before_write_guard import record_operator_read
            _sid = (
                args.get("_runtime_session_id")
                or args.get("_session_id")
                or "default"
            )
            record_operator_read(path, session_id=str(_sid))
        except Exception:
            pass
        _record_active_file(path, "read", args)
        return {"status": "ok", "result": out["result"], "path": path}
    return out


def _operator_file_exists(path: str, user_id: str) -> bool | None:
    """Best-effort: does `path` exist on the operator's machine?

    Returns True/False, or None if undeterminable (bridge error, bare
    filename, or parent we can't list). Used to disambiguate a NEW-file
    write (nothing to clobber → safe) from an overwrite. Cheap, read-only,
    no approval dialog — lists the parent dir and checks the basename.
    Handles both POSIX and Windows separators.
    """
    p = str(path or "").strip()
    if not p:
        return None
    norm = p.replace(chr(92), "/")  # backslash → forward slash
    if "/" not in norm:
        return None  # bare filename — no parent to list
    parent_norm, _, base = norm.rpartition("/")
    if not base:
        return None
    parent = parent_norm or "/"
    try:
        from core.tools.operator_tools import operator_list_dir_async
        out = _run_operator_async(
            lambda: operator_list_dir_async(path=parent, user_id=user_id, timeout_s=15.0),
            tool_name="operator_list_dir",
        )
    except Exception:
        return None
    if not isinstance(out, dict) or out.get("status") != "ok":
        return None  # parent unlistable (missing/denied) — stay conservative
    entries = out.get("result")
    if not isinstance(entries, list):
        return None
    try:
        names = {str(e.get("name")) for e in entries if isinstance(e, dict)}
    except Exception:
        return None
    return base in names


def _exec_operator_write_file(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    content = args.get("content")
    if not path:
        return {"error": "path is required", "status": "error"}
    if content is None:
        return {"error": "content is required", "status": "error"}
    # Phase 1 read-before-write guard: block if this path hasn't been
    # read in this session. The LLM can bypass legitimately by passing
    # force=true (e.g. brand-new file creation that doesn't exist yet).
    if not bool(args.get("force")):
        try:
            from core.services.gate_execution import check_operator
            _sid = (
                args.get("_runtime_session_id")
                or args.get("_session_id")
                or "default"
            )
            _ec = check_operator(path, session_id=str(_sid))
            if _ec.classification == "guard_blocked" and _ec.reason:
                # The guard wants to block — but a brand-new file can't
                # clobber anything, and you can't read what doesn't exist
                # (ENOENT → deadlock → LLM bypasses via `bash cat >`).
                # Probe existence on the operator side ONLY now (cheap,
                # read-only) to disambiguate new-file from overwrite.
                _exists = _operator_file_exists(path, _operator_user_id(args))
                if _exists is not False:
                    # Exists, or couldn't determine → keep the guard.
                    return {
                        "status": "error",
                        "error": _ec.reason,
                        "blocked_by": "read_before_write_guard",
                        "path": path,
                        "hint": (
                            "Kald operator_read_file('"
                            + path
                            + "') først, eller pass force=true hvis "
                            "filen er helt ny og ikke eksisterer."
                        ),
                    }
                # _exists is False → brand-new file → allow, fall through.
        except Exception:
            pass
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_write_file_async
    out = _run_operator_async(
        lambda: operator_write_file_async(
            path=path, content=str(content), user_id=user_id, timeout_s=30.0,
        ),
        tool_name="operator_write_file",
    )
    if isinstance(out, dict) and out.get("status") == "ok":
        try:
            from core.services.read_before_write_guard import (
                record_operator_edit,
                get_session_edit_summary,
            )
            _sid = (
                args.get("_runtime_session_id")
                or args.get("_session_id")
                or "default"
            )
            record_operator_edit(path, session_id=str(_sid), kind="write")
            summary = get_session_edit_summary(session_id=str(_sid))
            if summary:
                out["_session_summary"] = summary
        except Exception:
            pass
        _record_active_file(path, "write", args)
    return out


def _exec_operator_edit_file(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    old_string = args.get("old_string")
    new_string = args.get("new_string")
    if not path:
        return {"error": "path is required", "status": "error"}
    if old_string is None or new_string is None:
        return {"error": "old_string and new_string are required", "status": "error"}
    # Phase 1 read-before-write guard. edit_file by definition needs an
    # existing file, so no force bypass — if you're editing, you must
    # have read it in this session.
    try:
        from core.services.gate_execution import check_operator
        _sid = (
            args.get("_runtime_session_id")
            or args.get("_session_id")
            or "default"
        )
        _ec = check_operator(path, session_id=str(_sid), file_exists=True)
        if _ec.classification == "guard_blocked" and _ec.reason:
            return {
                "status": "error",
                "error": _ec.reason,
                "blocked_by": "read_before_write_guard",
                "path": path,
                "hint": (
                    "Kald operator_read_file('" + path
                    + "') først — operator_edit_file kan ikke "
                    "edite uden at have læst filen i denne session."
                ),
            }
    except Exception:
        pass
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_edit_file_async
    out = _run_operator_async(
        lambda: operator_edit_file_async(
            path=path,
            old_string=str(old_string),
            new_string=str(new_string),
            replace_all=bool(args.get("replace_all", False)),
            user_id=user_id,
            timeout_s=30.0,
        ),
        tool_name="operator_edit_file",
    )
    # Phase 2/3: record the edit + attach session summary so the LLM
    # sees the running tally without us building a UI sidebar.
    if isinstance(out, dict) and out.get("status") == "ok":
        try:
            from core.services.read_before_write_guard import (
                record_operator_edit,
                get_session_edit_summary,
            )
            _sid = (
                args.get("_runtime_session_id")
                or args.get("_session_id")
                or "default"
            )
            record_operator_edit(path, session_id=str(_sid), kind="edit")
            summary = get_session_edit_summary(session_id=str(_sid))
            if summary:
                out["_session_summary"] = summary
        except Exception:
            pass
        _record_active_file(path, "write", args)
    return out


def _exec_operator_glob(args: dict[str, Any]) -> dict[str, Any]:
    pattern = str(args.get("pattern") or "").strip()
    if not pattern:
        return {"error": "pattern is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_glob_async
    return _run_operator_async(
        lambda: operator_glob_async(
            pattern=pattern,
            cwd=args.get("cwd"),
            max_results=int(args.get("max_results") or 200),
            user_id=user_id,
            timeout_s=30.0,
        ),
        tool_name="operator_glob",
    )


def _exec_operator_grep(args: dict[str, Any]) -> dict[str, Any]:
    pattern = str(args.get("pattern") or "").strip()
    if not pattern:
        return {"error": "pattern is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_grep_async
    return _run_operator_async(
        lambda: operator_grep_async(
            pattern=pattern,
            path=args.get("path"),
            glob=args.get("glob"),
            case_insensitive=bool(args.get("case_insensitive", False)),
            max_results=int(args.get("max_results") or 200),
            user_id=user_id,
            timeout_s=60.0,  # grep over many files takes longer
        ),
        tool_name="operator_grep",
        timeout_s=65.0,
    )


def _exec_operator_list_dir(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    if not path:
        return {"error": "path is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_list_dir_async
    return _run_operator_async(
        lambda: operator_list_dir_async(path=path, user_id=user_id, timeout_s=30.0),
        tool_name="operator_list_dir",
    )


def _exec_operator_webfetch(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url:
        return {"error": "url is required", "status": "error"}
    user_id = _operator_user_id(args)
    timeout_s = float(args.get("timeout_s") or 30.0)
    from core.tools.operator_tools import operator_webfetch_async
    return _run_operator_async(
        lambda: operator_webfetch_async(
            url=url,
            method=str(args.get("method") or "GET"),
            headers=args.get("headers"),
            body=args.get("body"),
            timeout_s=timeout_s,
            user_id=user_id,
        ),
        tool_name="operator_webfetch",
        timeout_s=timeout_s + 35.0,
    )


def _exec_operator_bash(args: dict[str, Any]) -> dict[str, Any]:
    command = str(args.get("command") or "").strip()
    if not command:
        return {"error": "command is required", "status": "error"}
    user_id = _operator_user_id(args)
    timeout_s = float(args.get("timeout_s") or 30.0)
    thread_timeout = min(timeout_s, 300.0) + 30.0

    # Dispatch direkte til bridge — approval er håndteret af
    # chat-approval-card mekanismen på et højere niveau i flowet.
    # (screenshot og clipboard gør det samme; OS-dialog er fjernet).
    from core.tools.operator_tools import operator_bash_async
    return _run_operator_async(
        lambda: operator_bash_async(
            command=command,
            cwd=args.get("cwd"),
            timeout_s=timeout_s,
            user_id=user_id,
            skip_approval=True,
        ),
        tool_name="operator_bash",
        timeout_s=thread_timeout,
    )


def _exec_operator_screenshot(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    display_id = args.get("display_id")
    save_path = args.get("save_path")
    fmt = str(args.get("format") or "png").lower()
    jpeg_quality = int(args.get("jpeg_quality") or 85)
    from core.tools.operator_tools import operator_screenshot_async
    return _run_operator_async(
        lambda: operator_screenshot_async(
            user_id=user_id,
            display_id=int(display_id) if display_id is not None else None,
            save_path=str(save_path) if save_path else None,
            format=fmt,
            jpeg_quality=jpeg_quality,
            timeout_s=30.0,
        ),
        tool_name="operator_screenshot",
        timeout_s=45.0,
    )


def _exec_operator_open_url(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url:
        return {"error": "url is required", "status": "error"}
    user_id = _operator_user_id(args)

    # Godkendelse via chat-card (ikke OS-dialog).
    skip_approval = bool(args.get("_runtime_trust_all"))
    if not skip_approval:
        return {
            "status": "approval_needed",
            "tool_name": "operator_open_url",
            "message": f"Jarvis vil åbne URL i operatørens browser: {url}",
            "command": url,
            "url": url,
        }

    # Allerede godkendt — dispatcher til bridge med skip_approval=True.
    from core.tools.operator_tools import operator_open_url_async
    return _run_operator_async(
        lambda: operator_open_url_async(
            url=url,
            user_id=user_id,
            skip_approval=True,  # godkendt i chat; bridge spørger ikke igen
            timeout_s=30.0,
        ),
        tool_name="operator_open_url",
        timeout_s=45.0,
    )


def _exec_operator_launch_app(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or args.get("app") or "").strip()
    if not path:
        return {"error": "path is required", "status": "error"}
    user_id = _operator_user_id(args)
    cli_args = args.get("args") or []
    if not isinstance(cli_args, list):
        return {"error": "args must be a list of strings", "status": "error"}
    cwd = args.get("cwd")

    # Godkendelse via chat-card (ikke OS-dialog).
    skip_approval = bool(args.get("_runtime_trust_all"))
    if not skip_approval:
        args_preview = " ".join(str(a) for a in cli_args) if cli_args else ""
        detail = f"{path} {args_preview}".strip()
        return {
            "status": "approval_needed",
            "tool_name": "operator_launch_app",
            "message": f"Jarvis vil starte et program på operatørens maskine: {detail}",
            "command": detail,
            "path": path,
        }

    # Allerede godkendt — dispatcher til bridge med skip_approval=True.
    from core.tools.operator_tools import operator_launch_app_async
    return _run_operator_async(
        lambda: operator_launch_app_async(
            path=path,
            user_id=user_id,
            args=[str(a) for a in cli_args],
            cwd=str(cwd) if cwd else None,
            skip_approval=True,  # godkendt i chat; bridge spørger ikke igen
            timeout_s=30.0,
        ),
        tool_name="operator_launch_app",
        timeout_s=45.0,
    )


def _exec_operator_mouse_move(args: dict[str, Any]) -> dict[str, Any]:
    try:
        x, y = int(args["x"]), int(args["y"])
    except (KeyError, ValueError, TypeError):
        return {"error": "x and y are required integers", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_mouse_move_async
    return _run_operator_async(
        lambda: operator_mouse_move_async(
            x=x, y=y, user_id=user_id, smooth=bool(args.get("smooth")), timeout_s=15.0,
        ),
        tool_name="operator_mouse_move",
        timeout_s=20.0,
    )


def _exec_operator_mouse_click(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    button = str(args.get("button") or "left")
    double = bool(args.get("double"))
    x = args.get("x")
    y = args.get("y")
    from core.tools.operator_tools import operator_mouse_click_async
    return _run_operator_async(
        lambda: operator_mouse_click_async(
            user_id=user_id,
            button=button,
            double=double,
            x=int(x) if x is not None else None,
            y=int(y) if y is not None else None,
            timeout_s=15.0,
        ),
        tool_name="operator_mouse_click",
        timeout_s=20.0,
    )


def _exec_operator_mouse_position(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_mouse_position_async
    return _run_operator_async(
        lambda: operator_mouse_position_async(user_id=user_id, timeout_s=10.0),
        tool_name="operator_mouse_position",
        timeout_s=15.0,
    )


def _exec_operator_keyboard_type(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("text")
    if not isinstance(text, str) or not text:
        return {"error": "text is required (non-empty string)", "status": "error"}
    user_id = _operator_user_id(args)
    delay_ms = args.get("delay_ms")
    from core.tools.operator_tools import operator_keyboard_type_async
    return _run_operator_async(
        lambda: operator_keyboard_type_async(
            text=text,
            user_id=user_id,
            delay_ms=int(delay_ms) if delay_ms is not None else None,
            timeout_s=max(15.0, len(text) * 0.05),
        ),
        tool_name="operator_keyboard_type",
        timeout_s=max(20.0, len(text) * 0.1),
    )


def _exec_operator_keyboard_press(args: dict[str, Any]) -> dict[str, Any]:
    keys = args.get("keys")
    if keys is None:
        return {"error": "keys is required", "status": "error"}
    if not isinstance(keys, (str, list)):
        return {"error": "keys must be a string or list of strings", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_keyboard_press_async
    return _run_operator_async(
        lambda: operator_keyboard_press_async(
            keys=keys, user_id=user_id, timeout_s=10.0,
        ),
        tool_name="operator_keyboard_press",
        timeout_s=15.0,
    )


def _exec_operator_screen_size(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_screen_size_async
    return _run_operator_async(
        lambda: operator_screen_size_async(user_id=user_id, timeout_s=10.0),
        tool_name="operator_screen_size",
        timeout_s=15.0,
    )


def _exec_operator_clipboard_read(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_clipboard_read_async
    return _run_operator_async(
        lambda: operator_clipboard_read_async(user_id=user_id, timeout_s=10.0),
        tool_name="operator_clipboard_read",
        timeout_s=15.0,
    )


def _exec_operator_clipboard_write(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("text")
    if not isinstance(text, str):
        return {"error": "text is required (string)", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_clipboard_write_async
    return _run_operator_async(
        lambda: operator_clipboard_write_async(text=text, user_id=user_id, timeout_s=10.0),
        tool_name="operator_clipboard_write",
        timeout_s=15.0,
    )


def _exec_operator_list_windows(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_list_windows_async
    return _run_operator_async(
        lambda: operator_list_windows_async(user_id=user_id, timeout_s=15.0),
        tool_name="operator_list_windows",
        timeout_s=20.0,
    )


def _exec_operator_focus_window(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    title_substring = args.get("title_substring")
    handle = args.get("handle")
    if title_substring is None and handle is None:
        return {"error": "title_substring or handle is required", "status": "error"}
    from core.tools.operator_tools import operator_focus_window_async
    return _run_operator_async(
        lambda: operator_focus_window_async(
            user_id=user_id,
            title_substring=str(title_substring) if title_substring is not None else None,
            handle=int(handle) if handle is not None else None,
            timeout_s=15.0,
        ),
        tool_name="operator_focus_window",
        timeout_s=20.0,
    )


def _exec_operator_mouse_scroll(args: dict[str, Any]) -> dict[str, Any]:
    direction = str(args.get("direction") or "down")
    if direction not in ("up", "down", "left", "right"):
        return {"error": "direction must be one of: up, down, left, right", "status": "error"}
    amount = int(args.get("amount") or 3)
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_mouse_scroll_async
    return _run_operator_async(
        lambda: operator_mouse_scroll_async(
            direction=direction, amount=amount, user_id=user_id, timeout_s=10.0,
        ),
        tool_name="operator_mouse_scroll",
        timeout_s=15.0,
    )


def _exec_operator_mouse_drag(args: dict[str, Any]) -> dict[str, Any]:
    try:
        from_x = int(args["from_x"])
        from_y = int(args["from_y"])
        to_x = int(args["to_x"])
        to_y = int(args["to_y"])
    except (KeyError, ValueError, TypeError):
        return {"error": "from_x, from_y, to_x, to_y are required integers", "status": "error"}
    button = str(args.get("button") or "left")
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_mouse_drag_async
    return _run_operator_async(
        lambda: operator_mouse_drag_async(
            from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y,
            button=button, user_id=user_id, timeout_s=15.0,
        ),
        tool_name="operator_mouse_drag",
        timeout_s=20.0,
    )


def _exec_operator_list_processes(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    filter_str = args.get("filter")
    from core.tools.operator_tools import operator_list_processes_async
    return _run_operator_async(
        lambda: operator_list_processes_async(
            user_id=user_id,
            filter=str(filter_str) if filter_str is not None else None,
            timeout_s=15.0,
        ),
        tool_name="operator_list_processes",
        timeout_s=20.0,
    )


def _exec_operator_kill_process(args: dict[str, Any]) -> dict[str, Any]:
    pid = args.get("pid")
    if pid is None:
        return {"error": "pid is required", "status": "error"}
    try:
        pid = int(pid)
    except (ValueError, TypeError):
        return {"error": "pid must be an integer", "status": "error"}
    user_id = _operator_user_id(args)

    # Godkendelse via chat-card (ikke OS-dialog).
    skip_approval = bool(args.get("_runtime_trust_all"))
    if not skip_approval:
        return {
            "status": "approval_needed",
            "tool_name": "operator_kill_process",
            "message": f"Jarvis vil afslutte proces med PID {pid} på operatørens maskine",
            "command": str(pid),
            "pid": pid,
        }

    # Allerede godkendt — dispatcher til bridge med skip_approval=True.
    from core.tools.operator_tools import operator_kill_process_async
    return _run_operator_async(
        lambda: operator_kill_process_async(
            pid=pid,
            user_id=user_id,
            skip_approval=True,  # godkendt i chat; bridge spørger ikke igen
            timeout_s=30.0,
        ),
        tool_name="operator_kill_process",
        timeout_s=45.0,
    )


def _exec_operator_speak(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("text")
    if not isinstance(text, str) or not text:
        return {"error": "text is required (non-empty string)", "status": "error"}
    rate = int(args.get("rate") or 5)
    rate = max(0, min(10, rate))
    voice = args.get("voice")
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_speak_async
    return _run_operator_async(
        lambda: operator_speak_async(
            text=text, user_id=user_id,
            voice=str(voice) if voice is not None else None,
            rate=rate, timeout_s=30.0,
        ),
        tool_name="operator_speak",
        timeout_s=40.0,
    )


def _exec_operator_screenshot_window(args: dict[str, Any]) -> dict[str, Any]:
    title_substring = args.get("title_substring")
    handle = args.get("handle")
    if title_substring is None and handle is None:
        return {"error": "title_substring or handle is required", "status": "error"}
    save_path = args.get("save_path")
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_screenshot_window_async
    return _run_operator_async(
        lambda: operator_screenshot_window_async(
            user_id=user_id,
            title_substring=str(title_substring) if title_substring is not None else None,
            handle=str(handle) if handle is not None else None,
            save_path=str(save_path) if save_path is not None else None,
            timeout_s=20.0,
        ),
        tool_name="operator_screenshot_window",
        timeout_s=30.0,
    )


def _exec_operator_find_image(args: dict[str, Any]) -> dict[str, Any]:
    template_path = args.get("template_path")
    if not isinstance(template_path, str) or not template_path:
        return {"error": "template_path is required (string)", "status": "error"}
    confidence = float(args.get("confidence") or 0.85)
    confidence = max(0.0, min(1.0, confidence))
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_find_image_async
    return _run_operator_async(
        lambda: operator_find_image_async(
            template_path=template_path, user_id=user_id,
            confidence=confidence, timeout_s=20.0,
        ),
        tool_name="operator_find_image",
        timeout_s=30.0,
    )


def _exec_operator_ocr_region(args: dict[str, Any]) -> dict[str, Any]:
    try:
        x = int(args["x"])
        y = int(args["y"])
        width = int(args["width"])
        height = int(args["height"])
    except (KeyError, ValueError, TypeError):
        return {"error": "x, y, width, height are required integers", "status": "error"}
    if width <= 0 or height <= 0:
        return {"error": "width and height must be positive", "status": "error"}
    lang = str(args.get("lang") or "eng")
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_ocr_region_async
    return _run_operator_async(
        lambda: operator_ocr_region_async(
            x=x, y=y, width=width, height=height,
            user_id=user_id, lang=lang, timeout_s=30.0,
        ),
        tool_name="operator_ocr_region",
        timeout_s=45.0,
    )


# ── Tier-3 exec stubs ────────────────────────────────────────────────────


def _exec_operator_reminder(args: dict[str, Any]) -> dict[str, Any]:
    when = str(args.get("when") or "").strip()
    message = str(args.get("message") or "").strip()
    if not when:
        return {"error": "when is required", "status": "error"}
    if not message:
        return {"error": "message is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_reminder_async
    return _run_operator_async(
        lambda: operator_reminder_async(
            when=when, message=message,
            title=str(args.get("title")) if args.get("title") else None,
            user_id=user_id, timeout_s=15.0,
        ),
        tool_name="operator_reminder",
        timeout_s=25.0,
    )


def _exec_operator_wakeup(args: dict[str, Any]) -> dict[str, Any]:
    when = str(args.get("when") or "").strip()
    if not when:
        return {"error": "when is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_wakeup_async
    return _run_operator_async(
        lambda: operator_wakeup_async(
            when=when,
            message=str(args.get("message")) if args.get("message") else None,
            title=str(args.get("title")) if args.get("title") else None,
            user_id=user_id, timeout_s=15.0,
        ),
        tool_name="operator_wakeup",
        timeout_s=25.0,
    )


def _exec_operator_scheduled_list(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_scheduled_list_async
    return _run_operator_async(
        lambda: operator_scheduled_list_async(
            user_id=user_id,
            kind=str(args.get("kind")) if args.get("kind") else None,
            include_fired=bool(args.get("include_fired")),
            timeout_s=15.0,
        ),
        tool_name="operator_scheduled_list",
        timeout_s=20.0,
    )


def _exec_operator_scheduled_cancel(args: dict[str, Any]) -> dict[str, Any]:
    id_ = str(args.get("id") or "").strip()
    if not id_:
        return {"error": "id is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_scheduled_cancel_async
    return _run_operator_async(
        lambda: operator_scheduled_cancel_async(id=id_, user_id=user_id, timeout_s=15.0),
        tool_name="operator_scheduled_cancel",
        timeout_s=20.0,
    )


def _exec_operator_process_spawn(args: dict[str, Any]) -> dict[str, Any]:
    cmd = str(args.get("cmd") or "").strip()
    if not cmd:
        return {"error": "cmd is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_process_spawn_async
    return _run_operator_async(
        lambda: operator_process_spawn_async(
            cmd=cmd, user_id=user_id,
            cwd=str(args.get("cwd")) if args.get("cwd") else None,
            label=str(args.get("label")) if args.get("label") else None,
            timeout_s=15.0,
        ),
        tool_name="operator_process_spawn",
        timeout_s=20.0,
    )


def _exec_operator_process_status(args: dict[str, Any]) -> dict[str, Any]:
    id_ = str(args.get("id") or "").strip()
    if not id_:
        return {"error": "id is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_process_status_async
    return _run_operator_async(
        lambda: operator_process_status_async(id=id_, user_id=user_id, timeout_s=10.0),
        tool_name="operator_process_status",
        timeout_s=15.0,
    )


def _exec_operator_process_output(args: dict[str, Any]) -> dict[str, Any]:
    id_ = str(args.get("id") or "").strip()
    if not id_:
        return {"error": "id is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_process_output_async
    return _run_operator_async(
        lambda: operator_process_output_async(
            id=id_, user_id=user_id,
            since_offset=int(args.get("since_offset") or 0),
            max_bytes=int(args.get("max_bytes") or 64_000),
            timeout_s=15.0,
        ),
        tool_name="operator_process_output",
        timeout_s=20.0,
    )


def _exec_operator_process_kill(args: dict[str, Any]) -> dict[str, Any]:
    id_ = str(args.get("id") or "").strip()
    if not id_:
        return {"error": "id is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_process_kill_async
    return _run_operator_async(
        lambda: operator_process_kill_async(
            id=id_, user_id=user_id,
            signal=str(args.get("signal") or "SIGTERM"),
            timeout_s=10.0,
        ),
        tool_name="operator_process_kill",
        timeout_s=15.0,
    )


def _exec_operator_process_list(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_process_list_async
    return _run_operator_async(
        lambda: operator_process_list_async(
            user_id=user_id,
            include_finished=bool(args.get("include_finished", True)),
            timeout_s=10.0,
        ),
        tool_name="operator_process_list",
        timeout_s=15.0,
    )


def _exec_operator_notify(args: dict[str, Any]) -> dict[str, Any]:
    title = args.get("title")
    body = args.get("body")
    if not isinstance(title, str) or not title:
        return {"error": "title is required (non-empty string)", "status": "error"}
    if not isinstance(body, str):
        return {"error": "body is required (string)", "status": "error"}
    icon = args.get("icon")
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_notify_async
    return _run_operator_async(
        lambda: operator_notify_async(
            title=title, body=body, user_id=user_id,
            icon=str(icon) if icon is not None else None,
            timeout_s=10.0,
        ),
        tool_name="operator_notify",
        timeout_s=15.0,
    )


def _exec_operator_watch_folder(args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path")
    if not isinstance(path, str) or not path:
        return {"error": "path is required (non-empty string)", "status": "error"}
    recursive = bool(args.get("recursive", False))
    debounce_ms = int(args.get("debounce_ms") or 500)
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_watch_folder_async
    return _run_operator_async(
        lambda: operator_watch_folder_async(
            path=path, user_id=user_id,
            recursive=recursive, debounce_ms=debounce_ms,
            timeout_s=15.0,
        ),
        tool_name="operator_watch_folder",
        timeout_s=20.0,
    )


def _exec_operator_unwatch_folder(args: dict[str, Any]) -> dict[str, Any]:
    watcher_id = args.get("watcher_id")
    if not isinstance(watcher_id, str) or not watcher_id:
        return {"error": "watcher_id is required (non-empty string)", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_unwatch_folder_async
    return _run_operator_async(
        lambda: operator_unwatch_folder_async(
            watcher_id=watcher_id, user_id=user_id, timeout_s=10.0,
        ),
        tool_name="operator_unwatch_folder",
        timeout_s=15.0,
    )


def _exec_operator_watch_events(args: dict[str, Any]) -> dict[str, Any]:
    watcher_id = args.get("watcher_id")
    if not isinstance(watcher_id, str) or not watcher_id:
        return {"error": "watcher_id is required (non-empty string)", "status": "error"}
    max_events = int(args.get("max") or 100)
    max_events = max(1, min(1000, max_events))
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_watch_events_async
    return _run_operator_async(
        lambda: operator_watch_events_async(
            watcher_id=watcher_id, user_id=user_id, max=max_events, timeout_s=10.0,
        ),
        tool_name="operator_watch_events",
        timeout_s=15.0,
    )


def _exec_operator_record_audio(args: dict[str, Any]) -> dict[str, Any]:
    duration_s = args.get("duration_s")
    if duration_s is None:
        return {"error": "duration_s is required", "status": "error"}
    try:
        duration_s = int(duration_s)
    except (ValueError, TypeError):
        return {"error": "duration_s must be an integer", "status": "error"}
    if not (1 <= duration_s <= 300):
        return {"error": "duration_s must be between 1 and 300", "status": "error"}
    output_path = args.get("output_path")
    device = args.get("device")
    user_id = _operator_user_id(args)

    # Godkendelse via chat-card (ikke OS-dialog).
    skip_approval = bool(args.get("_runtime_trust_all"))
    if not skip_approval:
        return {
            "status": "approval_needed",
            "tool_name": "operator_record_audio",
            "message": f"Jarvis vil optage lyd fra mikrofonen i {duration_s} sekunder",
            "command": f"{duration_s}s lyd-optagelse",
            "duration_s": duration_s,
        }

    # Allerede godkendt — dispatcher til bridge med skip_approval=True.
    from core.tools.operator_tools import operator_record_audio_async
    return _run_operator_async(
        lambda: operator_record_audio_async(
            duration_s=duration_s,
            user_id=user_id,
            output_path=str(output_path) if output_path is not None else None,
            device=str(device) if device is not None else None,
            skip_approval=True,  # godkendt i chat; bridge spørger ikke igen
            timeout_s=float(duration_s) + 30.0,
        ),
        tool_name="operator_record_audio",
        timeout_s=float(duration_s) + 45.0,
    )


def _exec_operator_browser_open(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url:
        return {"error": "url is required", "status": "error"}
    user_id = _operator_user_id(args)
    wait_until = str(args.get("wait_until") or "load")
    timeout_ms = int(args.get("timeout_ms") or 30000)
    from core.tools.operator_tools import operator_browser_open_async
    return _run_operator_async(
        lambda: operator_browser_open_async(
            url=url, user_id=user_id, wait_until=wait_until,
            timeout_ms=timeout_ms, timeout_s=45.0,
        ),
        tool_name="operator_browser_open",
        timeout_s=55.0,
    )


def _exec_operator_browser_get_text(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    selector = args.get("selector")
    max_chars = int(args.get("max_chars") or 50000)
    from core.tools.operator_tools import operator_browser_get_text_async
    return _run_operator_async(
        lambda: operator_browser_get_text_async(
            user_id=user_id,
            selector=str(selector) if selector else None,
            max_chars=max_chars,
            timeout_s=20.0,
        ),
        tool_name="operator_browser_get_text",
        timeout_s=25.0,
    )


def _exec_operator_browser_get_links(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_browser_get_links_async
    return _run_operator_async(
        lambda: operator_browser_get_links_async(user_id=user_id, timeout_s=20.0),
        tool_name="operator_browser_get_links",
        timeout_s=25.0,
    )


def _exec_operator_browser_click(args: dict[str, Any]) -> dict[str, Any]:
    selector = str(args.get("selector") or "").strip()
    if not selector:
        return {"error": "selector is required", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_browser_click_async
    return _run_operator_async(
        lambda: operator_browser_click_async(
            selector=selector, user_id=user_id,
            wait_navigation=bool(args.get("wait_navigation")),
            wait_for_selector=bool(args.get("wait_for_selector", True)),
            timeout_ms=int(args.get("timeout_ms") or 5000),
            timeout_s=25.0,
        ),
        tool_name="operator_browser_click",
        timeout_s=30.0,
    )


def _exec_operator_browser_type(args: dict[str, Any]) -> dict[str, Any]:
    selector = str(args.get("selector") or "").strip()
    text = args.get("text")
    if not selector:
        return {"error": "selector is required", "status": "error"}
    if not isinstance(text, str):
        return {"error": "text is required (string)", "status": "error"}
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_browser_type_async
    return _run_operator_async(
        lambda: operator_browser_type_async(
            selector=selector, text=text, user_id=user_id,
            clear_first=bool(args.get("clear_first")),
            delay_ms=int(args.get("delay_ms") or 0),
            timeout_s=30.0,
        ),
        tool_name="operator_browser_type",
        timeout_s=35.0,
    )


def _exec_operator_browser_screenshot(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_browser_screenshot_async
    return _run_operator_async(
        lambda: operator_browser_screenshot_async(
            user_id=user_id,
            full_page=bool(args.get("full_page")),
            format=str(args.get("format") or "png"),
            jpeg_quality=int(args.get("jpeg_quality") or 85),
            timeout_s=30.0,
        ),
        tool_name="operator_browser_screenshot",
        timeout_s=40.0,
    )


def _exec_operator_browser_evaluate(args: dict[str, Any]) -> dict[str, Any]:
    script = str(args.get("script") or "")
    if not script:
        return {"error": "script is required", "status": "error"}
    user_id = _operator_user_id(args)

    # Godkendelse via chat-card (ikke OS-dialog).
    skip_approval = bool(args.get("_runtime_trust_all"))
    if not skip_approval:
        script_preview = script[:200] + "…" if len(script) > 200 else script
        return {
            "status": "approval_needed",
            "tool_name": "operator_browser_evaluate",
            "message": f"Jarvis vil køre JavaScript i operatørens browser: {script_preview}",
            "command": script_preview,
            "script": script,
        }

    # Allerede godkendt — dispatcher til bridge med skip_approval=True.
    from core.tools.operator_tools import operator_browser_evaluate_async
    return _run_operator_async(
        lambda: operator_browser_evaluate_async(
            script=script, user_id=user_id, skip_approval=True,  # godkendt i chat
            timeout_s=30.0,
        ),
        tool_name="operator_browser_evaluate",
        timeout_s=60.0,
    )


def _exec_operator_browser_status(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_browser_status_async
    return _run_operator_async(
        lambda: operator_browser_status_async(user_id=user_id, timeout_s=10.0),
        tool_name="operator_browser_status",
        timeout_s=15.0,
    )


def _exec_operator_browser_close(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _operator_user_id(args)
    from core.tools.operator_tools import operator_browser_close_async
    return _run_operator_async(
        lambda: operator_browser_close_async(user_id=user_id, timeout_s=10.0),
        tool_name="operator_browser_close",
        timeout_s=15.0,
    )


__all__ = [
    "_operator_user_id",
    "_record_active_file",
    "_run_operator_async",
    "_exec_operator_read_file",
    "_operator_file_exists",
    "_exec_operator_write_file",
    "_exec_operator_edit_file",
    "_exec_operator_glob",
    "_exec_operator_grep",
    "_exec_operator_list_dir",
    "_exec_operator_webfetch",
    "_exec_operator_bash",
    "_exec_operator_screenshot",
    "_exec_operator_open_url",
    "_exec_operator_launch_app",
    "_exec_operator_mouse_move",
    "_exec_operator_mouse_click",
    "_exec_operator_mouse_position",
    "_exec_operator_keyboard_type",
    "_exec_operator_keyboard_press",
    "_exec_operator_screen_size",
    "_exec_operator_clipboard_read",
    "_exec_operator_clipboard_write",
    "_exec_operator_list_windows",
    "_exec_operator_focus_window",
    "_exec_operator_mouse_scroll",
    "_exec_operator_mouse_drag",
    "_exec_operator_list_processes",
    "_exec_operator_kill_process",
    "_exec_operator_speak",
    "_exec_operator_screenshot_window",
    "_exec_operator_find_image",
    "_exec_operator_ocr_region",
    "_exec_operator_reminder",
    "_exec_operator_wakeup",
    "_exec_operator_scheduled_list",
    "_exec_operator_scheduled_cancel",
    "_exec_operator_process_spawn",
    "_exec_operator_process_status",
    "_exec_operator_process_output",
    "_exec_operator_process_kill",
    "_exec_operator_process_list",
    "_exec_operator_notify",
    "_exec_operator_watch_folder",
    "_exec_operator_unwatch_folder",
    "_exec_operator_watch_events",
    "_exec_operator_record_audio",
    "_exec_operator_browser_open",
    "_exec_operator_browser_get_text",
    "_exec_operator_browser_get_links",
    "_exec_operator_browser_click",
    "_exec_operator_browser_type",
    "_exec_operator_browser_screenshot",
    "_exec_operator_browser_evaluate",
    "_exec_operator_browser_status",
    "_exec_operator_browser_close",
]
