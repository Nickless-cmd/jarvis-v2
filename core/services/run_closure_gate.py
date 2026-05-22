"""Run-closure gate — fang tomme replies og unstaged changes efter agentic runs.

2026-05-22 (Claude): Bjørn rapporterede et systemisk problem: når Jarvis
laver agentic runs, returnerer han ofte ALDRIG et svar — brugeren ser
"han skriver..." status der aldrig færdiggør. Plus, hvis Jarvis har
redigeret kode under runet, ender ændringerne ofte som unstaged i git
working tree — Bjørn skal selv følge op og bede ham committe.

Diagnose:
1. visible_runs._post_process() kører KUN hvis ``visible_output_text``
   er truthy. Hvis modellen lander efter tool-calls uden text-output,
   sker der ingen post-processing.
2. discord_gateway subscriber buffer-er kun reply hvis ``content``
   ikke er tom; tom assistent-output → ingen buffer → flush ved
   run_completed finder intet → bruger får tavshed.
3. Ingen post-run gate tjekker git working tree for changes der blev
   introduceret under runet men aldrig committet.

Denne service subscriber til ``runtime.autonomous_run_completed`` og:

- Tager et snapshot af ``git status --porcelain`` PRE-run (via
  in-flight registry) og POST-run; hvis der er nye unstaged/untracked
  filer → publish ``runtime.run_left_unstaged_changes`` med fil-liste.
- Hvis runet endte med tom visible-text MEN værktøjer blev kaldt under
  forløbet → publish ``runtime.run_ended_silent`` med summary af
  tool-aktivitet, så Discord/Telegram-subscriber kan sende en
  auto-status til brugeren i stedet for ren tavshed.

Begge events er strikt informational — de blocker ikke runet og
mutater ikke noget. Output-channels (Discord, Telegram) opfanger dem
og leverer beskeder til brugeren.
"""

from __future__ import annotations

import logging
import queue
import subprocess
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]

_listener_thread: threading.Thread | None = None
_listener_running: bool = False


# ── git state snapshot ────────────────────────────────────────────────


def _git_porcelain_status(*, cwd: Path = _REPO_ROOT) -> set[str]:
    """Return the set of path-strings reported by ``git status --porcelain``.

    Each path is prefixed by its status code (e.g. ``" M file.py"``,
    ``"?? newfile.py"``). Returns empty set on any git failure — we
    fail-open so the gate never blocks a run on transient git errors.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if result.returncode != 0:
            return set()
        return set(line for line in result.stdout.splitlines() if line.strip())
    except Exception:
        return set()


def _git_dirty_content_hashes(*, cwd: Path = _REPO_ROOT) -> dict[str, str]:
    """Return {path: blob_hash_or_marker} for every file that differs from HEAD.

    Where porcelain status only tells us "M file.py" (modified at all), this
    captures the actual content hash so we can detect modify-modify changes
    within a single run window. Untracked files are included with an
    "untracked:<mtime>" sentinel.

    2026-05-22 (Claude): added because porcelain-only diff missed cases
    where Bjørn already had unstaged changes pre-run AND Jarvis edited
    the same file during the run. Pre and post porcelain both showed
    "M file.py" → empty diff → no notification.
    """
    out: dict[str, str] = {}
    try:
        # Modified tracked files: use `git diff` with object hashes
        result = subprocess.run(
            ["git", "diff", "HEAD", "--raw"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                # Format: :100644 100644 abc123 def456 M\tpath/to/file
                parts = line.split()
                if len(parts) >= 6:
                    new_hash = parts[3]
                    path = parts[-1]
                    out[path] = new_hash
        # Untracked files: use porcelain + mtime so creation/modification
        # of a brand-new file is detectable too.
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if result.returncode == 0:
            for path in result.stdout.splitlines():
                path = path.strip()
                if not path:
                    continue
                full = cwd / path
                try:
                    mtime = full.stat().st_mtime
                except Exception:
                    mtime = 0.0
                out[path] = f"untracked:{mtime}"
    except Exception:
        pass
    return out


# ── per-run state cache ────────────────────────────────────────────────
# Pre-run git snapshot, keyed by run_id. We store both porcelain status
# AND a content-hash map so we can detect modify-modify changes within
# a single run window (where porcelain status alone would look identical
# before and after).
_pre_run_git_state: dict[str, tuple[set[str], dict[str, str]]] = {}
_pre_run_git_lock = threading.Lock()


def _record_pre_run_state(run_id: str) -> None:
    if not run_id:
        return
    snapshot = _git_porcelain_status()
    hashes = _git_dirty_content_hashes()
    with _pre_run_git_lock:
        _pre_run_git_state[run_id] = (snapshot, hashes)


def _pop_pre_run_state(run_id: str) -> tuple[set[str], dict[str, str]]:
    with _pre_run_git_lock:
        return _pre_run_git_state.pop(run_id, (set(), {}))


# ── tool-call tracking ────────────────────────────────────────────────
# Track which runs have called any tool. We listen for tool events on
# the bus rather than parsing run-internal state.
_run_tool_calls: dict[str, list[str]] = {}
_run_tool_lock = threading.Lock()
# Cap memory: never track more than this many runs' tool histories.
_RUN_TOOL_CACHE_MAX = 256


# Latest in-flight run_id. Tool events from simple_tools.py don't carry
# run_id in their payload — we fall back to this when correlating.
# Concurrent runs would collide here, but in practice we have one active
# visible run at a time per process.
_current_run_id: str = ""
_current_run_lock = threading.Lock()


def _set_current_run(run_id: str) -> None:
    with _current_run_lock:
        global _current_run_id
        _current_run_id = run_id


def _get_current_run() -> str:
    with _current_run_lock:
        return _current_run_id


def _record_tool_call(run_id: str, tool_name: str) -> None:
    # Fall back to the in-flight run if payload didn't include run_id.
    if not run_id:
        run_id = _get_current_run()
    if not run_id or not tool_name:
        return
    with _run_tool_lock:
        if len(_run_tool_calls) >= _RUN_TOOL_CACHE_MAX:
            # Drop the oldest tracked run to bound memory
            oldest = next(iter(_run_tool_calls))
            _run_tool_calls.pop(oldest, None)
        _run_tool_calls.setdefault(run_id, []).append(tool_name)


def _pop_tool_calls(run_id: str) -> list[str]:
    with _run_tool_lock:
        return _run_tool_calls.pop(run_id, [])


# ── post-run handler ──────────────────────────────────────────────────


def _summarize_unstaged(diff: set[str], limit: int = 8) -> dict[str, Any]:
    """Build a structured summary of new unstaged/untracked paths."""
    paths: list[str] = []
    for line in sorted(diff):
        if not line.strip():
            continue
        # status codes are first 2 chars, then space, then path
        path = line[3:].strip() if len(line) > 3 else line.strip()
        paths.append(path)
    return {
        "count": len(paths),
        "paths": paths[:limit],
        "truncated": len(paths) > limit,
    }


def _on_run_completed(payload: dict[str, Any]) -> None:
    """Handle a runtime.autonomous_run_completed event."""
    run_id = str(payload.get("run_id") or "")
    session_id = str(payload.get("session_id") or "")
    if not run_id:
        return
    # Clear in-flight pointer if this is the current run.
    if _get_current_run() == run_id:
        _set_current_run("")

    # Compute changed/new paths introduced during this run.
    # We diff TWO things:
    #   1. New porcelain status lines (catches genuinely new file
    #      appearances and status-transitions like staged→unstaged)
    #   2. Content-hash deltas (catches modify-modify within run window
    #      where porcelain alone would look identical before and after)
    pre_lines, pre_hashes = _pop_pre_run_state(run_id)
    post_lines = _git_porcelain_status()
    post_hashes = _git_dirty_content_hashes()

    new_lines = post_lines - pre_lines
    # Content-changed paths: present in both pre+post but with different hash
    content_changed: set[str] = set()
    for path, new_hash in post_hashes.items():
        old_hash = pre_hashes.get(path)
        if old_hash is None or old_hash != new_hash:
            content_changed.add(path)
    # Combine into a single "touched during run" set (path-strings).
    # For porcelain new_lines, strip the status prefix so we get just paths.
    touched_paths: set[str] = set(content_changed)
    for line in new_lines:
        if len(line) > 3:
            touched_paths.add(line[3:].strip())
        else:
            touched_paths.add(line.strip())
    touched_paths.discard("")

    tool_calls = _pop_tool_calls(run_id)

    if touched_paths:
        # Build a fake "porcelain lines" set from the paths so the
        # existing _summarize_unstaged formatter works unchanged.
        synthetic = {f"   {p}" for p in touched_paths}
        summary = _summarize_unstaged(synthetic)
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish("runtime.run_left_unstaged_changes", {
                "run_id": run_id,
                "session_id": session_id,
                "summary": summary,
                "tool_calls": tool_calls,
            })
            logger.info(
                "run_closure_gate: %d unstaged paths after run %s (%s)",
                summary["count"],
                run_id[:12],
                ", ".join(summary["paths"][:3]),
            )
        except Exception:
            logger.debug("run_closure_gate: failed to publish unstaged event", exc_info=True)

    # Silent-run detection: tool calls happened but no visible text was
    # delivered. We check the run-record DB for the final output text.
    if tool_calls:
        try:
            from core.runtime.db import connect
            with connect() as conn:
                row = conn.execute(
                    "SELECT output_text FROM visible_runs WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
            output = (row[0] if row else "") or ""
            if not output.strip():
                from core.eventbus.bus import event_bus
                event_bus.publish("runtime.run_ended_silent", {
                    "run_id": run_id,
                    "session_id": session_id,
                    "tool_calls": tool_calls,
                    "tool_call_count": len(tool_calls),
                    "unique_tools": sorted(set(tool_calls)),
                })
                logger.info(
                    "run_closure_gate: silent run %s — %d tool calls, no visible output",
                    run_id[:12], len(tool_calls),
                )
        except Exception:
            logger.debug("run_closure_gate: failed silent-run check", exc_info=True)


def _on_run_started(payload: dict[str, Any]) -> None:
    """Handle runtime.autonomous_run_started — snapshot git state."""
    run_id = str(payload.get("run_id") or "")
    if run_id:
        _record_pre_run_state(run_id)
        _set_current_run(run_id)


def _on_tool_used(payload: dict[str, Any]) -> None:
    """Track tool calls so we can detect silent runs.

    Tool events from simple_tools.py don't include run_id in their
    payload — _record_tool_call falls back to the current in-flight
    run via _get_current_run().
    """
    run_id = str(payload.get("run_id") or "")
    tool_name = str(payload.get("tool") or payload.get("tool_name") or "")
    if tool_name:
        _record_tool_call(run_id, tool_name)


# ── eventbus subscriber thread ────────────────────────────────────────


def _listener_loop(q: "queue.Queue[dict[str, Any] | None]") -> None:
    global _listener_running
    while _listener_running:
        try:
            item = q.get(timeout=2.0)
            if item is None:
                break
            kind = str(item.get("kind") or "")
            payload = dict(item.get("payload") or {})
            if kind == "runtime.autonomous_run_started":
                _on_run_started(payload)
            elif kind == "runtime.autonomous_run_completed":
                _on_run_completed(payload)
            elif kind == "tool.invoked" or kind == "tool.used":
                _on_tool_used(payload)
        except queue.Empty:
            continue
        except Exception:
            logger.debug("run_closure_gate: listener iteration error", exc_info=True)


def start_run_closure_gate() -> None:
    """Start the eventbus subscriber thread. Safe to call multiple times."""
    global _listener_thread, _listener_running
    if _listener_thread and _listener_thread.is_alive():
        return
    try:
        from core.eventbus.bus import event_bus
        q = event_bus.subscribe()
        _listener_running = True
        _listener_thread = threading.Thread(
            target=_listener_loop,
            args=(q,),
            daemon=True,
            name="run-closure-gate",
        )
        _listener_thread.start()
        logger.warning("run_closure_gate: subscriber started")
    except Exception:
        logger.exception("run_closure_gate: failed to start subscriber")


def stop_run_closure_gate() -> None:
    global _listener_running
    _listener_running = False
