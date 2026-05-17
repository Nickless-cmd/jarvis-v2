"""Coding lane auto-reviewer — subscriber til coding_lane.commit_landed events.

Når en git commit lander, dispatcher denne subscriber et review til Codex
(gpt-5.3-codex) via coding lane og publiserer resultatet som event.

Design (Claude + Jarvis, 2026-05-17):
- Trigger: eventbus "coding_lane.commit_landed"
- Filtre (Bjørns spec):
  - Skip merge-commits (git log --no-merges style)
  - Skip diffs < 10 linjer — for lidt at reviewe
  - Skip commits med author = "Codex" — loop-beskyttelse
- Budget guard: hvis coding lane har budget-issues, skip gracefully
- Output: publiser "coding_lane.review_completed" event
- Zero-risk: læser kun, rører ikke production, fejler silently
"""

from __future__ import annotations

import logging
import queue
import re
import subprocess
import threading
from typing import Any

logger = logging.getLogger(__name__)

_listener_thread: threading.Thread | None = None
_listener_running: bool = False

# Max diff lines to send to Codex — prevents token-blowup on huge commits
_MAX_DIFF_LINES = 200

# Instruction template sent to Codex for review
_REVIEW_PROMPT_TEMPLATE = """Review this git diff. Return:
1) severity: info / warn / critical
2) observations as bullet points
3) specific improvement suggestions with line references where relevant

Keep under 500 tokens.

Commit message: {message}

Diff:
```diff
{diff}
```"""


def register_event_listeners() -> None:
    """Start background eventbus listener for coding_lane.commit_landed events."""
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
            name="coding-lane-auto-reviewer",
        )
        _listener_thread.start()
        logger.info("coding_lane auto_reviewer: listener started")
    except Exception as exc:
        logger.warning("coding_lane auto_reviewer: failed to start listener: %s", exc)


def stop_event_listeners() -> None:
    """Stop the background listener thread."""
    global _listener_running
    _listener_running = False


def _listener_loop(q: "queue.Queue[dict[str, Any] | None]") -> None:
    global _listener_running
    while _listener_running:
        try:
            item = q.get(timeout=2.0)
            if item is None:
                break
            kind = str(item.get("kind") or "")
            if kind == "coding_lane.commit_landed":
                payload = dict(item.get("payload") or {})
                _handle_commit_landed(payload)
        except queue.Empty:
            continue
        except Exception as exc:
            logger.debug("coding_lane auto_reviewer: listener error: %s", exc)


def _handle_commit_landed(payload: dict[str, Any]) -> None:
    """Receive a commit-landed event, apply filters, dispatch to coding lane."""
    sha = str(payload.get("sha") or "")
    message = str(payload.get("message") or "")
    files = list(payload.get("files") or [])
    author = str(payload.get("author") or "")
    project_root = str(payload.get("project_root") or "")

    if not sha or not project_root:
        logger.debug("coding_lane auto_reviewer: incomplete payload, skipping")
        return

    # --- Filter 1: Skip merge-commits ---
    try:
        parents = subprocess.run(
            ["git", "rev-list", "--parents", "-n", "1", sha],
            capture_output=True, text=True, timeout=10, cwd=project_root,
        )
        parent_count = len(parents.stdout.strip().split()) - 1  # first token is the commit itself
        if parent_count > 1:
            logger.info("coding_lane auto_reviewer: skip merge commit %s", sha[:8])
            _publish_skipped(sha, "merge-commit")
            return
    except Exception:
        pass  # If we can't check, proceed anyway

    # --- Filter 2: Skip commits where author = "Codex" ---
    if "codex" in author.lower():
        logger.info("coding_lane auto_reviewer: skip Codex-authored commit %s", sha[:8])
        _publish_skipped(sha, "codex-author")
        return

    # --- Get diff ---
    diff = _get_diff(sha, project_root)
    if diff is None:
        _publish_skipped(sha, "diff-failed")
        return

    # --- Filter 3: Skip diffs < 10 linjer ---
    diff_lines = diff.count("\n")
    if diff_lines < 10:
        logger.info(
            "coding_lane auto_reviewer: skip small diff (%d lines) %s",
            diff_lines, sha[:8],
        )
        _publish_skipped(sha, "small-diff", detail=f"{diff_lines} lines")
        return

    # --- Truncate diff to prevent token blowup ---
    if diff_lines > _MAX_DIFF_LINES:
        diff_lines_actual = diff_lines
        diff = "\n".join(diff.split("\n")[:_MAX_DIFF_LINES])
        diff += f"\n... (truncated from {diff_lines_actual} lines)"

    # --- Budget guard ---
    if not _has_budget():
        _publish_skipped(sha, "budget-exhausted")
        return

    # --- Dispatch to coding lane ---
    prompt = _REVIEW_PROMPT_TEMPLATE.format(message=message[:200], diff=diff)
    _dispatch_review(sha, message, prompt)


def _get_diff(sha: str, project_root: str) -> str | None:
    """Get the diff for a commit. Returns None on failure."""
    try:
        # Use git show with unified diff format, no color
        result = subprocess.run(
            ["git", "show", sha, "--format=", "--unified=3", "--no-color"],
            capture_output=True, text=True, timeout=30, cwd=project_root,
        )
        if result.returncode != 0:
            logger.warning(
                "coding_lane auto_reviewer: git show failed for %s: %s",
                sha[:8], result.stderr.strip()[:100],
            )
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        logger.warning("coding_lane auto_reviewer: git show timeout for %s", sha[:8])
        return None
    except Exception as exc:
        logger.warning("coding_lane auto_reviewer: git show error: %s", exc)
        return None


def _has_budget() -> bool:
    """Check if coding lane has budget to spend on a review.

    Currently a pass-through — always returns True.
    Future: integrate with a budget tracker.
    """
    return True


def _dispatch_review(sha: str, message: str, prompt: str) -> None:
    """Fire-and-forget dispatch to coding lane. Runs in a background thread."""
    thread = threading.Thread(
        target=_do_review,
        args=(sha, message, prompt),
        daemon=True,
        name=f"codex-review-{sha[:8]}",
    )
    thread.start()


def _do_review(sha: str, message: str, prompt: str) -> None:
    """Execute the review via coding lane and publish result."""
    try:
        from core.services.non_visible_lane_execution import execute_coding_lane

        result = execute_coding_lane(message=prompt)
        text = str(result.get("text") or "")
        status = str(result.get("status") or "unknown")

        if status != "completed" or not text:
            logger.warning(
                "coding_lane auto_reviewer: coding lane failed for %s: %s",
                sha[:8], status,
            )
            _publish_review(sha, message, status="failed", detail=status)
            return

        # Parse severity from review output
        severity = "info"
        text_lower = text.lower()[:200]  # scan first 200 chars for keyword
        if "critical" in text_lower:
            severity = "critical"
        elif "warn" in text_lower:
            severity = "warn"

        _publish_review(
            sha, message,
            status="completed",
            severity=severity,
            review_text=text[:2000],
        )

    except Exception as exc:
        logger.warning(
            "coding_lane auto_reviewer: review dispatch failed for %s: %s",
            sha[:8], exc,
        )
        _publish_review(sha, message, status="failed", detail=str(exc)[:200])


def _publish_skipped(sha: str, reason: str, detail: str = "") -> None:
    """Publish that a review was skipped (filter match)."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("coding_lane.review_skipped", {
            "sha": sha,
            "reason": reason,
            "detail": detail,
        })
    except Exception:
        pass


def _publish_review(
    sha: str,
    message: str,
    *,
    status: str,
    severity: str = "info",
    review_text: str = "",
    detail: str = "",
) -> None:
    """Publish a review result event."""
    try:
        from core.eventbus.bus import event_bus
        payload: dict[str, Any] = {
            "sha": sha,
            "message": message[:200],
            "status": status,
            "severity": severity,
        }
        if review_text:
            payload["review"] = review_text
        if detail:
            payload["detail"] = detail
        event_bus.publish("coding_lane.review_completed", payload)
    except Exception:
        pass
