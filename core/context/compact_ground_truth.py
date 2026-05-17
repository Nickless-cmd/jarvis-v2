"""Ground-truth injection and freshness checking for context compaction.

Lag A: Collects verifiable facts (git SHA, commit log, key-file checks)
before compaction so the LLM doesn't have to guess whether something
exists or not.

Lag B: Stamps each compact marker with the git SHA at creation time,
enabling staleness detection without re-validation.

Usage:
    from core.context.compact_ground_truth import (
        collect_compact_ground_truth,
        format_ground_truth_block,
        get_current_git_sha,
        check_compact_marker_freshness,
    )

    # Before compaction:
    gt = collect_compact_ground_truth()
    prompt = format_ground_truth_block(gt) + original_prompt

    # After compaction, when storing marker:
    sha = get_current_git_sha()
    store_compact_marker(session_id, text, git_sha=sha)

    # Later, when reading marker:
    freshness = check_compact_marker_freshness(stored_sha)
"""
from __future__ import annotations

import logging
import subprocess
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_DIR = Path("/media/projects/jarvis-v2")

# Key files to verify existence of — these are frequently claimed "missing"
# by compaction LLMs even when they're committed and live.
KEY_FILES: list[str] = [
    "core/runtime/db_credit_assignment.py",
    "core/services/chat_sessions.py",
    "core/services/heartbeat_runtime.py",
    "core/services/identity_composer.py",
    "core/context/auto_compact.py",
    "core/context/session_compact.py",
    "core/context/compact_llm.py",
    "core/context/run_compact.py",
    "core/tools/wake_word_tool.py",
    "core/tools/speak_tool.py",
    "core/tools/smart_compact_tools.py",
]


def get_current_git_sha() -> str:
    """Get the current git HEAD SHA of the Jarvis repo. Returns empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=REPO_DIR, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception as exc:
        logger.warning("compact_ground_truth: git rev-parse failed: %s", exc)
        return ""


def get_commit_count_since(start_sha: str | None = None) -> int | None:
    """Count commits between start_sha and HEAD. Returns None if start_sha is empty or unknown."""
    if not start_sha:
        return None
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{start_sha}..HEAD"],
            capture_output=True, text=True, cwd=REPO_DIR, timeout=5,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
        return None
    except Exception:
        return None


def get_recent_commit_log(since: str | None = None, count: int = 30) -> str:
    """Get recent git log as oneline. Optionally since an ISO timestamp.

    Returns empty string on failure.
    """
    try:
        cmd = ["git", "log", "--oneline", f"-{count}"]
        if since:
            cmd.insert(2, f"--since={since}")
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=REPO_DIR, timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception as exc:
        logger.warning("compact_ground_truth: git log failed: %s", exc)
        return ""


def check_key_files(key_files: list[str] | None = None) -> dict[str, str]:
    """Check existence of key files. Returns dict of {relative_path: 'exists'|'missing'}."""
    checked = key_files or KEY_FILES
    result: dict[str, str] = {}
    for rel in checked:
        path = REPO_DIR / rel
        result[rel] = "exists" if path.exists() else "missing"
    return result


def check_cognitive_decisions_count() -> int | None:
    """Return count of cognitive_decision records in DB, or None on failure."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM cognitive_decisions"
            ).fetchone()
            return int(row[0]) if row else None
    except Exception:
        return None


def collect_compact_ground_truth(session_id: str | None = None) -> dict[str, Any]:
    """Collect ground-truth data before compaction.

    Returns a dict with:
      - current_git_sha: str
      - recent_commits: str (git log --oneline -30)
      - key_files: dict[str, str]
      - cognitive_decisions_count: int | None
      - collected_at: str (ISO timestamp)

    If session_id is provided, also fetches session_created_at for
    `--since` filtering of git log.
    """
    sha = get_current_git_sha()

    # Try to get session timestamp for granular git log
    session_since: str | None = None
    if session_id:
        try:
            from core.services.chat_sessions import get_chat_session
            info = get_chat_session(session_id)
            if info and info.get("created_at"):
                session_since = info["created_at"]
        except Exception:
            pass

    return {
        "current_git_sha": sha,
        "recent_commits": get_recent_commit_log(since=session_since),
        "key_files": check_key_files(),
        "cognitive_decisions_count": check_cognitive_decisions_count(),
        "collected_at": datetime.now(UTC).isoformat(),
    }


def format_ground_truth_block(gt: dict[str, Any]) -> str:
    """Format a ground-truth dict into a human-readable block for prompt injection."""
    lines: list[str] = [
        "=== GROUND TRUTH (verifiable facts) ===",
        f"Current git HEAD: {gt.get('current_git_sha', '?')}",
        f"Collected at: {gt.get('collected_at', '?')}",
        "",
    ]

    commits = gt.get("recent_commits", "")
    if commits:
        lines.append(f"Commits (session-related):\n{commits}")
        lines.append("")

    files = gt.get("key_files", {})
    if files:
        lines.append("Key files:")
        for rel, status in sorted(files.items()):
            lines.append(f"  [{status.upper()}] {rel}")
        lines.append("")

    dec_count = gt.get("cognitive_decisions_count")
    if dec_count is not None:
        lines.append(f"cognitive_decisions records in DB: {dec_count}")
    else:
        lines.append("cognitive_decisions table: not accessible")

    lines.append("=== END GROUND TRUTH ===")
    return "\n".join(lines)


def get_compact_marker_freshness(stored_sha: str | None) -> dict[str, Any]:
    """Check freshness of a stored compact marker against current git HEAD.

    Returns:
        {
            "stored_sha": str | None,
            "current_sha": str,
            "fresh": bool,          # True if SHAs match or stored_sha is empty
            "commits_since": int | None,   # None if can't compute
            "status": "fresh" | "stale" | "unknown",
        }
    """
    current = get_current_git_sha()
    if not stored_sha or not current:
        return {
            "stored_sha": stored_sha,
            "current_sha": current,
            "fresh": not stored_sha,  # no stored SHA = can't tell, treat as fresh
            "commits_since": None,
            "status": "unknown",
        }

    if stored_sha == current:
        return {
            "stored_sha": stored_sha,
            "current_sha": current,
            "fresh": True,
            "commits_since": 0,
            "status": "fresh",
        }

    commits = get_commit_count_since(stored_sha)
    return {
        "stored_sha": stored_sha,
        "current_sha": current,
        "fresh": False,
        "commits_since": commits,
        "status": "stale",
    }
