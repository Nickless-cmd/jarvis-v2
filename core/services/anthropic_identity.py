"""Build Jarvis identity prefix from a workspace directory.

Reads SOUL.md, IDENTITY.md, USER.md, STANDING_ORDERS.md (in that order)
and concatenates them into a single system-prompt prefix. Cached per
workspace; invalidated when any file's mtime advances.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_FILES_IN_ORDER = ("SOUL.md", "IDENTITY.md", "USER.md", "STANDING_ORDERS.md")

# cache: workspace_path_str -> (signature, content)
_cache: dict[str, tuple[str, str]] = {}


def _signature(workspace_dir: Path) -> str:
    parts = []
    for name in _FILES_IN_ORDER:
        p = workspace_dir / name
        if p.exists():
            try:
                parts.append(f"{name}:{p.stat().st_mtime_ns}")
            except OSError:
                pass
    return "|".join(parts)


def build_identity_prefix(workspace_dir: Path) -> str:
    """Return concatenated identity files for this workspace, or empty string.

    Format: each present file becomes a `## <FILENAME>\\n\\n<contents>`
    section, joined by blank lines.
    """
    key = str(workspace_dir.resolve())
    sig = _signature(workspace_dir)

    cached = _cache.get(key)
    if cached and cached[0] == sig:
        return cached[1]

    parts = []
    for name in _FILES_IN_ORDER:
        p = workspace_dir / name
        if not p.exists():
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("anthropic_identity: cannot read %s: %s", p, exc)
            continue
        parts.append(f"## {name}\n\n{content.strip()}")

    out = "\n\n".join(parts)
    _cache[key] = (sig, out)
    return out


def invalidate_cache() -> None:
    _cache.clear()
