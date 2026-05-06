"""Read-before-write guard — prevents overwrite of existing files without prior read.

When `write_file` targets a file that already exists, this guard checks whether
the file has been read in the current session. If not, it blocks the write and
returns an error with the file's current content preview, forcing the LLM to
read first and then make an informed edit.

This is a safety net for identity/personality files (USER.md, MEMORY.md, etc.)
that have been accidentally overwritten in the past, destroying months of
accumulated context.

Design:
- Tracks file reads per session via a lightweight in-memory set.
- Only blocks writes to files that ALREADY EXIST and are in the protected set.
- New files (doesn't exist yet) are always allowed — no data to lose.
- Files outside the protected set are always allowed.
- The guard can be bypassed by the user explicitly confirming (not implemented
  at this level — the LLM should read first and then write, which satisfies
  the guard).
- Session tracking uses the visible-run session_id from the runtime context.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Protected files ──────────────────────────────────────────
# These files contain identity, memory, and relationship data that must never
# be overwritten without reading first. The canonical workspace paths are
# resolved at check time.
_PROTECTED_FILENAMES = frozenset({
    "USER.md",
    "MEMORY.md",
    "SOUL.md",
    "IDENTITY.md",
    "STANDING_ORDERS.md",
    "SKILLS.md",
})

# ── Session read-tracker ─────────────────────────────────────
# Maps session_id → set of absolute paths that have been read in that session.
# This is in-memory only — resets on restart. That's fine: the guard is about
# preventing accidental overwrite within a single conversation/run, not across
# restarts (where the model context is fresh anyway).
_read_tracker: dict[str, set[str]] = {}


def record_read(path: str, session_id: str = "default") -> None:
    """Record that a file has been read in this session."""
    abs_path = str(Path(path).expanduser().resolve())
    if session_id not in _read_tracker:
        _read_tracker[session_id] = set()
    _read_tracker[session_id].add(abs_path)


def check_read_before_write(
    path: str,
    session_id: str = "default",
) -> tuple[bool, str | None]:
    """Check whether write_file should be allowed for this path.

    Returns (allowed, reason). If allowed=False, the write is blocked and
    the reason explains why.

    Logic:
    1. If the file's basename is not in the protected set → allow.
    2. If the file doesn't exist yet (new file) → allow.
    3. If the file has been read in this session → allow.
    4. Otherwise → block with a helpful message including current content preview.
    """
    target = Path(path).expanduser().resolve()

    # Step 1: Only protect specific files
    if target.name not in _PROTECTED_FILENAMES:
        return True, None

    # Step 2: New files are always fine
    if not target.exists():
        return True, None

    # Step 3: Already read in this session → allow
    abs_path = str(target)
    session_reads = _read_tracker.get(session_id, set())
    if abs_path in session_reads:
        return True, None

    # Step 4: Block — file exists but hasn't been read
    # Read a preview of the current content to include in the error
    try:
        current_content = target.read_text(encoding="utf-8", errors="replace")
        content_lines = current_content.split("\n")
        preview_lines = content_lines[:20]
        preview = "\n".join(preview_lines)
        total_lines = len(content_lines)
        total_bytes = len(current_content.encode("utf-8"))
        reason = (
            f"⚠️ READ-BEFORE-WRITE GUARD: {target.name} eksisterer allerede "
            f"({total_bytes} bytes, {total_lines} linjer) men er ikke blevet "
            f"læst i denne session. Læs filen først med `read_file`, brug "
            f"derefter `edit_file` for kirurgiske ændringer — eller `write_file` "
            f"hvis du har læst og forstået indholdet.\n\n"
            f"Første 20 linjer:\n{preview}"
        )
    except Exception as e:
        reason = (
            f"⚠️ READ-BEFORE-WRITE GUARD: {target.name} eksisterer men er ikke "
            f"blevet læst i denne session. Læs filen først. (Kunne ikke læse "
            f"preview: {e})"
        )

    logger.info(f"Read-before-write guard blocked write to {target.name} "
                f"(session={session_id}, reads={len(session_reads)})")

    return False, reason


def clear_session(session_id: str = "default") -> None:
    """Clear the read-tracker for a session (e.g., on session end)."""
    _read_tracker.pop(session_id, None)


def get_session_reads(session_id: str = "default") -> set[str]:
    """Return the set of paths read in this session (for debugging)."""
    return _read_tracker.get(session_id, set()).copy()