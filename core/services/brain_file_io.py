"""Low-level file helpers for Jarvis Brain markdown files."""

from __future__ import annotations

from pathlib import Path

import yaml


class MissingFrontmatterError(ValueError):
    """Raised when a markdown file does not start with YAML frontmatter."""


def atomic_write(path: Path, content: str) -> None:
    """Atomically write ``content`` via a sibling temporary file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


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
        raise ValueError(f"frontmatter is not a mapping in {path}")
    return frontmatter, body
