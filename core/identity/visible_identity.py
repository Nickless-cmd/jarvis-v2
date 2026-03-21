from __future__ import annotations

from pathlib import Path

from core.identity.workspace_bootstrap import ensure_default_workspace

IDENTITY_FILES = (
    ("SOUL.md", "SOUL"),
    ("IDENTITY.md", "IDENTITY"),
    ("USER.md", "USER"),
)
MAX_LINES_PER_FILE = 3
MAX_LINE_CHARS = 160


def load_visible_identity_prompt(name: str = "default") -> str | None:
    workspace_dir = ensure_default_workspace(name=name)
    sections: list[str] = []

    for filename, label in IDENTITY_FILES:
        lines = _identity_lines(workspace_dir / filename)
        if not lines:
            continue
        sections.append("\n".join([f"{label}:", *[f"- {line}" for line in lines]]))

    if not sections:
        return None

    return "\n".join(
        [
            "Visible workspace identity truth:",
            *sections,
            "Stay consistent with this identity truth in visible replies.",
        ]
    )


def _identity_lines(path: Path) -> list[str]:
    if not path.exists():
        return []

    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(_bounded_line(line))
        if len(lines) >= MAX_LINES_PER_FILE:
            break
    return lines


def _bounded_line(text: str) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= MAX_LINE_CHARS:
        return normalized
    return normalized[: MAX_LINE_CHARS - 1].rstrip() + "…"
