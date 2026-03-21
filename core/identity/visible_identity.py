from __future__ import annotations

import hashlib
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


def load_visible_identity_summary(name: str = "default") -> dict[str, object]:
    workspace_dir = ensure_default_workspace(name=name)
    files: list[dict[str, object]] = []
    total_extracted_lines = 0

    for filename, label in IDENTITY_FILES:
        path = workspace_dir / filename
        lines = _identity_lines(path)
        total_extracted_lines += len(lines)
        files.append(
            {
                "label": label,
                "file": filename,
                "present": path.exists(),
                "has_extracted_text": bool(lines),
                "extracted_lines": len(lines),
            }
        )

    prompt = load_visible_identity_prompt(name=name)
    return {
        "workspace": str(workspace_dir),
        "name": name,
        "active": bool(prompt),
        "files": files,
        "source_files": [item["file"] for item in files if item["has_extracted_text"]],
        "extracted_line_count": total_extracted_lines,
        "prompt_chars": len(prompt or ""),
        "fingerprint": _fingerprint(prompt),
    }


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


def _fingerprint(text: str | None) -> str | None:
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
