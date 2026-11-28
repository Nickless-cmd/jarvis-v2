"""Low-level file helpers for Jarvis Brain markdown files."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml


class MissingFrontmatterError(ValueError):
    """Raised when a markdown file does not start with YAML frontmatter."""


def _fsync_directory(directory: Path) -> None:
    """fsync ``directory`` so the rename itself survives a crash.

    Measured 28/11-2026: two brain entries stood at 0 bytes on disk while the
    index still reported 928 bytes and a mtime matching to the nanosecond.
    ext4's ``auto_da_alloc`` only flushes a rename that lands ON an existing
    file; ``write_entry`` creates a new path, so nothing flushed the directory
    entry. Without this the rename is not durable even when the file is.
    """
    fd = os.open(str(directory), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write(path: Path, content: str) -> None:
    """Atomically and durably write ``content`` via a unique sibling temp file.

    The temp name is unique rather than ``path + ".tmp"``: the fixed name is
    itself a race, measured at 275 ``FileNotFoundError`` out of 300 rounds with
    two threads, because one thread's rename steals the other's temp file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = (path.stat().st_mode & 0o777) if path.exists() else 0o644
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
        _fsync_directory(path.parent)
    finally:
        tmp.unlink(missing_ok=True)


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter and body from a markdown file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise MissingFrontmatterError(f"missing frontmatter in {path}")
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError(f"unterminated frontmatter in {path}")
    yaml_text = parts[0][len("---\n"):]
    body = parts[1]
    frontmatter = yaml.safe_load(yaml_text) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError("frontmatter is not a mapping in {path}")
    return frontmatter, body
