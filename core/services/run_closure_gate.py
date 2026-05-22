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


# ── per-run state cache ────────────────────────────────────────────────
# Pre-run git snapshot, keyed by run_id. Populated by a pre-run event
# subscriber and consumed by the post-run handler so we can diff.
_pre_run_git_state: dict[str, set[str]] = {}
_pre_run_git_lock = threading.Lock()


def _record_pre_run_state(run_id: str) -> None:
    if not run_id:
        return
    snapshot = _git_porcelain_status()
    with _pre_run_git_lock:
        _pre_run_git_state[run_id] = snapshot


def _pop_pre_run_state(run_id: str) -> set[str]:
    with _pre_run_git_lock:
        return _pre_run_git_state.pop(run_id, set())


# ── tool-call tracking ────────────────────────────────────────────────
# Track which runs have called any tool. We listen for tool events on
# the bus rather than parsing run-internal state.
_run_tool_calls: dict[str, list[str]] = {}
_run_tool_lock = threading.Lock()
# Cap memory: never track more than this many runs' tool histories.
_RUN_TOOL_CACHE_MAX = 256


def _record_tool_call(run_id: str, tool_name: str) -> None:
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

    # Compute new unstaged paths introduced during this run.
    pre = _pop_pre_run_state(run_id)
    post = _git_porcelain_status()
    new_lines = post - pre

    tool_calls = _pop_tool_calls(run_id)

    if new_lines:
        summary = _summarize_unstaged(new_lines)
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


def _on_tool_used(payload: dict[str, Any]) -> None:
    """Track tool calls so we can detect silent runs."""
    run_id = str(payload.get("run_id") or "")
    tool_name = str(payload.get("tool") or payload.get("tool_name") or "")
    if run_id and tool_name:
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
        logger.info("run_closure_gate: subscriber started")
    except Exception:
        logger.exception("run_closure_gate: failed to start subscriber")


def stop_run_closure_gate() -> None:
    global _listener_running
    _listener_running = False
