"""Read-before-write guard — prevents overwrite of existing files without prior read.

When `write_file` targets a file that already exists, this guard checks whether
the file has been read in the current session. If not, it blocks the write and
returns an error with the file's current content preview, forcing the LLM to
read first and then make an informed edit.

This is a safety net for identity/personality files (USER.md, MEMORY.md, etc.)
that have been accidentally overwritten in the past, destroying months of
accumulated context.

Two hardenings landed 2026-05-14 after a SOUL.md + USER.md overwrite:

  1. **Cross-worker via shared_cache.** Was a per-process in-memory dict.
     jarvis-api runs 4 workers — a read on worker A was invisible to a
     write on worker B, so the guard silently let cross-worker writes
     through. Now uses shared_cache (SQLite-backed) so all workers see
     the same recent-reads.

  2. **Bash overwrite detection.** The guard only checked write_file.
     Jarvis bypassed it by using `bash cp ... SOUL.md` to overwrite —
     no read_file → no track, no write_file → no guard, just gone.
     check_bash_command_safe now sniffs bash commands for cp/mv/redirect/
     tee patterns targeting protected files and blocks the same way.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Protected files ──────────────────────────────────────────
_PROTECTED_FILENAMES = frozenset({
    "USER.md",
    "MEMORY.md",
    "SOUL.md",
    "IDENTITY.md",
    "STANDING_ORDERS.md",
    "SKILLS.md",
    "MANIFEST.md",
    "VOICE.md",
    "CHRONICLE.md",
})

# How long a recent-read is considered "fresh enough" to satisfy the guard.
# Stored as TTL in shared_cache so cross-process visibility is automatic.
_READ_FRESHNESS_SECONDS = 600  # 10 minutes

_CACHE_KEY_PREFIX = "rbw_guard:"  # shared_cache key prefix


def _cache_key(session_id: str, abs_path: str) -> str:
    return f"{_CACHE_KEY_PREFIX}{session_id}:{abs_path}"


def record_read(path: str, session_id: str = "default") -> None:
    """Record that a file has been read in this session.

    Persisted to shared_cache so all worker processes see it. Best-effort —
    silently degrades if the cache is unavailable.
    """
    try:
        from core.services import shared_cache as _sc
        abs_path = str(Path(path).expanduser().resolve())
        _sc.set(
            _cache_key(session_id, abs_path),
            {"path": abs_path, "session_id": session_id},
            ttl_seconds=_READ_FRESHNESS_SECONDS,
        )
    except Exception as exc:
        logger.debug("read_before_write_guard: record_read failed: %s", exc)


def _was_read(abs_path: str, session_id: str) -> bool:
    """True if `abs_path` was read in this session within the TTL window.

    Also checks the "default" session as a fallback — many callers don't
    propagate the real session_id, so reads under default + writes under
    default are a common path.
    """
    try:
        from core.services import shared_cache as _sc
        if _sc.get(_cache_key(session_id, abs_path)) is not None:
            return True
        if session_id != "default" and _sc.get(_cache_key("default", abs_path)) is not None:
            return True
    except Exception:
        pass
    return False


def is_protected(path: str) -> bool:
    """True if the path's basename is in the protected set."""
    try:
        name = Path(path).expanduser().name
    except Exception:
        return False
    return name in _PROTECTED_FILENAMES


def check_read_before_write(
    path: str,
    session_id: str = "default",
) -> tuple[bool, str | None]:
    """Check whether write_file should be allowed for this path.

    Returns (allowed, reason). If allowed=False, the write is blocked.
    """
    target = Path(path).expanduser().resolve()

    if target.name not in _PROTECTED_FILENAMES:
        return True, None
    if not target.exists():
        return True, None
    if _was_read(str(target), session_id):
        return True, None

    # Block — file exists but hasn't been read
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
            f"læst i denne session. Læs filen først med `read_file('{target}')`, "
            f"brug derefter `edit_file` for kirurgiske ændringer — eller "
            f"`write_file` hvis du har læst og forstået indholdet.\n\n"
            f"Første 20 linjer:\n{preview}"
        )
    except Exception as e:
        reason = (
            f"⚠️ READ-BEFORE-WRITE GUARD: {target.name} eksisterer men er ikke "
            f"blevet læst i denne session. Læs filen først. (Kunne ikke læse "
            f"preview: {e})"
        )

    logger.info(
        "read_before_write_guard: BLOCKED write to %s (session=%s)",
        target.name, session_id,
    )
    return False, reason


# ── Bash overwrite detection ──────────────────────────────────
# Today Jarvis bypassed the write_file guard by using `bash cp` to
# overwrite SOUL.md. These patterns catch the common shell ways to
# clobber a file: cp/mv to a path or a directory, > redirect, tee.

_BASH_OVERWRITE_PATTERNS = [
    # cp [opts] src dest  — dest may be file or directory
    re.compile(
        r"\bcp\s+(?:-[a-zA-Z]+\s+)*\S+\s+(\S+)",
    ),
    # mv [opts] src dest
    re.compile(
        r"\bmv\s+(?:-[a-zA-Z]+\s+)*\S+\s+(\S+)",
    ),
    # > path or >> path — capture path
    re.compile(r"(?<![<>])>>?\s*([^\s|;&]+)"),
    # tee [-a] path
    re.compile(r"\btee\s+(?:-[a-zA-Z]+\s+)*([^\s|;&]+)"),
    # sed -i ... path
    re.compile(r"\bsed\s+(?:-\S+\s+)*(?:--?in[-_]?place\S*\s+)?[^\s]*\s+([^\s|;&]+)\s*$"),
]


def _normalize_path(p: str, *, base: Path | None = None) -> Path | None:
    """Best-effort resolve of a path token (may be ~/, relative, ./)."""
    try:
        expanded = Path(p).expanduser()
        if not expanded.is_absolute() and base is not None:
            expanded = base / expanded
        return expanded.resolve()
    except Exception:
        return None


def check_bash_command_safe(
    command: str,
    *,
    session_id: str = "default",
    cwd: str | None = None,
) -> tuple[bool, str | None]:
    """Sniff a bash command for protected-file overwrites without prior read.

    Returns (allowed, reason). Conservative: when in doubt about whether
    the pattern is a real overwrite, we err on the side of blocking. The
    user can always read the file first to satisfy the guard.

    Detected patterns:
      - cp ... PROTECTED.md
      - cp ... /path/to/dir/  (where dir contains a PROTECTED.md target)
      - mv ... PROTECTED.md
      - > PROTECTED.md / >> PROTECTED.md
      - tee PROTECTED.md
      - sed -i ... PROTECTED.md
    """
    cmd = str(command or "")
    if not cmd:
        return True, None

    # Fast path: no protected filename anywhere in the command → allow
    if not any(name in cmd for name in _PROTECTED_FILENAMES):
        return True, None

    base = Path(cwd).expanduser().resolve() if cwd else None

    # Collect every protected-target candidate from the command
    candidates: list[Path] = []
    for pattern in _BASH_OVERWRITE_PATTERNS:
        for match in pattern.finditer(cmd):
            raw_path = match.group(1).strip().strip("\"'")
            if not raw_path:
                continue
            resolved = _normalize_path(raw_path, base=base)
            if resolved is None:
                continue
            # If the captured path IS a protected file → candidate
            if resolved.name in _PROTECTED_FILENAMES:
                candidates.append(resolved)
                continue
            # If the captured path is an existing directory, and a source
            # path in the command is a protected filename, the cp/mv lands
            # there as `dir/PROTECTED.md`. Check.
            if resolved.is_dir():
                for name in _PROTECTED_FILENAMES:
                    if name in cmd:
                        possible = resolved / name
                        # Only treat as overwrite candidate if it would
                        # actually clobber an existing file there.
                        if possible.exists():
                            candidates.append(possible)
            # Trailing slash in raw_path also means destination is a dir
            elif raw_path.endswith("/"):
                for name in _PROTECTED_FILENAMES:
                    if name in cmd:
                        possible = resolved / name
                        if possible.exists():
                            candidates.append(possible)

    # Dedupe
    unique_candidates = []
    seen: set[str] = set()
    for c in candidates:
        s = str(c)
        if s not in seen:
            seen.add(s)
            unique_candidates.append(c)

    if not unique_candidates:
        return True, None

    # Now check each candidate against the recent-read tracker
    for target in unique_candidates:
        if _was_read(str(target), session_id):
            continue
        # Block — found a protected overwrite without prior read
        try:
            preview = "\n".join(
                target.read_text(encoding="utf-8", errors="replace").split("\n")[:20]
            )
        except Exception:
            preview = "(could not read preview)"
        reason = (
            f"⚠️ READ-BEFORE-WRITE GUARD (bash): denne kommando vil "
            f"overskrive {target.name} ({target}) men filen er ikke "
            f"blevet læst i denne session. Læs den først med "
            f"`read_file('{target}')`, og kør derefter kommandoen igen.\n\n"
            f"Første 20 linjer af filen:\n{preview}"
        )
        logger.info(
            "read_before_write_guard: BLOCKED bash overwrite of %s (session=%s)",
            target.name, session_id,
        )
        return False, reason

    return True, None


def clear_session(session_id: str = "default") -> None:
    """Clear all recent-read entries for a session in shared_cache."""
    try:
        from core.services import shared_cache as _sc
        _sc.invalidate_prefix(f"{_CACHE_KEY_PREFIX}{session_id}:")
    except Exception as exc:
        logger.debug("read_before_write_guard: clear_session failed: %s", exc)


def get_session_reads(session_id: str = "default") -> set[str]:
    """Return the set of paths read in this session (for debugging).

    Reads directly from shared_cache; only returns live (non-expired) entries.
    """
    out: set[str] = set()
    try:
        from core.runtime.db import connect
        import time
        now = time.time()
        prefix = f"{_CACHE_KEY_PREFIX}{session_id}:"
        with connect() as conn:
            rows = conn.execute(
                "SELECT cache_key FROM shared_cache "
                "WHERE cache_key LIKE ? AND expires_at > ?",
                (prefix + "%", now),
            ).fetchall()
        for r in rows:
            full_key = str(r[0])
            path = full_key.removeprefix(prefix)
            if path:
                out.add(path)
    except Exception as exc:
        logger.debug("read_before_write_guard: get_session_reads failed: %s", exc)
    return out


def build_read_before_write_guard_surface() -> dict[str, object]:
    """MC surface — read-only meta-projection."""
    return {
        "active": True,
        "mode": "read_before_write_guard",
        "protected_files": sorted(_PROTECTED_FILENAMES),
        "freshness_seconds": _READ_FRESHNESS_SECONDS,
        "default_session_reads": sorted(get_session_reads("default")),
        "authority": "policy-enforcing",
    }


def _emit_read_before_write_guard_event(
    kind: str, payload: dict[str, object] | None = None
) -> None:
    """Defensive scoped event emitter."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"read_before_write_guard.{kind}", payload or {})
    except Exception:
        pass


# ── Operator-side variant (Phase 1: enforcement on operator_* tools) ─────
#
# Same shared_cache TTL model, but paths are NOT resolved (the operator's
# filesystem is foreign to the backend — Path.resolve() would silently
# rewrite "~/foo" to /home/bs/foo on the LXC and the cache key wouldn't
# match what the operator-side handler later sees). We normalize lightly
# (strip + lowercase drive letter on Windows + forward-slashes) so
# C:\Users\onkel\x and c:/users/onkel/x track as the same file.
#
# Unlike the protected-filename mechanism above, operator_* enforcement
# is universal: ANY existing file on the operator's machine that hasn't
# been read in the current session is blocked from write/edit. New files
# (path doesn't yet exist on operator side — which we can't check from
# here, so we treat as a separate signal below) pass through.

_OPERATOR_CACHE_KEY_PREFIX = "rbw_operator:"


def _normalize_operator_path(path: str) -> str:
    """Light normalization for cross-OS path consistency."""
    s = str(path or "").strip()
    if not s:
        return s
    # Forward-slashes everywhere
    s = s.replace(chr(92) + chr(92), "/").replace(chr(92), "/")
    # Lowercase Windows drive letter (C:/ → c:/) — keeps the rest as-is
    if len(s) >= 2 and s[1] == ":" and s[0].isalpha():
        s = s[0].lower() + s[1:]
    return s


def _operator_cache_key(session_id: str, norm_path: str) -> str:
    return f"{_OPERATOR_CACHE_KEY_PREFIX}{session_id}:{norm_path}"


def record_operator_read(path: str, session_id: str = "default") -> None:
    """Note that the operator side has read this path. Best-effort."""
    try:
        from core.services import shared_cache as _sc
        norm = _normalize_operator_path(path)
        if not norm:
            return
        _sc.set(
            _operator_cache_key(session_id, norm),
            {"path": norm, "session_id": session_id},
            ttl_seconds=_READ_FRESHNESS_SECONDS,
        )
    except Exception as exc:
        logger.debug("record_operator_read failed: %s", exc)


def _operator_was_read(norm_path: str, session_id: str) -> bool:
    try:
        from core.services import shared_cache as _sc
        if _sc.get(_operator_cache_key(session_id, norm_path)) is not None:
            return True
        if session_id != "default" and _sc.get(
            _operator_cache_key("default", norm_path)
        ) is not None:
            return True
    except Exception:
        pass
    return False


def check_operator_read_before_write(
    path: str,
    session_id: str = "default",
    file_exists: bool | None = None,
) -> tuple[bool, str | None]:
    """Block operator_write_file / operator_edit_file on existing files
    the LLM hasn't read in this session.

    file_exists: pass True for operator_edit_file (which by definition
    requires an existing file). For operator_write_file the caller can
    pass None (treated as "we don't know — assume yes if cached read
    is missing", which is the safer default for an LLM that tends to
    forget read steps).
    """
    norm = _normalize_operator_path(path)
    if not norm:
        return True, None  # caller will reject empty path anyway
    # Brand-new file: nothing to clobber, and you can't read what doesn't
    # exist (read → ENOENT → permanent deadlock that pushes the LLM to
    # bypass the guard via `bash cat >`). The caller (operator_write_file)
    # determines existence on the operator side and passes file_exists=False
    # for new files. Honor it — this is what the module docstring promises
    # ("New files ... pass through").
    if file_exists is False:
        return True, None
    if _operator_was_read(norm, session_id):
        return True, None
    # No prior read recorded. For operator_edit_file we know the file
    # must exist; for operator_write_file the caller may not know but
    # the cost of one extra read_file call is small and the upside
    # (preventing accidental clobber) is large.
    hint = (
        "operator_read_file('{p}') skal kaldes først i denne session, "
        "så du arbejder på et bevidst grundlag og ikke ved et "
        "uheld overskriver indhold du ikke har set."
    ).format(p=path)
    reason = (
        "⚠️ READ-BEFORE-WRITE GUARD (operator): {p}\n\n{hint}"
    ).format(p=path, hint=hint)
    return False, reason


# ── Phase 2/3: Session edit/write tracker ─────────────────────────────────
#
# After each successful operator_edit_file or operator_write_file, we
# record what file was touched under a per-session key. Lets us attach
# a small "so far this session" block to tool results — Jarvis sees
# the running tally automatically without us building a sidebar that
# gets banner-blindness.
#
# shared_cache backed so all uvicorn workers see the same tally.

_SESSION_EDITS_KEY_PREFIX = "rbw_session_edits:"
_SESSION_EDITS_TTL_SECONDS = 24 * 60 * 60  # 24h — survives long working sessions


def _session_edits_key(session_id: str) -> str:
    return _SESSION_EDITS_KEY_PREFIX + session_id


def record_operator_edit(
    path: str, session_id: str = "default", kind: str = "edit"
) -> None:
    """Record that the operator side mutated this file. kind is 'edit' or 'write'."""
    try:
        from datetime import datetime as _dt, UTC as _UTC
        from core.services import shared_cache as _sc
        norm = _normalize_operator_path(path)
        if not norm:
            return
        key = _session_edits_key(session_id)
        existing = _sc.get(key) or {}
        if not isinstance(existing, dict):
            existing = {}
        paths = list(existing.get("paths") or [])
        # Dedup but keep order — most recent moves to the end
        if norm in paths:
            paths.remove(norm)
        paths.append(norm)
        # Cap at 50 — long sessions don't need to surface ancient files
        if len(paths) > 50:
            paths = paths[-50:]
        existing["paths"] = paths
        existing["edits"] = int(existing.get("edits") or 0) + (1 if kind == "edit" else 0)
        existing["writes"] = int(existing.get("writes") or 0) + (1 if kind == "write" else 0)
        existing["last_kind"] = kind
        existing["last_path"] = norm
        existing["last_iso"] = _dt.now(_UTC).isoformat()
        _sc.set(key, existing, ttl_seconds=_SESSION_EDITS_TTL_SECONDS)
    except Exception as exc:
        logger.debug("record_operator_edit failed: %s", exc)


def get_session_edit_summary(session_id: str = "default") -> dict:
    """Return the running tally for this session. Empty dict if nothing yet."""
    try:
        from core.services import shared_cache as _sc
        data = _sc.get(_session_edits_key(session_id))
        if isinstance(data, dict):
            return {
                "paths_touched": list(data.get("paths") or []),
                "edit_count": int(data.get("edits") or 0),
                "write_count": int(data.get("writes") or 0),
                "last_kind": data.get("last_kind"),
                "last_path": data.get("last_path"),
                "last_iso": data.get("last_iso"),
            }
    except Exception:
        pass
    return {}
